import pytest
import json
from agent2.tool_api.pipeline import StandardToolPipeline
from agent2.tool_api.xml.xml_tool_call_extractor import XMLToolCallExtractor
from agent2.tool_api.xml.xml_tool_call_builder import XMLToolCallBuilder
from agent2.tool_api.xml.xml_tool_schema_builder import XMLToolSchemaBuilder
from agent2.tool_api.generic_response_builder import GenericResponseBuilder

def test_pipeline_end_to_end_xml(capsys):
    """
    Test the StandardToolPipeline end-to-end using XML components.
    This simulates the full flow:
    1. OpenAI Request -> Pipeline -> Model Input (String with Schema)
    2. Model Response (String with XML) -> Pipeline -> OpenAI Response (Tool Calls)
    3. OpenAI Request (with Tool Output) -> Pipeline -> Model Input (Formatted History)
    """
    
    # 1. Setup Pipeline
    extractor = XMLToolCallExtractor()
    builder = XMLToolCallBuilder()
    schema_builder = XMLToolSchemaBuilder()
    response_builder = GenericResponseBuilder()
    
    pipeline = StandardToolPipeline(
        tool_call_extractor=extractor,
        tool_call_builder=builder,
        tool_response_builder=response_builder,
        tool_schema_builder=schema_builder
    )

    # 2. Define Tools and Input
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    messages = [
        {"role": "system", "content": "You are a helpful assistant. {{llm_tools_list}}"},
        {"role": "user", "content": "What is the weather in London?"}
    ]

    openai_request = {
        "model": "gpt-4",
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto"
    }

    print("\n\n=== 1. Original OpenAI Request ===")
    print(json.dumps(openai_request, indent=2))

    # 3. Convert to Model Input (Pipeline Step 1)
    converted_request = pipeline.convert_openai(openai_request)

    print("\n=== 2. Converted Request (Sent to Model) ===")
    print(json.dumps(converted_request, indent=2))

    # Assertions for Conversion
    last_message = converted_request["messages"][-1]
    assert last_message["role"] == "user"
    assert "What is the weather in London?" in last_message["content"]
    
    # Check if schema was injected
    system_message = converted_request["messages"][0]
    # The schema builder should have replaced the placeholder
    assert "{{llm_tools_list}}" not in system_message["content"]
    # It should contain the tool definition
    assert "get_weather" in system_message["content"]
    assert "location" in system_message["content"]

    # 4. Simulate Model Response
    # The model should return an XML tool call
    # Note: The exact format depends on the XMLToolCallExtractor's expectations.
    # Assuming standard <tool_code> format based on previous context.
    model_response_str = """Thinking process...
<tool_call>
<name>get_weather</name>
<location>London</location>
<unit>celsius</unit>
</tool_call>
"""
    print("\n=== 3. Simulated Model Response ===")
    print(model_response_str)

    # 5. Extract Response (Pipeline Step 2)
    openai_response, errors = pipeline.extract_response(model_response_str)

    print("\n=== 4. Extracted OpenAI Response ===")
    print(json.dumps(openai_response, indent=2))
    
    if errors:
        print("\n--- Errors ---")
        print(errors)

    # Assertions for Extraction
    assert openai_response["role"] == "assistant"
    assert openai_response["finish_reason"] == "tool"
    assert len(openai_response["tool_calls"]) == 1
    
    tool_call = openai_response["tool_calls"][0]
    assert tool_call["function"]["name"] == "get_weather"
    
    # Arguments are a JSON string in the OpenAI format
    args = json.loads(tool_call["function"]["arguments"])
    assert args["location"] == "London"
    assert args["unit"] == "celsius"
    assert errors == []

    # 6. Simulate Tool Execution and Follow-up
    # Now we simulate the user sending back the tool result
    
    tool_result_message = {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "name": "get_weather",
        "content": "The weather in London is 15 degrees Celsius."
    }
    
    # Construct the follow-up request including the history
    follow_up_request = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. {{llm_tools_list}}"},
            {"role": "user", "content": "What is the weather in London?"},
            openai_response, # The assistant's tool call message
            tool_result_message # The tool output message
        ],
        "tools": tools
    }
    
    print("\n=== 5. Follow-up OpenAI Request (with Tool Output) ===")
    print(json.dumps(follow_up_request, indent=2))

    converted_follow_up = pipeline.convert_openai(follow_up_request)
    
    print("\n=== 6. Converted Follow-up Request ===")
    print(json.dumps(converted_follow_up, indent=2))

    # Assertions for Follow-up
    # The pipeline should merge the tool response into the conversation
    # The tool call itself (from the assistant) should be formatted by tool_call_builder
    # The tool result (from the tool) should be formatted by tool_response_builder
    
    # Check that the assistant message (index 2) has the tool call formatted
    # Note: convert_openai modifies the messages list in place or returns a new one?
    # It does deepcopy at the start: new_json = copy.deepcopy(openai_json)
    
    # The assistant message with tool_calls should be converted to content
    assistant_msg = converted_follow_up["messages"][2]
    assert assistant_msg["role"] == "assistant"
    # The tool call builder should have put the XML representation in content
    assert "<tool_call>" in assistant_msg["content"]
    assert "get_weather" in assistant_msg["content"]
    
    # The tool result message (index 3) should be formatted
    # Wait, the pipeline logic merges tool responses.
    # Let's look at the pipeline logic again.
    # It iterates messages. If role is tool, it buffers.
    # Then it flushes buffer.
    # If the next message is user, it appends to user.
    # If end of list, it appends a new user message?
    
    # In our case, the tool message is the last one.
    # So it should flush buffer.
    # flush_buffer() with no user message appends {"role": "user", "content": ...}
    
    last_msg = converted_follow_up["messages"][-1]
    assert last_msg["role"] == "user"
    # The content should contain the tool output
    assert "The weather in London is 15 degrees Celsius." in last_msg["content"]
