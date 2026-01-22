import json
from typing import List, Dict, Any

class ToolValidator:
    """
    Validates OpenAI tool calls against a provided tool schema list.
    """
    
    @staticmethod
    def validate(tool_call: Dict[str, Any], tool_schemas: List[Dict[str, Any]]) -> List[str]:
        """
        Validates a single tool call against the provided schemas.
        
        Args:
            tool_call (Dict[str, Any]): The OpenAI tool call object.
                Expected format:
                {
                    "type": "function",
                    "function": {
                        "name": "tool_name",
                        "arguments": "{\"arg\": \"val\"}"
                    }
                }
            tool_schemas (List[Dict[str, Any]]): List of OpenAI tool definitions.
            
        Returns:
            List[str]: A list of error messages. Empty if valid.
        """
        errors = []
        
        # 1. Basic Structure Check
        if tool_call.get("type") != "function":
            return ["Tool call type must be 'function'."]
        
        if "function" not in tool_call:
            return ["Tool call missing 'function' field."]
            
        call_func = tool_call["function"]
        tool_name = call_func.get("name")
        
        if not tool_name:
            return ["Tool call missing function name."]
            
        # Parse arguments
        try:
            arguments_str = call_func.get("arguments", "{}")
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
            if not isinstance(arguments, dict):
                return ["Tool arguments must be a dictionary."]
        except json.JSONDecodeError:
            return ["Tool arguments are not valid JSON."]

        # 2. Find Schema
        matching_schema = None
        for schema in tool_schemas:
            # OpenAI schema format: {"type": "function", "function": {...}}
            if schema.get("type") == "function":
                schema_func = schema.get("function", {})
                if schema_func.get("name") == tool_name:
                    matching_schema = schema_func
                    break
            # Handle case where schema might be just the function dict (less common in OpenAI API but possible in internal reps)
            elif schema.get("name") == tool_name:
                matching_schema = schema
                break
        
        if not matching_schema:
            return [f"Tool '{tool_name}' not found in schema."]

        # 3. Validate Arguments
        parameters = matching_schema.get("parameters", {})
        properties = parameters.get("properties", {})
        required_args = parameters.get("required", [])
        
        # Check for missing required arguments
        for req_arg in required_args:
            if req_arg not in arguments:
                errors.append(f"Missing required argument: '{req_arg}'.")
        
        # Check for extra arguments
        for arg_name in arguments:
            if arg_name not in properties:
                errors.append(f"Unknown argument: '{arg_name}'.")
            else:
                expected_type = properties[arg_name].get("type")
                value = arguments[arg_name]
                
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Argument '{arg_name}' expected type 'string', got '{type(value).__name__}'.")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Argument '{arg_name}' expected type 'integer', got '{type(value).__name__}'.")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Argument '{arg_name}' expected type 'boolean', got '{type(value).__name__}'.")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Argument '{arg_name}' expected type 'number', got '{type(value).__name__}'.")
                elif expected_type == "array" and not isinstance(value, list):
                    errors.append(f"Argument '{arg_name}' expected type 'array', got '{type(value).__name__}'.")
                elif expected_type == "object" and not isinstance(value, dict):
                    errors.append(f"Argument '{arg_name}' expected type 'object', got '{type(value).__name__}'.")
                    
                enum_values = properties[arg_name].get("enum")
                if enum_values and value not in enum_values:
                    errors.append(f"Argument '{arg_name}' value '{value}' is not valid. Allowed: {enum_values}.")

        return errors
