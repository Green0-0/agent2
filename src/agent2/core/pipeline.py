from __future__ import annotations

import asyncio

from agent2.core.agent import Agent
from agent2.core.objects import Pipeline, PipelineResult
from agent2.core.session import Session
from agent2.core.workspace import Workspace


class SingleAgentPipeline(Pipeline):
    """Create and run one agent to completion."""

    def __init__(
        self,
        config_path: str,
        prompt: str,
    ) -> None:
        super().__init__()
        self.config_path = config_path
        self.prompt = prompt

    def _create_agent(self, session: Session) -> Agent:
        return Agent(
            session=session,
            workspace=Workspace(session),
            config=session.get_config(self.config_path),
            prompt=self.prompt,
        )

    async def run(self, session: Session) -> PipelineResult:
        agent = self._create_agent(session)
        return await self.start_agent(agent)


class BasicMultiAgentPipeline(Pipeline):
    """Run five isolated candidates and let a sixth agent select a diff."""

    def __init__(
        self,
        config_path: str,
        prompt: str,
        *,
        judge_config_path: str = "config/agents/diff_judge.toml",
    ) -> None:
        super().__init__()
        self.config_path = config_path
        self.judge_config_path = judge_config_path
        self.prompt = prompt
        self.workspaces: list[Workspace] = []
        self.diffs: list[str] = []
        self.errors: list[str | None] = []

    async def run(self, session: Session) -> int:
        agents = [
            Agent(
                session,
                Workspace(session),
                session.get_config(self.config_path),
                self.prompt,
            )
            for _ in range(5)
        ]
        results = await asyncio.gather(
            *(self.start_agent(agent) for agent in agents),
            return_exceptions=True,
        )
        self.workspaces = [agent.workspace for agent in agents]
        self.diffs = [
            "\n".join(content for _, content in workspace.diff())
            for workspace in self.workspaces
        ]
        self.errors = [str(result) if isinstance(result, BaseException) else None for result in results]
        choices = "\n\n".join(
            f"CANDIDATE {number}\n"
            f"STATUS: {f'failed: {error}' if error else 'completed'}\n"
            f"{diff or '(no changes)'}"
            for number, (diff, error) in enumerate(zip(self.diffs, self.errors), 1)
        )
        judge = Agent(
            session,
            Workspace(session),
            session.get_config(self.judge_config_path),
            f"TASK\n{self.prompt}\n\n{choices}",
        )
        answer = str((await self.start_agent(judge)).answer).strip()
        if answer not in {"1", "2", "3", "4", "5"}:
            raise ValueError(f"Judge returned {answer!r}; expected one number from 1 to 5")
        return int(answer)
