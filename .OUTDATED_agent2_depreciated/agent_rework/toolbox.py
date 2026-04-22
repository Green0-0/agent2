from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any

from agent2.agent_rework.boundtool import BoundTool 
from agent2.agent_rework.agent import Agent
from agent2.agent_rework.toolresponse import ToolResponse
from agent2.agent_rework.workspace import Workspace
from agent2.agent_rework.tool import Tool

class Toolbox(ABC):
    """
    Abstract base class for a toolbox.

    A toolbox is a set of tools and a shared configuration passed to each tool call.
    Subclasses handle:
      - Parsing a string tool-message from the agent
      - Validating and executing the matching tool
      - Generating documentation and examples for tools in the format the agent expects
    """

    def __init__(self, tools: List[Tool], tool_config: Optional[Dict[str, Any]] = None) -> None:
        self.tools: List[Tool] = tools
        self.tool_config: Dict[str, Any] = tool_config or {}
        self.bound_tool: Optional[BoundTool] = None

    @abstractmethod
    def run(
        self,
        agent: Agent,
        workspace: Workspace,
        tool_message: str
    ) -> ToolResponse:
        """
        Run a tool call parsed from a string message. The string message should only contain a tool call and no other text. No excess newlines should be present. If a bound tool is present, the bound tool will override the tools list (and be discarded afterwards). If the tool returns a bound tool, this toolbox will be bound to that tool.

        Parameters
        ----------
        agent : Agent
        workspace : Workspace
        tool_message : str
            Raw string containing the tool invocation.

        Returns
        -------
        ToolResponse
        """
        raise NotImplementedError
    
    def generate_docs(self) -> List[str]:
        return [self.generate_doc(tool) for tool in self.tools]
    
    def generate_examples(self, start_wrapper: str, end_wrapper: str) -> List[str]:
        return [self.generate_example(tool, start_wrapper, end_wrapper) for tool in self.tools]

    @abstractmethod
    def generate_doc(self, tool: Tool) -> str:
        """
        Generate documentation for a tool in the specific format
        that this toolbox’s agent expects.

        Parameters
        ----------
        tool : Tool

        Returns
        -------
        str
        """
        raise NotImplementedError

    @abstractmethod
    def generate_example(
        self,
        tool: Tool,
        start_wrapper: str,
        end_wrapper: str,
        override_example: Optional[str] = None,
        override_example_args: Optional[List[str]] = None
    ) -> str:
        """
        Generate an example for how the tool would be called in the expected format.

        Result format is typically:
        {tool_example_scenario}
        {start_wrapper}
        {tool_example_json}
        {end_wrapper}

        Parameters
        ----------
        tool : Tool
        start_wrapper : str
            Prefix wrapper used in the example.
        end_wrapper : str
            Postfix wrapper used in the example.
        override_example : str
            Optional override for the example.
        override_example_args : List[str]
            Optional override for the example arguments.

        Returns
        -------
        str
        """
        raise NotImplementedError
