from typing import Optional
from agent2.code_parser.dataclasses import CodeNode
from agent2.code_parser.dataclasses import CodeBlock
from agent2.code_parser.dataclasses import CodeState
import textwrap
import ast
import tree_sitter
import tree_sitter_python
from typing import List, Any
from agent2.code_parser.languages.abc import LanguageAdapter

class PythonLanguageAdapter(LanguageAdapter):
    """Adapter executing Python Tree-sitter queries and AST safety checks."""
    @property
    def language_id(self) -> str:
        return "python"

    @property
    def extensions(self) -> List[str]:
        return [".py", ".pyi"]

    def __init__(self):
        self.ts_lang = tree_sitter.Language(tree_sitter_python.language())
        self.parser = tree_sitter.Parser(self.ts_lang)
        
        self.node_query = tree_sitter.Query(self.ts_lang, """
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
        
        self.docstring_query = tree_sitter.Query(self.ts_lang, """
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
        cursor = tree_sitter.QueryCursor(self.node_query)
        matches = cursor.matches(root_node)
        
        def make_block(n):
            return CodeBlock(n.start_byte, n.end_byte, n.start_point, n.end_point) if n else None
            
        def get_parent_path(node):
            names = []
            curr = node.parent
            while curr:
                if curr.type in ('class_definition', 'function_definition'):
                    name_child = curr.child_by_field_name('name')
                    if name_child:
                        names.append(name_child.text.decode('utf-8'))
                curr = curr.parent
            names.reverse()
            return ".".join(names) if names else None

        for pattern_idx, captures in matches:
            if 'full' not in captures or not captures['full']: continue
            full_node = captures['full'][0]
            
            if full_node.parent and full_node.parent.type == 'decorated_definition' and full_node.type in ('function_definition', 'class_definition'):
                continue
                
            name_node = captures['name'][0] if 'name' in captures and captures['name'] else None
            body_node = captures['body'][0] if 'body' in captures and captures['body'] else None
            
            if not name_node or not body_node: continue
            
            leading_nodes = captures.get('leading', [])
            sig_start = leading_nodes[0].start_byte if leading_nodes else full_node.start_byte
            sig_start_point = leading_nodes[0].start_point if leading_nodes else full_node.start_point

            
            signature_block = CodeBlock(
                start_byte=sig_start,
                end_byte=body_node.start_byte,
                start_point=sig_start_point,
                end_point=body_node.start_point
            )
            
            doc_block = None
            doc_cursor = tree_sitter.QueryCursor(self.docstring_query)
            doc_matches = doc_cursor.matches(body_node)
            if doc_matches:
                first_match = doc_matches[0][1]
                if 'docstring' in first_match and first_match['docstring']:
                    d_node = first_match['docstring'][0]
                    if len(body_node.children) > 0 and d_node == body_node.children[0]:
                        doc_block = make_block(d_node)
            
            nodes.append(CodeNode(
                name=name_node.text.decode('utf-8'),
                full_block=make_block(full_node),
                signature_block=signature_block,
                doc_block=doc_block,
                body_block=make_block(body_node),
                parent_path=get_parent_path(full_node)
            ))
            
        return nodes

    def parse(self, source_bytes: bytes, old_tree: Optional[Any] = None) -> Any:
        """Parses the bytes into a Tree-sitter AST.
        
        Args:
            source_bytes: The bytes to parse.
            old_tree: The previous tree to use for incremental parsing.
        
        Returns:
            The root node of the AST.
        """
        if old_tree is None:
            return self.parser.parse(source_bytes)
        return self.parser.parse(source_bytes, old_tree)


    def attempt_fix_formatting(self, new_code: str, target_code_block: CodeBlock, code_state: CodeState) -> str:
        """
        Sanitizes cursed LLM output and aligns the code's base indentation 
        to the file structure, preserving comments.

        Args:
            new_code: The new code to format.
            target_code_block: The CodeBlock to format.
            code_state: The code state containing the code.
        
        Returns:
            The formatted code.
        """
        clean_code = textwrap.dedent(new_code).strip('\n')

        current_row = target_code_block.start_point[0] + 1
        line_start_byte, _ = code_state.get_line_byte_range(current_row)
        
        prefix_bytes = code_state.bytes[line_start_byte:target_code_block.start_byte]
        ast_whitespace = "".join([chr(b) for b in prefix_bytes if chr(b).isspace()])

        lines = clean_code.splitlines()
        normalized_lines = [ast_whitespace + line if line.strip() else "" for line in lines]
        
        return "\n".join(normalized_lines) + "\n"