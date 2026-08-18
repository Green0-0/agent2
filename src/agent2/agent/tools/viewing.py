def view(paths: str):
    """View the contents of multiple files or elements specified by a comma-separated list of paths.
    
    Each viewing path is composed of either a file path, an element path, or both (separated by double colons).
    
    If specific lines need to be viewed, or if a file extension is not supported, use the view_lines tool instead.

    Args:
        paths: A list of comma-separated paths to view.

    Examples:
        Task: Read the script my_script.py, the class element my_class (if found), and the nested inner function in custom_script.py.
        Tool Call: {"paths": "scripts/my_script.py, my_class, scripts/custom_script.py::my_class.outer_function.inner_function"}
    """
    pass
    
    
def view_path(path: str):
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
    pass
    
    
def view_files(file_paths: str):
    """View an overview or the full contents of multiple files.
    
    An overview will be given instead of the full raw file by default. If the full file is desired, mark it with an asterisk (*).
    
    Args:
        file_paths: A list of comma-separated file paths to view.

    Examples:
        Task: Show the entirety of script_2.py, and an overview of script_1.py.
        Tool Call: {"file_paths": "scripts/script_1.py, scripts/script_2.py*"}
    """
    pass


def view_file(file_path: str, full: bool = False):
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
    pass
    
def views_at(paths: str, full: bool = False):
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
    pass
    
def view_at(file_path: str, line: int, full: bool = False):
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
    pass
    
def view_element(file_path: str, element_path: str, full: bool = False):
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
    pass


def view_multi_lines(file_line_paths: str):
    """View specific line ranges across multiple files.
    
    The format for a singular view is {{file_path}}::{{start_line}}::{{end_line}}.

    Args:
        file_line_paths: A list of comma-separated file paths with line ranges.

    Examples:
        Task: Show lines 100-200 from script_1.py, and lines 300-400 from script_2.py.
        Tool Call: {"file_line_paths": "scripts/script_1.py::100::200, scripts/script_2.py::300::400"}
    """
    pass
    
    
def view_lines(file_path: str, line_start: int, line_end: int):
    """View a specific start/end line range within a file.
    
    Args:
        file_path: The file path to view the lines of.
        line_start: The starting line number (inclusive).
        line_end: The ending line number (inclusive).

    Examples:
        Task: Show lines 100-200 from script_1.py.
        Tool Call: {"file_path": "scripts/script_1.py", "line_start": 100, "line_end": 200}
    """
    pass