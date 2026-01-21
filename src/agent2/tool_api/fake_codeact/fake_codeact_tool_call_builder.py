from typing import List, Dict
import json
from agent2.tool_api.abc.tool_call_builder import ToolCallBuilder

class FakeCodeActToolCallBuilder(ToolCallBuilder):
    """
    Builds a tool call string for the Fake CodeAct format.
    """
    def __init__(self, tool_start: str = "<code>", tool_end: str = "</code>"):
        self.tool_start = tool_start
        self.tool_end = tool_end
    
    def build(self, tool_call_json: List[Dict]) -> str:
        """
        Builds a tool call string from a tool call list.
        
        Args:
            tool_call_json (List[Dict]): The tool call list.
            
        Returns:
            str: The tool call string.
        """
        if not tool_call_json:
            return ""
            
        lines = [self.tool_start]
        
        for tool_call in tool_call_json:
            # Assume OpenAI format (function.name)
            name = tool_call["function"]["name"]
            args_str = tool_call["function"]["arguments"]
            if isinstance(args_str, str):
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
            else:
                args = args_str
                
            # Format arguments as python kwargs
            arg_parts = []
            for k, v in args.items():
                # specific handling for strings to ensure quotes
                if isinstance(v, str):
                    # Use repr to handle escaping quotes correctly
                    arg_parts.append(f"{k}={repr(v)}")
                else:
                    arg_parts.append(f"{k}={v}")
            
            call_str = f"{name}({', '.join(arg_parts)})"
            lines.append(call_str)
            
        lines.append(self.tool_end)
        
        return "\n".join(lines)
