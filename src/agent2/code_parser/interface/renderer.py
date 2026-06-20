from typing import Literal
from agent2.code_parser.dataclasses import CodeNode

def apply_line_prefixes(text: str, starting_row_0_indexed: int, spacer: str = "| ") -> str:
    """Injects explicit visual line numbers (e.g., '42 | def foo():').
    
    Args:
        text: The text to apply line numbers to.
        starting_row_0_indexed: The starting row number (0-indexed).
        spacer: The spacer to use between the line number and the text.
    """
    lines = text.splitlines()
    return "\n".join(f"{starting_row_0_indexed + idx + 1}{spacer}{line}" for idx, line in enumerate(lines))

def view_code_node_full(code_node: CodeNode, src_bytes: bytes, prefix_lines: bool = True, spacer: str = "| ") -> str:
    """Extracts raw bytes for a code node and formats them based on the requested view mode.

    Args:
        code_node: The code node to view.
        src_bytes: The source code as bytes.
        prefix_lines: Whether to prefix lines with line numbers.
        spacer: The spacer to use between the line number and the text.
    """
    start_row = code_node.full_block.start_point[0]
    fragment = src_bytes[code_node.full_block.start_byte:code_node.full_block.end_byte].decode('utf-8')
    if prefix_lines:
        return apply_line_prefixes(fragment, start_row, spacer)
    return fragment

def view_code_node_collapsed(code_node: CodeNode, src_bytes: bytes, show_inner_docstrings: bool = True, max_depth: int = 1, prefix_lines: bool = True, spacer: str = "| ") -> str:
    """Extracts raw bytes for a code node and removes inner objects with a depth greater than max_depth, showing their docstrings if show_inner_docstrings is true (otherwise only showing headers).

    Args:
        code_node: The code node to view.
        src_bytes: The source code as bytes.
        show_inner_docstrings: Whether to show docstrings of inner objects.
        max_depth: The maximum depth of inner objects to show. If max_depth = 0, then the only shown node is the viewed node.
        prefix_lines: Whether to prefix lines with line numbers.
        spacer: The spacer to use between the line number and the text.
    """
    def _render_node_at_depth(node: CodeNode, current_depth: int) -> list:
        show_doc = True if current_depth == 0 else show_inner_docstrings
        
        if current_depth >= max_depth:
            hide_start = node.doc_block.end_byte if (node.doc_block and show_doc) else node.body_block.start_byte
            header_text = src_bytes[node.full_block.start_byte:hide_start].decode('utf-8')
            
            hidden_lines_count = node.body_block.end_point[0] - node.body_block.start_point[0]
            separator = f"    ... [BODY HIDDEN: {hidden_lines_count} LINES] ..."
            
            res = [("text", header_text, node.full_block.start_point[0]), ("separator", separator, 0)]
            
            footer_text = src_bytes[node.body_block.end_byte:node.full_block.end_byte].decode('utf-8')
            if footer_text.strip():
                res.append(("text", footer_text, node.body_block.end_point[0]))
            return res
        else:
            sorted_children = sorted(node.children, key=lambda c: c.full_block.start_byte)
            parts = []
            current_byte = node.full_block.start_byte
            current_row = node.full_block.start_point[0]
            
            for child in sorted_children:
                if child.full_block.start_byte < current_byte:
                    continue
                
                chunk_text = src_bytes[current_byte:child.full_block.start_byte].decode('utf-8')
                if chunk_text:
                    parts.append(("text", chunk_text, current_row))
                
                parts.extend(_render_node_at_depth(child, current_depth + 1))
                
                current_byte = child.full_block.end_byte
                current_row = child.full_block.end_point[0]
                
            chunk_text = src_bytes[current_byte:node.full_block.end_byte].decode('utf-8')
            if chunk_text:
                parts.append(("text", chunk_text, current_row))
                
            return parts

    parts = _render_node_at_depth(code_node, 0)
    
    output = []
    at_line_start = True
    
    for type_, text, row in parts:
        if type_ == "text":
            current_row = row
            for char in text:
                if at_line_start:
                    if prefix_lines:
                        output.append(f"{current_row + 1}{spacer}")
                    at_line_start = False
                output.append(char)
                if char == '\n':
                    current_row += 1
                    at_line_start = True
        elif type_ == "separator":
            if not at_line_start:
                output.append("\n")
            output.append(text + "\n")
            at_line_start = True
            
    # Strip trailing newline if it was added by our system or inherently existed 
    # to maintain compatibility with the rest of the layout expectations.
    res_str = "".join(output)
    if res_str.endswith("\n"):
        res_str = res_str[:-1]
    return res_str

def view_code_node_automatic(code_node: CodeNode, src_bytes: bytes, symbol_limit: int = 2000, ceiling_behavior: Literal["under", "over", "closer"] = "under", prefix_lines: bool = True, spacer: str = "| ") -> str:
    """Extracts raw bytes for a code node and automatically decides the max depth, and where to show docstrings, based on the symbol limit (the number of words after splitting by whitespace). May overflow if the symbols inside the node are long.

    Args:
        code_node: The code node to view.
        src_bytes: The source code as bytes.
        symbol_limit: The approximate number of words to display. 
        ceiling_behavior: The ceiling behavior determines whether the desired symbol count will be under, over, or closest to the symbol limit.
        prefix_lines: Whether to prefix lines with line numbers.
        spacer: The spacer to use between the line number and the text.
    """
    full_view = view_code_node_full(code_node, src_bytes, prefix_lines, spacer)
    full_len = len(full_view.split())
    diff = full_len - symbol_limit
    
    best_under_view = None
    best_under_diff = float('inf')
    best_over_view = None
    best_over_diff = float('inf')

    if diff <= 0:
        best_under_diff = abs(diff)
        best_under_view = full_view
    else:
        best_over_diff = abs(diff)
        best_over_view = full_view
        
    depth = 0
    last_depth_views = set()
    
    while True:
        current_depth_views = set()
        for show_docs in (False, True):
            current_view = view_code_node_collapsed(
                code_node, src_bytes, 
                show_inner_docstrings=show_docs, 
                max_depth=depth, 
                prefix_lines=prefix_lines, 
                spacer=spacer
            )
            
            current_depth_views.add(current_view)
            current_len = len(current_view.split())
            diff = current_len - symbol_limit
            
            if diff <= 0:
                if abs(diff) < best_under_diff:
                    best_under_diff = abs(diff)
                    best_under_view = current_view
            else:
                if abs(diff) < best_over_diff:
                    best_over_diff = abs(diff)
                    best_over_view = current_view
        
        if current_depth_views == last_depth_views or full_view in current_depth_views or depth > 100:
            break
            
        last_depth_views = current_depth_views
        depth += 1
        
    if ceiling_behavior == "under":
        return best_under_view if best_under_view is not None else best_over_view
    elif ceiling_behavior == "over":
        return best_over_view if best_over_view is not None else best_under_view
    else: # closer
        if best_under_view is None:
            return best_over_view
        if best_over_view is None:
            return best_under_view
        if best_under_diff <= best_over_diff:
            return best_under_view
        return best_over_view