def view(paths: str):
    """Takes as input a comma separated list of paths to view. 
    
    Each viewing path is composed of either a file path, an element path, or both (separated by double colons).
    
    For example:
    ``"scripts/my_script.py, my_class, scripts/custom_script.py::my_class.outer_function.inner_function"``
    Reads the script my_script, the class element my_class (if found), and the nested inner function in custom_script.
    
    If specific lines need to be viewed, or if a file extension is not supported, lookup the view_lines tool instead."""
    ...
    
    
def view_path(path: str):
    """Takes as input a path to view. 
    
    The viewing path is composed of either a file path, an element path, or both (separated by double colons).
    
    For example:
    ``"scripts/custom_script.py::my_class.outer_function.inner_function" ``
    Reads the the nested inner function in custom_script.
    ``"scripts/my_script.py"``
    Reads the script my_script.
    ``"my_class"``
    Reads the class element my_class.
    
    If specific lines need to be viewed, or if a file extension is not supported, lookup the view_lines tool instead."""
    ...
    
    
def view_files(file_paths: str):
    """Takes as input a comma separated list of file paths to view.
    
    An overview will be given instead of the full, raw file. If the full file is desired, mark it with an asterisk (*).
    
    For example:
    ``"scripts/script_1.py, scripts/script_2.py*"``
    Shows the entirety of script_2, and an overview of script_1."""
    ...


def view_file(file_path: str, full: bool = False):
    """Takes as input a file path to view.
    
    If `full` is true, the entire file will be shown. Otherwise, an overview will be given.
    
    For example:
    ``"scripts/script_2.py", True``
    Shows the entirety of script_2.
    ``"scripts/script_1.py", False``
    Shows an overview of script_1.
    """
    ...
    
    
def view_element(file_path: str, element_path: str, full: bool = False):
    """Takes as input an element path at a given file path to view.
    
    If `full` is true, the entire element is guranteed to be shown. Otherwise, it may be simplified if it is too long.
    
    For example:
    ``"scripts/script_2.py", "my_class", True``
    Shows the entirety of my_class.
    ``"scripts/script_1.py", "my_class.my_func", False``
    Shows an overview of the function my_func inside my_class. It may be reduced to an overview if its content is too long.
    """
    ...


def view_multi_lines(file_line_paths: str):
    """Takes as input a comma separated list of file paths with line ranges to view.
    
    The format for a singular view is {{file_path}}::{{start_line}}::{{end_line}}.
    
    For example:
    ``"scripts/script_1.py::100::200, scripts/script_2.py::300::400"``
    Shows lines 100-200 from script_1, and lines 300-400 from script_2.
    """
    ...
    
    
def view_lines(file_path: str, line_start: int, line_end: int):
    """Takes as input a file path and the start/end line range to view at.
    
    For example:
    ``"scripts/script_1.py", 100, 200``
    Shows lines 100-200 from script_1.
    """
    ...
    