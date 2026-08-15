from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

class Rollout(BaseModel):
    agent_id: str
    unique_id: str
    date_deployed: str
    parent: Optional[str] = None
    children: list[str] = Field(default_factory=list)
    raw_chat: list[Any] = Field(default_factory=list)
    action_history: list[Any] = Field(default_factory=list)

class AgentConfig(BaseModel):
    id: str
    subagent_description: str
    system_prompt: str
    header: str
    speculative_viewing_prompt: str
    prompt_wrapper: str
    
class Agent:
    def __init__(self, config: AgentConfig, unique_id: str, parent_id: Optional[str] = None) -> None:
        self.config = config
        self.rollout: Rollout = Rollout(
            agent_id=config.id,
            unique_id=unique_id,
            date_deployed=datetime.now().isoformat(),
            parent=parent_id
        )