// Nullable context
#nullable enable

using System;
using System.Collections.Generic;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

namespace Test.Syntax
{
    // File-scoped namespace (C# 10+) - this file uses it

    /// <summary>
    /// Target-typed new expressions.
    /// </summary>
    class TargetTypedNew
    {
        void Demo()
        {
            List<int> list = new();
            Dictionary<string, int> dict = new()
            {
                ["key"] = 1,
                ["other"] = 2
            };

            Point p = new(1, 2);
            var arr = new[] { 1, 2, 3 };
        }
    }

    /// <summary>
    /// Record with positional and property syntax.
    /// </summary>
    record Point(int X, int Y)
    {
        public double Distance => Math.Sqrt(X * X + Y * Y);

        // Deconstruct is implicit for positional records
        // but can be overridden
        public void Deconstruct(out int x, out int y, out double dist)
        {
            x = X;
            y = Y;
            dist = Distance;
        }
    }

    /// <summary>
    /// Record struct.
    /// </summary>
    readonly record struct Vector2(double X, double Y);

    /// <summary>
    /// Record class with init-only properties.
    /// </summary>
    record Person(string Name)
    {
        public int Age { get; init; }
        public string? Email { get; init; }

        // Required members (C# 11+)
        public required string Department { get; init; }
    }

    /// <summary>
    /// Required members usage.
    /// </summary>
    class RequiredDemo
    {
        void Demo()
        {
            var person = new Person("John")
            {
                Age = 30,
                Department = "Engineering"
            };
        }
    }

    /// <summary>
    /// Generic with multiple constraints.
    /// </summary>
    class MultiConstrained<T>
        where T : class, IDisposable, IComparable<T>, new()
    {
        public T Create() => new();
    }

    /// <summary>
    /// Generic with notnull and unmanaged constraints.
    /// </summary>
    class SpecialConstraints<T, U>
        where T : notnull
        where U : unmanaged
    {
        public unsafe U* GetPointer(U[] arr)
        {
            fixed (U* ptr = arr)
            {
                return ptr;
            }
        }
    }

    /// <summary>
    /// Static abstract members in interface (C# 11+).
    /// </summary>
    interface IParsable<T> where T : IParsable<T>
    {
        static abstract T Parse(string input);
        static virtual T? TryParse(string input) => default;
    }

    /// <summary>
    /// Implementation of static abstract.
    /// </summary>
    struct MyInt : IParsable<MyInt>
    {
        public int Value;

        public static MyInt Parse(string input) => new() { Value = int.Parse(input) };
    }

    /// <summary>
    /// Ref struct and ref fields (C# 11+).
    /// </summary>
    ref struct RefStruct
    {
        public ref int Field;

        public RefStruct(ref int field)
        {
            Field = ref field;
        }

        public Span<int> GetSpan(int[] arr)
        {
            return arr.AsSpan();
        }
    }

    /// <summary>
    /// Scoped ref (C# 11+).
    /// </summary>
    class ScopedRef
    {
        public void Process(scoped ref int value)
        {
            value++;
        }

        public void ProcessSpan(scoped Span<int> span)
        {
            span[0] = 42;
        }
    }

    /// <summary>
    /// Pattern matching stress test.
    /// </summary>
    class PatternMatching
    {
        public string MatchObject(object? obj) => obj switch
        {
            null => "null",
            int i and > 0 => $"positive int {i}",
            int i and < 0 => $"negative int {i}",
            int 0 => "zero",
            string { Length: > 10 } s => $"long string: {s[..10]}...",
            string { Length: 0 } => "empty string",
            string s => $"string: {s}",
            List<int> { Count: 0 } => "empty int list",
            List<int> list => $"int list with {list.Count} items",
            int[] [1, 2, 3] => "array [1,2,3]",
            int[] arr => $"int array length {arr.Length}",
            { } => $"object: {obj.GetType().Name}",
        };

        public string MatchTuple((int, int) point) => point switch
        {
            (0, 0) => "origin",
            (> 0, > 0) => "quadrant 1",
            (< 0, > 0) => "quadrant 2",
            (< 0, < 0) => "quadrant 3",
            (> 0, < 0) => "quadrant 4",
            (var x, 0) => $"on x-axis at {x}",
            (0, var y) => $"on y-axis at {y}",
            var (x, y) => $"point ({x}, {y})",
        };

        public string MatchListPattern(int[] arr) => arr switch
        {
            [] => "empty",
            [1] => "single one",
            [1, 2] => "one and two",
            [1, .., 9] => "starts with 1, ends with 9",
            [var first, .. var rest] => $"starts with {first}, {rest.Length} more",
            _ => "something else"
        };

