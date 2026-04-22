from __future__ import annotations
from collections import OrderedDict
from typing import List
from agent2.agent_rework.element import Element
from agent2.parsing.parser import parse_code

def normalize_path(path: str) -> str:
    """Normalize file path by replacing backslashes and removing leading dots/slashes."""
    if "\\" in path:
        path = path.replace("\\", "/")
    if path.startswith("."):
        path = path[1:]
    if path.startswith("/"):
        path = path[1:]
    return path

class File:
    """
    Represents a source file, its content, and the parsed code elements within.

    Attributes:
        path: Full path to the file
        extension: File extension derived from the path (e.g., "py"); "Unknown" if none
        original_content: The original file content provided at construction
        content: The current (possibly modified) file content
        elements: The list of top-level parsed Elements contained in this file
    """

    def __init__(self, path: str, content: str) -> None:
        """
        Initialize a File with its path and content.

        Args:
            path: Full path to the file
            content: Original file content as a single string
        """
        self.path: str = normalize_path(path)
        if "." in path:
            self.extension: str = ".".join(path.split(".")[1:])
        else:
            self.extension = "Unknown"
        self.original_content: str = content
        self.content: str = content
        self.elements: List[Element] = []
        self.update_elements()

    def update_elements(self) -> None:
        """
        Parse the current content into Elements and update the elements list.

        This method:
        - Recursively collects existing elements to preserve their embeddings where possible.
        - Re-parses the current content using parse_code.
        - Re-attaches previous embeddings to newly parsed elements when content matches.
        """
        elements_to_lookat: List[Element] = list(self.elements)
        embeddings_current: dict[str, list[float] | None] = {}
        while elements_to_lookat:
            element = elements_to_lookat.pop()
            elements_to_lookat.extend(element.elements)
            embeddings_current[element.content] = element.embedding

        self.elements = parse_code(self.content, self.extension)

        to_visit: List[Element] = list(self.elements)
        while to_visit:
            el = to_visit.pop()
            if el.content in embeddings_current:
                el.embedding = embeddings_current[el.content]
            to_visit.extend(el.elements)

    def update_content(self, new_content: str) -> None:
        """
        Replace the file content and re-parse elements.

        Args:
            new_content: The new content to assign to the file
        """
        self.content = new_content
        self.update_elements()

    def get_elements(self) -> OrderedDict[str, Element]:
        """
        Retrieve all elements in the file as an OrderedDict keyed by lowercase identifier.
        """
        all_elements: OrderedDict[str, Element] = OrderedDict()
        stack: List[Element] = list(self.elements)

        while stack:
            el = stack.pop()
            key = el.identifier.lower()
            if key not in all_elements:
                all_elements[key] = el
            stack.extend(el.elements)

        return all_elements

    def get_element(self, element_id: str) -> Element:
        """
        Locate an element by case-insensitive identifier using OrderedDict for lookup.
        """
        elements_map = self.get_elements()
        key = element_id.lower()

        if key in elements_map:
            return elements_map[key]

        # Otherwise gather “close” matches
        close_matches = [el for k, el in elements_map.items() if key in k]
        if not close_matches:
            suffix = key.split(".")[-1]
            close_matches = [el for k, el in elements_map.items() if suffix in k]

        if close_matches:
            opts = "`, `".join(e.identifier for e in close_matches)
            raise ValueError(
                f"Element '{element_id}' not found in file '{self.path}'. "
                f"Closest matches: `{opts}`"
            )

        raise ValueError(f"Element '{element_id}' not found in file '{self.path}'")

    def __str__(self) -> str:
        """
        Return a human-readable representation.

        Returns:
            The file path
        """
        return self.path

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            A string showing the path, extension, top-level element identifiers, and content length
        """
        top_level_ids = [e.identifier for e in self.elements]
        return (
            f"File(path={self.path!r}, extension={self.extension!r}, "
            f"top_level_ids={top_level_ids!r}, content_len={len(self.content)})"
        )
