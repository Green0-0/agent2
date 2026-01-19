from typing import List
import re
import bisect
from enum import Enum, IntEnum
from agent2.element import Element

# region CODE PARSERS
def parse_code(code: str, extension) -> List:
    from agent2.parsing.code_parsers.parse_python import parse_python_elements
    from agent2.parsing.code_parsers.parse_java import parse_java_elements
    from agent2.parsing.code_parsers.parse_javascript import parse_javascript_elements
    from agent2.parsing.code_parsers.parse_csharp import parse_csharp_elements

    parsers = {
        "py": parse_python_elements,
        "java": parse_java_elements,
        "js": parse_javascript_elements,
        "cs": parse_csharp_elements
    }
    
    parser_func = parsers.get(extension, lambda content: [Element("Content", content, "", 0, None, [])])
    return parser_func(code)
# endregion

# region INDENTATION FORMATTERS  
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
# endregion

# region LINE FORMATTERS
def enumerate_lines(text: str) -> str:
    """
    Add line numbers to each line of the input text.

    Splits the input text into lines, prepends each line with its corresponding
    line number followed by a space, and joins the lines back into a single
    string.

    Args:
        text: The input string to be enumerated.

    Returns:
        A string where each line is prefixed with its line number.
    """

    lines = text.splitlines()
    enumerated_lines = [f"{i} {line}" for i, line in enumerate(lines)]
    return '\n'.join(enumerated_lines)

def unenumerate_lines(text: str) -> tuple[int, list, str]:
    """
    Remove line numbers from text and return number of lines unenumerated, original line numbers, and the unenumerated text.
    
    Args:
        text: The input string to be unenumerated.
    
    Returns:
        A tuple (num_unenumerated, list_numbers, unenumerated_text) where
        - num_unenumerated: The number of lines in the input text that were unenumerated.
        - list_numbers: A list of the original line numbers that were unenumerated (or None), in order.
        - unenumerated_text: The input text with line numbers removed.
    """
    def is_int(text: str) -> bool:
        try:
            int(text)
            return True
        except ValueError:
            return False
    lines = text.splitlines()
    list_lines = []
    list_numbers = []
    num_unenumerated = 0
    # Check for {i} {line} format with singular space
    for line in lines:
        if re.match(r"^\d+\s+", line) is not None:
            list_lines.append(" ".join(line.split(" ")[1:]))
            list_numbers.append(int(line.split(" ")[0]))
            num_unenumerated += 1
        elif is_int(line.strip()):
            list_lines.append("")
            list_numbers.append(int(line))
            num_unenumerated += 1
        else:
            list_lines.append(line)
            list_numbers.append(None)
    return num_unenumerated, list_numbers, "\n".join(list_lines)

def remove_comments(text: str) -> str:
    """Remove lines that are entirely comments considering common comment formats.
    
    Supported comment line prefixes after stripping leading whitespace:
    //, #, /*, /**, * (for block comment continuation), % (MATLAB/LaTeX)
    
    Does not remove inline comments that appear after code on the same line.
    """
    lines = text.split('\n')
    filtered_lines = []
    
    for line in lines:
        line_stripped = line.lstrip()
        # Check if the line starts with any comment prefix
        if (line_stripped.startswith('//') or
            line_stripped.startswith('#') or
            line_stripped.startswith('/*') or
            line_stripped.startswith('/**') or
            line_stripped.startswith('*') or      # Block comment continuation
            line_stripped.startswith('%')):       # MATLAB, LaTeX, Erlang
            # This line is entirely a comment, skip it
            continue
        filtered_lines.append(line)
    
    return '\n'.join(filtered_lines)

def remove_spaces(text: str) -> str:
    """Remove all whitespace characters including spaces, tabs, and newlines."""
    return re.sub(r'\s+', '', text)
# endregion

