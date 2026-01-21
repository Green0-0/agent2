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

    def test_wrong_type(self):
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
