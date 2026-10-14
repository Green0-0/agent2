import json
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from agent2.core.agent import Agent
from agent2.core.globals import CONSTRUCTORS, HOOKS, TOOLS
from agent2.core.objects import Message, Rollout
from agent2.core.pipeline import BasicMultiAgentPipeline, SingleAgentPipeline
from agent2.core.session import Session
from agent2.core.tools.editing import (
    open_element,
    open_element_at,
    open_file,
    open_lines,
    replace_file,
    replace_lines,
)
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


class MultiFakeClient:
    def __init__(self, fail_at=None):
        self.candidates = 0
        self.fail_at = fail_at
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.requests.append(deepcopy(kwargs))
        if kwargs["messages"][-1]["role"] == "tool":
            message = FakeMessage(content="done")
        elif "tools" not in kwargs:
            message = FakeMessage(content="3")
        else:
            self.candidates += 1
            if self.candidates == self.fail_at:
                raise RuntimeError("candidate failed")
            call = SimpleNamespace(
                id=f"call-{self.candidates}",
                function=SimpleNamespace(
                    name="replace_file",
                    arguments=json.dumps({
                        "file_path": "main.py",
                        "new_content": f"candidate {self.candidates}\n",
                    }),
                ),
            )
            message = FakeMessage(tool_calls=[call])
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def configure_agent(session, monkeypatch, client, functions=(), hooks=("tool_call",)):
    config = session.get_config("config/agents/sample.toml")
    config.primary_tools = [function.__name__ for function in functions]
    config.secondary_tools = []
    config.hooks = list(hooks)
    for function in functions:
        monkeypatch.setitem(TOOLS, function.__name__, Tool(function))
    monkeypatch.setattr("agent2.core.agent.AsyncOpenAI", lambda **kwargs: client)
    return config


