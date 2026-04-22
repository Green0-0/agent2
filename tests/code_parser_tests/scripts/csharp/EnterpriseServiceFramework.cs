using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.ComponentModel;
using System.Diagnostics;
using System.Diagnostics.CodeAnalysis;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;

namespace Enterprise.Framework
{
    /// <summary>
    /// Framework version information.
    /// </summary>
    public readonly record struct FrameworkVersion(int Major, int Minor, int Patch)
    {
        /// <summary>
        /// Parse from version string.
        /// </summary>
        public static FrameworkVersion Parse(string version)
        {
            var parts = version.Split('.');
            return new FrameworkVersion(
                int.Parse(parts[0]),
                int.Parse(parts[1]),
                int.Parse(parts[2])
            );
        }

        /// <inheritdoc/>
        public override string ToString() => $"{Major}.{Minor}.{Patch}";
    }

    /// <summary>
    /// Attribute marking a service as managed by the framework.
    /// </summary>
    [AttributeUsage(AttributeTargets.Class | AttributeTargets.Interface | AttributeTargets.Method)]
    public sealed class ManagedAttribute : Attribute
    {
        /// <summary>
        /// Priority for initialization order.
        /// </summary>
        public int Priority { get; init; } = 100;

        /// <summary>
        /// Whether this service is required.
        /// </summary>
        public bool Required { get; init; } = true;

        /// <summary>
        /// Optional service category.
        /// </summary>
        public string? Category { get; init; }
    }

    /// <summary>
    /// Attribute for unit of work behavior.
    /// </summary>
    [AttributeUsage(AttributeTargets.Method)]
    public sealed class TransactionalAttribute : Attribute
    {
        /// <summary>
        /// Isolation level.
        /// </summary>
        public IsolationLevel Isolation { get; init; } = IsolationLevel.ReadCommitted;

        /// <summary>
        /// Timeout in seconds.
        /// </summary>
        public int Timeout { get; init; } = -1;

        /// <summary>
        /// Whether read-only.
        /// </summary>
        public bool ReadOnly { get; init; }

        /// <summary>
        /// Exception types that trigger rollback.
        /// </summary>
        public Type[] RollbackFor { get; init; } = Array.Empty<Type>();
    }

    /// <summary>
    /// Transaction isolation levels.
    /// </summary>
    public enum IsolationLevel
    {
        ReadUncommitted,
        ReadCommitted,
        RepeatableRead,
        Serializable
    }

    /// <summary>
    /// Base exception for all framework errors.
    /// </summary>
    public abstract class FrameworkException : Exception
    {
        /// <summary>
        /// Error code.
        /// </summary>
        public string ErrorCode { get; }

        /// <summary>
        /// Timestamp when exception occurred.
        /// </summary>
        public DateTimeOffset Timestamp { get; }

        /// <summary>
        /// Constructs exception.
        /// </summary>
        /// <param name="message">Detail message.</param>
        /// <param name="errorCode">Error code.</param>
        protected FrameworkException(string message, string errorCode)
            : base(message)
        {
            ErrorCode = errorCode;
            Timestamp = DateTimeOffset.UtcNow;
        }

        /// <summary>
        /// Constructs with inner exception.
        /// </summary>
        /// <param name="message">Detail message.</param>
        /// <param name="errorCode">Error code.</param>
        /// <param name="innerException">Underlying cause.</param>
        protected FrameworkException(string message, string errorCode, Exception innerException)
            : base(message, innerException)
        {
            ErrorCode = errorCode;
            Timestamp = DateTimeOffset.UtcNow;
        }
    }

    /// <summary>
    /// Validation exception with multiple violations.
    /// </summary>
    public sealed class ValidationException : FrameworkException
    {
        /// <summary>
        /// Validation violations.
        /// </summary>
        public IReadOnlyList<string> Violations { get; }

