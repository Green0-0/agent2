from agent2.agent.agent_state import AgentState
from agent2.agent.agent_depreciated import AgentResponse
from agent2.utils.utils import extract_all_code_blocks

def extract_code_block(agentResponse : AgentResponse, agentState : AgentState):
    agentResponse.done = extract_all_code_blocks(agentResponse.done)[0]

from typing import List
from agent2.parsing.parser import reindent, unenumerate_lines, extract_codeblock

def apply_code_edits_workplace(agentResponse: AgentResponse, agentState: AgentState):
    warning = False
    code_source = agentResponse.done
    if "</think>" in agentResponse.done:
        code_source = agentResponse.done.split("</think>")[1]
    code_blocks = extract_all_code_blocks(code_source)
    for code_block in code_blocks:
        print("Found:")
        print(code_block[0:100])
        lines = code_block.split('\n')
        if not lines or not lines[0].startswith('#'):
            print("Missing comment")
            warning = True
            continue
        
        header_line = lines[0][1:].strip()
        if ':' in header_line:
            file_path, element_id = header_line.split(':', 1)
            file_path = file_path.strip()
            element_id = element_id.strip()
        else:
            file_path = None
            element_id = header_line.strip()
        
        target_file = None
        target_element = None
        
        # Find target file and element
        if file_path:
            # Look for the file by path
            target_file = next((f for f in agentState.workspace if f.path == file_path), None)
            if not target_file:
                warning = True
                continue
            
            # Flatten all elements in file
            all_elements = []
            stack = list(target_file.elements)
            while stack:
                el = stack.pop()
                all_elements.append(el)
                stack.extend(el.elements)
            
            # Find matching element
            matching_elements = [el for el in all_elements if el.identifier == element_id]
            if len(matching_elements) != 1:
                warning = True
                continue
            target_element = matching_elements[0]
        else:
            # Search all files for element
            candidates = []
            for file in agentState.workspace:
                all_elements = []
                stack = list(file.elements)
                while stack:
                    el = stack.pop()
                    all_elements.append(el)
                    stack.extend(el.elements)
                for el in all_elements:
                    if el.identifier == element_id:
                        candidates.append((file, el))
            
            if len(candidates) != 1:
                warning = True
                continue
            target_file, target_element = candidates[0]
        
        if not target_element:
            warning = True
            print("No element found")
            continue
        
        # Process new content
        new_content_raw = '\n'.join(lines[1:])
        new_content_clean = extract_codeblock(new_content_raw)
        unenumerated = unenumerate_lines(new_content_clean)
        
        # Use cleaned code if majority had line numbers
        if unenumerated[0] > 0.6 * len(unenumerated[1]):
            new_content_clean = unenumerated[2]
        else:
            new_content_clean = unenumerated[2]
        
        # Reindent to match original element indentation
        original_content = target_element.content
        new_content_reindented = reindent(original_content, new_content_clean)
        if original_content == new_content_reindented:
            print("Equal...")
            continue
        
        # Calculate line range to replace
        line_start = target_element.line_start
        original_lines = original_content.split('\n')
        line_end = line_start + len(original_lines)
        
        # Apply update
        file_content_lines = target_file.content.split('\n')
        if line_start >= len(file_content_lines) or line_end > len(file_content_lines):
            warning = True
            print("WEIRD FAILURE")
            continue
        
        target_file.content = '\n'.join(
            file_content_lines[:line_start] +
            new_content_reindented.split('\n') +
            file_content_lines[line_end:]
        )
        print("update content")
        target_file.update_elements()
    
    return warning