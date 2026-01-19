from __future__ import annotations
from typing import List
from collections import OrderedDict

class Element:
    """
    Represents a parsed code element (e.g., class, function, method) and its structure.

    Attributes:
        identifier: Fully-qualified identifier of the element (e.g., "MyClass.my_method")
        header: The exact source line that declares the element
        content: The full raw source text of the element (from first decorator/def/class line through its body)
        description: The element's docstring text (without quotes), empty string if none
        line_start: 0-based line number where the element begins in its file, considering decorators
        embedding: A semantic vector embedding of the element (None if not computed yet)
        elements: A list of sub-elements directly contained within this element (e.g., methods in a class)
    """

    def __init__(
        self,
        identifier: str,
        header: str,
        content: str,
        description: str,
        line_start: int,
        embedding: list[float] | None = None,
        elements: List[Element] | None = None,
    ) -> None:
        """
        Initialize a code Element.

        Args:
            identifier: Fully-qualified identifier (e.g., "MyClass.my_method")
            header: Exact declaring line
            content: Full raw source text of the element
            description: Docstring text, empty string if none
            line_start: 0-based starting line number in the source file
            embedding: Optional semantic embedding vector
            elements: Optional list of direct child elements

        Raises:
            ValueError: If identifier, header, or content are empty, or if line_start < 1
        """
        self.identifier: str = identifier
        self.header: str = header
        self.content: str = content
        self.description: str = description or ""
        self.line_start: int = line_start
        self.embedding: list[float] | None = embedding
        self.elements: List[Element] = elements if elements is not None else []

    def add_child(self, element: Element) -> None:
        """
        Add a sub-element to this element.

        Args:
            element: The child Element to add
        """
        self.elements.append(element)

    def has_children(self) -> bool:
        """
        Check whether this element contains any sub-elements.

        Returns:
            True if there is at least one child element; otherwise False
        """
        return len(self.elements) > 0
    
    def get_elements(self) -> OrderedDict[str, Element]:
        """
        Retrieve all elements contained within the element, including nested ones,
        as an OrderedDict keyed by lowercase identifier.
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

    def __str__(self) -> str:
        """
        Return a concise string representation.

        Returns:
            The element's identifier
        """
        return self.identifier

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns:
            A string summarizing key fields of the Element
        """
        return (
            f"Element(identifier={self.identifier!r}, "
            f"line_start={self.line_start}, "
            f"children={len(self.elements)}, "
            f"has_embedding={self.embedding is not None})"
        )
