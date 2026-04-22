/**
 * Enterprise Service Framework
 * 
 * A comprehensive demonstration of Java class hierarchies, Javadoc parsing,
 * nested structures, annotations, generics, functional interfaces, and
 * modern Java features (records, sealed classes, pattern matching).
 * 
 * @author Test Suite
 * @version 21.0
 * @since 1.0
 */
package com.enterprise.framework;

import java.io.Serializable;
import java.lang.annotation.*;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.*;
import java.util.stream.*;

/**
 * Marker annotation for framework-managed components.
 */
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD, ElementType.FIELD})
@interface Managed {
    /** Priority for initialization order. Lower values first. */
    int priority() default 100;
    
    /** Whether this component is required. */
    boolean required() default true;
}

/**
 * Annotation for transactional behavior.
 */
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
@interface Transactional {
    /** Transaction isolation level. */
    Isolation isolation() default Isolation.READ_COMMITTED;
    
    /** Timeout in seconds. */
    int timeout() default -1;
    
    /** Whether to read-only. */
    boolean readOnly() default false;
    
    /** Exception types that trigger rollback. */
    Class<? extends Exception>[] rollbackFor() default {};
    
    /** Nested enum for isolation levels. */
    enum Isolation {
        READ_UNCOMMITTED,
        READ_COMMITTED,
        REPEATABLE_READ,
        SERIALIZABLE
    }
}

/**
 * Base exception for all framework errors.
 */
class FrameworkException extends RuntimeException {
    private final String errorCode;
    private final Instant timestamp;
    
    /**
     * Constructs a new framework exception.
     * 
     * @param message the detail message
     * @param errorCode the error code
     */
    public FrameworkException(String message, String errorCode) {
        super(message);
        this.errorCode = errorCode;
        this.timestamp = Instant.now();
    }
    
    /**
     * Constructs with cause.
     * 
     * @param message the detail message
     * @param errorCode the error code
     * @param cause the underlying cause
     */
    public FrameworkException(String message, String errorCode, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.timestamp = Instant.now();
    }
    
    /** @return the error code */
    public String getErrorCode() { return errorCode; }
    
    /** @return the timestamp */
    public Instant getTimestamp() { return timestamp; }
}

/**
 * Validation exception for input errors.
 */
class ValidationException extends FrameworkException {
    private final List<String> violations;
    
    /**
     * @param message error message
     * @param violations list of validation violations
     */
    public ValidationException(String message, List<String> violations) {
        super(message, "VALIDATION_ERROR");
        this.violations = List.copyOf(violations);
    }
    
    /** @return unmodifiable list of violations */
    public List<String> getViolations() { return violations; }
}

/**
 * Abstract base for all entities in the system.
 * 
 * <p>All entities must provide:
 * <ul>
 *   <li>A unique identifier</li>
 *   <li>Audit timestamp tracking</li>
 *   <li>Serialization support</li>
 * </ul>
 * 
 * @param <T> the entity type for fluent API
 */
@Managed(priority = 1)
abstract class BaseEntity<T extends BaseEntity<T>> implements Serializable, Comparable<T> {
    
    /** Serial version UID. */
    private static final long serialVersionUID = 1L;
    
    /** Global counter for ID generation. */
    private static final AtomicLong ID_COUNTER = new AtomicLong(0);
    
    /** Entity identifier. */
    private final String id;
    
    /** Creation timestamp. */
    private final Instant createdAt;
    
    /** Last modification timestamp. */
    private volatile Instant modifiedAt;
    
    /** Optimistic locking version. */
    @Managed(required = false)
    private volatile long version;
    
    /**
     * Protected constructor for subclasses.
     * 
     * @param prefix ID prefix for type discrimination
     */
    protected BaseEntity(String prefix) {
        this.id = prefix + "-" + ID_COUNTER.incrementAndGet();
        this.createdAt = Instant.now();
        this.modifiedAt = this.createdAt;
        this.version = 0;
    }
    
    /**
     * Copy constructor.
     * 
     * @param other entity to copy
     */
    protected BaseEntity(BaseEntity<T> other) {
        this.id = other.id;
        this.createdAt = other.createdAt;
        this.modifiedAt = other.modifiedAt;
        this.version = other.version;
    }
    
