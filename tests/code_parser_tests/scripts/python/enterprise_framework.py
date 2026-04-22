from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import weakref
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    ClassVar,
    Final,
    Generic,
    Literal,
    NamedTuple,
    ParamSpec,
    Protocol,
    TypeAlias,
    TypeVar,
    final,
    overload,
)

# Type variables and aliases
T = TypeVar("T")
P = ParamSpec("P")
R = TypeVar("R")

JsonDict: TypeAlias = dict[str, Any]
MaybeInt: TypeAlias = int | None


class FrameworkError(Exception):
    """Base exception for framework errors."""

    def __init__(self, message: str, *, code: int = 500) -> None:
        self.code = code
        super().__init__(message)


class ValidationError(FrameworkError):
    """Raised when input validation fails."""

    pass


class AuthenticationError(FrameworkError):
    """Raised when authentication fails."""

    pass


def log_calls(level: int = logging.INFO) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator factory that logs function calls with arguments.

    Args:
        level: The logging level to use.

    Returns:
        A decorator that wraps the target function.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            logging.log(level, f"Calling {func.__name__} with {args}, {kwargs}")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def retry(
    max_attempts: int = 3, exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator that retries function calls on failure.

    Args:
        max_attempts: Maximum number of retry attempts.
        exceptions: Tuple of exception types to catch.

    Returns:
        A decorator that implements retry logic.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        raise
                    logging.warning(f"Attempt {attempt} failed: {e}")

            # Should never reach here, but satisfies type checker
            raise RuntimeError("Unexpected exit from retry loop")

        return wrapper

    return decorator


class PropertyDescriptor:
    """
    Custom descriptor implementing property-like behavior with caching.

    This demonstrates a non-decorator descriptor class that tree-sitter
    must correctly associate with its containing class.
    """

    def __init__(self, getter: Callable[[Any], Any]) -> None:
        self.getter = getter
        self.name = getter.__name__
        self._cache: weakref.WeakKeyDictionary[Any, Any] = weakref.WeakKeyDictionary()

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        if instance is None:
            return self
        if instance not in self._cache:
            self._cache[instance] = self.getter(instance)
        return self._cache[instance]

    def __set__(self, instance: Any, value: Any) -> None:
        raise AttributeError(f"Cannot set read-only descriptor {self.name}")

    def __delete__(self, instance: Any) -> None:
        if instance in self._cache:
            del self._cache[instance]


class FrameworkMeta(type):
    """
    Metaclass that automatically registers subclasses.

    This metaclass maintains a registry of all classes created with it,
    demonstrating that tree-sitter must handle metaclass syntax correctly.
    """

    _registry: ClassVar[dict[str, type[Any]]] = {}

    def __new__(
        mcs: type[type],
        name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type[Any]:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        mcs._registry[name] = cls
        return cls

    def __init__(
        cls,
        name: str,
        bases: tuple[type[Any], ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, namespace, **kwargs)


class BaseEntity(ABC, metaclass=FrameworkMeta):
    """
    Abstract base class for all framework entities.

    All entities must implement the serialize method and provide
    a unique identifier.

    Attributes:
        _id: Internal unique identifier.
        created_at: Timestamp of creation.
    """

    _counter: ClassVar[int] = 0

    def __init__(self, name: str) -> None:
        """
        Initialize the base entity.

        Args:
            name: Human-readable name for the entity.

        Raises:
            ValueError: If name is empty.
        """
        if not name:
            raise ValueError("Name cannot be empty")
        BaseEntity._counter += 1
        self._id = f"{self.__class__.__name__}-{BaseEntity._counter}"
        self.name = name
        self.created_at = asyncio.get_event_loop().time()

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Return the entity type identifier."""
        ...

    @abstractmethod
    def serialize(self) -> JsonDict:
        """
        Serialize entity to JSON-compatible dictionary.

        Returns:
            Dictionary representation of the entity.
        """
        ...

    @log_calls(level=logging.DEBUG)
    def validate(self) -> bool:
        """
        Validate entity state.

        Returns:
            True if valid, False otherwise.
        """
        return bool(self.name and self._id)

    @classmethod
    def get_registry(cls) -> dict[str, type[Any]]:
        """Get the class registry from the metaclass."""
        return FrameworkMeta._registry

    @staticmethod
    def generate_id(prefix: str) -> str:
        """Generate a new unique ID with the given prefix."""
        return f"{prefix}-{BaseEntity._counter}"


@dataclass(frozen=True, slots=True)
class Point(NamedTuple):
    """
    Immutable 2D point.

    This uses both @dataclass and NamedTuple inheritance to test
    tree-sitter's handling of multiple decorators and inheritance.
    """

    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        """Calculate Euclidean distance to another point."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class Status(Enum):
    """Entity status enumeration."""

    PENDING = auto()
    ACTIVE = auto()
    SUSPENDED = auto()
    TERMINATED = auto()


class ServiceEntity(BaseEntity):
    """
    Concrete service entity with full feature set.

    This class demonstrates:
    - Nested classes
    - Property decorators with setters
    - Overloaded methods
    - Async methods
    - Context manager protocol
    - Generic typing

    Attributes:
        status: Current service status.
        config: Service configuration dictionary.
    """

    class Config:
        """
        Nested configuration class.

        This nested class should be identified as a child of ServiceEntity
        by the tree-sitter parser.
        """

        DEFAULT_TIMEOUT: Final[int] = 30

        def __init__(self, timeout: int = DEFAULT_TIMEOUT, retries: int = 3) -> None:
            self.timeout = timeout
            self.retries = retries

        def as_dict(self) -> dict[str, int]:
            """Convert config to dictionary."""
            return {"timeout": self.timeout, "retries": self.retries}

    _status: Status = Status.PENDING
    _config: Config

    @overload
    def __init__(self, name: str, config: None = None) -> None:
        ...

    @overload
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        ...

    def __init__(
        self,
        name: str,
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name)
        self._config = self.Config(**config) if config else self.Config()

    @property
    def entity_type(self) -> str:
        """Return the entity type."""
        return "service"

    @property
    def status(self) -> Status:
        """Get current status."""
        return self._status

    @status.setter
    def status(self, value: Status) -> None:
        """Set status with validation."""
        if not isinstance(value, Status):
            raise ValidationError(f"Invalid status: {value}")
        self._status = value

    @status.deleter
    def status(self) -> None:
        """Reset status to pending."""
        self._status = Status.PENDING

    @PropertyDescriptor
    def computed_value(self) -> int:
        """
        Computed property using custom descriptor.

        This should be identified as a property with a custom descriptor.
        """
        return hash(self._id) % 10000

    @retry(max_attempts=3, exceptions=(ConnectionError,))
    def connect(self, endpoint: str) -> bool:
        """
        Connect to a remote endpoint with retry logic.

        Args:
            endpoint: The URL to connect to.

        Returns:
            True if connection successful.

        Raises:
            ConnectionError: If all retries fail.
        """
        # Simulated connection logic
        if "fail" in endpoint:
            raise ConnectionError(f"Failed to connect to {endpoint}")
        return True

    async def health_check(self) -> dict[str, Any]:
        """
        Async health check.

        Returns:
            Health status dictionary.
        """
        await asyncio.sleep(0.1)
        return {"status": "healthy", "entity": self._id}

    async def __aenter__(self) -> ServiceEntity:
        """Async context manager entry."""
        await self.health_check()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> Literal[False]:
        """Async context manager exit."""
        self.status = Status.TERMINATED
        return False

    def serialize(self) -> JsonDict:
        """Serialize to dictionary."""
        return {
            "id": self._id,
            "name": self.name,
            "type": self.entity_type,
            "status": self._status.name,
            "config": self._config.as_dict(),
        }

    def __enter__(self) -> ServiceEntity:
        """Sync context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> Literal[False]:
        """Sync context manager exit."""
        self.status = Status.TERMINATED
        return False

    def __repr__(self) -> str:
        return f"<ServiceEntity {self._id}: {self.name}>"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ServiceEntity):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


class Repository(Generic[T], ABC):
    """
    Generic repository pattern implementation.

    Demonstrates Generic typing, Protocol usage, and abstract methods
    with complex type signatures.
    """

    @abstractmethod
    async def get(self, id: str) -> T | None:
        """Retrieve entity by ID."""
        ...

    @abstractmethod
    async def list(
        self, *, limit: int = 100, offset: int = 0
    ) -> AsyncIterator[T]:
        """List entities with pagination."""
        ...

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Save or update entity."""
        ...

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        ...


class ServiceRepository(Repository[ServiceEntity]):
    """
    Concrete repository for ServiceEntity.

    Implements all abstract methods with async generators and
    complex control flow.
    """

    def __init__(self) -> None:
        self._storage: dict[str, ServiceEntity] = {}

    async def get(self, id: str) -> ServiceEntity | None:
        """Get service by ID."""
        return self._storage.get(id)

    async def list(
        self, *, limit: int = 100, offset: int = 0
    ) -> AsyncIterator[ServiceEntity]:
        """
        Async generator listing services.

        Yields:
            ServiceEntity instances.
        """
        values = list(self._storage.values())[offset : offset + limit]
        for entity in values:
            yield entity
            await asyncio.sleep(0)  # Cooperative yield

    async def save(self, entity: ServiceEntity) -> ServiceEntity:
        """Save service to storage."""
        self._storage[entity._id] = entity
        return entity

    async def delete(self, id: str) -> bool:
        """Delete service by ID."""
        if id in self._storage:
            del self._storage[id]
            return True
        return False


# Module-level execution
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    async def main() -> None:
        """Main async entry point."""
        repo = ServiceRepository()

        async with ServiceEntity("test-service") as service:
            service.status = Status.ACTIVE
            await repo.save(service)
            print(f"Created: {service.serialize()}")

            retrieved = await repo.get(service._id)
            assert retrieved is not None

            async for s in repo.list(limit=10):
                print(f"Listed: {s}")

    asyncio.run(main())