import json
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from agent2.core.objects import Rollout
from agent2.core.pipeline import SingleAgentPipeline
from agent2.core.session import Session
from agent2.core.tools.editing import replace_file, replace_lines
from agent2.core.tools.tool import Tool
from agent2.core.workspace import Workspace


class FakeMessage:
    def __init__(self, *, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_dump(self, exclude_unset=True):
        message = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ]
        return message


class FakeClient:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.requests = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create),
        )

    async def create(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        return SimpleNamespace(choices=[SimpleNamespace(message=next(self.messages))])


def test_session_uses_config_paths_and_round_trips_rollouts(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    session = Session(tmp_path)

    config = session.get_config("config/agents/sample.toml")
    assert config.path == "config/agents/sample.toml"
    assert session.files["main.py"].current_state.bytes == b"print('hello')\n"
    assert (tmp_path / ".agent2" / "task").is_dir()

    parent = Rollout(
        config_path=config.path,
        id="parent",
        date_deployed="now",
    )
    child = Rollout(
        config_path=config.path,
        id="child",
        date_deployed="now",
        parent="parent",
    )
    session.register_rollout(parent)
    session.register_rollout(child)
    session.save_rollout(child)

    assert parent.children == ["child"]
    reloaded = Session(tmp_path)
    assert reloaded.datastore["parent"].children == ["child"]
    assert reloaded.datastore["child"].parent == "parent"


def test_shared_workspaces_see_edits_and_clones_become_stale(tmp_path):
    (tmp_path / "main.py").write_text("original\n", encoding="utf-8")
    session = Session(tmp_path)
    shared = Workspace(session)
    assert shared.files == {}

    replace_file(session, SimpleNamespace(workspace=shared), "main.py", "shared\n")
    assert shared.files["main.py"].current_state.bytes == b"shared\n"
    assert shared.read_file("main.py").current_state.bytes == b"shared\n"

    isolated = shared.clone()
    replace_file(session, SimpleNamespace(workspace=isolated), "main.py", "isolated\n")
    isolated.commit()
    assert (tmp_path / "main.py").read_bytes() == b"isolated\n"

    with pytest.raises(ValueError, match="main.py"):
        shared.commit()
    assert shared.read_file("main.py").current_state.bytes == b"shared\n"


def test_session_refresh_preserves_workspace_edits_and_commit_detects_disk_changes(tmp_path):
    (tmp_path / "main.py").write_text("original\n", encoding="utf-8")
    session = Session(tmp_path)
    workspace = Workspace(session)
    replace_file(session, SimpleNamespace(workspace=workspace), "main.py", "agent\n")

    old_file = session.files["main.py"]
    session.refresh_files()
    assert session.files["main.py"] is old_file
    (tmp_path / "main.py").write_text("external\n", encoding="utf-8")
    session.refresh_files()
    assert session.files["main.py"].current_state.bytes == b"external\n"
    assert workspace.read_file("main.py").current_state.bytes == b"agent\n"
    with pytest.raises(ValueError, match="main.py"):
        workspace.commit()


def test_session_incrementally_reparses_changed_code_files(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("value = 1\n", encoding="utf-8")
    session = Session(tmp_path)
    code_file = session.files["main.py"]

    path.write_text("value = 2\n\ndef added():\n    return value\n", encoding="utf-8")
    session.refresh_files()

    assert session.files["main.py"] is code_file
    assert code_file.original_state is code_file.current_state
    assert "added" in code_file.code_nodes


def test_workspace_commits_creations_and_deletions(tmp_path):
    (tmp_path / "old.txt").write_text("old", encoding="utf-8")
    session = Session(tmp_path)
    workspace = Workspace(session)
    workspace.write_file("new.txt", b"new")
    workspace.delete_file("old.txt")
    workspace.commit()

    assert not (tmp_path / "old.txt").exists()
    assert (tmp_path / "new.txt").read_bytes() == b"new"
    assert set(session.files) >= {"new.txt"}
    assert "old.txt" not in session.files
    assert workspace.files == {}


def test_workspace_can_recreate_a_deleted_file(tmp_path):
    path = tmp_path / "file.txt"
    path.write_text("old", encoding="utf-8")
    workspace = Workspace(Session(tmp_path))
    workspace.delete_file("file.txt")
    workspace.write_file("file.txt", b"new")
    workspace.commit()
    assert path.read_bytes() == b"new"


def test_structural_edits_checkout_privately(tmp_path):
    path = tmp_path / "main.py"
    path.write_text("def value():\n    return 1\n", encoding="utf-8")
    session = Session(tmp_path)
    workspace = Workspace(session)
    agent = SimpleNamespace(workspace=workspace)

    replace_lines(session, agent, "main.py", 2, 2, "    return 2\n")

    assert b"return 1" in session.files["main.py"].current_state.bytes
    assert b"return 2" in workspace.read_file("main.py").current_state.bytes


def test_single_agent_pipeline_runs_tools_until_final_response(tmp_path):
    call = SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name="double", arguments=json.dumps({"value": 4})),
    )
    client = FakeClient(
        [
            FakeMessage(tool_calls=[call]),
            FakeMessage(content="The answer is 8."),
        ]
    )

    def double(value: int) -> int:
        """Double a value."""
        return value * 2

    session = Session(tmp_path)
    pipeline = SingleAgentPipeline(
        "config/agents/sample.toml",
        "Calculate it",
        rollout_id="run-1",
        tools={"double": Tool(double)},
        client=client,
    )

    result = asyncio.run(pipeline.run(session))

    assert result == "The answer is 8."
    assert len(client.requests) == 2
    assert client.requests[1]["messages"][-1]["role"] == "tool"
    assert client.requests[1]["messages"][-1]["content"] == "8"
    assert pipeline.active_agents == {}
    persisted = json.loads((tmp_path / ".agent2" / "task" / "run-1.json").read_text())
    assert persisted["id"] == "run-1"
    assert persisted["raw_chat"][-1]["content"] == "The answer is 8."
