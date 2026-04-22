from agent2.agent.tool_settings_depreciated import ToolSettings
from agent2.file import File
from agent2.agent.agent_state import AgentState
from agent2.parsing.parser import reindent, extract_codeblock, unenumerate_lines
from agent2.parsing.lookup import lookup_text
from agent2.utils.tool_utils import find_file
import re
import difflib

def get_edit_diff(before: str, after: str):
    diff = difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            lineterm=''
        )
    return '\n'.join(diff)

def replace_lines(state: AgentState, settings: ToolSettings, path: str, line_start: int, line_end: int, replacement: str):
    """
    Replace lines in a file with a replacement string. Make sure to include all the lines that need to be removed and substituted with the replacement code, which must be written in its entirety. Returns a diff of the edits made.
    
    Args:
        path: File path
        line_start: Starting line number, inclusive
        line_end: Ending line number, inclusive
        replacement: String to replace lines with

    Example:
        Replace lines 100-100 (line 100) of auth.py with ``i = 5``
    Tool Call:
        {"name": "replace_lines", "arguments": {"path": "src/auth/auth.py", "line_start": 100, "line_end": 100, "replacement": "i = 5"}}
    """
    if line_start < 0 or line_end < 0:
        raise ValueError("Line numbers must be non-negative")
    if line_start > line_end:
        raise ValueError("Line start must be less than or equal to line end")
    
    file = find_file(state, path)
    removed_line_numbers = unenumerate_lines(replacement)
    if removed_line_numbers[0] > 0.6 * len(removed_line_numbers[1]):
        replacement = removed_line_numbers[2]
    replacement = extract_codeblock(replacement)
    content = file.content
    lines = content.splitlines()
    if line_start >= len(lines) or line_end >= len(lines):
        raise ValueError("Line numbers out of range")
    original_chunk = "\n".join(lines[line_start:line_end+1])
    if settings.reindent_outputs:
        new_chunk = reindent(original_chunk, replacement)
    else:
        new_chunk = replacement
    if lookup_text(original_chunk, new_chunk, settings.match_strict_level) == 0:
        raise ValueError("No changes made!")
    
    lines[line_start:line_end+1] = new_chunk.splitlines()
    new_content = "\n".join(lines)
    file.content = new_content
    
    file.update_elements()
    return ("Success:\n" + get_edit_diff(content, file.content), None)

def replace_block(state: AgentState, settings: ToolSettings, path: str, block: str, replacement: str):
    """
    Replace a block in a file with a replacement string. You must output the entire block being replaced, and every line that must be deleted, which must be written in its entirety. Returns a diff of the edits made.
    
    Args:
        path: File path
        block: Block to replace, every line must be typed in its entirety and matched exactly
        replacement: String to replace block with

    Example:
        Replace block ```\ndef login():\n    i = 5\n``` in auth.py with ```\ndef login(username, password):\n    i = 6\n```
    Tool Call:
        {"name": "replace_block", "arguments": {"path": "src/auth/auth.py", "block": "def login():\\n    i = 5", "replacement": "def login(username, password):\\n    i = 6"}}
    """
    file = find_file(state, path)
    
    block_start_line = lookup_text(file.content, block, strict_level=settings.match_strict_level)
    block_end_line = block_start_line + len(block.split("\n")) - 1

    if block_start_line < 0 or block_end_line < 0:
        raise ValueError("Block not found")
    
    if block_start_line > block_end_line:
        raise ValueError("This is an extremely strange error that should not occur: Block start must be less than or equal to block end!")
    
    return replace_lines(state, settings, path, block_start_line, block_end_line, replacement)

import functools
from agent2.agent.tool_settings_depreciated import ToolSettings
from agent2.file import File
from agent2.element import Element
from agent2.agent.agent_state import AgentState
from agent2.parsing.parser import reindent, unenumerate_lines, extract_codeblock, enumerate_lines, unindent
from agent2.parsing.lookup import lookup_text
from agent2.utils.tool_utils import find_file

