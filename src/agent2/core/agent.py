from __future__ import annotations
import asyncio
import inspect
import os
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4
from openai import AsyncOpenAI

from agent2.core.globals import CONSTRUCTORS, HOOKS, TOOLS
from agent2.core.objects import AgentConfig, Rollout, Message, PendingContinuation

if TYPE_CHECKING:
    from agent2.core.objects import Pipeline
    from agent2.core.session import Session
    from agent2.core.workspace import Workspace

_STOP = object()


class Agent:
    """
    Represents an active agent in the system.
    Each agent holds its own configuration, task, and a Rollout to track history.
    """
    def __init__(self, session: Session, workspace: Workspace, config: AgentConfig, prompt: str, unique_id: str | None = None, parent_id: Optional[str] = None, client: Any = None) -> None:
        """
        Initializes an Agent with a configuration and a unique rollout context.
        
        Args:
            session (Session): The session this agent belongs to.
            config (AgentConfig): The configuration defining the agent's behavior.
            prompt (str): The initial user input or task description.
            unique_id (str): Optional rollout ID. Generated when omitted.
            parent_id (Optional[str], optional): The ID of the parent agent, if any. Defaults to None.
        """
        self.session = session
        self.workspace = workspace
        self.pipeline: Pipeline | None = None
        self.config = config
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.inbox_ready = asyncio.Event()
        self.outbox: asyncio.Queue = asyncio.Queue()
        self.rollout: Rollout = Rollout(
            config_path=config.path,
            id=unique_id or uuid4().hex,
            date_deployed=datetime.now().isoformat(),
            parent=parent_id
        )
        
        api_key = os.environ.get(self.config.api_key_env_var) if self.config.api_key_env_var else None
        self.client = client or AsyncOpenAI(api_key=api_key, base_url=self.config.api_base_url)
        
        try:
            self.constructors = [CONSTRUCTORS[name]() for name in config.constructors]
            self.hooks = [HOOKS[name]() for name in config.hooks]
            self.primary_tools = {name: TOOLS[name] for name in config.primary_tools}
            self.secondary_tools = {name: TOOLS[name] for name in config.secondary_tools}
        except KeyError as exc:
            raise ValueError(f"Unknown configured agent component: {exc.args[0]}") from exc
        for toolset in (self.primary_tools, self.secondary_tools):
            if "delegate" in toolset:
                toolset["delegate"] = deepcopy(toolset["delegate"])
                field = toolset["delegate"].openai_schema["function"]["parameters"]["properties"]["subagent_name"]
                field["enum"] = config.subagent_names
                field["description"] += " Available: " + "; ".join(
                    f"{name} — {session.get_config_by_name(name).subagent_description}"
                    for name in config.subagent_names
                )
        self.tools = self.primary_tools.copy()
        self.pending_continuation: PendingContinuation | None = None

        self.session.register_rollout(self.rollout)
        
        for constructor in self.constructors:
            constructor.setup(self, prompt)

    async def receive_message(self, message: str) -> None:
        """Puts a message into the agent's inbox."""
        if not isinstance(message, str):
            raise TypeError("Agent messages must be strings")
        await self.inbox.put(message)
        self.inbox_ready.set()

    async def stop(self) -> None:
        """Stop the agent through its private control channel."""
        await self.inbox.put(_STOP)
        self.inbox_ready.set()

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

    async def run(self) -> Any:
        """
        The main loop for the agent.
        It processes incoming messages, then performs an LLM step.
        """
        for _ in range(self.config.max_steps):
            inbox = []
            while not self.inbox.empty():
                msg = self.inbox.get_nowait()
                self.inbox.task_done()
                if msg is _STOP:
                    await self.save_rollout()
                    return None
                inbox.append(msg)
            if self.inbox.empty():
                self.inbox_ready.clear()
            if self.pending_continuation:
                for msg in inbox:
                    self.inbox.put_nowait(msg)
                if inbox:
                    self.inbox_ready.set()
            elif inbox:
                content = "\n\n".join(inbox)
                if self.rollout.raw_chat and self.rollout.raw_chat[-1].get("role") == "user":
                    self.rollout.raw_chat[-1]["content"] += f"\n\n{content}"
                else:
                    self.followup(content)
                
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

        raise RuntimeError(f"Agent {self.rollout.id!r} exceeded {self.config.max_steps} LLM steps")
