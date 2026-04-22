from typing import List, Optional
from agent2.element import Element
from agent2.file import File
from agent2.agent.agent_state import AgentState
from agent2.agent.tool_settings_depreciated import ToolSettings
from agent2.utils.tool_utils import normalize_path
import re

class SearchedElement:
    element: Element
    actual_matches: List[str]
    subtracted_matches: List[str]
    sub_elements: List["SearchedElement"]
    docstring: str

    def __init__(self, element: Element, actual_matches: List[str], docstring: str):
        self.element = element
        self.actual_matches = actual_matches
        self.subtracted_matches = actual_matches.copy()  # Will be adjusted later
        self.sub_elements = []
        self.sub_matches_count = 0
        self.docstring = "\n".join([line.strip() for line in docstring.split("\n") if line.strip()])

class SearchedFile:
    file: File
    elements: List[SearchedElement]

    def __init__(self, file: File, elements: List[SearchedElement]):
        self.file = file
        self.elements = elements

def make_searchtree(project: List[File], regex: str) -> List[SearchedFile]:
    """
    Build a search tree based on regex matching.
    """
    import re
    regex_pattern = re.compile(regex, flags=re.IGNORECASE)
    result = []
    
    for file in project:
        searched_elements = []
        
        # Process elements in the file
        for element in file.elements:
            searched_element = _process_element(element, regex_pattern)
            if searched_element:
                searched_elements.append(searched_element)
        
        # Only include files with matching elements
        if searched_elements:
            result.append(SearchedFile(file, searched_elements))
    
    # Second pass: calculate subtracted matches
    for searched_file in result:
        for element in searched_file.elements:
            _calculate_subtracted_matches_recursive(element)
    
    return result


def _process_element(element: Element, regex_pattern) -> Optional[SearchedElement]:
    """Process an element to find regex matches and build SearchedElement."""
    # Search in the current element's content
    matches = []
    if regex_pattern.search(element.identifier):
        matches.append(f"{element.identifier} (identifier)")
    lines = element.content.splitlines()
    for i, line in enumerate(lines, start=element.line_start):
        stripped_line = line.strip()
        formatted_line = f"{i} {stripped_line}"
        
        if regex_pattern.search(formatted_line):
            matches.append(formatted_line)
    
    # Process sub-elements
    sub_elements = []
    for sub_element in element.elements:
        searched_sub_element = _process_element(sub_element, regex_pattern)
        if searched_sub_element:
            sub_elements.append(searched_sub_element)
    
    # Only create a SearchedElement if there are matches in this element or its sub-elements
    if matches or sub_elements:
        searched_element = SearchedElement(element, matches, element.description)
        searched_element.sub_elements = sub_elements
        return searched_element
    
    return None

def _calculate_subtracted_matches_recursive(element: SearchedElement):
    """Calculate subtracted_matches recursively for an element and its sub-elements."""
    # First, calculate for all sub-elements
    for sub_element in element.sub_elements:
        _calculate_subtracted_matches_recursive(sub_element)
    
    # Then calculate for this element
    element.subtracted_matches = element.actual_matches.copy()
    for sub_element in element.sub_elements:
        for match in sub_element.actual_matches:
            if match in element.subtracted_matches:
                element.subtracted_matches.remove(match)
    element.sub_matches_count = len(element.subtracted_matches)


def flatten_searchtree(to_flatten: List[SearchedFile]) -> List[SearchedFile]:
    """
    Convert the search tree to a flat structure where elements are organized linearly.
    Children elements should be right below the parent element.
    """
    result = []
    
    for searched_file in to_flatten:
        flattened_elements = []
        
        # Flatten elements for each file
        for element in searched_file.elements:
            _flatten_element_recursive(element, flattened_elements)
        
        # Create a new SearchedFile with flattened elements
        if flattened_elements:
            flattened_file = SearchedFile(searched_file.file, flattened_elements)
            result.append(flattened_file)
    
    return result


