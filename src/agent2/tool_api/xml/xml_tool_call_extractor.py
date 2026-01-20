from typing import List, Dict, Tuple
import re
import ast
from agent2.tool_api.abc.tool_call_extractor import ToolCallExtractor, ToolError, DuplicateArgumentError

class XMLToolCallExtractor(ToolCallExtractor):
    """
    Extracts XML tool calls from text responses.
    """
    def __init__(self, tool_start: str = "<tool_call>", tool_end: str = "</tool_call>"):
        self.tool_start = tool_start
        self.tool_end = tool_end

    def extract(self, response_str: str) -> Tuple[str, List[Dict], List[ToolError]]:
        """
        Extracts tool calls from the response string.
        
        Args:
            response_str (str): The raw response from the model.
            
        Returns:
            Tuple[str, List[Dict], List[ToolError]]: 
                - The response text with tool calls removed (or just the text part).
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
            # No tool calls found
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
            content = match.group(1).strip()
            if not content:
                errors.append(ToolError.TOOL_MALFORMATTED)
                continue
                
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
        Adapted from XMLToolFormatter.string_to_json.
        """
        def unescape_xml(text: str) -> str:
            replacements = {
                "&amp;": "&",
                "&lt;": "<",
                "&gt;": ">",
                "&quot;": "\"",
                "&apos;": "'"
            }
            for esc, char in replacements.items():
                text = text.replace(esc, char)
            return text

        def parse_value(s: str):
            s = s.strip()
            if s.lower() in ("true", "false"):
                return s.lower() == "true"
            try:
                return int(s)
            except ValueError:
                try:
                    return float(s)
                except ValueError:
                    # Try to parse as a complex structure (list, dict)
                    try:
                        val = ast.literal_eval(s)
                        if isinstance(val, (list, dict)):
                            return val
                    except (ValueError, SyntaxError):
                        pass
                    return s

        # Find all XML elements with their content
        # This regex matches <tag>content</tag>
        elements = re.findall(r"<([a-zA-Z0-9_]+)>(.*?)</\1>", input_str, re.DOTALL)
        
        if not elements:
            raise ValueError("No valid XML elements found")

        # Validate first element is the name tag
        name_tag, name_content = elements[0]
        if name_tag != "name":
            raise KeyError("First element must be <name>")
            
        name_value = unescape_xml(name_content.strip())
        if not name_value:
            raise ValueError("Name value cannot be empty")

        result = {"name": name_value, "arguments": {}}

        # Process remaining elements as arguments
        seen_tags = set()
        for tag, content in elements[1:]:
            if tag in seen_tags:
                raise DuplicateArgumentError(f"Duplicate argument '{tag}'")
            seen_tags.add(tag)
            
            cleaned = parse_value(unescape_xml(content))
            result["arguments"][tag] = cleaned

        return result