        /// <summary>
        /// Constructs validation exception.
        /// </summary>
        public ValidationException(string message, IEnumerable<string> violations)
            : base(message, "VALIDATION_ERROR")
        {
            Violations = violations.ToImmutableList();
        }
    }

    /// <summary>
    /// Entity not found exception.
    /// </summary>
    public sealed class NotFoundException : FrameworkException
    {
        /// <summary>
        /// Entity identifier.
        /// </summary>
        public string EntityId { get; }

        /// <summary>
        /// Entity type.
        /// </summary>
        public Type EntityType { get; }

        public NotFoundException(string entityId, Type entityType)
            : base($"Entity not found: {entityId}", "NOT_FOUND")
        {
            EntityId = entityId;
            EntityType = entityType;
        }
    }

    /// <summary>
    /// Abstract base for all entities with self-referential generic type.
    /// </summary>
    /// <typeparam name="T">The derived entity type.</typeparam>
    [Managed(Priority = 1, Required = true)]
    public abstract class BaseEntity<T> : IEquatable<T>, IComparable<T>
        where T : BaseEntity<T>
    {
        private static long _idCounter;

        /// <summary>
        /// Unique identifier.
        /// </summary>
        public string Id { get; }

        /// <summary>
        /// Creation timestamp.
        /// </summary>
        public DateTimeOffset CreatedAt { get; }

        /// <summary>
        /// Last modification timestamp.
        /// </summary>
        public DateTimeOffset? ModifiedAt { get; private set; }

        /// <summary>
        /// Optimistic concurrency version.
        /// </summary>
        public long Version { get; private set; }

        /// <summary>
        /// Protected constructor.
        /// </summary>
        /// <param name="prefix">ID prefix for type discrimination.</param>
        protected BaseEntity(string prefix)
        {
            Id = $"{prefix}-{Interlocked.Increment(ref _idCounter)}";
            CreatedAt = DateTimeOffset.UtcNow;
            Version = 0;
        }

        /// <summary>
        /// Copy constructor.
        /// </summary>
        protected BaseEntity(BaseEntity<T> other)
        {
            Id = other.Id;
            CreatedAt = other.CreatedAt;
            ModifiedAt = other.ModifiedAt;
            Version = other.Version;
        }

        /// <summary>
        /// Business key for equality.
        /// </summary>
        public abstract string BusinessKey { get; }

        /// <summary>
        /// Mark entity as modified.
        /// </summary>
        protected void Touch()
        {
            ModifiedAt = DateTimeOffset.UtcNow;
            Version++;
        }

        /// <summary>
        /// Validate entity state.
        /// </summary>
        /// <returns>Validation result.</returns>
        public virtual ValidationResult Validate() => ValidationResult.Success;

        /// <inheritdoc/>
        public int CompareTo(T? other) => other is null ? 1 : CreatedAt.CompareTo(other.CreatedAt);

        /// <inheritdoc/>
        public bool Equals(T? other) => other is not null && Id == other.Id;

        /// <inheritdoc/>
        public override bool Equals(object? obj) => Equals(obj as T);

        /// <inheritdoc/>
        public override int GetHashCode() => Id.GetHashCode();

        /// <inheritdoc/>
        public override string ToString() => $"{GetType().Name}[{Id}]";

        /// <summary>
        /// Validation result record.
        /// </summary>
        public readonly record struct ValidationResult(bool IsValid, ImmutableList<string> Errors)
        {
            /// <summary>
            /// Successful validation.
            /// </summary>
            public static ValidationResult Success => new(true, ImmutableList<string>.Empty);

            /// <summary>
            /// Failed validation.
            /// </summary>
            public static ValidationResult Failure(params string[] errors) => new(false, errors.ToImmutableList());
        }

        /// <summary>
        /// Builder interface for fluent construction.
        /// </summary>
        /// <typeparam name="TBuilder">Concrete builder type.</typeparam>
        protected interface IBuilder<TBuilder> where TBuilder : IBuilder<TBuilder>
        {
            TBuilder WithId(string id);
            T Build();
        }
    }

