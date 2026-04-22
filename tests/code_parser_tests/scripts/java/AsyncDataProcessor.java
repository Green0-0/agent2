/**
 * Async Data Processor
 * 
 * Exhaustive coverage of Java functional programming, async patterns,
 * generics with wildcards, and stream operations.
 */

package com.enterprise.async;

import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.function.*;
import java.util.stream.*;

/**
 * Functional interface with generics and default methods.
 * 
 * @param <T> input type
 * @param <R> output type
 */
@FunctionalInterface
interface Processor<T, R> {
    
    /**
     * Process a single item.
     * 
     * @param item the input
     * @return the processed result
     */
    R process(T item);
    
    /**
     * Compose with another processor.
     * 
     * @param <V> final output type
     * @param after next processor
     * @return composed processor
     */
    default <V> Processor<T, V> andThen(Processor<? super R, ? extends V> after) {
        return item -> after.process(process(item));
    }
    
    /**
     * Convert to async version.
     * 
     * @return async processor
     */
    default AsyncProcessor<T, R> async() {
        return item -> CompletableFuture.supplyAsync(() -> process(item));
    }
    
    /**
     * Static factory for identity processor.
     * 
     * @param <T> the type
     * @return identity processor
     */
    static <T> Processor<T, T> identity() {
        return item -> item;
    }
}

/**
 * Async variant of processor.
 * 
 * @param <T> input type
 * @param <R> output type
 */
@FunctionalInterface
interface AsyncProcessor<T, R> {
    
    /**
     * Async process method.
     * 
     * @param item the input
     * @return future result
     */
    CompletableFuture<R> process(T item);
    
    /**
     * Compose async processors.
     */
    default <V> AsyncProcessor<T, V> andThen(AsyncProcessor<? super R, ? extends V> after) {
        return item -> process(item).thenCompose(after::process);
    }
    
    /**
     * Convert to parallel stream processor.
     */
    default ParallelProcessor<T, R> parallel() {
        return items -> items.parallelStream()
            .map(this::process)
            .map(CompletableFuture::join)
            .toList();
    }
}

/**
 * Parallel batch processor.
 * 
 * @param <T> input type
 * @param <R> output type
 */
@FunctionalInterface
interface ParallelProcessor<T, R> {
    
    /**
     * Process collection in parallel.
     * 
     * @param items input collection
     * @return processed results
     */
    List<R> process(Collection<T> items);
}

/**
 * Data record with validation.
 * 
 * @param id unique identifier
 * @param payload data payload
 * @param metadata optional metadata
 */
record DataRecord(String id, Map<String, Object> payload, Optional<Map<String, String>> metadata) {
    
    /**
     * Compact constructor for validation.
     */
    public DataRecord {
        Objects.requireNonNull(id, "ID cannot be null");
        Objects.requireNonNull(payload, "Payload cannot be null");
        payload = Map.copyOf(payload);
    }
    
    /**
     * Factory without metadata.
     */
    public static DataRecord of(String id, Map<String, Object> payload) {
        return new DataRecord(id, payload, Optional.empty());
    }
    
    /**
     * Get typed value from payload.
     */
    public <T> Optional<T> get(String key, Class<T> type) {
        return Optional.ofNullable(payload.get(key))
            .filter(type::isInstance)
            .map(type::cast);
    }
}

/**
 * Pipeline stage with type-safe chaining.
 * 
 * @param <I> input type
 * @param <O> output type
 */
class PipelineStage<I, O> {
    
    private final String name;
    private final Processor<I, O> processor;
    private final List<Consumer<O>> listeners = new ArrayList<>();
    private volatile boolean enabled = true;
    
    public PipelineStage(String name, Processor<I, O> processor) {
        this.name = name;
        this.processor = processor;
    }
    
    public String getName() { return name; }
    
    public boolean isEnabled() { return enabled; }
    
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
    
    public O process(I input) {
        if (!enabled) {
            throw new IllegalStateException("Stage " + name + " is disabled");
        }
        var result = processor.process(input);
        listeners.forEach(l -> l.accept(result));
        return result;
    }
    
    public void addListener(Consumer<O> listener) {
        listeners.add(listener);
    }
    
    /**
     * Chain to next stage.
     */
    public <V> PipelineStage<I, V> then(String name, Processor<? super O, ? extends V> next) {
        return new PipelineStage<>(name, processor.andThen(next));
    }
}

/**
 * Async pipeline with backpressure.
 * 
 * @param <T> input type
 * @param <R> final output type
 */
class AsyncPipeline<T, R> {
    
    private final List<PipelineStage<?, ?>> stages = new ArrayList<>();
    private final ExecutorService executor;
    private final BlockingQueue<T> inputQueue;
    private final AtomicBoolean running = new AtomicBoolean(false);
    
    public AsyncPipeline(int capacity, ExecutorService executor) {
        this.executor = executor;
        this.inputQueue = new LinkedBlockingQueue<>(capacity);
    }
    
    /**
     * Add stage with type erasure for storage.
     */
    @SuppressWarnings("unchecked")
    public <I, O> AsyncPipeline<T, R> addStage(String name, Processor<I, O> processor) {
        stages.add(new PipelineStage<>(name, processor));
        return this;
    }
    
    /**
     * Submit item for processing.
     */
    public CompletableFuture<R> submit(T item) throws InterruptedException {
        inputQueue.put(item);
        return CompletableFuture.supplyAsync(() -> {
            try {
                var current = (Object) inputQueue.take();
                for (var stage : stages) {
                    current = ((PipelineStage<Object, Object>) stage).process(current);
                }
                return (R) current;
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new CompletionException(e);
            }
        }, executor);
    }
    
