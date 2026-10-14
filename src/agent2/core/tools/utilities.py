from __future__ import annotations
from agent2.core.session import Session
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agent2.core.agent import Agent


def delegate(session: Session, agent: Agent, subagent_name: str, instructions: str):
    """Start a configured subagent and return its rollout ID.

    Args:
        subagent_name: Allowed configured subagent name.
        instructions: Task for the subagent.
    """
    if not agent.pipeline:
        raise RuntimeError("Agent is not running in a pipeline")
    return agent.pipeline.spawn_agent(agent, subagent_name, instructions)


async def message_subagent(
    session: Session,
    agent: Agent,
    content: str,
    subagent_id: str,
):
    """Message an agent by rollout ID through the current pipeline.

    Args:
        content: Message to send.
        subagent_id: Target rollout ID.
    """
    if not agent.pipeline:
        raise RuntimeError("Agent is not running in a pipeline")
    await agent.send_message(subagent_id, content)
    return f"Message queued for {subagent_id}."


async def cancel_subagent(session: Session, agent: Agent, subagent_id: str):
    """Cancel a direct subagent and its descendants.

    Args:
        subagent_id: Rollout ID of the direct subagent to cancel.
    """
    if not agent.pipeline:
        raise RuntimeError("Agent is not running in a pipeline")
    child = agent.pipeline.active_agents.get(subagent_id)
    if not child or child.rollout.parent != agent.rollout.id:
        return f"Subagent {subagent_id!r} is not active."
    await agent.pipeline.cancel_agent(subagent_id)
    return f"Cancelled subagent {subagent_id}."
    
def tools(session: Session, agent: Agent, filter_regex: Optional[str] = None):
    ...
    
def bash(session: Session, agent: Agent):
    # TODO
    ...
