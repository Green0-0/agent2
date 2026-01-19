from agent2.agent_rework.tool import Tool


class BoundTool:
    """
    A BoundTool represents a *forced* tool invocation that the agent will execute 
    in the next step, regardless of whether the LLM output requests it.

    This is usually returned by another Tool in order to "bind" a follow-up action.

    Attributes
    ----------
    tag   : str
        An arbitrary identifier for this binding. Can be used for logging, 
        debugging, or conditional binding in the agent.
    tool  : Tool
        The tool object that will be invoked in the agent’s next run.
    """

    def __init__(self, tag: str, tool: Tool):
        self.tag = tag
        self.tool = tool

    def __repr__(self):
        return f"<BoundTool tag={self.tag!r} tool={self.tool.name!r}>"
