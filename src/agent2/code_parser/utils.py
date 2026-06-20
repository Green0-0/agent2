from typing import Tuple

def calculate_new_endpoint(start_point: Tuple[int, int], new_text: bytes) -> Tuple[int, int]:
    """Calculates the outgoing (row, byte_column) coordinates for a newly injected text block."""
    newlines = new_text.count(b'\n')
    if newlines == 0:
        return (start_point[0], start_point[1] + len(new_text))
    
    last_line_bytes = new_text.rsplit(b'\n', 1)[-1]
    return (start_point[0] + newlines, len(last_line_bytes))