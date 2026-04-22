from typing import Optional, List
from agent2.parsing.parser import unindent

class Element:
    identifier: str
    content: str
    description: str
    line_start: int
    embedding: Optional[list[float]]
    elements = List["Element"]

    """
    Represents an element within a file
    
    Args:
        identifier: Path of the element, e.g., myclass.foo.bar
        content: The complete text content of the element
        description: The element's docstring if available
        line_start: Starting line number of the element (inclusive)
        embedding: Optional embedding vector for semantic search
        elements: List of sub-elements
    """
    def __init__(self, identifier: str, content: str, description: str, line_start: int, embedding: Optional[List[float]], elements: List["Element"]):
        self.identifier = identifier
        self.content = content
        self.description = description
        self.line_start = line_start
        self.embedding = embedding
        self.elements = elements

    def to_string(self, unindent_text = True, number_lines = True, mask_subelements = True):
        cont = self.content
        if unindent_text:
            cont = unindent(cont)
        lines = cont.split('\n')
        if number_lines:
            lines = [f"{i} {line}" for i, line in enumerate(lines, start=self.line_start)]
        if not mask_subelements:
            return '\n'.join(lines)
        mask = [False] * len(lines)
        for sub in self.elements:
            sub_rel_start = sub.line_start - self.line_start  # 0-based within this element
            # Look for first occurance of the subelement's header
            f = 0
            for i in lines[sub_rel_start:]:
                if sub.identifier.split(".")[-1] in i:
                    break
                f += 1
            sub_rel_start += f
            if 0 <= sub_rel_start < len(lines):
                # Mask all lines after the subelement's header
                mask[sub_rel_start + 1 : sub_rel_start + len(sub.content.split('\n'))] = [True] * (len(sub.content.split('\n')) - 1)
        
        # Build truncated content
        truncated = []
        for i, line in enumerate(lines):
            if mask[i]:
                if not truncated or not truncated[-1].endswith("..."):  # Avoid duplicate ...
                    truncated[-1] += "..."
            else:
                truncated.append(line)
        return '\n'.join(truncated)