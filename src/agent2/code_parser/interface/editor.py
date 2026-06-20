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