def _flatten_element_recursive(element: SearchedElement, result: List[SearchedElement]):
    """Flatten an element and its sub-elements into a list."""
    # First add the current element
    new_element = SearchedElement(element.element, element.actual_matches, element.docstring)
    new_element.subtracted_matches = element.subtracted_matches.copy()
    new_element.sub_matches_count = element.sub_matches_count
    if new_element.sub_matches_count != 0:
        result.append(new_element)
    
    # Then recursively add all sub-elements
    for sub_element in element.sub_elements:
        _flatten_element_recursive(sub_element, result)


def prune_elements(files: List[SearchedFile], remaining: int) -> List[SearchedFile]:
    """
    Prune the search tree to keep only the specified number of elements.
    Elements with the least subtracted_matches are removed first.
    """
    # Create a flat list of all elements with their identifiers
    all_elements = []
    for file_idx, file in enumerate(files):
        for element_idx, element in enumerate(file.elements):
            all_elements.append(((file_idx, element_idx), element, element.sub_matches_count))
    
    # Count total elements
    total_elements = len(all_elements)
    
    # If there are fewer elements than requested, return as is
    if total_elements <= remaining:
        return files.copy()
    
    # Sort elements by the number of subtracted_matches (ascending)
    all_elements.sort(key=lambda x: x[2])
    
    # Create a set of element identifiers to remove
    elements_to_remove = set(idx for idx, _, _ in all_elements[:total_elements - remaining])
    
    # Create new files with only the kept elements
    result = []
    for file_idx, file in enumerate(files):
        kept_elements = []
        for element_idx, element in enumerate(file.elements):
            if (file_idx, element_idx) not in elements_to_remove:
                kept_elements.append(element)
        
        if kept_elements:  # Only include files that still have elements
            new_file = SearchedFile(file.file, kept_elements)
            result.append(new_file)
    
    return result

def remove_redundant_docstring_matches(files: List[SearchedFile]) -> List[SearchedFile]:
    """
    Remove matches from subtracted_matches that already appear in the element's docstring.
    
    Args:
        files: Flattened search tree
        
    Returns:
        Updated search tree with redundant matches removed
    """
    for file in files:
        for element in file.elements:
            if not element.docstring:
                continue
                
            # Get docstring lines for comparison
            docstring_lines = element.docstring.splitlines()
            
            # Process matches based on enumeration setting
            matches_to_remove = []
            for match in element.subtracted_matches:
                # Extract the content part if there's enumeration
                match_content = match
                if " " in match:
                    # Split by first space to remove line number
                    match_content = match.split(" ", 1)[1]
                
                # Check if this match appears in the docstring
                for docline in docstring_lines:
                    # For enumerated comparison, check if match content is in docline
                    if match_content in docline:
                        matches_to_remove.append(match)
                        break
            
            # Remove the redundant matches
            for match in matches_to_remove:
                element.subtracted_matches.remove(match)
                
    return files