    /**
     * Start consuming with backpressure.
     */
    public void start() {
        if (running.compareAndSet(false, true)) {
            executor.submit(() -> {
                while (running.get()) {
                    try {
                        var item = inputQueue.poll(100, TimeUnit.MILLISECONDS);
                        if (item != null) {
                            submit(item);
                        }
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        break;
                    }
                }
            });
        }
    }
    
    public void stop() {
        running.set(false);
    }
}

/**
 * Complex stream operations demonstration.
 */
class StreamOperations {
    
    /**
     * Flat map with nested streams.
     */
    public static <T, R> List<R> flatMapDeep(
        List<List<List<T>>> nested,
        Function<? super T, ? extends R> mapper
    ) {
        return nested.stream()
            .flatMap(List::stream)
            .flatMap(List::stream)
            .map(mapper)
            .toList();
    }
    
    /**
     * Collect with custom collector.
     */
    public static <T> Map<String, List<T>> groupByProperty(
        List<T> items,
        Function<? super T, String> classifier
    ) {
        return items.stream()
            .collect(Collectors.groupingBy(
                classifier,
                LinkedHashMap::new,
                Collectors.toList()
            ));
    }
    
    /**
     * Reduce with identity and combiner.
     */
    public static <T> T parallelReduce(
        List<T> items,
        T identity,
        BinaryOperator<T> accumulator,
        BinaryOperator<T> combiner
    ) {
        return items.parallelStream()
            .reduce(identity, accumulator, combiner);
    }
    
    /**
     * Teeing collector (Java 12+).
     */
    public static <T> Map<String, Object> statistics(
        List<T> items,
        ToDoubleFunction<? super T> extractor
    ) {
        return items.stream()
            .collect(Collectors.teeing(
                Collectors.summarizingDouble(extractor),
                Collectors.counting(),
                (stats, count) -> Map.of(
                    "count", count,
                    "sum", stats.getSum(),
                    "avg", stats.getAverage(),
                    "min", stats.getMin(),
                    "max", stats.getMax()
                )
            ));
    }
}

/**
 * Concurrent utilities demonstration.
 */
class ConcurrentUtils {
    
    /**
     * Phaser for complex coordination.
     */
    public static void phasedExecution(
        List<Runnable> phases,
        int parallelism
    ) throws InterruptedException {
        var phaser = new Phaser(1);
        var executor = Executors.newFixedThreadPool(parallelism);
        
        for (var phase : phases) {
            phaser.arriveAndAwaitAdvance();
            executor.submit(() -> {
                phase.run();
                phaser.arrive();
            });
        }
        
        phaser.arriveAndDeregister();
        executor.shutdown();
        executor.awaitTermination(1, TimeUnit.MINUTES);
    }
    
    /**
     * StampedLock for optimistic reading.
     */
    public static class OptimisticCounter {
        private final StampedLock lock = new StampedLock();
        private long value = 0;
        
        public long increment() {
            long stamp = lock.writeLock();
            try {
                return ++value;
            } finally {
                lock.unlockWrite(stamp);
            }
        }
        
        public long get() {
            long stamp = lock.tryOptimisticRead();
            long current = value;
            if (!lock.validate(stamp)) {
                stamp = lock.readLock();
                try {
                    current = value;
                } finally {
                    lock.unlockRead(stamp);
                }
            }
            return current;
        }
    }
    
    /**
     * CompletableFuture composition patterns.
     */
    public static CompletableFuture<String> composedAsync(
        String input,
        ExecutorService executor
    ) {
        return CompletableFuture.supplyAsync(() -> input.toUpperCase(), executor)
            .thenApply(s -> s + "-PROCESSED")
            .thenCompose(s -> CompletableFuture.supplyAsync(() -> s + "-SAVED", executor))
            .thenApplyAsync(s -> "RESULT: " + s, executor)
            .exceptionally(ex -> "ERROR: " + ex.getMessage());
    }
}

/**
 * Main demonstration.
 */
public class AsyncDataProcessor {
    
    public static void main(String[] args) throws Exception {
        // Processor chaining
        Processor<String, Integer> parseInt = Integer::parseInt;
        Processor<Integer, Double> halve = i -> i / 2.0;
        var combined = parseInt.andThen(halve);
        
        System.out.println(combined.process("42"));
        
        // Async pipeline
        var executor = Executors.newVirtualThreadPerTaskExecutor();
        var pipeline = new AsyncPipeline<String, Double>(100, executor)
            .addStage("parse", parseInt)
            .addStage("halve", halve);
        
        pipeline.start();
        
        var future = pipeline.submit("100");
        System.out.println(future.get());
        
        pipeline.stop();
        executor.shutdown();
        
        // Stream operations
        var nested = List.of(
            List.of(List.of(1, 2), List.of(3, 4)),
            List.of(List.of(5, 6), List.of(7, 8))
        );
        var flat = StreamOperations.flatMapDeep(nested, x -> x * 2);
        System.out.println(flat);
        
        // Concurrent operations
        var counter = new ConcurrentUtils.OptimisticCounter();
        var threads = IntStream.range(0, 100)
            .mapToObj(i -> Thread.ofVirtual().start(counter::increment))
            .toList();
        
        for (var t : threads) t.join();
        System.out.println("Final count: " + counter.get());
    }
}