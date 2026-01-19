from typing import List, Dict, Any
from agent2.tool_api.abc.tool_schema_builder import ToolSchemaBuilder

class MDToolSchemaBuilder(ToolSchemaBuilder):
    """
    Builds Markdown schema definitions for tools.
    """
    def __init__(self, tool_start: str = "# Tool Use", tool_end: str = "# Tool End"):
        self.tool_start = tool_start
        self.tool_end = tool_end

    def build(self, tool_schema_json: List[Dict]) -> str:
        """
        Builds a tool schema string from a list of tool schema dictionaries.
        
        Args:
            tool_schema_json (List[Dict]): List of tool definitions.
            
        Returns:
            str: The Markdown formatted schema string.
        """
        schemas = []
        for tool in tool_schema_json:
            # Handle OpenAI format where the tool definition is inside "function"
            if "function" in tool:
                func = tool["function"]
            else:
                func = tool
            
            name = func.get("name", "")
            description = func.get("description", "")
            parameters = func.get("parameters", {})
            properties = parameters.get("properties", {})
            required = parameters.get("required", [])
            
            lines = [
                f"## Name: {name}",
            ]
            if description:
                lines.append(f"### Description: {description}")
            
            # Process arguments
            for prop_name, prop_def in properties.items():
                prop_type = prop_def.get("type", "string")
                prop_desc = prop_def.get("description", "")
                
                is_required = prop_name in required
                req_str = "required" if is_required else "optional"
                
                # Format: ### arg_name (type, required/optional): description
                content = f"### {prop_name} ({prop_type}, {req_str}): {prop_desc}"
                lines.append(content)
            
            schema = f"{self.tool_start}\n" + "\n".join(lines) + f"\n{self.tool_end}"
            schemas.append(schema)
            
        return "\n\n".join(schemas)
