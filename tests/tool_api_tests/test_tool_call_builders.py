import pytest
import json
from typing import List, Dict, Any
from agent2.tool_api.xml.xml_tool_call_builder import XMLToolCallBuilder
from agent2.tool_api.json.json_tool_call_builder import JSONToolCallBuilder
from agent2.tool_api.md.md_tool_call_builder import MDToolCallBuilder
from agent2.tool_api.fake_codeact.fake_codeact_tool_call_builder import FakeCodeActToolCallBuilder

# --- Test Data ---

# Standard tool call (OpenAI format)
SAMPLE_TOOL_CALLS = [
    {
        "id": "call_1",
        "type": "function",
        "function": {
            "name": "get_weather",
            "arguments": '{"location": "San Francisco, CA", "unit": "celsius"}'
        }
    }
]

# Multiple tool calls
MULTIPLE_TOOL_CALLS = [
    {
        "id": "call_2",
        "type": "function",
        "function": {
            "name": "get_weather",
            "arguments": '{"location": "New York, NY"}'
        }
    },
    {
        "id": "call_3",
        "type": "function",
        "function": {
            "name": "search_web",
            "arguments": '{"query": "best pizza in NYC"}'
        }
    }
]

# Complex arguments (nested, types)
# Note: OpenAI arguments are JSON strings.
COMPLEX_TOOL_CALLS = [
    {
        "id": "call_4",
        "type": "function",
        "function": {
            "name": "complex_action",
            "arguments": json.dumps({
                "count": 42,
                "is_active": True,
                "tags": ["a", "b", "c"],
                "metadata": {"source": "user"}
            })
        }
    }
]

# Edge case: No arguments
NO_ARGS_TOOL_CALLS = [
    {
        "id": "call_5",
        "type": "function",
        "function": {
            "name": "simple_action",
            "arguments": "{}"
        }
    }
]



# --- Helper Functions ---

def print_section(title: str, content: str):
    print(f"\n--- {title} ---")
    print(content)

def print_comparison(title: str, xml: str, json_str: str, md: str, codeact: str):
    print(f"\n=== {title} Output ===")
    print_section("XML", xml)
    print_section("JSON", json_str)
    print_section("MD", md)
    print_section("CodeAct", codeact)
    print("=========================\n")

# --- Tests ---

def test_standard_tool_call_generation():
    """Test that all builders correctly generate strings for a standard tool call."""
    xml_builder = XMLToolCallBuilder()
    json_builder = JSONToolCallBuilder()
    md_builder = MDToolCallBuilder()
    codeact_builder = FakeCodeActToolCallBuilder()

    xml_out = xml_builder.build(SAMPLE_TOOL_CALLS)
    json_out = json_builder.build(SAMPLE_TOOL_CALLS)
    md_out = md_builder.build(SAMPLE_TOOL_CALLS)
    codeact_out = codeact_builder.build(SAMPLE_TOOL_CALLS)

    print_comparison("Standard Tool Call", xml_out, json_out, md_out, codeact_out)

    # XML Assertions
    assert "<tool_call>" in xml_out
    assert "<name>get_weather</name>" in xml_out
    assert "<location>San Francisco, CA</location>" in xml_out
    assert "<unit>celsius</unit>" in xml_out
    assert "</tool_call>" in xml_out

    # JSON Assertions
    # Strip markdown delimiters for parsing
    json_content = json_out.replace("```json\n", "").replace("\n```", "")
    loaded_json = json.loads(json_content)
    # The builder should simplify the OpenAI format to a list of {name, arguments}
    assert len(loaded_json) == 1
    assert loaded_json[0]["name"] == "get_weather"
    assert loaded_json[0]["arguments"]["location"] == "San Francisco, CA"

    # MD Assertions
    assert "# Tool Use" in md_out
    assert "## Name: get_weather" in md_out
    assert "### location: San Francisco, CA" in md_out
    assert "### unit: celsius" in md_out
    assert "# Tool End" in md_out
    
    # CodeAct Assertions
    assert "<code>" in codeact_out
    assert "get_weather(location='San Francisco, CA', unit='celsius')" in codeact_out
    assert "</code>" in codeact_out


