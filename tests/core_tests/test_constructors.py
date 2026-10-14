from types import SimpleNamespace

from agent2.core.constructors import DefaultConstructor, DirectoryConstructor


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


def test_default_constructor_wraps_initial_and_followup_prompts():
    agent = SimpleNamespace(
        config=SimpleNamespace(
            system_prompt="system",
            prompt_wrap_top="Task:\n",
            prompt_wrap_bottom="{{TASK}}\nEnd.",
            followup_prompt_wrapper="Followup: {{TASK}}",
        ),
        rollout=SimpleNamespace(raw_chat=[]),
    )
    constructor = DefaultConstructor("TASK")

    constructor.setup(agent, "initial")
    constructor.followup(agent, "next")

    assert agent.rollout.raw_chat == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "Task:\ninitial\nEnd."},
        {"role": "user", "content": "Followup: next"},
    ]