        public string MatchPropertyPattern(Point p) => p switch
        {
            { X: 0, Y: 0 } => "origin",
            { X: var x, Y: > 0 } => $"above x-axis at x={x}",
            { Distance: > 10 } => "far from origin",
            _ => "somewhere"
        };

        public string MatchRelational(int n) => n switch
        {
            < 0 => "negative",
            0 => "zero",
            > 0 and < 10 => "small positive",
            >= 10 and < 100 => "medium",
            >= 100 => "large"
        };

        public string MatchLogical(object obj) => obj switch
        {
            string s when s.StartsWith("A") && s.Length > 5 => "long A-string",
            string s when s is ['A' or 'a', ..] => "starts with A",
            int i when i is > 0 and < 100 or > 1000 => "special int",
            _ => "other"
        };
    }

    /// <summary>
    /// Lambda and delegate stress test.
    /// </summary>
    class LambdaStress
    {
        void Demo()
        {
            // Simple lambda
            Func<int, int> square = x => x * x;

            // Statement lambda
            Func<int, int, int> add = (a, b) =>
            {
                var sum = a + b;
                return sum;
            };

            // Lambda with discards
            Action<int, int> ignoreSecond = (_, y) => Console.WriteLine(y);

            // Lambda with explicit types
            Func<int, string> toString = (int x) => x.ToString();

            // Lambda with attributes
            Func<string, int> parse = [DebuggerStepThrough] (string s) => int.Parse(s);

            // Lambda with ref
            var increment = (ref int x) => x++;

            // Lambda with in
            var read = (in int x) => x;

            // Lambda with out
            var tryParse = (string s, out int result) => int.TryParse(s, out result);

            // Natural type for method group
            var methodGroup = Console.WriteLine;

            // Delegate with target type
            Delegate del = (string s) => s.Length;

            // Func with natural type (C# 10+)
            var natural = object (bool b) => b ? 1 : "one";

            // Async lambda
            Func<Task<int>> asyncLambda = async () =>
            {
                await Task.Delay(100);
                return 42;
            };

            // Async lambda with parameters
            Func<int, Task<string>> asyncWithParam = async (n) =>
            {
                await Task.Yield();
                return n.ToString();
            };

            // Lambda in LINQ
            var query = Enumerable.Range(1, 10)
                .Where(n => n % 2 == 0)
                .Select(n => new { Value = n, Square = n * n });

            // Closure capture
            int captured = 0;
            Action capture = () => captured++;
            capture();

            // Static lambda (no closure)
            Func<int, int> staticLambda = static x => x * 2;
        }
    }

    /// <summary>
    /// Operator overloading and conversion.
    /// </summary>
    class OverloadedOperators
    {
        private int _value;

        public OverloadedOperators(int value) => _value = value;

        // Unary
        public static OverloadedOperators operator +(OverloadedOperators o) => new(+o._value);
        public static OverloadedOperators operator -(OverloadedOperators o) => new(-o._value);
        public static OverloadedOperators operator ~(OverloadedOperators o) => new(~o._value);
        public static OverloadedOperators operator ++(OverloadedOperators o) => new(o._value + 1);
        public static OverloadedOperators operator --(OverloadedOperators o) => new(o._value - 1);

        // Binary arithmetic
        public static OverloadedOperators operator +(OverloadedOperators a, OverloadedOperators b) =>
            new(a._value + b._value);
        public static OverloadedOperators operator -(OverloadedOperators a, OverloadedOperators b) =>
            new(a._value - b._value);
        public static OverloadedOperators operator *(OverloadedOperators a, OverloadedOperators b) =>
            new(a._value * b._value);
        public static OverloadedOperators operator /(OverloadedOperators a, OverloadedOperators b) =>
            new(a._value / b._value);
        public static OverloadedOperators operator %(OverloadedOperators a, OverloadedOperators b) =>
            new(a._value % b._value);

        // Bitwise
        public static OverloadedOperators operator &(OverloadedOperators a, OverloadedOperators b) =>
            new(a._value & b._value);
        public static OverloadedOperators operator |(OverloadedOperators a, OverloadedOperators b) =>
            new(a._value | b._value);
        public static OverloadedOperators operator ^(OverloadedOperators a, OverloadedOperators b) =>
            new(a._value ^ b._value);
        public static OverloadedOperators operator <<(OverloadedOperators o, int shift) =>
            new(o._value << shift);
        public static OverloadedOperators operator >>(OverloadedOperators o, int shift) =>
            new(o._value >> shift);
        public static OverloadedOperators operator >>>(OverloadedOperators o, int shift) =>
            new(o._value >>> shift); // Unsigned right shift (C# 11+)

