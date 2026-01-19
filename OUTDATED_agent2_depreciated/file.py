import difflib
from typing import Optional, List
from agent2.element import Element
from agent2.parsing.parser import unindent
from agent2.parsing.code_parser import parse_code

class File:
    path: str
    extension: str
    original_content: str
    content: str
    elements: List[Element]

    def __init__(self, path: str, content: str):
        """
        Represents a file with its content and metadata
        
        Args:
            path: Full path to the file
            content: Original file content as string
            embedding: Optional embedding vector for semantic search
        """
        self.path = path
        if "." in path:
            self.extension = path.split('.')[-1]
        else:
            self.extension = "Unknown"
        self.original_content = content
        self.content = content
        self.elements = []
        self.update_elements()

    def update_elements(self):
        """
        Parse the updated content into elements using code_parser and create Element instances.
        Updates the elements list with the parsed elements. Preserves embeddings from previous
        elements when identifier and text match.
        """
        # Recursively store current elements for embeddings preservation
        elements_to_lookat = self.elements
        embeddings_current = {}
        while len(elements_to_lookat) > 0:
            element = elements_to_lookat.pop()
            elements_to_lookat.extend(element.elements)
            embeddings_current[element.content] = element.embedding
        
        # Parse updated content
        self.elements = parse_code(self.content, self.extension)

        # Match new elements to old elements
        for element in self.elements:
            if element.content in embeddings_current:
                element.embedding = embeddings_current[element.content]
    
    def diff(self, root) -> str:
        """
        Generate unified diff between original and updated content
        
        Returns:
            str: Unified diff string showing changes
        """
        if not self.content:
            return ""
        if root:
            total_path = f"{root}/{self.path}"
        else:
            total_path = self.path
        diff = difflib.unified_diff(
            self.original_content.splitlines(),
            self.content.splitlines(),
            fromfile= f"a/{total_path}",
            tofile= f"b/{total_path}",
            lineterm=''
        )
        return '\n'.join(diff)
    
    def to_string(self, unindent_text = True, number_lines = True):
        if unindent_text:
            content = unindent(self.content)
        lines = content.split('\n')
        if number_lines:
            lines = [f"{i} {line}" for i, line in enumerate(lines)]
        mask = [False] * len(lines)
        for sub in self.elements:
            sub_rel_start = sub.line_start
            # Look for first occurance of the element's header
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