    /// <summary>
    /// Service status enumeration.
    /// </summary>
    public enum ServiceStatus
    {
        Pending,
        Initializing,
        Active,
        Degraded,
        Terminated
    }

    /// <summary>
    /// Service event record.
    /// </summary>
    /// <param name="Type">Event type.</param>
    /// <param name="Payload">Event payload.</param>
    /// <param name="Timestamp">Event timestamp.</param>
    public sealed record ServiceEvent(string Type, object? Payload, DateTimeOffset Timestamp)
    {
        /// <summary>
        /// Convenience constructor with current timestamp.
        /// </summary>
        public ServiceEvent(string type, object? payload) : this(type, payload, DateTimeOffset.UtcNow) { }
    }

    /// <summary>
    /// Concrete service entity with nested types.
    /// </summary>
    /// <typeparam name="T">Self-referential type.</typeparam>
    [Managed(Priority = 10, Category = "Core")]
    public class ServiceEntity<T> : BaseEntity<T>
        where T : ServiceEntity<T>
    {
        /// <summary>
        /// Nested configuration class.
        /// </summary>
        public sealed class ServiceConfig
        {
            /// <summary>
            /// Timeout in seconds.
            /// </summary>
            public int Timeout { get; init; } = 30;

            /// <summary>
            /// Retry count.
            /// </summary>
            public int Retries { get; init; } = 3;

            /// <summary>
            /// Strict validation flag.
            /// </summary>
            public bool StrictValidation { get; init; } = true;

            /// <summary>
            /// Fluent timeout setter.
            /// </summary>
            public ServiceConfig WithTimeout(int timeout) => this with { Timeout = timeout };
        }

        /// <summary>
        /// Service event handler delegate.
        /// </summary>
        /// <param name="sender">Event source.</param>
        /// <param name="event">Event data.</param>
        public delegate void ServiceEventHandler(ServiceEntity<T> sender, ServiceEvent @event);

        private readonly Dictionary<string, List<ServiceEventHandler>> _listeners = new();
        private ServiceStatus _status;

        /// <summary>
        /// Service name.
        /// </summary>
        public string Name { get; private set; }

        /// <summary>
        /// Current status.
        /// </summary>
        public ServiceStatus Status
        {
            get => _status;
            private set
            {
                if (_status != value)
                {
                    _status = value;
                    Touch();
                    EmitEvent("STATUS_CHANGED", value);
                }
            }
        }

        /// <summary>
        /// Configuration.
        /// </summary>
        public ServiceConfig Config { get; }

        /// <inheritdoc/>
        public override string BusinessKey => $"{Name}:{Id}";

        /// <summary>
        /// Status changed event.
        /// </summary>
        public event ServiceEventHandler? StatusChanged;

        /// <summary>
        /// Private constructor.
        /// </summary>
        private ServiceEntity(Builder builder)
            : base("SRV")
        {
            Name = builder.Name;
            Config = builder.Config ?? new ServiceConfig();
            _status = ServiceStatus.Pending;
        }

        /// <summary>
        /// Create builder.
        /// </summary>
        public static Builder CreateBuilder(string name) => new(name);

        /// <summary>
        /// Transition status with validation.
        /// </summary>
        /// <param name="newStatus">Target status.</param>
        /// <exception cref="ValidationException">If transition invalid.</exception>
        [Transactional(Isolation = IsolationLevel.Serializable)]
        public void TransitionTo(ServiceStatus newStatus)
        {
            if (!IsValidTransition(_status, newStatus))
            {
                throw new ValidationException(
                    $"Invalid transition: {_status} -> {newStatus}",
                    new[] { "Status transition not allowed" }
                );
            }

            Status = newStatus;
        }

        private static bool IsValidTransition(ServiceStatus from, ServiceStatus to) => (from, to) switch
        {
            (ServiceStatus.Pending, ServiceStatus.Initializing) => true,
            (ServiceStatus.Initializing, ServiceStatus.Active) => true,
            (ServiceStatus.Initializing, ServiceStatus.Terminated) => true,
            (ServiceStatus.Active, ServiceStatus.Degraded) => true,
            (ServiceStatus.Active, ServiceStatus.Terminated) => true,
            (ServiceStatus.Degraded, ServiceStatus.Active) => true,
            (ServiceStatus.Degraded, ServiceStatus.Terminated) => true,
            _ => false
        };

        /// <summary>
        /// Register event handler.
        /// </summary>
        public void On(string eventType, ServiceEventHandler handler)
        {
            if (!_listeners.TryGetValue(eventType, out var handlers))
            {
                handlers = new List<ServiceEventHandler>();
                _listeners[eventType] = handlers;
            }
            handlers.Add(handler);
        }

        private void EmitEvent(string type, object? payload)
        {
            var evt = new ServiceEvent(type, payload);
            if (_listeners.TryGetValue(type, out var handlers))
            {
                foreach (var handler in handlers)
                {
                    try
                    {
                        handler(this, evt);
                    }
                    catch (Exception ex)
                    {
                        Debug.WriteLine($"Handler error: {ex}");
                    }
                }
            }
            StatusChanged?.Invoke(this, evt);
        }

        /// <inheritdoc/>
        public override ValidationResult Validate()
        {
            var errors = new List<string>();
            if (string.IsNullOrWhiteSpace(Name))
                errors.Add("Name is required");

            return errors.Count > 0
                ? ValidationResult.Failure(errors.ToArray())
                : ValidationResult.Success;
        }

        /// <summary>
        /// Builder class.
        /// </summary>
        public sealed class Builder
        {
            internal string Name { get; }
            internal ServiceConfig? Config { get; private set; }

            internal Builder(string name)
            {
                Name = name;
            }

            public Builder WithConfig(ServiceConfig config)
            {
                Config = config;
                return this;
            }

            public T Build() => (T)new ServiceEntity<T>(this);
        }
    }

