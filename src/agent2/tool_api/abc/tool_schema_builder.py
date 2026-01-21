from abc import ABC, abstractmethod
from typing import List, Dict

class ToolSchemaBuilder(ABC):
    """The ToolSchemaBuilder builds tool schema strings from tool schema jsons."""
    
    @abstractmethod
    def build(self, tool_schema_json: List[Dict]) -> List[str]:
        """Builds a tool schema string from a tool schema list.
        
        Args:
            tool_schema_json (List[Dict]): The tool schema list to build the tool schema string from.
            
        Returns:
            List[str]: The list of tool schema strings.
        """
        pass
    