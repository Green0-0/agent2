from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from agent2.core.agent import Agent
from agent2.core.constructors import DefaultConstructor
from agent2.core.hooks import ToolCallHook
from agent2.core.objects import Constructor, Hook, Pipeline
from agent2.core.session import Session
from agent2.core.tools.tool import Tool
from agent2.core.workspace import Workspace


class SingleAgentPipeline(Pipeline):
    """Create and run one agent to completion."""

    def __init__(
        self,
        config_path: str,
        prompt: str,
        *,
        rollout_id: str | None = None,
        parent_id: str | None = None,
        constructors: list[Constructor] | None = None,
        hooks: list[Hook] | None = None,
        tools: dict[str, Tool] | None = None,
        workspace: Workspace | None = None,
        client: Any = None,
        max_steps: int = 100,
    ) -> None:
        super().__init__()
        self.config_path = config_path
        self.prompt = prompt
        self.rollout_id = rollout_id or uuid4().hex
        self.parent_id = parent_id
        self.constructors = constructors if constructors is not None else [DefaultConstructor()]
        self.hooks = hooks if hooks is not None else [ToolCallHook()]
        self.tools = tools or {}
        self.workspace = workspace
        self.client = client
        self.max_steps = max_steps

    async def run(self, session: Session) -> Any:
        config = session.get_config(self.config_path)
        agent = Agent(
            session=session,
            workspace=self.workspace or Workspace(session),
            config=config,
            unique_id=self.rollout_id,
            prompt=self.prompt,
            constructors=self.constructors,
            hooks=self.hooks,
            tools=self.tools,
            parent_id=self.parent_id,
            client=self.client,
        )
        self.active_agents[agent.rollout.id] = agent
        try:
            agent_task = asyncio.create_task(agent.run(max_steps=self.max_steps))
            outbox_task = asyncio.create_task(agent.outbox.get())
            while True:
                done, _ = await asyncio.wait(
                    {agent_task, outbox_task},
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if outbox_task in done:
                    message = outbox_task.result()
                    target = self.active_agents.get(message.target_id)
                    if target is None:
                        agent_task.cancel()
                        await asyncio.gather(agent_task, return_exceptions=True)
                        raise KeyError(f"Active agent {message.target_id!r} was not found")
                    await target.receive_message(message.content)
                    outbox_task = asyncio.create_task(agent.outbox.get())
                if agent_task in done:
                    outbox_task.cancel()
                    await asyncio.gather(outbox_task, return_exceptions=True)
                    return agent_task.result()
        finally:
            for task in (agent_task, outbox_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(agent_task, outbox_task, return_exceptions=True)
            await agent.save_rollout()
            self.active_agents.pop(agent.rollout.id, None)
