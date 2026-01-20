import json
from typing import List, Dict
from agent2.tool_api.abc.tool_call_builder import ToolCallBuilder

class JSONToolCallBuilder(ToolCallBuilder):
    """
    Builds JSON strings for tool calls.
    """
    def __init__(self, indent: int = 4, tool_start: str = "```json", tool_end: str = "```"):
        self.indent = indent
        self.tool_start = tool_start
        self.tool_end = tool_end

    def build(self, tool_call_json: List[Dict]) -> str:
        """
        Builds a JSON string from a list of tool calls.
        
        Args:
            tool_call_json (List[Dict]): List of tool calls.
            
        Returns:
            str: The JSON formatted tool call string.
        """
        simplified_calls = []
        for call in tool_call_json:
            func = call["function"]
            name = func["name"]
            arguments = json.loads(func["arguments"])
                
            simplified_calls.append({
                "name": name,
                "arguments": arguments
            })
            
        json_str = json.dumps(simplified_calls, indent=self.indent)
        return f"{self.tool_start}\n{json_str}\n{self.tool_end}"
