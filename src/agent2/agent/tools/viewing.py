from __future__ import annotations
from agent2.agent.core import Session
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from agent2.agent.core import Agent

def view(session: Session, agent: Agent, paths: str):
    """View the contents of multiple files or elements specified by a comma-separated list of paths.
    
    Each viewing path is composed of either a file path, an element path, or both (separated by double colons).
    
    If specific lines need to be viewed, or if a file extension is not supported, use the view_lines tool instead.

    Args:
        paths: A list of comma-separated paths to view.

    Examples:
        Task: Read the script my_script.py, the class element my_class (if found), and the nested inner function in custom_script.py.
        Tool Call: {"paths": "scripts/my_script.py, my_class, scripts/custom_script.py::my_class.outer_function.inner_function"}
    """
    results = []
    for path in [p.strip() for p in paths.split(',') if p.strip()]:
        results.append(view_path(session, agent, path))
    return "\n\n".join(results)
    
    
def view_path(session: Session, agent: Agent, path: str):
    """View the contents of a specific file or element.
    
    The viewing path is composed of either a file path, an element path, or both (separated by double colons).
    
    If specific lines need to be viewed, or if a file extension is not supported, use the view_lines tool instead.

    Args:
        path: A path to view.

    Examples:
        Task: Read the nested inner function in custom_script.py.
        Tool Call: {"path": "scripts/custom_script.py::my_class.outer_function.inner_function"}

        Task: Read the script my_script.py.
        Tool Call: {"path": "scripts/my_script.py"}

        Task: Read the class element my_class.
        Tool Call: {"path": "my_class"}
    """
    if "::" in path:
        file_path, element_path = path.split("::", 1)
        return view_element(session, agent, file_path, element_path)
    else:
        return view_file(session, agent, path)
    
    
def view_files(session: Session, agent: Agent, file_paths: str):
    """View an overview or the full contents of multiple files.
    
    An overview will be given instead of the full raw file by default. If the full file is desired, mark it with an asterisk (*).
    
    Args:
        file_paths: A list of comma-separated file paths to view.

    Examples:
        Task: Show the entirety of script_2.py, and an overview of script_1.py.
        Tool Call: {"file_paths": "scripts/script_1.py, scripts/script_2.py*"}
    """
    results = []
    for path in [p.strip() for p in file_paths.split(',') if p.strip()]:
        full = False
        if path.endswith('*'):
            full = True
            path = path[:-1]
        results.append(view_file(session, agent, path, full))
    return "\n\n".join(results)


def view_file(session: Session, agent: Agent, file_path: str, full: bool = False):
    """View the contents of a single file.
    
    If `full` is true, the entire file will be shown. Otherwise, an overview will be provided.
    
    Args:
        file_path: The file path to view.
        full: Whether to show the full file or an overview.

    Examples:
        Task: Show the entirety of script_2.py.
        Tool Call: {"file_path": "scripts/script_2.py", "full": true}

        Task: Show an overview of script_1.py.
        Tool Call: {"file_path": "scripts/script_1.py", "full": false}
    """
    file = session.files.get(file_path)
    if not file: return f"Error: File {file_path} not found."
    text = file.current_state.bytes.decode('utf-8', errors='replace')
    if not full:
        lines = text.split('\n')
        if len(lines) > 50:
            text = '\n'.join(lines[:50]) + f"\n\n... (file truncated, {len(lines) - 50} more lines. Use full=True to view entire file)"
    return f"--- {file_path} ---\n{text}"
    
def views_at(session: Session, agent: Agent, paths: str, full: bool = False):
    """View the innermost code elements at specific lines across multiple files.
    
    The format for a singular view is {{file_path}}::{{line}}. If `full` is true, the entire element is guaranteed to be shown. Otherwise, it may be simplified if it is too long.
    
    Note: If no specific element is present at a line, this tool will instead display everything from that line down up to the nearest element.
    
    If specific lines need to be viewed, or if a file extension is not supported, use the view_lines tool instead.

    Args:
        paths: A list of comma-separated file paths with lines to view.
        full: Whether to show the full element or an overview.

    Examples:
        Task: Show the entirety of the innermost element found at line 100 in script_1.py, and line 200 in script_2.py.
        Tool Call: {"paths": "scripts/script_1.py::100, scripts/script_2.py::200", "full": true}
    """
    results = []
    for path in [p.strip() for p in paths.split(',') if p.strip()]:
        if "::" in path:
            file_path, line_str = path.split("::", 1)
            try:
                results.append(view_at(session, agent, file_path, int(line_str), full))
            except ValueError:
                results.append(f"Error: Invalid line number in {path}")
        else:
            results.append(f"Error: Missing :: in {path}")
    return "\n\n".join(results)
    