# region CODE BLOCK EXTRACTORS
class Extraction_Mode(Enum):
    """Enum for specifying code block extraction mode."""
    FIRST = "first"     # Extract first code block
    LAST = "last"       # Extract last code block
    SPAN_MAX = "span_max"  # Extract between first and last triple backticks

def extract_codeblock(text: str, mode: Extraction_Mode = Extraction_Mode.FIRST):
    """
    Extract a code block from text based on specified mode.
    
    Args:
        text: Input text containing code blocks
        mode: Extraction mode (FIRST, LAST, or SPAN_MAX)
        
    Returns:
        Extracted code block content as string, or None if no valid code block found
        
    Modes:
        - FIRST: Extract first complete code block
        - LAST: Extract last complete code block
        - SPAN_MAX: Extract between first opening and last closing triple backticks
    """
    if "```" not in text:
        return None
    
    if mode == Extraction_Mode.FIRST:
        # Extract the first code block
        index1 = text.find("```")
        index1n = text.find("\n", index1)
        if index1n == -1:
            return None
        index2 = text.find("```", index1n + 1)
        return text[index1n:index2].strip() if index2 != -1 else text[index1n:].strip()
    
    elif mode == Extraction_Mode.LAST:
        # Extract the last code block
        index2 = text.rfind("```")
        index1 = text.rfind("```", 0, index2)
        if index1 == -1:
            index2n = text.find("\n", index2)
            if index2n == -1:
                return None
            return text[index2n:].strip()
        index1n = text.find("\n", index1)
        if index1n == -1:
            return None
        return text[index1n:index2].strip()
    
    elif mode == Extraction_Mode.SPAN_MAX:
        # Assume there's only one code block; extract it by finding the first ``` and the last ```
        index1 = text.find("```")
        if index1 == -1:
            return None
        index1n = text.find("\n", index1)
        if index1n == -1:
            return None
        index2 = text.rfind("```")
        if index2 == -1 or index1 == index2:
            return text[index1n:].strip()
        return text[index1n:index2].strip()

def extract_all_codeblocks(text: str) -> list:
    """
    Extract all complete code blocks from text.
    
    Args:
        text: Input text containing code blocks
        
    Returns:
        List of all extracted code block contents (empty list if none found)
    """
    codeblocks = []
    start_idx = 0
    
    while True:
        # Find the opening ```
        open_idx = text.find("```", start_idx)
        if open_idx == -1:
            break
        
        # Find the newline after the opening ```
        newline_idx = text.find("\n", open_idx)
        if newline_idx == -1:
            break
        
        # Find the closing ```
        close_idx = text.find("```", newline_idx + 1)
        if close_idx == -1:
            break
        
        # Extract the code block and add it to the list
        codeblock = text[newline_idx:close_idx].strip()
        codeblocks.append(codeblock)
        
        # Move the start index to after the closing ```
        start_idx = close_idx + 3
    
    return codeblocks
# endregion

# region CODE OPERATIONS
class EquivalencyLevel(IntEnum):
    """Represents different levels of equivalency between code blocks.
    
    The levels are ordered from least similar (1) to most similar (5):
    
    UNEQUAL (1): Code blocks have fundamentally different content that cannot
                 be reconciled by removing comments or whitespace.
                 
    DIFFER_COMMENTS (2): Code blocks are equivalent after removing comment-only 
                        lines and all whitespace. This means they have the same 
                        logical code structure but differ in comments and/or 
                        whitespace formatting.
                        
    DIFFER_WHITESPACE (3): Code blocks are equivalent after removing all 
                          whitespace (spaces, tabs, newlines). They have 
                          identical content but different formatting.
                          
    DIFFER_NEWLINE (4): Code blocks are equivalent after removing only newlines.
                       They differ only in line breaks but have identical 
                       spacing and content otherwise.
                       
    EQUAL (5): Code blocks are character-for-character identical, including
               all whitespace, comments, and formatting.
    
    Note: Higher numeric values indicate greater similarity. DIFFER_COMMENTS 
    implies DIFFER_WHITESPACE since comment removal also removes whitespace.
    """
    UNEQUAL = 1
    DIFFER_COMMENTS = 2
    DIFFER_WHITESPACE = 3
    DIFFER_NEWLINE = 4
    EQUAL = 5

