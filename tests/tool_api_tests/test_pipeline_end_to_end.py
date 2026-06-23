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

    converted_request = pipeline.convert_openai(openai_request)

    print("\n=== 2. Converted Request (Sent to Model) ===")
    print(json.dumps(converted_request, indent=2))

    last_message = converted_request["messages"][-1]
    assert last_message["role"] == "user"
    assert "What is the weather in London?" in last_message["content"]
    
    system_message = converted_request["messages"][0]
    assert "{{llm_tools_list}}" not in system_message["content"]
    assert "get_weather" in system_message["content"]
    assert "location" in system_message["content"]

    model_response_str = """Thinking process...
<tool_call>
<name>get_weather</name>
<location>London</location>
<unit>celsius</unit>
</tool_call>
"""
    print("\n=== 3. Simulated Model Response ===")
    print(model_response_str)

    openai_response, errors = pipeline.extract_response(model_response_str)

    print("\n=== 4. Extracted OpenAI Response ===")
    print(json.dumps(openai_response, indent=2))
    
    if errors:
        print("\n--- Errors ---")
        print(errors)

    assert openai_response["role"] == "assistant"
    assert openai_response["finish_reason"] == "tool"
    assert len(openai_response["tool_calls"]) == 1
    
    tool_call = openai_response["tool_calls"][0]
    assert tool_call["function"]["name"] == "get_weather"
    
    args = json.loads(tool_call["function"]["arguments"])
    assert args["location"] == "London"
    assert args["unit"] == "celsius"
    assert errors == []
    
    tool_result_message = {
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "name": "get_weather",
        "content": "The weather in London is 15 degrees Celsius."
    }
    
    follow_up_request = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant. {{llm_tools_list}}"},
            {"role": "user", "content": "What is the weather in London?"},
            openai_response,
            tool_result_message
        ],
        "tools": tools
    }
    
    print("\n=== 5. Follow-up OpenAI Request (with Tool Output) ===")
    print(json.dumps(follow_up_request, indent=2))

    converted_follow_up = pipeline.convert_openai(follow_up_request)
    
    print("\n=== 6. Converted Follow-up Request ===")
    print(json.dumps(converted_follow_up, indent=2))

    assistant_msg = converted_follow_up["messages"][2]
    assert assistant_msg["role"] == "assistant"
    assert "<tool_call>" in assistant_msg["content"]
    assert "get_weather" in assistant_msg["content"]

    last_msg = converted_follow_up["messages"][-1]
    assert last_msg["role"] == "user"
    assert "The weather in London is 15 degrees Celsius." in last_msg["content"]

def test_pipeline_schema_validation():
    """Test that pipeline properly triggers schema validation errors."""
    extractor = XMLToolCallExtractor()
    builder = XMLToolCallBuilder()
    schema_builder = XMLToolSchemaBuilder()
    response_builder = GenericResponseBuilder()
    
    pipeline = StandardToolPipeline(extractor, builder, response_builder, schema_builder)
    
    schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "unit": {"type": "string", "enum": ["c", "f"]}
                    },
                    "required": ["location", "unit"]
                }
            }
        }
    ]
    
    model_response_str = """
<tool_call>
<name>get_weather</name>
<location>London</location>
<unit>invalid_unit</unit>
</tool_call>
"""
    
    openai_response, errors = pipeline.extract_response(model_response_str, schemas=schemas)
    
    assert len(errors) == 1
    assert "Argument 'unit' value 'invalid_unit' is not valid." in errors[0]

def test_pipeline_invalid_tool_choice():
    """Test that the pipeline raises ValueError on invalid tool_choice."""
    pipeline = StandardToolPipeline(
        XMLToolCallExtractor(), XMLToolCallBuilder(), GenericResponseBuilder(), XMLToolSchemaBuilder()
    )
    with pytest.raises(ValueError, match="Unsupported parameter: 'tool_choice'"):
        pipeline.convert_openai({"messages": [], "tool_choice": "required"})

def test_pipeline_missing_messages():
    """Test that the pipeline raises ValueError if messages key is missing."""
    pipeline = StandardToolPipeline(
        XMLToolCallExtractor(), XMLToolCallBuilder(), GenericResponseBuilder(), XMLToolSchemaBuilder()
    )
    with pytest.raises(ValueError, match="OpenAI JSON must contain a messages key."):
        pipeline.convert_openai({"tool_choice": "auto"})

def test_pipeline_multimodal_payload():
    """Test pipeline handling of multimodal lists in message contents."""
    pipeline = StandardToolPipeline(
        XMLToolCallExtractor(), XMLToolCallBuilder(), GenericResponseBuilder(), XMLToolSchemaBuilder()
    )
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "test_tool",
                "parameters": {"type": "object", "properties": {}}
            }
        }
    ]
    
    openai_request = {
        "messages": [
            {
                "role": "system",
                "content": [{"type": "text", "text": "System message {{llm_tools_list}}"}]
            },
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "I will call a tool."}],
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {"name": "test_tool", "arguments": "{}"}
                    }
                ]
            },
            {
                "role": "tool",
                "tool_call_id": "call_123",
                "name": "test_tool",
                "content": "Tool result"
            },
            {
                "role": "user",
                "content": [{"type": "text", "text": "Follow up"}]
            }
        ],
        "tools": tools
    }
    
    converted = pipeline.convert_openai(openai_request)
    
    sys_content = converted["messages"][0]["content"]
    assert isinstance(sys_content, list)
    assert "test_tool" in sys_content[0]["text"]
    assert "{{llm_tools_list}}" not in sys_content[0]["text"]
    
    asst_content = converted["messages"][1]["content"]
    assert isinstance(asst_content, list)
    assert len(asst_content) == 2
    assert asst_content[0]["text"] == "I will call a tool."
    assert "<tool_call>" in asst_content[1]["text"]
    
    usr_content = converted["messages"][2]["content"]
    assert isinstance(usr_content, list)
    assert len(usr_content) == 2
    assert "Tool result" in usr_content[0]["text"]
    assert usr_content[1]["text"] == "Follow up"
