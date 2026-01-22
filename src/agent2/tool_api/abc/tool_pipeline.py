import uuid
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from agent2.tool_api.abc.tool_call_extractor import ToolCallExtractor
from agent2.tool_api.abc.tool_call_builder import ToolCallBuilder
from agent2.tool_api.abc.tool_response_builder import ToolResponseBuilder
from agent2.tool_api.abc.tool_schema_builder import ToolSchemaBuilder

class ToolPipeline(ABC):
    """The ToolPipeline is a pipeline of tool call extractors, tool call builders, and tool schema builders."""
    
    def __init__(self, tool_call_extractor: ToolCallExtractor, tool_call_builder: ToolCallBuilder, tool_response_builder: ToolResponseBuilder, tool_schema_builder: ToolSchemaBuilder, schema_key: str = "{{llm_tools_list}}", replace_schema_all: bool = True):
        self.tool_call_extractor = tool_call_extractor
        self.tool_call_builder = tool_call_builder
        self.tool_response_builder = tool_response_builder
        self.tool_schema_builder = tool_schema_builder
        self.schema_key = schema_key
        self.replace_schema_all = replace_schema_all

    @abstractmethod
    def convert_openai(self, openai_json: List[Dict]) -> List[Dict]:
        """Converts an OpenAI chat with tools to another OpenAI chat with no tools.
        
        Args:
            openai_json (List[Dict]): The OpenAI chat with tool schemas/calls to convert.
            
        Returns:
            List[Dict]: The OpenAI chat with no tools. 
        """
        pass
    
    @abstractmethod
    def extract_response(self, response_str: str) -> Tuple[Dict, List]:
        """Parses a response string into an OpenAI message dict.

        Args:
            response_str (str): The response string to parse.
            
        Returns:
            Tuple[Dict, List]: The openai message dict and a list of errors.
        """
        pass

    def _get_schema_string(self, tools: List[Dict]) -> str:
        """
        Builds the tool schema string from the list of tools, wrapping each schema in the tool call builder's start/end tags.

        Args:
            tools (List[Dict]): The list of tool definitions in OpenAI format.

        Returns:
            str: The formatted schema string ready to be injected into the system prompt.
        """
        schema_list = self.tool_schema_builder.build(tools)
        
        wrapped_schema_list = []
        for schema in schema_list:
            start_tag = getattr(self.tool_call_builder, "tool_start", "")
            end_tag = getattr(self.tool_call_builder, "tool_end", "")
            wrapped_schema_list.append(f"{start_tag}\n{schema}\n{end_tag}")
        
        return "\n\n".join(wrapped_schema_list)

    def _to_openai_fc(self, content: str, tool_calls: List[Dict]) -> Dict:
        """
        Converts extracted content and tool calls into an OpenAI message format.

        Args:
            content (str): The text content extracted from the model's response.
            tool_calls (List[Dict]): The list of tool calls extracted from the model's response.

        Returns:
            Dict: An OpenAI-formatted assistant message containing the content and tool calls.
        """
        openai_tool_calls = []
        for tool_call in tool_calls:
            # Convert from internal format
            openai_tool_calls.append({
                "id": "call_" + str(uuid.uuid4())[:8],
                "type": "function",
                "function": {
                    "name": tool_call["name"],
                    "arguments": json.dumps(tool_call["arguments"])
                }
            })

        openai_message = {"role": "assistant", "content": content, "tool_calls": openai_tool_calls, "finish_reason": "stop" if openai_tool_calls == [] else "tool"}
        return openai_message