from types import SimpleNamespace

import pytest

from agent2.core.session import Session
from agent2.core.tools.searching import search
from agent2.core.workspace import Workspace


def make_agent(session):
    return SimpleNamespace(workspace=Workspace(session))


def test_search_groups_matches_under_the_innermost_element(tmp_path):
    (tmp_path / "main.py").write_text(
        "import needle\n\n"
        "class Outer:\n"
        "    def inner(self):\n"
        "        return 'needle'\n",
        encoding="utf-8",
    )
    session = Session(tmp_path)

    result = search(session, make_agent(session), "needle")

    assert "## File main.py:" in result
    assert "### Element `<file>`" in result
    assert "1 import needle" in result
    assert "### Element `Outer.inner`" in result
    assert "5 return 'needle'" in result
    assert "### Element `Outer`," not in result


def test_search_filters_paths_with_a_regex_and_extensions(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "main.py").write_text("target\n", encoding="utf-8")
    (tmp_path / "src" / "notes.txt").write_text("target\n", encoding="utf-8")
    (tmp_path / "tests" / "test_main.py").write_text("target\n", encoding="utf-8")
    session = Session(tmp_path)

    result = search(
        session,
        make_agent(session),
        "target",
        path_regex=r"^src/",
        extensions=".py",
    )

    assert "src/main.py" in result
    assert "notes.txt" not in result
    assert "tests/test_main.py" not in result


def test_search_uses_workspace_edits_and_deletions(tmp_path):
    (tmp_path / "changed.txt").write_text("old value\n", encoding="utf-8")
    (tmp_path / "deleted.txt").write_text("new value\n", encoding="utf-8")
    session = Session(tmp_path)
    agent = make_agent(session)
    agent.workspace.write_file("changed.txt", b"new value\n")
    agent.workspace.delete_file("deleted.txt")

    result = search(session, agent, "new value")

    assert "changed.txt" in result
    assert "deleted.txt" not in result
    assert search(session, agent, "old value") == "No matches found."


def test_search_includes_docstrings_without_repeating_the_matching_line(tmp_path):
    (tmp_path / "main.py").write_text(
        "def example():\n"
        "    \"\"\"A unique phrase.\"\"\"\n"
        "    return None\n",
        encoding="utf-8",
    )
    session = Session(tmp_path)

    result = search(session, make_agent(session), "unique phrase")

    assert result.count('"""A unique phrase."""') == 1
    assert "(1 matches)" in result


def test_search_validates_both_patterns_and_limits_output(tmp_path):
    (tmp_path / "main.py").write_text(
        "\n\n".join(f"def function_{i}():\n    return 'match'" for i in range(12)),
        encoding="utf-8",
    )
    session = Session(tmp_path)
    agent = make_agent(session)

    result = search(session, agent, "match")
    assert result.count("### Element") == 10
    assert len(result.splitlines()) <= 40

    with pytest.raises(ValueError, match="Invalid regex pattern"):
        search(session, agent, "[")
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        search(session, agent, "match", path_regex="[")
