def move_files(paths: str, make_dir: bool = False):
    """Move files or directories based on a list of comma-separated movement paths.
    
    Each path must be formatted as {original_location}>{new_location}, ensuring there is exactly one angle bracket pointing right per movement. Renaming files is also supported.
    
    Args:
        paths: A list of comma-separated movement paths.
        make_dir: If true, missing directories will be created automatically.

    Examples:
        Task: Move script_1 and rename it to script_2 (creating the folder if it doesn't exist), and rename pic to picture.
        Tool Call: {"paths": "scripts/script_1.py>new_scripts/script_2.py, folder/pic.png>folder/picture.png", "make_dir": true}
    """
    pass


def make_empty_files(file_paths: str, make_dir: bool = False):
    """Create an empty file at each specified comma-separated file path.
    
    Args:
        file_paths: A list of comma-separated file paths to create.
        make_dir: If true, missing directories will be created automatically.

    Examples:
        Task: Create empty files script_1.py and script_2.py in the scripts folder. Create the scripts folder if it doesn't exist.
        Tool Call: {"file_paths": "scripts/script_1.py, scripts/script_2.py", "make_dir": true}
    """
    pass


def replace_file(file_path: str, new_content: str):
    """Replace the entire contents of a file with the provided string.
    
    Args:
        file_path: The file path to replace the contents of.
        new_content: The new contents of the file.

    Examples:
        Task: Replace the script my_script.py with the new script.
        Tool Call: {"file_path": "scripts/my_script.py", "new_content": "import ..."}
    """
    pass
    
    
def replace_element(file_path: str, element_path: str, new_content: str):
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
    pass
    
def replace_element_at(file_path: str, line: int, new_content: str):
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
    pass
    
def replace_lines(file_path: str, line_start: int, line_end: int, new_content: str):    
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
    pass


def open_lines(file_path: str, line_start: int, line_end: int):
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


def open_file(file_path: str):
    """Open an interactive editing window displaying the entire contents of a file.
    
    The editing window will display the file and wait for a replacement code block or a cancellation reason. Upon receiving either, the window closes and shows a diff or the cancellation message.
    
    Args:
        file_path: The file path to open.

    Examples:
        Task: Display the entirety of my_script.py in the editing window.
        Tool Call: {"file_path": "scripts/my_script.py"}
    """
    pass
    
    
def open_element(file_path: str, element_path: str):
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
    
def open_element_at(file_path: str, line: int):
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