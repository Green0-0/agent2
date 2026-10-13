from types import SimpleNamespace

from agent2.core.constructors import DirectoryConstructor


def test_provider_replaces_lite_and_full_tokens_during_setup_and_followup():
    agent = SimpleNamespace(
        rollout=SimpleNamespace(raw_chat=[{
            "role": "system",
            "content": "lite={{files}}\n{{files*}}",
        }]),
        workspace=SimpleNamespace(paths=lambda: {"b.py", "a.py"}),
    )
    constructor = DirectoryConstructor(
        "files",
        format_lite="[{}]",
        format_full="Files:\n{}",
    )

    constructor.setup(agent, "")
    assert agent.rollout.raw_chat[0]["content"] == "lite=[a.py\nb.py]\nFiles:\na.py\nb.py"

    agent.rollout.raw_chat.append({"role": "user", "content": "{{files}} / {{files*}}"})
    constructor.followup(agent, "")
    assert agent.rollout.raw_chat[-1]["content"] == "[a.py\nb.py] / Files:\na.py\nb.py"
