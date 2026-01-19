from typing import List
from agent2.agent.tool_settings_depreciated import ToolSettings
from agent2.file import File
from agent2.element import Element
from agent2.agent.agent_state import AgentState
from agent2.utils.tool_utils import find_file, truncate_lines
from agent2.parsing.parser import enumerate_lines
from agent2.parsing.parser import unindent

def get_overlaps(file: File, line_start: int, line_end: int) -> List[Element]:
    overlapping_elements = []
    
    def collect_overlapping(elements: List[Element]):
        for element in elements:
            content_lines = element.content.split('\n')
            element_line_count = len(content_lines)
            e_start = element.line_start
            e_end = e_start + element_line_count - 1
            if e_start <= line_end and e_end >= line_start:
                overlapping_elements.append(element)
                collect_overlapping(element.elements)
    
    collect_overlapping(file.elements)
    
    exception_candidates = []
    for elem in overlapping_elements:
        if not elem.elements:
            content_lines = elem.content.split('\n')
            e_line_count = len(content_lines)
            e_start = elem.line_start
            e_end = e_start + e_line_count - 1
            overlap_start = max(e_start, line_start)
            overlap_end = min(e_end, line_end)
            if overlap_start > overlap_end:
                continue
            overlap_lines = overlap_end - overlap_start + 1
            if overlap_lines >= 4:
                pre_lines = max(0, line_start - e_start)
                post_lines = max(0, e_end - line_end)
                if pre_lines <= 2 and post_lines <= 2:
                    exception_candidates.append(elem)
    
    if exception_candidates:
        deepest = max(exception_candidates, key=lambda x: len(x.identifier.split('.')))
        return [deepest]
    else:
        return overlapping_elements

def format_subelements_description(elements):
    """Format the description of subelements."""
    if not elements:
        return ""
    examples = [elements[i].identifier for i in range(min(2, len(elements)))]
    return f"This element has {len(elements)} subelements, you may reference them with a dot after this element's identifier, ie: `{'`, `'.join(examples)}`, etc"

def count_all_elements(file):
    """Count all elements including nested ones in a file."""
    total = 0
    stack = list(file.elements)
    while stack:
        total += 1
        element = stack.pop()
        stack.extend(element.elements)
    return total

# View functions
def view_lines(state: AgentState, settings: ToolSettings, line_start: int, line_end: int, path: str):
    """
    View a range of lines in a file
    
    Args:
        line_start: Starting line number, inclusive
        line_end: Ending line number, inclusive
        path: File path to view

    Example:
        View lines 100-125 of auth.py
    Tool Call:
        {"name": "view_lines", "arguments": {"line_start": 100, "line_end": 125, "path": "src/auth/auth.py"}}
    """
    # Validate line numbers
    if line_start < 0 or line_end < 0:
        raise ValueError("Line numbers must be non-negative")
    if line_start > line_end:
        raise ValueError("Line start must be less than or equal to line end")
    
    # Get the file
    file = find_file(state, path)
    
    # Save elements if needed
    elements = []
    if settings.secretly_save:
        elements = get_overlaps(file, line_start, line_end)
        for element in elements:
            if (file, element) not in state.saved_elements: 
                state.saved_elements.append((file, element))
    
    # Prepare content
    content = file.content
    if settings.unindent_inputs:
        content = unindent(content)
    if settings.number_lines:
        content = enumerate_lines(content)
    
    content_lines = content.splitlines()
    
    # Validate line range
    if line_start >= len(content_lines) or line_end >= len(content_lines):
        raise ValueError("Line numbers out of range")
    
    # Extract and format lines
    selected_lines = content_lines[line_start:line_end+1]
    truncated_lines, truncation_message = truncate_lines(settings, selected_lines)
    truncated_lines = "\n".join(truncated_lines)
    
    # Format header and output
    header = f"Viewing file {file.path}, lines {line_start}-{line_end}"
    element_list = f"Element(s) `{'`, `'.join(el.identifier for el in elements)}`" if elements else ""
    
    result = f"{header}"
    if element_list:
        result += f"\n{element_list}"
    result += f"\n```\n{truncated_lines}\n```{truncation_message}"
    
    return (result, None)


