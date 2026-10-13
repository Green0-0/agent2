from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from agent2.code_parser.file import CodeFile
from agent2.core.session import Session

if TYPE_CHECKING:
    from agent2.core.agent import Agent


def multisearch(session: Session, agent: Agent, regexes: str):
    ...


def search(
    session: Session,
    agent: Agent,
    regex: str,
    path_regex: str | None = None,
    extensions: str | None = None,
) -> str:
    """Search workspace contents with a case-insensitive regular expression.

    Matches are grouped under the innermost parsed code element. Matches outside
    an element, and matches in unparsed text files, are grouped under ``<file>``.

    Args:
        regex: Regular expression to match against file contents and element paths.
        path_regex: Optional regular expression used to select workspace paths.
        extensions: Optional comma-separated file extensions to include.

    Examples:
        Task: Find authentication code in Python files under src or tests.
        Tool Call: {"regex": "auth|login|session", "path_regex": "^(src|tests)/", "extensions": "py"}
    """
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

    kept = {
        result["order"]
        for result in sorted(results, key=lambda result: (-result["count"], result["order"]))[:10]
    }
    results = [result for result in results if result["order"] in kept]
    line_count = 1 + len({result["path"] for result in results}) + sum(
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

    output = [f"# Showing first {len(results)} elements with a match"]
    current_path = None
    for result in results:
        if result["path"] != current_path:
            current_path = result["path"]
            output.append(f"## File {current_path}:")
        output.append(
            f"### Element `{result['name']}`, lines {result['start']}-{result['end']} "
            f"({result['count']} matches)"
        )
        output.extend(result["doc"])
        output.extend(result["matches"])
        output.append("")
    return "\n".join(output).strip()


def list_folder(session: Session, agent: Agent, folder_path: str):
    ...


def search_folders_multi(session: Session, agent: Agent, regexes: str):
    ...


def search_folders(session: Session, agent: Agent, regex: str):
    ...
