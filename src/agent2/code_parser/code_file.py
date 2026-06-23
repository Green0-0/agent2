from agent2.code_parser.utils import calculate_new_endpoint
from typing import Tuple
from typing import Optional, Dict, Any

from agent2.code_parser.dataclasses import CodeEdit, CodeNode, CodeState
from agent2.code_parser.languages.abc import LanguageAdapter

class CodeFile:
    """
    Represents a file in the codebase that has been parsed.
    
    Attributes:
        adapter: The language adapter for the file.
        buffer: The CodeState for the file.
        tree: The tree-sitter tree for the file.
        code_nodes: A dictionary of code nodes in the file, with their paths as keys.
    """
    def __init__(self, adapter: LanguageAdapter, initial_bytes: Optional[bytes] = None):
        self.adapter = adapter        
        self.buffer: Optional[CodeState] = None
        self.tree: Optional[Any] = None
        self.code_nodes: Dict[str, CodeNode] = {}
        if initial_bytes:
            self.parse_to_bytes(initial_bytes)

    def parse_to_bytes(self, new_bytes: bytes, old_tree: Optional[Any] = None) -> CodeState:
        """
        Reparses the file to a new state.

        Args:
            new_bytes: The raw bytes of the file.
            
        Returns:
            The previous CodeState.
        """
        old_state = self.buffer
        self.tree = self.adapter.parse(new_bytes, old_tree)
        self.buffer = CodeState(new_bytes)
        self.code_nodes = {}
        for s in self.adapter.extract_nodes(self.tree.root_node, self.buffer):
            self.code_nodes[s.llm_path] = s
            self.code_nodes[s.path] = s
            if s.parent_path and s.parent_path in self.code_nodes:
                parent = self.code_nodes[s.parent_path]
                object.__setattr__(parent, 'children', parent.children + (s,))
        return old_state

    def apply_edit_and_reparse(self, edit: CodeEdit) -> CodeState:
        """
        Applies an edit to the file and reparses it.

        Args:
            edit: The edit to apply.

        Returns:
            The previous CodeState.
        """
        if not self.buffer or not self.tree:
            raise RuntimeError("Cannot apply edits to an unparsed CodeFile. Call parse_to_bytes first.")

        old_bytes = self.buffer.bytes
        
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
        return self.parse_to_bytes(new_bytes, old_tree=self.tree)

    