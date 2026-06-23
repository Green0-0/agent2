import pytest
from agent2.tool_api.generic_response_builder import GenericResponseBuilder

def test_generic_response_builder():
    """Test that GenericResponseBuilder properly joins multiple responses."""
    builder = GenericResponseBuilder()
    tool_responses = [
        {"role": "tool", "content": "First response", "name": "tool1"},
        {"role": "tool", "content": "Second response", "name": "tool2"}
    ]
    
    result = builder.build(tool_responses)
    
    assert result == "First response\nSecond response"

def test_generic_response_builder_empty():
    """Test that GenericResponseBuilder handles an empty response list."""
    builder = GenericResponseBuilder()
    assert builder.build([]) == ""

def test_generic_response_builder_single():
    """Test that GenericResponseBuilder handles a single response."""
    builder = GenericResponseBuilder()
    assert builder.build([{"role": "tool", "content": "Single response"}]) == "Single response"
