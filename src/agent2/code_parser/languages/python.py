from typing import Optional
from agent2.code_parser.dataclasses import CodeNode
from agent2.code_parser.dataclasses import CodeBlock
from agent2.code_parser.dataclasses import CodeState
import textwrap
import ast
from typing import List, Any

class PythonLanguageAdapter:
    """Adapter executing Python Tree-sitter queries and AST safety checks."""
    language_id = "python"

    extensions = [".py", ".pyi"]

    def __init__(self):
        self.ts_lang = ...
        self.parser = ...
        
        self.node_query = self.ts_lang.query("""
            (decorated_definition 
                (decorator)* @leading
                definition: [
                    (function_definition name: (identifier) @name body: (block) @body)
                    (class_definition name: (identifier) @name body: (block) @body)
                ]
            ) @full
            (function_definition name: (identifier) @name body: (block) @body) @full
            (class_definition name: (identifier) @name body: (block) @body) @full
        """)
        
        self.docstring_query = self.ts_lang.query("""
            (block (expression_statement (string)) @docstring)
        """)

    def extract_nodes(self, root_node: Any, code_state: CodeState) -> List[CodeNode]:
        """
        Parses captures from the active Tree-sitter tree into code nodes.

        Args:
            root_node: The root node of the AST.
            code_state: The CodeState containing the code.
        
        Returns:
            A list of code nodes.
        """
        nodes = []
        # TODO: IMPLEMENT
        return nodes

    def parse(self, source_bytes: bytes, old_tree: Optional[Any] = None) -> Any:
        """Parses the bytes into a Tree-sitter AST.
        
        Args:
            source_bytes: The bytes to parse.
            old_tree: The previous tree to use for incremental parsing.
        
        Returns:
            The root node of the AST.
        """
        # TODO: IMPLEMENT
        return None

    def attempt_fix_formatting(self, new_code: str, target_code_block: CodeBlock, code_state: CodeState) -> str:
        """
        Sanitizes cursed LLM output using native AST, then utilizes the LineIndex
        to perfectly align the code's base indentation to the file structure.

        Args:
            new_code: The new code to format.
            target_code_block: The CodeBlock to format.
            code_state: The code state containing the code.
        
        Returns:
            The formatted code.
        """
        try:
            parsed_snippet = ast.parse(new_code)
            clean_code = ast.unparse(parsed_snippet)
        except SyntaxError:
            clean_code = textwrap.dedent(new_code).strip('\n')

        current_row = target_code_block.start_point[0] + 1
        line_start_byte, _ = code_state.get_line_byte_range(current_row)
        
        prefix_bytes = code_state.bytes[line_start_byte:target_code_block.start_byte]
        ast_whitespace = "".join([chr(b) for b in prefix_bytes if chr(b).isspace()])

        lines = clean_code.splitlines()
        normalized_lines = [ast_whitespace + line for line in lines]
        
        return "\n".join(normalized_lines) + "\n"