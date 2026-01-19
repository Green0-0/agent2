import pytest
import json
from typing import List, Dict, Any
from agent2.tool_api.xml.xml_tool_schema_builder import XMLToolSchemaBuilder
from agent2.tool_api.json.json_tool_schema_builder import JSONToolSchemaBuilder
from agent2.tool_api.md.md_tool_schema_builder import MDToolSchemaBuilder

# --- Test Data ---

SAMPLE_TOOL_SCHEMA = [
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
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit of temperature"
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for a query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

COMPLEX_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "complex_tool",
            "description": "A tool with complex parameters",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of items"
                    },
                    "is_valid": {
                        "type": "boolean",
                        "description": "Check validity"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tags"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Arbitrary metadata"
                    }
                },
                "required": ["count"]
            }
        }
    }
]

MISSING_FIELDS_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "incomplete_props",
            "parameters": {
                "type": "object",
                "properties": {
                    "arg_no_type": {"description": "Missing type"},
                    "arg_no_desc": {"type": "string"},
                    "arg_empty": {}
                }
            }
        }
    }
]

MINIMAL_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "minimal_tool"
        }
    }
]

EMPTY_PARAMS_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "no_params",
            "parameters": {}
        }
    }
]

# --- Helper Functions ---

def print_section(title: str, content: str):
    print(f"\n--- {title} ---")
    print(content)

def print_comparison(title: str, xml: str, json_str: str, md: str):
    print(f"\n=== {title} Output ===")
    print_section("XML", xml)
    print_section("JSON", json_str)
    print_section("MD", md)
    print("=========================\n")

# --- Tests ---

def test_standard_schema_generation():
    """Test that all builders correctly generate schemas for a standard set of tools."""
    xml_builder = XMLToolSchemaBuilder()
    json_builder = JSONToolSchemaBuilder()
    md_builder = MDToolSchemaBuilder()

    xml_schema = xml_builder.build(SAMPLE_TOOL_SCHEMA)
    json_schema = json_builder.build(SAMPLE_TOOL_SCHEMA)
    md_schema = md_builder.build(SAMPLE_TOOL_SCHEMA)

    print_comparison("Standard Schema", xml_schema, json_schema, md_schema)

    # XML Assertions
    assert "<name>get_weather</name>" in xml_schema
    assert "<location>Required (string): The city and state, e.g. San Francisco, CA</location>" in xml_schema
    assert "<name>search_web</name>" in xml_schema

    # JSON Assertions
    loaded_json = json.loads(json_schema)
    assert loaded_json == SAMPLE_TOOL_SCHEMA

    # MD Assertions
    assert "## Name: get_weather" in md_schema
    assert "### location (string, required): The city and state" in md_schema
    assert "## Name: search_web" in md_schema


def test_complex_properties():
    """Test handling of complex property types (integer, boolean, array, object)."""
    xml_builder = XMLToolSchemaBuilder()
    json_builder = JSONToolSchemaBuilder()
    md_builder = MDToolSchemaBuilder()

    xml_schema = xml_builder.build(COMPLEX_TOOL_SCHEMA)
    json_schema = json_builder.build(COMPLEX_TOOL_SCHEMA)
    md_schema = md_builder.build(COMPLEX_TOOL_SCHEMA)

    print_comparison("Complex Properties", xml_schema, json_schema, md_schema)

    # XML Assertions
    assert "<count>Required (integer): Number of items</count>" in xml_schema
    assert "<tags>Optional (array): List of tags</tags>" in xml_schema

    # JSON Assertions
    assert "complex_tool" in json_schema
    assert "integer" in json_schema

    # MD Assertions
    assert "### count (integer, required): Number of items" in md_schema
    assert "### tags (array, optional): List of tags" in md_schema


def test_missing_fields_in_properties():
    """Test robustness when property fields (type, description) are missing."""
    xml_builder = XMLToolSchemaBuilder()
    json_builder = JSONToolSchemaBuilder()
    md_builder = MDToolSchemaBuilder()

    xml_schema = xml_builder.build(MISSING_FIELDS_TOOL_SCHEMA)
    json_schema = json_builder.build(MISSING_FIELDS_TOOL_SCHEMA)
    md_schema = md_builder.build(MISSING_FIELDS_TOOL_SCHEMA)

    print_comparison("Missing Fields", xml_schema, json_schema, md_schema)

    # XML Assertions (Defaults: type=string, desc="")
    assert "<arg_no_type>Optional (string): Missing type</arg_no_type>" in xml_schema
    assert "<arg_no_desc>Optional (string)</arg_no_desc>" in xml_schema

    # JSON Assertions
    assert "incomplete_props" in json_schema

    # MD Assertions
    assert "### arg_no_type (string, optional): Missing type" in md_schema
    assert "### arg_no_desc (string, optional): " in md_schema


def test_edge_cases():
    """Test edge cases: empty schema, minimal tool, empty parameters."""
    xml_builder = XMLToolSchemaBuilder()
    json_builder = JSONToolSchemaBuilder()
    md_builder = MDToolSchemaBuilder()

    # 1. Empty Schema
    empty_schema = []
    assert xml_builder.build(empty_schema) == ""
    assert json_builder.build(empty_schema) == "[]"
    assert md_builder.build(empty_schema) == ""

    # 2. Minimal Tool (no params, no desc)
    xml_min = xml_builder.build(MINIMAL_TOOL_SCHEMA)
    json_min = json_builder.build(MINIMAL_TOOL_SCHEMA)
    md_min = md_builder.build(MINIMAL_TOOL_SCHEMA)
    
    print_comparison("Edge Case: Minimal Tool", xml_min, json_min, md_min)

    assert "<name>minimal_tool</name>" in xml_min
    assert "minimal_tool" in json_min
    assert "## Name: minimal_tool" in md_min

    # 3. Tool with Empty Parameters
    xml_empty = xml_builder.build(EMPTY_PARAMS_TOOL_SCHEMA)
    json_empty = json_builder.build(EMPTY_PARAMS_TOOL_SCHEMA)
    md_empty = md_builder.build(EMPTY_PARAMS_TOOL_SCHEMA)

    print_comparison("Edge Case: Empty Params", xml_empty, json_empty, md_empty)

    assert "<name>no_params</name>" in xml_empty
    assert "no_params" in json_empty
    assert "## Name: no_params" in md_empty
