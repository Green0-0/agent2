from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from agent2.code_parser.file import CodeFile
from agent2.core.session import Session

if TYPE_CHECKING:
    from agent2.core.agent import Agent

def search(
    session: Session,
    agent: Agent,
    regex: str,
    path_regex: str | None = None,
    extensions: str | None = None,
    start_index: int = 0,
) -> str:
    """Search workspace contents with a case-insensitive regular expression.

    Matches are grouped under the innermost parsed code element. Matches outside
    an element, and matches in unparsed text files, are grouped under ``<file>``.

    Args:
        regex: Regular expression to match against file contents and element paths.
        path_regex: Optional regular expression used to select workspace paths.
        extensions: Optional comma-separated file extensions to include.
        start_index: Zero-based index of the first ranked result to show.

    Examples:
        Task: Find authentication code in Python files under src or tests.
        Tool Call: {"regex": "auth|login|session", "path_regex": "^(src|tests)/", "extensions": "py", "start_index": 0}
    """
    if start_index < 0:
        raise ValueError("start_index must be zero or greater")
    try:
        pattern = re.compile(regex, re.IGNORECASE)
        path_pattern = re.compile(path_regex, re.IGNORECASE) if path_regex else None
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}") from exc

    suffixes = {
        extension.strip().lower().removeprefix(".")
        for extension in (extensions or "").split(",")
        if extension.strip()
    }
    results = []

    for path in sorted(agent.workspace.paths()):
        if path_pattern and not path_pattern.search(path):
            continue
        if suffixes and Path(path).suffix.lower().removeprefix(".") not in suffixes:
            continue
        file = agent.workspace.read_file(path)
        if not file or not file.current_state:
            continue

        state = file.current_state
        lines = state.bytes.decode("utf-8", errors="replace").splitlines()
        nodes = []
        if isinstance(file, CodeFile):
            nodes = sorted(
                {node.llm_path: node for node in file.code_nodes.values()}.values(),
                key=lambda node: (node.full_block.start_byte, -node.full_block.end_byte),
            )

        groups = {None: {"node": None, "matches": []}}
        groups.update({node.llm_path: {"node": node, "matches": []} for node in nodes})
        for node in nodes:
            if pattern.search(node.path):
                groups[node.llm_path]["matches"].append(f"{node.path} (identifier)")

        active = []
        node_index = 0
        for row, line in enumerate(lines):
            if not pattern.search(line):
                continue
            while node_index < len(nodes) and nodes[node_index].full_block.start_point[0] <= row:
                active.append(nodes[node_index])
                node_index += 1
            active = [node for node in active if node.full_block.end_point[0] >= row]
            owner = min(
                active,
                key=lambda node: node.full_block.end_byte - node.full_block.start_byte,
                default=None,
            )
            groups[owner.llm_path if owner else None]["matches"].append(f"{row + 1} {line.strip()}")

        for group in groups.values():
            matches = group["matches"]
            if not matches:
                continue
            node = group["node"]
            doc = []
            if node and node.doc_block:
                doc = [
                    line.strip()
                    for line in state.bytes[node.doc_block.start_byte:node.doc_block.end_byte]
                    .decode("utf-8", errors="replace")
                    .splitlines()
                    if line.strip()
                ]
                matches = [
                    match for match in matches
                    if match.endswith(" (identifier)")
                    or not any(match.split(" ", 1)[1] in line for line in doc)
                ]
            results.append({
                "path": path,
                "name": node.path if node else "<file>",
                "start": node.full_block.start_point[0] + 1 if node else 1,
                "end": node.full_block.end_point[0] + 1 if node else max(1, len(lines)),
                "count": len(group["matches"]),
                "matches": matches,
                "doc": doc,
                "order": len(results),
            })

    if not results:
        return "No matches found."

    total = len(results)
    results = sorted(results, key=lambda result: (-result["count"], result["order"]))[
        start_index:start_index + 10
    ]
    if not results:
        return f"No search results at or after index {start_index}."
    line_count = 1 + sum(
        index == 0 or result["path"] != results[index - 1]["path"]
        for index, result in enumerate(results)
    ) + sum(
        2 + len(result["doc"]) + len(result["matches"]) for result in results
    )
    while line_count > 40:
        result = max(results, key=lambda item: len(item["matches"]) + len(item["doc"]))
        if result["matches"]:
            result["matches"].pop()
        elif result["doc"]:
            result["doc"].pop()
        else:
            break
        line_count -= 1

    output = [
        f"# Showing ranked results {start_index + 1}-{start_index + len(results)} of {total}"
    ]
    current_path = None
    for rank, result in enumerate(results, start_index + 1):
        if result["path"] != current_path:
            current_path = result["path"]
            output.append(f"## File {current_path}:")
        output.append(
            f"### {rank}. Element `{result['name']}`, lines {result['start']}-{result['end']} "
            f"({result['count']} matches)"
        )
        output.extend(result["doc"])
        output.extend(result["matches"])
        output.append("")
    return "\n".join(output).strip()


def list_folder(session: Session, agent: Agent, folder_path: str) -> str:
    """List the immediate files and folders at a project-relative path.

    Folders end with ``/``. Use ``.`` or an empty string for the project root.

    Args:
        folder_path: Project-relative folder path to list.

    Examples:
        Task: List the contents of the source folder.
        Tool Call: {"folder_path": "src"}
    """
    folder = folder_path.strip().strip("/")
    if folder == ".":
        folder = ""
    if ".." in folder.split("/"):
        return f"Error: Folder path must stay within the project: {folder_path}"
    prefix = f"{folder}/" if folder else ""
    entries = {
        name + ("/" if separator else "")
        for path in agent.workspace.paths()
        if path.startswith(prefix) and (remainder := path[len(prefix):])
        for name, separator, _ in [remainder.partition("/")]
    }
    if not entries:
        return f"Error: Folder {folder_path or '.'} not found or empty."
    return f"# Folder {folder or '.'}\n" + "\n".join(sorted(entries))


def search_folders(session: Session, agent: Agent, regex: str) -> str:
    """Search project-relative folder and file paths with a case-insensitive regex.

    Matching folders end with ``/``. At most the first 100 sorted matches are shown.

    Args:
        regex: Regular expression to match against complete project-relative paths.

    Examples:
        Task: Find test folders and Python test files.
        Tool Call: {"regex": "(^|/)tests?(/|$)|test_.*[.]py$"}
    """
    try:
        pattern = re.compile(regex, re.IGNORECASE)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}") from exc

    paths = set(agent.workspace.paths())
    entries = set(paths)
    for path in paths:
        parts = path.split("/")
        entries.update("/".join(parts[:end]) + "/" for end in range(1, len(parts)))
    matches = sorted(path for path in entries if pattern.search(path.rstrip("/")))
    if not matches:
        return "No matching paths found."
    shown = matches[:100]
    return f"# Showing {len(shown)} of {len(matches)} matching paths\n" + "\n".join(shown)
