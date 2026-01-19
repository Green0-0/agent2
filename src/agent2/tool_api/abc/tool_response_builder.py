from abc import ABC, abstractmethod
from typing import List, Dict

class ToolResponseBuilder(ABC):
    """The ToolResponseBuilder builds tool response strings from tool response jsons."""
    
    @abstractmethod
    def build(self, tool_response_json: List[Dict]) -> str:
        """Builds a tool response string from a tool response list.
        
        Args:
            tool_response_json (List[Dict]): The tool response list to build the tool response string from.
            
        Returns:
            str: The tool response string.
        """
        pass