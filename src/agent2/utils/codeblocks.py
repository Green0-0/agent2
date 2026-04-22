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