def test_multiple_tool_calls():
    """Test handling of multiple tool calls in a single list."""
    xml_builder = XMLToolCallBuilder()
    json_builder = JSONToolCallBuilder()
    md_builder = MDToolCallBuilder()
    codeact_builder = FakeCodeActToolCallBuilder()

    xml_out = xml_builder.build(MULTIPLE_TOOL_CALLS)
    json_out = json_builder.build(MULTIPLE_TOOL_CALLS)
    md_out = md_builder.build(MULTIPLE_TOOL_CALLS)
    codeact_out = codeact_builder.build(MULTIPLE_TOOL_CALLS)

    print_comparison("Multiple Tool Calls", xml_out, json_out, md_out, codeact_out)

    # XML Assertions
    assert xml_out.count("<tool_call>") == 2
    assert "<name>get_weather</name>" in xml_out
    assert "<name>search_web</name>" in xml_out

    # JSON Assertions
    json_content = json_out.replace("```json\n", "").replace("\n```", "")
    loaded_json = json.loads(json_content)
    assert len(loaded_json) == 2
    assert loaded_json[0]["name"] == "get_weather"
    assert loaded_json[1]["name"] == "search_web"

    # MD Assertions
    assert md_out.count("# Tool Use") == 2
    assert "## Name: get_weather" in md_out
    assert "## Name: search_web" in md_out
    
    # CodeAct Assertions
    assert "get_weather(location='New York, NY')" in codeact_out
    assert "search_web(query='best pizza in NYC')" in codeact_out


def test_complex_arguments():
    """Test handling of non-string arguments (int, bool, list, dict)."""
    xml_builder = XMLToolCallBuilder()
    json_builder = JSONToolCallBuilder()
    md_builder = MDToolCallBuilder()
    codeact_builder = FakeCodeActToolCallBuilder()

    xml_out = xml_builder.build(COMPLEX_TOOL_CALLS)
    json_out = json_builder.build(COMPLEX_TOOL_CALLS)
    md_out = md_builder.build(COMPLEX_TOOL_CALLS)
    codeact_out = codeact_builder.build(COMPLEX_TOOL_CALLS)

    print_comparison("Complex Arguments", xml_out, json_out, md_out, codeact_out)

    # XML Assertions
    # Note: XML builder uses str() conversion
    assert "<count>42</count>" in xml_out
    assert "<is_active>True</is_active>" in xml_out
    # List/Dict string representation might vary slightly but usually predictable
    # XML builder no longer escapes quotes
    assert "<tags>['a', 'b', 'c']</tags>" in xml_out

    # JSON Assertions
    json_content = json_out.replace("```json\n", "").replace("\n```", "")
    loaded_json = json.loads(json_content)
    assert loaded_json[0]["arguments"]["count"] == 42
    assert loaded_json[0]["arguments"]["is_active"] is True

    # MD Assertions
    assert "### count: 42" in md_out
    assert "### is_active: True" in md_out
    
    # CodeAct Assertions
    assert "count=42" in codeact_out
    assert "is_active=True" in codeact_out
    assert "tags=['a', 'b', 'c']" in codeact_out
    assert "metadata={'source': 'user'}" in codeact_out


def test_edge_cases():
    """Test empty list and empty arguments."""
    xml_builder = XMLToolCallBuilder()
    json_builder = JSONToolCallBuilder()
    md_builder = MDToolCallBuilder()
    codeact_builder = FakeCodeActToolCallBuilder()

    # 1. Empty List
    empty_out_xml = xml_builder.build([])
    empty_out_json = json_builder.build([])
    empty_out_md = md_builder.build([])
    empty_out_codeact = codeact_builder.build([])

    assert empty_out_xml == ""
    # JSON builder now wraps empty list in delimiters too
    assert "```json" in empty_out_json
    assert "[]" in empty_out_json
    assert empty_out_md == ""
    assert empty_out_codeact == ""

    # 2. No Arguments
    no_args_xml = xml_builder.build(NO_ARGS_TOOL_CALLS)
    no_args_json = json_builder.build(NO_ARGS_TOOL_CALLS)
    no_args_md = md_builder.build(NO_ARGS_TOOL_CALLS)
    no_args_codeact = codeact_builder.build(NO_ARGS_TOOL_CALLS)

    print_comparison("No Arguments", no_args_xml, no_args_json, no_args_md, no_args_codeact)

    assert "<name>simple_action</name>" in no_args_xml
    # Should not have any argument tags
    assert "<arguments>" not in no_args_xml 

    assert "simple_action" in no_args_json
    
    assert "## Name: simple_action" in no_args_md
    # Should not have any argument lines
    assert "###" not in no_args_md
    
    assert "simple_action()" in no_args_codeact
