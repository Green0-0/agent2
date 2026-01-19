from __future__ import annotations

import ast
from typing import List

from tree_sitter import Node
from tree_sitter_languages import get_parser
from typing import Optional, List
from agent2.agent_rework.element import Element

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def parse_python_elements(code: str) -> List[Element]:
    """
    Parse the given Python *source string* into a tree of Element objects.

    Guarantees:
      • Every Element.line_start is an *int* (never None)
      • No “empty” top-level blocks consisting of pure whitespace
    """
    code_bytes = code.encode("utf8")
    parser = get_parser("python")
    tree = parser.parse(code_bytes)
    root = tree.root_node

    return _parse_scope(root, "", code_bytes)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _parse_scope(scope_node: Node, prefix: str, buf: bytes) -> List[Element]:
    """
    Convert all *direct* children of `scope_node` into Element instances.
    `prefix` is the fully-qualified name of the current scope.
    """
    elements: List[Element] = []
    pending_block: list[Node] = []
    used_simple_names: set[str] = set()
    block_idx = 0

    for child in scope_node.children:
        if _is_real_def(child):
            # Flush a pending block before the definition
            if _has_meaningful_content(pending_block):
                blk = _make_block(
                    pending_block, prefix, block_idx, used_simple_names, buf
                )
                elements.append(blk)
                used_simple_names.add(blk.identifier.split(".")[-1])
                block_idx += 1
            pending_block = []

            # Real element
            el = _make_element(child, prefix, buf)
            elements.append(el)
            used_simple_names.add(el.identifier.split(".")[-1])
        else:
            pending_block.append(child)

    # Tail block (only if not empty, and, for nested scopes, only when we
    # already found at least one real definition)
    if _has_meaningful_content(pending_block) and (prefix == "" or elements):
        blk = _make_block(
            pending_block, prefix, block_idx, used_simple_names, buf
        )
        elements.append(blk)

    return elements


def _is_real_def(node: Node) -> bool:
    return node.type in (
        "class_definition",
        "function_definition",
        "decorated_definition",
    )


def _has_meaningful_content(nodes: list[Node]) -> bool:
    """
    Return True iff at least one node in `nodes` is *not* just whitespace,
    indent/dedent or a blank newline.
    """
    for n in nodes:
        if n.type not in ("indent", "dedent", "newline"):
            return True
    return False


def _make_block(
    nodes: list[Node],
    prefix: str,
    idx: int,
    used: set[str],
    buf: bytes,
) -> Element:
    """
    Turn a list of sibling AST nodes that are *not* definitions into a
    single “top_level_block_X” Element.
    """
    start_node = next((n for n in nodes if n.type != "indent"), nodes[0])
    start_line = start_node.start_point[0] if start_node else 0

    start_b = nodes[0].start_byte
    end_b = nodes[-1].end_byte
    raw = buf[start_b:end_b].decode("utf8")

    # First non-empty line becomes the header (if none, header == '<blank>')
    header = next((ln.rstrip() for ln in raw.splitlines() if ln.strip()), "<blank>")

    simple_name = f"top_level_block_{idx}"
    if simple_name in used:
        simple_name = f"_{simple_name}"
    identifier = simple_name if not prefix else f"{prefix}.{simple_name}"

    return Element(
        identifier=identifier,
        header=header,
        content=raw,
        description="",
        line_start=start_line,
        embedding=None,
        elements=[],
    )


def _make_element(node: Node, prefix: str, buf: bytes) -> Element:
    """
    Convert one (possibly decorated) class/function node into an Element,
    recurse into its body and return the fully populated Element object.
    """
    # Grab decorators if present
    if node.type == "decorated_definition":
        decorator_start = node.start_byte
        decorator_point = node.start_point
        def_node = next(
            c for c in node.named_children
            if c.type in ("class_definition", "function_definition")
        )
    else:
        decorator_start = node.start_byte
        decorator_point = node.start_point
        def_node = node

    # Header == lines from "class/def" … up to the body
    body_node = def_node.child_by_field_name("body") or def_node
    hdr_raw = buf[def_node.start_byte: body_node.start_byte].decode("utf8")
    hdr_lines = [ln.strip() for ln in hdr_raw.splitlines()]
    header = " ".join(hdr_lines) if hdr_lines else "<unknown>"

    # Docstring (first string-literal in the body)
    description = ""
    for stmt in body_node.named_children:
        if (
            stmt.type == "expression_statement"
            and stmt.named_children
            and stmt.named_children[0].type == "string"
        ):
            lit = stmt.named_children[0]
            try:
                description = ast.literal_eval(
                    buf[lit.start_byte: lit.end_byte].decode("utf8")
                )
            except Exception:
                description = buf[lit.start_byte: lit.end_byte].decode("utf8").strip(
                    "\"'"
                )
            break

    # Identifier
    name_node = def_node.child_by_field_name("name")
    name = buf[name_node.start_byte: name_node.end_byte].decode("utf8") if name_node else ""
    identifier = name if not prefix else f"{prefix}.{name}"

    # Full content (decorators + def body)
    content = buf[decorator_start: node.end_byte].decode("utf8")

    # Recursively parse the body for nested elements / blocks
    children = _parse_scope(body_node, identifier, buf)

    return Element(
        identifier=identifier,
        header=header,
        content=content,
        description=description,
        line_start=decorator_point[0],   # 0-based
        embedding=None,
        elements=children,
    )