def test_session_uses_config_paths_and_round_trips_rollouts(tmp_path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    session = Session(tmp_path)

    config = session.get_config("config/agents/sample.toml")
    assert config.path == "config/agents/sample.toml"
    assert config.max_steps == 100
    assert set(config.constructors) <= CONSTRUCTORS.keys()
    assert set(config.hooks) <= HOOKS.keys()
    assert set(config.primary_tools + config.secondary_tools) <= TOOLS.keys()
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


def test_workspace_diff_returns_one_path_and_diff_tuple_per_file(tmp_path):
    (tmp_path / "a.txt").write_text("old\n", encoding="utf-8")
    workspace = Workspace(Session(tmp_path))
    workspace.write_file("a.txt", b"new\n")
    workspace.write_file("b.txt", b"created\n")

    diffs = workspace.diff()

    assert [path for path, _ in diffs] == ["a.txt", "b.txt"]
    assert diffs[0][1].startswith("--- a/a.txt\n+++ b/a.txt")
    assert diffs[1][1].startswith("--- /dev/null\n+++ b/b.txt")


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


def test_workspace_reuses_parse_trees_for_checkout_writes_and_clones(tmp_path, monkeypatch):
    path = tmp_path / "main.py"
    path.write_text("def value():\n    return 1\n", encoding="utf-8")
    session = Session(tmp_path)
    source = session.files["main.py"]
    parse = source.adapter.parse
    old_trees = []

    def track_parse(data, old_tree=None):
        old_trees.append(old_tree)
        return parse(data, old_tree)

    monkeypatch.setattr(source.adapter, "parse", track_parse)
    workspace = Workspace(session)
    agent = SimpleNamespace(workspace=workspace)

    replace_file(session, agent, "main.py", "def value():\n    return 2\n")
    checked_out = workspace.files["main.py"]
    assert len(old_trees) == 1 and old_trees[0] is not None
    assert checked_out.tree is not source.tree
    assert b"return 1" in source.current_state.bytes

    old_trees.clear()
    isolated = workspace.clone()
    assert old_trees == []
    assert isolated.files["main.py"].tree is not checked_out.tree
    replace_file(session, SimpleNamespace(workspace=isolated), "main.py", "def value():\n    return 3\n")
    assert len(old_trees) == 1 and old_trees[0] is not None
    assert b"return 2" in checked_out.current_state.bytes

    old_trees.clear()
    workspace.write_file("new.py", b"def created():\n    pass\n")
    assert old_trees == [None]
    workspace.write_file("new.py", b"def created():\n    return 1\n")
    assert old_trees[1] is not None
    assert workspace.files["new.py"].original_state is None


def test_single_agent_pipeline_runs_tools_until_final_response(tmp_path, monkeypatch):
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
    configure_agent(session, monkeypatch, client, (double,))
    pipeline = SingleAgentPipeline(
        "config/agents/sample.toml",
        "Calculate it",
    )

    result = asyncio.run(pipeline.run(session))

    assert result.answer == "The answer is 8."
    assert len(client.requests) == 2
    assert "Calculate it" in client.requests[0]["messages"][1]["content"]
    assert "{{PROMPT}}" not in client.requests[0]["messages"][1]["content"]
    assert client.requests[1]["messages"][-1]["role"] == "tool"
    assert client.requests[1]["messages"][-1]["content"] == "8"
    assert pipeline.active_agents == {}
    persisted = json.loads((tmp_path / ".agent2" / "task" / f"{result.rollout_id}.json").read_text())
    assert persisted["id"] == result.rollout_id
    assert persisted["raw_chat"][-1]["content"] == "The answer is 8."


def test_multi_agent_pipeline_selects_an_isolated_diff_without_committing(tmp_path, monkeypatch):
    path = tmp_path / "main.py"
    path.write_text("original\n", encoding="utf-8")
    client = MultiFakeClient()
    session = Session(tmp_path)
    configure_agent(session, monkeypatch, client, (replace_file,))
    pipeline = BasicMultiAgentPipeline(
        "config/agents/sample.toml",
        "Improve main.py",
    )

    choice = asyncio.run(pipeline.run(session))

    assert choice == 3
    assert len(pipeline.diffs) == 5
    assert all(f"+candidate {number}" in diff for number, diff in enumerate(pipeline.diffs, 1))
    assert path.read_text(encoding="utf-8") == "original\n"
    assert len(list((tmp_path / ".agent2" / "task").glob("*.json"))) == 6
    assert "CANDIDATE 5" in client.requests[-1]["messages"][-1]["content"]


def test_multi_agent_pipeline_keeps_other_candidates_after_one_fails(tmp_path, monkeypatch):
    (tmp_path / "main.py").write_text("original\n", encoding="utf-8")
    client = MultiFakeClient(fail_at=5)
    session = Session(tmp_path)
    configure_agent(session, monkeypatch, client, (replace_file,))
    pipeline = BasicMultiAgentPipeline(
        "config/agents/sample.toml",
        "Improve main.py",
    )

    assert asyncio.run(pipeline.run(session)) == 3
    assert pipeline.errors == [None, None, None, None, "candidate failed"]
    assert len(pipeline.diffs) == 5
    assert "STATUS: failed: candidate failed" in client.requests[-1]["messages"][-1]["content"]


def test_open_file_routes_and_scrubs_its_continuation(tmp_path, monkeypatch):
    (tmp_path / "main.txt").write_text("old\n", encoding="utf-8")
    call = SimpleNamespace(
        id="open-1",
        function=SimpleNamespace(name="open_file", arguments=json.dumps({"file_path": "main.txt"})),
    )
    client = FakeClient([
        FakeMessage(tool_calls=[call]),
        FakeMessage(content="```text\nnew\n```"),
        FakeMessage(content="done"),
    ])
    session = Session(tmp_path)
    configure_agent(session, monkeypatch, client, (open_file,))
    pipeline = SingleAgentPipeline(
        "config/agents/sample.toml",
        "Edit main.txt",
    )

    result = asyncio.run(pipeline.run(session))
    assert result.answer == "done"
    assert result.workspace.read_file("main.txt").current_state.bytes == b"new\n"
    assert len(client.requests) == 3
    assert client.requests[2]["messages"][-1]["role"] == "user"
    assert "Edited main.txt" in client.requests[2]["messages"][-1]["content"]
    assert not any(
        message.get("role") == "assistant" and message.get("content") == "```text\nnew\n```"
        for message in session.datastore[result.rollout_id].raw_chat
    )


def test_continuations_can_chain_without_scrubbing_history(tmp_path, monkeypatch):
    events = []

    def staged():
        def first(message):
            events.append(message.content)

            def second(next_message):
                events.append(next_message.content)

            return "first handled", second

        return "waiting", first

    call = SimpleNamespace(
        id="stage-1",
        function=SimpleNamespace(name="staged", arguments="{}"),
    )
    client = FakeClient([
        FakeMessage(tool_calls=[call]),
        FakeMessage(content="stage one"),
        FakeMessage(content="stage two"),
        FakeMessage(content="done"),
    ])
    session = Session(tmp_path)
    configure_agent(session, monkeypatch, client, (staged,))
    pipeline = SingleAgentPipeline(
        "config/agents/sample.toml",
        "Run stages",
    )

    result = asyncio.run(pipeline.run(session))
    assert result.answer == "done"
    assert events == ["stage one", "stage two"]
    chat = session.datastore[result.rollout_id].raw_chat
    assert any(message.get("content") == "stage one" for message in chat)
    assert any(message.get("content") == "stage two" for message in chat)


def test_multiple_continuations_are_all_rejected(tmp_path, monkeypatch):
    called = []

    def staged():
        return "waiting", lambda message: called.append(message.content)

    calls = [
        SimpleNamespace(
            id=f"stage-{number}",
            function=SimpleNamespace(name="staged", arguments="{}"),
        )
        for number in range(2)
    ]
    client = FakeClient([
        FakeMessage(tool_calls=calls),
        FakeMessage(content="done"),
    ])
    session = Session(tmp_path)
    configure_agent(session, monkeypatch, client, (staged,))
    pipeline = SingleAgentPipeline(
        "config/agents/sample.toml",
        "Run one stage",
    )

    assert asyncio.run(pipeline.run(session)).answer == "done"
    assert called == []
    errors = [
        message["content"] for message in client.requests[1]["messages"]
        if message.get("role") == "tool"
    ]
    assert len(errors) == 2
    assert all("Multiple continuation tools" in error for error in errors)


def test_open_tools_share_ranges_and_reject_stale_edits(tmp_path):
    (tmp_path / "main.py").write_text(
        "def one():\n    return 1\n\ndef two():\n    return 2\n",
        encoding="utf-8",
    )
    session = Session(tmp_path)
    workspace = Workspace(session)
    agent = SimpleNamespace(
        session=session,
        workspace=workspace,
        rollout=SimpleNamespace(raw_chat=[]),
    )

    lines, finish_lines = open_lines(session, agent, "main.py", 2, 2)
    element, _ = open_element(session, agent, "main.py", "one")
    element_at, _ = open_element_at(session, agent, "main.py", 5)
    assert "    return 1" in lines and "def one" not in lines
    assert "def one" in element and "def two" not in element
    assert "def two" in element_at and "def one" not in element_at

    reply = FakeMessage(content="```python\n    return 3\n```")
    agent.rollout.raw_chat.append(reply.model_dump())
    finish_lines(reply)
    assert b"def one():\n    return 3\n" in workspace.read_file("main.py").current_state.bytes

    _, finish = open_file(session, agent, "main.py")
    workspace.write_file("main.py", b"changed elsewhere\n")
    reply = FakeMessage(content="```python\nreplacement\n```")
    agent.rollout.raw_chat.append(reply.model_dump())
    finish(reply)

    assert workspace.read_file("main.py").current_state.bytes == b"changed elsewhere\n"
    assert "changed after it was opened" in agent.rollout.raw_chat[-1]["content"]


def test_open_element_includes_indentation_and_retries_tool_calls(tmp_path):
    (tmp_path / "main.py").write_text("class C:\n    def method(self):\n        return 1\n", encoding="utf-8")
    session = Session(tmp_path)
    workspace = Workspace(session)
    agent = SimpleNamespace(
        session=session,
        workspace=workspace,
        rollout=SimpleNamespace(raw_chat=[]),
    )
    content, finish = open_element(session, agent, "main.py", "C.method")
    assert "\n    def method" in content

    repeated_call = FakeMessage(tool_calls=[SimpleNamespace(
        id="repeat",
        function=SimpleNamespace(name="open_element", arguments="{}"),
    )])
    agent.rollout.raw_chat.append(repeated_call.model_dump())
    assert finish(repeated_call) == ("", finish)
    assert "still open" in agent.rollout.raw_chat[-1]["content"]

    reply = FakeMessage(content="```python\n    def method(self):\n        return 2\n```")
    agent.rollout.raw_chat.append(reply.model_dump())
    finish(reply)
    assert workspace.read_file("main.py").current_state.bytes == b"class C:\n    def method(self):\n        return 2\n"


def test_agent_coalesces_adjacent_inbox_user_messages(tmp_path):
    session = Session(tmp_path)
    client = FakeClient([FakeMessage(content="done")])
    config = session.get_config("config/agents/sample.toml")
    config.constructors = ["default"]
    config.prompt_wrap_top = None
    config.prompt_wrap_bottom = "{{PROMPT}}"
    config.followup_prompt_wrapper = "{{PROMPT}}"
    config.primary_tools = []
    config.secondary_tools = []
    agent = Agent(
        session,
        Workspace(session),
        config,
        "prompt",
        unique_id="inbox",
        client=client,
    )

    async def run():
        await agent.receive_message("first")
        await agent.receive_message("second")
        await agent.receive_message("STOP")
        return await agent.run()

    assert asyncio.run(run()) == "done"
    users = [message for message in client.requests[0]["messages"] if message["role"] == "user"]
    assert users == [{"role": "user", "content": "prompt\n\nfirst\n\nsecond\n\nSTOP"}]


def test_agent_defers_inbox_during_a_continuation(tmp_path):
    session = Session(tmp_path)
    client = FakeClient([
        FakeMessage(content="continuation reply"),
        FakeMessage(content="done"),
    ])
    config = session.get_config("config/agents/sample.toml")
    config.constructors = ["default"]
    config.prompt_wrap_top = None
    config.prompt_wrap_bottom = "{{PROMPT}}"
    config.followup_prompt_wrapper = "{{PROMPT}}"
    config.primary_tools = []
    config.secondary_tools = []
    agent = Agent(
        session,
        Workspace(session),
        config,
        "prompt",
        unique_id="deferred-inbox",
        client=client,
    )
    agent.pending_continuation = lambda message: None

    async def run():
        await agent.receive_message("first")
        await agent.receive_message("second")
        return await agent.run()

    assert asyncio.run(run()) == "done"
    assert all("first" not in message.get("content", "") for message in client.requests[0]["messages"])
    assert client.requests[1]["messages"][-1] == {
        "role": "user",
        "content": "first\n\nsecond",
    }


def test_agent_rejects_unhandled_tool_calls(tmp_path, monkeypatch):
    call = SimpleNamespace(
        id="unhandled-1",
        function=SimpleNamespace(name="unused", arguments="{}"),
    )
    def unused():
        return None

    session = Session(tmp_path)
    configure_agent(
        session,
        monkeypatch,
        FakeClient([FakeMessage(tool_calls=[call])]),
        (unused,),
        hooks=(),
    )
    pipeline = SingleAgentPipeline(
        "config/agents/sample.toml",
        "Call a tool",
    )

    with pytest.raises(RuntimeError, match="not consumed by a hook"):
        asyncio.run(pipeline.run(session))


def test_agent_message_channel_is_string_only_and_cannot_target_self(tmp_path):
    session = Session(tmp_path)
    config = session.get_config("config/agents/sample.toml")
    config.constructors = ["default"]
    config.prompt_wrap_top = None
    config.prompt_wrap_bottom = "{{PROMPT}}"
    config.followup_prompt_wrapper = "{{PROMPT}}"
    config.hooks = []
    config.primary_tools = []
    config.secondary_tools = []
    agent = Agent(
        session,
        Workspace(session),
        config,
        "prompt",
        unique_id="messages",
        client=FakeClient([]),
    )

    async def check():
        with pytest.raises(TypeError, match="must be strings"):
            await agent.receive_message({"role": "system", "content": "spoofed"})
        with pytest.raises(ValueError, match="cannot message themselves"):
            await agent.send_message(agent.rollout.id, "self message")
        await agent.stop()
        return await agent.run()

    assert asyncio.run(check()) is None
    assert agent.client.requests == []


def test_pipeline_transfers_messages_only_between_its_active_agents():
    def live_agent(agent_id):
        received = []

        async def receive_message(content):
            received.append(content)

        return SimpleNamespace(
            rollout=SimpleNamespace(id=agent_id),
            receive_message=receive_message,
            received=received,
        )

    pipeline = SingleAgentPipeline("config/agents/sample.toml", "unused")
    other_pipeline = SingleAgentPipeline("config/agents/sample.toml", "unused")
    sender, target, outsider = live_agent("sender"), live_agent("target"), live_agent("outsider")
    pipeline.register_agents([sender, target])
    other_pipeline.register_agents([outsider])
    with pytest.raises(ValueError, match="another pipeline"):
        other_pipeline.register_agents([sender])

    async def check():
        await pipeline.transfer_message(sender, Message("target", "hello"))
        with pytest.raises(KeyError, match="not found in this pipeline"):
            await pipeline.transfer_message(sender, Message("outsider", "blocked"))
        with pytest.raises(KeyError, match="not active in this pipeline"):
            await pipeline.transfer_message(outsider, Message("target", "blocked"))
        with pytest.raises(ValueError, match="cannot message themselves"):
            await pipeline.transfer_message(sender, Message("sender", "blocked"))

    asyncio.run(check())
    assert target.received == ["hello"]
    assert outsider.received == []
