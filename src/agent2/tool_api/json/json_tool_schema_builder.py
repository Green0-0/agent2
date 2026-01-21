import json
from typing import List, Dict, Any
from agent2.tool_api.abc.tool_schema_builder import ToolSchemaBuilder

class JSONToolSchemaBuilder(ToolSchemaBuilder):
    """
    Builds JSON schema definitions for tools.
    """
    def __init__(self, indent: int = 4):
        self.indent = indent

    def build(self, tool_schema_json: List[Dict]) -> List[str]:
        """
        Builds a tool schema string from a list of tool schema dictionaries.
        
        Args:
            tool_schema_json (List[Dict]): List of tool definitions.
            
        Returns:
            List[str]: The list of JSON formatted schema strings.
        """
        return [json.dumps(tool, indent=self.indent) for tool in tool_schema_json]
