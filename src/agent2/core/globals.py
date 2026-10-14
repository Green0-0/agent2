from functools import partial

from agent2.core.constructors import (
    DateConstructor,
    DefaultConstructor,
    DirectoryConstructor,
    OSInfoConstructor,
)
from agent2.core.hooks import ToolCallHook
from agent2.core.tools.editing import (
    make_empty_files,
    move_files,
    open_element,
    open_element_at,
    open_file,
    open_lines,
    replace_element,
    replace_element_at,
    replace_file,
    replace_lines,
)
from agent2.core.tools.searching import list_folder, search, search_folders
from agent2.core.tools.tool import Tool
from agent2.core.tools.utilities import bash, cancel_subagent, delegate, message_subagent, tools
from agent2.core.tools.viewing import (
    view,
    view_at,
    view_element,
    view_file,
    view_files,
    view_lines,
    view_multi_lines,
    view_path,
    views_at,
)


TOOLS = {
    function.__name__: Tool(function)
    for function in (
        search, list_folder, search_folders,
        view, view_path, view_files, view_file, views_at, view_at,
        view_element, view_multi_lines, view_lines,
        move_files, make_empty_files, replace_file, replace_element,
        replace_element_at, replace_lines, open_lines, open_file,
        open_element, open_element_at,
        delegate, message_subagent, cancel_subagent, tools, bash,
    )
}

CONSTRUCTORS = {
    "default": partial(DefaultConstructor, "PROMPT"),
    "date": partial(DateConstructor, "DATE"),
    "directory": partial(DirectoryConstructor, "FILES"),
    "os": partial(OSInfoConstructor, "OS"),
}

HOOKS = {
    "tool_call": ToolCallHook,
}
