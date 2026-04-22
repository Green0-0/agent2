import json
from agent2.agent.tool import Tool
import re 

class ToolFormatter:
    def __init__(self, tool_start: str = "<tool_call>", tool_end: str = "</tool_call>"):
        self.tool_start = tool_start
        self.tool_end = tool_end

    def string_to_json(self, input: str):
        pass

    def json_to_string(self, j: dict):
        pass

    def tool_to_string(self, tool: Tool):
        pass

class JSONToolFormatter(ToolFormatter):
    def string_to_json(self, input: str):
        loaded = json.loads(input)
        if not isinstance(loaded, dict):
            raise ValueError("Expected JSON tool all, got:" + str(type(loaded).__name__))
        return loaded
    
    def json_to_string(self, j: dict):
        return json.dumps(j)
    
    def tool_to_string(self, tool: Tool) -> str:
        """Convert a Tool to a JSON function definition schema."""
        # Map Python types to JSON schema types
        type_mapping = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object"
        }

        # Build parameters schema
        parameters = {
            "type": "object",
            "properties": {},
            "required": [arg[0] for arg in tool.required_args]
        }

        # Process all arguments (required + optional)
        for arg in tool.required_args + tool.optional_args:
            name, description, param_type = arg
            
            # Handle enum types (special case)
            if param_type.startswith("enum:"):
                enum_values = param_type.split(":", 1)[1].split(",")
                param_schema = {
                    "type": "string",
                    "description": description,
                    "enum": enum_values
                }
            else:
                param_schema = {
                    "type": type_mapping.get(param_type.lower(), "string"),
                    "description": description
                }

                # Add array/object structure if needed
                if param_type.lower() == "array":
                    param_schema["items"] = {"type": "string"}  # Default array items
                elif param_type.lower() == "object":
                    param_schema["properties"] = {}  # Default empty object

            parameters["properties"][name] = param_schema

        # Build full schema
        function_schema = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description.strip(),
                "parameters": parameters
            }
        }

        return f"{self.tool_start}\n" + json.dumps(function_schema) + f"\n{self.tool_end}"

class XMLToolFormatter(ToolFormatter):
    def string_to_json(self, input: str) -> dict:
        """Convert XML tool call to JSON with strict validation.
        
        Raises:
            ValueError: For any XML format errors, duplicate arguments, or unclosed tags
            KeyError: If name tag is missing or not the first element
        """
        def unescape_xml(text: str) -> str:
            replacements = {
                "&amp;": "&",
                "&lt;": "<",
                "&gt;": ">",
                "&quot;": "\"",
                "&apos;": "'"
            }
            for esc, char in replacements.items():
                text = text.replace(esc, char)
            return text

        def parse_value(s: str):
            s = s.strip()
            try:
                return int(s)
            except ValueError:
                try:
                    return float(s)
                except ValueError:
                    if s.lower() in ("true", "false"):
                        return s.lower() == "true"
                    return s

        input = input.strip()
        if not input:
            raise ValueError("Empty XML input")

        # Find all XML elements with their content
        elements = re.findall(r"<([a-zA-Z0-9_]+)>(.*?)</\1>", input, re.DOTALL)
        
        # Check for unclosed tags or invalid content
        stripped = re.sub(r"<([a-zA-Z0-9_]+)>(.*?)</\1>", "", input, flags=re.DOTALL).strip()
        if stripped:
            raise ValueError(f"Invalid XML structure or unclosed tag in: {stripped}")

        if not elements:
            raise ValueError("No valid XML elements found")

        # Validate first element is the name tag
        name_tag, name_content = elements[0]
        if name_tag != "name":
            raise KeyError("First element must be <name>")
        name_value = unescape_xml(name_content.strip())
        if not name_value:
            raise ValueError("Name value cannot be empty")

        result = {"name": name_value, "arguments": {}}

        # Process each argument element
        seen_tags = set()
        for tag, content in elements[1:]:
            if tag in seen_tags:
                raise ValueError(f"Duplicate argument '{tag}'")
            seen_tags.add(tag)
            
            cleaned = parse_value(unescape_xml(content))
            result["arguments"][tag] = cleaned

        return result
    
    def json_to_string(self, j: dict):
        """
        Converts the given JSON to an XML string representation.

        The input JSON should contain a "name" key for the tool name and an
        "arguments" key containing a dictionary of argument names to values.
        
        one line for each argument in the format:
        <argument_name>value</argument_name>
        """
        xml_lines = [f"<name>{j['name']}</name>"]
    
        # Process arguments
        for arg_name, arg_value in j.get('arguments', {}).items():
            # Convert values to strings and escape XML-sensitive characters
            str_value = str(arg_value)
            str_value = (str_value.replace("&", "&amp;")
                                .replace("<", "&lt;")
                                .replace(">", "&gt;"))
            xml_lines.append(f"<{arg_name}>{str_value}</{arg_name}>")
        
        return '\n'.join(xml_lines)
    
    def tool_to_string(self, tool: Tool) -> str:
        """Converts the tool to an XML string representation."""
        xml_lines = [
            f"<name>{tool.name}</name>",
            f"<description>{tool.description}</description>"
        ]
        
        # Process required arguments
        for name, desc, type_ in tool.required_args:
            content = f"Required ({type_}): {desc}" if desc else f"Required: ({type_})"
            xml_lines.append(f"<{name}>{content}</{name}>")
        
        # Process optional arguments
        for name, desc, type_ in tool.optional_args:
            content = f"Optional ({type_}): {desc}" if desc else f"Optional: ({type_})"
            xml_lines.append(f"<{name}>{content}</{name}>")
        
        return f"{self.tool_start}\n" + '\n'.join(xml_lines) + f"\n{self.tool_end}"

