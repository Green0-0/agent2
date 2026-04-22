from typing import List
from tree_sitter import Node
from agent2.agent_rework.element import Element

def parse_csharp_elements(code: str) -> List[Element]:
    from tree_sitter_languages import get_language, get_parser
    
    parser = get_parser('c_sharp')
    code_bytes = code.encode('utf8')
    tree = parser.parse(code_bytes)
    root_node = tree.root_node
    
    def get_node_text(node: Node) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')
    
    def is_element_node(node: Node) -> bool:
        return node.type in [
            'class_declaration',
            'interface_declaration', 
            'struct_declaration',
            'enum_declaration',
            'method_declaration',
            'constructor_declaration',
            'property_declaration',
            'field_declaration',
            'delegate_declaration',
            'namespace_declaration',
            'local_function_statement'
        ]
    
    def get_identifier_from_node(node: Node, parent_identifier: str = "") -> str:
        name = "unknown"
        
        if node.type == 'namespace_declaration':
            # Find the namespace name
            for child in node.children:
                if child.type == 'qualified_name' or child.type == 'identifier':
                    name = get_node_text(child)
                    break
        elif node.type == 'field_declaration':
            # For field declarations, look for variable_declaration -> variable_declarator -> identifier
            for child in node.children:
                if child.type == 'variable_declaration':
                    for grandchild in child.children:
                        if grandchild.type == 'variable_declarator':
                            for ggchild in grandchild.children:
                                if ggchild.type == 'identifier':
                                    name = get_node_text(ggchild)
                                    break
                            if name != "unknown":
                                break
                    if name != "unknown":
                        break
        elif node.type in ['method_declaration', 'constructor_declaration', 'local_function_statement']:
            # For methods, we need to find the method name identifier (not return type)
            # The method name typically comes after the return type but before parameter_list
            identifiers = []
            parameter_list_found = False
            
            for child in node.children:
                if child.type == 'parameter_list':
                    parameter_list_found = True
                    break
                elif child.type == 'identifier':
                    identifiers.append(get_node_text(child))
            
            if identifiers:
                # The method name is typically the last identifier before parameter_list
                name = identifiers[-1]
        else:
            # Find the identifier child for other types
            for child in node.children:
                if child.type == 'identifier':
                    name = get_node_text(child)
                    break
        
        if parent_identifier:
            return f"{parent_identifier}.{name}"
        return name
    
    def get_header_from_node(node: Node) -> str:
        full_text = get_node_text(node)
        lines = full_text.split('\n')
        
        # For namespace, get the namespace declaration line
        if node.type == 'namespace_declaration':
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('namespace'):
                    return stripped.split('{')[0].strip()
        
        # For other elements, skip attributes and find declaration
        for line in lines:
            stripped = line.strip()
            if (stripped and 
                not stripped.startswith('[') and  # Skip attributes
                not stripped.startswith('//') and  # Skip comments
                not stripped.startswith('/*') and
                not stripped.startswith('///') and
                not stripped == '{' and
                not stripped == '}'):
                # Remove opening brace if present
                if '{' in stripped:
                    stripped = stripped[:stripped.index('{')].strip()
                return stripped
        
        return lines[0].strip() if lines else ""
    
    def get_description_from_node(node: Node) -> str:
        # Look for XML documentation comments preceding the node
        parent = node.parent
        if not parent:
            return ""
        
        # Find this node's position in parent's children
        node_index = -1
        for i, child in enumerate(parent.children):
            if child == node:
                node_index = i
                break
        
        if node_index <= 0:
            return ""
        
        # Look backwards for comment nodes
        doc_parts = []
        for i in range(node_index - 1, -1, -1):
            child = parent.children[i]
            if child.type == 'comment':
                comment_text = get_node_text(child)
                if '///' in comment_text:
                    # Extract XML doc content
                    lines = comment_text.split('\n')
                    for line in reversed(lines):  # Process in reverse to maintain order
                        if '///' in line:
                            content = line.split('///', 1)[1].strip()
                            if content:
                                doc_parts.insert(0, content)
                else:
                    break  # Stop at non-XML doc comment
            elif child.type not in ['comment', 'preproc_line']:
                break
        
        return ' '.join(doc_parts) if doc_parts else ""
    
    def get_line_start_with_attributes(node: Node) -> int:
        line_start = node.start_point[0]
        
        # Look for preceding attribute_list nodes
        parent = node.parent
        if parent:
            node_index = -1
            for i, child in enumerate(parent.children):
                if child == node:
                    node_index = i
                    break
            
            if node_index > 0:
                # Check previous siblings for attributes
                for i in range(node_index - 1, -1, -1):
                    child = parent.children[i]
                    if child.type == 'attribute_list':
                        line_start = min(line_start, child.start_point[0])
                    elif child.type not in ['comment', 'preproc_line']:
                        break
        
        return line_start
    
    def parse_element(node: Node, parent_identifier: str = "") -> Element:
        identifier = get_identifier_from_node(node, parent_identifier)
        header = get_header_from_node(node)
        content = get_node_text(node)
        description = get_description_from_node(node)
        line_start = get_line_start_with_attributes(node)
        
        element = Element(identifier, header, content, description, line_start)
        
        # Find direct child elements recursively
        child_elements = []
        find_child_elements(node, child_elements, identifier)
        
        # Create top-level blocks only if there are child elements and meaningful content
        if child_elements:
            top_level_blocks = create_top_level_blocks(
                node, child_elements, identifier
            )
            child_elements.extend(top_level_blocks)
        
        element.elements = child_elements
        return element
    
    def find_child_elements(node: Node, child_elements: List[Element], parent_identifier: str):
        """Recursively find all child elements within a node"""
        for child in node.children:
            if is_element_node(child):
                child_element = parse_element(child, parent_identifier)
                child_elements.append(child_element)
            else:
                # Recursively search in non-element nodes
                find_child_elements(child, child_elements, parent_identifier)
    
    def create_top_level_blocks(parent_node: Node, child_elements: List[Element], 
                              parent_identifier: str) -> List[Element]:
        blocks = []
        parent_content = get_node_text(parent_node)
        parent_lines = parent_content.split('\n')
        parent_start_line = parent_node.start_point[0]
        
        # Find which lines are covered by child elements (relative to parent)
        covered_lines = set()
        for child_elem in child_elements:
            # Calculate relative position within parent
            child_start_relative = child_elem.line_start - parent_start_line
            child_line_count = child_elem.content.count('\n') + 1
            for i in range(child_start_relative, child_start_relative + child_line_count):
                if 0 <= i < len(parent_lines):
                    covered_lines.add(i)
        
        # Find uncovered content blocks
        current_block_lines = []
        current_block_start = 0
        block_count = 0
        
        for i, line in enumerate(parent_lines):
            stripped = line.strip()
            
            if i not in covered_lines:
                # This line is not covered by any child element
                if (stripped and 
                    not stripped in ['{', '}'] and
                    not stripped.startswith('//') and
                    not stripped.startswith('/*') and
                    not stripped.startswith('///') and
                    not is_declaration_line(stripped)):
                    
                    if not current_block_lines:
                        current_block_start = i
                    current_block_lines.append(line)
            else:
                # This line is covered, end current block if exists
                if current_block_lines:
                    block = create_top_level_block(
                        current_block_lines, 
                        parent_start_line + current_block_start,
                        parent_identifier,
                        block_count,
                        child_elements
                    )
                    if block:
                        blocks.append(block)
                    current_block_lines = []
                    block_count += 1
        
        # Handle final block
        if current_block_lines:
            block = create_top_level_block(
                current_block_lines,
                parent_start_line + current_block_start,
                parent_identifier,
                block_count,
                child_elements
            )
            if block:
                blocks.append(block)
        
        return blocks
    
    def is_declaration_line(line: str) -> bool:
        """Check if a line is a declaration line that should be excluded from top-level blocks"""
        line = line.strip()
        declaration_keywords = [
            'namespace', 'class', 'interface', 'struct', 'enum', 
            'public class', 'private class', 'internal class', 'protected class',
            'public interface', 'private interface', 'internal interface',
            'public struct', 'private struct', 'internal struct',
            'public enum', 'private enum', 'internal enum',
            'public void', 'private void', 'internal void', 'protected void',
            'void ', 'public static', 'private static'
        ]
        return any(line.startswith(keyword) for keyword in declaration_keywords)
    
    def create_top_level_block(lines: List[str], line_start: int, 
                             parent_identifier: str, block_count: int,
                             existing_elements: List[Element]) -> Element:
        # Filter out empty lines and braces
        meaningful_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and stripped not in ['{', '}']:
                meaningful_lines.append(line)
        
        if not meaningful_lines:
            return None
        
        content = '\n'.join(meaningful_lines)
        header = meaningful_lines[0].strip()
        
        base_identifier = f"top_level_block_{block_count}"
        identifier = base_identifier
        
        existing_names = {elem.identifier.split('.')[-1] for elem in existing_elements}
        if base_identifier in existing_names:
            identifier = f"_top_level_block_{block_count}"
        
        full_identifier = f"{parent_identifier}.{identifier}" if parent_identifier else identifier
        
        return Element(full_identifier, header, content, "", line_start)
    
    # Parse all root-level elements
    root_elements = []
    find_child_elements(root_node, root_elements, "")
    
    # Create file-level top-level blocks if there are elements
    if root_elements:
        file_blocks = create_file_top_level_blocks(root_elements, code_bytes)
        root_elements.extend(file_blocks)
    
    return root_elements

