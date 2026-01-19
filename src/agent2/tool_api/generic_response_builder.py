from typing import List, Dict
from agent2.tool_api.abc.tool_response_builder import ToolResponseBuilder

class GenericResponseBuilder(ToolResponseBuilder):
    """
    Builds a generic response for tool calls.
    """
    def build(self, tool_response_json: List[Dict]) -> str:
        """
        Builds a tool response string from a tool response list.
        
        Args:
            tool_response_json (List[Dict]): List of tool execution results. 
            
        Returns:
            str: A string representing the list of tool response messages.
        """
        responses = []
        for resp in tool_response_json:
            responses.append(resp["content"])
            
        # Return as a JSON list
        return "\n".join(responses)
