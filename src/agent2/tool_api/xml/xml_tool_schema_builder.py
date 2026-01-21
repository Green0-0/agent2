from typing import List, Dict, Any
from agent2.tool_api.abc.tool_schema_builder import ToolSchemaBuilder

class XMLToolSchemaBuilder(ToolSchemaBuilder):
    """
    Builds XML schema definitions for tools.
    """
    def build(self, tool_schema_json: List[Dict]) -> List[str]:
        """
        Builds a tool schema string from a list of tool schema dictionaries.
        
        Args:
            tool_schema_json (List[Dict]): List of tool definitions (OpenAI function format).
            
        Returns:
            List[str]: The list of XML formatted schema strings.
        """
        schemas = []
        for tool in tool_schema_json:
            # Handle OpenAI format where the tool definition is inside "function"
            if "function" in tool:
                func = tool["function"]
            else:
                func = tool
            
            name = func["name"]
            description = func.get("description", "No description specified.")
            parameters = func.get("parameters", {})
            properties = parameters.get("properties", {})
            required = parameters.get("required", [])
            
            xml_lines = [
                f"<name>{name}</name>",
                f"<description>{description}</description>"
            ]
            
            # Process arguments
            for prop_name, prop_def in properties.items():
                prop_type = prop_def.get("type", "string")
                prop_desc = prop_def.get("description", "")
                
                is_required = prop_name in required
                req_str = "Required" if is_required else "Optional"
                
                # Format: <arg_name>Required (type): description</arg_name>
                content = f"{req_str} ({prop_type})"
                if prop_desc:
                    content += f": {prop_desc}"
                
                xml_lines.append(f"<{prop_name}>{content}</{prop_name}>")
            
            schema = "\n".join(xml_lines)
            schemas.append(schema)
            
        return schemas
