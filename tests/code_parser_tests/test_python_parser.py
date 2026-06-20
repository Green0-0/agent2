import os
import pytest
from pathlib import Path

from agent2.code_parser.code_file import CodeFile
from agent2.code_parser.dataclasses import CodeEdit
from agent2.code_parser.languages.python import PythonLanguageAdapter
from agent2.code_parser.interface.renderer import view_code_node_automatic, view_code_node_full

SCRIPTS_DIR = Path(__file__).parent / "scripts" / "python"

def read_script(filename: str) -> bytes:
    with open(SCRIPTS_DIR / filename, "rb") as f:
        return f.read()

@pytest.fixture
def python_adapter():
    return PythonLanguageAdapter()

def print_node_report(node, source: bytes):
    if not os.environ.get("PRINT_PARSE_REPORT"): return
    print(f"\n{'='*60}")
    print(f"Node Report: {node.llm_path}")
    print(f"{'='*60}")
    print("--- SIGNATURE ---")
    if node.signature_block:
        print(source[node.signature_block.start_byte:node.signature_block.end_byte].decode("utf-8", errors="replace"))
    print("--- DOCSTRING ---")
    if node.doc_block:
        print(source[node.doc_block.start_byte:node.doc_block.end_byte].decode("utf-8", errors="replace"))
    else:
        print("None")
    print("--- BODY ---")
    if node.body_block:
        print(source[node.body_block.start_byte:node.body_block.end_byte].decode("utf-8", errors="replace"))
    else:
        print("None")
    print(f"{'='*60}\n")

def print_render_report(title: str, text: str):
    if not os.environ.get("PRINT_PARSE_REPORT"): return
    print(f"\n{'='*60}")
    print(f"Render Report: {title}")
    print(f"{'='*60}")
    print(text)
    print(f"{'='*60}\n")

def test_syntax_edge_cases_extraction(python_adapter):
    source = read_script("syntax_edge_case.py")
    code_file = CodeFile(python_adapter, source)
    
    nodes = code_file.code_nodes
    
    # Check simple function
    assert "plain_function.2" in nodes
    plain_func = nodes["plain_function.2"]
    print_node_report(plain_func, source)
    assert plain_func.doc_block is not None
    assert source[plain_func.signature_block.start_byte:plain_func.signature_block.end_byte].strip() == b"def plain_function():"
    assert b"This docstring comes before any decorators." in source[plain_func.doc_block.start_byte:plain_func.doc_block.end_byte]
    assert source[plain_func.body_block.start_byte:plain_func.body_block.end_byte].strip().endswith(b"pass")
    
    # Check decorated function
    assert "multi_decorated.11" in nodes
    multi_decorated = nodes["multi_decorated.11"]
    print_node_report(multi_decorated, source)
    sig = source[multi_decorated.signature_block.start_byte:multi_decorated.signature_block.end_byte]
    assert sig.startswith(b"@decorator1")
    assert b"def multi_decorated():" in sig
    assert source[multi_decorated.doc_block.start_byte:multi_decorated.doc_block.end_byte] == b'"""Function with multiple stacked decorators."""'
    assert source[multi_decorated.body_block.start_byte:multi_decorated.body_block.end_byte].strip().endswith(b"return 42")
    
    # Check nested classes and methods
    assert "WeirdLayout.30" in nodes
    assert "WeirdLayout" in nodes
    weird_layout = nodes["WeirdLayout.30"]
    print_node_report(weird_layout, source)
    assert source[weird_layout.doc_block.start_byte:weird_layout.doc_block.end_byte] == b'"""Class with unusual method ordering and spacing."""'
    
    assert "WeirdLayout.method_after_attribute.35" in nodes
    assert "WeirdLayout.method_after_attribute" in nodes
    assert "WeirdLayout.InnerClass.41" in nodes
    assert "WeirdLayout.InnerClass" in nodes
    assert "WeirdLayout.InnerClass.inner_method.44" in nodes
    assert "WeirdLayout.InnerClass.inner_method" in nodes
    
    # Check docstring on one-liner
    assert "WeirdLayout.minimal.58" in nodes
    minimal_node = nodes["WeirdLayout.minimal.58"]
    print_node_report(minimal_node, source)
    assert minimal_node.doc_block is not None
    assert source[minimal_node.doc_block.start_byte:minimal_node.doc_block.end_byte] == b'"""One-liner docstring"""'
    assert source[minimal_node.body_block.start_byte:minimal_node.body_block.end_byte].endswith(b'pass')
    
    # Check async functions
    assert "async_function.105" in nodes
    async_func = nodes["async_function.105"]
    print_node_report(async_func, source)
    assert source[async_func.signature_block.start_byte:async_func.signature_block.end_byte].strip() == b"async def async_function():"
    
    # Check nested functions
    assert "scope_manipulation.152" in nodes
    assert "scope_manipulation.nested.159" in nodes
    nested_func = nodes["scope_manipulation.nested.159"]
    print_node_report(nested_func, source)
    assert b"nonlocal local_var" in source[nested_func.body_block.start_byte:nested_func.body_block.end_byte]

