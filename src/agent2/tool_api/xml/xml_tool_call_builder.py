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
            name = call.get("name", "")
            arguments = call.get("arguments", {})
            
            xml_lines = [f"<name>{name}</name>"]
            
            for arg_name, arg_value in arguments.items():
                str_value = str(arg_value)
                # Escape XML entities
                str_value = (str_value.replace("&", "&amp;")
                                    .replace("<", "&lt;")
                                    .replace(">", "&gt;")
                                    .replace("\"", "&quot;")
                                    .replace("'", "&apos;"))
                xml_lines.append(f"<{arg_name}>{str_value}</{arg_name}>")
            
            xml_call = f"{self.tool_start}\n" + "\n".join(xml_lines) + f"\n{self.tool_end}"
            xml_calls.append(xml_call)
            
        return "\n".join(xml_calls)