def create_file_top_level_blocks(elements: List[Element], code_bytes: bytes) -> List[Element]:
    blocks = []
    # Get the full code text
    code_lines = code_bytes.decode('utf8').split('\n')
    
    # Find which lines are covered by elements
    covered_lines = set()
    for elem in elements:
        line_count = elem.content.count('\n') + 1
        for i in range(elem.line_start, elem.line_start + line_count):
            if 0 <= i < len(code_lines):
                covered_lines.add(i)
    
    # Find uncovered content blocks
    current_block_lines = []
    current_block_start = 0
    block_count = 0
    
    for i, line in enumerate(code_lines):
        stripped = line.strip()
        
        if i not in covered_lines:
            # Line not covered by any element
            if (stripped and 
                not stripped.startswith('//') and
                not stripped.startswith('/*') and
                not stripped.startswith('///') and
                stripped not in ['{', '}']):
                
                if not current_block_lines:
                    current_block_start = i
                current_block_lines.append(line)
        else:
            # Line is covered, end current block
            if current_block_lines:
                content = '\n'.join(current_block_lines)
                header = current_block_lines[0].strip()
                
                identifier = f"top_level_block_{block_count}"
                existing_names = {elem.identifier for elem in elements}
                if identifier in existing_names:
                    identifier = f"_top_level_block_{block_count}"
                
                block = Element(identifier, header, content, "", current_block_start)
                blocks.append(block)
                
                current_block_lines = []
                block_count += 1
    
    # Handle final block
    if current_block_lines:
        content = '\n'.join(current_block_lines)
        header = current_block_lines[0].strip()
        
        identifier = f"top_level_block_{block_count}"
        existing_names = {elem.identifier for elem in elements}
        if identifier in existing_names:
            identifier = f"_top_level_block_{block_count}"
        
        block = Element(identifier, header, content, "", current_block_start)
        blocks.append(block)
    
    return blocks
