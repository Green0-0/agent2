from abc import ABC, abstractmethod
from typing import List, Dict, Tuple
from enum import Enum

class ToolError(Enum):
    TOOL_START_MISSING = 1
    TOOL_END_MISSING = 2
    TOOL_MALFORMATTED = 3
    TOOL_DUPLICATE_ARGUMENT = 4

class DuplicateArgumentError(Exception):
    """Raised when a tool call contains duplicate arguments."""
    pass

class ToolCallExtractor(ABC):
    """The ToolCallExtractor parses the message and tool call from the response string, along with errors, if applicable."""
    
    @abstractmethod
    def extract(self, response_str: str) -> Tuple[str, List[Dict], List[ToolError]]:
        """Extracts a tool call string from a tool call list.
        In the event of an extraction error, the tool will be left blank and the message string will contain the partially complete tool.

        Args:
            response_str (str): The response string to extract the tool call from.
            
        Returns:
            Tuple[str, List[Dict], List[ToolError]]: A tuple containing the tool call string, a list of tool call dictionaries, and a list of tool errors.
        """
        pass