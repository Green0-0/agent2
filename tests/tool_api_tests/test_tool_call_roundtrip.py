import json
import pytest
from typing import List, Dict
from agent2.tool_api.xml.xml_tool_call_builder import XMLToolCallBuilder
from agent2.tool_api.xml.xml_tool_call_extractor import XMLToolCallExtractor
from agent2.tool_api.json.json_tool_call_builder import JSONToolCallBuilder
from agent2.tool_api.json.json_tool_call_extractor import JSONToolCallExtractor
from agent2.tool_api.md.md_tool_call_builder import MDToolCallBuilder
from agent2.tool_api.md.md_tool_call_extractor import MDToolCallExtractor

from agent2.tool_api.fake_codeact.fake_codeact_tool_call_builder import FakeCodeActToolCallBuilder
from agent2.tool_api.fake_codeact.fake_codeact_tool_call_extractor import FakeCodeActToolCallExtractor

def normalize_whitespace(s: str) -> str:
    """Normalize whitespace for comparison."""
    return "\n".join([line.strip() for line in s.strip().splitlines() if line.strip()])

def run_roundtrip_test(builder_cls, extractor_cls, tool_calls: List[Dict], format_name: str):
    print(f"--- Starting Roundtrip Test for {format_name} ---")
    
    builder = builder_cls()
    extractor = extractor_cls()
    
    # 1. Generate message with tool call using builder
    generated_text = builder.build(tool_calls)
    print(f"Generated Text:\n{generated_text}")
    
    # 2. Attempt to extract it again
    cleaned_text, extracted_calls, errors = extractor.extract(generated_text)
    
    if errors:
        print(f"Extraction Errors: {errors}")
        pytest.fail(f"Extraction failed with errors: {errors}")
        
    print(f"Extracted Calls: {extracted_calls}")
    
    # 3. Build it again
    # We need to convert extracted calls back to the format expected by builder
    # Builder expects: [{'function': {'name': '...', 'arguments': 'json_string'}}]
    # Extracted calls are: [{'name': '...', 'arguments': {...}}]
    
    reconstructed_tool_calls = []
    for call in extracted_calls:
        reconstructed_call = {
            "type": "function",
            "function": {
                "name": call["name"],
                "arguments": json.dumps(call["arguments"])
            }
        }
        reconstructed_tool_calls.append(reconstructed_call)
        
    rebuilt_text = builder.build(reconstructed_tool_calls)
    print(f"Rebuilt Text:\n{rebuilt_text}")
    
    # 4. Check if the final result is the exact same
    if generated_text != rebuilt_text:
        print(f"Generated text and rebuilt text differ for {format_name}.")
        
        norm_gen = normalize_whitespace(generated_text)
        norm_rebuilt = normalize_whitespace(rebuilt_text)
        
        if norm_gen == norm_rebuilt:
            print("Difference is only whitespace.")
        else:
            print("Difference is NOT just whitespace.")
            print(f"Normalized Generated:\n{norm_gen}")
            print(f"Normalized Rebuilt:\n{norm_rebuilt}")
            pytest.fail(f"Roundtrip failed for {format_name}: Content mismatch.")
    else:
        print(f"Roundtrip successful for {format_name} (Exact match).")

def test_xml_roundtrip():
    tool_calls = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "arguments": json.dumps({
                    "query": "python testing",
                    "limit": 5,
                    "verbose": True
                })
            }
        }
    ]
    run_roundtrip_test(XMLToolCallBuilder, XMLToolCallExtractor, tool_calls, "XML")

def test_json_roundtrip():
    tool_calls = [
        {
            "type": "function",
            "function": {
                "name": "calculate_sum",
                "arguments": json.dumps({
                    "a": 10,
                    "b": 20,
                    "operation": "add"
                })
            }
        }
    ]
    run_roundtrip_test(JSONToolCallBuilder, JSONToolCallExtractor, tool_calls, "JSON")

def test_md_roundtrip():
    tool_calls = [
        {
            "type": "function",
            "function": {
                "name": "create_file",
                "arguments": json.dumps({
                    "filename": "test.txt",
                    "content": "Hello\nWorld"
                })
            }
        }
    ]
    run_roundtrip_test(MDToolCallBuilder, MDToolCallExtractor, tool_calls, "Markdown")

def test_codeact_roundtrip():
    tool_calls = [
        {
            "type": "function",
            "function": {
                "name": "python_tool",
                "arguments": json.dumps({
                    "code": "print('hello')",
                    "execution_id": 123
                })
            }
        }
    ]
    run_roundtrip_test(FakeCodeActToolCallBuilder, FakeCodeActToolCallExtractor, tool_calls, "CodeAct")

def test_complex_types_roundtrip():
    # Test with lists and nested structures if supported
    tool_calls = [
        {
            "type": "function",
            "function": {
                "name": "process_data",
                "arguments": json.dumps({
                    "ids": [1, 2, 3],
                    "metadata": {"source": "api", "version": 1.0}
                })
            }
        }
    ]
    
    # XML supports simple string conversion of lists/dicts via str() and ast.literal_eval()
    run_roundtrip_test(XMLToolCallBuilder, XMLToolCallExtractor, tool_calls, "XML Complex")
    
    # JSON naturally supports it
    run_roundtrip_test(JSONToolCallBuilder, JSONToolCallExtractor, tool_calls, "JSON Complex")
    
    # MD uses str() and might be tricky with newlines in dicts, but let's see
    run_roundtrip_test(MDToolCallBuilder, MDToolCallExtractor, tool_calls, "Markdown Complex")

    # CodeAct supports complex types via python syntax
    run_roundtrip_test(FakeCodeActToolCallBuilder, FakeCodeActToolCallExtractor, tool_calls, "CodeAct Complex")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