    /// <summary>
    /// Generic repository interface with variance.
    /// </summary>
    /// <typeparam name="T">Entity type.</typeparam>
    /// <typeparam name="TId">Identifier type.</typeparam>
    public interface IRepository<in TId, T>
        where T : BaseEntity<T>
    {
        /// <summary>
        /// Find by ID.
        /// </summary>
        Task<T?> FindByIdAsync(TId id, CancellationToken cancellationToken = default);

        /// <summary>
        /// Find all matching predicate.
        /// </summary>
        IAsyncEnumerable<T> FindAllAsync(Func<T, bool> predicate, CancellationToken cancellationToken = default);

        /// <summary>
        /// Save entity.
        /// </summary>
        [Transactional]
        Task<T> SaveAsync(T entity, CancellationToken cancellationToken = default);

        /// <summary>
        /// Delete by ID.
        /// </summary>
        Task DeleteAsync(TId id, CancellationToken cancellationToken = default);

        /// <summary>
        /// Check existence.
        /// </summary>
        Task<bool> ExistsAsync(TId id, CancellationToken cancellationToken = default);
    }

    /// <summary>
    /// In-memory repository implementation.
    /// </summary>
    /// <typeparam name="T">Entity type.</typeparam>
    public sealed class InMemoryRepository<T> : IRepository<string, T>, IDisposable
        where T : BaseEntity<T>
    {
        private readonly Dictionary<string, T> _storage = new();
        private readonly ReaderWriterLockSlim _lock = new();
        private bool _disposed;

        /// <inheritdoc/>
        public Task<T?> FindByIdAsync(string id, CancellationToken cancellationToken = default)
        {
            _lock.EnterReadLock();
            try
            {
                _storage.TryGetValue(id, out var entity);
                return Task.FromResult(entity);
            }
            finally
            {
                _lock.ExitReadLock();
            }
        }

        /// <inheritdoc/>
        public async IAsyncEnumerable<T> FindAllAsync(
            Func<T, bool> predicate,
            [EnumeratorCancellation] CancellationToken cancellationToken = default)
        {
            T[] snapshot;
            _lock.EnterReadLock();
            try
            {
                snapshot = _storage.Values.Where(predicate).ToArray();
            }
            finally
            {
                _lock.ExitReadLock();
            }

            foreach (var entity in snapshot)
            {
                cancellationToken.ThrowIfCancellationRequested();
                yield return entity;
                await Task.Yield();
            }
        }

        /// <inheritdoc/>
        public Task<T> SaveAsync(T entity, CancellationToken cancellationToken = default)
        {
            _lock.EnterWriteLock();
            try
            {
                _storage[entity.Id] = entity;
                return Task.FromResult(entity);
            }
            finally
            {
                _lock.ExitWriteLock();
            }
        }

        /// <inheritdoc/>
        public Task DeleteAsync(string id, CancellationToken cancellationToken = default)
        {
            _lock.EnterWriteLock();
            try
            {
                _storage.Remove(id);
                return Task.CompletedTask;
            }
            finally
            {
                _lock.ExitWriteLock();
            }
        }

        /// <inheritdoc/>
        public Task<bool> ExistsAsync(string id, CancellationToken cancellationToken = default)
        {
            _lock.EnterReadLock();
            try
            {
                return Task.FromResult(_storage.ContainsKey(id));
            }
            finally
            {
                _lock.ExitReadLock();
            }
        }

        /// <inheritdoc/>
        public void Dispose()
        {
            if (_disposed) return;
            _lock.Dispose();
            _disposed = true;
        }
    }

