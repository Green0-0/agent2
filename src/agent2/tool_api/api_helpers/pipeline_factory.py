from typing import Any, Dict
from agent2.tool_api.abc.tool_pipeline import ToolPipeline
from agent2.tool_api.pipeline import StandardToolPipeline
from agent2.tool_api.xml.xml_tool_call_builder import XMLToolCallBuilder
from agent2.tool_api.xml.xml_tool_call_extractor import XMLToolCallExtractor
from agent2.tool_api.xml.xml_tool_schema_builder import XMLToolSchemaBuilder
from agent2.tool_api.json.json_tool_call_builder import JSONToolCallBuilder
from agent2.tool_api.json.json_tool_call_extractor import JSONToolCallExtractor
from agent2.tool_api.json.json_tool_schema_builder import JSONToolSchemaBuilder
from agent2.tool_api.md.md_tool_call_builder import MDToolCallBuilder
from agent2.tool_api.md.md_tool_call_extractor import MDToolCallExtractor
from agent2.tool_api.md.md_tool_schema_builder import MDToolSchemaBuilder
from agent2.tool_api.fake_codeact.fake_codeact_tool_call_builder import FakeCodeActToolCallBuilder
from agent2.tool_api.fake_codeact.fake_codeact_tool_call_extractor import FakeCodeActToolCallExtractor
from agent2.tool_api.fake_codeact.fake_codeact_tool_schema_builder import FakeCodeActToolSchemaBuilder
from agent2.tool_api.generic_response_builder import GenericResponseBuilder

def build_pipeline(
    fmt: str = "xml", **kwargs: Any
) -> ToolPipeline:
    """
    Build a fully wired ToolPipeline for the requested format.
    Add new branches here when you implement additional formats (json, yaml, etc.).
    """
    response_builder = GenericResponseBuilder()
    schema_key = kwargs.get("schema_key", "{{llm_tools_list}}")
    replace_schema_all = kwargs.get("replace_schema_all", True)
    
    if fmt == "xml":
        tool_start = kwargs.get("tool_start", "<tool_call>")
        tool_end = kwargs.get("tool_end", "</tool_call>")
        builder = XMLToolCallBuilder(tool_start=tool_start, tool_end=tool_end)
        extractor = XMLToolCallExtractor(tool_start=tool_start, tool_end=tool_end)
        schema_builder = XMLToolSchemaBuilder()
    elif fmt == "json":
        tool_start = kwargs.get("tool_start", "```json")
        tool_end = kwargs.get("tool_end", "```")
        builder = JSONToolCallBuilder(tool_start=tool_start, tool_end=tool_end)
        extractor = JSONToolCallExtractor(tool_start=tool_start, tool_end=tool_end)
        schema_builder = JSONToolSchemaBuilder()
    elif fmt == "md":
        tool_start = kwargs.get("tool_start", "# Tool Use")
        tool_end = kwargs.get("tool_end", "# Tool End")
        builder = MDToolCallBuilder(tool_start=tool_start, tool_end=tool_end)
        extractor = MDToolCallExtractor(tool_start=tool_start, tool_end=tool_end)
        schema_builder = MDToolSchemaBuilder()
    elif fmt == "fake_codeact":
        tool_start = kwargs.get("tool_start", "<code>")
        tool_end = kwargs.get("tool_end", "</code>")
        builder = FakeCodeActToolCallBuilder(tool_start=tool_start, tool_end=tool_end)
        extractor = FakeCodeActToolCallExtractor(tool_start=tool_start, tool_end=tool_end)
        schema_builder = FakeCodeActToolSchemaBuilder()
    else:
        raise ValueError(f"Unsupported pipeline format: {fmt}")
        
    return StandardToolPipeline(
        tool_call_extractor=extractor,
        tool_call_builder=builder,
        tool_response_builder=response_builder,
        tool_schema_builder=schema_builder,
        schema_key=schema_key,
        replace_schema_all=replace_schema_all,
    )