from __future__ import annotations
import asyncio
from typing import Any, Callable, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass

if TYPE_CHECKING:
    from agent2.core.agent import Agent
    from agent2.core.session import Session
    from agent2.core.workspace import Workspace

class Rollout(BaseModel):
    """
    Represents the data store and history for a specific agent task execution.
    Saved into a JSON file within the rollout directory.
    Tracks the session/agent relationships, deployment info, and history.
    """
    config_path: str
    id: str
    date_deployed: str
    parent: Optional[str] = None
    children: list[str] = Field(default_factory=list)
    raw_chat: list[Any] = Field(default_factory=list)
    action_history: list[Any] = Field(default_factory=list)


class WorkspacePolicy(str, Enum):
    ISOLATED = "isolated"
    CLONE = "clone"
    SHARED = "shared"


class AgentConfig(BaseModel):
    """
    Configuration for an agent, typically loaded from a TOML file.
    Defines the identity, instructions, and prompt structures for the agent.
    """
    path: str
    subagent_name: str
    subagent_description: str
    model: str
    api_base_url: Optional[str] = None
    api_key_env_var: Optional[str] = None
    system_prompt: str
    prompt_wrap_top: Optional[str] = None
    spec_prompt_middle: Optional[str] = None
    prompt_wrap_bottom: str
    followup_prompt_wrapper: str
    max_steps: int = Field(gt=0)
    constructors: list[str]
    hooks: list[str]
    primary_tools: list[str]
    secondary_tools: list[str]
    workspace_policy: WorkspacePolicy
    subagent_names: list[str]


