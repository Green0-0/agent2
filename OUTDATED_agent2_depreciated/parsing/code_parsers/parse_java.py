from typing import List
from agent2.agent_rework.element import Element

def parse_java_elements(code: str) -> List[Element]:
    from tree_sitter import Node
    from tree_sitter_languages import get_language, get_parser
    
    parser = get_parser('java')
    code_bytes = code.encode('utf8')
    tree = parser.parse(code_bytes)
    root_node = tree.root_node
    
    language = get_language('java')
    
    def get_text(node: Node) -> str:
        """Extract text from a node"""
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')
    
    def find_javadoc_before(node: Node) -> Node:
        """Find Javadoc comment immediately before this node"""
        prev = node.prev_sibling
        while prev and prev.type in ['annotation', 'modifiers']:
            prev = prev.prev_sibling
        
        if prev and prev.type == 'block_comment':
            text = get_text(prev)
            if text.startswith('/**'):
                return prev
        return None
    
    def find_class_javadoc(class_node: Node) -> str:
        """Find Javadoc for a class, looking before any annotations"""
        # For classes, we need to look before the @CustomAnnotation
        current = class_node.prev_sibling
        javadoc_text = ""
        
        # Skip backwards through annotations and modifiers to find Javadoc
        while current:
            if current.type == 'annotation':
                current = current.prev_sibling
                continue
            elif current.type == 'block_comment':
                text = get_text(current)
                if text.startswith('/**'):
                    # This is Javadoc - extract and clean it
                    content = text[3:-2].strip()
                    lines = content.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        cleaned = line.strip().lstrip('*').strip()
                        if cleaned:
                            cleaned_lines.append(cleaned)
                    javadoc_text = ' '.join(cleaned_lines)
                break
            else:
                break
            
        return javadoc_text
    
    def find_start_with_annotations(node: Node) -> Node:
        """Find the starting node including any annotations/modifiers before it"""
        start_node = node
        
        # For classes, include class-level Javadoc and annotations
        if node.type in ['class_declaration', 'interface_declaration', 'enum_declaration']:
            prev = node.prev_sibling
            while prev and prev.type in ['annotation', 'modifiers']:
                start_node = prev
                prev = prev.prev_sibling
            
            # Include class Javadoc
            if prev and prev.type == 'block_comment':
                text = get_text(prev)
                if text.startswith('/**'):
                    start_node = prev
        else:
            # For other elements, don't include Javadoc that might belong to parent
            prev = node.prev_sibling
            while prev and prev.type in ['annotation', 'modifiers']:
                start_node = prev
                prev = prev.prev_sibling
            
            # Only include Javadoc if it's immediately before (not separated by other content)
            if prev and prev.type == 'block_comment':
                text = get_text(prev)
                if text.startswith('/**'):
                    # Check if this Javadoc is immediately before this element
                    prev_line = prev.end_point[0]
                    current_line = start_node.start_point[0]
                    if current_line - prev_line <= 1:  # Adjacent or on next line
                        start_node = prev
                
        return start_node
    
    def extract_javadoc(node: Node) -> str:
        """Extract Javadoc comment before this node"""
        if node.type in ['class_declaration', 'interface_declaration', 'enum_declaration']:
            return find_class_javadoc(node)
        
        javadoc_node = find_javadoc_before(node)
        if javadoc_node:
            text = get_text(javadoc_node)
            if text.startswith('/**'):
                # Clean up Javadoc: remove /** */, trim whitespace and asterisks
                content = text[3:-2].strip()
                lines = content.split('\n')
                cleaned_lines = []
                for line in lines:
                    # Remove leading whitespace and asterisks
                    cleaned = line.strip().lstrip('*').strip()
                    if cleaned:
                        cleaned_lines.append(cleaned)
                return ' '.join(cleaned_lines)
        return ""
    
    def get_element_name(node: Node) -> str:
        """Get the name of an element"""
        if node.type == 'static_initializer':
            return "static_block"
        
        name_node = node.child_by_field_name('name')
        if name_node:
            return get_text(name_node)
        return ""
    
    def get_clean_header(node: Node) -> str:
        """Get the declaration header without annotations and opening braces"""
        text = get_text(node)
        
        # Special handling for static blocks
        if node.type == 'static_initializer':
            return "static"
        
        lines = text.split('\n')
        
        # Find lines that form the declaration (skip annotations)
        declaration_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith('@'):
                continue  # Skip annotations
            if stripped == '{' or stripped.endswith('{'):
                # Remove opening brace and add to declaration
                clean_line = stripped.rstrip('{').strip()
                if clean_line:
                    declaration_lines.append(clean_line)
                break
            else:
                declaration_lines.append(stripped)
        
        # Join and clean up
        header = ' '.join(declaration_lines)
        return ' '.join(header.split())  # Normalize whitespace
    
    def get_lines_between(start_line: int, end_line: int) -> str:
        """Extract lines between start_line and end_line (inclusive, 0-indexed)"""
        lines = code.split('\n')
        if start_line < 0 or end_line >= len(lines) or start_line > end_line:
            return ""
        return '\n'.join(lines[start_line:end_line + 1])
    
    def get_first_non_empty_line(content: str) -> str:
        """Get the first non-empty line from content"""
        lines = content.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped:
                return stripped
        return "// Top level block"
    
    def is_significant_content(content: str) -> bool:
        """Check if content is significant enough to warrant a top-level block"""
        stripped_content = content.strip()
        
        # Any non-empty content is significant (including comments, field declarations, etc.)
        return bool(stripped_content)
    
    def has_following_element(body_node: Node, current_end_line: int) -> bool:
        """Check if there's an element after the current position"""
        element_types = {
            'class_declaration', 'interface_declaration', 'method_declaration',
            'constructor_declaration', 'enum_declaration', 'annotation_type_declaration',
            'record_declaration', 'static_initializer'
        }
        
        for child in body_node.children:
            if child.type in element_types and child.start_point[0] > current_end_line:
                return True
        return False
    
    def content_is_only_javadoc_for_following(content: str, body_node: Node, current_end_line: int) -> bool:
        """Check if content is only Javadoc that belongs to the next element"""
        if not has_following_element(body_node, current_end_line):
            return False
            
        lines = content.strip().split('\n')
        has_non_javadoc_content = False
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            # Allow only Javadoc patterns (/** */ style), not regular comments
            if (stripped.startswith('/**') or 
                (stripped.startswith('*') and not stripped.startswith('*/')) or 
                stripped == '*/'):
                continue
            else:
                has_non_javadoc_content = True
                break
        
        return not has_non_javadoc_content
    
    def parse_element(node: Node, parent_identifier: str = "") -> Element:
        """Parse a single element node into an Element object"""
        element_name = get_element_name(node)
        if not element_name:
            return None
        
        # Build full identifier
        if parent_identifier:
            identifier = f"{parent_identifier}.{element_name}"
        else:
            identifier = element_name
        
        # Find start position including annotations and Javadoc
        start_node = find_start_with_annotations(node)
        line_start = start_node.start_point[0]  # 0-indexed
        
        # Get header (declaration line)
        header = get_clean_header(node)
        
        # Get full content including annotations
        content = get_text_from_to(start_node, node)
        
        # Get Javadoc description
        description = extract_javadoc(node)
        
        # Parse child elements and top-level blocks
        child_elements = []
        
        # Element types that can contain other elements
        container_types = {
            'class_declaration', 'interface_declaration', 'enum_declaration', 
            'annotation_type_declaration', 'record_declaration', 'method_declaration',
            'constructor_declaration', 'static_initializer'
        }
        
        if node.type in container_types:
            if node.type in ['method_declaration', 'constructor_declaration', 'static_initializer']:
                # Methods/constructors can contain local classes
                child_elements = parse_method_body(node, identifier)
            else:
                # Classes/interfaces/enums/records have a body field
                body = node.child_by_field_name('body')
                if body:
                    child_elements = parse_body_elements(body, identifier)
        
        return Element(
            identifier=identifier,
            header=header,
            content=content,
            description=description,
            line_start=line_start,
            elements=child_elements
        )
    
    def get_text_from_to(start_node: Node, end_node: Node) -> str:
        """Get text from start_node to end_node"""
        return code_bytes[start_node.start_byte:end_node.end_byte].decode('utf8')
    
    def parse_method_body(method_node: Node, parent_identifier: str) -> List[Element]:
        """Parse elements within a method body (like local classes)"""
        elements = []
        
        def find_local_classes(node: Node):
            """Recursively find local class declarations"""
            if node.type == 'class_declaration':
                element = parse_element(node, parent_identifier)
                if element:
                    elements.append(element)
            
            for child in node.children:
                find_local_classes(child)
        
        find_local_classes(method_node)
        return elements
    
    def parse_body_elements(body_node: Node, parent_identifier: str) -> List[Element]:
        """Parse elements within a class/interface/enum body"""
        elements = []
        top_level_blocks = []
        
        element_types = {
            'class_declaration', 'interface_declaration', 'method_declaration',
            'constructor_declaration', 'enum_declaration', 'annotation_type_declaration',
            'record_declaration', 'static_initializer'
        }
        
        # Collect all element children
        element_children = []
        for child in body_node.children:
            if child.type in element_types:
                element_children.append(child)
        
        # Process elements and find top-level blocks between them
        last_end_line = body_node.start_point[0]
        top_level_counter = 0
        
        for i, child in enumerate(element_children):
            # Check for content between last position and current element
            child_start_line = find_start_with_annotations(child).start_point[0]
            
            if child_start_line > last_end_line + 1:
                # There's content between - check if it's significant and not just Javadoc
                block_content = get_lines_between(last_end_line + 1, child_start_line - 1)
                if (block_content.strip() and 
                    is_significant_content(block_content) and
                    not content_is_only_javadoc_for_following(block_content, body_node, last_end_line)):
                    # There's significant content - create top-level block
                    block_name = f"top_level_block_{top_level_counter}"
                    # Check for naming conflicts
                    existing_names = {e.identifier.split('.')[-1] for e in elements}
                    while block_name in existing_names:
                        block_name = f"_top_level_block_{top_level_counter}"
                    
                    block_identifier = f"{parent_identifier}.{block_name}"
                    # Use the first non-empty line as the header
                    block_header = get_first_non_empty_line(block_content)
                    
                    top_level_block = Element(
                        identifier=block_identifier,
                        header=block_header,
                        content=block_content,
                        description="",
                        line_start=last_end_line + 1,
                        elements=[]
                    )
                    top_level_blocks.append(top_level_block)
                    top_level_counter += 1
            
            # Parse the actual element
            element = parse_element(child, parent_identifier)
            if element:
                elements.append(element)
            
            last_end_line = child.end_point[0]
        
        # Check for content after the last element
        body_end_line = body_node.end_point[0] - 1  # Exclude closing brace
        if body_end_line > last_end_line:
            block_content = get_lines_between(last_end_line + 1, body_end_line)
            if (block_content.strip() and 
                is_significant_content(block_content) and
                not content_is_only_javadoc_for_following(block_content, body_node, last_end_line)):
                block_name = f"top_level_block_{top_level_counter}"
                existing_names = {e.identifier.split('.')[-1] for e in elements}
                while block_name in existing_names:
                    block_name = f"_top_level_block_{top_level_counter}"
                
                block_identifier = f"{parent_identifier}.{block_name}"
                # Use the first non-empty line as the header
                block_header = get_first_non_empty_line(block_content)
                
                top_level_block = Element(
                    identifier=block_identifier,
                    header=block_header,
                    content=block_content,
                    description="",
                    line_start=last_end_line + 1,
                    elements=[]
                )
                top_level_blocks.append(top_level_block)
        
        # Combine elements and top-level blocks, but only add top-level blocks if there are other elements
        result = elements[:]
        if elements and top_level_blocks:
            result.extend(top_level_blocks)
        
        return result
    
    # Parse root-level elements
    root_elements = []
    element_types = {
        'class_declaration', 'interface_declaration', 'method_declaration',
        'constructor_declaration', 'enum_declaration', 'annotation_type_declaration',
        'record_declaration'
    }
    
    # Find all top-level elements
    top_level_element_nodes = []
    for child in root_node.children:
        if child.type in element_types:
            top_level_element_nodes.append(child)
    
    # Process root-level elements and top-level blocks
    last_end_line = -1
    top_level_counter = 0
    
    for child in top_level_element_nodes:
        # Check for content before this element
        child_start_line = find_start_with_annotations(child).start_point[0]
        
        if child_start_line > last_end_line + 1:
            # There's content between
            block_content = get_lines_between(last_end_line + 1, child_start_line - 1)
            if block_content.strip() and is_significant_content(block_content):
                # There's significant content - create top-level block
                block_name = f"top_level_block_{top_level_counter}"
                existing_names = {e.identifier for e in root_elements}
                while block_name in existing_names:
                    block_name = f"_top_level_block_{top_level_counter}"
                
                # Use the first non-empty line as the header
                block_header = get_first_non_empty_line(block_content)
                
                top_level_block = Element(
                    identifier=block_name,
                    header=block_header,
                    content=block_content,
                    description="",
                    line_start=last_end_line + 1,
                    elements=[]
                )
                root_elements.append(top_level_block)
                top_level_counter += 1
        
        # Parse the actual element
        element = parse_element(child)
        if element:
            root_elements.append(element)
        
        last_end_line = child.end_point[0]
    
    # Handle any remaining content at the end of the file
    total_lines = len(code.split('\n'))
    if total_lines > last_end_line + 2:
        block_content = get_lines_between(last_end_line + 1, total_lines - 1)
        if block_content.strip() and is_significant_content(block_content):
            block_name = f"top_level_block_{top_level_counter}"
            existing_names = {e.identifier for e in root_elements}
            while block_name in existing_names:
                block_name = f"_top_level_block_{top_level_counter}"
            
            # Use the first non-empty line as the header
            block_header = get_first_non_empty_line(block_content)
            
            top_level_block = Element(
                identifier=block_name,
                header=block_header,
                content=block_content,  
                description="",
                line_start=last_end_line + 1,
                elements=[]
            )
            root_elements.append(top_level_block)
    
    return root_elements
