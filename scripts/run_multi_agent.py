#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
from functools import partial
from pathlib import Path
from types import SimpleNamespace

from openai import AsyncOpenAI

from agent2.core.constructors import DefaultConstructor, DirectoryConstructor
from agent2.core.pipeline import BasicMultiAgentPipeline
from agent2.core.session import Session
from agent2.core.tools.editing import (
    make_empty_files,
    replace_element,
    replace_element_at,
    replace_file,
    replace_lines,
)
from agent2.core.tools.searching import search
from agent2.core.tools.tool import Tool
from agent2.core.tools.viewing import view, view_lines


async def run(args: argparse.Namespace) -> None:
    session = Session(args.folder)
    config = session.get_config(args.config)
    create = partial(
        AsyncOpenAI(
            api_key=os.environ.get(config.api_key_env_var),
            base_url=config.api_base_url,
        ).chat.completions.create,
        extra_body={"output_config": {"effort": "low"}},
    )
    functions = (
        search,
        view,
        view_lines,
        replace_file,
        replace_lines,
        replace_element,
        replace_element_at,
        make_empty_files,
    )
    pipeline = BasicMultiAgentPipeline(
        args.config,
        args.prompt,
        rollout_id=args.rollout_id,
        constructors=[DefaultConstructor(), DirectoryConstructor("files")],
        tools={function.__name__: Tool(function) for function in functions},
        client=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        ),
        max_steps=args.max_steps,
    )
    choice = await pipeline.run(session)
    for number, diff in enumerate(pipeline.diffs, 1):
        print(f"\n=== Candidate {number} ===\n{diff or 'No file changes.'}")
    print(f"\n=== Chosen candidate: {choice} ===")
    print(pipeline.diffs[choice - 1] or "No file changes.")


def main() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if "ANTHROPIC_API_KEY" not in os.environ and env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.removeprefix("export ").strip() == "ANTHROPIC_API_KEY":
                os.environ["ANTHROPIC_API_KEY"] = value.strip().strip("'\"")
                break

    parser = argparse.ArgumentParser(
        description="Run five isolated coding agents and print the judge's chosen diff."
    )
    parser.add_argument("folder", type=Path, help="Project folder for the agents to inspect")
    parser.add_argument("prompt", help="Task to send to every candidate agent")
    parser.add_argument("--config", default="config/agents/basic_agent.toml")
    parser.add_argument("--rollout-id", help="Optional rollout ID prefix")
    parser.add_argument("--max-steps", type=int, default=30)
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
