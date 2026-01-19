# NOTE: ALL PATHS AND ELEMENT IDS ARE TREATED CASE-INSENSITIVE
from collections import OrderedDict
import os
from typing import List, Optional

from file import normalize_path
from agent2.agent_rework.file import File
from agent2.agent_rework.element import Element

class Workspace:
    """
    In-memory representation of the agent’s current project tree.

    Parameters
    ----------
    root_path : str | None, default=None
        • ``None`` → start with an empty workspace  
        • path     → recursively load all text files under that directory
                     (binary files are skipped exactly as in *load_project_files*).

    Attributes
    ----------
    files : List[File]
        The project’s files, each parsed into its own ``Element`` hierarchy.
    """

    files: List[File]  # static type-checking aid

    def __init__(self, root_path: Optional[str] = None):
        """
        Optionally populate the workspace from disk.

        The implementation is copied verbatim from the earlier
        ``load_project_files`` helper so that behaviour stays identical.
        """
        self.files = []  # start empty

        if root_path:
            for root, _, filenames in os.walk(root_path):
                for fname in filenames:
                    file_path = os.path.join(root, fname)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        rel_path = os.path.relpath(file_path, root_path)
                        rel_path = rel_path.replace("\\", "/")  # normalise slashes
                        self.files.append(File(rel_path, content))
                    except (UnicodeDecodeError, IsADirectoryError):
                        # Skip binary files or directories encountered as files
                        continue

    def get_files(self, path: str = "", extension: str = "") -> OrderedDict[str, File]:
        """Return matching files in an OrderedDict keyed by lowercase path."""
        norm_filter = normalize_path(path).lower()
        ext_filter = extension.lower()

        files_map: OrderedDict[str, File] = OrderedDict()
        for f in self.files:
            if norm_filter in f.path.lower() and (not ext_filter or f.extension.lower() == ext_filter):
                files_map[f.path.lower()] = f
        return files_map

    def get_file(self, path: str) -> File:
        """Case-insensitive lookup using OrderedDict."""
        norm_query = normalize_path(path).lower()
        files_map = OrderedDict((f.path.lower(), f) for f in self.files)

        if norm_query in files_map:
            return files_map[norm_query]

        # Fallback: find close matches
        folder_parts = norm_query.rsplit("/", 1)
        folder = folder_parts[0] if len(folder_parts) == 2 else ""
        filename = folder_parts[-1]
        base_name, _, ext = filename.rpartition(".")
        ext = ext.lower()

        candidates = [
            f for k, f in files_map.items()
            if f.path.rsplit("/", 1) == folder and f.extension.lower() == ext
        ]

        if candidates:
            def _rank(file: File) -> int:
                f_base = file.path.rsplit("/", 1)[-1].rpartition(".").lower()
                pre = sum(a == b for a, b in zip(base_name, f_base))
                suf = sum(a == b for a, b in zip(base_name[::-1], f_base[::-1]))
                return (pre + suf) - abs(len(base_name) - len(f_base))

            sorted_candidates = sorted(candidates, key=_rank, reverse=True)
            suggestions = "`, `".join(f.path for f in sorted_candidates[:5])
            raise ValueError(
                f"File '{path}' not found in workspace. "
                f"Closest matches: `{suggestions}`"
            )

        raise ValueError(f"File '{path}' not found in workspace")
    
    def get_element(self, path: str, element_id: str) -> Element:
        """
        Locate an Element inside a given file by delegating
        lookup to File.get_element().
        """
        file = self.get_file(path)  # uses case-insensitive path lookup
        return file.get_element(element_id)  # reuse File class logic