def view_element(state: AgentState, settings: ToolSettings, path: str, identifier: str):
    """
    View an element in a file. Make sure to specify the element path exactly; if you want to view mymethod within myclass, use myclass.mymethod.
    
    Args:
        identifier: Element identifier to view

    Example:
        View element auth
    Tool Call:
        {"name": "view_element", "arguments": {"path": "src/auth/auth.py", "identifier": "auth"}}
    """
    # Get the file
    file = find_file(state, path)
    # Find the element
    all_elements = []
    stack = list(file.elements)
    while stack:
        element = stack.pop()
        all_elements.append(element)
        stack.extend(element.elements)
    element = next((e for e in all_elements if e.identifier.lower() == identifier.lower()), None)
    if not element:
        matching_elements = []
        for e in all_elements:
            if identifier.lower() in e.identifier.lower():
                matching_elements.append(e)
        if len(matching_elements) == 0:
            for e in all_elements:
                if identifier.lower().split(".")[-1] in e.identifier.lower():
                    matching_elements.append(e)
            if len(matching_elements) == 0:
                raise ValueError(f"Element {identifier} not found in file {path}")
        raise ValueError(f"Element `{identifier}` not found in file {path}. Closest matches: `{'`, `'.join(e.identifier for e in matching_elements)}`")
    # Save element if needed
    if settings.secretly_save:
        if (file, element) not in state.saved_elements:
            state.saved_elements.append((file, element))
    # Get element content
    content = element.to_string(number_lines=settings.number_lines, unindent_text=settings.unindent_inputs, mask_subelements=False)
    # Truncate if needed
    lines = content.splitlines()
    truncated_lines, truncation_message= truncate_lines(settings, lines)
    content = "\n".join(truncated_lines)
    
    # Format header and element info
    start_line = element.line_start
    end_line = element.line_start + len(element.content.splitlines()) - 1
    header = f"Viewing file {file.path}, lines {start_line}-{end_line}"
    element_header = f"Element `{element.identifier}`"
    result = f"{header}\n{element_header}\n```\n{content}\n```"
    # Add subelements info if any
    if element.elements:
        subelements_desc = format_subelements_description(element.elements)
        result += f"\n{subelements_desc}"
    if truncation_message:
        result += truncation_message
    return (result, None)


def view_element_at(state: AgentState, settings: ToolSettings, path: str, line: int):
    """
    View the innermost element at a specific line in a file.
    
    Args:
        path: Path to the file
        line: Zero-indexed line number in the file
    
    Example:
        View element at line 5 in src/app.py
    Tool Call:
        {"name": "view_element_at", "arguments": {"path": "src/app.py", "line": 5}}
    """
    # Find the file
    file = find_file(state, path)
    
    # Validate line number
    lines_in_file = len(file.content.split('\n'))
    if line < 0 or line >= lines_in_file:
        raise ValueError(f"Line {line} is out of bounds for file {path} (0-based, {lines_in_file} total lines)")
    
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
    # Call view_element with the found identifier
    return view_element(state, settings, path, best_element.identifier)


def view_file(state: AgentState, settings: ToolSettings, path: str):
    """
    View the general contents of a file.
    
    Args:
        path: File path

    Example:
        View file src/auth/auth.py

    Tool Call:
        {"name": "view_file", "arguments": {"path": "src/auth/auth.py"}}
    """
    # Get the file
    file = find_file(state, path)
    
    # Prepare content
    content = file.to_string(unindent_text=settings.unindent_inputs, number_lines=settings.number_lines)
    
    # Truncate if needed
    lines = content.splitlines()
    truncated_lines = truncate_lines(settings, lines)
    content = "\n".join(truncated_lines)
    
    # Get stats
    line_count = len(file.content.splitlines())
    element_count = count_all_elements(file)
    
    # Format header
    header = f"Viewing file {file.path}, {line_count} lines, {element_count} elements"

    result = f"{header}\n```\n{truncated_lines}\n```"
    
    return (result, None)


def view_file_raw(state: AgentState, settings: ToolSettings, path: str):
    """
    View the contents of a file.
    
    Args:
        path: File path

    Example:
        View file src/auth/auth.py

    Tool Call:
        {"name": "view_file_raw", "arguments": {"path": "src/auth/auth.py"}}
    """
    # Get the file
    file = find_file(state, path)
    
    # Prepare content
    content = file.content
    if settings.unindent_inputs:
        content = unindent(content)
    if settings.number_lines:
        content = enumerate_lines(content)
    
    # Truncate if needed
    lines = content.splitlines()
    truncated_lines = truncate_lines(lines, settings)
    content = "\n".join(truncated_lines)
    
    # Get stats
    line_count = len(file.content.splitlines())
    element_count = count_all_elements(file)
    
    # Format header
    header = f"Viewing file {file.path}, {line_count} lines, {element_count} elements"
    
    result = f"{header}\n```\n{truncated_lines}\n```"
    return (result, None)