import inspect
from agent2.parsing.parser import extract_codeblock

class CodeACTToolFormatter(ToolFormatter):
    def tool_to_string(self, tool: Tool) -> str:
        tool_doc = tool.func.__doc__
        if "Example:" in tool_doc:
            tool_doc = tool_doc.split("Example:")[0].strip()
        tool_signature = str(inspect.signature(tool.func))
        index1 = tool_signature.find("settings")
        index2 = tool_signature.find(",", index1)
        tool_signature = "def " + tool.name + "(" + tool_signature[index2 + 1:].strip()
        return f"{self.tool_start}\n```python\n" + tool_signature + "\n\"\"\"\n" + tool_doc + "\n\"\"\"\n```\n" + self.tool_end

    def json_to_string(self, j: dict):
        """Convert JSON tool call to CodeACT format (Python function call syntax).
        
        Example:
            {"name": "replace_block", "arguments": {"path": "a.txt", "block": "text"}}
            becomes:
            replace_block(path="a.txt", block="text")
        """
        name = j.get("name", "")
        arguments = j.get("arguments", {})
        
        args = []
        for key, value in arguments.items():
            if isinstance(value, str):
                # Escape double quotes and newlines
                escaped = (value.replace('"', r'\"')
                              .replace('\n', r'\n'))
                args.append(f'{key}="{escaped}"')
            elif isinstance(value, bool):
                args.append(f"{key}={str(value).lower()}")
            else:
                args.append(f"{key}={repr(value)}")
                
        return f"```python\n{name}({', '.join(args)})\n```"

    def string_to_json(self, input: str):
        return extract_codeblock(input)
    
class MarkdownToolFormatter(ToolFormatter):
    def __init__(self, tool_start: str = "# Tool Use", tool_end: str = "# Tool End"):
        super().__init__(tool_start, tool_end)

    def string_to_json(self, input: str) -> dict:
        """Convert a Markdown-formatted tool call to JSON with validation.
        
        Raises:
            ValueError: For invalid Markdown structure or content
            KeyError: If name is missing or parameters are malformed
        """
        content = input.strip()
        
        lines = [line for line in content.split('\n')]
        anyLines = False
        for line in lines:
            if len(line) > 0:
                anyLines = True
        if not lines:
            raise ValueError("Empty tool call content")

        # Parse tool name
        if not lines[0].startswith('## Name: '):
            raise KeyError("First line must be '## Name: [tool_name]'")
        name = lines[0][len('## Name: '):].strip()
        result = {"name": name, "arguments": {}}

        current_param = None
        current_value = []

        for line in lines[1:]:
            if line.startswith('### '):
                if current_param is not None:
                    # Save the previous parameter
                    value_str = '\n'.join(current_value).strip()
                    parsed_value = self.parse_value(value_str)
                    result['arguments'][current_param] = parsed_value
                    current_value = []
                
                # Parse new parameter
                param_line = line[len('### '):]
                if ':' not in param_line:
                    raise ValueError(f"Parameter line missing colon: {line}")
                param_name, param_value = param_line.split(':', 1)
                current_param = param_name.strip()
                current_value.append(param_value)
                # Check for duplicate parameters
                if current_param in result['arguments']:
                    raise ValueError(f"Duplicate parameter: {current_param}")
            else:
                if current_param is None:
                    raise ValueError(f"Line '{line}' is not part of any parameter")
                current_value.append(line)
        
        # Add the last parameter
        if current_param is not None:
            value_str = '\n'.join(current_value).strip()
            parsed_value = self.parse_value(value_str)
            result['arguments'][current_param] = parsed_value

        return result

    def json_to_string(self, j: dict) -> str:
        """Convert a JSON tool call to Markdown format."""
        lines = []
        lines.append(f"## Name: {j['name']}")
        
        for arg_name, arg_value in j.get('arguments', {}).items():
            # Convert value to string and escape XML entities
            str_value = str(arg_value)
            parts = str_value.split('\n')
            
            # First part after colon, remaining parts as separate lines
            lines.append(f"### {arg_name}: {parts[0]}")
            for part in parts[1:]:
                lines.append(part)
        
        return '\n'.join(lines)

    def tool_to_string(self, tool: Tool) -> str:
        """Generate Markdown documentation for the tool."""
        lines = [
            f"## Name: {tool.name}",
        ]
        if tool.description:
            lines.append(f"### Description: {tool.description}")
        
        # Required parameters
        for name, desc, type_ in tool.required_args:
            lines.append(f"### {name} ({type_}, required): {desc}")
        
        # Optional parameters
        for name, desc, type_ in tool.optional_args:
            lines.append(f"### {name} ({type_}, optional): {desc}")
        
        return f"{self.tool_start}\n" + '\n'.join(lines) + f"\n{self.tool_end}"

    def parse_value(self, s: str):
        """Convert string to appropriate type (int, float, bool, or str)."""
        stripped = s.strip()
        if stripped.lower() in ("true", "false"):
            return stripped.lower() == "true"
        try:
            return int(s)
        except ValueError:
            try:
                return float(s)
            except ValueError:
                return s