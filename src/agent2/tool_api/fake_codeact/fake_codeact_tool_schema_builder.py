from typing import List, Dict, Any
from agent2.tool_api.abc.tool_schema_builder import ToolSchemaBuilder

class FakeCodeActToolSchemaBuilder(ToolSchemaBuilder):
    """
    Builds a tool schema string for the Fake CodeAct format.
    The schema presents tools as Python functions.
    """
    def build(self, tool_schema_json: List[Dict]) -> List[str]:
        """
        Builds a tool schema string from a tool schema list.
        
        Args:
            tool_schema_json (List[Dict]): The tool schema list.
            
        Returns:
            List[str]: The list of tool schema strings.
        """
        schemas = []
        
        for tool in tool_schema_json:
            if tool.get("type") != "function":
                continue
                
            func = tool.get("function", {})
            name = func.get("name")
            description = func.get("description", "")
            parameters = func.get("parameters", {})
            properties = parameters.get("properties", {})
            required = parameters.get("required", [])
            
            # Build arguments string
            args_parts = []
            for prop_name, prop_def in properties.items():
                prop_type = prop_def.get("type", "any")
                # Map JSON types to Python types roughly
                type_map = {
                    "string": "str",
                    "integer": "int",
                    "number": "float",
                    "boolean": "bool",
                    "array": "list",
                    "object": "dict"
                }
                py_type = type_map.get(prop_type, "Any")
                
                arg_str = f"{prop_name}: {py_type}"
                if prop_name not in required:
                    arg_str += " = None"
                args_parts.append(arg_str)
                
            args_str = ", ".join(args_parts)
            
            schema_lines = []
            schema_lines.append(f"def {name}({args_str}):")
            if description:
                schema_lines.append(f"    \"\"\"{description}\"\"\"")
            schema_lines.append("    ...")
            
            schemas.append("\n".join(schema_lines))
        
        return schemas
