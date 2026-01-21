import pytest
import json
from typing import Tuple, List, Dict
from agent2.tool_api.xml.xml_tool_call_extractor import XMLToolCallExtractor
from agent2.tool_api.json.json_tool_call_extractor import JSONToolCallExtractor
from agent2.tool_api.md.md_tool_call_extractor import MDToolCallExtractor
from agent2.tool_api.abc.tool_call_extractor import ToolError

def log_test_result(test_name: str, input_str: str, result: Tuple[str, List[Dict], List[ToolError]]):
    """Helper to print test results in a clean, readable format."""
    message, tool_calls, errors = result
    
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'-'*80}")
    print("INPUT:")
    print(f"{'-'*20}")
    print(input_str.strip())
    print(f"{'-'*20}")
    print("EXTRACTED MESSAGE:")
    print(f"'{message}'")
    print(f"{'-'*20}")
    print("TOOL CALLS:")
    print(json.dumps(tool_calls, indent=2))
    print(f"{'-'*20}")
    if errors:
        print("ERRORS:")
        print(errors)
        print(f"{'-'*20}")
    print(f"{'='*80}\n")

class TestXMLToolCallExtractor:
    def test_basic_extraction(self):
        extractor = XMLToolCallExtractor()
        response = """Here is a tool call:
<tool_call>
<name>search_web</name>
<query>python testing</query>
</tool_call>
End of message."""
        
        result = extractor.extract(response)
        log_test_result("XML - Basic Extraction", response, result)
        
        message, tool_calls, errors = result
        assert "Here is a tool call:" in message
        assert "End of message." not in message
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "search_web"
        assert tool_calls[0]["arguments"]["query"] == "python testing"
        assert not errors

    def test_contiguous_extraction(self):
        extractor = XMLToolCallExtractor()
        response = """Message text.
<tool_call>
<name>tool1</name>
<arg1>value1</arg1>
</tool_call>
<tool_call>
<name>tool2</name>
<arg2>123</arg2>
</tool_call>
Text in between.
<tool_call>
<name>tool3</name>
<arg3>456</arg3>
</tool_call>"""
        
        result = extractor.extract(response)
        log_test_result("XML - Contiguous Extraction", response, result)
        
        message, tool_calls, errors = result
        assert message.strip() == "Message text."
        assert len(tool_calls) == 2
        assert tool_calls[0]["name"] == "tool1"
        assert tool_calls[1]["name"] == "tool2"

    def test_error_handling(self):
        extractor = XMLToolCallExtractor()
        response = "<tool_call><arg>val</arg></tool_call>"
        
        result = extractor.extract(response)
        log_test_result("XML - Error Handling (Missing Name)", response, result)
        
        assert len(result[2]) > 0

    def test_list_parsing(self):
        extractor = XMLToolCallExtractor()
        response = """
<tool_call>
<name>test_tool</name>
<items>[1, 2, 3]</items>
</tool_call>
"""
        result = extractor.extract(response)
        log_test_result("XML - List Parsing", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["items"] == [1, 2, 3]

    def test_dict_parsing(self):
        extractor = XMLToolCallExtractor()
        response = """
<tool_call>
<name>test_tool</name>
<config>{'a': 1, 'b': 'val'}</config>
</tool_call>
"""
        result = extractor.extract(response)
        log_test_result("XML - Dict Parsing", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["config"] == {'a': 1, 'b': 'val'}

    def test_tuple_parsing_disabled(self):
        extractor = XMLToolCallExtractor()
        response = """
<tool_call>
<name>test_tool</name>
<point>(10, 20)</point>
</tool_call>
"""
        result = extractor.extract(response)
        log_test_result("XML - Tuple Parsing Disabled", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        # Should be returned as a string now, not a tuple
        assert tool_calls[0]["arguments"]["point"] == "(10, 20)"

    def test_implicit_tuple_as_string(self):
        extractor = XMLToolCallExtractor()
        response = """
<tool_call>
<name>test_tool</name>
<items>1, 2</items>
</tool_call>
"""
        result = extractor.extract(response)
        log_test_result("XML - Implicit Tuple as String", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["items"] == "1, 2"

    def test_nested_complex_types(self):
        extractor = XMLToolCallExtractor()
        response = """
<tool_call>
<name>test_tool</name>
<data>{'users': [{'id': 1}, {'id': 2}], 'meta': (1, 2)}</data>
</tool_call>
"""
        result = extractor.extract(response)
        log_test_result("XML - Nested Complex Types", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["data"] == {'users': [{'id': 1}, {'id': 2}], 'meta': (1, 2)}

    def test_duplicate_args(self):
        extractor = XMLToolCallExtractor()
        response = """
<tool_call>
<name>t1</name>
<arg>v1</arg>
<arg>v2</arg>
</tool_call>
"""
        result = extractor.extract(response)
        log_test_result("XML - Duplicate Args", response, result)
        
        assert result[2] == [ToolError.TOOL_DUPLICATE_ARGUMENT]

class TestJSONToolCallExtractor:
    def test_strict_extraction(self):
        extractor = JSONToolCallExtractor(tool_start="<json>", tool_end="</json>")
        response = """Sure, I can help.
<json>
{
    "name": "calculator",
    "arguments": {
        "expression": "2 + 2"
    }
}
</json>
Truncated text."""
        
        result = extractor.extract(response)
        log_test_result("JSON - Strict Extraction", response, result)
        
        message, tool_calls, errors = result
        assert "Sure, I can help." in message
        assert "Truncated text." not in message
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "calculator"

    def test_contiguous_extraction(self):
        extractor = JSONToolCallExtractor(tool_start="```json", tool_end="```")
        response = """Message.
```json
{"name": "tool1", "arguments": {"a": 1}}
```
```json
{"name": "tool2", "arguments": {"b": 2}}
```
Stop here.
```json
{"name": "tool3", "arguments": {"c": 3}}
```"""
        
        result = extractor.extract(response)
        log_test_result("JSON - Contiguous Extraction", response, result)
        
        message, tool_calls, errors = result
        assert message.strip() == "Message."
        assert len(tool_calls) == 2

    def test_invalid_format(self):
        extractor = JSONToolCallExtractor(tool_start="<json>", tool_end="</json>")
        response = '{"name": "raw_tool", "arguments": {"x": true}}'
        
        result = extractor.extract(response)
        log_test_result("JSON - Invalid Format (No Delimiters)", response, result)
        
        assert len(result[1]) == 0
        assert len(result[1]) == 0
        assert result[0] == response

    def test_duplicate_args(self):
        extractor = JSONToolCallExtractor()
        response = """
```json
{"name": "t1", "arguments": {"arg": "v1", "arg": "v2"}}
```
"""
        result = extractor.extract(response)
        log_test_result("JSON - Duplicate Args", response, result)
        
        assert result[2] == [ToolError.TOOL_DUPLICATE_ARGUMENT]

class TestMDToolCallExtractor:
    def test_basic_extraction(self):
        extractor = MDToolCallExtractor()
        response = """I will use a tool.
# Tool Use
## Name: file_search
### pattern: *.py
### path: /src
# Tool End
Truncated."""
        
        result = extractor.extract(response)
        log_test_result("MD - Basic Extraction", response, result)
        
        message, tool_calls, errors = result
        assert "I will use a tool." in message
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "file_search"

    def test_contiguous_extraction(self):
        extractor = MDToolCallExtractor()
        response = """Start.
# Tool Use
## Name: tool1
### arg: 1
# Tool End
# Tool Use
## Name: tool2
### arg: 2
# Tool End
Break.
# Tool Use
## Name: tool3
### arg: 3
# Tool End"""
        
        result = extractor.extract(response)
        log_test_result("MD - Contiguous Extraction", response, result)
        
        message, tool_calls, errors = result
        assert message.strip() == "Start."
        assert len(tool_calls) == 2

    def test_multiline_arguments(self):
        extractor = MDToolCallExtractor()
        response = """# Tool Use
## Name: write_file
### content:
def hello():
    print("world")
### filename: hello.py
# Tool End"""
        
        result = extractor.extract(response)
        log_test_result("MD - Multiline Arguments", response, result)
        
        assert len(result[1]) == 1
        assert "def hello():" in result[1][0]["arguments"]["content"]

    def test_list_parsing(self):
        extractor = MDToolCallExtractor()
        response = """
# Tool Use
## Name: test_tool
### items: [1, 2, 3]
# Tool End
"""
        result = extractor.extract(response)
        log_test_result("MD - List Parsing", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["items"] == [1, 2, 3]

    def test_dict_parsing(self):
        extractor = MDToolCallExtractor()
        response = """
# Tool Use
## Name: test_tool
### config: {'a': 1, 'b': 'val'}
# Tool End
"""
        result = extractor.extract(response)
        log_test_result("MD - Dict Parsing", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["config"] == {'a': 1, 'b': 'val'}

    def test_tuple_parsing_disabled(self):
        extractor = MDToolCallExtractor()
        response = """
# Tool Use
## Name: test_tool
### point: (10, 20)
# Tool End
"""
        result = extractor.extract(response)
        log_test_result("MD - Tuple Parsing Disabled", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        # Should be returned as a string now, not a tuple
        assert tool_calls[0]["arguments"]["point"] == "(10, 20)"

    def test_implicit_tuple_as_string(self):
        extractor = MDToolCallExtractor()
        response = """
# Tool Use
## Name: test_tool
### items: 1, 2
# Tool End
"""
        result = extractor.extract(response)
        log_test_result("MD - Implicit Tuple as String", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["items"] == "1, 2"

    def test_nested_complex_types(self):
        extractor = MDToolCallExtractor()
        response = """
# Tool Use
## Name: test_tool
### data: {'users': [{'id': 1}, {'id': 2}], 'meta': (1, 2)}
# Tool End
"""
        result = extractor.extract(response)
        log_test_result("MD - Nested Complex Types", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["data"] == {'users': [{'id': 1}, {'id': 2}], 'meta': (1, 2)}

    def test_string_fallback(self):
        extractor = MDToolCallExtractor()
        # "foo" is not a valid python literal (unless it's a variable, which literal_eval rejects)
        # So it should fall back to string "foo"
        response = """
# Tool Use
## Name: test_tool
### status: foo
# Tool End
"""
        result = extractor.extract(response)
        log_test_result("MD - String Fallback", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["status"] == "foo"

    def test_quoted_string_behavior(self):
        extractor = MDToolCallExtractor()
        # "'foo'" is a valid python string literal.
        # ast.literal_eval("'foo'") -> "foo"
        # Previous behavior: "'foo'" -> "'foo'" (string with quotes)
        # New behavior: "'foo'" -> "foo" (string without quotes) IF literal_eval is used for strings.
        # BUT my implementation only returns val if isinstance(val, (list, dict, tuple)).
        # So ast.literal_eval("'foo'") returns "foo" (str), which is NOT in (list, dict, tuple).
        # So it falls through to return stripped -> "'foo'".
        # This preserves backward compatibility for strings!
        response = """
# Tool Use
## Name: test_tool
### status: 'foo'
# Tool End
"""
        result = extractor.extract(response)
        log_test_result("MD - Quoted String Behavior", response, result)
        
        _, tool_calls, errors = result
        assert not errors
        assert len(tool_calls) == 1
        assert tool_calls[0]["arguments"]["status"] == "'foo'"

    def test_duplicate_args(self):
        extractor = MDToolCallExtractor()
        response = """
# Tool Use
## Name: t1
### arg: v1
### arg: v2
# Tool End
"""
        result = extractor.extract(response)
        log_test_result("MD - Duplicate Args", response, result)
        
        assert result[2] == [ToolError.TOOL_DUPLICATE_ARGUMENT]

from agent2.tool_api.fake_codeact.fake_codeact_tool_call_extractor import FakeCodeActToolCallExtractor

class TestFakeCodeActToolCallExtractor:
    def test_basic_extraction(self):
        extractor = FakeCodeActToolCallExtractor()
        response = """
Some text
<code>
tool_name(arg1="value1", arg2=123)
</code>
"""
        result = extractor.extract(response)
        log_test_result("CodeAct - Basic Extraction", response, result)
        
        text, tools, errors = result
        assert text == "Some text"
        assert len(tools) == 1
        assert tools[0]["name"] == "tool_name"
        assert tools[0]["arguments"] == {"arg1": "value1", "arg2": 123}
        assert not errors

    def test_multiple_calls(self):
        extractor = FakeCodeActToolCallExtractor()
        response = """
<code>
tool1(x=1)
tool2(y=2)
</code>
"""
        result = extractor.extract(response)
        log_test_result("CodeAct - Multiple Calls", response, result)
        
        text, tools, errors = result
        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        assert tools[0]["arguments"] == {"x": 1}
        assert tools[1]["name"] == "tool2"
        assert tools[1]["arguments"] == {"y": 2}

    def test_markdown_wrapper(self):
        extractor = FakeCodeActToolCallExtractor()
        response = """
<code>
```python
tool(a=1)
```
</code>
"""
        result = extractor.extract(response)
        log_test_result("CodeAct - Markdown Wrapper", response, result)
        
        text, tools, errors = result
        assert len(tools) == 1
        assert tools[0]["name"] == "tool"
        assert tools[0]["arguments"] == {"a": 1}

    def test_indentation_allowed(self):
        extractor = FakeCodeActToolCallExtractor()
        response = """
<code>
    tool(a=1)
</code>
"""
        result = extractor.extract(response)
        log_test_result("CodeAct - Indentation Allowed", response, result)
        
        text, tools, errors = result
        assert not errors
        assert len(tools) == 1
        assert tools[0]["name"] == "tool"
        assert tools[0]["arguments"] == {"a": 1}

    def test_non_call_code(self):
        extractor = FakeCodeActToolCallExtractor()
        response = """
<code>
x = 1
</code>
"""
        result = extractor.extract(response)
        log_test_result("CodeAct - Non-Call Code", response, result)
        
        assert result[2] == [ToolError.TOOL_MALFORMATTED]

    def test_positional_args_error(self):
        extractor = FakeCodeActToolCallExtractor()
        response = """
<code>
tool(1, 2)
</code>
"""
        result = extractor.extract(response)
        log_test_result("CodeAct - Positional Args Error", response, result)
        
        assert result[2] == [ToolError.TOOL_MALFORMATTED]

    def test_mismatched_tags(self):
        extractor = FakeCodeActToolCallExtractor()
        
        # Missing end tag
        response = "<code>tool()<code>"
        result = extractor.extract(response)
        log_test_result("CodeAct - Missing End Tag", response, result)
        assert result[2] == [ToolError.TOOL_END_MISSING]

        # Missing start tag
        response = "</code>"
        result = extractor.extract(response)
        log_test_result("CodeAct - Missing Start Tag", response, result)
        assert result[2] == [ToolError.TOOL_START_MISSING]
        
        # Extra tags but valid block exists -> Should be valid now
        response = "<code>tool()</code><code>"
        result = extractor.extract(response)
        log_test_result("CodeAct - Extra Tags Valid", response, result)
        assert not result[2]
        assert len(result[1]) == 1
        assert result[1][0]["name"] == "tool"

    def test_markdown_same_line_end(self):
        extractor = FakeCodeActToolCallExtractor()
        response = """
<code>
```python
tool(a=1)```
</code>
"""
        result = extractor.extract(response)
        log_test_result("CodeAct - Markdown Same Line End", response, result)
        
        text, tools, errors = result
        assert len(tools) == 1
        assert tools[0]["name"] == "tool"
        assert tools[0]["arguments"] == {"a": 1}
