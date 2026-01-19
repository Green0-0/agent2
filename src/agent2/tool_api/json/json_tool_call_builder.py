import json
from typing import List, Dict
from agent2.tool_api.abc.tool_call_builder import ToolCallBuilder

class JSONToolCallBuilder(ToolCallBuilder):
    """
    Builds JSON strings for tool calls.
    """
    def __init__(self, indent: int = 4):
        self.indent = indent

    def build(self, tool_call_json: List[Dict]) -> str:
        """
        Builds a JSON string from a list of tool calls.
        
        Args:
            tool_call_json (List[Dict]): List of tool calls.
            
        Returns:
            str: The JSON formatted tool call string.
        """
        return json.dumps(tool_call_json, indent=self.indent)
