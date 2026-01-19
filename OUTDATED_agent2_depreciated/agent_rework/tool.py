import json
import inspect
from typing import Callable, List, Tuple, Dict, Any, Union

from agent2.agent_rework.agent import Agent
from agent2.agent_rework.workspace import Workspace


class Tool:
    """
    Thin wrapper that turns an ordinary Python function into an *agent tool*.

    A tool is simply a call-target the LLM can invoke.  The wrapper extracts a
    JSON schema (argument names, types, descriptions) from the wrapped
    function’s signature + docstring so that the agent can validate and route
    tool-calls at runtime.

    Attributes
    ----------
    func            : Callable
        The underlying Python function executed when the tool is invoked.
        It **must** accept the leading arguments  
        ``(agent, agent_workspace, agent_config, *tool_args)``
        It must also return a tuple ``(List[str], BoundTool|None, Agent|None)
    name            : str
        `func.__name__`.
    description     : str | None
        Plain-language summary extracted from the docstring (text before the
        “Args:” section).  ``None`` if the function has no docstring.
    required_args   : List[Tuple[str, str, str]]
        ``(param, description, type)`` triples for parameters **without**
        defaults.
    optional_args   : List[Tuple[str, str, str]]
        Same structure as ``required_args`` but for parameters **with**
        defaults.
    example_task    : str | None
        Free-form example task description found under the “Example:” stanza.
    example_tool_call : dict | None
        Parsed JSON representing the example call supplied in the docstring, after the "Tool Call:" stanza.

    Notes
    -----
    * The parameter list is scanned **after** the three agent-specific leading
      parameters ``agent``, ``agent_workspace`` and ``agent_config``.  Those
      are *never* exposed to the LLM.
    * Valid primitive type strings are: ``str, int, float, bool, list, dict``.
    """

    func: Callable
    name: str
    description: str | None

    optional_args: List[Tuple[str, str, str]]
    required_args: List[Tuple[str, str, str]]

    example_task: str | None
    example_tool_call: Dict[str, Any] | None

    def __init__(self, func: Callable):
        """
        Wrap *func* as an agent tool and build its schema.
        """
        self.func = func
        self.name = func.__name__

        doc = func.__doc__ or ""
        if "Args" in doc:
            self.description = doc.split("Args")[0].strip()
        else:
            self.description = doc.strip() or None

        if "Example:" in doc and "Tool Call:" in doc:
            try:
                example_body, example_json = doc.split("Example:")[1].split(
                    "Tool Call:"
                )
                self.example_task = example_body.strip()
                self.example_tool_call = json.loads(example_json.strip())
            except Exception:
                raise ValueError(
                    f"Malformed example tool call in docstring of {func.__name__}"
                )
        else:
            self.example_task = None
            self.example_tool_call = None

        self.optional_args, self.required_args = self._get_args(func)

    def __call__(self, agent: Agent, workspace: Workspace, *args, **kwargs):
        """
        Execute the underlying function.
        """
        return self.func(agent, workspace, *args, **kwargs)

    def match(self, json_call: dict) -> Union[Tuple[List[str], List[str], List[str]], None]:
        """
        Validate a JSON tool call against the tool's argument schema.

        Returns
        -------
        None  – if the call is fully valid
        (missing, extra, faulty) – otherwise
        """
        # --------------------------------------------------------------- #
        # Build look-up tables
        # --------------------------------------------------------------- #
        required_map = {n: (d, t) for n, d, t in self.required_args}
        optional_map = {n: (d, t) for n, d, t in self.optional_args}
        allowed      = {**required_map, **optional_map}

        provided: Dict[str, Any] = json_call.get("arguments", {})
        provided_keys            = set(provided)

        # --------------------------------------------------------------- #
        # Missing required
        # --------------------------------------------------------------- #
        missing = [
            f"{name}: {required_map[name][0]}"
            for name in required_map
            if name not in provided_keys
        ]

        # --------------------------------------------------------------- #
        # Extra / unknown
        # --------------------------------------------------------------- #
        extra = [k for k in provided_keys if k not in allowed]

        # --------------------------------------------------------------- #
        # Type checking
        # --------------------------------------------------------------- #
        py_type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
        }
        faulty: List[str] = []
        for name in provided_keys & set(allowed):
            expected_type = allowed[name][1].lower()
            actual_val    = provided[name]

            # int is allowed when float expected
            if expected_type == "float" and isinstance(actual_val, int):
                continue

            if expected_type == "bool":
                if not isinstance(actual_val, bool):
                    faulty.append(f"{name}: expected bool, got {type(actual_val).__name__}")
                continue

            if not isinstance(actual_val, py_type_map.get(expected_type, str)):
                faulty.append(f"{name}: expected {expected_type}, got {type(actual_val).__name__}")

        return (missing, extra, faulty) if any((missing, extra, faulty)) else None

    @staticmethod
    def _get_args(func: Callable) -> Tuple[
        List[Tuple[str, str, str]], List[Tuple[str, str, str]]
    ]:
        """
        Build ``optional_args`` and ``required_args`` from *func*'s signature.
        The first occurrence of **agent**, **agent_workspace**, **agent_config**
        (in that order) is silently ignored – they are framework internals and
        never shown to the LLM.
        """
        sig  = inspect.signature(func)
        doc  = func.__doc__ or ""
        desc: Dict[str, str] = {}

        # Grab per-parameter description lines from docstring
        for line in doc.splitlines():
            if line.strip().startswith("Args"):
                continue
            if ":" in line:
                name, txt = line.split(":", 1)
                desc[name.strip()] = txt.strip()

        skip_names = {"agent", "agentworkspace", "agentconfig"}
        optional_args, required_args = [], []

        for name, param in sig.parameters.items():
            if name.lower().replace("_", "") in skip_names:
                continue

            # Fallback to `str` if type annotation is missing / complex
            if hasattr(param.annotation, "__name__"):
                param_type = param.annotation.__name__
            else:
                param_type = "str"

            entry = (name, desc.get(name, ""), param_type)
            if param.default is inspect.Parameter.empty:
                required_args.append(entry)
            else:
                optional_args.append(entry)

        return optional_args, required_args