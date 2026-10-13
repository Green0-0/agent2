import json
import inspect
from typing import Any
from agent2.core.objects import Hook, HookResult, PendingContinuation
from agent2.core.agent import Agent


def _unpack(result: Any) -> tuple[str | None, PendingContinuation | None]:
    if not isinstance(result, tuple):
        return (None if result is None else str(result)), None
    if len(result) != 2 or not callable(result[1]):
        raise TypeError("Continuation tool results must be (content, callable)")
    return str(result[0]), result[1]

class ToolCallHook(Hook):
    """
    Parses the LLM response for tool calls, executes them by finding the matching
    Tool wrapper in `agent.tools`, and directly appends the required OpenAI tool 
    messages to `agent.rollout.raw_chat`.
    """
    async def run(self, agent: Agent, response: Any) -> HookResult | None:
        message = response.choices[0].message

        if agent.pending_continuation:
            continuation = agent.pending_continuation
            agent.pending_continuation = None
            try:
                result = continuation(message)
                if inspect.isawaitable(result):
                    result = await result
                output, agent.pending_continuation = _unpack(result)
            except Exception as e:
                output = f"Error executing continuation: {e}"
            return HookResult(output, consumed=True)
        
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return None

        continuations = []
        for call in message.tool_calls:
            agent.session.refresh_files()
            tool_name = call.function.name
            args_str = call.function.arguments
            
            tool_msg = {
                "role": "tool",
                "tool_call_id": call.id,
                "name": tool_name,
            }
            
            if hasattr(agent, "tools") and tool_name in agent.tools:
                try:
                    tool_wrapper = agent.tools[tool_name]
                    args = json.loads(args_str)

                    sig = inspect.signature(tool_wrapper.func)
                    if "agent" in sig.parameters:
                        args["agent"] = agent
                    if "session" in sig.parameters:
                        args["session"] = getattr(agent, "session", None)
                    if "agentconfig" in sig.parameters:
                        args["agentconfig"] = getattr(agent, "config", None)
                        
                    result = tool_wrapper(**args)
                    if inspect.isawaitable(result):
                        result = await result
                    tool_msg["content"], continuation = _unpack(result)
                    if continuation:
                        continuations.append((tool_msg, continuation))
                except Exception as e:
                    tool_msg["content"] = f"Error executing tool {tool_name}: {e}"
            else:
                tool_msg["content"] = f"Error: Tool {tool_name} not found."
                
            agent.rollout.raw_chat.append(tool_msg)

        if len(continuations) == 1:
            agent.pending_continuation = continuations[0][1]
        elif len(continuations) > 1:
            error = (
                "Error: Multiple continuation tools were called in one response. "
                "No continuation was bound; call one at a time."
            )
            for tool_msg, _ in continuations:
                tool_msg["content"] = error

        return HookResult(consumed=True)