def test_enterprise_framework_extraction(python_adapter):
    source = read_script("enterprise_framework.py")
    code_file = CodeFile(python_adapter, source)
    nodes = code_file.code_nodes
    
    assert "log_calls.57" in nodes
    assert "log_calls.decorator.68" in nodes
    assert "log_calls.decorator.wrapper.69" in nodes
    
    wrapper_func = nodes["log_calls.decorator.wrapper.69"]
    print_node_report(wrapper_func, source)
    assert b"@functools.wraps(func)" in source[wrapper_func.signature_block.start_byte:wrapper_func.signature_block.end_byte]
    assert b"def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:" in source[wrapper_func.signature_block.start_byte:wrapper_func.signature_block.end_byte]
    
    assert "BaseEntity.171" in nodes
    assert "BaseEntity.__init__.185" in nodes
    assert "BaseEntity.entity_type.202" in nodes
    entity_type = nodes["BaseEntity.entity_type.202"]
    print_node_report(entity_type, source)
    assert b"@property\n    @abstractmethod\n    def entity_type(self) -> str:" in source[entity_type.signature_block.start_byte:entity_type.signature_block.end_byte]
    assert source[entity_type.doc_block.start_byte:entity_type.doc_block.end_byte] == b'"""Return the entity type identifier."""'
    assert source[entity_type.body_block.start_byte:entity_type.body_block.end_byte].strip().endswith(b"...")
    
    assert "ServiceEntity.265" in nodes
    assert "ServiceEntity.Config.282" in nodes
    assert "ServiceEntity.Config.__init__.292" in nodes
    
    # Check overloaded methods resolving uniquely by line number
    assert "ServiceEntity.__init__.303" in nodes
    assert "ServiceEntity.__init__.307" in nodes
    assert "ServiceEntity.__init__.311" in nodes  # Wait, line 311 is the def
    
    init_303 = nodes["ServiceEntity.__init__.303"]
    print_node_report(init_303, source)
    assert b"@overload\n    def __init__(self, name: str, config: None = None) -> None:" in source[init_303.signature_block.start_byte:init_303.signature_block.end_byte]
    
    init_311 = nodes["ServiceEntity.__init__.311"]
    print_node_report(init_311, source)
    assert b"def __init__(\n        self,\n        name: str,\n        config: dict[str, Any] | None = None,\n    ) -> None:" in source[init_311.signature_block.start_byte:init_311.signature_block.end_byte]

def test_data_processing_pipeline_extraction(python_adapter):
    source = read_script("data_processing_pipeline.py")
    code_file = CodeFile(python_adapter, source)
    nodes = code_file.code_nodes
    
    assert "pipeline_stage.19" in nodes
    assert "pipeline_stage.decorator.32" in nodes
    assert "pipeline_stage.decorator.wrapper.35" in nodes
    
    assert "DataRecord.88" in nodes
    assert "DataRecord.with_metadata.103" in nodes
    
    assert "Pipeline.110" in nodes
    assert "Pipeline.__init__.118" in nodes
    assert "Pipeline.add.122" in nodes
    assert "Pipeline.add.conditional_stage.140" in nodes

def test_apply_edit_and_reparse(python_adapter):
    source = b"def test():\n    pass\n"
    code_file = CodeFile(python_adapter, source)
    
    node = code_file.code_nodes["test.1"]
    
    # Replace "pass" with "return True"
    edit = CodeEdit(
        start_byte=node.body_block.start_byte,
        end_byte=node.body_block.end_byte,
        start_point=node.body_block.start_point,
        end_point=node.body_block.end_point,
        new_text=b"    return True\n"
    )
    
    code_file.apply_edit_and_reparse(edit)
    
    assert b"return True" in code_file.buffer.bytes
    assert "test.1" in code_file.code_nodes

def test_view_code_node_automatic(python_adapter):
    source = read_script("enterprise_framework.py")
    code_file = CodeFile(python_adapter, source)
    
    node = code_file.code_nodes["ServiceEntity.265"]
    
    full_view = view_code_node_full(node, source)
    full_len = len(full_view.split())
    print_render_report("FULL VIEW", full_view)
    
    # Test ceiling_behavior = under
    view_under = view_code_node_automatic(node, source, symbol_limit=10, ceiling_behavior="under")
    print_render_report("AUTOMATIC VIEW (limit=10, under)", view_under)
    
    view_over = view_code_node_automatic(node, source, symbol_limit=10, ceiling_behavior="over")
    print_render_report("AUTOMATIC VIEW (limit=10, over)", view_over)
    
    assert len(view_under.split()) <= 10 or len(view_under.split()) == len(view_over.split())
    assert "BODY HIDDEN" in view_under
    
    # Test ceiling_behavior = over
    assert len(view_over.split()) >= 10
    
    # Test ceiling_behavior = closer
    view_closer = view_code_node_automatic(node, source, symbol_limit=full_len, ceiling_behavior="closer")
    print_render_report(f"AUTOMATIC VIEW (limit={full_len}, closer)", view_closer)
    assert "BODY HIDDEN" not in view_closer
    assert len(view_closer.split()) == full_len
    
    # Test a middle limit, triggering a partially collapsed depth
    middle_limit = full_len // 2
    view_middle = view_code_node_automatic(node, source, symbol_limit=middle_limit, ceiling_behavior="closer")
    print_render_report(f"AUTOMATIC VIEW (limit={middle_limit}, closer)", view_middle)
    assert "BODY HIDDEN" in view_middle or len(view_middle.split()) <= full_len