        // Comparison
        public static bool operator ==(OverloadedOperators a, OverloadedOperators b) =>
            a._value == b._value;
        public static bool operator !=(OverloadedOperators a, OverloadedOperators b) =>
            !(a == b);
        public static bool operator <(OverloadedOperators a, OverloadedOperators b) =>
            a._value < b._value;
        public static bool operator >(OverloadedOperators a, OverloadedOperators b) =>
            a._value > b._value;
        public static bool operator <=(OverloadedOperators a, OverloadedOperators b) =>
            a._value <= b._value;
        public static bool operator >=(OverloadedOperators a, OverloadedOperators b) =>
            a._value >= b._value;

        // Compound assignment (implicit from binary)
        // Conversion
        public static implicit operator int(OverloadedOperators o) => o._value;
        public static explicit operator OverloadedOperators(int value) => new(value);

        // True/False for short-circuit
        public static bool operator true(OverloadedOperators o) => o._value != 0;
        public static bool operator false(OverloadedOperators o) => o._value == 0;

        // Logical operators (if true/false defined)
        public static OverloadedOperators operator &(OverloadedOperators a, OverloadedOperators b) =>
            a._value != 0 && b._value != 0 ? new(1) : new(0);
        public static OverloadedOperators operator |(OverloadedOperators a, OverloadedOperators b) =>
            a._value != 0 || b._value != 0 ? new(1) : new(0);

        // Indexer
        public int this[int index] => (int)(Math.Pow(_value, index));

        // Multi-dimensional indexer
        public int this[int i, int j] => _value + i * j;

        // Slice indexer (C# 8+)
        public int[] this[Range range] => new[] { _value };

        public override bool Equals(object? obj) => obj is OverloadedOperators other && _value == other._value;
        public override int GetHashCode() => _value.GetHashCode();
    }

    /// <summary>
    /// Attributes everywhere.
    /// </summary>
    [Serializable]
    [Obsolete("Use NewClass instead", error: false)]
    class AttributeHell : Attribute
    {
        [field: NonSerialized]
        public int FieldAttribute { get; set; }

        [method: DebuggerHidden]
        [return: MaybeNull]
        public string? MethodWithAttributes([AllowNull] string? input) => input;

        [param: NotNull]
        public void ParameterAttribute([NotNull] string input) { }

        [module: CLSCompliant(false)] // Module-level attribute syntax
        public void ModuleAttribute() { }
    }

    /// <summary>
    /// Unsafe code block.
    /// </summary>
    unsafe class UnsafeOperations
    {
        public void PointerArithmetic()
        {
            int[] arr = { 1, 2, 3, 4, 5 };
            fixed (int* ptr = arr)
            {
                int* end = ptr + arr.Length;
                for (int* p = ptr; p < end; p++)
                {
                    Console.WriteLine(*p);
                }
            }
        }

        public void FunctionPointers()
        {
            delegate*<int, int, int> add = &Add;
            int result = add(1, 2);

            static int Add(int a, int b) => a + b;
        }

        public void StackAlloc()
        {
            Span<int> span = stackalloc int[100];
            span.Fill(42);
        }

        public void SkipLocalsInit()
        {
            [SkipLocalsInit]
            static void NoInit()
            {
                int x;
                // x is uninitialized
            }

            NoInit();
        }
    }

    /// <summary>
    /// Local functions and static local functions.
    /// </summary>
    class LocalFunctions
    {
        public int Calculate(int n)
        {
            // Regular local function
            int Factorial(int x) => x <= 1 ? 1 : x * Factorial(x - 1);

            // Static local function (no closure)
            static int Fibonacci(int x) => x <= 1 ? x : Fibonacci(x - 1) + Fibonacci(x - 2);

            // Local function with attributes
            [DebuggerStepThrough]
            int Square(int x) => x * x;

            // Async local function
            async Task<int> AsyncWork()
            {
                await Task.Delay(10);
                return n * 2;
            }

            return Factorial(n) + Fibonacci(n) + Square(n);
        }
    }

    /// <summary>
    /// Expression-bodied everything.
    /// </summary>
    class ExpressionBodies
    {
        private int _value;

        // Constructor
        public ExpressionBodies(int value) => _value = value;

        // Finalizer
        ~ExpressionBodies() => Console.WriteLine("Finalized");

        // Property
        public int Value
        {
            get => _value;
            set => _value = value;
        }

        // Indexer
        public int this[int index] => _value + index;

        // Method
        public int Double() => _value * 2;

        // Operator
        public static ExpressionBodies operator +(ExpressionBodies a, ExpressionBodies b) =>
            new(a._value + b._value);