    /** @return the unique identifier */
    public final String getId() { return id; }
    
    /** @return creation timestamp */
    public final Instant getCreatedAt() { return createdAt; }
    
    /** @return last modification timestamp */
    public Instant getModifiedAt() { return modifiedAt; }
    
    /** Mark entity as modified. */
    protected void touch() {
        this.modifiedAt = Instant.now();
        this.version++;
    }
    
    /**
     * Abstract method for business key extraction.
     * 
     * @return the business key
     */
    public abstract String getBusinessKey();
    
    /**
     * Template method for validation hooks.
     * 
     * @return validation result
     */
    @Managed(priority = 50)
    protected ValidationResult validate() {
        return ValidationResult.valid();
    }
    
    @Override
    public int compareTo(T other) {
        return this.createdAt.compareTo(other.getCreatedAt());
    }
    
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof BaseEntity<?> that)) return false;
        return Objects.equals(id, that.id);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
    
    @Override
    public String toString() {
        return getClass().getSimpleName() + "[id=" + id + "]";
    }
    
    /**
     * Validation result record.
     */
    record ValidationResult(boolean valid, List<String> errors) {
        static ValidationResult valid() {
            return new ValidationResult(true, List.of());
        }
        
        static ValidationResult invalid(String... errors) {
            return new ValidationResult(false, List.of(errors));
        }
    }
    
    /**
     * Builder interface for fluent construction.
     * 
     * @param <B> the builder type
     */
    protected interface Builder<B extends Builder<B>> {
        B withId(String id);
        T build();
    }
}

/**
 * Concrete entity representing a service in the system.
 * 
 * @param <T> self-referential type parameter
 */
@Managed(priority = 10)
class ServiceEntity<T extends ServiceEntity<T>> extends BaseEntity<T> {
    
    /** Service name. */
    private String name;
    
    /** Service status. */
    private ServiceStatus status;
    
    /** Service configuration. */
    private final ServiceConfig config;
    
    /** Nested registry for event listeners. */
    private final Map<String, List<Consumer<ServiceEvent>>> listeners = new ConcurrentHashMap<>();
    
    /**
     * Service status enumeration.
     */
    enum ServiceStatus {
        PENDING,
        INITIALIZING,
        ACTIVE,
        DEGRADED,
        TERMINATED
    }
    
    /**
     * Service event record.
     */
    record ServiceEvent(String type, Object payload, Instant timestamp) {
        ServiceEvent(String type, Object payload) {
            this(type, payload, Instant.now());
        }
    }
    
    /**
     * Nested configuration class.
     */
    @Managed(priority = 5)
    class ServiceConfig {
        private int timeout = 30;
        private int retries = 3;
        private boolean strictValidation = true;
        
        /** @return timeout in seconds */
        public int timeout() { return timeout; }
        
        /** @return retry count */
        public int retries() { return retries; }
        
        /** @return strict validation flag */
        public boolean strictValidation() { return strictValidation; }
        
        /**
         * Fluent setter.
         * 
         * @param timeout new timeout
         * @return this config
         */
        public ServiceConfig withTimeout(int timeout) {
            this.timeout = timeout;
            return this;
        }
    }
    
    /**
     * Private constructor enforcing builder usage.
     */
    private ServiceEntity(Builder<T> builder) {
        super("SRV");
        this.name = builder.name;
        this.status = ServiceStatus.PENDING;
        this.config = builder.config != null ? builder.config : new ServiceConfig();
    }
    
    /**
     * Static factory method.
     * 
     * @param name service name
     * @return new builder
     */
    public static <T extends ServiceEntity<T>> Builder<T> builder(String name) {
        return new Builder<>(name);
    }
    
    /** @return service name */
    public String getName() { return name; }
    
    /** @return current status */
    public ServiceStatus getStatus() { return status; }
    
    /** @return configuration */
    public ServiceConfig getConfig() { return config; }
    
