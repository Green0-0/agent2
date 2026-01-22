import pytest
import json
from agent2.tool_api.tool_validator import ToolValidator

class TestToolValidator:
    def setup_method(self):
        self.schemas = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather info",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"},
                            "unit": {"type": "string", "enum": ["c", "f"]},
                            "days": {"type": "integer"}
                        },
                        "required": ["location"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "complex_tool",
                    "description": "Test various types",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "str_arg": {"type": "string"},
                            "int_arg": {"type": "integer"},
                            "bool_arg": {"type": "boolean"},
                            "num_arg": {"type": "number"},
                            "list_arg": {"type": "array"},
                            "obj_arg": {"type": "object"},
                        },
                        "required": ["str_arg"]
                    }
                }
            }
        ]

    def test_valid_call(self):
        call = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"location": "London", "unit": "c", "days": 5})
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert errors == []

    def test_missing_tool(self):
        call = {
            "type": "function",
            "function": {
                "name": "unknown_tool",
                "arguments": "{}"
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Tool 'unknown_tool' not found in schema." in errors

    def test_missing_required_arg(self):
        call = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"unit": "c"})
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Missing required argument: 'location'." in errors

    def test_extra_arg(self):
        call = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"location": "London", "extra": "val"})
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Unknown argument: 'extra'." in errors

    def test_wrong_type_string(self):
        call = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"location": 123}) # Should be string
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Argument 'location' expected type 'string', got 'int'." in errors

    def test_invalid_enum(self):
        call = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({"location": "London", "unit": "kelvin"})
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Argument 'unit' value 'kelvin' is not valid. Allowed: ['c', 'f']." in errors

    # --- New Edge Cases ---

    def test_malformed_json_arguments(self):
        call = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": "{bad_json"
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Tool arguments are not valid JSON." in errors

    def test_arguments_not_dict(self):
        call = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": "[\"list\", \"instead\"]"
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Tool arguments must be a dictionary." in errors

    def test_missing_function_field(self):
        call = {
            "type": "function",
            # Missing "function"
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Tool call missing 'function' field." in errors

    def test_missing_name_field(self):
        call = {
            "type": "function",
            "function": {
                # Missing "name"
                "arguments": "{}"
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Tool call missing function name." in errors

    def test_wrong_tool_type(self):
        call = {
            "type": "code_interpreter", # Wrong type
            "function": {
                "name": "get_weather",
                "arguments": "{}"
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Tool call type must be 'function'." in errors

    def test_multiple_errors(self):
        # Missing required arg AND extra arg AND wrong type
        call = {
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": json.dumps({
                    "unit": 123, # Wrong type (should be string)
                    "extra": "val" # Extra arg
                    # Missing 'location'
                })
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Missing required argument: 'location'." in errors
        assert "Unknown argument: 'extra'." in errors
        assert "Argument 'unit' expected type 'string', got 'int'." in errors

    def test_complex_types(self):
        # Test int, bool, number, array, object
        call = {
            "type": "function",
            "function": {
                "name": "complex_tool",
                "arguments": json.dumps({
                    "str_arg": "ok",
                    "int_arg": "not_int",
                    "bool_arg": "not_bool",
                    "num_arg": "not_num",
                    "list_arg": "not_list",
                    "obj_arg": "not_obj"
                })
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert "Argument 'int_arg' expected type 'integer', got 'str'." in errors
        assert "Argument 'bool_arg' expected type 'boolean', got 'str'." in errors
        assert "Argument 'num_arg' expected type 'number', got 'str'." in errors
        assert "Argument 'list_arg' expected type 'array', got 'str'." in errors
        assert "Argument 'obj_arg' expected type 'object', got 'str'." in errors

    def test_valid_complex_types(self):
        call = {
            "type": "function",
            "function": {
                "name": "complex_tool",
                "arguments": json.dumps({
                    "str_arg": "ok",
                    "int_arg": 42,
                    "bool_arg": True,
                    "num_arg": 3.14,
                    "list_arg": [1, 2, 3],
                    "obj_arg": {"key": "val"}
                })
            }
        }
        errors = ToolValidator.validate(call, self.schemas)
        assert errors == []

    def test_schema_fallback_format(self):
        # Test schema that is just the function dict (without wrapper)
        simple_schema = [
            {
                "name": "simple_tool",
                "parameters": {
                    "type": "object",
                    "properties": {"arg": {"type": "string"}},
                    "required": ["arg"]
                }
            }
        ]
        call = {
            "type": "function",
            "function": {
                "name": "simple_tool",
                "arguments": json.dumps({"arg": "val"})
            }
        }
        errors = ToolValidator.validate(call, simple_schema)
        assert errors == []
