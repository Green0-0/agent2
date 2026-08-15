def move_files(paths: str, make_dir: bool = False):
    """Takes as input a list of comma separated movement paths, which are formatted {original_location}>{new_location}, ensuring that there is exactly one angle bracket pointing right per file movement. Renaming files is also possible. If make_dir is true, missing directories will be created.
    
    For example:
    ``"scripts/script_1.py>new_scripts/script_2.py, folder/pic.png>folder/picture.png", True``
    Moves script_1 and renames it to script_2 (creating the folder if it doesn't exist) and renames pic to picture."""


def make_empty_files(file_paths: str, make_dir: bool = False):
    """Takes as input a list of comma separated file paths, of which an empty file is created at each. If make_dir is true, missing directories will be created.
    
    For example:
    ``"scripts/script_1.py, scripts/script_2.py", True``
    Creates empty files script_1.py and script_2.py in the scripts folder. The scripts folder is created if it doesn't exist."""
    ...


def replace_file(file_path: str, new_content: str):
    """Takes as input a file path, and replaces its contents. 
        
    For example:
    ``"scripts/my_script.py", "import ..."``
    Replaces the script my_script with the new script."""
    ...
    
    
def replace_element(file_path: str, element_path: str, new_content: str):
    """Takes as input an element path at a given file path, and replaces its contents.
    
    For example:
    ``"scripts/my_script.py" "my_class.inner_function" "def inner_function..."``
    Would replace the inner function in my_class of my_script.py with the specified code specified.
    
    If specific lines need to be edited, or if a file extension is not supported, lookup the replace_lines tool instead.
    """
    ...
    
def replace_element_at(file_path: str, line: int, new_content: str):
    """Takes as input a line number at a given file path, and replaces the innermost element at that line with the contents.
    
    For example:
    ``"scripts/my_script.py" 10 "def inner_function..."``
    Would replace the element present at line 10 of my_script.py with the specified code.
    
    If specific lines need to be edited, or if a file extension is not supported, lookup the replace_lines tool instead.
    """
    # WARNING: THIS SHOULD NOT BE USED, AS A MISFIRE FROM WRITING THE WRONG LINE WILL DESTROY THE ELEMENT
    ...
    
def replace_lines(file_path: str, line_start: int, line_end: int, new_content: str):    
    """Takes as input a file path and the start/end line range, and replaces its contents.
    
    For example:
    ``"scripts/my_script.py", 100, 200, "def inner_function..."``
    Would replace lines 100-200 of my_script.py with whatever code specified.
    """
    ...


def open_lines(file_path: str, line_start: int, line_end: int):
    """Opens an editing window at the specified file_path and the given start/end line range. The editing window first displays the file and then looks for a replacement code block or a cancellation reason. In either case, the editing window then closes, and the previously shown code is hidden (removed from context), only the diff or cancellation reason is shown. 
    
    For example:
    ``"scripts/my_script.py" "100" "200"``
    Will show lines 100-200 of my_script. 
    Next, outputting a cancellation message, such as:
    "Accidentally specified the wrong lines to edit. Should edit lines 200-300 instead because ..."
    or a code block in markdown:
    ```python
    def inner_function()
        ...
    ```
    will close the edit window and show either the diff or cancellation message.
    """


def open_file(file_path: str):
    """Opens an editing window at the specified file_path. The editing window first displays the file and then looks for a replacement code block or a cancellation reason. In either case, the editing window then closes, and the previously shown code is hidden (removed from context), only the diff or cancellation reason is shown. 
    
    For example:
    ``"scripts/my_script.py"``
    Will show the entirety of my_script. 
    Next, outputting a cancellation message, such as:
    "Accidentally specified the wrong file to edit. Should edit script_2 instead because ..."
    or a code block in markdown:
    ```python
    def inner_function()
        ...
    ```
    will close the edit window and show either the diff or cancellation message.
    """
    ...
    
    
def open_element(file_path: str, element_path: str):
    """Opens an editing window at the specified file_path and the given element_path. The editing window first displays the element and then looks for a replacement code block or a cancellation reason. In either case, the editing window then closes, and the previously shown code is hidden (removed from context), only the diff or cancellation reason is shown. 
    
    For example:
    ``"scripts/my_script.py" "my_class"``
    Will show the entirety of my_class. 
    Next, outputting a cancellation message, such as:
    "Accidentally specified the wrong element to edit. Should edit inner_function instead because ..."
    or a code block in markdown:
    ```python
    class my_class:
        ...
    ```
    will close the edit window and show either the diff or cancellation message.
    
    If specific lines need to be edited, or if a file extension is not supported, lookup the open_lines tool instead.
    """
    ...
    
def open_element_at(file_path: str, element_path: str):
    """Opens an editing window at the specified file_path and the innermost element at the given line. The editing window first displays the element and then looks for a replacement code block or a cancellation reason. In either case, the editing window then closes, and the previously shown code is hidden (removed from context), only the diff or cancellation reason is shown. 
    
    For example:
    ``"scripts/my_script.py" 10``
    Will show the entirety the element at line 10. 
    Next, outputting a cancellation message, such as:
    "Accidentally specified the wrong element to edit. Should edit inner_function instead because ..."
    or a code block in markdown:
    ```python
    class my_class:
        ...
    ```
    will close the edit window and show either the diff or cancellation message.
    
    If specific lines need to be edited, or if a file extension is not supported, lookup the open_lines tool instead.
    """
    ...