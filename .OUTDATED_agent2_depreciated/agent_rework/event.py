from typing import List, Optional

class Event:
    """
    Represents an agentic event and its associated text.
    
    Attributes:
        raw_content: Unmodified source content for debugging.
        tool_content: String content for tool processing, ``None`` if no tool was used or if the event represents a tool response.
        display_content: A list of display strings, ordered by the amount of truncation applied.
    """
    
    def __init__(
        self, 
        *display_args: str,
        raw_content: str = None, 
        tool_content: str = None,
    ) -> None:
        """
        Initialize an Event with content in different formats.
        
        Args:
            raw_content: Unmodified source content for debugging, defaults to the first element of ``display_args``.
            tool_content: String content for tool processing, ``None`` if no tool was used or if the event represents a tool response.
            *display_args: Variable number of string arguments that become display_content.
                          At least one ``display_args`` must be provided.
        
        Raises:
            ValueError: If display_args is empty
        """
        if not display_args:
            raise ValueError("At least one display_args must be provided")
        
        self.raw_content: str = display_args[0] if raw_content is None else raw_content
        self.tool_content: str = tool_content
        
        self.display_content: List[str] = list(display_args)
    
    def wrap_display(self, wrapper: str, key: str) -> None:
        """
        Wrap each element of display_content using a template wrapper.
        
        This method substitutes each display content element into the wrapper template
        by replacing the specified key placeholder.
        
        Args:
            wrapper: Template string containing the key placeholder (e.g., "Result: {{content}}")
            key: The placeholder key to replace (e.g., "{{content}}")
        
        Example:
            If display_content = ["hello", "world"] and wrapper = "Message: {{text}}" 
            with key = "{{text}}", the display_content becomes:
            ["Message: hello", "Message: world"]
        """
        # Apply the wrapper template to each display content element
        wrapped_content = []
        for content in self.display_content:
            wrapped_content.append(wrapper.replace(key, content))
        
        self.display_content = wrapped_content

    def decay(self) -> Optional[str]:
        """
        If there is more than one element in display_content, remove the first.
        
        Because successive elements of display_content should be shorter, this will decrease the amount of tokens the event occupies.
        
        Returns:
            The removed element, or None
        """
        if len(self.display_content) > 1:
            return self.display_content.pop(0)
        return None
    
    def __str__(self) -> str:
        """
        Return the string representation of the Event.
        
        Returns:
            The first element of display_content
        """
        return self.display_content[0]
    
    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.
        
        Returns:
            A string showing the Event's internal state
        """
        return (f"Event(display_content={self.display_content}, "
                f"tool_content='{self.tool_content}', "
                f"raw_source_content='{self.raw_content}')")
