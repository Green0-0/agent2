import copy
from typing import List, Dict, Tuple
from agent2.tool_api.abc.tool_pipeline import ToolPipeline
from agent2.tool_api.tool_validator import validate

class StandardToolPipeline(ToolPipeline):
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
                if "content" in user_message and user_message["content"] != "" and user_message["content"] != []:
                    if isinstance(user_message["content"], str):
                        tool_response_str = tool_response_str + "\n"
                else:
                    user_message["content"] = ""
                new_messages.append(user_message)
            else:
                new_messages.append({"role": "user", "content": ""})
            
            if isinstance(new_messages[-1]["content"], list):
                new_messages[-1]["content"].insert(0, {"type": "text", "text": tool_response_str + "\n"})
            else:
                new_messages[-1]["content"] = tool_response_str + new_messages[-1]["content"]
        for message in new_json["messages"]:
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
            schema_str = self._get_schema_string(new_json["tools"])
            if self.replace_schema_all:
                for message in new_json["messages"]:
                    if "content" in message and message["content"]:
                        if isinstance(message["content"], str):
                            message["content"] = message["content"].replace(self.schema_key, schema_str)
                        elif isinstance(message["content"], list):
                            for item in message["content"]:
                                if item.get("type") == "text" and "text" in item:
                                    item["text"] = item["text"].replace(self.schema_key, schema_str)
            else:
                for message in new_json["messages"]:
                    if message["role"] == "system" and "content" in message and message["content"]:
                        if isinstance(message["content"], str):
                            message["content"] = message["content"].replace(self.schema_key, schema_str)
                        elif isinstance(message["content"], list):
                            for item in message["content"]:
                                if item.get("type") == "text" and "text" in item:
                                    item["text"] = item["text"].replace(self.schema_key, schema_str)
            del new_json["tools"]
            
        # Now parse tool calls
        for message in new_json["messages"]:
            if "tool_calls" in message:
                if "content" not in message:
                    message["content"] = ""
                else:
                    if isinstance(message["content"], str):
                        message["content"] += "\n"
                tool_call_str = self.tool_call_builder.build(message["tool_calls"])
                if isinstance(message["content"], list):
                    message["content"].append({"type": "text", "text": "\n" + tool_call_str})
                else:
                    message["content"] += tool_call_str
                del message["tool_calls"]
        return new_json
    
    def extract_response(self, response_str: str, schemas: List[Dict] = None) -> Tuple[Dict, List]:
        extracted_response = self.tool_call_extractor.extract(response_str)
        
        openai_message = self._to_openai_fc(extracted_response[0], extracted_response[1])
        errors = extracted_response[2]

        if schemas is not None:
            for tool_call in openai_message.get("tool_calls", []):
                errors.extend(validate(tool_call, schemas))

        return openai_message, errors
