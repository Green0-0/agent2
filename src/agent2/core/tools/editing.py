from __future__ import annotations
from typing import TYPE_CHECKING
from agent2.core.session import Session
from agent2.code_parser.objects import FileEdit
from agent2.utils.codeblocks import extract_all_codeblocks

if TYPE_CHECKING:
    from agent2.core.agent import Agent


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
        file = agent.workspace.read_file(src)
        if not file:
            results.append(f"Error: Source file {src} not found.")
            continue
        agent.workspace.delete_file(src)
        agent.workspace.write_file(dst, file.current_state.bytes)
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
        agent.workspace.write_file(path, b"")
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
    file = agent.workspace.read_file(file_path)
    if not file: return f"Error: File {file_path} not found."
    agent.workspace.write_file(file_path, new_content.encode('utf-8'))
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
    file = agent.workspace.read_file(file_path)
    if not file: return f"Error: File {file_path} not found."
    if not hasattr(file, 'code_nodes'): return f"Error: {file_path} is not a parsed code file."
    node = file.code_nodes.get(element_path)
    if not node: return f"Error: Element {element_path} not found in {file_path}."
    edit = FileEdit(
        start_byte=node.full_block.start_byte,
        end_byte=node.full_block.end_byte,
        start_point=node.full_block.start_point,
        end_point=node.full_block.end_point,
        new_text=new_content.encode('utf-8')
    )
    agent.workspace.apply_edit(file_path, edit)
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
    file = agent.workspace.read_file(file_path)
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
    edit = FileEdit(
        start_byte=best_node.full_block.start_byte,
        end_byte=best_node.full_block.end_byte,
        start_point=best_node.full_block.start_point,
        end_point=best_node.full_block.end_point,
        new_text=new_content.encode('utf-8')
    )
    agent.workspace.apply_edit(file_path, edit)
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
    file = agent.workspace.read_file(file_path)
    if not file: return f"Error: File {file_path} not found."
    start_byte = file.current_state.get_line_byte_range(line_start)[0]
    end_byte = file.current_state.get_line_byte_range(line_end)[1]
    idx = min(line_end - 1, len(file.current_state._line_starts) - 1)
    edit = FileEdit(
        start_byte=start_byte,
        end_byte=end_byte,
        start_point=(line_start - 1, 0),
        end_point=(idx, end_byte - file.current_state._line_starts[idx]),
        new_text=new_content.encode('utf-8')
    )
    agent.workspace.apply_edit(file_path, edit)
    return f"Replaced lines {line_start}-{line_end} in {file_path}."


def _open_range(agent: Agent, file_path: str, start_byte: int, end_byte: int, start_point, end_point):
    file = agent.workspace.read_file(file_path)
    if not file or not file.current_state:
        return f"Error: File {file_path} not found."
    original = file.current_state.bytes
    content = original[start_byte:end_byte].decode("utf-8")

    def finish(message):
        if not agent.rollout.raw_chat or agent.rollout.raw_chat[-1].get("role") != "assistant":
            raise RuntimeError("Continuation response is missing from chat history")
        agent.rollout.raw_chat.pop()
        text = getattr(message, "content", None) or ""
        blocks = extract_all_codeblocks(text)
        if not blocks:
            result = f"No edits made. {text.strip() or 'Edit cancelled.'}"
        elif len(blocks) > 1:
            result = "No edits made: expected exactly one replacement code block."
        else:
            agent.session.refresh_files()
            current = agent.workspace.read_file(file_path)
            if not current or not current.current_state or current.current_state.bytes != original:
                result = f"No edits made: {file_path} changed after it was opened."
            else:
                agent.workspace.apply_edit(file_path, FileEdit(
                    start_byte,
                    end_byte,
                    start_point,
                    end_point,
                    blocks[0].encode("utf-8"),
                ))
                diff = dict(agent.workspace.diff()).get(file_path)
                result = f"Edited {file_path}." + (f"\n\n{diff}" if diff else " No content changed.")
        agent.rollout.raw_chat.append({"role": "user", "content": result})

    return (
        f"```\n{content}\n```\n"
        "The next code block you send will replace this content. "
        "Send no code block to cancel.",
        finish,
    )


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
    file = agent.workspace.read_file(file_path)
    if not file or not file.current_state:
        return f"Error: File {file_path} not found."
    state = file.current_state
    if line_start < 1 or line_end < line_start or line_end > len(state._line_starts):
        return f"Error: Invalid line range {line_start}-{line_end} for {file_path}."
    start_byte = state.get_line_byte_range(line_start)[0]
    end_byte = state.get_line_byte_range(line_end)[1]
    end_row = line_end - 1
    return _open_range(
        agent,
        file_path,
        start_byte,
        end_byte,
        (line_start - 1, 0),
        (end_row, end_byte - state._line_starts[end_row]),
    )


def open_file(session: Session, agent: Agent, file_path: str):
    """Open an interactive editing window displaying the entire contents of a file.
    
    The editing window will display the file and wait for a replacement code block or a cancellation reason. Upon receiving either, the window closes and shows a diff or the cancellation message.
    
    Args:
        file_path: The file path to open.

    Examples:
        Task: Display the entirety of my_script.py in the editing window.
        Tool Call: {"file_path": "scripts/my_script.py"}
    """
    file = agent.workspace.read_file(file_path)
    if not file or not file.current_state:
        return f"Error: File {file_path} not found."
    state = file.current_state
    end_row = len(state._line_starts) - 1
    return _open_range(
        agent,
        file_path,
        0,
        state.total_bytes,
        (0, 0),
        (end_row, state.total_bytes - state._line_starts[end_row]),
    )
    
    
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
    file = agent.workspace.read_file(file_path)
    if not file:
        return f"Error: File {file_path} not found."
    if not hasattr(file, "code_nodes"):
        return f"Error: {file_path} is not a parsed code file."
    node = file.code_nodes.get(element_path)
    if not node:
        return f"Error: Element {element_path} not found in {file_path}."
    block = node.full_block
    return _open_range(
        agent,
        file_path,
        block.start_byte,
        block.end_byte,
        block.start_point,
        block.end_point,
    )
    
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
    file = agent.workspace.read_file(file_path)
    if not file:
        return f"Error: File {file_path} not found."
    if not hasattr(file, "code_nodes"):
        return f"Error: {file_path} is not a parsed code file."
    nodes = [
        node for node in file.code_nodes.values()
        if node.full_block.start_point[0] < line <= node.full_block.end_point[0] + 1
    ]
    if not nodes:
        return f"Error: No element found at line {line}."
    block = min(nodes, key=lambda node: node.full_block.end_byte - node.full_block.start_byte).full_block
    return _open_range(
        agent,
        file_path,
        block.start_byte,
        block.end_byte,
        block.start_point,
        block.end_point,
    )
