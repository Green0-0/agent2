using System;
using System.Buffers;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Channels;
using System.Threading.Tasks;

namespace Enterprise.Pipeline
{
    /// <summary>
    /// Generic processor interface.
    /// </summary>
    /// <typeparam name="TInput">Input type.</typeparam>
    /// <typeparam name="TOutput">Output type.</typeparam>
    public interface IProcessor<in TInput, TOutput>
    {
        /// <summary>
        /// Process single item.
        /// </summary>
        TOutput Process(TInput item);

        /// <summary>
        /// Async process single item.
        /// </summary>
        ValueTask<TOutput> ProcessAsync(TInput item, CancellationToken ct = default);
    }

    /// <summary>
    /// Pipeline stage with composition.
    /// </summary>
    /// <typeparam name="TInput">Input type.</typeparam>
    /// <typeparam name="TOutput">Output type.</typeparam>
    public sealed class PipelineStage<TInput, TOutput> : IProcessor<TInput, TOutput>
    {
        private readonly Func<TInput, TOutput> _syncProcessor;
        private readonly Func<TInput, CancellationToken, ValueTask<TOutput>>? _asyncProcessor;
        private readonly List<Func<TOutput, Task>> _listeners = new();

        /// <summary>
        /// Stage name.
        /// </summary>
        public string Name { get; }

        /// <summary>
        /// Whether stage is enabled.
        /// </summary>
        public bool IsEnabled { get; set; } = true;

        public PipelineStage(string name, Func<TInput, TOutput> processor)
        {
            Name = name;
            _syncProcessor = processor;
        }

        public PipelineStage(string name, Func<TInput, CancellationToken, ValueTask<TOutput>> processor)
        {
            Name = name;
            _asyncProcessor = processor;
            _syncProcessor = input => throw new InvalidOperationException("Use async method");
        }

        /// <summary>
        /// Add output listener.
        /// </summary>
        public void AddListener(Func<TOutput, Task> listener) => _listeners.Add(listener);

        /// <inheritdoc/>
        public TOutput Process(TInput item)
        {
            if (!IsEnabled) throw new InvalidOperationException($"Stage {Name} disabled");
            var result = _syncProcessor(item);
            NotifyListeners(result);
            return result;
        }

        /// <inheritdoc/>
        public async ValueTask<TOutput> ProcessAsync(TInput item, CancellationToken ct = default)
        {
            if (!IsEnabled) throw new InvalidOperationException($"Stage {Name} disabled");
            var result = _asyncProcessor is not null
                ? await _asyncProcessor(item, ct)
                : _syncProcessor(item);
            await NotifyListenersAsync(result, ct);
            return result;
        }

        private void NotifyListeners(TOutput result)
        {
            foreach (var listener in _listeners)
            {
                listener(result).GetAwaiter().GetResult();
            }
        }

        private async Task NotifyListenersAsync(TOutput result, CancellationToken ct)
        {
            foreach (var listener in _listeners)
            {
                await listener(result);
            }
        }

        /// <summary>
        /// Compose with next stage.
        /// </summary>
        public PipelineStage<TInput, TNext> Then<TNext>(PipelineStage<TOutput, TNext> next) =>
            new($"{Name}->{next.Name}", input => next.Process(Process(input)));

        /// <summary>
        /// Async compose.
        /// </summary>
        public PipelineStage<TInput, TNext> ThenAsync<TNext>(
            PipelineStage<TOutput, TNext> next) =>
            new($"{Name}->{next.Name}",
                async (input, ct) => await next.ProcessAsync(await ProcessAsync(input, ct), ct));
    }

    /// <summary>
    /// Async pipeline with backpressure.
    /// </summary>
    /// <typeparam name="TInput">Input type.</typeparam>
    /// <typeparam name="TOutput">Output type.</typeparam>
    public sealed class AsyncPipeline<TInput, TOutput> : IAsyncDisposable
    {
        private readonly Channel<TInput> _inputChannel;
        private readonly List<object> _stages = new();
        private readonly CancellationTokenSource _cts = new();
        private Task? _processingTask;
        private bool _started;

