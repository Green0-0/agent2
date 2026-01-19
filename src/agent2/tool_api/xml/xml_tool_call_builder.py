import json
from typing import List, Dict
from agent2.tool_api.abc.tool_call_builder import ToolCallBuilder

class XMLToolCallBuilder(ToolCallBuilder):
    """
    Builds XML strings for tool calls.
    """
    def __init__(self, tool_start: str = "<tool_call>", tool_end: str = "</tool_call>"):
        self.tool_start = tool_start
        self.tool_end = tool_end

    def build(self, tool_call_json: List[Dict]) -> str:
        """
        Builds an XML string from a list of tool calls.
        
        Args:
            tool_call_json (List[Dict]): List of tool calls, each with 'name' and 'arguments'.
            
        Returns:
            str: The XML formatted tool call string.
        """
        xml_calls = []
        for call in tool_call_json:
            func = call["function"]
            name = func["name"]
            arguments = json.loads(func["arguments"])
            
            xml_lines = [f"<name>{name}</name>"]
            
            for arg_name, arg_value in arguments.items():
                xml_lines.append(f"<{arg_name}>{str(arg_value)}</{arg_name}>")
            
            xml_call = f"{self.tool_start}\n" + "\n".join(xml_lines) + f"\n{self.tool_end}"
            xml_calls.append(xml_call)
            
        return "\n".join(xml_calls)
