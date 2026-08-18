from __future__ import annotations
from typing import TYPE_CHECKING
from agent2.agent.core import Session
from agent2.code_parser.file import File, CodeFile
from agent2.code_parser.objects import CodeEdit, CodeState
from agent2.code_parser.languages.adapters import get_adapter_for_extension

if TYPE_CHECKING:
    from agent2.agent.core import Agent


def move_files(session: Session, agent: Agent, paths: str, make_dir: bool = False):
    """Move files or directories based on a list of comma-separated movement paths.
    
    Each path must be formatted as {original_location}>{new_location}, ensuring there is exactly one angle bracket pointing right per movement. Renaming files is also supported.
    
    Args:
        paths: A list of comma-separated movement paths.
        make_dir: If true, missing directories will be created automatically.

    Examples:
        Task: Move script_1 and rename it to script_2 (creating the folder if it doesn't exist), and rename pic to picture.
        Tool Call: {"paths": "scripts/script_1.py>new_scripts/script_2.py, folder/pic.png>folder/picture.png", "make_dir": true}
    """
    results = []
    for move_path in [p.strip() for p in paths.split(',') if p.strip()]:
        if ">" not in move_path:
            results.append(f"Error: Invalid syntax in '{move_path}'. Expected src>dst.")
            continue
        src, dst = move_path.split(">", 1)
        src, dst = src.strip(), dst.strip()
        file = session.files.get(src)
        if not file:
            results.append(f"Error: Source file {src} not found.")
            continue
        file.path = dst
        del session.files[src]
        session.files[dst] = file
        results.append(f"Moved {src} to {dst} in memory.")
    return "\n".join(results)


def make_empty_files(session: Session, agent: Agent, file_paths: str, make_dir: bool = False):
    """Create an empty file at each specified comma-separated file path.
    
    Args:
        file_paths: A list of comma-separated file paths to create.
        make_dir: If true, missing directories will be created automatically.

    Examples:
        Task: Create empty files script_1.py and script_2.py in the scripts folder. Create the scripts folder if it doesn't exist.
        Tool Call: {"file_paths": "scripts/script_1.py, scripts/script_2.py", "make_dir": true}
    """
    results = []
    for path in [p.strip() for p in file_paths.split(',') if p.strip()]:
        adapter = get_adapter_for_extension(path)
        if adapter:
            session.files[path] = CodeFile(path, adapter, b"")
        else:
            session.files[path] = File(path, b"")
        results.append(f"Created empty file {path} in memory.")
    return "\n".join(results)


def replace_file(session: Session, agent: Agent, file_path: str, new_content: str):
    """Replace the entire contents of a file with the provided string.
    
    Args:
        file_path: The file path to replace the contents of.
        new_content: The new contents of the file.

    Examples:
        Task: Replace the script my_script.py with the new script.
        Tool Call: {"file_path": "scripts/my_script.py", "new_content": "import ..."}
    """
    from agent2.code_parser.objects import CodeState
    file = session.files.get(file_path)
    if not file: return f"Error: File {file_path} not found."
    new_bytes = new_content.encode('utf-8')
    if hasattr(file, 'parse_to_bytes'):
        file.parse_to_bytes(new_bytes, sync_original=False)
    else:
        file.current_state = CodeState(new_bytes)
    return f"Replaced content of {file_path}."
    
    
def replace_element(session: Session, agent: Agent, file_path: str, element_path: str, new_content: str):
    """Replace the contents of a specific code element (e.g. class or function) at a given file path.
    
    If specific lines need to be edited, or if a file extension is not supported, use the replace_lines tool instead.

    Args:
        file_path: The file path to replace the element in.
        element_path: The path of the element within the file (e.g. 'my_class.inner_function').
        new_content: The new contents of the element.

    Examples:
        Task: Replace the inner function in my_class of my_script.py with the specified code.
        Tool Call: {"file_path": "scripts/my_script.py", "element_path": "my_class.inner_function", "new_content": "def inner_function..."}
    """
    file = session.files.get(file_path)
    if not file: return f"Error: File {file_path} not found."
    if not hasattr(file, 'code_nodes'): return f"Error: {file_path} is not a parsed code file."
    node = file.code_nodes.get(element_path)
    if not node: return f"Error: Element {element_path} not found in {file_path}."
    edit = CodeEdit(
        start_byte=node.full_block.start_byte,
        end_byte=node.full_block.end_byte,
        start_point=node.full_block.start_point,
        end_point=node.full_block.end_point,
        new_text=new_content.encode('utf-8')
    )
    file.apply_edit_and_reparse(edit)
    return f"Replaced element {element_path} in {file_path}."
    