    /**
     * Transition status with validation.
     * 
     * @param newStatus target status
     * @throws ValidationException if transition invalid
     */
    @Transactional(isolation = Transactional.Isolation.SERIALIZABLE)
    public synchronized void transitionTo(ServiceStatus newStatus) {
        if (!isValidTransition(this.status, newStatus)) {
            throw new ValidationException(
                "Invalid transition: " + this.status + " -> " + newStatus,
                List.of("Status transition not allowed")
            );
        }
        this.status = newStatus;
        touch();
        emitEvent("STATUS_CHANGED", newStatus);
    }
    
    private boolean isValidTransition(ServiceStatus from, ServiceStatus to) {
        return switch (from) {
            case PENDING -> to == ServiceStatus.INITIALIZING;
            case INITIALIZING -> to == ServiceStatus.ACTIVE || to == ServiceStatus.TERMINATED;
            case ACTIVE -> to == ServiceStatus.DEGRADED || to == ServiceStatus.TERMINATED;
            case DEGRADED -> to == ServiceStatus.ACTIVE || to == ServiceStatus.TERMINATED;
            case TERMINATED -> false;
        };
    }
    
    /**
     * Register event listener.
     * 
     * @param eventType event type to listen for
     * @param listener callback function
     */
    public void on(String eventType, Consumer<ServiceEvent> listener) {
        listeners.computeIfAbsent(eventType, k -> new CopyOnWriteArrayList<>()).add(listener);
    }
    
    private void emitEvent(String type, Object payload) {
        var event = new ServiceEvent(type, payload);
        listeners.getOrDefault(type, List.of()).forEach(l -> l.accept(event));
    }
    
    @Override
    public String getBusinessKey() {
        return getName() + ":" + getId();
    }
    
    /**
     * Concrete builder implementation.
     * 
     * @param <T> the built type
     */
    static class Builder<T extends ServiceEntity<T>> {
        private String name;
        private ServiceConfig config;
        
        private Builder(String name) {
            this.name = name;
        }
        
        public Builder<T> withName(String name) {
            this.name = name;
            return this;
        }
        
        public Builder<T> withConfig(ServiceConfig config) {
            this.config = config;
            return this;
        }
        
        @SuppressWarnings("unchecked")
        public T build() {
            return (T) new ServiceEntity<>(this);
        }
    }
}

/**
 * Repository interface with generic typing.
 * 
 * @param <T> entity type
 * @param <ID> identifier type
 */
interface Repository<T extends BaseEntity<T>, ID> {
    
    /**
     * Find by ID.
     * 
     * @param id the identifier
     * @return optional containing entity if found
     */
    Optional<T> findById(ID id);
    
    /**
     * Find all matching predicate.
     * 
     * @param predicate filter condition
     * @return stream of matching entities
     */
    Stream<T> findAll(Predicate<? super T> predicate);
    
    /**
     * Save entity.
     * 
     * @param entity to save
     * @return saved entity
     */
    @Transactional
    T save(T entity);
    
    /**
     * Delete by ID.
     * 
     * @param id the identifier
     */
    void deleteById(ID id);
    
    /**
     * Default method for existence check.
     * 
     * @param id the identifier
     * @return true if exists
     */
    default boolean existsById(ID id) {
        return findById(id).isPresent();
    }
}

/**
 * In-memory repository implementation.
 * 
 * @param <T> entity type
 */
class InMemoryRepository<T extends BaseEntity<T>> implements Repository<T, String> {
    
    private final Map<String, T> storage = new ConcurrentHashMap<>();
    private final List<Consumer<T>> saveListeners = new CopyOnWriteArrayList<>();
    
    @Override
    public Optional<T> findById(String id) {
        return Optional.ofNullable(storage.get(id));
    }
    
    @Override
    public Stream<T> findAll(Predicate<? super T> predicate) {
        return storage.values().stream().filter(predicate);
    }
    
    @Override
    public T save(T entity) {
        storage.put(entity.getId(), entity);
        saveListeners.forEach(l -> l.accept(entity));
        return entity;
    }
    
    @Override
    public void deleteById(String id) {
        storage.remove(id);
    }
    
    /**
     * Register save listener.
     * 
     * @param listener callback
     */
    public void addSaveListener(Consumer<T> listener) {
        saveListeners.add(listener);
    }
}

