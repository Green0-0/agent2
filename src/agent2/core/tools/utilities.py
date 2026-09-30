from __future__ import annotations
from agent2.core.session import Session
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agent2.core.agent import Agent


def delegate(session: Session, agent: Agent, subagent_id: str, instructions: str, folder_path: Optional[str] = None):
    ...
    
def message_subagent(session: Session, agent: Agent, subagent_id: Optional[str] = None):
    ...
    
def cancel_subagent(session: Session, agent: Agent, subagent_id: str):
    ...
    
def tools(session: Session, agent: Agent, filter_regex: Optional[str] = None):
    ...
    
def bash(session: Session, agent: Agent):
    # TODO
    ...
