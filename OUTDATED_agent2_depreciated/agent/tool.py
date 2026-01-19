import json
from typing import Callable, Dict, List, Tuple
import inspect

from agent2.agent.tool_settings_depreciated import ToolSettings
from agent2.agent.agent_state import AgentState

class Tool:
    """Class representing a tool wrapping a function"""

    func: Callable = None
    name: str = None
    description: str = None

    # Name, description, type 
    optional_args: List[Tuple[str, str, str]] = []
    required_args: List[Tuple[str, str, str]] = []
    
    # Example (optional)
    example_task: str = None
    example_tool_call: dict = None

    def __call__(self, state: AgentState, settings: ToolSettings, *args, **kwargs):
        """Call the tool function with all_files"""
        return self.func(state, settings, *args, **kwargs)

    def match(self, json_call: dict) -> Tuple[List[str], List[str], List[str]]:
        """Validate a JSON tool call against the tool's requirements.
        
        Returns:
            None if valid, otherwise tuple containing:
            - Missing required args (with descriptions)
            - Extra unrecognized args 
            - Type-mismatched args (with expected/actual types)
        """
        # Get argument specifications
        required_params = {arg[0]: (arg[1], arg[2]) for arg in self.required_args}
        optional_params = {arg[0]: (arg[1], arg[2]) for arg in self.optional_args}
        allowed_params = {**required_params, **optional_params}
        provided_args = json_call.get('arguments', {})
        provided_keys = set(provided_args.keys())
        allowed_keys = set(allowed_params.keys())
        # Check missing required parameters
        missing = [
            f"{name}: {required_params[name][0]}" 
            for name in required_params 
            if name not in provided_keys
        ]

        # Identify extra parameters
        extra = [
            name for name in provided_keys
            if name not in allowed_keys
        ]
        # Validate parameter types
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict
        }
        faulty = []
        for name in provided_keys & allowed_keys:  # Only check valid params
            expected_type_str = allowed_params[name][1].lower()
            value = provided_args[name]
            
            # Handle special cases for numeric types
            if expected_type_str == "float" and isinstance(value, int):
                continue  # Allow int as float
            
            # Handle bool type checking strictly
            if expected_type_str == "bool":
                if not isinstance(value, bool):
                    actual_type = type(value).__name__
                    faulty.append(f"{name}: expected bool, got {actual_type}")
                continue
                
            # Check remaining types
            expected_type = type_map.get(expected_type_str, str)
            if not isinstance(value, expected_type):
                actual_type = type(value).__name__
                faulty.append(f"{name}: expected {expected_type_str}, got {actual_type}")
        return (missing, extra, faulty) if any([missing, extra, faulty]) else None

    
    def __init__(self, func: Callable):
        """
        Initialize tool with function and automatically generate schema
        
        Args:
            func: The tool function
        """
        self.func = func
        self.name = func.__name__
        if func.__doc__ is not None:
            self.description = func.__doc__.split("Args")[0].strip()
            if "Example:" in func.__doc__:
                example_parts = func.__doc__.split("Example:")[1].split("Tool Call:")
                try:
                    self.example_tool_call = json.loads(example_parts[1].strip())
                    self.example_task = example_parts[0].strip()
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON in example tool call: {e}")
        
        self.optional_args, self.required_args = self._get_args(func)
        
    def _get_args(self, func: Callable) -> Tuple[List[Tuple[str, str, str]], List[Tuple[str, str, str]]]:
        sig = inspect.signature(func)
        optional_args = []
        required_args = []

        docstring = func.__doc__ or ""
        param_descriptions = {}
        for line in docstring.split("\n"):
            if line.strip().startswith("Args:"):
                continue
            if ":" in line and line.strip().startswith(tuple(sig.parameters.keys())):
                param_name = line.split(":")[0].strip()
                param_desc = ":".join(line.split(":")[1:]).strip()
                param_descriptions[param_name] = param_desc

        skip = 2 if len(sig.parameters.items()) > 1 else 0
        for name, param in sig.parameters.items():
            if skip > 0:
                skip -= 1
                continue
            # Get parameter type`
            param_type = param.annotation.__name__
            if param.default == inspect.Parameter.empty:
                required_args.append((name, param_descriptions.get(name, ""), param_type))
            else:
                optional_args.append((name, param_descriptions.get(name, ""), param_type))
        return optional_args, required_args