def view_at(session: Session, agent: Agent, file_path: str, line: int, full: bool = False):
    """View the innermost code element located at a specific line within a file.
    
    If `full` is true, the entire element is guaranteed to be shown. Otherwise, it may be simplified if it is too long.
    
    Note: If no specific element is present at a line, this tool will instead display everything from that line down up to the nearest element.
    
    If specific lines need to be viewed, or if a file extension is not supported, use the view_lines tool instead.

    Args:
        file_path: The file path to view the element of.
        line: The line number of the element to view.
        full: Whether to show the full element or an overview.

    Examples:
        Task: Show the entirety of the innermost element found at line 100 in script_2.py.
        Tool Call: {"file_path": "scripts/script_2.py", "line": 100, "full": true}

        Task: Show an overview of the innermost element found at line 200 in script_1.py. It may be reduced to an overview if its content is too long.
        Tool Call: {"file_path": "scripts/script_1.py", "line": 200, "full": false}
    """
    file = session.files.get(file_path)
    if not file: return f"Error: File {file_path} not found."
    if hasattr(file, 'code_nodes'):
        best_node, best_len = None, float('inf')
        for node in file.code_nodes.values():
            start_line = node.full_block.start_point[0] + 1
            end_line = node.full_block.end_point[0] + 1
            if start_line <= line <= end_line:
                length = node.full_block.end_byte - node.full_block.start_byte
                if length < best_len:
                    best_len = length
                    best_node = node
        if best_node:
            text = file.current_state.bytes[best_node.full_block.start_byte:best_node.full_block.end_byte].decode('utf-8', errors='replace')
            if not full and len(text.split('\n')) > 50:
                text = '\n'.join(text.split('\n')[:50]) + f"\n\n... (truncated)"
            return f"--- {file_path}::{best_node.llm_path} ---\n{text}"
    start, end = file.current_state.get_line_byte_range(line)
    text = file.current_state.bytes[start:].decode('utf-8', errors='replace')
    if not full and len(text.split('\n')) > 50:
        text = '\n'.join(text.split('\n')[:50]) + "\n\n... (truncated)"
    return f"--- {file_path} (from line {line}) ---\n{text}"
    
def view_element(session: Session, agent: Agent, file_path: str, element_path: str, full: bool = False):
    """View a specific code element (e.g. class or function) within a file.
    
    If `full` is true, the entire element is guaranteed to be shown. Otherwise, it may be simplified if it is too long.
    
    If specific lines need to be viewed, or if a file extension is not supported, use the view_lines tool instead.

    Args:
        file_path: The file path to view the element of.
        element_path: The element path within the file.
        full: Whether to show the full element or an overview.

    Examples:
        Task: Show the entirety of my_class.
        Tool Call: {"file_path": "scripts/script_2.py", "element_path": "my_class", "full": true}

        Task: Show an overview of the function my_func inside my_class. It may be reduced to an overview if its content is too long.
        Tool Call: {"file_path": "scripts/script_1.py", "element_path": "my_class.my_func", "full": false}
    """
    file = session.files.get(file_path)
    if not file: return f"Error: File {file_path} not found."
    if not hasattr(file, 'code_nodes'): return f"Error: {file_path} is not a parsed code file."
    node = file.code_nodes.get(element_path)
    if not node: return f"Error: Element {element_path} not found in {file_path}."
    text = file.current_state.bytes[node.full_block.start_byte:node.full_block.end_byte].decode('utf-8', errors='replace')
    if not full and len(text.split('\n')) > 50:
        text = '\n'.join(text.split('\n')[:50]) + f"\n\n... (truncated)"
    return f"--- {file_path}::{element_path} ---\n{text}"


def view_multi_lines(session: Session, agent: Agent, file_line_paths: str):
    """View specific line ranges across multiple files.
    
    The format for a singular view is {{file_path}}::{{start_line}}::{{end_line}}.

    Args:
        file_line_paths: A list of comma-separated file paths with line ranges.

    Examples:
        Task: Show lines 100-200 from script_1.py, and lines 300-400 from script_2.py.
        Tool Call: {"file_line_paths": "scripts/script_1.py::100::200, scripts/script_2.py::300::400"}
    """
    results = []
    for path in [p.strip() for p in file_line_paths.split(',') if p.strip()]:
        parts = path.split("::")
        if len(parts) == 3:
            try:
                results.append(view_lines(session, agent, parts[0], int(parts[1]), int(parts[2])))
            except ValueError:
                results.append(f"Error: Invalid line numbers in {path}")
        else:
            results.append(f"Error: Invalid format {path}. Expected file::start::end")
    return "\n\n".join(results)
    
    
def view_lines(session: Session, agent: Agent, file_path: str, line_start: int, line_end: int):
    """View a specific start/end line range within a file.
    
    Args:
        file_path: The file path to view the lines of.
        line_start: The starting line number (inclusive).
        line_end: The ending line number (inclusive).

    Examples:
        Task: Show lines 100-200 from script_1.py.
        Tool Call: {"file_path": "scripts/script_1.py", "line_start": 100, "line_end": 200}
    """
    file = session.files.get(file_path)
    if not file: return f"Error: File {file_path} not found."
    start_byte = file.current_state.get_line_byte_range(line_start)[0]
    end_byte = file.current_state.get_line_byte_range(line_end)[1]
    text = file.current_state.bytes[start_byte:end_byte].decode('utf-8', errors='replace')
    return f"--- {file_path} (lines {line_start}-{line_end}) ---\n{text}"