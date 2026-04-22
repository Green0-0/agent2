from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import functools
import itertools
import operator
from collections import ChainMap, Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any, Concatenate, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")
U = TypeVar("U")


def pipeline_stage(
    name: str | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator that marks a function as a pipeline stage.

    Args:
        name: Optional stage name. Uses function name if not provided.

    Returns:
        Decorated function with stage metadata.
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        stage_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            print(f"[STAGE: {stage_name}] Starting...")
            try:
                result = func(*args, **kwargs)
                print(f"[STAGE: {stage_name}] Completed")
                return result
            except Exception as e:
                print(f"[STAGE: {stage_name}] Failed: {e}")
                raise

        wrapper._stage_name = stage_name  # type: ignore[attr-defined]
        wrapper._is_pipeline_stage = True  # type: ignore[attr-defined]
        return wrapper

    return decorator


def compose(
    *functions: Callable[[Any], Any],
) -> Callable[[Any], Any]:
    """
    Compose multiple functions right-to-left.

    Returns:
        Composed function.
    """

    def composed(value: Any) -> Any:
        result = value
        for fn in reversed(functions):
            result = fn(result)
        return result

    return composed


def curry(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Curry a function of any arity.

    Returns:
        Curried version of the function.
    """

    def curried(*args: Any) -> Any:
        if len(args) >= func.__code__.co_argcount:
            return func(*args)
        return lambda *more: curried(*(args + more))

    return curried


@dataclass(frozen=True)
class DataRecord:
    """
    Immutable data record for pipeline processing.

    Attributes:
        id: Unique record identifier.
        payload: Record data payload.
        metadata: Processing metadata.
    """

    id: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = functools.field(default_factory=dict)

    def with_metadata(self, **kwargs: Any) -> DataRecord:
        """Return new record with updated metadata."""
        return DataRecord(
            self.id, self.payload, {**self.metadata, **kwargs}
        )


class Pipeline:
    """
    Configurable data processing pipeline.

    Supports branching, conditional stages, error recovery,
    and parallel execution.
    """

    def __init__(self) -> None:
        self._stages: list[Callable[[Any], Any]] = []
        self._error_handlers: dict[type[Exception], Callable[[Exception], Any]] = {}

    def add(
        self,
        stage: Callable[[T], U],
        *,
        condition: Callable[[T], bool] | None = None,
    ) -> Pipeline:
        """
        Add a processing stage.

        Args:
            stage: The processing function.
            condition: Optional predicate to conditionally execute.

        Returns:
            Self for method chaining.
        """
        if condition:

            def conditional_stage(data: T) -> U | T:
                return stage(data) if condition(data) else data  # type: ignore[return-value]

            self._stages.append(conditional_stage)
        else:
            self._stages.append(stage)
        return self

    def on_error(
        self,
        exc_type: type[Exception],
        handler: Callable[[Exception], Any],
    ) -> Pipeline:
        """Register error handler for specific exception type."""
        self._error_handlers[exc_type] = handler
        return self

    def execute(self, data: Any) -> Any:
        """
        Execute pipeline on data with error handling.

        Args:
            data: Input data.

        Returns:
            Processed data.

        Raises:
            Exception: If unhandled error occurs.
        """
        result = data
        for stage in self._stages:
            try:
                result = stage(result)
            except Exception as e:
                handler = None
                for exc_type, h in self._error_handlers.items():
                    if isinstance(e, exc_type):
                        handler = h
                        break
                if handler:
                    result = handler(e)
                else:
                    raise
        return result

    def parallel_execute(
        self,
        items: Sequence[Any],
        *,
        max_workers: int = 4,
    ) -> Iterator[Any]:
        """
        Execute pipeline in parallel over multiple items.

        Args:
            items: Sequence of input items.
            max_workers: Maximum parallel workers.

        Yields:
            Processed results.
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers
        ) as executor:
            futures = [executor.submit(self.execute, item) for item in items]
            for future in concurrent.futures.as_completed(futures):
                yield future.result()


@pipeline_stage(name="validate")
def validate_record(record: DataRecord) -> DataRecord:
    """
    Validate that record has required fields.

    Args:
        record: Input data record.

    Returns:
        Validated record.

    Raises:
        ValueError: If validation fails.
    """
    if not record.id:
        raise ValueError("Record ID is required")
    if "type" not in record.payload:
        raise ValueError("Record type is required")
    return record


@pipeline_stage(name="enrich")
def enrich_record(record: DataRecord) -> DataRecord:
    """
    Enrich record with computed fields.

    Args:
        record: Input data record.

    Returns:
        Enriched record.
    """
    payload = dict(record.payload)
    payload["_computed"] = {
        "hash": hash(record.id),
        "size": len(str(record.payload)),
    }
    return DataRecord(record.id, payload, record.metadata)


@pipeline_stage(name="transform")
def transform_record(record: DataRecord) -> DataRecord:
    """
    Apply type-specific transformations.

    Uses structural pattern matching (match/case) to handle
    different record types.
    """
    match record.payload.get("type"):
        case "user":
            return record.with_metadata(category="identity")
        case "event" as event_type:
            return record.with_metadata(
                category="activity", event_type=event_type
            )
        case {"nested": True, **rest}:
            return record.with_metadata(nested=True, rest=rest)
        case _:
            return record.with_metadata(category="unknown")


def complex_control_flow_demo(n: int) -> dict[str, Any]:
    """
    Demonstrate every Python control flow construct.

    Args:
        n: Input number to process.

    Returns:
        Dictionary of results.
    """
    results: dict[str, Any] = {}

    # If/elif/else chain
    if n < 0:
        results["sign"] = "negative"
    elif n == 0:
        results["sign"] = "zero"
    else:
        results["sign"] = "positive"

    # While loop with else
    i = 0
    while i < n:
        if i == 5:
            break
        i += 1
    else:
        results["while_completed"] = True

    # For loop with continue and else
    squares = []
    for x in range(n):
        if x % 2 == 0:
            continue
        squares.append(x**2)
    else:
        results["for_completed"] = True

    # Try/except/else/finally with multiple except clauses
    try:
        risky = 1 / n
    except ZeroDivisionError:
        results["division"] = "undefined"
    except Exception as e:
        results["division_error"] = str(e)
    else:
        results["division"] = risky
    finally:
        results["division_checked"] = True

    # Match statement (structural pattern matching)
    match n:
        case 0:
            results["matched"] = "zero"
        case 1 | 2 | 3:
            results["matched"] = "small"
        case x if x > 100:
            results["matched"] = "large"
        case _:
            results["matched"] = "medium"

    # Exception groups (Python 3.11+)
    try:
        raise ExceptionGroup(
            "multiple errors",
            [
                ValueError("first"),
                TypeError("second"),
                ValueError("third"),
            ],
        )
    except* ValueError as eg:
        results["value_errors"] = len(eg.exceptions)
    except* TypeError as eg:
        results["type_errors"] = len(eg.exceptions)

    # With statement and context managers
    with contextlib.suppress(ZeroDivisionError):
        results["suppressed"] = 1 / 0

    # Nested with
    with open(__file__) as f1:
        with open(__file__) as f2:
            results["nested_with"] = f1.readline() == f2.readline()

    # Async for and comprehensions (defined but not run here)
    async def async_generator() -> AsyncIterator[int]:
        for i in range(n):
            yield i
            await asyncio.sleep(0)

    # List/dict/set comprehensions with complex nesting
    matrix = [[i * j for j in range(3)] for i in range(3)]
    flat = [x for row in matrix for x in row if x > 0]
    grouped = {
        k: [v for v in range(n) if v % 2 == k]
        for k in [0, 1]
    }
    unique = {x**2 for x in range(n)}

    # Generator expression
    gen = (x**3 for x in range(n) if x % 2 == 0)

    results.update(
        squares=squares,
        matrix=matrix,
        flat=flat,
        grouped=grouped,
        unique=unique,
        gen=list(gen),
    )

    return results


def lambda_nesting_demo() -> Callable[[int], int]:
    """
    Demonstrate deeply nested lambda expressions.

    Returns:
        A function composed of nested lambdas.
    """
    # Lambda returning lambda
    make_adder = lambda x: (lambda y: x + y)

    # Lambda in default argument
    def with_lambda_default(
        fn: Callable[[int], int] = lambda z: z * 2
    ) -> Callable[[int], int]:
        return fn

    # Lambda in comprehension
    processors = [(lambda n: n + i) for i in range(5)]

    # Lambda with conditional expression
    conditional = lambda x: "even" if x % 2 == 0 else "odd"

    # Immediately invoked lambda
    result = (lambda: 42)()

    return make_adder(5)


def closure_and_nonlocal_demo() -> Callable[[], int]:
    """
    Demonstrate closure with nonlocal and cell variables.
    """
    count = 0

    def increment() -> int:
        nonlocal count
        count += 1
        return count

    def decrement() -> int:
        nonlocal count
        count -= 1
        return count

    def get() -> int:
        return count

    # Return a dispatch function
    def dispatch(op: str) -> int:
        match op:
            case "inc":
                return increment()
            case "dec":
                return decrement()
            case "get":
                return get()
            case _:
                raise ValueError(f"Unknown operation: {op}")

    return dispatch


# Module-level complex expressions
records = [
    DataRecord(
        id=f"rec-{i}",
        payload={"type": "user", "name": f"User {i}"},
    )
    for i in range(100)
    if i % 3 == 0
]

# ChainMap and Counter usage
counter = Counter(r.payload["type"] for r in records)
grouped = defaultdict(list)
for r in records:
    grouped[r.payload["type"]].append(r)

# Complex boolean expression
filtered = [
    r
    for r in records
    if r.id.startswith("rec-")
    and r.payload.get("type") == "user"
    and len(r.payload) > 1
    or r.metadata.get("override", False)
]

# Walrus operator in while and if
while (line := "sample"):
    if (n := len(line)) > 0:
        print(f"Length: {n}")
    break

# Type alias with union
StringOrInt = str | int

# Final assignment
FINAL_VALUE: Final[int] = 42