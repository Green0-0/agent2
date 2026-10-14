from types import SimpleNamespace

import pytest

from agent2.core.session import Session
from agent2.core.tools.searching import list_folder, search, search_folders
from agent2.core.tools.tool import Tool
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
    assert "Element `<file>`" in result
    assert "1 import needle" in result
    assert "Element `Outer.inner`" in result
    assert "5 return 'needle'" in result
    assert "Element `Outer`," not in result


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
    assert result.count(". Element") == 10
    assert len(result.splitlines()) <= 40

    next_page = search(session, agent, "match", start_index=10)
    assert "ranked results 11-12 of 12" in next_page
    assert "### 11. Element `function_10`" in next_page
    assert "### 12. Element `function_11`" in next_page
    assert search(session, agent, "match", start_index=12) == "No search results at or after index 12."
    with pytest.raises(ValueError, match="start_index"):
        search(session, agent, "match", start_index=-1)

    with pytest.raises(ValueError, match="Invalid regex pattern"):
        search(session, agent, "[")
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        search(session, agent, "match", path_regex="[")
    schema = Tool(search).openai_schema["function"]["parameters"]
    assert schema["properties"]["start_index"]["type"] == "integer"
    assert "start_index" not in schema["required"]


def test_list_folder_shows_immediate_effective_workspace_entries(tmp_path):
    (tmp_path / "src" / "nested").mkdir(parents=True)
    (tmp_path / "src" / "main.py").write_text("old\n", encoding="utf-8")
    (tmp_path / "src" / "nested" / "child.py").write_text("child\n", encoding="utf-8")
    (tmp_path / "gone.txt").write_text("gone\n", encoding="utf-8")
    session = Session(tmp_path)
    agent = make_agent(session)
    agent.workspace.write_file("new/deep/file.txt", b"new\n")
    agent.workspace.delete_file("gone.txt")

    assert list_folder(session, agent, ".") == "# Folder .\nnew/\nsrc/"
    assert list_folder(session, agent, "src") == "# Folder src\nmain.py\nnested/"
    assert list_folder(session, agent, "new") == "# Folder new\ndeep/"
    assert list_folder(session, agent, "missing").startswith("Error: Folder missing")
    assert list_folder(session, agent, "../src").startswith("Error: Folder path")


def test_search_folders_matches_inferred_folders_and_files(tmp_path):
    (tmp_path / "Tests" / "unit").mkdir(parents=True)
    (tmp_path / "Tests" / "unit" / "test_main.py").write_text("", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("", encoding="utf-8")
    session = Session(tmp_path)
    agent = make_agent(session)

    result = search_folders(session, agent, r"tests|test_main")
    assert "Tests/" in result
    assert "Tests/unit/test_main.py" in result
    assert "src/main.py" not in result
    assert search_folders(session, agent, "absent") == "No matching paths found."
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        search_folders(session, agent, "[")
    assert Tool(list_folder).openai_schema["function"]["name"] == "list_folder"
    assert Tool(search_folders).openai_schema["function"]["name"] == "search_folders"