        public AsyncPipeline(int capacity)
        {
            _inputChannel = Channel.CreateBounded<TInput>(new BoundedChannelOptions(capacity)
            {
                FullMode = BoundedChannelFullMode.Wait
            });
        }

        /// <summary>
        /// Add sync stage.
        /// </summary>
        public AsyncPipeline<TInput, TOutput> AddStage<TIntermediate>(
            PipelineStage<TInput, TIntermediate> stage)
        {
            _stages.Add(stage);
            return this;
        }

        /// <summary>
        /// Start processing.
        /// </summary>
        public void Start()
        {
            if (_started) return;
            _started = true;
            _processingTask = ProcessLoopAsync(_cts.Token);
        }

        /// <summary>
        /// Submit item.
        /// </summary>
        public async ValueTask SubmitAsync(TInput item, CancellationToken ct = default)
        {
            await _inputChannel.Writer.WriteAsync(item, ct);
        }

        /// <summary>
        /// Complete and wait.
        /// </summary>
        public async Task CompleteAsync(CancellationToken ct = default)
        {
            _inputChannel.Writer.Complete();
            if (_processingTask is not null)
            {
                await _processingTask.WaitAsync(ct);
            }
        }

        private async Task ProcessLoopAsync(CancellationToken ct)
        {
            await foreach (var item in _inputChannel.Reader.ReadAllAsync(ct))
            {
                try
                {
                    object current = item;
                    foreach (var stage in _stages)
                    {
                        // Dynamic dispatch based on stage type
                        current = stage switch
                        {
                            IProcessor<object, object> p => p.Process(current),
                            _ => current
                        };
                    }
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Pipeline error: {ex}");
                }
            }
        }

        /// <inheritdoc/>
        public async ValueTask DisposeAsync()
        {
            _cts.Cancel();
            await CompleteAsync();
            _cts.Dispose();
            _inputChannel.Writer.Complete();
        }
    }

    /// <summary>
    /// Generic math operations using INumber (C# 11+).
    /// </summary>
    public static class GenericMath
    {
        /// <summary>
        /// Sum generic numbers.
        /// </summary>
        public static T Sum<T>(IEnumerable<T> values) where T : INumber<T>
        {
            T sum = T.Zero;
            foreach (var value in values)
            {
                sum += value;
            }
            return sum;
        }

        /// <summary>
        /// Average generic numbers.
        /// </summary>
        public static T Average<T>(IEnumerable<T> values) where T : INumber<T>
        {
            T sum = T.Zero;
            int count = 0;
            foreach (var value in values)
            {
                sum += value;
                count++;
            }
            return count > 0 ? sum / T.CreateChecked(count) : T.Zero;
        }

        /// <summary>
        /// Generic clamp.
        /// </summary>
        public static T Clamp<T>(T value, T min, T max) where T : INumber<T>
        {
            if (value < min) return min;
            if (value > max) return max;
            return value;
        }
    }

    /// <summary>
    /// Span and Memory demonstrations.
    /// </summary>
    public static class MemoryOperations
    {
        /// <summary>
        /// Process span with stackalloc.
        /// </summary>
        public static int ProcessSpan(ReadOnlySpan<int> input)
        {
            Span<int> buffer = stackalloc int[input.Length];
            input.CopyTo(buffer);
            buffer.Sort();
            return buffer[^1]; // Index from end
        }

        /// <summary>
        /// Process memory with ArrayPool.
        /// </summary>
        public static async Task<int[]> ProcessLargeAsync(ReadOnlyMemory<int> input, CancellationToken ct = default)
        {
            int[]? rented = null;
            try
            {
                rented = ArrayPool<int>.Shared.Rent(input.Length);
                input.CopyTo(rented);
                Array.Sort(rented, 0, input.Length);
                return rented[..input.Length].ToArray();
            }
            finally
            {
                if (rented is not null)
                {
                    ArrayPool<int>.Shared.Return(rented);
                }
            }
        }

