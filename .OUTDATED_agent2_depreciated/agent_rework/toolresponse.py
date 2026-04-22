from agent2.agent_rework.event import Event
from typing import Optional

class ToolResponse:
    """
    Container for the result of a tool execution.

    Attributes
    ----------
    event : Event
        Event containing the execution output. `tool_content` is None.
        `display_content` is the list returned by the tool, or an error message list.
    error : Optional[str]
        Error message if execution failed.
    """
    def __init__(self, event: Event, error: Optional[str] = None) -> None:
        """
        Create a ToolResponse from an Event and an optional error message.

        Parameters
        ----------
        event : Event
            Event containing the execution output. `tool_content` is None.
            `display_content` is the list returned by the tool, or an error message list.
        error : Optional[str]
            Error message if execution failed, or None if no error occurred.
        """
        self.event = event
        self.error = error

    def __repr__(self) -> str:
        return f"ToolResponse(event={self.event!r}, error={self.error!r})"