@dataclass
class Message:
    """Represents a message sent between agents or from the pipeline."""
    target_id: str
    content: str


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Completed single-agent output and its generated artifacts."""
    answer: Any
    rollout_id: str
    workspace: Workspace


PendingContinuation = Callable[[Any], Any]


@dataclass(slots=True)
class HookResult:
    """Output from a hook and whether it handled the assistant response."""
    output: str | None = None
    consumed: bool = False


class Constructor(ABC):
    """Classes which wrap functions that run before the agent loop begins, to setup the agent."""
    @abstractmethod
    def setup(self, agent: Agent, prompt: str) -> None:
        """
        Execute setup logic before the agent loop.
        
        Args:
            agent (Agent): The agent instance to be set up.
            prompt (str): The initial user input or task description.
        """
        pass

    @abstractmethod
    def followup(self, agent: Agent, prompt: str) -> None:
        """
        Execute followup logic on the latest user message.
        
        Args:
            agent (Agent): The agent instance whose chat is to be modified.
            prompt (str): The new user message content.
        """
        pass


class Hook(ABC):
    """Classes which wrap functions that run in the agent loop right after the LLM response is parsed.
    Hook output is appended to the tool response or user message."""
    @abstractmethod
    def run(self, agent: Agent, response: Any) -> HookResult | None:
        """
        Execute the hook logic.
        
        Args:
            agent (Agent): The active agent running the hook.
            response (Any): The parsed LLM response triggering the hook.
            
        Returns:
            HookResult | None: Optional output and response-consumption state.
        """
        pass


class Pipeline(ABC):
    """Abstract pipeline that gets implemented for specific pipeline types."""
    def __init__(self) -> None:
        self.active_agents: dict[str, Agent] = {}
        self.agent_tasks: dict[str, asyncio.Task] = {}

    def register_agents(self, agents: list[Agent]) -> None:
        """Register agents as members of this pipeline's messaging boundary."""
        for agent in agents:
            if agent.rollout.id in self.active_agents and self.active_agents[agent.rollout.id] is not agent:
                raise ValueError(f"Active agent {agent.rollout.id!r} is already registered")
            self.active_agents[agent.rollout.id] = agent
            agent.pipeline = self

    async def transfer_message(self, sender: Agent, message: Message) -> None:
        """Transfer a message when its target is active in this pipeline."""
        target = self.active_agents.get(message.target_id)
        if target:
            name = getattr(getattr(sender, "config", None), "subagent_name", "agent")
            await target.receive_message(
                f"Message from {name} ({sender.rollout.id}):\n{message.content}"
            )

    def start_agent(self, agent: Agent) -> asyncio.Task:
        """Register and run an agent under this pipeline."""
        self.register_agents([agent])
        task = asyncio.create_task(self.watch_agent(agent))
        self.agent_tasks[agent.rollout.id] = task
        return task

    def spawn_agent(self, parent: Agent, subagent_name: str, instructions: str) -> str:
        """Create and start one permitted child agent."""
        if subagent_name not in parent.config.subagent_names:
            raise ValueError(f"Subagent {subagent_name!r} is not allowed by this agent's config")
        config = parent.session.get_config_by_name(subagent_name)
        from agent2.core.agent import Agent

        workspace = {
            WorkspacePolicy.ISOLATED: lambda: type(parent.workspace)(parent.session),
            WorkspacePolicy.CLONE: parent.workspace.clone,
            WorkspacePolicy.SHARED: lambda: parent.workspace,
        }[config.workspace_policy]()
        child = Agent(
            parent.session,
            workspace,
            config,
            f"{instructions}\n\nYour parent agent's rollout ID is {parent.rollout.id}.",
            parent_id=parent.rollout.id,
        )
        self.start_agent(child)
        return child.rollout.id

    async def cancel_agent(self, agent_id: str) -> bool:
        """Cancel an active agent and all of its descendants."""
        agent = self.active_agents.get(agent_id)
        if not agent:
            return False
        descendants = [
            active.rollout.id for active in self.active_agents.values()
            if active.rollout.parent == agent_id
        ]
        await asyncio.gather(*(self.cancel_agent(child) for child in descendants))
        task = self.agent_tasks.get(agent_id)
        if task and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        if self.active_agents.get(agent_id) is agent:
            await agent.save_rollout()
            del self.active_agents[agent_id]
            self.agent_tasks.pop(agent_id, None)
            agent.pipeline = None
            parent = self.active_agents.get(agent.rollout.parent)
            if parent:
                await parent.receive_message(
                    f"Subagent {agent.config.subagent_name} ({agent_id}) failed: cancelled."
                )
        return True

    async def watch_agent(self, agent: Agent) -> PipelineResult:
        """Run and resume an agent until it has no active children."""
        answer = None
        failure: BaseException | None = None
        agent_task = outbox_task = None
        try:
            while True:
                agent_task = asyncio.create_task(agent.run())
                outbox_task = asyncio.create_task(agent.outbox.get())
                while not agent_task.done():
                    done, _ = await asyncio.wait(
                        {agent_task, outbox_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if outbox_task in done:
                        try:
                            await self.transfer_message(agent, outbox_task.result())
                        finally:
                            agent.outbox.task_done()
                        outbox_task = asyncio.create_task(agent.outbox.get())
                outbox_task.cancel()
                await asyncio.gather(outbox_task, return_exceptions=True)
                answer = agent_task.result()
                if agent.inbox.empty() and not any(
                    active.rollout.parent == agent.rollout.id
                    for active in self.active_agents.values()
                ):
                    break
                if agent.inbox.empty():
                    await agent.inbox_ready.wait()
        except asyncio.CancelledError:
            failure = asyncio.CancelledError()
        except BaseException as exc:
            failure = exc
        finally:
            for task in (agent_task, outbox_task):
                if task and not task.done():
                    task.cancel()
            await asyncio.gather(
                *(task for task in (agent_task, outbox_task) if task),
                return_exceptions=True,
            )
            await agent.save_rollout()
            if self.active_agents.get(agent.rollout.id) is agent:
                del self.active_agents[agent.rollout.id]
            if self.agent_tasks.get(agent.rollout.id) is asyncio.current_task():
                del self.agent_tasks[agent.rollout.id]
            if getattr(agent, "pipeline", None) is self:
                agent.pipeline = None
        parent = self.active_agents.get(agent.rollout.parent) if agent.rollout.parent else None
        if parent:
            error = "cancelled" if isinstance(failure, asyncio.CancelledError) else str(failure)
            status = f"failed: {error}" if failure else "completed"
            await parent.receive_message(
                f"Subagent {agent.config.subagent_name} ({agent.rollout.id}) {status}.\n"
                f"Final answer:\n{answer}"
            )
        if failure and not agent.rollout.parent:
            raise failure
        return PipelineResult(answer, agent.rollout.id, agent.workspace)

    @abstractmethod
    async def run(self, session: Session) -> Any:
        """
        Execute the pipeline with the given session state.
        
        Args:
            session (Session): The global session holding configs and rollouts.
            
        Returns:
            Any: The result or status of the pipeline run.
        """
        pass
