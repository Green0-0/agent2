/**
 * Syntax Stress Test
 * 
 * Valid but pathological Java for parser boundary testing.
 */

package com.test.syntax;

import java.io.*;
import java.lang.annotation.*;
import java.util.*;
import java.util.function.*;

// Annotation on package (requires package-info.java normally, here for parsing)
@interface PackageMarker {}

/**
 * Type-use annotation.
 */
@Target(ElementType.TYPE_USE)
@interface NonNull {}

/**
 * Type parameter annotation.
 */
@Target(ElementType.TYPE_PARAMETER)
@interface TypeParam {}

/**
 * Repeating annotation container.
 */
@Retention(RetentionPolicy.RUNTIME)
@interface Tests {
    Test[] value();
}

/**
 * Repeatable annotation.
 */
@Retention(RetentionPolicy.RUNTIME)
@Repeatable(Tests.class)
@interface Test {
    String value();
}

/**
 * Class with every possible modifier combination.
 */
public abstract strictfp class SyntaxStressTest<T extends @NonNull Comparable<@NonNull T>> 
    extends Object 
    implements Serializable, Comparable<T> {
    
    // Static initialization block
    static {
        System.out.println("Static init 1");
    }
    
    // Instance initialization block
    {
        System.out.println("Instance init");
    }
    
    // Another static block
    static {
        System.out.println("Static init 2");
    }
    
    // Fields with all modifiers
    public static final int PUBLIC_CONSTANT = 42;
    private static volatile int volatileField;
    protected transient String transientField;
    transient volatile int tvField;
    
    // Varargs field (annotation)
    private String @NonNull [] arrayField;
    
    // Annotated type
    private @NonNull List<@NonNull String> annotatedList;
    
    // Lambda as field initializer
    private final Function<String, Integer> fieldLambda = s -> s.length();
    
    // Method reference as field
    private final Predicate<String> notEmpty = String::isEmpty;
    
    // Complex generic field
    private Map<? extends Number, ? super Integer> wildcardMap;
    
    /**
     * Constructor with every feature.
     */
    @Test("constructor")
    @Deprecated(since = "1.0", forRemoval = true)
    public SyntaxStressTest() throws IOException, IllegalStateException {
        super();
        this.annotatedList = new ArrayList<>();
    }
    
    /**
     * Varargs constructor.
     */
    @SafeVarargs
    public SyntaxStressTest(T... items) {
        this();
        for (T item : items) {
            System.out.println(item);
        }
    }
    
    // Native method
    public native void nativeMethod();
    
    // Strictfp method
    public strictfp double strictCalculation(double a, double b) {
        return a * b + a / b;
    }
    
    // Synchronized method
    public synchronized void synchronizedMethod() {
        System.out.println("thread-safe");
    }
    
    // Method with complex generics
    public <@TypeParam U extends T, V extends List<? super U>> 
    Map<U, V> complexGenerics(V list, U item) {
        return Map.of(item, list);
    }
    
    // Method with intersection type
    public <T extends Number & Comparable<T>> T intersection(T value) {
        return value;
    }
    
    // Varargs with final parameter
    public void varargsMethod(final String prefix, Object... args) {
        System.out.println(prefix);
        for (Object arg : args) {
            System.out.println(arg);
        }
    }
    
    // Method with annotated parameters and exceptions
    public void annotatedParams(
        @NonNull final String required,
        @Deprecated Optional<String> optional
    ) throws @NonNull IOException, IllegalArgumentException {
        System.out.println(required + optional.orElse(""));
    }
    
    // Lambda with complex body
    public void lambdaStress() {
        // No-arg lambda
        Runnable r = () -> {};
        
        // Single param with inferred type
        Consumer<String> c = s -> System.out.println(s);
        
        // Multi-statement lambda
        Function<String, Integer> f = s -> {
            int len = s.length();
            return len * 2;
        };
        
        // Lambda with exception handling
        Supplier<String> supplier = () -> {
            try {
                return new BufferedReader(new FileReader("test")).readLine();
            } catch (IOException e) {
                throw new RuntimeException(e);
            }
        };
        
        // Generic lambda (inferred)
        Function<List<String>, Integer> listFn = list -> list.size();
        
        // Method references
        Function<String, Integer> lengthRef = String::length;
        BiFunction<String, String, Integer> compareRef = String::compareTo;
        Supplier<Object> constructorRef = Object::new;
        Function<String[], List<String>> arrayRef = Arrays::asList;
        
        // Chained lambdas
        Function<Function<String, Integer>, Function<String, Integer>> higherOrder = 
            fn -> fn.andThen(i -> i * 2).compose(String::trim);
    }
    
    // Switch expressions with pattern matching (Java 21+)
    public String patternSwitch(Object obj) {
        return switch (obj) {
            case null -> "null";
            case Integer i when i > 0 -> "positive integer: " + i;
            case Integer i -> "integer: " + i;
            case String s && s.isEmpty() -> "empty string";
            case String s -> "string: " + s.toUpperCase();
            case List<?> list when list.isEmpty() -> "empty list";
            case List<?> list -> "list with " + list.size() + " items";
            case Map<?, ?> map -> "map with " + map.size() + " entries";
            default -> "unknown: " + obj.getClass().getSimpleName();
        };
    }
    
    // Record pattern matching
    public String matchRecord(Object obj) {
        if (obj instanceof Point(int x, int y)) {
            return "point at (" + x + ", " + y + ")";
        }
        if (obj instanceof Person(String name, int age)) {
            return name + " is " + age;
        }
        return "not a record";
    }
    
    // Array patterns
    public String matchArray(Object obj) {
        return switch (obj) {
            case int[] arr when arr.length == 0 -> "empty int array";
            case int[] arr -> "int array length " + arr.length;
            case String[] arr -> "string array: " + Arrays.toString(arr);
            case Object[] arr -> "object array length " + arr.length;
            default -> "not an array";
        };
    }
    
    // Nested switch with yield
    public int nestedSwitch(int a, int b) {
        return switch (a) {
            case 1 -> switch (b) {
                case 1 -> yield 11;
                case 2 -> yield 12;
                default -> yield 10;
            };
            case 2 -> {
                System.out.println("two");
                yield 20;
            }
            default -> {
                yield -1;
            }
        };
    }
    
    // Text blocks with various content
    public String textBlocks() {
        var simple = """
            Hello
            World
            """;
        
        var indented = """
            {
                "key": "value",
                "nested": {
                    "array": [1, 2, 3]
                }
            }
            """;
        
        var escaped = """
            Line 1\nLine 2\tTabbed
            """;
        
        var concatenated = """
            Part 1
            """ + """
            Part 2
            """;
        
        return simple + indented + escaped + concatenated;
    }
    
    // Annotated local variables and types
    public void localAnnotations() {
        @SuppressWarnings("unchecked")
        var list = new ArrayList<String>();
        
        @NonNull String required = "test";
        
        final var immutable = 42;
        
        // Local class
        class LocalClass {
            void localMethod() {
                System.out.println("local");
            }
        }
        
        new LocalClass().localMethod();
        
        // Local interface
        interface LocalInterface {
            void act();
        }
        
        // Local enum
        enum LocalEnum { A, B, C }
        
        // Anonymous class
        var anon = new LocalInterface() {
            @Override
            public void act() {
                System.out.println("anonymous");
            }
        };
        anon.act();
        
        // Lambda implementing functional interface
        LocalInterface lambda = () -> System.out.println("lambda");
        lambda.act();
    }
    
    // Complex try-with-resources
    public void resourceManagement() throws Exception {
        try (var in = new FileInputStream("in");
             var out = new FileOutputStream("out");
             var reader = new BufferedReader(new InputStreamReader(in))) {
            out.write(reader.readLine().getBytes());
        } catch (IOException | IllegalStateException e) {
            System.err.println("IO error: " + e.getMessage());
            throw e;
        } catch (Exception e) {
            e.printStackTrace();
            throw new RuntimeException("wrapped", e);
        } finally {
            System.out.println("cleanup");
        }
    }
    
    // Try-with-resources with effectively final
    public void effectiveFinalResource() throws Exception {
        final var resource = new FileInputStream("test");
        try (resource) {
            resource.read();
        }
    }
    
    // Synchronized statement (not method)
    public void synchronizedBlock() {
        synchronized (this) {
            System.out.println("locked");
        }
    }
    
    // Labeled statements and breaks
    public void labeledBreaks() {
        outer: for (int i = 0; i < 10; i++) {
            inner: for (int j = 0; j < 10; j++) {
                if (i == 5 && j == 5) {
                    break outer;
                }
                if (j == 3) {
                    continue inner;
                }
            }
        }
    }
    
    // While with complex condition
    public void whileComplex() {
        int i = 0;
        while ((i = increment(i)) < 100 && i % 2 == 0) {
            System.out.println(i);
        }
    }
    
    private int increment(int i) {
        return ++i;
    }
    
    // Do-while
    public void doWhileTest() {
        int count = 0;
        do {
            count++;
        } while (count < 0); // executes once
    }
    
    // For-each with var and pattern
    public void forEachPatterns(List<Object> items) {
        for (var item : items) {
            if (item instanceof String s) {
                System.out.println(s);
            }
        }
    }
    
    // Traditional for with multiple variables (Java not supported, but parsing test)
    public void traditionalFor() {
        for (int i = 0, j = 10; i < j; i++, j--) {
            System.out.println(i + ", " + j);
        }
    }
    
    // If with complex boolean expression
    public void complexIf() {
        boolean a = true, b = false, c = true;
        if ((a && b) || (!c && a) || (b ^ c)) {
            System.out.println("complex true");
        } else if (a ? b : c) {
            System.out.println("ternary");
        }
    }
    
    // Ternary nesting
    public String nestedTernary(int x) {
        return x > 0 ? x > 10 ? "large" : "small" : x < -10 ? "very negative" : "negative";
    }
    
    // Cast with intersection (Java not directly supported, but parsing)
    public void castTest(Object obj) {
        if (obj instanceof Number n) {
            double d = n.doubleValue();
            System.out.println(d);
        }
    }
    
    // Instanceof with pattern and logic
    public void patternInstanceof(Object obj) {
        if (obj instanceof String s && s.length() > 5 && s.startsWith("test")) {
            System.out.println(s.toUpperCase());
        }
    }
    
    // Sealed class hierarchy (Java 17+)
    sealed interface Shape permits Circle, Rectangle, Square {
        double area();
    }
    
    record Circle(double radius) implements Shape {
        @Override
        public double area() {
            return Math.PI * radius * radius;
        }
    }
    
    record Rectangle(double width, double height) implements Shape {
        @Override
        public double area() {
            return width * height;
        }
    }
    
    record Square(double side) implements Shape {
        @Override
        public double area() {
            return side * side;
        }
    }
    
    // Non-sealed extension
    non-sealed interface Polygon extends Shape {
        int sides();
    }
    
    // Abstract sealed class
    abstract sealed class AbstractShape permits ConcreteShape {
        abstract void draw();
    }
    
    final class ConcreteShape extends AbstractShape {
        @Override
        void draw() {
            System.out.println("drawing");
        }
    }
    
    // Static nested class with generics
    static class NestedGeneric<U> {
        private U value;
        
        public void set(U value) {
            this.value = value;
        }
        
        public U get() {
            return value;
        }
        
        // Nested in nested
        class DeepNested {
            void access() {
                System.out.println(value);
            }
        }
    }
    
    // Inner class accessing outer
    class InnerClass {
        void outerAccess() {
            System.out.println(SyntaxStressTest.this.volatileField);
        }
    }
    
    // Anonymous inner class extending outer
    public Object anonymousExtends() {
        return new SyntaxStressTest<String>() {
            @Override
            public String patternSwitch(Object obj) {
                return "overridden";
            }
        };
    }
    
    // Enum with complex features
    enum ComplexEnum {
        FIRST(1) {
            @Override
            void action() {
                System.out.println("first action");
            }
        },
        SECOND(2) {
            @Override
            void action() {
                System.out.println("second action");
            }
        },
        THIRD(3) {
            @Override
            void action() {
                System.out.println("third action");
            }
        };
        
        private final int value;
        
        ComplexEnum(int value) {
            this.value = value;
        }
        
        public int getValue() {
            return value;
        }
        
        abstract void action();
        
        // Nested enum in enum
        enum NestedEnum { A, B }
    }
    
    // Interface with default and static methods
    interface FunctionalInterface {
        void abstractMethod();
        
        default void defaultMethod() {
            System.out.println("default");
        }
        
        static void staticMethod() {
            System.out.println("static");
        }
        
        private void privateMethod() {
            System.out.println("private");
        }
        
        private static void privateStaticMethod() {
            System.out.println("private static");
        }
    }
    
    // Record with compact constructor, validation, nested
    record Point(int x, int y) {
        public Point {
            if (x < 0 || y < 0) {
                throw new IllegalArgumentException("Coordinates must be non-negative");
            }
        }
        
        public Point(int value) {
            this(value, value);
        }
        
        public static final Point ORIGIN = new Point(0, 0);
        
        // Nested record
        record Polar(double r, double theta) {}
    }
    
    // Record with generic
    record Person<T>(String name, int age, T metadata) {
        public Person {
            Objects.requireNonNull(name);
            if (age < 0) throw new IllegalArgumentException();
        }
    }
    
    // Main method with varargs
    public static void main(String... args) {
        var test = new SyntaxStressTest<String>();
        
        // Switch expression
        var day = "MONDAY";
        var type = switch (day) {
            case "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY" -> "weekday";
            case "SATURDAY", "SUNDAY" -> "weekend";
            default -> "unknown";
        };
        System.out.println(type);
        
        // Pattern matching for switch
        System.out.println(test.patternSwitch("hello"));
        System.out.println(test.patternSwitch(42));
        System.out.println(test.patternSwitch(List.of(1, 2, 3)));
        
        // Record patterns
        System.out.println(test.matchRecord(new Point(1, 2)));
        
        // Sealed type pattern matching
        Shape shape = new Circle(5.0);
        var area = switch (shape) {
            case Circle c -> c.area();
            case Rectangle r -> r.area();
            case Square s -> s.area();
        };
        System.out.println("Area: " + area);
        
        // Text blocks
        System.out.println(test.textBlocks());
        
        // Lambda stress
        test.lambdaStress();
        
        // Local annotations
        test.localAnnotations();
        
        // Complex enum
        ComplexEnum.FIRST.action();
    }
}