#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from agent2.core.pipeline import SingleAgentPipeline
from agent2.core.session import Session


async def run(args: argparse.Namespace) -> None:
    session = Session(args.folder)
    pipeline = SingleAgentPipeline(
        args.config,
        args.prompt,
    )

    result = await pipeline.run(session)
    print("\nAgent response:\n")
    print(result.answer or "(no final response)")
    print("\nUncommitted workspace diff:\n")
    print("\n".join(content for _, content in result.workspace.diff()) or "No file changes.")
    print(f"\nRollout saved to {session.rollout_path / f'{result.rollout_id}.json'}")


def main() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if "ANTHROPIC_API_KEY" not in os.environ and env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.removeprefix("export ").strip() == "ANTHROPIC_API_KEY":
                os.environ["ANTHROPIC_API_KEY"] = value.strip().strip("'\"")
                break

    parser = argparse.ArgumentParser(
        description="Run one coding agent and print its uncommitted edits."
    )
    parser.add_argument("folder", type=Path, help="Project folder for the agent to inspect")
    parser.add_argument("prompt", help="Task to send to the agent")
    parser.add_argument("--config", default="config/agents/basic_agent.toml")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
