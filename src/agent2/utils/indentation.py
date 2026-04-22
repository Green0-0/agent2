def find_shortest_indentation(text: str) -> int:
    """Calculate the minimum indentation in non-empty lines of text.
    
    Analyzes leading whitespace to determine the smallest indentation level
    across all non-empty lines. Empty lines (including whitespace-only) are
    ignored for minimum calculation.
    
    Args:
        text: Input string containing potentially indented lines
        
    Returns:
        Minimum indentation level (number of whitespace characters).
        Returns 0 if no indented lines exist.
    """
    lines = text.splitlines()
    indentations: List[int] = []
    
    for line in lines:
        stripped = line.lstrip()
        if stripped:  # Only consider lines with actual content
            # Calculate indentation by comparing original and stripped lengths
            indent = len(line) - len(stripped)
            indentations.append(indent)
    return min(indentations) if indentations else 0


def unindent(text: str) -> str:
    """Remove uniform indentation from all lines while preserving structure.
    
    The removed indentation amount equals the smallest indentation found
    in the text. Maintains relative indentation levels between lines and
    preserves empty lines without modification.
    
    Args:
        text: Input text block with consistent indentation
        
    Returns:
        Text block with base indentation removed from all lines
    """
    indent_to_remove = find_shortest_indentation(text)
    lines = text.split('\n')
    processed: List[str] = []
    for line in lines:
        # Preserve empty lines and short lines without modification
        if len(line) >= indent_to_remove:
            processed_line = line[indent_to_remove:]
        else:
            processed_line = line
        processed.append(processed_line)
    
    return '\n'.join(processed)


def reindent(original_text: str, new_text: str) -> str:
    """Reapply original code's indentation pattern to new text.
    
    Process:
    1. Find base indentation of original_text
    2. Remove existing indentation from new_text
    3. Apply original's base indentation to unindented new_text
    
    Args:
        original_text: Source text providing indentation pattern
        new_text: Text to reformat using original's indentation
        
    Returns:
        new_text aligned with original_text's base indentation,
        maintaining new_text's internal structure
    """
    base_indent = find_shortest_indentation(original_text)
    unindented = unindent(new_text)

    reindented_lines: List[str] = []
    if "\t" in original_text:
        indent_str = '\t' * base_indent
    else:
        indent_str = ' ' * base_indent
    
    for line in unindented.split('\n'):
        if line.strip():  # Only indent lines with actual content
            reindented_lines.append(f"{indent_str}{line}")
        else:
            # Preserve empty lines and whitespace-only lines
            reindented_lines.append(line)
    return '\n'.join(reindented_lines)