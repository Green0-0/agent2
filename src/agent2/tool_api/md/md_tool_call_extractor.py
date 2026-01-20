import ast
import re

from typing import List, Dict, Tuple
from agent2.tool_api.abc.tool_call_extractor import ToolCallExtractor, ToolError, DuplicateArgumentError

class MDToolCallExtractor(ToolCallExtractor):
    """
    Extracts Markdown tool calls from text responses.
    """
    def __init__(self, tool_start: str = "# Tool Use", tool_end: str = "# Tool End"):
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
        # Check for mismatched tags
        num_starts = response_str.count(self.tool_start)
        num_ends = response_str.count(self.tool_end)
        
        # Adjust for overlapping tags (e.g. ```json contains ```)
        if num_starts > 0 and self.tool_end in self.tool_start:
            num_ends -= num_starts * self.tool_start.count(self.tool_end)
            
        if num_starts > num_ends:
            return response_str, [], [ToolError.TOOL_END_MISSING]
        if num_ends > num_starts:
            return response_str, [], [ToolError.TOOL_START_MISSING]

        tool_calls = []
        errors = []
        
        # Escape tags for regex
        start_tag_esc = re.escape(self.tool_start)
        end_tag_esc = re.escape(self.tool_end)
        
        # Pattern to find tool call blocks
        pattern = f"{start_tag_esc}(.*?){end_tag_esc}"
        
        matches = list(re.finditer(pattern, response_str, re.DOTALL))
        
        if not matches:
            return response_str, [], []
            
        # Identify contiguous matches
        contiguous_matches = []
        if matches:
            contiguous_matches.append(matches[0])
            for i in range(1, len(matches)):
                prev_match = matches[i-1]
                curr_match = matches[i]
                intervening_text = response_str[prev_match.end():curr_match.start()]
                if intervening_text.strip():
                    # Found non-whitespace text between tool calls, stop here
                    break
                contiguous_matches.append(curr_match)
        
        # The message is everything before the first tool call
        cleaned_response = response_str[:contiguous_matches[0].start()].strip()
        
        for match in contiguous_matches:
            content = match.group(1)
            if not content.strip():
                errors.append(ToolError.TOOL_MALFORMATTED)
                continue
                
            content = match.group(1).strip()
            
            try:
                tool_call = self._parse_single_call(content)
                tool_calls.append(tool_call)
            except DuplicateArgumentError:
                errors.append(ToolError.TOOL_DUPLICATE_ARGUMENT)
            except (ValueError, KeyError, Exception):
                errors.append(ToolError.TOOL_MALFORMATTED)
                
        if errors:
            return response_str, [], errors
            
        return cleaned_response, tool_calls, []

    def _parse_single_call(self, input_str: str) -> Dict:
        """
        Parses the content inside a tool call block.
        """
        def parse_value(s: str):
            stripped = s.strip()
            if stripped.lower() in ("true", "false"):
                return stripped.lower() == "true"
            try:
                return int(stripped)
            except ValueError:
                try:
                    return float(stripped)
                except ValueError:
                    # Try to parse as a complex structure (list, dict)
                    try:
                        val = ast.literal_eval(stripped)
                        if isinstance(val, (list, dict)):
                            return val
                    except (ValueError, SyntaxError):
                        pass
                    return stripped

        lines = [line for line in input_str.split('\n')]
        
        if not lines:
            raise ValueError("Empty tool call content")

        # Parse tool name
        # Find first non-empty line
        first_line_idx = 0
        while first_line_idx < len(lines) and not lines[first_line_idx].strip():
            first_line_idx += 1
            
        if first_line_idx >= len(lines):
            raise ValueError("Empty tool call content")
            
        if not lines[first_line_idx].startswith('## Name: '):
            raise KeyError("First line must be '## Name: [tool_name]'")
            
        name = lines[first_line_idx][len('## Name: '):].strip()
        result = {"name": name, "arguments": {}}

        current_param = None
        current_value = []

        for line in lines[first_line_idx + 1:]:
            if line.startswith('### '):
                if current_param is not None:
                    # Save the previous parameter
                    value_str = '\n'.join(current_value).strip()
                    parsed_value = parse_value(value_str)
                    result['arguments'][current_param] = parsed_value
                    current_value = []
                
                # Parse new parameter
                param_line = line[len('### '):]
                if ':' not in param_line:
                    # Maybe it's a malformed line, or just '### param:' with empty value on this line
                    if param_line.strip().endswith(':'):
                        param_name = param_line.strip()[:-1]
                        param_value = ""
                    else:
                        raise ValueError(f"Parameter line missing colon: {line}")
                else:
                    param_name, param_value = param_line.split(':', 1)
                
                current_param = param_name.strip()
                current_value.append(param_value) # Don't strip yet, might be multiline
                
                # Check for duplicate parameters
                if current_param in result['arguments']:
                    raise DuplicateArgumentError(f"Duplicate parameter: {current_param}")
            else:
                if current_param is None:
                    # Ignore empty lines before first param
                    if not line.strip():
                        continue
                    raise ValueError(f"Line '{line}' is not part of any parameter")
                current_value.append(line)
        
        # Add the last parameter
        if current_param is not None:
            value_str = '\n'.join(current_value).strip()
            parsed_value = parse_value(value_str)
            result['arguments'][current_param] = parsed_value

        return result