        /// <summary>
        /// String processing with Span.
        /// </summary>
        public static ReadOnlySpan<char> ExtractToken(ReadOnlySpan<char> input, char delimiter)
        {
            int idx = input.IndexOf(delimiter);
            return idx >= 0 ? input[..idx] : input;
        }
    }

    /// <summary>
    /// Parallel processing utilities.
    /// </summary>
    public static class ParallelProcessing
    {
        /// <summary>
        /// Process with parallel foreach and async.
        /// </summary>
        public static async Task ProcessAsync<T>(
            IEnumerable<T> items,
            Func<T, CancellationToken, Task> processor,
            int maxParallelism,
            CancellationToken ct = default)
        {
            await Parallel.ForEachAsync(items, new ParallelOptions
            {
                MaxDegreeOfParallelism = maxParallelism,
                CancellationToken = ct
            }, async (item, ct) => await processor(item, ct));
        }

        /// <summary>
        /// Ordered parallel processing with async enumerable.
        /// </summary>
        public static async IAsyncEnumerable<TResult> ProcessOrderedAsync<T, TResult>(
            IAsyncEnumerable<T> source,
            Func<T, CancellationToken, Task<TResult>> processor,
            [EnumeratorCancellation] CancellationToken ct = default)
        {
            await using var enumerator = source.GetAsyncEnumerator(ct);
            int index = 0;
            var pending = new SortedDictionary<int, Task<TResult>>();

            while (await enumerator.MoveNextAsync())
            {
                var currentIndex = index++;
                pending[currentIndex] = processor(enumerator.Current, ct);

                while (pending.Count > 0 && pending.First().Key == currentIndex - pending.Count + 1)
                {
                    var kvp = pending.First();
                    pending.Remove(kvp.Key);
                    yield return await kvp.Value;
                }
            }

            foreach (var kvp in pending)
            {
                yield return await kvp.Value;
            }
        }
    }

    /// <summary>
    /// Program demonstrating features.
    /// </summary>
    public static class Program
    {
        public static async Task Main(string[] args)
        {
            // Generic math
            var ints = new[] { 1, 2, 3, 4, 5 };
            Console.WriteLine(GenericMath.Sum(ints));
            Console.WriteLine(GenericMath.Average(ints));

            var doubles = new[] { 1.0, 2.0, 3.0 };
            Console.WriteLine(GenericMath.Sum(doubles));

            // Span operations
            var spanResult = MemoryOperations.ProcessSpan(ints.AsSpan());
            Console.WriteLine(spanResult);

            // Pipeline
            var pipeline = new AsyncPipeline<string, int>(100);
            var stage1 = new PipelineStage<string, int>("parse", int.Parse);
            var stage2 = new PipelineStage<int, int>("double", x => x * 2);
            pipeline.AddStage(stage1.Then(stage2));
            pipeline.Start();

            await pipeline.SubmitAsync("42");
            await pipeline.CompleteAsync();

            // Parallel processing
            var items = Enumerable.Range(1, 100);
            await ParallelProcessing.ProcessAsync(
                items,
                async (n, ct) =>
                {
                    await Task.Delay(10, ct);
                    Console.WriteLine(n);
                },
                maxParallelism: 10);

            // Async enumerable
            await foreach (var n in GetNumbersAsync(10))
            {
                Console.WriteLine(n);
            }

            // LINQ with complex query
            var query = Enumerable.Range(1, 1000)
                .Chunk(10)
                .SelectMany(chunk => chunk.Select((n, i) => new { Value = n, Index = i }))
                .GroupBy(x => x.Value % 3)
                .Select(g => new { Mod = g.Key, Sum = g.Sum(x => x.Value), Count = g.Count() })
                .OrderByDescending(x => x.Sum);

            foreach (var item in query)
            {
                Console.WriteLine(item);
            }
        }

        private static async IAsyncEnumerable<int> GetNumbersAsync(
            int count,
            [EnumeratorCancellation] CancellationToken ct = default)
        {
            for (int i = 0; i < count; i++)
            {
                await Task.Delay(10, ct);
                yield return i;
            }
        }
    }
}