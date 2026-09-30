import json
import inspect
from typing import Any, Optional
from agent2.core.objects import Hook
from agent2.core.agent import Agent

class ToolCallHook(Hook):
    """
    Parses the LLM response for tool calls, executes them by finding the matching
    Tool wrapper in `agent.tools`, and directly appends the required OpenAI tool 
    messages to `agent.rollout.raw_chat`.
    """
    def run(self, agent: Agent, response: Any) -> Optional[str]:
        # If there are no tool calls, there's nothing to execute.
        message = response.choices[0].message
        
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            return None
            
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
                    
                    # Tool.py skips agent and session from the OpenAI schema, 
                    # so we must inject them here if the underlying function needs them.
                    sig = inspect.signature(tool_wrapper.func)
                    if "agent" in sig.parameters:
                        args["agent"] = agent
                    if "session" in sig.parameters:
                        args["session"] = getattr(agent, "session", None)
                    if "agentconfig" in sig.parameters:
                        args["agentconfig"] = getattr(agent, "config", None)
                        
                    result = tool_wrapper(**args)
                    tool_msg["content"] = str(result)
                except Exception as e:
                    tool_msg["content"] = f"Error executing tool {tool_name}: {e}"
            else:
                tool_msg["content"] = f"Error: Tool {tool_name} not found."
                
            agent.rollout.raw_chat.append(tool_msg)
            
        return None
