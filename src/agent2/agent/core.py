import tomllib
from __future__ import annotations
from pathlib import Path
from collections import OrderedDict
from datetime import datetime
from typing import Any, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


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


class Constructor(ABC):
    """Classes which wrap functions that run before the agent loop begins, to setup the agent."""
    @abstractmethod
    def setup(self, agent: Agent) -> None:
        """
        Execute setup logic before the agent loop.
        
        Args:
            agent (Agent): The agent instance to be set up.
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
    @abstractmethod
    def run(self, session: Session) -> Any:
        """
        Execute the pipeline with the given session state.
        
        Args:
            session (Session): The global session holding configs and rollouts.
            
        Returns:
            Any: The result or status of the pipeline run.
        """
        pass
    

class Agent:
    """
    Represents an active agent in the system.
    Each agent holds its own configuration, task, and a Rollout to track history.
    """
    def __init__(self, config: AgentConfig, unique_id: str, parent_id: Optional[str] = None) -> None:
        """
        Initializes an Agent with a configuration and a unique rollout context.
        
        Args:
            config (AgentConfig): The configuration defining the agent's behavior.
            unique_id (str): A unique identifier for the agent's task execution.
            parent_id (Optional[str], optional): The ID of the parent agent, if any. Defaults to None.
        """
        self.config = config
        self.rollout: Rollout = Rollout(
            config_path=config.path,
            id=unique_id,
            date_deployed=datetime.now().isoformat(),
            parent=parent_id
        )


class Session:
    """
    Represents the global session state, including loaded configurations and active rollouts.
    Acts as the main registry and entrypoint before pipelines are executed.
    """
    def __init__(self, config_dir: str = "config/agents", rollout_dir: str = ".agent2/task") -> None:
        """
        Initializes the Session by loading AgentConfigs from TOML files and existing Rollouts from JSON files.
        
        Args:
            config_dir (str, optional): The directory containing agent TOML configs. Defaults to "config/agents".
            rollout_dir (str, optional): The directory containing JSON task rollouts. Defaults to ".agent2/task".
        """
        self.configs: OrderedDict[str, AgentConfig] = OrderedDict()
        self.datastore: OrderedDict[str, Rollout] = OrderedDict()
        
        config_path = Path(config_dir)
        rollout_path = Path(rollout_dir)
        assert config_path.exists() and config_path.is_dir(), f"Config directory {config_path} does not exist or is not a directory" 
        assert rollout_path.exists() and rollout_path.is_dir(), f"Rollout directory {rollout_path} does not exist or is not a directory" 

        for file_path in config_path.glob("*.toml"):
            with open(file_path, "rb") as f:
                data = tomllib.load(f)
                config = AgentConfig.model_validate(data)
                self.configs[config.id] = config
            
        for file_path in rollout_path.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                store = Rollout.model_validate(data)
                self.datastore[store.agent_id] = store