def equate_code_blocks(text1: str, text2: str) -> EquivalencyLevel:
    """Compare two code blocks and return their level of equivalency.
    
    Performs hierarchical comparison starting from strictest (character-exact) 
    to most lenient (ignoring comments and whitespace). The function returns 
    the highest level of equivalency found.
    
    Comparison Levels:
    1. UNEQUAL: Fundamentally different content
    2. DIFFER_COMMENTS: Same after removing comment-only lines AND all whitespace
    3. DIFFER_WHITESPACE: Same after removing all whitespace (spaces, tabs, newlines)
    4. DIFFER_NEWLINE: Same after removing newlines only
    5. EQUAL: Texts are character-for-character identical
    
    Comment Removal Strategy:
    - Only removes lines that are entirely comments (after stripping leading whitespace)
    - Supports: //, #, /*, /**, *, % comment prefixes
    - Does NOT remove inline comments or ambiguous cases
    
    Args:
        text1: First code block to compare
        text2: Second code block to compare
        
    Returns:
        EquivalencyLevel: The highest level of equivalency between the texts.
        Higher numeric values (1-5) indicate greater similarity.
    """
    # Check exact equality first
    if text1 == text2:
        return EquivalencyLevel.EQUAL
    
    # Check if they differ only by newlines
    text1_no_newlines = text1.replace('\n', '')
    text2_no_newlines = text2.replace('\n', '')
    if text1_no_newlines == text2_no_newlines:
        return EquivalencyLevel.DIFFER_NEWLINE
    
    # Check if they differ only by whitespace
    text1_no_whitespace = remove_spaces(text1)
    text2_no_whitespace = remove_spaces(text2)
    if text1_no_whitespace == text2_no_whitespace:
        return EquivalencyLevel.DIFFER_WHITESPACE
    
    # Check if they differ only by comments (and whitespace)
    text1_no_comments = remove_comments(text1)
    text2_no_comments = remove_comments(text2)
    text1_no_comments_no_whitespace = remove_spaces(text1_no_comments)
    text2_no_comments_no_whitespace = remove_spaces(text2_no_comments)
    if text1_no_comments_no_whitespace == text2_no_comments_no_whitespace:
        return EquivalencyLevel.DIFFER_COMMENTS
    
    # If none of the above conditions are met, they are unequal
    return EquivalencyLevel.UNEQUAL

