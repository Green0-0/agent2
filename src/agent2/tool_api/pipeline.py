import copy
import json
import uuid
from typing import List, Dict, Tuple
from agent2.tool_api.abc.tool_pipeline import ToolPipeline
from agent2.tool_api.abc.tool_call_extractor import ToolCallExtractor
from agent2.tool_api.abc.tool_call_builder import ToolCallBuilder
from agent2.tool_api.abc.tool_response_builder import ToolResponseBuilder
from agent2.tool_api.abc.tool_schema_builder import ToolSchemaBuilder

class StandardToolPipeline(ToolPipeline):
    def __init__(self, tool_call_extractor: ToolCallExtractor, tool_call_builder: ToolCallBuilder, tool_response_builder: ToolResponseBuilder, tool_schema_builder: ToolSchemaBuilder, schema_key: str = "{{llm_tools_list}}", replace_schema_all: bool = True):
        self.tool_call_extractor = tool_call_extractor
        self.tool_call_builder = tool_call_builder
        self.tool_response_builder = tool_response_builder
        self.tool_schema_builder = tool_schema_builder
        self.schema_key = schema_key
        self.replace_schema_all = replace_schema_all
    
    def convert_openai(self, openai_json: Dict) -> Dict:
        new_json = copy.deepcopy(openai_json)
        if "tool_choice" in new_json:
            if new_json["tool_choice"] not in ["auto", "none", None]:
                raise ValueError(f"Unsupported parameter: 'tool_choice' set to '{new_json['tool_choice']}'. This pipeline only supports 'auto' behavior.")
            del new_json["tool_choice"]
        if "messages" not in new_json:
            raise ValueError("OpenAI JSON must contain a messages key.")
        
        # Begin by parsing tool responses and copying over the message history
        # Merge adjacent tool responses with hanging user messages into one response block
        tool_response_buffer = []
        new_messages = []
        def flush_buffer(user_message: Dict = None):
            # Append the buffer and user message
            tool_response_str = self.tool_response_builder.build(tool_response_buffer)
            if user_message is not None:
                if "content" in user_message and user_message["content"] != "":
                    tool_response_str = tool_response_str + "\n"
                else:
                    user_message["content"] = ""
                new_messages.append(user_message)
            else:
                new_messages.append({"role": "user", "content": ""})
            new_messages[-1]["content"] = tool_response_str + new_messages[-1]["content"]
        for message in new_json["messages"]:
            # Note: Odd cases where the user message is multimodal and preceeded by tool calls will cause a crash
            # This is rare so will be ignored for now
            if len(tool_response_buffer) > 0 and message["role"] != "tool":
                if message["role"] == "user":
                    flush_buffer(message)
                else:
                    flush_buffer(None)
                    new_messages.append(message)
                tool_response_buffer.clear()
            elif message["role"] == "tool":
                tool_response_buffer.append(message)
            else:
                new_messages.append(message)
        if len(tool_response_buffer) > 0:
            flush_buffer()
        new_json["messages"] = new_messages

        # Parse schema, replace the schema key with the schema string
        if "tools" in new_json:
            schema_list = self.tool_schema_builder.build(new_json["tools"])
            schema_str = "\n\n".join(schema_list)
            if self.replace_schema_all:
                for message in new_json["messages"]:
                    if "content" in message and message["content"] != "" and isinstance(message["content"], str):
                        message["content"] = message["content"].replace(self.schema_key, schema_str)
            else:
                for message in new_json["messages"]:
                    if message["role"] == "system" and "content" in message and message["content"] != "" and isinstance(message["content"], str):
                        message["content"] = message["content"].replace(self.schema_key, schema_str)
            del new_json["tools"]
        # Now parse tool calls
        for message in new_json["messages"]:
            if "tool_calls" in message:
                if "content" not in message:
                    message["content"] = ""
                else:
                    message["content"] += "\n"
                tool_call_str = self.tool_call_builder.build(message["tool_calls"])
                message["content"] += tool_call_str
                del message["tool_calls"]
        return new_json
    
    def extract_response(self, response_str: str) -> Tuple[Dict, List]:
        extracted_response = self.tool_call_extractor.extract(response_str)
        
        # Convert extracted tool calls to OpenAI format
        openai_tool_calls = []
        for tool_call in extracted_response[1]:
            # Convert from internal format
            openai_tool_calls.append({
                "id": "call_" + str(uuid.uuid4())[:8],
                "type": "function",
                "function": {
                    "name": tool_call["name"],
                    "arguments": json.dumps(tool_call["arguments"])
                }
            })

        openai_message = {"role": "assistant", "content": extracted_response[0], "tool_calls": openai_tool_calls, "finish_reason": "stop" if openai_tool_calls == [] else "tool"}
        return openai_message, extracted_response[2]