from agent2.code_parser.languages.abc import LanguageAdapter
from agent2.code_parser.languages.python import PythonLanguageAdapter
from typing import List, Optional, Set

SUPPORTED_ADAPTERS: List[LanguageAdapter] = [
    PythonLanguageAdapter(),
]

def get_adapter_for_extension(extension: str) -> Optional[LanguageAdapter]:
    """Retrieves the appropriate LanguageAdapter for a given file extension.
    
    Args:
        extension (str): The file extension to look up (e.g., '.py').
        
    Returns:
        Optional[LanguageAdapter]: The corresponding adapter if supported,
            otherwise None.
    """
    for adapter in SUPPORTED_ADAPTERS:
        if extension in adapter.extensions:
            return adapter
    return None

def get_all_ignored_directories() -> Set[str]:
    """Retrieves a consolidated set of directory names to ignore.
    
    Returns:
        Set[str]: A set of directory names that should be ignored during 
            file traversal across all supported languages.
    """
    ignored = set()
    for adapter in SUPPORTED_ADAPTERS:
        ignored.update(adapter.ignored_directories)
    return ignored

def get_all_ignored_extensions() -> Set[str]:
    """Retrieves a consolidated set of file extensions to ignore.
    
    Returns:
        Set[str]: A set of file extensions that should be ignored during 
            file traversal across all supported languages.
    """
    ignored = set()
    for adapter in SUPPORTED_ADAPTERS:
        ignored.update(adapter.ignored_extensions)
    return ignored