def prune_elements_strings(files: List[SearchedFile], max_lines: int, include_docstr: bool = False) -> List[SearchedFile]:
    """
    Prune elements to fit within a specified number of lines.
    """
    # Count the number of files and elements
    num_files = len(files)
    num_elements = sum(len(file.elements) for file in files)
    
    # Calculate the remaining lines after accounting for files and elements count
    remaining_lines = max_lines - num_files - num_elements
    # Make a deep copy of the files to avoid modifying the original
    result = []
    for file in files:
        new_elements = []
        for element in file.elements:
            new_element = SearchedElement(element.element, element.actual_matches.copy(), element.docstring)
            new_element.subtracted_matches = element.subtracted_matches.copy()
            new_element.sub_matches_count = element.sub_matches_count
            new_elements.append(new_element)
        
        new_file = SearchedFile(file.file, new_elements)
        result.append(new_file)
    
    # Calculate the current total line count
    current_lines = 0
    for file in result:
        for element in file.elements:
            if include_docstr:
                current_lines += len(element.docstring.splitlines())
            current_lines += len(element.subtracted_matches)
    
    # Prune until we fit within the limit
    while current_lines > remaining_lines:
        # Find the element with the greatest line count
        max_lines_element = None
        max_lines_count = -1
        
        for file in result:
            for element in file.elements:
                if include_docstr:
                    element_lines = len(element.docstring.splitlines()) + len(element.subtracted_matches)
                else:
                    element_lines = len(element.subtracted_matches)
                if element_lines > max_lines_count:
                    max_lines_count = element_lines
                    max_lines_element = element
        
        # If no element has any lines (shouldn't happen), break
        if max_lines_count <= 0:
            break
        
        # Remove the last line of subtracted_matches or docstring
        if max_lines_element.subtracted_matches:
            max_lines_element.subtracted_matches.pop()
        elif max_lines_element.docstring and include_docstr:
            lines = max_lines_element.docstring.splitlines()
            if lines:
                lines.pop()
                max_lines_element.docstring = "\n".join(lines)
        
        # Recalculate the current line count
        current_lines = 0
        for file in result:
            for element in file.elements:
                if include_docstr:
                    current_lines += len(element.docstring.splitlines())
                current_lines += len(element.subtracted_matches)
    
    return result


def stringify_searchtree(files: List[SearchedFile], include_docstr: bool = False) -> str:
    """
    Convert the search tree to a string format.
    """
    if not files:
        return "No matches found."
    
    # Count total elements
    total_elements = sum(len(file.elements) for file in files)
    
    result = [f"# Showing first {total_elements} elements with a match"]
    
    for file in files:
        result.append(f"## File {file.file.path}:")
        
        for element in file.elements:
            # Calculate the line end (line_start + length of element content - 1)
            line_start = element.element.line_start
            line_end = line_start + len(element.element.content.splitlines()) - 1
            
            result.append(f"### Element `{element.element.identifier}`, lines {line_start}-{line_end} ({element.sub_matches_count} matches)")
            
            # Add docstring if available
            if element.docstring and include_docstr:
                result.append(element.docstring)
            
            # Add subtracted matches
            for match in element.subtracted_matches:
                result.append(match)
            
            # Add a newline between elements
            result.append("")
    
    return ("\n".join(result)).strip()

def search(agent: Agent, agent_workspace: Workspace, agent_config: dict, regex: str, path: str = "", extensions: str = None):
    """
    Recursively search along the path for lines matching a regex (case insensitive)
    
    Args:
        regex: Regular expression to match against
        path: Path of directory to search (defaults to root)
        extensions: Optional comma seperated string list of file extensions to filter

    Example:
        Find places containing authentication patterns
    Tool Call:
        {"regex": "auth|login|session", "path": "src/auth/", "extensions": "py"}
    """ 
    
    path = normalize_path(path)

    try:
        pattern = re.compile(regex, flags=re.IGNORECASE)
    except re.error:
        raise ValueError(f"Invalid regex pattern: {regex}")
    
    files = workspace.files
    if path:
        files = [f for f in files if f.path.startswith(path)]
    if extensions:
        extensions = extensions.split(",")
        files = [f for f in files if any(f.extension.lower() in ext.lower() or ext.lower() in f.extension.lower() for ext in extensions)]

    if len (files) == 0:
        raise ValueError(f"Path {path} does not exist in workspace")
    
    search_tree = make_searchtree(files, regex)
    flattened_tree = flatten_searchtree(search_tree)
    pruned_tree = prune_elements(flattened_tree, settings.max_search_result_listings)
    if settings.search_use_docstring:
        pruned_tree = remove_redundant_docstring_matches(pruned_tree)
    stringed_tree = prune_elements_strings(pruned_tree, settings.max_search_result_lines, settings.search_use_docstring)
    stringed_tree = stringify_searchtree(stringed_tree, settings.search_use_docstring)

    return (stringed_tree, None)