    /// <summary>
    /// Sealed service operation hierarchy.
    /// </summary>
    public abstract record ServiceOperation
    {
        public sealed record Start(Dictionary<string, object> Config) : ServiceOperation;
        public sealed record Stop(bool Force) : ServiceOperation;
        public sealed record Restart(TimeSpan Delay) : ServiceOperation;
    }

    /// <summary>
    /// Service manager with pattern matching.
    /// </summary>
    public sealed class ServiceManager
    {
        private readonly Dictionary<string, ServiceEntity<ServiceEntity<object>>> _services = new();
        private readonly Channel<ServiceOperation> _operationChannel;

        public ServiceManager()
        {
            _operationChannel = Channel.CreateUnbounded<ServiceOperation>();
        }

        /// <summary>
        /// Execute operation with pattern matching.
        /// </summary>
        public async Task<string> ExecuteAsync(string serviceId, ServiceOperation operation, CancellationToken ct = default)
        {
            if (!_services.TryGetValue(serviceId, out var service))
            {
                throw new NotFoundException(serviceId, typeof(ServiceEntity<>));
            }

            return operation switch
            {
                ServiceOperation.Start start => await HandleStartAsync(service, start, ct),
                ServiceOperation.Stop stop => await HandleStopAsync(service, stop, ct),
                ServiceOperation.Restart restart => await HandleRestartAsync(service, restart, ct),
                _ => throw new FrameworkException("Unknown operation", "INVALID_OPERATION")
            };
        }

        private static async Task<string> HandleStartAsync(
            ServiceEntity<ServiceEntity<object>> service,
            ServiceOperation.Start start,
            CancellationToken ct)
        {
            service.TransitionTo(ServiceStatus.Initializing);
            foreach (var (key, value) in start.Config)
            {
                Debug.WriteLine($"{key}={value}");
            }
            await Task.Delay(100, ct);
            service.TransitionTo(ServiceStatus.Active);
            return $"Started {service.BusinessKey}";
        }