/**
 * Sealed interface for service operations (Java 17+).
 */
sealed interface ServiceOperation 
    permits ServiceOperation.Start, ServiceOperation.Stop, ServiceOperation.Restart {
    
    record Start(Map<String, Object> config) implements ServiceOperation {}
    record Stop(boolean force) implements ServiceOperation {}
    record Restart(Duration delay) implements ServiceOperation {}
}

/**
 * Service manager with pattern matching.
 */
class ServiceManager {
    
    private final Map<String, ServiceEntity<?>> services = new ConcurrentHashMap<>();
    private final ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
    
    /**
     * Execute operation with pattern matching.
     * 
     * @param serviceId target service
     * @param operation operation to perform
     * @return result future
     */
    public CompletableFuture<String> execute(String serviceId, ServiceOperation operation) {
        var service = services.get(serviceId);
        if (service == null) {
            return CompletableFuture.failedFuture(
                new FrameworkException("Service not found: " + serviceId, "NOT_FOUND")
            );
        }
        
        return switch (operation) {
            case ServiceOperation.Start start -> 
                CompletableFuture.supplyAsync(() -> {
                    service.transitionTo(ServiceEntity.ServiceStatus.INITIALIZING);
                    start.config().forEach((k, v) -> System.out.println(k + "=" + v));
                    service.transitionTo(ServiceEntity.ServiceStatus.ACTIVE);
                    return "Started " + serviceId;
                }, executor);
                
            case ServiceOperation.Stop stop -> 
                CompletableFuture.supplyAsync(() -> {
                    if (stop.force()) {
                        service.transitionTo(ServiceEntity.ServiceStatus.TERMINATED);
                    } else {
                        service.transitionTo(ServiceEntity.ServiceStatus.TERMINATED);
                    }
                    return "Stopped " + serviceId;
                }, executor);
                
            case ServiceOperation.Restart restart -> 
                execute(serviceId, new ServiceOperation.Stop(false))
                    .thenCompose(s -> {
                        try {
                            Thread.sleep(restart.delay().toMillis());
                        } catch (InterruptedException e) {
                            Thread.currentThread().interrupt();
                        }
                        return execute(serviceId, new ServiceOperation.Start(Map.of()));
                    });
        };
    }
}

/**
 * Main entry point with comprehensive feature demonstration.
 */
public class EnterpriseServiceFramework {
    
    public static void main(String[] args) {
        // Record construction
        var event = new ServiceEntity.ServiceEvent("TEST", "payload");
        System.out.println(event);
        
        // Pattern matching with instanceof
        Object obj = "test string";
        if (obj instanceof String s && s.length() > 4) {
            System.out.println(s.toUpperCase());
        }
        
        // Switch expression with arrow syntax
        var status = ServiceEntity.ServiceStatus.ACTIVE;
        var label = switch (status) {
            case PENDING, INITIALIZING -> "Not ready";
            case ACTIVE -> "Running";
            case DEGRADED -> "Degraded";
            case TERMINATED -> "Stopped";
        };
        System.out.println(label);
        
        // Lambda variations
        Function<String, Integer> lengthFn = String::length;
        Predicate<String> notEmpty = ((Predicate<String>) String::isEmpty).negate();
        Consumer<Object> printer = System.out::println;
        
        // Stream with complex pipeline
        var repo = new InMemoryRepository<ServiceEntity<?>>();
        Stream.of("svc1", "svc2", "svc3")
            .map(name -> ServiceEntity.builder(name).build())
            .peek(repo::save)
            .filter(e -> e.getName().startsWith("svc"))
            .sorted(Comparator.comparing(ServiceEntity::getCreatedAt))
            .map(ServiceEntity::getBusinessKey)
            .forEach(System.out::println);
        
        // Text blocks (Java 15+)
        var json = """
            {
                "service": "test",
                "status": "active"
            }
            """;
        System.out.println(json);
        
        // Var in lambda parameters (Java 11+)
        var sum = (var a, var b) -> a + b;
        System.out.println(sum.apply(1, 2));
    }
}