def lookup_text(search_block: str, search_for: str, strict_level: int = 3, case_sensitive = False) -> int:
    """Find the starting line number of a search pattern in a text block.
    
    The matching behavior varies by strictness level, with different handling of
    whitespace, indentation, and line breaks. Line numbers are 0-indexed.

    With strict_level 4, match blocks exactly but ignore empty lines.
    With strict_level 3, match unindented versions and ignore empty lines.
    With strict_level 2, match stripped lines and ignore empty lines.
    With strict_level 1, match whitespace-free versions of both texts.
    
    Args:
        search_block: The multi-line text to search within
        search_for: The multi-line pattern to search for
        strict_level: Matching strictness from 1 (lenient) to 4 (strictest)
        case_sensitive: True to perform case-sensitive matching
        
    Returns:
        int: Line number where match starts, or -1 if no match found
        
    Raises:
        ValueError: For invalid strict_level values
    """
    
    def find_subsequence(block_lines: list, for_lines: list) -> int:
        """Find first occurrence of for_lines sequence in block_lines.
        
        Helper for strict levels 2-4. Performs exact sequence matching.
        
        Args:
            block_lines: List of processed lines from search_block
            for_lines: List of processed lines from search_for
            
        Returns:
            int: Starting index in block_lines, or -1 if not found
        """
        len_for = len(for_lines)
        len_block = len(block_lines)
        if len_for == 0:
            return -1
        # Slide window through block lines to find pattern
        for i in range(len_block - len_for + 1):
            if block_lines[i:i+len_for] == for_lines:
                return i
        return -1

    def preprocess_block_lines(block: str, strict_level: int, is_search_block: bool = True) -> list:
        """Process text lines according to strictness level rules.
        
        Handles strict levels 2-4. For search_block, preserves original line numbers.
        
        Args:
            block: Input text to process
            strict_level: Current matching strictness level
            is_search_block: True if processing search_block, False for search_for
            
        Returns:
            list: Processed lines with original line numbers (if search_block)
        """
        lines = block.split('\n')
        processed_lines = []

        if strict_level == 4:
            # Level 4: Exact match but ignore empty lines
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if stripped_line:
                    # Preserve original lines with empty lines removed
                    if is_search_block:
                        processed_lines.append((i, line))  # (original line number, original content)
                    else:
                        processed_lines.append(line)

        elif strict_level == 3:
            # Level 3: Match unindented versions, ignore empty lines
            unindented_block = unindent(block)
            unindented_lines = unindented_block.split('\n')
            for original_line_number, line in enumerate(unindented_lines):
                stripped_line = line.strip()
                if stripped_line:
                    # Map back to original line numbers through unindent
                    if is_search_block:
                        processed_lines.append((original_line_number, line))
                    else:
                        processed_lines.append(line)

        elif strict_level == 2:
            # Level 2: Match stripped lines, ignore empty lines
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if stripped_line:
                    processed_line = stripped_line
                    if is_search_block:
                        processed_lines.append((i, processed_line))
                    else:
                        processed_lines.append(processed_line)
        
        return processed_lines

    def preprocess_block_strict1(block: str, is_search_block: bool = True) -> tuple:
        """Process text for strict level 1 by removing all whitespace.
        
        Creates concatenated string and tracks character offsets per line.
        
        Args:
            block: Input text to process
            is_search_block: True if processing search_block
            
        Returns:
            tuple: (concatenated string, cumulative lengths list) if search_block
                concatenated string otherwise
        """
        lines = block.split('\n')
        processed_lines = []
        cumulative_lengths = [0]  # Track character count per line for offset mapping
        current_length = 0

        for line in lines:
            # Remove all whitespace from line
            processed_line = re.sub(r'\s+', '', line)
            processed_lines.append(processed_line)
            current_length += len(processed_line)
            cumulative_lengths.append(current_length)

        concatenated = ''.join(processed_lines)

        if is_search_block:
            return concatenated, cumulative_lengths
        else:
            return concatenated

    # Validate strict_level before processing
    if strict_level not in [1, 2, 3, 4]:
        raise ValueError("strict_level must be 1, 2, 3, or 4")
    
    if not case_sensitive:
        search_block = search_block.lower()
        search_for = search_for.lower()

    # Handle strict level 1 separately due to different processing
    if strict_level == 1:
        # Process both texts into whitespace-free concatenations
        block_concatenated, cumulative_lengths = preprocess_block_strict1(search_block)
        for_concatenated = preprocess_block_strict1(search_for, is_search_block=False)
        
        # Find substring position in concatenated strings
        start_index = block_concatenated.find(for_concatenated)
        if start_index == -1:
            return -1
            
        # Map character index back to original line number
        line_index = bisect.bisect_right(cumulative_lengths, start_index) - 1
        return line_index

    else:
        # Process both texts according to strictness rules
        processed_block = preprocess_block_lines(search_block, strict_level)
        processed_for = preprocess_block_lines(search_for, strict_level, is_search_block=False)
        
        # Extract processed lines for matching
        block_lines = [line for (_, line) in processed_block]
        for_lines = processed_for
        
        # Find matching subsequence
        start_index = find_subsequence(block_lines, for_lines)
        if start_index == -1:
            return -1
            
        # Return original line number from search_block processing
        original_line_number = processed_block[start_index][0]
        return original_line_number
# endregion