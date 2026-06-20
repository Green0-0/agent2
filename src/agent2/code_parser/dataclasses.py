from dataclasses import field
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class CodeEdit:
    """Payload representing a targeted text mutation.
    
    Attributes:
        start_byte: The starting byte of the edit.
        end_byte: The ending byte of the edit.
        start_point: The starting line/column of the edit. 0-indexed.
        end_point: The ending line/column of the edit. 0-indexed.
        new_text: The new text to insert.
    """
    start_byte: int
    end_byte: int
    start_point: Tuple[int, int]
    end_point: Tuple[int, int]
    new_text: bytes

@dataclass(frozen=True)
class CodeBlock:
    """
    Stores the information corresponding to a block of code represented with tree-sitter.
    
    Attributes:
        start_byte: The starting byte of the block.
        end_byte: The ending byte of the block.
        start_point: The starting line/column of the block. 0-indexed.
        end_point: The ending line/column of the block. 0-indexed.
    """
    start_byte: int
    end_byte: int
    start_point: Tuple[int, int]
    end_point: Tuple[int, int]

@dataclass(frozen=True)
class CodeState:
    """
    An immutable snapshot of a script's raw text state at a specific moment.
    Also contains information about line-endings, which are necessary for byte/line/column coordinate transformations.
    
    Attributes:
        bytes: The raw bytes of the file.
        total_bytes: The total number of bytes in the file.
        _line_starts: A list of byte offsets corresponding to the start of each line.
    """
    bytes: bytes
    
    total_bytes: int = field(init=False)
    _line_starts: Tuple[int, ...] = field(init=False, repr=False)

    def __post_init__(self):
        """Precomputes the line starts for O(1) line-number resolution."""
        object.__setattr__(self, 'total_bytes', len(self.bytes))
        
        line_starts = [0]
        for i, byte in enumerate(self.bytes):
            if byte == ord('\n'):
                line_starts.append(i + 1)

        object.__setattr__(self, '_line_starts', tuple(line_starts))

    def get_line_byte_range(self, line_num_1_indexed: int) -> Tuple[int, int]:
        """Returns the (start_byte, end_byte) for a given 1-indexed line number.
        
        Args:
            line_num_1_indexed: The 1-indexed line number.
            
        Returns:
            A tuple of (start_byte, end_byte).
        """
        idx = line_num_1_indexed - 1
        
        if idx >= len(self._line_starts) or idx < 0:
            return self.total_bytes, self.total_bytes
        
        start = self._line_starts[idx]
        end = self._line_starts[idx + 1] if idx + 1 < len(self._line_starts) else self.total_bytes
        return start, end

@dataclass(frozen=True)
class CodeNode:
    """
    A code node in a script that has been parsed. Holds an identifying path.

    Attributes:
        name: The name of the node.
        full_block: The block of the entire node.
        signature_block: The block of the node signature.
        doc_block: The block of the node docstring.
        body_block: The block of the node body.
        parent_path: The path to the parent node.
        children: A tuple of child CodeNodes.
    """
    name: str
    full_block: CodeBlock
    signature_block: CodeBlock
    doc_block: Optional[CodeBlock]
    body_block: Optional[CodeBlock]
    parent_path: Optional[str] = None
    children: tuple['CodeNode', ...] = field(default_factory=tuple)

    @property
    def llm_path(self) -> str:
        """
        Generates deterministic, 1-indexed lookup paths for the agent.
        Example: 'MyClass.my_function.42'
        """
        line_num = self.full_block.start_point[0] + 1
        base = f"{self.parent_path}.{self.name}" if self.parent_path else self.name
        return f"{base}.{line_num}"

    @property
    def path(self) -> str:
        """
        Generates deterministic lookup paths for the agent without line numbers.
        Example: 'MyClass.my_function'
        """
        return f"{self.parent_path}.{self.name}" if self.parent_path else self.name