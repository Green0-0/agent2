import json
import re
from typing import List, Dict, Tuple, Optional
from agent2.tool_api.abc.tool_call_extractor import ToolCallExtractor, ToolError

class JSONToolCallExtractor(ToolCallExtractor):
    """
    Extracts JSON tool calls from text responses.
    Supports extracting from markdown code blocks or raw JSON.
    """
    def __init__(self, tool_start: Optional[str] = None, tool_end: Optional[str] = None):
        self.tool_start = tool_start
        self.tool_end = tool_end

    def extract(self, response_str: str) -> Tuple[str, List[Dict], List[ToolError]]:
        """
        Extracts tool calls from the response string.
        
        Args:
            response_str (str): The raw response from the model.
            
        Returns:
            Tuple[str, List[Dict], List[ToolError]]: 
                - The response text with tool calls removed.
                - A list of extracted tool call dictionaries.
                - A list of errors encountered during extraction.
        """
        tool_calls = []
        errors = []
        cleaned_response = response_str
        
        json_blocks = []
        
        # Strategy 1: If tool_start/end are defined, use them
        if self.tool_start and self.tool_end:
            pattern = re.escape(self.tool_start) + r"(.*?)" + re.escape(self.tool_end)
            matches = list(re.finditer(pattern, response_str, re.DOTALL))
            
            if matches:
                cleaned_response = ""
                last_pos = 0
                for match in matches:
                    cleaned_response += response_str[last_pos:match.start()]
                    last_pos = match.end()
                    json_blocks.append(match.group(1).strip())
                cleaned_response += response_str[last_pos:]
        
        # Strategy 2: Look for markdown code blocks ```json ... ``` or ``` ... ```
        if not json_blocks:
            code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            matches = list(re.finditer(code_block_pattern, response_str, re.DOTALL))
            
            if matches:
                # We only extract if we find valid JSON in blocks
                # But we need to be careful not to remove non-tool code blocks if they exist.
                # For now, let's assume if we find JSON-parsable blocks, they are tools.
                
                # To properly handle mixed content, we might need a more complex approach.
                # Here we will try to parse each block.
                
                temp_cleaned = ""
                last_pos = 0
                found_valid_json = False
                
                for match in matches:
                    content = match.group(1).strip()
                    try:
                        parsed = json.loads(content)
                        # Heuristic: It's a tool call if it's a list of dicts or a dict with 'name'/'arguments'
                        is_tool = False
                        if isinstance(parsed, list):
                            if all(isinstance(x, dict) and "name" in x for x in parsed):
                                is_tool = True
                        elif isinstance(parsed, dict):
                            if "name" in parsed:
                                is_tool = True
                        
                        if is_tool:
                            json_blocks.append(content)
                            temp_cleaned += response_str[last_pos:match.start()]
                            last_pos = match.end()
                            found_valid_json = True
                        else:
                            # Not a tool call, keep it
                            temp_cleaned += response_str[last_pos:match.end()]
                            last_pos = match.end()
                    except json.JSONDecodeError:
                        # Not JSON, keep it
                        temp_cleaned += response_str[last_pos:match.end()]
                        last_pos = match.end()
                
                if found_valid_json:
                    temp_cleaned += response_str[last_pos:]
                    cleaned_response = temp_cleaned

        # Strategy 3: If still no blocks, try to find a JSON list or object in the text
        # This is risky as it might match random text, so we only do it if we haven't found anything yet
        # and if the text looks like it starts/ends with JSON structure.
        if not json_blocks and not errors:
            stripped = response_str.strip()
            if (stripped.startswith("[") and stripped.endswith("]")) or \
               (stripped.startswith("{") and stripped.endswith("}")):
                try:
                    # Check if it parses
                    json.loads(stripped)
                    json_blocks.append(stripped)
                    cleaned_response = "" # It was all JSON
                except json.JSONDecodeError:
                    pass

        # Process extracted blocks
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            tool_calls.append(item)
                        else:
                            errors.append(ToolError.TOOL_SYNTAX_MISMATCH)
                elif isinstance(parsed, dict):
                    tool_calls.append(parsed)
                else:
                    errors.append(ToolError.TOOL_SYNTAX_MISMATCH)
            except json.JSONDecodeError:
                errors.append(ToolError.TOOL_SYNTAX_MISMATCH)
        
        if not tool_calls and not errors and not json_blocks:
            # No tools found
            pass
            
        return cleaned_response.strip(), tool_calls, errors
