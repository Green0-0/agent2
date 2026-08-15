
from typing import Optional


def delegate(subagent_id: str, instructions: str, folder_path: Optional[str] = None):
    ...
    
def message_subagent(subagent_id: Optional[str] = None):
    ...
    
def cancel_subagent(subagent_id: str):
    ...
    
def tools(filter_regex: Optional[str] = None):
    ...
    
def bash():
    # TODO
    ...