        private static async Task<string> HandleStopAsync(
            ServiceEntity<ServiceEntity<object>> service,
            ServiceOperation.Stop stop,
            CancellationToken ct)
        {
            if (stop.Force)
            {
                service.TransitionTo(ServiceStatus.Terminated);
            }
            else
            {
                await Task.Delay(500, ct);
                service.TransitionTo(ServiceStatus.Terminated);
            }
            return $"Stopped {service.BusinessKey}";
        }

        private static async Task<string> HandleRestartAsync(
            ServiceEntity<ServiceEntity<object>> service,
            ServiceOperation.Restart restart,
            CancellationToken ct)
        {
            await HandleStopAsync(service, new ServiceOperation.Stop(false), ct);
            await Task.Delay(restart.Delay, ct);
            return await HandleStartAsync(service, new ServiceOperation.Start(new()), ct);
        }
    }

    /// <summary>
    /// Program entry point.
    /// </summary>
    public static class Program
    {
        public static async Task Main(string[] args)
        {
            // Record construction
            var version = new FrameworkVersion(1, 0, 0);
            Console.WriteLine(version);

            // Pattern matching with is
            object obj = "test string";
            if (obj is string s && s.Length > 4)
            {
                Console.WriteLine(s.ToUpperInvariant());
            }

            // Switch expression
            var status = ServiceStatus.Active;
            var label = status switch
            {
                ServiceStatus.Pending or ServiceStatus.Initializing => "Not ready",
                ServiceStatus.Active => "Running",
                ServiceStatus.Degraded => "Degraded",
                ServiceStatus.Terminated => "Stopped",
                _ => "Unknown"
            };
            Console.WriteLine(label);

            // Property patterns
            var point = new { X = 1, Y = 2 };
            var isOrigin = point is { X: 0, Y: 0 };

            // List patterns
            var numbers = new[] { 1, 2, 3 };
            var isTriple = numbers is [_, _, _];

            // Lambda variations
            Func<string, int> lengthFn = s => s.Length;
            Predicate<string> notEmpty = s => !string.IsNullOrEmpty(s);
            Func<int, int, int> add = (a, b) => a + b;

            // Async lambda
            Func<Task<int>> asyncLambda = async () =>
            {
                await Task.Delay(100);
                return 42;
            };

            // LINQ query syntax
            var query = from x in Enumerable.Range(1, 100)
                        where x % 2 == 0
                        orderby x descending
                        group x by x % 10 into g
                        where g.Count() > 4
                        select new { Remainder = g.Key, Count = g.Count(), Max = g.Max() };

            foreach (var item in query)
            {
                Console.WriteLine(item);
            }

            // LINQ method syntax with complex pipeline
            var result = Enumerable.Range(1, 1000)
                .AsParallel()
                .Where(n => n % 3 == 0)
                .Select(n => n * n)
                .Aggregate((acc, n) => acc + n);

            Console.WriteLine(result);

            // Async enumerable
            await foreach (var n in GetNumbersAsync(10))
            {
                Console.WriteLine(n);
            }

            // Using declaration
            using var repo = new InMemoryRepository<ServiceEntity<ServiceEntity<object>>>();

            // Nullable operations
            string? maybe = GetMaybe();
            var length = maybe?.Length ?? 0;

            // Target-typed new
            List<int> list = new();
            Dictionary<string, int> dict = new()
            {
                ["one"] = 1,
                ["two"] = 2
            };

            // With expressions
            var config = new ServiceEntity<ServiceEntity<object>>.ServiceConfig { Timeout = 30 };
            var modified = config with { Timeout = 60 };

            Console.WriteLine(modified);
        }

        private static string? GetMaybe() => null;

        private static async IAsyncEnumerable<int> GetNumbersAsync(int count, [EnumeratorCancellation] CancellationToken ct = default)
        {
            for (int i = 0; i < count; i++)
            {
                ct.ThrowIfCancellationRequested();
                await Task.Delay(10, ct);
                yield return i;
            }
        }
    }
}