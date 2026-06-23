from typing import Optional
from agent2.code_parser.dataclasses import CodeBlock
from typing import List, Any
from abc import ABC, abstractmethod
from agent2.code_parser.dataclasses import CodeNode, CodeState

class LanguageAdapter(ABC):
    """
    Abstract Base Class for language adapters.
    """
    
    @property
    @abstractmethod
    def language_id(self) -> str:
        pass

    @property
    @abstractmethod
    def extensions(self) -> List[str]:
        pass

    @abstractmethod
    def extract_nodes(self, root_node: Any, code_state: CodeState) -> List[CodeNode]:
        """Executes Tree-sitter queries to extract granular code nodes.
        
        Args:
            root_node: The root node of the AST.
            code_state: The CodeState containing the code.
        
        Returns:
            A list of CodeNodes.
        """
        pass

    @abstractmethod
    def parse(self, source_bytes: bytes, old_tree: Optional[Any] = None) -> Any:
        """Parses the bytes into a Tree-sitter AST.
        
        Args:
            source_bytes: The bytes to parse.
            old_tree: The previous tree to use for incremental parsing.
        
        Returns:
            The root node of the AST.
        """
        pass

    @abstractmethod
    def attempt_fix_formatting(self, new_code: str, target_code_block: CodeBlock, code_state: CodeState) -> str:
        """Attempts to fix formatting issues, such as indentation, and beautify the code. May not be implemented for certain languages.
        
        Args:
            new_code: The new code to format.
            target_code_block: The CodeNode to format.
            code_state: The CodeState containing the code.
        
        Returns:
            The formatted code.
        """
        pass