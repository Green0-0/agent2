import json
import re
from typing import List, Dict, Tuple, Optional
from agent2.tool_api.abc.tool_call_extractor import ToolCallExtractor, ToolError, DuplicateArgumentError

class JSONToolCallExtractor(ToolCallExtractor):
    """
    Extracts JSON tool calls from text responses.
    Parses JSON inside blocks delimited by tool_start and tool_end.
    """
    def __init__(self, tool_start: str = "```json", tool_end: str = "```"):
        self.tool_start = tool_start
        self.tool_end = tool_end

    def extract(self, response_str: str) -> Tuple[str, List[Dict], List[ToolError]]:
        """
        Extracts tool calls from the response string.

        Parse the first run of tool blocks separated only by whitespace.
        Text after the first block begins is omitted on success. If no blocks
        are found or extraction fails, preserve the original response; failures
        return no calls and report extraction errors.
        
        Args:
            response_str (str): The raw response from the model.
            
        Returns:
            Tuple[str, List[Dict], List[ToolError]]: 
                - The stripped assistant text before the first tool block,
                  or the original response when no blocks are found or parsing fails.
                - A list of extracted tool call dictionaries.
                - A list of errors encountered during extraction.
        """
        num_starts = response_str.count(self.tool_start)
        num_ends = response_str.count(self.tool_end)
        
        if num_starts > 0 and self.tool_end in self.tool_start:
            num_ends -= num_starts * self.tool_start.count(self.tool_end)
            
        if num_starts > num_ends:
            return response_str, [], [ToolError.TOOL_END_MISSING]
        if num_ends > num_starts:
            return response_str, [], [ToolError.TOOL_START_MISSING]

        tool_calls = []
        errors = []

        start_tag_esc = re.escape(self.tool_start)
        end_tag_esc = re.escape(self.tool_end)
        
        pattern = f"{start_tag_esc}(.*?){end_tag_esc}"
        
        matches = list(re.finditer(pattern, response_str, re.DOTALL))
        
        if not matches:
            return response_str, [], []

        contiguous_matches = []
        if matches:
            contiguous_matches.append(matches[0])
            for i in range(1, len(matches)):
                prev_match = matches[i-1]
                curr_match = matches[i]
                intervening_text = response_str[prev_match.end():curr_match.start()]
                if intervening_text.strip():
                    break
                contiguous_matches.append(curr_match)
        
        cleaned_response = response_str[:contiguous_matches[0].start()].strip()
        
        def duplicate_key_check(ordered_pairs):
            d = {}
            for k, v in ordered_pairs:
                if k in d:
                    raise DuplicateArgumentError(f"Duplicate key: {k}")
                d[k] = v
            return d

        for match in contiguous_matches:
            content = match.group(1).strip()
            try:
                parsed = json.loads(content, object_pairs_hook=duplicate_key_check)
                
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict):
                            tool_calls.append(item)
                        else:
                            errors.append(ToolError.TOOL_MALFORMATTED)
                elif isinstance(parsed, dict):
                    tool_calls.append(parsed)
                else:
                    errors.append(ToolError.TOOL_MALFORMATTED)
            except DuplicateArgumentError:
                errors.append(ToolError.TOOL_DUPLICATE_ARGUMENT)
            except (json.JSONDecodeError, Exception):
                errors.append(ToolError.TOOL_MALFORMATTED)
        
        if errors:
            return response_str, [], errors
                
        return cleaned_response, tool_calls, []
