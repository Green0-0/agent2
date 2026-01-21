from typing import List, Dict, Tuple
import re
import ast
from agent2.tool_api.abc.tool_call_extractor import ToolCallExtractor, ToolError, DuplicateArgumentError

class FakeCodeActToolCallExtractor(ToolCallExtractor):
    """
    Extracts tool calls from a fake CodeAct format where tool calls are python function calls
    inside <code> tags.
    """
    def __init__(self, tool_start: str = "<code>", tool_end: str = "</code>"):
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
        has_start = self.tool_start in response_str
        has_end = self.tool_end in response_str
        
        if has_start and not has_end:
            return response_str, [], [ToolError.TOOL_END_MISSING]
        if has_end and not has_start:
            return response_str, [], [ToolError.TOOL_START_MISSING]

        # Find the first code block
        start_idx = response_str.find(self.tool_start)
        if start_idx == -1:
            return response_str, [], []
            
        end_idx = response_str.find(self.tool_end, start_idx)
        
        if end_idx == -1:
            return response_str, [], [ToolError.TOOL_END_MISSING]
        
        # The message is everything before the first tool call
        cleaned_response = response_str[:start_idx].strip()
        
        # Extract content inside tags
        content = response_str[start_idx + len(self.tool_start):end_idx].strip()
        
        # Handle optional markdown code block wrapper
        # Check if the content starts with a markdown block
        # We split by lines first to handle the markdown wrapper correctly
        lines = content.split('\n')
        
        if not lines:
            return cleaned_response, [], []

        # Handle optional markdown code block wrapper
        if lines[0].strip().startswith("```"):
            lines.pop(0)
            # If we popped the start, we should check for the end
            if lines:
                last_line = lines[-1].strip()
                if last_line.startswith("```"):
                    lines.pop()
                elif last_line.endswith("```"):
                    # Handle case where ``` is at the end of the code line
                    lines[-1] = lines[-1].rstrip()[:-3]
            
        tool_calls = []
        errors = []
        
        for line in lines:
            line_content = line.strip()
            if not line_content:
                continue
            
            try:
                # Parse the line as python code
                tree = ast.parse(line_content)
                
                # We expect a single expression which is a Call
                if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
                    # Not an expression (e.g. assignment, import, etc)
                    return response_str, [], [ToolError.TOOL_MALFORMATTED]
                
                expr = tree.body[0].value
                if not isinstance(expr, ast.Call):
                    # Not a function call
                    return response_str, [], [ToolError.TOOL_MALFORMATTED]
                
                # Extract function name
                if isinstance(expr.func, ast.Name):
                    func_name = expr.func.id
                elif isinstance(expr.func, ast.Attribute):
                    # Handle obj.method() if necessary
                    parts = []
                    curr = expr.func
                    while isinstance(curr, ast.Attribute):
                        parts.append(curr.attr)
                        curr = curr.value
                    if isinstance(curr, ast.Name):
                        parts.append(curr.id)
                    func_name = ".".join(reversed(parts))
                else:
                    return response_str, [], [ToolError.TOOL_MALFORMATTED]
                
                # Extract arguments
                arguments = {}
                
                if expr.args:
                    # Positional arguments are not supported in this fake parser
                    return response_str, [], [ToolError.TOOL_MALFORMATTED]

                for keyword in expr.keywords:
                    arg_name = keyword.arg
                    # Evaluate the value
                    try:
                        arg_value = ast.literal_eval(keyword.value)
                        arguments[arg_name] = arg_value
                    except ValueError:
                        # Non-literal argument
                        return response_str, [], [ToolError.TOOL_MALFORMATTED]

                tool_calls.append({
                    "name": func_name,
                    "arguments": arguments,
                    "id": f"call_{func_name}_{len(tool_calls)}"
                })

            except SyntaxError:
                return response_str, [], [ToolError.TOOL_MALFORMATTED]
            except Exception:
                return response_str, [], [ToolError.TOOL_MALFORMATTED]
                
        return cleaned_response, tool_calls, errors
