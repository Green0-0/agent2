from agent2.core.tools.tool import Tool


def test_tool_schema_handles_postponed_annotations():
    def example(line: "int", full: "bool" = False):
        pass

    properties = Tool(example).openai_schema["function"]["parameters"]["properties"]
    assert properties["line"]["type"] == "integer"
    assert properties["full"]["type"] == "boolean"
