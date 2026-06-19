from typing import Literal
from agent2.code_parser.dataclasses import CodeEdit
from agent2.code_parser.code_file import CodeFile
from agent2.code_parser.dataclasses import CodeNode
from typing import List, Tuple

def commit_mutations(code_file: CodeFile, updates: List[Tuple[str, str]]) -> None:
    """
    Translates a list of target paths and string replacements into safe byte mutations.
    
    Args:
        code_file: The CodeFile to apply the mutations to.
        updates: A list of tuples containing (code_node_path, new_body_text).
    """
    resolved_edits: List[Tuple[CodeNode, str]] = []
    for path, body_text in updates:
        sym = code_file.code_nodes.get(path)
        if sym and sym.body_block:
            resolved_edits.append((sym, body_text))

    resolved_edits.sort(key=lambda item: item[0].body_block.start_byte, reverse=True)

    for sym, new_text in resolved_edits:
        normalized_text = code_file.adapter.attempt_fix_formatting(
            new_text, 
            sym.body_block, 
            code_file.buffer
        )
        
        edit_payload = CodeEdit(
            start_byte=sym.body_block.start_byte,
            end_byte=sym.body_block.end_byte,
            start_point=sym.body_block.start_point,
            end_point=sym.body_block.end_point,
            new_text=normalized_text.encode('utf-8')
        )
        
        code_file.apply_edit_and_reparse(edit_payload)

def apply_line_prefixes(text: str, starting_row_0_indexed: int) -> str:
    """Injects explicit visual line numbers (e.g., '42 | def foo():')."""
    lines = text.splitlines()
    return "\n".join(f"{starting_row_0_indexed + idx + 1} | {line}" for idx, line in enumerate(lines))

def format_code_node_view(code_node: CodeNode, src_bytes: bytes, mode: Literal["full", "collapsed"]) -> str:
    """Extracts raw bytes for a code node and formats them based on the requested view mode."""
    start_row = code_node.full_block.start_point[0]

    if mode == "full" or not code_node.body_block:
        fragment = src_bytes[code_node.full_block.start_byte:code_node.full_block.end_byte].decode('utf-8')
        return apply_line_prefixes(fragment, start_row)
    
    elif mode == "collapsed":
        hide_start = code_node.doc_block.end_byte if code_node.doc_block else code_node.body_block.start_byte
        
        # 1. Render Header with accurate starting line
        header_text = src_bytes[code_node.full_block.start_byte:hide_start].decode('utf-8')
        header_rendered = apply_line_prefixes(header_text, start_row)
        
        # 2. Render Footer with its true starting line (where the body ends)
        footer_text = src_bytes[code_node.body_block.end_byte:code_node.full_block.end_byte].decode('utf-8')
        
        # Calculate exactly how many lines we are hiding for LLM awareness
        hidden_lines_count = code_node.body_block.end_point[0] - code_node.body_block.start_point[0]
        separator = f"    ... [BODY HIDDEN: {hidden_lines_count} LINES] ..."

        if footer_text.strip():
            footer_start_row = code_node.body_block.end_point[0]
            footer_rendered = apply_line_prefixes(footer_text, footer_start_row)
            return f"{header_rendered}\n{separator}\n{footer_rendered}"
            
        return f"{header_rendered}\n{separator}"
        
    return ""