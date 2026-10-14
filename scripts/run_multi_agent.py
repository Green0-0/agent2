#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from agent2.core.pipeline import BasicMultiAgentPipeline
from agent2.core.session import Session


async def run(args: argparse.Namespace) -> None:
    session = Session(args.folder)
    pipeline = BasicMultiAgentPipeline(
        args.config,
        args.prompt,
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
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
