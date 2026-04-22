import json
from typing import Dict, List, Optional, Any
from agent2.agent_rework.toolbox import Toolbox
from agent2.agent_rework.toolresponse import ToolResponse
from agent2.agent_rework.event import Event
from agent2.agent_rework.tool import Tool
from agent2.agent_rework.agent import Agent
from agent2.agent_rework.workspace import Workspace


class JSONToolbox(Toolbox):
    """
    A toolbox that processes tool calls in JSON format.
    
    Expected JSON format:
    {
        "name": "tool_name",
        "arguments": {
            "arg1": "value1",
            "arg2": "value2"
        }
    }
    """

    def run(
        self,
        agent: Agent,
        workspace: Workspace,
        tool_message: str
    ) -> ToolResponse:
        try:
            # Check if we have a bound tool (overrides tools list)
            if self.bound_tool is not None:
                bound_tool = self.bound_tool
                self.bound_tool = None  # Clear the bound tool
                
                try:
                    # Execute the bound tool
                    result = bound_tool.tool(agent, workspace, self.tool_config)
                    # result should be (List[str], Optional[BoundTool], Optional[Agent])
                    outputs, new_bound_tool, _ = result
                    if new_bound_tool:
                        self.bound_tool = new_bound_tool
                    
                    # Convert strings to Events
                    events = [Event(output, tool_content=None) for output in outputs]
                    return ToolResponse(events=events, error=None)
                    
                except Exception as e:
                    error_msg = f"Tool error: {str(e)}"
                    event = Event(error_msg, tool_content=None)
                    return ToolResponse(events=[event], error=e)
            
            # Parse JSON tool call
            try:
                tool_call = json.loads(tool_message.strip())
                if not isinstance(tool_call, dict):
                    raise ValueError(f"Expected JSON object, got {type(tool_call).__name__}")
            except (json.JSONDecodeError, ValueError) as e:
                error_msg = f"Malformatted tool: {str(e)}"
                event = Event(error_msg, tool_content=None)
                return ToolResponse(events=[event], error=e)
            
            # Extract tool name
            tool_name = tool_call.get("name")
            if not tool_name:
                error_msg = "Malformatted tool: missing 'name' field"
                event = Event(error_msg, tool_content=None)
                return ToolResponse(events=[event], error=ValueError("Missing tool name"))
            
            # Find matching tool
            matched_tool = None
            for tool in self.tools:
                if tool.name == tool_name:
                    matched_tool = tool
                    break
            
            if matched_tool is None:
                # Try to find similar tools
                lookup_keys = tool_name.split(" ") + tool_name.split("_")
                lookup_keys = [k.lower() for k in lookup_keys if k]
                
                closest_tool = None
                # First pass: check tool names
                for tool in self.tools:
                    if any(k in tool.name.lower() for k in lookup_keys):
                        closest_tool = tool
                        break
                
                # Second pass: check descriptions and examples
                if closest_tool is None:
                    for tool in self.tools:
                        desc = (tool.description or "").lower()
                        task = (tool.example_task or "").lower()
                        args_str = str(tool.required_args + tool.optional_args).lower()
                        if any(k in desc or k in task or k in args_str for k in lookup_keys):
                            closest_tool = tool
                            break
                
                if closest_tool:
                    error_msg = f"Tool not found: did you mean {closest_tool.name}?"
                else:
                    tool_names = [t.name for t in self.tools]
                    error_msg = f"Tool not found: Available tools: {', '.join(tool_names)}"
                
                event = Event(error_msg, tool_content=None)
                return ToolResponse(events=[event], error=ValueError(f"Tool not found: {tool_name}"))
            
            # Validate arguments
            args_errors = matched_tool.match(tool_call)
            if args_errors is not None:
                missing, extra, faulty = args_errors
                error_parts = []
                if faulty:
                    error_parts.append(f"Wrong arguments: {', '.join(faulty)}")
                if missing:
                    error_parts.append(f"Missing arguments: {', '.join(missing)}")
                if extra:
                    error_parts.append(f"Unrecognized arguments: {', '.join(extra)}")
                
                error_msg = " ".join(error_parts)
                event = Event(error_msg, tool_content=None)
                return ToolResponse(events=[event], error=ValueError("Argument validation failed"))
            
            # Execute tool
            try:
                arguments = tool_call.get("arguments", {})
                result = matched_tool(agent, workspace, self.tool_config, **arguments)
                
                # result should be (List[str], Optional[BoundTool], Optional[Agent])
                outputs, new_bound_tool, _ = result
                if new_bound_tool:
                    self.bound_tool = new_bound_tool
                
                # Convert strings to Events
                events = [Event(output, tool_content=None) for output in outputs]
                return ToolResponse(events=events, error=None)
                
            except Exception as e:
                error_msg = f"Tool error: {str(e)}"
                event = Event(error_msg, tool_content=None)
                return ToolResponse(events=[event], error=e)
                
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Tool error: {str(e)}"
            event = Event(error_msg, tool_content=None)
            return ToolResponse(events=[event], error=e)

    def generate_doc(self, tool: Tool) -> str:
        """
        Generate JSON schema documentation for a tool.
        """
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
                    "enum": [v.strip() for v in enum_values]
                }
            else:
                param_schema = {
                    "type": type_mapping.get(param_type.lower(), "string"),
                    "description": description
                }

                # Add array/object structure if needed
                if param_type.lower() == "list":
                    param_schema["items"] = {"type": "string"}  # Default array items
                elif param_type.lower() == "dict":
                    param_schema["properties"] = {}  # Default empty object

            parameters["properties"][name] = param_schema

        # Build full schema
        function_schema = {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "No description available",
                "parameters": parameters
            }
        }

        return json.dumps(function_schema, indent=2)

    def generate_example(
        self,
        tool: Tool,
        start_wrapper: str,
        end_wrapper: str,
        override_example: Optional[str] = None,
        override_example_args: Optional[List[str]] = None
    ) -> str:
        """
        Generate an example for how the tool would be called in JSON format.
        """
        # Validate overrides
        if (override_example is None) != (override_example_args is None):
            raise ValueError("Both override_example and override_example_args must be provided together, or neither")
        
        # Use overrides if provided
        if override_example is not None and override_example_args is not None:
            example_task = override_example
            # Convert override_example_args to a tool call format
            example_call = {
                "name": tool.name,
                "arguments": {}
            }
            if override_example_args:
                for i, arg in enumerate(tool.required_args + tool.optional_args):
                    if i < len(override_example_args):
                        example_call["arguments"][arg[0]] = override_example_args[i]
        else:
            # Use tool's built-in example
            if tool.example_task is None or tool.example_tool_call is None:
                raise ValueError(f"Tool {tool.name} lacks an example and no overrides provided")
            
            example_task = tool.example_task
            example_call = {
                "name": tool.name,
                "arguments": tool.example_tool_call
            }
        
        # Format the example
        example_json = json.dumps(example_call, indent=2)
        
        return f"{example_task}\n{start_wrapper}\n{example_json}\n{end_wrapper}"
