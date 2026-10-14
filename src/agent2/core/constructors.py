from __future__ import annotations

import platform
from datetime import datetime
from typing import TYPE_CHECKING

from agent2.core.objects import Constructor

if TYPE_CHECKING:
    from agent2.core.agent import Agent


class DefaultConstructor(Constructor):
    """Initialize the agent's chat history."""

    def __init__(self, key: str = "PROMPT"):
        self.key = key

    def setup(self, agent: Agent, prompt: str) -> None:
        content = ((agent.config.prompt_wrap_top or "") + agent.config.prompt_wrap_bottom).replace(
            f"{{{{{self.key}}}}}", prompt
        )
        agent.rollout.raw_chat.extend([
            {"role": "system", "content": agent.config.system_prompt},
            {"role": "user", "content": content},
        ])

    def followup(self, agent: Agent, prompt: str) -> None:
        agent.rollout.raw_chat.append({
            "role": "user",
            "content": agent.config.followup_prompt_wrapper.replace(f"{{{{{self.key}}}}}", prompt),
        })


class _ProviderConstructor(Constructor):
    def __init__(self, key: str, format_lite: str, format_full: str):
        self.key = key
        self.format_lite = format_lite
        self.format_full = format_full

    def value(self, agent: Agent) -> str:
        raise NotImplementedError

    def _apply(self, agent: Agent, messages: list[dict]) -> None:
        value = self.value(agent)
        for message in messages:
            content = message.get("content")
            if isinstance(content, str):
                message["content"] = content.replace(
                    f"{{{{{self.key}}}}}", self.format_lite.format(value)
                ).replace(
                    f"{{{{{self.key}*}}}}", self.format_full.format(value)
                )

    def setup(self, agent: Agent, prompt: str) -> None:
        self._apply(agent, agent.rollout.raw_chat)

    def followup(self, agent: Agent, prompt: str) -> None:
        messages = agent.rollout.raw_chat
        if messages and messages[-1].get("role") == "user":
            self._apply(agent, messages[-1:])


class DateConstructor(_ProviderConstructor):
    """Provide the current date to the agent chat."""

    def __init__(self, key: str, format_lite: str = "{}", format_full: str = "The current date is {}."):
        super().__init__(key, format_lite, format_full)

    def value(self, agent: Agent) -> str:
        return datetime.now().isoformat()


class DirectoryConstructor(_ProviderConstructor):
    """Provide the working directory structure to the agent chat."""

    def __init__(self, key: str, format_lite: str = "{}", format_full: str = "The directory structure is:\n{}", dir_format: str = "full"):
        super().__init__(key, format_lite, format_full)
        self.dir_format = dir_format

    def value(self, agent: Agent) -> str:
        return "\n".join(sorted(agent.workspace.paths()))


class OSInfoConstructor(_ProviderConstructor):
    """Provide operating-system information to the agent chat."""

    def __init__(self, key: str, format_lite: str = "{}", format_full: str = "The operating system is {}."):
        super().__init__(key, format_lite, format_full)

    def value(self, agent: Agent) -> str:
        return f"{platform.system()} {platform.release()}"