        // Event
        private EventHandler? _event;
        public event EventHandler? MyEvent
        {
            add => _event += value;
            remove => _event -= value;
        }
    }

    /// <summary>
    /// Namespace alias and extern alias.
    /// </summary>
    class AliasDemo
    {
        void Demo()
        {
            // Using alias
            using MyList = System.Collections.Generic.List<int>;
            var list = new MyList();

            // Global using (would be at top of file normally)
            // global using System.Linq;

            // Static using
            // using static System.Math;
        }
    }

    /// <summary>
    /// Interpolated strings and raw strings.
    /// </summary>
    class StringInterpolation
    {
        void Demo()
        {
            var name = "world";
            var oldStyle = $"Hello, {name}!";

            // Interpolated with format
            var number = 42;
            var formatted = $"Number: {number:D5}";

            // Interpolated with alignment
            var aligned = $"[{name,10}]";

            // Raw string literals (C# 11+)
            var raw = """
                Line 1
                Line 2
                Line 3
                """;

            // Raw with interpolation
            var rawInterpolated = $$"""
                {
                    "name": "{{name}}",
                    "value": {{number}}
                }
                """;

            // UTF-8 string literals (C# 11+)
            ReadOnlySpan<byte> utf8 = "hello"u8;
        }
    }

    /// <summary>
    /// Checked/unchecked contexts.
    /// </summary>
    class CheckedContext
    {
        public int CheckedAdd(int a, int b)
        {
            checked
            {
                return a + b;
            }
        }

        public int UncheckedAdd(int a, int b)
        {
            unchecked
            {
                return a + b;
            }
        }

        public int CheckedExpression(int a, int b) => checked(a + b);
        public int UncheckedExpression(int a, int b) => unchecked(a + b);
    }

    /// <summary>
    /// Main entry with comprehensive feature demo.
    /// </summary>
    public class Program
    {
        public static async Task Main(string[] args)
        {
            // Target-typed new
            List<int> list = new();
            Point p = new(1, 2);

            // With expression
            var p2 = p with { X = 3 };

            // Deconstruction
            var (x, y, dist) = p;

            // Pattern matching
            var matcher = new PatternMatching();
            Console.WriteLine(matcher.MatchObject(42));
            Console.WriteLine(matcher.MatchObject("hello world"));
            Console.WriteLine(matcher.MatchListPattern(new[] { 1, 2, 3, 4, 5 }));

            // Null-conditional and null-coalescing
            string? maybe = null;
            var length = maybe?.Length ?? 0;
            var notNull = maybe ??= "default";

            // Range and index
            var arr = new[] { 1, 2, 3, 4, 5 };
            var last = arr[^1];
            var slice = arr[1..^1];

            // Switch expression
            var day = DayOfWeek.Monday;
            var type = day switch
            {
                DayOfWeek.Saturday or DayOfWeek.Sunday => "weekend",
                >= DayOfWeek.Monday and <= DayOfWeek.Friday => "weekday",
                _ => "unknown"
            };

            // Async streams
            await foreach (var n in GetNumbersAsync(10))
            {
                Console.WriteLine(n);
            }

            // LINQ
            var query = from n in Enumerable.Range(1, 100)
                        where n % 2 == 0
                        orderby n descending
                        select n * n;

            // Tuple
            var tuple = (1, "two", 3.0);
            var (a, b, c) = tuple;

            // Discards
            _ = SomeMethod();

            // Nameof
            Console.WriteLine(nameof(Main));
            Console.WriteLine(nameof(list.Count));

            // Default literal
            int def = default;
            string? nullStr = default;

            // Null-forgiving
            string notNullStr = nullStr!;

            // Caller info attributes
            Log("message");

            // Await using
            await using var resource = new AsyncDisposable();

            // Await foreach
            await foreach (var item in GetAsyncEnumerable())
            {
                Console.WriteLine(item);
            }
        }

        private static void Log(
            string message,
            [CallerMemberName] string? member = null,
            [CallerFilePath] string? file = null,
            [CallerLineNumber] int line = 0)
        {
            Console.WriteLine($"[{member}] {message} at {file}:{line}");
        }

        private static int SomeMethod() => 42;

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

        private static async IAsyncEnumerable<string> GetAsyncEnumerable()
        {
            yield return "one";
            await Task.Delay(10);
            yield return "two";
        }
    }

    /// <summary>
    /// Async disposable implementation.
    /// </summary>
    class AsyncDisposable : IAsyncDisposable
    {
        public async ValueTask DisposeAsync()
        {
            await Task.Delay(10);
            Console.WriteLine("Disposed async");
        }
    }
}