def replace_element(state: AgentState, settings: ToolSettings, path: str, identifier: str, replacement: str):
    """
    Replace an element and all its subelements with a replacement string. Always edit the innermost elements and not outer elements. Replace one element at a time. Make sure to specify the element path exactly, and the entirety of the replacement code, otherwise it will be cut off; if you want to edit mymethod within myclass, use myclass.mymethod. Returns a diff of the edits made.
    
    Args:
        path: File path
        identifier: Identifier of the element to replace
        replacement: String to replace lines with
    
    Example:
        Replace element auth in auth.py with ```python\ndef auth():\n\tpass\n```
    Tool Call:
        {"name": "replace_element", "arguments": {"path": "src/auth/auth.py", "identifier": "auth", "replacement": "def auth():\\n\\tpass"}}
    """
    print("REPLACEMENT")
    print(replacement)
    file = find_file(state, path)
    
    all_elements = []
    stack = list(file.elements)
    while stack:
        element = stack.pop()
        all_elements.append(element)
        stack.extend(element.elements)
    
    element = next((e for e in all_elements if e.identifier.lower() == identifier.lower()), None)
    if not element:
        # Find closest element
        element = next((e for e in all_elements if identifier.lower() in e.identifier.lower()), None)
        if not element:
            element = next((e for e in all_elements if identifier.lower().split(".")[-1] in e.identifier.lower()), None)
        if not element:
            element = next((e for e in all_elements if e.identifier.lower().split(".")[-1] in identifier.lower()), None)
        if not element:
            raise ValueError(f"Element {identifier} not found in file {path}")
        else:
            raise ValueError(f"Element {identifier} not found in file {path}. Did you mean {element.identifier}?")
    
    line_start = element.line_start
    line_end = line_start + len(element.content.splitlines())

    removed_line_numbers = unenumerate_lines(replacement)
    if removed_line_numbers[0] > 0.6 * len(removed_line_numbers[1]):
        replacement = removed_line_numbers[2]
    if "```" in replacement.splitlines()[0] and "```" in replacement.splitlines()[-1]:
        replacement = extract_codeblock(replacement)

    content = file.content
    lines = content.splitlines()
    if line_start > len(lines) or line_end > len(lines) or line_start > line_end:
        raise ValueError("This is an extremely strange error that should not occur: Element numbers out of range")
    
    original_chunk = "\n".join(lines[line_start:line_end])
    print("ORIGINAL:")
    print(original_chunk)
    if settings.reindent_outputs:
        new_chunk = reindent(original_chunk, replacement)
    else:
        new_chunk = replacement
    print("NEW:")
    print(new_chunk)
    if lookup_text(original_chunk, new_chunk, settings.match_strict_level) == 0:
        raise ValueError("No changes made!")
    
    lines[line_start:line_end] = new_chunk.splitlines()
    new_content = "\n".join(lines)
    file.content = new_content
    file.update_elements()
    return ("Success:\n" + get_edit_diff(content, file.content), None)

def open_element(state: AgentState, settings: ToolSettings, path: str, identifier: str):
    """
    Open up an element, will allow you to edit that element. Always prioritize opening inner functions and not outer classes and functions. Make sure to specify the element path exactly; if you want to open mymethod within myclass, use myclass.mymethod. After editing, the file will be closed and any diffs (from editing) will be shown.
    
    Args:
        path: File path
        identifier: Element identifier to view

    Example:
        Open element auth and prepare to edit it
    Tool Call:
        {"name": "open_element", "arguments": {"path": "src/auth/auth.py", "identifier": "auth"}}
    """
    file = find_file(state, path)
    
    all_elements = []
    stack = list(file.elements)
    while stack:
        element = stack.pop()
        all_elements.append(element)
        stack.extend(element.elements)
    
    element = next((e for e in all_elements if e.identifier.lower() == identifier.lower()), None)
    if not element:
        # Find closest element
        element = next((e for e in all_elements if identifier.lower() in e.identifier.lower()), None)
        if not element:
            element = next((e for e in all_elements if identifier.lower().split(".")[-1] in e.identifier.lower()), None)
        if not element:
            element = next((e for e in all_elements if e.identifier.lower().split(".")[-1] in identifier.lower()), None)
        if not element:
            raise ValueError(f"Element {identifier} not found in file {path}")
        else:
            raise ValueError(f"Element {identifier} not found in file {path}. Did you mean {element.identifier}?")
    if len(element.content.splitlines()) > 600:
        raise ValueError("This element is way too large to directly edit!")
    if settings.secretly_save:
        if (file, element) not in state.saved_elements:
            state.saved_elements.append((file, element))
    partial_open_element = functools.partial(open_element_final, state, settings, path, identifier)
    return (f"```python\n{element.to_string(unindent_text = settings.unindent_inputs, number_lines = settings.number_lines, mask_subelements = False)}\n```\nIf you would like to make any changes, output a replacement code block, wrapped within ``` for the entirety of this element. Do not output any other code blocks besides this replacement. You do not need to use any tool calls for this operation, nor do you need to include line numbers in the code you write. If you would like to cancel, do not output a code block and instead output a cancellation reason.", partial_open_element)
        
