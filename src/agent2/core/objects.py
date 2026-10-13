from __future__ import annotations
from typing import Any, Optional, TYPE_CHECKING
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from dataclasses import dataclass

if TYPE_CHECKING:
    from agent2.core.agent import Agent
    from agent2.core.session import Session

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
    system_prompt: str
    header: str
    speculative_viewing_prompt: str
    prompt_wrapper: str
    model: str
    api_base_url: Optional[str] = None
    api_key_env_var: Optional[str] = None


@dataclass
class Message:
    """Represents a message sent between agents or from the pipeline."""
    target_id: str
    content: Any


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
    Each optionally returns a string which is appended to the tool response or user message."""
    @abstractmethod
    def run(self, agent: Agent, response: Any) -> Optional[str]:
        """
        Execute the hook logic.
        
        Args:
            agent (Agent): The active agent running the hook.
            response (Any): The parsed LLM response triggering the hook.
            
        Returns:
            Optional[str]: An optional string to append to the tool response or user message.
        """
        pass


class Pipeline(ABC):
    """Abstract pipeline that gets implemented for specific pipeline types."""
    def __init__(self) -> None:
        self.active_agents: dict[str, Agent] = {}

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
