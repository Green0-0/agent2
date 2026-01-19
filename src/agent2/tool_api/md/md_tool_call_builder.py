import json
from typing import List, Dict
from agent2.tool_api.abc.tool_call_builder import ToolCallBuilder

class MDToolCallBuilder(ToolCallBuilder):
    """
    Builds Markdown strings for tool calls.
    """
    def __init__(self, tool_start: str = "# Tool Use", tool_end: str = "# Tool End"):
        self.tool_start = tool_start
        self.tool_end = tool_end

    def build(self, tool_call_json: List[Dict]) -> str:
        """
        Builds a Markdown string from a list of tool calls.
        
        Args:
            tool_call_json (List[Dict]): List of tool calls.
            
        Returns:
            str: The Markdown formatted tool call string.
        """
        md_calls = []
        for call in tool_call_json:
            func = call["function"]
            name = func["name"]
            arguments = json.loads(func["arguments"])
            
            lines = [f"## Name: {name}"]
            
            for arg_name, arg_value in arguments.items():
                str_value = str(arg_value)
                parts = str_value.split('\n')
                
                # First part after colon, remaining parts as separate lines
                if len(parts) > 0:
                    lines.append(f"### {arg_name}: {parts[0]}")
                    for part in parts[1:]:
                        lines.append(part)
                else:
                    lines.append(f"### {arg_name}:")

            md_call = f"{self.tool_start}\n" + "\n".join(lines) + f"\n{self.tool_end}"
            md_calls.append(md_call)
            
        return "\n".join(md_calls)
