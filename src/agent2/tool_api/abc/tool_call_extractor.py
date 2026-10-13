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
    """Parse assistant text, structured tool calls, and errors from a model response."""
    
    @abstractmethod
    def extract(self, response_str: str) -> Tuple[str, List[Dict], List[ToolError]]:
        """Extract structured tool calls and assistant text from a response string.

        On successful block parsing, assistant text is the stripped prefix before
        the first tool block; text after that point is omitted. If no tool block
        is found, return the original response with empty call and error lists.
        On an extraction error, return the original response, an empty call list,
        and the errors.

        Args:
            response_str (str): The raw model response to parse.
            
        Returns:
            Tuple[str, List[Dict], List[ToolError]]: Assistant content text,
                extracted tool call dictionaries, and extraction errors.
        """
        pass
