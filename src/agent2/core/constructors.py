import platform
from datetime import datetime
from agent2.core.objects import Constructor
from agent2.core.agent import Agent

class DefaultConstructor(Constructor):
    """
    Initializes the agent's chat history.
    Sets up the system prompt and adds the first user message.
    """
    def setup(self, agent: Agent, prompt: str, full: bool = False) -> None:
        agent.rollout.raw_chat.append({
            "role": "system",
            "content": agent.config.system_prompt
        })
        agent.rollout.raw_chat.append({
            "role": "user",
            "content": prompt
        })

    def followup(self, agent: Agent, prompt: str, full: bool = False) -> None:
        agent.rollout.raw_chat.append({
            "role": "user",
            "content": prompt
        })


class DateConstructor(Constructor):
    """Provides the current date to the agent chat."""
    def __init__(self, key: str, format_lite: str = "{}", format_full: str = "The current date is {}."):
        self.key = key
        self.format_lite = format_lite
        self.format_full = format_full

    def setup(self, agent: Agent, prompt: str, full: bool = False) -> None:
        value = datetime.now().isoformat()
        
        if full:
            formatted_value = self.format_full.format(value)
            target_token = f"{{{{{self.key}*}}}}"
        else:
            formatted_value = self.format_lite.format(value)
            target_token = f"{{{{{self.key}}}}}"
            
        for msg in agent.rollout.raw_chat:
            if isinstance(msg.get("content"), str):
                msg["content"] = msg["content"].replace(target_token, formatted_value)

    def followup(self, agent: Agent, prompt: str, full: bool = False) -> None:
        value = datetime.now().isoformat()
        
        if full:
            formatted_value = self.format_full.format(value)
            target_token = f"{{{{{self.key}*}}}}"
        else:
            formatted_value = self.format_lite.format(value)
            target_token = f"{{{{{self.key}}}}}"
            
        if agent.rollout.raw_chat and agent.rollout.raw_chat[-1].get("role") == "user":
            msg = agent.rollout.raw_chat[-1]
            if isinstance(msg.get("content"), str):
                msg["content"] = msg["content"].replace(target_token, formatted_value)


class DirectoryConstructor(Constructor):
    """Provides the working directory structure to the agent chat."""
    def __init__(self, key: str, format_lite: str = "{}", format_full: str = "The directory structure is:\n{}", dir_format: str = "full"):
        self.key = key
        self.format_lite = format_lite
        self.format_full = format_full
        self.dir_format = dir_format

    def setup(self, agent: Agent, prompt: str, full: bool = False) -> None:
        files = sorted(agent.workspace.paths())
        value = "\n".join(files)
        
        if full:
            formatted_value = self.format_full.format(value)
            target_token = f"{{{{{self.key}*}}}}"
        else:
            formatted_value = self.format_lite.format(value)
            target_token = f"{{{{{self.key}}}}}"
        
        for msg in agent.rollout.raw_chat:
            if isinstance(msg.get("content"), str):
                msg["content"] = msg["content"].replace(target_token, formatted_value)

    def followup(self, agent: Agent, prompt: str, full: bool = False) -> None:
        files = sorted(agent.workspace.paths())
        value = "\n".join(files)
        
        if full:
            formatted_value = self.format_full.format(value)
            target_token = f"{{{{{self.key}*}}}}"
        else:
            formatted_value = self.format_lite.format(value)
            target_token = f"{{{{{self.key}}}}}"
        
        if agent.rollout.raw_chat and agent.rollout.raw_chat[-1].get("role") == "user":
            msg = agent.rollout.raw_chat[-1]
            if isinstance(msg.get("content"), str):
                msg["content"] = msg["content"].replace(target_token, formatted_value)


class OSInfoConstructor(Constructor):
    """Provides operating system information to the agent chat."""
    def __init__(self, key: str, format_lite: str = "{}", format_full: str = "The operating system is {}."):
        self.key = key
        self.format_lite = format_lite
        self.format_full = format_full

    def setup(self, agent: Agent, prompt: str, full: bool = False) -> None:
        value = f"{platform.system()} {platform.release()}"
        
        if full:
            formatted_value = self.format_full.format(value)
            target_token = f"{{{{{self.key}*}}}}"
        else:
            formatted_value = self.format_lite.format(value)
            target_token = f"{{{{{self.key}}}}}"
        
        for msg in agent.rollout.raw_chat:
            if isinstance(msg.get("content"), str):
                msg["content"] = msg["content"].replace(target_token, formatted_value)

    def followup(self, agent: Agent, prompt: str, full: bool = False) -> None:
        value = f"{platform.system()} {platform.release()}"
        
        if full:
            formatted_value = self.format_full.format(value)
            target_token = f"{{{{{self.key}*}}}}"
        else:
            formatted_value = self.format_lite.format(value)
            target_token = f"{{{{{self.key}}}}}"
        
        if agent.rollout.raw_chat and agent.rollout.raw_chat[-1].get("role") == "user":
            msg = agent.rollout.raw_chat[-1]
            if isinstance(msg.get("content"), str):
                msg["content"] = msg["content"].replace(target_token, formatted_value)
