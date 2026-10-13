from __future__ import annotations
import asyncio
import inspect
import os
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING
from openai import AsyncOpenAI

from agent2.core.objects import AgentConfig, Rollout, Message, Constructor, Hook, PendingContinuation
from agent2.core.tools.tool import Tool

if TYPE_CHECKING:
    from agent2.core.session import Session
    from agent2.core.workspace import Workspace

_STOP = object()


class Agent:
    """
    Represents an active agent in the system.
    Each agent holds its own configuration, task, and a Rollout to track history.
    """
    def __init__(self, session: Session, workspace: Workspace, config: AgentConfig, unique_id: str, prompt: str, constructors: list[Constructor], hooks: list[Hook], tools: dict[str, Tool], parent_id: Optional[str] = None, client: Any = None) -> None:
        """
        Initializes an Agent with a configuration and a unique rollout context.
        
        Args:
            session (Session): The session this agent belongs to.
            config (AgentConfig): The configuration defining the agent's behavior.
            unique_id (str): A unique identifier for the agent's task execution.
            prompt (str): The initial user input or task description.
            constructors (list[Constructor]): The constructors to setup the agent.
            hooks (list[Hook]): The hooks to run after LLM execution.
            tools (dict[str, Tool]): A dictionary of instantiated Tools available to the agent.
            parent_id (Optional[str], optional): The ID of the parent agent, if any. Defaults to None.
        """
        self.session = session
        self.workspace = workspace
        self.config = config
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.outbox: asyncio.Queue = asyncio.Queue()
        self.rollout: Rollout = Rollout(
            config_path=config.path,
            id=unique_id,
            date_deployed=datetime.now().isoformat(),
            parent=parent_id
        )
        
        api_key = os.environ.get(self.config.api_key_env_var) if self.config.api_key_env_var else None
        self.client = client or AsyncOpenAI(api_key=api_key, base_url=self.config.api_base_url)
        
        self.constructors = constructors
        self.hooks = hooks
        self.tools = tools
        self.pending_continuation: PendingContinuation | None = None

        self.session.register_rollout(self.rollout)
        
        for constructor in self.constructors:
            constructor.setup(self, prompt)

    async def receive_message(self, message: str) -> None:
        """Puts a message into the agent's inbox."""
        if not isinstance(message, str):
            raise TypeError("Agent messages must be strings")
        await self.inbox.put(message)

    async def stop(self) -> None:
        """Stop the agent through its private control channel."""
        await self.inbox.put(_STOP)

    def followup(self, prompt: str) -> None:
        """
        Processes a followup message by routing it through all constructors.
        """
        for constructor in self.constructors:
            constructor.followup(self, prompt)

    async def send_message(self, target_id: str, content: str) -> None:
        """Emits a message to the pipeline for routing."""
        if target_id == self.rollout.id:
            raise ValueError("Agents cannot message themselves")
        if not isinstance(content, str):
            raise TypeError("Agent messages must be strings")
        await self.outbox.put(Message(target_id=target_id, content=content))

    async def save_rollout(self) -> None:
        """Persist the rollout through its owning session."""
        self.session.save_rollout(self.rollout)

    async def _run_llm_step(self):
        """Executes a single step of the LLM generation using raw_chat."""
        tools_schema = [tool.openai_schema for tool in self.tools.values()] if self.tools else None
        
        kwargs = {
            "model": self.config.model,
            "messages": self.rollout.raw_chat
        }
        if tools_schema:
            kwargs["tools"] = tools_schema
            
        response = await self.client.chat.completions.create(**kwargs)
        return response

    async def run(self, max_steps: int = 100) -> Any:
        """
        The main loop for the agent.
        It processes incoming messages, then performs an LLM step.
        """
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")

        for _ in range(max_steps):
            inbox = []
            while not self.inbox.empty():
                msg = self.inbox.get_nowait()
                self.inbox.task_done()
                if msg is _STOP:
                    await self.save_rollout()
                    return None
                inbox.append(msg)
            if self.pending_continuation:
                for msg in inbox:
                    self.inbox.put_nowait(msg)
            elif inbox:
                content = "\n\n".join(inbox)
                if self.rollout.raw_chat and self.rollout.raw_chat[-1].get("role") == "user":
                    self.rollout.raw_chat[-1]["content"] += f"\n\n{content}"
                else:
                    self.rollout.raw_chat.append({"role": "user", "content": content})
                
            # 2. Run the LLM step (do not interrupt as it wastes tokens)
            response = await self._run_llm_step()
            
            # Append assistant message to raw_chat
            self.rollout.raw_chat.append(response.choices[0].message.model_dump(exclude_unset=True))
            
            # Run hooks and collect stacked returns
            stacked_outputs = []
            consumed = False
            for hook in self.hooks:
                result = hook.run(self, response)
                if inspect.isawaitable(result):
                    result = await result
                if result:
                    consumed |= result.consumed
                    if result.output:
                        stacked_outputs.append(result.output)
                    
            if stacked_outputs:
                stacked_str = "\n".join(stacked_outputs)
                if self.rollout.raw_chat and self.rollout.raw_chat[-1].get("role") in ["tool", "user"]:
                    msg = self.rollout.raw_chat[-1]
                    if isinstance(msg.get("content"), str):
                        msg["content"] += f"\n\n{stacked_str}"
                else:
                    self.rollout.raw_chat.append({
                        "role": "user",
                        "content": stacked_str
                    })
            
            await self.save_rollout()

            if consumed:
                continue
            message = response.choices[0].message
            if getattr(message, "tool_calls", None):
                raise RuntimeError("Assistant tool calls were not consumed by a hook")
            return getattr(message, "content", None)

        raise RuntimeError(f"Agent {self.rollout.id!r} exceeded {max_steps} LLM steps")
