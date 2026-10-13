from __future__ import annotations

from bisect import bisect_right
from typing import Optional, Dict, Any
from agent2.code_parser.objects import CodeState, FileEdit, CodeNode
from agent2.code_parser.utils import calculate_new_endpoint
from agent2.code_parser.languages.abc import LanguageAdapter

class File:
    """
    Represents a generic file in the codebase.
    
    Attributes:
        path: Full path to the file.
        original_state: The initial CodeState for the file when loaded.
        current_state: The current CodeState for the file.
    """
    def __init__(self, path: str, initial_bytes: Optional[bytes] = None):
        self.path = path
        self.original_state: Optional[CodeState] = None
        self.current_state: Optional[CodeState] = None
        if initial_bytes is not None:
            self.original_state = CodeState(initial_bytes)
            self.current_state = self.original_state

    def apply_edit(self, edit: FileEdit) -> CodeState:
        """Apply a byte-range edit and return the previous state."""
        if not self.current_state:
            raise RuntimeError("Cannot edit a file without content.")
        old_state = self.current_state
        data = old_state.bytes
        self.current_state = CodeState(data[:edit.start_byte] + edit.new_text + data[edit.end_byte:])
        return old_state

    def replace_bytes(self, data: bytes) -> CodeState:
        """Replace content through the smallest single byte-range edit."""
        if not self.current_state:
            raise RuntimeError("Cannot replace a file without content.")
        old = self.current_state.bytes
        if old == data:
            return self.current_state
        start = next((i for i, pair in enumerate(zip(old, data)) if pair[0] != pair[1]), min(len(old), len(data)))
        old_end, new_end = len(old), len(data)
        while old_end > start and new_end > start and old[old_end - 1] == data[new_end - 1]:
            old_end -= 1
            new_end -= 1
        starts = self.current_state._line_starts
        start_row = bisect_right(starts, start) - 1
        end_row = bisect_right(starts, old_end) - 1
        return self.apply_edit(FileEdit(
            start,
            old_end,
            (start_row, start - starts[start_row]),
            (end_row, old_end - starts[end_row]),
            data[start:new_end],
        ))

    def clone(self) -> File:
        clone = File(self.path)
        clone.original_state = self.original_state
        clone.current_state = self.current_state
        return clone


class CodeFile(File):
    """
    Represents a file in the codebase that has been parsed.
    
    Attributes:
        path: Full path to the file.
        adapter: The language adapter for the file.
        original_state: The initial CodeState for the file.
        current_state: The current CodeState for the file.
        tree: The tree-sitter tree for the file.
        code_nodes: A dictionary of code nodes in the file, with their paths as keys.
    """
    def __init__(self, path: str, adapter: LanguageAdapter, initial_bytes: Optional[bytes] = None):
        super().__init__(path, initial_bytes)
        self.adapter = adapter        
        self.tree: Optional[Any] = None
        self.code_nodes: Dict[str, CodeNode] = {}
        if initial_bytes is not None:
            self.parse_to_bytes(initial_bytes)

    def parse_to_bytes(self, new_bytes: bytes, old_tree: Optional[Any] = None, sync_original: bool = True) -> CodeState:
        """
        Reparses the file to a new state.

        Args:
            new_bytes: The raw bytes of the file.
            
        Returns:
            The previous CodeState.
        """
        old_state = self.current_state
        self.tree = self.adapter.parse(new_bytes, old_tree)
        self.current_state = CodeState(new_bytes)
        if sync_original:
            self.original_state = self.current_state
        self.code_nodes = {}
        for s in self.adapter.extract_nodes(self.tree.root_node, self.current_state):
            self.code_nodes[s.llm_path] = s
            self.code_nodes[s.path] = s
            if s.parent_path and s.parent_path in self.code_nodes:
                parent = self.code_nodes[s.parent_path]
                object.__setattr__(parent, 'children', parent.children + (s,))
        return old_state

    def apply_edit(self, edit: FileEdit) -> CodeState:
        """Apply a byte-range edit, incrementally reparse, and return the previous state."""
        if not self.current_state or not self.tree:
            raise RuntimeError("Cannot apply edits to an unparsed CodeFile. Call parse_to_bytes first.")

        old_bytes = self.current_state.bytes
        
        new_end_point = calculate_new_endpoint(edit.start_point, edit.new_text)
        
        self.tree.edit(
            start_byte=edit.start_byte,
            old_end_byte=edit.end_byte,
            new_end_byte=edit.start_byte + len(edit.new_text),
            start_point=edit.start_point,
            old_end_point=edit.end_point,
            new_end_point=new_end_point
        )
        
        new_bytes = old_bytes[:edit.start_byte] + edit.new_text + old_bytes[edit.end_byte:]
        return self.parse_to_bytes(new_bytes, old_tree=self.tree, sync_original=False)

    def clone(self) -> CodeFile:
        clone = CodeFile(self.path, self.adapter)
        clone.original_state = self.original_state
        clone.current_state = self.current_state
        clone.tree = self.tree.copy() if self.tree is not None else None
        clone.code_nodes = self.code_nodes.copy()
        return clone
