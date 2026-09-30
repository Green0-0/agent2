from typing import Tuple
from typing import List
import inspect
import json
from typing import Callable, Any, Dict
from abc import ABC, abstractmethod


class DescriptionBuilder(ABC):
    """Abstract base class for building a tool's description string for the OpenAI schema."""
    
    @abstractmethod
    def build(self, description: str | None, properties: Dict[str, Any], examples: List[Tuple[str, Dict[str, Any]]]) -> str:
        """
        Build the description string.
        
        Args:
            description: The base description of the tool.
            properties: A dictionary of argument names to their schema properties.
            examples: A list of (task, tool_call) examples.
            
        Returns:
            The formatted description string.
        """
        pass


class GenericDescriptionBuilder(DescriptionBuilder):
    """A generic description builder that formats the description, arguments, and examples cleanly."""
    
    def __init__(
        self, 
        args_header: str = "Args:", 
        examples_header: str = "Examples:", 
        indent: str = "    ", 
        task_prefix: str = "Task: ", 
        tool_call_prefix: str = "Tool Call: ",
        include_args: bool = True,
        include_examples: bool = True
    ):
        """
        Initialize the GenericDescriptionBuilder with custom formatting.
        
        Args:
            args_header: The header string preceding arguments.
            examples_header: The header string preceding examples.
            indent: The indentation string for block elements.
            task_prefix: The prefix string for a task description.
            tool_call_prefix: The prefix string for a tool call JSON.
            include_args: Whether to include the arguments block.
            include_examples: Whether to include the examples block.
        """
        self.args_header = args_header
        self.examples_header = examples_header
        self.indent = indent
        self.task_prefix = task_prefix
        self.tool_call_prefix = tool_call_prefix
        self.include_args = include_args
        self.include_examples = include_examples

    def build(self, description: str | None, properties: Dict[str, Any], examples: List[Tuple[str, Dict[str, Any]]]) -> str:
        parts = []
        if description:
            parts.append(description)
            parts.append("")
            
        if self.include_args and properties:
            parts.append(self.args_header)
            for arg_name, arg_data in properties.items():
                arg_desc = arg_data.get("description", "")
                parts.append(f"{self.indent}{arg_name}: {arg_desc}")
            parts.append("")
            
        if self.include_examples and examples:
            parts.append(self.examples_header)
            for task, call in examples:
                parts.append(f"{self.indent}{self.task_prefix}{task}")
                parts.append(f"{self.indent}{self.tool_call_prefix}{json.dumps(call)}")
                parts.append("")
                
        return "\n".join(parts).strip()


class Tool:
    """Thin wrapper that converts Python functions into agent tools."""

    func: Callable
    name: str
    description: str | None
    
    examples: List[Tuple[str, Dict[str, Any]]]
    
    openai_schema: Dict[str, Any]

    def __init__(self, func: Callable, description_builder: DescriptionBuilder | None = None):
        """
        Wrap func as an agent tool and build its schema.
        
        Args:
            func: The Python function to wrap.
            description_builder: An optional custom DescriptionBuilder instance. Defaults to GenericDescriptionBuilder.
        """
        self.func = func
        self.name = func.__name__

        doc = func.__doc__ or ""
        if "Args:" in doc:
            self.description = doc.split("Args:")[0].strip()
        elif "Examples:" in doc:
            self.description = doc.split("Examples:")[0].strip()
        else:
            self.description = doc.strip() or None

        self.examples = []
        if "Examples:" in doc:
            examples_section = doc.split("Examples:")[1]
            parts = examples_section.split("Task:")
            for part in parts[1:]:
                if "Tool Call:" in part:
                    task_str, call_str = part.split("Tool Call:")
                    try:
                        call_json = json.loads(call_str.strip())
                        self.examples.append((task_str.strip(), call_json))
                    except Exception as e:
                        raise ValueError(
                            f"Malformed example tool call in docstring of {func.__name__}: {e}"
                        )

        builder = description_builder or GenericDescriptionBuilder()
        self.openai_schema = self._build_openai_schema(builder)

    def __call__(self, *args, **kwargs):
        """
        Execute the underlying function.
        """
        return self.func(*args, **kwargs)

    def _build_openai_schema(self, description_builder: DescriptionBuilder) -> Dict[str, Any]:
        """
        Build an OpenAI-compatible tool schema from the function's signature and docstring.
        
        Args:
            description_builder: The DescriptionBuilder used to format the schema description.
            
        Returns:
            The final formatted OpenAI tool schema.
        """
        sig = inspect.signature(self.func)
        doc = self.func.__doc__ or ""
        desc: Dict[str, str] = {}

        for line in doc.splitlines():
            if line.strip().startswith("Args"):
                continue
            if ":" in line:
                parts = line.split(":", 1)
                if len(parts) == 2:
                    param_name, txt = parts
                    desc[param_name.strip()] = txt.strip()

        skip_names = {"agent", "agentworkspace", "agentconfig", "session"}
        
        properties = {}
        required = []

        type_map = {
            "str": "string",
            "int": "integer",
            "float": "number",
            "bool": "boolean",
            "list": "array",
            "dict": "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name.lower().replace("_", "") in skip_names:
                continue

            if hasattr(param.annotation, "__name__"):
                param_type_str = param.annotation.__name__
            else:
                param_type_str = "str"

            json_type = type_map.get(param_type_str.lower(), "string")

            properties[param_name] = {
                "type": json_type,
                "description": desc.get(param_name, "")
            }

            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        final_description = description_builder.build(self.description, properties, self.examples)

        schema = {
            "type": "function",
            "function": {
                "name": self.name,
                "description": final_description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
        
        if not required:
            schema["function"]["parameters"].pop("required")

        return schema
