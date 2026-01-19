from typing import List, Dict, Tuple
import re
from agent2.tool_api.abc.tool_call_extractor import ToolCallExtractor, ToolError

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
            
        cleaned_response = ""
        last_pos = 0
        
        for match in matches:
            # Append text before this match
            cleaned_response += response_str[last_pos:match.start()]
            last_pos = match.end()
            
            content = match.group(1).strip()
            if not content:
                errors.append(ToolError.TOOL_SYNTAX_MISMATCH)
                continue
                
            try:
                tool_call = self._parse_single_call(content)
                tool_calls.append(tool_call)
            except ValueError:
                errors.append(ToolError.TOOL_SYNTAX_MISMATCH)
            except KeyError:
                errors.append(ToolError.TOOL_ARGUMENTS_MISMATCH)
            except Exception:
                errors.append(ToolError.TOOL_SYNTAX_MISMATCH)
                
        # Append remaining text
        cleaned_response += response_str[last_pos:]
        
        return cleaned_response.strip(), tool_calls, errors

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
            try:
                return int(s)
            except ValueError:
                try:
                    return float(s)
                except ValueError:
                    if s.lower() in ("true", "false"):
                        return s.lower() == "true"
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
                raise ValueError(f"Duplicate argument '{tag}'")
            seen_tags.add(tag)
            
            cleaned = parse_value(unescape_xml(content))
            result["arguments"][tag] = cleaned

        return result