def replace_element_at(session: Session, agent: Agent, file_path: str, line: int, new_content: str):
    """Replace the innermost code element located at a specific line number within a file.
    
    If specific lines need to be edited, or if a file extension is not supported, use the replace_lines tool instead.

    Args:
        file_path: The file path containing the element to replace.
        line: The line number where the target element is located.
        new_content: The new contents of the element.

    Examples:
        Task: Replace the element present at line 10 of my_script.py with the specified code.
        Tool Call: {"file_path": "scripts/my_script.py", "line": 10, "new_content": "def inner_function..."}
    """
    # WARNING: THIS SHOULD NOT BE USED, AS A MISFIRE FROM WRITING THE WRONG LINE WILL DESTROY THE ELEMENT
    file = session.files.get(file_path)
    if not file: return f"Error: File {file_path} not found."
    if not hasattr(file, 'code_nodes'): return f"Error: {file_path} is not a parsed code file."
    best_node, best_len = None, float('inf')
    for node in file.code_nodes.values():
        start_line = node.full_block.start_point[0] + 1
        end_line = node.full_block.end_point[0] + 1
        if start_line <= line <= end_line:
            length = node.full_block.end_byte - node.full_block.start_byte
            if length < best_len:
                best_len, best_node = length, node
    if not best_node: return f"Error: No element found at line {line}."
    edit = CodeEdit(
        start_byte=best_node.full_block.start_byte,
        end_byte=best_node.full_block.end_byte,
        start_point=best_node.full_block.start_point,
        end_point=best_node.full_block.end_point,
        new_text=new_content.encode('utf-8')
    )
    file.apply_edit_and_reparse(edit)
    return f"Replaced element at line {line} ({best_node.llm_path}) in {file_path}."
    
def replace_lines(session: Session, agent: Agent, file_path: str, line_start: int, line_end: int, new_content: str):    
    """Replace a specific start/end line range within a file with the provided contents.
    
    Args:
        file_path: The file path to replace the lines in.
        line_start: The starting line number (inclusive).
        line_end: The ending line number (inclusive).
        new_content: The new contents for the specified line range.

    Examples:
        Task: Replace lines 100-200 of my_script.py with the specified code.
        Tool Call: {"file_path": "scripts/my_script.py", "line_start": 100, "line_end": 200, "new_content": "def inner_function..."}
    """
    file = session.files.get(file_path)
    if not file: return f"Error: File {file_path} not found."
    start_byte = file.current_state.get_line_byte_range(line_start)[0]
    end_byte = file.current_state.get_line_byte_range(line_end)[1]
    if hasattr(file, 'apply_edit_and_reparse'):
        start_point = (line_start - 1, 0)
        idx = line_end - 1
        starts = file.current_state._line_starts
        if idx >= len(starts): idx = len(starts) - 1
        col = end_byte - starts[idx]
        edit = CodeEdit(
            start_byte=start_byte,
            end_byte=end_byte,
            start_point=start_point,
            end_point=(idx, col),
            new_text=new_content.encode('utf-8')
        )
        file.apply_edit_and_reparse(edit)
    else:
        old_bytes = file.current_state.bytes
        new_bytes = old_bytes[:start_byte] + new_content.encode('utf-8') + old_bytes[end_byte:]
        file.current_state = CodeState(new_bytes)
    return f"Replaced lines {line_start}-{line_end} in {file_path}."


def open_lines(session: Session, agent: Agent, file_path: str, line_start: int, line_end: int):
    """Open an interactive editing window displaying the specified start/end line range of a file.
    
    The editing window will display the lines and wait for a replacement code block or a cancellation reason. Upon receiving either, the window closes and shows a diff or the cancellation message.
    
    Args:
        file_path: The file path to open the lines of.
        line_start: The starting line number.
        line_end: The ending line number.

    Examples:
        Task: Display lines 100-200 of my_script.py in the editing window.
        Tool Call: {"file_path": "scripts/my_script.py", "line_start": 100, "line_end": 200}
    """
    pass


def open_file(session: Session, agent: Agent, file_path: str):
    """Open an interactive editing window displaying the entire contents of a file.
    
    The editing window will display the file and wait for a replacement code block or a cancellation reason. Upon receiving either, the window closes and shows a diff or the cancellation message.
    
    Args:
        file_path: The file path to open.

    Examples:
        Task: Display the entirety of my_script.py in the editing window.
        Tool Call: {"file_path": "scripts/my_script.py"}
    """
    pass
    
    
def open_element(session: Session, agent: Agent, file_path: str, element_path: str):
    """Open an interactive editing window displaying a specific code element from a file.
    
    The editing window will display the element and wait for a replacement code block or a cancellation reason. Upon receiving either, the window closes and shows a diff or the cancellation message.
    
    If specific lines need to be edited, or if a file extension is not supported, use the open_lines tool instead.

    Args:
        file_path: The file path to open the element of.
        element_path: The element path within the file.

    Examples:
        Task: Display the entirety of my_class in the editing window.
        Tool Call: {"file_path": "scripts/my_script.py", "element_path": "my_class"}
    """
    pass
    
def open_element_at(session: Session, agent: Agent, file_path: str, line: int):
    """Open an interactive editing window displaying the innermost code element found at a specific line.
    
    The editing window will display the element and wait for a replacement code block or a cancellation reason. Upon receiving either, the window closes and shows a diff or the cancellation message.
    
    If specific lines need to be edited, or if a file extension is not supported, use the open_lines tool instead.

    Args:
        file_path: The file path to open the element of.
        line: The line number where the target element is located.

    Examples:
        Task: Display the element at line 10 in the editing window.
        Tool Call: {"file_path": "scripts/my_script.py", "line": 10}
    """
    pass