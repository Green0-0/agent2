from __future__ import annotations
import asyncio
from typing import Any, Callable, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod
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

    def register_agents(self, agents: list[Agent]) -> None:
        """Register agents as members of this pipeline's messaging boundary."""
        additions = {}
        for agent in agents:
            owner = getattr(agent, "pipeline", None)
            if owner is not None and owner is not self:
                raise ValueError(f"Agent {agent.rollout.id!r} already belongs to another pipeline")
            current = self.active_agents.get(agent.rollout.id)
            if current is not None and current is not agent:
                raise ValueError(f"Active agent {agent.rollout.id!r} is already registered")
            current = additions.get(agent.rollout.id)
            if current is not None and current is not agent:
                raise ValueError(f"Duplicate active agent id {agent.rollout.id!r}")
            additions[agent.rollout.id] = agent
        self.active_agents.update(additions)
        for agent in agents:
            agent.pipeline = self

    async def transfer_message(self, sender: Agent, message: Message) -> None:
        """Transfer a message only when sender and target belong to this pipeline."""
        if self.active_agents.get(sender.rollout.id) is not sender:
            raise KeyError(f"Sender {sender.rollout.id!r} is not active in this pipeline")
        if message.target_id == sender.rollout.id:
            raise ValueError("Agents cannot message themselves")
        target = self.active_agents.get(message.target_id)
        if target is None:
            raise KeyError(f"Active agent {message.target_id!r} was not found in this pipeline")
        await target.receive_message(message.content)

    async def watch_agent(self, agent: Agent) -> PipelineResult:
        """Run one registered agent while routing its outgoing messages."""
        if self.active_agents.get(agent.rollout.id) is not agent:
            raise KeyError(f"Agent {agent.rollout.id!r} is not active in this pipeline")
        agent_task = asyncio.create_task(agent.run())
        outbox_task = asyncio.create_task(agent.outbox.get())
        try:
            while True:
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
                if agent_task in done:
                    outbox_task.cancel()
                    await asyncio.gather(outbox_task, return_exceptions=True)
                    return PipelineResult(agent_task.result(), agent.rollout.id, agent.workspace)
        finally:
            for task in (agent_task, outbox_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(agent_task, outbox_task, return_exceptions=True)
            await agent.save_rollout()
            if self.active_agents.get(agent.rollout.id) is agent:
                del self.active_agents[agent.rollout.id]
            if getattr(agent, "pipeline", None) is self:
                agent.pipeline = None

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
