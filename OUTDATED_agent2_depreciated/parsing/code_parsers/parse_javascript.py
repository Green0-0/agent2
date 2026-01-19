from typing import List

from agent2.agent_rework.element import Element


def parse_javascript_elements(code: str) -> List[Element]:
    from tree_sitter import Node
    from tree_sitter_languages import get_language, get_parser
    
    parser = get_parser('javascript')
    code_bytes = code.encode('utf8')
    tree = parser.parse(code_bytes)
    root_node = tree.root_node
    
    lines = code.split('\n')
    
    def get_node_text(node: Node) -> str:
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')
    
    def get_line_number(node: Node) -> int:
        return node.start_point[0]  # 0-indexed
    
    def get_end_line_number(node: Node) -> int:
        return node.end_point[0]  # 0-indexed
    
    def extract_jsdoc(node: Node) -> str:
        """Extract JSDoc comment preceding the node."""
        current = node
        while current.prev_sibling:
            prev = current.prev_sibling
            if prev.type == 'comment':
                comment_text = get_node_text(prev)
                if comment_text.startswith('/**') and comment_text.endswith('*/'):
                    content = comment_text[3:-2]
                    cleaned_lines = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line.startswith('*'):
                            line = line[1:].strip()
                        cleaned_lines.append(line)
                    return '\n'.join(cleaned_lines).strip()
            elif prev.type not in ['comment']:
                break
            current = prev
        return ""
    
    def get_element_name(node: Node) -> str:
        """Get the name of a function, class, or method."""
        if node.type in ['function_declaration', 'async_function_declaration', 'generator_function_declaration']:
            name_node = node.child_by_field_name('name')
            return get_node_text(name_node) if name_node else "anonymous"
            
        elif node.type == 'class_declaration':
            name_node = node.child_by_field_name('name')
            return get_node_text(name_node) if name_node else "anonymous"
            
        elif node.type == 'method_definition':
            # Try different possible field names and child types
            key_node = node.child_by_field_name('key')
            if key_node:
                return get_node_text(key_node)
            
            # Fallback: look for identifier or property_identifier children
            for child in node.children:
                if child.type in ['identifier', 'property_identifier', 'string']:
                    text = get_node_text(child)
                    if child.type == 'string':
                        return text.strip('\'"')
                    return text
            
            return "anonymous"
            
        elif node.type == 'export_statement':
            # Handle different export patterns
            declaration = node.child_by_field_name('declaration')
            if declaration:
                if declaration.type in ['function_declaration', 'class_declaration']:
                    inner_name = get_element_name(declaration)
                    return f"export_{inner_name}"
                elif declaration.type == 'function_expression':
                    return "export_default_function"
                elif declaration.type == 'variable_declaration':
                    # Handle export const/let/var
                    for child in declaration.children:
                        if child.type == 'variable_declarator':
                            name_node = child.child_by_field_name('name')
                            if name_node:
                                var_name = get_node_text(name_node)
                                return f"export_{var_name}"
            
            # Handle export { ... }
            for child in node.children:
                if child.type == 'export_clause':
                    return "export_clause"
            
            # Handle export default function() without name
            text = get_node_text(node)
            if 'export default function' in text:
                return "export_default_function"
            
            return "export_statement"
            
        elif node.type == 'variable_declaration':
            # Handle const/let/var function assignments
            for child in node.children:
                if child.type == 'variable_declarator':
                    name_node = child.child_by_field_name('name')
                    if name_node:
                        return get_node_text(name_node)
            return "variable"
            
        return "unknown"
    
    def get_element_header(node: Node) -> str:
        """Get the declaration header without the body."""
        text = get_node_text(node)
        
        # For functions, classes, and methods, get everything up to the opening brace
        if '{' in text:
            header = text[:text.index('{')].strip()
            # Remove newlines and extra whitespace
            header = ' '.join(header.split())
            return header
        
        # For variable declarations and other statements, take the whole line until semicolon
        if ';' in text:
            header = text[:text.index(';') + 1].strip()
            return ' '.join(header.split())
        
        # For arrow functions and other expressions, take until =>
        if '=>' in text:
            header = text[:text.index('=>') + 2].strip()
            return ' '.join(header.split())
        
        # Fallback: just the first line
        return text.split('\n')[0].strip()
    
    def is_element_node(node: Node) -> bool:
        """Check if node represents a parseable element."""
        if node.type in [
            'function_declaration',
            'class_declaration', 
            'method_definition',
            'async_function_declaration',
            'generator_function_declaration',
            'export_statement'
        ]:
            return True
        
        # Check for variable declarations that contain functions
        if node.type == 'variable_declaration':
            for child in node.children:
                if child.type == 'variable_declarator':
                    init_node = child.child_by_field_name('init')
                    if init_node and init_node.type in ['function_expression', 'arrow_function']:
                        return True
        
        return False
    
    def find_decorators(node: Node) -> int:
        """Find decorators (or similar constructs) before a node and return the starting line."""
        start_line = get_line_number(node)
        
        # Look for preceding comment nodes that might be decorators
        current = node
        while current.prev_sibling:
            prev = current.prev_sibling
            if prev.type == 'comment' and get_node_text(prev).strip().startswith('@'):
                start_line = get_line_number(prev)
            else:
                break
            current = prev
        
        return start_line
    
    def get_actual_element_node(node: Node) -> Node:
        """Get the actual element node, handling exports and variable declarations."""
        if node.type == 'export_statement':
            declaration = node.child_by_field_name('declaration')
            if declaration and declaration.type in ['function_declaration', 'class_declaration']:
                return declaration
        elif node.type == 'variable_declaration':
            for child in node.children:
                if child.type == 'variable_declarator':
                    init_node = child.child_by_field_name('init')
                    if init_node and init_node.type in ['function_expression', 'arrow_function']:
                        return node  # Return the variable declaration itself
        
        return node
    
    def parse_element(node: Node, parent_identifier: str = "") -> Element:
        """Parse a single element and its children."""
        name = get_element_name(node)
        identifier = f"{parent_identifier}.{name}" if parent_identifier else name
        header = get_element_header(node)
        content = get_node_text(node)
        description = extract_jsdoc(node)
        line_start = find_decorators(node)
        
        element = Element(
            identifier=identifier,
            header=header,
            content=content,
            description=description,
            line_start=line_start
        )
        
        # Find child elements - use the actual element node for traversal
        actual_node = get_actual_element_node(node)
        child_elements = []
        
        if actual_node.type == 'class_declaration':
            # Look for methods in class body
            class_body = actual_node.child_by_field_name('body')
            if class_body:
                for child in class_body.children:
                    if is_element_node(child):
                        child_element = parse_element(child, identifier)
                        child_elements.append(child_element)
        else:
            # For functions and other elements, look for nested function declarations
            def find_nested_elements(n: Node):
                for child in n.children:
                    if is_element_node(child):
                        child_element = parse_element(child, identifier)
                        child_elements.append(child_element)
                    elif child.type in ['statement_block', 'function_body', 'class_body']:
                        # Continue searching in bodies
                        find_nested_elements(child)
                    elif child.type not in ['identifier', 'formal_parameters', 'type_annotation']:
                        # Continue searching in other containers, but skip simple leaf nodes
                        find_nested_elements(child)
            
            find_nested_elements(actual_node)
        
        # Handle top-level blocks if there are child elements
        if child_elements:
            top_level_blocks = create_top_level_blocks(actual_node, child_elements, identifier)
            child_elements.extend(top_level_blocks)
        
        element.elements = child_elements
        return element
    
    def create_top_level_blocks(parent_node: Node, child_elements: List[Element], parent_identifier: str) -> List[Element]:
        """Create top-level block elements for code between child elements."""
        if not child_elements:
            return []
            
        blocks = []
        parent_content = get_node_text(parent_node)
        parent_lines = parent_content.split('\n')
        parent_start_line = get_line_number(parent_node)
        
        # Sort child elements by line start
        sorted_children = sorted(child_elements, key=lambda e: e.line_start)
        
        # Determine which lines are covered by child elements
        covered_lines = set()
        for child in sorted_children:
            child_start_relative = child.line_start - parent_start_line
            child_end_relative = child_start_relative + child.content.count('\n')
            for line_num in range(child_start_relative, child_end_relative + 1):
                if 0 <= line_num < len(parent_lines):
                    covered_lines.add(line_num)
        
        # Find the actual content boundaries
        content_start = 0
        content_end = len(parent_lines) - 1
        
        # Skip opening line with declaration and find opening brace
        for i, line in enumerate(parent_lines):
            if '{' in line:
                content_start = i + 1
                break
        
        # Skip closing brace
        for i in range(len(parent_lines) - 1, -1, -1):
            if parent_lines[i].strip() == '}':
                content_end = i - 1
                break
        
        # Group uncovered lines into meaningful blocks
        current_block_lines = []
        current_block_start = None
        block_count = 0
        
        for i in range(content_start, content_end + 1):
            if i >= len(parent_lines):
                break
                
            line = parent_lines[i]
            line_stripped = line.strip()
            
            if i not in covered_lines:
                if line_stripped:  # Only add non-empty lines
                    if current_block_start is None:
                        current_block_start = i
                    current_block_lines.append(line)
                elif current_block_lines:  # Add empty lines within blocks
                    current_block_lines.append(line)
            else:
                # Hit a covered line, create block if we have content
                if current_block_lines and any(line.strip() for line in current_block_lines):
                    # Remove trailing empty lines
                    while current_block_lines and not current_block_lines[-1].strip():
                        current_block_lines.pop()
                    
                    if current_block_lines:
                        block_content = '\n'.join(current_block_lines)
                        block_identifier = f"{parent_identifier}.top_level_block_{block_count}"
                        
                        # Check for naming conflicts
                        existing_names = {elem.identifier.split('.')[-1] for elem in child_elements}
                        while block_identifier.split('.')[-1] in existing_names:
                            block_identifier = f"{parent_identifier}._top_level_block_{block_count}"
                        
                        block_element = Element(
                            identifier=block_identifier,
                            header="",
                            content=block_content,
                            description="",
                            line_start=parent_start_line + current_block_start
                        )
                        blocks.append(block_element)
                        block_count += 1
                
                current_block_lines = []
                current_block_start = None
        
        # Handle final block
        if current_block_lines and any(line.strip() for line in current_block_lines):
            # Remove trailing empty lines
            while current_block_lines and not current_block_lines[-1].strip():
                current_block_lines.pop()
            
            if current_block_lines:
                block_content = '\n'.join(current_block_lines)
                block_identifier = f"{parent_identifier}.top_level_block_{block_count}"
                
                existing_names = {elem.identifier.split('.')[-1] for elem in child_elements}
                while block_identifier.split('.')[-1] in existing_names:
                    block_identifier = f"{parent_identifier}._top_level_block_{block_count}"
                
                block_element = Element(
                    identifier=block_identifier,
                    header="",
                    content=block_content,
                    description="",
                    line_start=parent_start_line + current_block_start
                )
                blocks.append(block_element)
        
        return blocks
    
    # Parse all top-level elements
    elements = []
    
    for child in root_node.children:
        if is_element_node(child):
            element = parse_element(child)
            elements.append(element)
    
    # Create file-level top-level blocks
    if elements:
        # Sort elements by line start
        sorted_elements = sorted(elements, key=lambda e: e.line_start)
        
        # Determine which lines are covered by elements
        covered_lines = set()
        for element in sorted_elements:
            element_start = element.line_start
            element_end = element_start + element.content.count('\n')
            for line_num in range(element_start, element_end + 1):
                covered_lines.add(line_num)
        
        # Group uncovered lines into file-level blocks
        current_block_lines = []
        current_block_start = None
        block_count = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if i not in covered_lines:
                if line_stripped:  # Only add non-empty lines
                    if current_block_start is None:
                        current_block_start = i
                    current_block_lines.append(line)
                elif current_block_lines:  # Add empty lines within blocks
                    current_block_lines.append(line)
            else:
                # Hit a covered line, create block if we have content
                if current_block_lines and any(line.strip() for line in current_block_lines):
                    # Remove trailing empty lines
                    while current_block_lines and not current_block_lines[-1].strip():
                        current_block_lines.pop()
                    
                    if current_block_lines:
                        block_content = '\n'.join(current_block_lines)
                        block_identifier = f"top_level_block_{block_count}"
                        
                        # Check for naming conflicts
                        existing_names = {elem.identifier for elem in elements}
                        while block_identifier in existing_names:
                            block_identifier = f"_top_level_block_{block_count}"
                        
                        block_element = Element(
                            identifier=block_identifier,
                            header=current_block_lines[0].strip() if current_block_lines else "",
                            content=block_content,
                            description="",
                            line_start=current_block_start
                        )
                        elements.append(block_element)
                        block_count += 1
                
                current_block_lines = []
                current_block_start = None
        
        # Handle final file-level block
        if current_block_lines and any(line.strip() for line in current_block_lines):
            # Remove trailing empty lines
            while current_block_lines and not current_block_lines[-1].strip():
                current_block_lines.pop()
            
            if current_block_lines:
                block_content = '\n'.join(current_block_lines)
                block_identifier = f"top_level_block_{block_count}"
                
                existing_names = {elem.identifier for elem in elements}
                while block_identifier in existing_names:
                    block_identifier = f"_top_level_block_{block_count}"
                
                block_element = Element(
                    identifier=block_identifier,
                    header=current_block_lines[0].strip() if current_block_lines else "",
                    content=block_content,
                    description="",
                    line_start=current_block_start
                )
                elements.append(block_element)
    
    return elements
