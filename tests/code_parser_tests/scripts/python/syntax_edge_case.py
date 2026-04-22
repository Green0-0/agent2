# Function with docstring before decorators (unusual but valid)
def plain_function():
    """
    This docstring comes before any decorators.
    Tree-sitter must not associate it with a non-existent decorator.
    """
    pass


# Multiple decorators with arguments
@decorator1
@decorator2(
    arg1="value1",
    arg2="value2",
)
@decorator3
def multi_decorated():
    """Function with multiple stacked decorators."""
    return 42


# Decorator with lambda
@lambda f: (lambda *a, **k: f(*a, **k))
def decorated_with_lambda():
    """Function decorated by a lambda."""
    pass


# Class with methods in weird order
class WeirdLayout:
    """Class with unusual method ordering and spacing."""

    class_attribute = 1

    def method_after_attribute(self):
        """Method defined after class attribute."""
        return self.class_attribute

    inner_class_attribute = 2

    class InnerClass:
        """Nested class not at top of parent."""

        def inner_method(self):
            """Method in nested class."""
            return "inner"

    @property
    def prop_after_nested(self):
        """Property defined after nested class."""
        return self.inner_class_attribute

    # Method with no body (ellipsis)
    def abstract_like(self, x: int, y: str) -> None:
        ...

    # Method with pass and docstring on same line
    def minimal(self): """One-liner docstring"""; pass

    # Method with only docstring (implicit pass)
    def doc_only(self):
        """Only a docstring, no explicit body."""


# Function with type comments (Python 2 style, still parsed)
def type_comments(x, y):
    # type: (int, str) -> bool
    """Function with type comments."""
    return True


# Function with complex signature
def complex_signature(
    self,
    a: int = 1,
    /,
    b: str = "default",
    *args: Any,
    c: float = 3.14,
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Function with positional-only, keyword-only, varargs, and defaults.

    Args:
        a: Positional-only parameter.
        b: Regular parameter with default.
        args: Variable positional arguments.
        c: Keyword-only parameter.
        kwargs: Variable keyword arguments.

    Returns:
        Dictionary of all arguments.
    """
    return {
        "a": a,
        "b": b,
        "args": args,
        "c": c,
        "kwargs": kwargs,
    }


# Async functions with every variant
async def async_function():
    """Standard async function."""
    await asyncio.sleep(0)


async def async_generator():
    """Async generator function."""
    yield 1
    yield 2


async def async_comprehension():
    """Async function with async comprehension."""
    return [x async for x in async_generator()]


# Generator with send/throw/close
def interactive_generator():
    """
    Generator that interacts with caller via send().

    Yields:
        Processed values.
    """
    value = yield "initial"
    while value is not None:
        value = yield f"received: {value}"
    yield "done"


# Function with yield from (delegation)
def delegating_generator():
    """Generator that delegates to another."""
    yield from range(10)
    yield from interactive_generator()


# Context manager as decorator
@contextlib.contextmanager
def managed_resource():
    """Context manager used as decorator."""
    print("acquiring")
    yield "resource"
    print("releasing")


# Function with global and nonlocal
def scope_manipulation():
    """Function demonstrating global and nonlocal."""
    global module_level_var
    module_level_var = 100

    local_var = 0

    def nested():
        nonlocal local_var
        local_var += 1
        return local_var

    return nested


# Function with try/except inside finally
def nested_exception_handling():
    """
    Function with deeply nested exception handling.
    """
    try:
        try:
            raise ValueError("inner")
        except ValueError:
            raise TypeError("converted")
        finally:
            print("inner finally")
    except TypeError:
        print("caught converted")
    finally:
        try:
            print("outer finally")
        except Exception:
            pass


# Function with for/else and break/continue complexity
def loop_complexity(items):
    """
    Function with complex loop control flow.
    """
    found = None
    for i, item in enumerate(items):
        if item == "skip":
            continue
        if item == "break":
            break
        if item == "found":
            found = i
            break
    else:
        # Executes if loop completed without break
        found = -1

    # While with complex condition
    while (found is not None and found >= 0):
        found -= 1
        if found == 0:
            break
    else:
        print("while completed")

    return found


# Function with match and guards
def pattern_matching(value):
    """
    Function using structural pattern matching.
    """
    match value:
        case None:
            return "nothing"
        case int(n) if n < 0:
            return f"negative {n}"
        case int(n):
            return f"positive {n}"
        case str(s) if s.startswith("prefix"):
            return f"prefixed: {s}"
        case str(s):
            return f"string: {s}"
        case [x, y, *rest]:
            return f"list with {x}, {y}, and {len(rest)} more"
        case {"type": "user", "name": name}:
            return f"user {name}"
        case _:
            return "unknown"


# Class with dataclass and slots
@dataclass(frozen=True, slots=True, kw_only=True)
class FrozenData:
    """
    Frozen dataclass with keyword-only arguments and slots.
    """
    x: int
    y: int = 0
    z: str = "default"


# Class with custom __init_subclass__
class BaseWithInitSubclass:
    """
    Base class that modifies subclass creation.
    """
    _subclasses: list[type] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._subclasses.append(cls)


class Sub1(BaseWithInitSubclass):
    pass


class Sub2(BaseWithInitSubclass, extra=True):
    pass


# Function with exec and eval (dynamic code)
def dynamic_execution():
    """Function using dynamic code execution."""
    code = compile("x = 1 + 2", "<string>", "exec")
    namespace = {}
    exec(code, namespace)
    return eval("x", namespace)


# Function with del statements
def deletion_operations():
    """Function demonstrating del on various targets."""
    x = [1, 2, 3]
    del x[0]
    del x[1:2]
    y = {"a": 1, "b": 2}
    del y["a"]
    z = 1
    del z


# Function with assert
def assertion_function(x):
    """Function with assertion."""
    assert x > 0, "x must be positive"
    assert isinstance(x, int)
    return x


# Function with raise from (exception chaining)
def chained_exception():
    """Function raising exception with explicit chaining."""
    try:
        raise ValueError("original")
    except ValueError as e:
        raise RuntimeError("wrapped") from e


# Function with return annotation but no body
def stub_function(x: int) -> str:
    ...


# Function with only ellipsis body
def only_ellipsis():
    ...


# Lambda with complex expression
complex_lambda = (
    lambda x,
    y,
    z=10: (
        x + y
        if x > y
        else x - y
    )
    * z
)

# Walrus operator in various contexts
def walrus_demo():
    """Function demonstrating assignment expressions."""
    if (n := len("hello")) > 3:
        print(f"Length is {n}")

    while (line := input()) != "quit":
        print(f"Echo: {line}")

    return [
        y := x + 1
        for x in range(10)
        if (y := x * 2) > 5
    ]


# Module-level conditional execution
if __name__ == "__main__":
    print("Running as script")
elif __name__ == "syntax_edge_cases":
    print("Running as module")
else:
    print("Unknown execution context")


# Module-level try/except
try:
    risky_module_operation()
except NameError:
    print("Expected error")
finally:
    print("Cleanup")


# Star imports (valid syntax, though discouraged)
# from typing import *


# Future import (must be first in real code, here for testing)
# from __future__ import annotations