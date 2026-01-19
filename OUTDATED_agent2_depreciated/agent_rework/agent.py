from typing import List, Optional, Tuple, Dict, Union

from agent2.agent_rework.event import Event
from agent2.agent_rework.file import File
from agent2.agent_rework.element import Element
from agent2.agent_rework.interaction import Interaction

class Agent:
    """
    Core orchestrator that turns *memories* and *history* into OpenAI messages,
    parses model output for tool calls, and stores resulting events.

    Attributes
    ----------
    system_message : str
        Template shown to the LLM before any user / assistant turns.
        May contain keys that are replaced by ``build_input``, e.g. "{{files}}".
    start_message  : str
        Very first assistant message; may also contain replacement keys, e.g. "{{usermessage}}".
    tool_start_tag : str
        Marker that precedes a tool-call block, e.g. "<tool>".
    tool_end_tag   : str
        Marker that terminates a tool-call block, e.g. "</tool>".
    events         : List[Event]
        Chronological list of agentic turns (assistant, tool).
    interactions   : List[Interaction]
        Basic record of noteworthy things the agent did each turn.
    """

    def __init__(self, system_message: str, start_message: str, tool_start_tag: str, tool_end_tag: str) -> None:
        self.system_message: str = system_message
        self.start_message: str = start_message
        self.tool_start_tag: str = tool_start_tag
        self.tool_end_tag: str = tool_end_tag

        self.reset()

    def reset(self) -> None:
        """Resets events and interactions."""
        self.events: List[Event] = []
        self.interactions: List[Interaction] = []

    def build_input(self, data_replacements: List[Tuple[str, str]]) -> List[Dict[str, str]]:
        """
        Assemble an OpenAI-compatible ``messages`` list.

        Parameters
        ----------
        data_replacements : List[Tuple[str, str]]
            (key, value) pairs used to substitute placeholders that appear in
            ``system_message`` or ``start_message``.  Keys must include the
            delimiting braces or other sentinel exactly as it appears.

        Returns
        -------
        List[Dict[str, str]]
on for a too            Sequence of ``{"role": ..., "content": ...}`` dictionaries ready
            for an OpenAI chat-completion call.
        """
        def _apply(text: str) -> str:
            for k, v in data_replacements:
                text = text.replace(k, v)
            return text

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": _apply(self.system_message)},
            {"role": "user", "content": _apply(self.start_message)},
        ]
        role_cycle = ("assistant", "user")  # start with assistant, then user
        for idx, ev in enumerate(self.events):
            role = role_cycle[idx % 2]
            messages.append({"role": role, "content": str(ev)})

        if messages[-1]["role"] == "assistant":
            raise RuntimeError(
                "History ends with an assistant turn; waiting for user reply or tool response."
            )
        return messages

    def process_response(self, raw_response: str, append_event: bool = True, error_on_misformat: bool = False) -> Tuple[str, Optional[str], Event]:
        """
        Split a raw model response into message part and tool call, and create an Event.
        Warning: Only messages with one tool call are supported. Additional tool calls past the first will be truncated.

        Parameters
        ----------
        raw_response : str
            Exact text returned by the LLM. Do not preprocess this.
        append_event : bool, default=True
            If ``True`` the created Event is pushed into ``events``.

        Returns
        -------
        Tuple[str, str | None, Event]
            1. ``message_part`` – assistant text with any tool block removed.
            2. ``tool_block``   – content inside start/end tags, or ``None``.
            3. ``event``        – Event encapsulating the raw response.
        """
        start = raw_response.find(self.tool_start_tag)
        end   = raw_response.find(self.tool_end_tag, start + len(self.tool_start_tag))

        message_part: str
        tool_block: str | None = None

        if start == -1:
            # No tool-call: entire response is message_part
            message_part = raw_response
        else:
            # Tag found – ensure we have a closing tag
            if end == -1:
                if error_on_misformat:
                    raise ValueError(
                        f"Malformed tool call (no closing tag) in response: {raw_response}"
                    )
                # Malformed: append closing tag on a new line
                raw_response += f"\n{self.tool_end_tag}"
                end = raw_response.find(self.tool_end_tag, start)

            # Grab first (only) tool call
            tool_block = raw_response[
                start + len(self.tool_start_tag) : end
            ].strip()

            # Message is everything *before* the start tag
            message_part = raw_response[:start].rstrip()

        # Create agentic Event for debugging / display
        display = raw_response if tool_block is None else raw_response[:end + len(self.tool_end_tag)].rstrip()

        event = Event(
            raw_content=raw_response,
            tool_content=tool_block,
            display_content=[display],
        )

        if append_event:
            self.events.append(event)

        return message_part, tool_block, event
    
    def append_event(self, item: Union[str, Event]) -> None:
        """
        Append either an existing ``Event`` or a raw assistant string.

        If a string is provided, a trivial ``Event`` wrapper is created with
        identical ``raw_content`` and ``display_content`` and no tool block.
        """
        if isinstance(item, Event):
            self.events.append(item)
        elif isinstance(item, str):
            new_event = Event(
                raw_content=item,
                tool_content=None,
                display_content=[item],
            )
            self.events.append(new_event)
        else:
            raise TypeError("append_event expects a str or Event instance")
        
    def debug_system_string(self, data_replacements: List[Tuple[str, str]]) -> str:
        """
        Returns the system and start messages with data replacements applied.

        Parameters
        ----------
        data_replacements : List[Tuple[str, str]]
            (key, value) pairs used to substitute placeholders in ``system_message`` and ``start_message``.
            Keys must include the delimiting braces or other sentinel exactly as it appears.

        Returns
        -------
        str
            A string containing the system message and start message with data replacements applied.
        """
        def _apply(text: str) -> str:
            for k, v in data_replacements:
                text = text.replace(k, v)
            return text
        system_message = _apply(self.system_message)
        start_message  = _apply(self.start_message)
        system_text = "### System\n" + system_message + "\n" + "### Start\n" + start_message

        return system_text
        
    def __str__(self) -> str:
        """
        Return a chat-style log that alternates *### Assistant* and *### User*  
        blocks, showing what the model did over the past events. 
        Note that the system prompt and start message are not shown, as they must be built.

        Example
        -------
        >>> print(agent)
        ### Assistant
        I need to view the file /path/to/file.txt
        <tool>
        {"name": "view_file", "arguments": {"path": "/path/to/file.txt"}}
        </tool>
        ### User
        File contents: ...
        """
        out_lines: List[str] = []

        role_cycle = ("### Assistant", "### User")
        for idx, ev in enumerate(self.events):
            header = role_cycle[idx % 2]
            out_lines.append(header + "\n" + str(ev))
        return "\n\n".join(out_lines)
    
    def get_interaction_elements(self) -> List[Element]:
        """
        Get all unique elements that have been interacted with.
        
        Returns
        -------
        List[Element]
            List of unique Element objects that have been targets of interactions.
            Only includes elements where target_element is not None.
        """
        elements = []
        
        for interaction in self.interactions:
            if interaction.target_element is not None and interaction.target_element not in elements:
                elements.append(interaction.target_element)
        
        return elements

    def get_interaction_files(self) -> List[File]:
        """
        Get all unique files that have been interacted with.
        
        Returns
        -------
        List[File]
            List of unique File objects that have been targets of interactions.
            Only includes files where target_file is not None.
        """
        files = []
        
        for interaction in self.interactions:
            if interaction.target_file is not None and interaction.target_file not in files:
                files.append(interaction.target_file)
        
        return files

    def get_latest_interaction(self) -> Optional[Interaction]:
        """
        Get the latest interaction for the agent.
        
        Returns
        -------
        Optional[Interaction]
            The most recent Interaction object, or None if no interactions exist.
        """
        if not self.interactions:
            return None
        return self.interactions[-1]
