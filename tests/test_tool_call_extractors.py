import pytest
from agent2.tool_api.xml.xml_tool_call_extractor import XMLToolCallExtractor
from agent2.tool_api.json.json_tool_call_extractor import JSONToolCallExtractor
from agent2.tool_api.md.md_tool_call_extractor import MDToolCallExtractor
from agent2.tool_api.abc.tool_call_extractor import ToolError

def print_conversion(format_name, input_str, output_tuple):
    print(f"\n--- {format_name} Extraction Test ---")
    print(f"Input:\n{input_str}")
    print(f"Output Message: {output_tuple[0]}")
    print(f"Output Tool Calls: {output_tuple[1]}")
    print(f"Output Errors: {output_tuple[2]}")
    print("-" * 30)

class TestXMLToolCallExtractor:
    def test_basic_extraction(self):
        extractor = XMLToolCallExtractor()
        response = """
        Here is a tool call:
        <tool_call>
        <name>search_web</name>
        <query>python testing</query>
        </tool_call>
        End of message.
        """
        result = extractor.extract(response)
        print_conversion("XML", response, result)
        
        message, tool_calls, errors = result
        assert "Here is a tool call:" in message
        assert "End of message." in message
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "search_web"
        assert tool_calls[0]["arguments"]["query"] == "python testing"
        assert len(errors) == 0

    def test_multiple_tool_calls(self):
        extractor = XMLToolCallExtractor()
        response = """
        <tool_call>
        <name>tool1</name>
        <arg1>value1</arg1>
        </tool_call>
        Text in between.
        <tool_call>
        <name>tool2</name>
        <arg2>123</arg2>
        </tool_call>
        """
        result = extractor.extract(response)
        print_conversion("XML", response, result)
        
        message, tool_calls, errors = result
        assert message == "Text in between."
        assert len(tool_calls) == 2
        assert tool_calls[0]["name"] == "tool1"
        assert tool_calls[1]["name"] == "tool2"
        assert tool_calls[1]["arguments"]["arg2"] == 123

    def test_edge_cases(self):
        extractor = XMLToolCallExtractor()
        # Missing name
        response = "<tool_call><arg>val</arg></tool_call>"
        result = extractor.extract(response)
        print_conversion("XML - Missing Name", response, result)
        assert len(result[2]) > 0 # Should have errors
        
        # Duplicate args
        response = """
        <tool_call>
        <name>test</name>
        <arg>1</arg>
        <arg>2</arg>
        </tool_call>
        """
        result = extractor.extract(response)
        print_conversion("XML - Duplicate Args", response, result)
        assert len(result[2]) > 0

class TestJSONToolCallExtractor:
    def test_markdown_block_extraction(self):
        extractor = JSONToolCallExtractor()
        response = """
        Sure, I can help.
        ```json
        {
            "name": "calculator",
            "arguments": {
                "expression": "2 + 2"
            }
        }
        ```
        """
        result = extractor.extract(response)
        print_conversion("JSON - Markdown", response, result)
        
        message, tool_calls, errors = result
        assert "Sure, I can help." in message
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "calculator"
        assert tool_calls[0]["arguments"]["expression"] == "2 + 2"

    def test_list_of_tools(self):
        extractor = JSONToolCallExtractor()
        response = """
        ```json
        [
            {"name": "tool1", "arguments": {"a": 1}},
            {"name": "tool2", "arguments": {"b": 2}}
        ]
        ```
        """
        result = extractor.extract(response)
        print_conversion("JSON - List", response, result)
        
        message, tool_calls, errors = result
        assert len(tool_calls) == 2
        assert tool_calls[0]["name"] == "tool1"
        assert tool_calls[1]["name"] == "tool2"

    def test_raw_json_extraction(self):
        extractor = JSONToolCallExtractor()
        response = '{"name": "raw_tool", "arguments": {"x": true}}'
        result = extractor.extract(response)
        print_conversion("JSON - Raw", response, result)
        
        message, tool_calls, errors = result
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "raw_tool"
        assert tool_calls[0]["arguments"]["x"] is True

class TestMDToolCallExtractor:
    def test_basic_extraction(self):
        extractor = MDToolCallExtractor()
        response = """
        I will use a tool.
        # Tool Use
        ## Name: file_search
        ### pattern: *.py
        ### path: /src
        # Tool End
        """
        result = extractor.extract(response)
        print_conversion("MD", response, result)
        
        message, tool_calls, errors = result
        assert "I will use a tool." in message
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "file_search"
        assert tool_calls[0]["arguments"]["pattern"] == "*.py"
        assert tool_calls[0]["arguments"]["path"] == "/src"

    def test_multiline_argument(self):
        extractor = MDToolCallExtractor()
        response = """
        # Tool Use
        ## Name: write_file
        ### content:
        def hello():
            print("world")
        ### filename: hello.py
        # Tool End
        """
        result = extractor.extract(response)
        print_conversion("MD - Multiline", response, result)
        
        message, tool_calls, errors = result
        assert len(tool_calls) == 1
        assert "def hello():" in tool_calls[0]["arguments"]["content"]
        assert tool_calls[0]["arguments"]["filename"] == "hello.py"

    def test_edge_cases(self):
        extractor = MDToolCallExtractor()
        # Missing name
        response = """
        # Tool Use
        ### arg: val
        # Tool End
        """
        result = extractor.extract(response)
        print_conversion("MD - Missing Name", response, result)
        assert len(result[2]) > 0
