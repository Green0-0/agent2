from typing import Optional, Dict, Any
from agent2.code_parser.objects import CodeState, CodeEdit, CodeNode
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
        if initial_bytes:
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
        if sync_original or self.original_state is None:
            self.original_state = self.current_state
        self.code_nodes = {}
        for s in self.adapter.extract_nodes(self.tree.root_node, self.current_state):
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