def open_element_final(state: AgentState, settings: ToolSettings, path: str, identifier: str, input: str):
    """
    Close the file and parse any edits
    """
    state.chat.messages.pop()

    if input.count("```") < 2:
        return ("No edits made with message:\n" + input + "\nNote that edits made within open_element need to be wrapped inside code blocks.", None, None)

    last_closing = input.rfind('```')
    # Find the opening triple backticks before the last closing
    opening_start = input.find('```')
    if opening_start == -1:
        return ("No edits made with message:\n" + input + "\nNote that edits made within open_element need to be wrapped inside code blocks.", None, None)
    newline_pos = input.find('\n', opening_start)
    if newline_pos == -1:
        newline_pos = input.find(' ', opening_start) + 1
    else:
        code_start = newline_pos + 1
    
    # Parse input, check if code block is contained, pop last chat message
    try:
        return replace_element(state, settings, path, identifier, input[code_start:last_closing])
    except Exception as e:
        if "No changes made!" in str(e):
            raise Exception("While the element was succesfully opened, no edits were made. Try something else.")
        else:
            raise

def open_element_at(state: AgentState, settings: ToolSettings, path: str, line: int):
    """
    Open up the innermost element at a specific line in a file, will allow you to edit that element. Always prioritize opening inner functions and not outer classes and functions. After editing, the file will be closed and any diffs (from editing) will be shown.

    Args:
        path: Path to the file
        line: Zero-indexed line number in the file
    
    Example:
        Open element at line 5 in src/app.py
    Tool Call:
        {"name": "open_element_at", "arguments": {"path": "src/app.py", "line": 5}}
    """
    # Normalize path
    file = find_file(state, path)
    
    # Validate line number
    lines_in_file = len(file.content.split('\n'))
    if line < 0 or line >= lines_in_file:
        raise ValueError(f"Line {line} is out of bounds for file {path} (0-based, total lines {lines_in_file})")
    
    # Find the innermost element
    best_element = None
    best_depth = -1
    stack = [(element, 0) for element in file.elements]  # (element, depth)
    
    while stack:
        element, depth = stack.pop()
        line_count = len(element.content.split('\n'))
        end_line = element.line_start + line_count - 1
        if element.line_start <= line <= end_line:
            if depth > best_depth:
                best_element = element
                best_depth = depth
            # Add children to stack with incremented depth
            stack.extend([(child, depth + 1) for child in element.elements])
    
    if not best_element:
        raise ValueError(f"No element found at line {line} in file {path}")
    
    # Call open_element with the found identifier
    return open_element(state, settings, path, best_element.identifier)

def replace_element_at(state: AgentState, settings: ToolSettings, path: str, line: int, replacement: str):
    """
    Replace the innermost element and all its subelements at a specific line in a file with a replacement string. Always edit the innermost elements and not outer elements. Replace one element at a time. Returns a diff of the edits made.

    Args:
        path: Path to the file
        line: Zero-indexed line number in the file
        replacement: Replacement code for the element
    
    Example:
        Replace element at line 5 in src/app.py with new code
    Tool Call:
        {"name": "replace_element_at", "arguments": {"path": "src/app.py", "line": 5, "replacement": "def new_func():\\n    pass"}}
    """
    file = find_file(state, path)
    
    # Validate line number
    lines_in_file = len(file.content.split('\n'))
    if line < 0 or line >= lines_in_file:
        raise ValueError(f"Line {line} is out of bounds for file {path} (0-based, total lines {lines_in_file})")
    
    # Find the innermost element
    best_element = None
    best_depth = -1
    stack = [(element, 0) for element in file.elements]  # (element, depth)
    
    while stack:
        element, depth = stack.pop()
        line_count = len(element.content.split('\n'))
        end_line = element.line_start + line_count - 1
        if element.line_start <= line <= end_line:
            if depth > best_depth:
                best_element = element
                best_depth = depth
            # Add children to stack with incremented depth
            stack.extend([(child, depth + 1) for child in element.elements])
    
    if not best_element:
        raise ValueError(f"No element found at line {line} in file {path}")
    
    # Call replace_element with the found identifier and replacement
    return replace_element(state, settings, path, best_element.identifier, replacement)