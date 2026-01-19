from abc import ABC, abstractmethod
from typing import List, Dict

class ToolCallBuilder(ABC):
    """The ToolCallBuilder builds tool call strings from tool call jsons."""
    
    @abstractmethod
    def build(self, tool_call_json: List[Dict]) -> str:
        """Builds a tool call string from a tool call list.
        
        Args:
            tool_call_json (List[Dict]): The tool call list to build the tool call string from.
            
        Returns:
            str: The tool call string.
        """
        pass
    