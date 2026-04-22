#include <stdalign.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

/**
 * @brief Preprocessor torture
 */

// Token pasting edge cases
#define PASTE(a, b) a##b
#define PASTE3(a, b, c) a##b##c
#define PASTE_STR(a) #a
#define PASTE_STR_EXPAND(a) PASTE_STR(a)

// Empty macro arguments
#define EMPTY()
#define CALL_WITH_EMPTY(x) x EMPTY()

// Macro that expands to directives (not valid but tests lexer)
#define IF_MACRO if
#define ELSE_MACRO else

// Indirect expansion
#define INDIRECT(x) x
#define INDIRECT2(x) INDIRECT(x)
#define INDIRECT3(x) INDIRECT2(x)

// Recursive macro protection
#define RECURSE RECURSE
#define NO_EXPAND(x) x

// Variadic macros
#define VA_MACRO(...) __VA_ARGS__
#define VA_NAMED(fmt, ...) printf(fmt, ##__VA_ARGS__)
#define VA_COUNT(...) VA_COUNT_IMPL(__VA_ARGS__, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0)
#define VA_COUNT_IMPL(_1, _2, _3, _4, _5, _6, _7, _8, _9, _10, N, ...) N

// Macro in stringification
#define VERSION 1.2.3
#define VERSION_STRING PASTE_STR_EXPAND(VERSION)

// Line directive
#line 100 "fake_file.c"

/**
 * @brief Type qualifier torture
 */

// All qualifiers on one declaration
volatile const restrict _Atomic int qualified_var;

// Multiple const (legal but redundant)
const const int double_const = 0;  /* C99 allows, C11 forbids duplicate */

// Pointer with all qualifiers
const volatile restrict _Atomic int * const volatile restrict _Atomic crazy_pointer;

// Complex qualifier nesting
const int * volatile * restrict const * ptr_to_ptr_to_ptr;

/**
 * @brief Declarator complexity - the spiral rule
 */

// Simple to complex declarations
int simple_int;
int *pointer_to_int;
int **pointer_to_pointer;
int *array_of_pointers[10];
int (*pointer_to_array)[10];
int *(*pointer_to_array_of_pointers)[10];
int (*array_of_pointers_to_arrays[10])[10];

// Function pointers
int (*fp)(void);
int (*fp_array[10])(void);
int (*(*fp_ptr)(void))(void);
int (*(*fp_array_of_ptrs[10])(void))(void);

// Array of pointers to functions returning pointers to functions
int (*(*(*complex_array[10])(void))(void))(void);

// Function returning pointer to array of pointers to functions
int (*(*(*weird_function(void))(void))[10])(void);

// The ultimate: signal handler type from K&R
void (*signal(int sig, void (*func)(int)))(int);

// Modern typedef for clarity
typedef void (*sighandler_t)(int);
sighandler_t signal2(int sig, sighandler_t func);

// Function pointer with all qualifiers
int (*const volatile restrict qualified_fp)(void);

/**
 * @brief Compound types
 */

// Struct with bitfields and anonymous members
struct complex_struct {
    unsigned int flag1 : 1;
    unsigned int flag2 : 1;
    unsigned int : 6;           /* Anonymous padding */
    unsigned int value : 24;
    
    union {
        struct {
            uint8_t lo;
            uint8_t hi;
        };
        uint16_t combined;
    } bytes;
    
    /* Anonymous struct (C11) */
    struct {
        int x;
        int y;
    };
    
    /* Anonymous union (C11) */
    union {
        float f;
        int i;
    };
    
    /* Flexible array member */
    char data[];
};

// Union with all type punning
union punner {
    uint32_t u32;
    uint16_t u16[2];
    uint8_t u8[4];
    float f32;
    int32_t i32;
};

// Enum with explicit values and trailing comma
enum weird_enum {
    A = 1,
    B = 2,
    C = 4,
    D = 8,
    E = A | B | C | D,
    F,          /* = 9 (previous + 1) */
    G = 100,
    H,          /* = 101 */
};

// Enum with underlying type (C23)
typedef enum : uint8_t {
    SMALL_A,
    SMALL_B,
} small_enum_t;

/**
 * @brief Alignment and static assertions
 */

// _Alignas usage
_Alignas(64) char aligned_buffer[1024];
_Alignas(max_align_t) char max_aligned[256];

// _Static_assert
_Static_assert(sizeof(int) >= 4, "int must be at least 32 bits");
_Static_assert(alignof(max_align_t) >= alignof(void *), "max_align_t too small");

/**
 * @brief _Generic selection (C11)
 */

#define TYPE_NAME(x) _Generic((x), \
    int: "int", \
    long: "long", \
    long long: "long long", \
    float: "float", \
    double: "double", \
    char *: "string", \
    void *: "pointer", \
    default: "unknown" \
)

#define ABS(x) _Generic((x), \
    int: abs_int, \
    long: abs_long, \
    long long: abs_longlong, \
    float: fabsf, \
    double: fabs \
)(x)

static inline int abs_int(int x) { return x < 0 ? -x : x; }
static inline long abs_long(long x) { return x < 0 ? -x : x; }
static inline long long abs_longlong(long long x) { return x < 0 ? -x : x; }

/**
 * @brief Typeof (C23) or GCC extension
 */
#if defined(__STDC_VERSION__) && __STDC_VERSION__ >= 202311L
#define AUTO_VAR(name, expr) typeof(expr) name = (expr)
#define TYPEOF_UNQUAL(x) typeof_unqual(x)
#elif defined(__GNUC__) || defined(__clang__)
#define AUTO_VAR(name, expr) __typeof__(expr) name = (expr)
#define TYPEOF_UNQUAL(x) __typeof__(expr)
#else
#define AUTO_VAR(name, expr) /* not supported */
#define TYPEOF_UNQUAL(x)
#endif

/**
 * @brief Designated initializers
 */

// Array designated init
int array_init[] = {
    [0] = 1,
    [1] = 2,
    [10] = 10,      /* Sparse */
    [20] = 20,
};

// Struct designated init
struct complex_struct struct_init = {
    .flag1 = 1,
    .bytes.combined = 0x1234,
    .x = 10,
    .y = 20,
};

// Nested designated init
struct nested_init {
    struct {
        int a;
        int b;
    } inner;
    int outer;
};

struct nested_init nested = {
    .inner = {
        .a = 1,
        .b = 2,
    },
    .outer = 3,
};

// Mixed designated and positional (C23 allows, earlier standards vary)
struct mixed {
    int a;
    int b;
    int c;
};

struct mixed mixed_init = {
    .a = 1,
    2,          /* b = 2 */
    .c = 3,
};

// Range init (GNU extension, C23)
int range_init[10] = {
    [0 ... 4] = 1,
    [5 ... 9] = 2,
};

/**
 * @brief Compound literals
 */

// Simple compound literal
int *compound_ptr = (int []){1, 2, 3, 4, 5};

// Compound literal in function call
void takes_array(int *arr, size_t n);

static void compound_demo(void) {
    takes_array((int []){1, 2, 3}, 3);
    
    // Compound literal with designated init
    struct complex_struct cs = (struct complex_struct){
        .flag1 = 1,
        .value = 42,
    };
    (void)cs;
    
    // Static compound literal (lifetime of program)
    int *static_compound = (static int []){1, 2, 3};
    (void)static_compound;
}

/**
 * @brief Operator precedence and associativity torture
 */

static void operator_stress(void) {
    int a = 1, b = 2, c = 3, d = 4;
    
    // Precedence traps
    int r1 = a + b * c;           /* a + (b * c) */
    int r2 = a * b + c;           /* (a * b) + c */
    int r3 = a + b << c;          /* (a + b) << c */
    int r4 = a << b + c;          /* a << (b + c) */
    
    // Associativity
    int r5 = a - b - c;           /* (a - b) - c */
    int r6 = a / b / c;           /* (a / b) / c */
    int r7 = a << b << c;         /* (a << b) << c */
    
    // Ternary
    int r8 = a ? b : c ? d : 0;   /* a ? b : (c ? d : 0) */
    int r9 = a ? b, c : d;        /* a ? (b, c) : d */
    
    // Comma operator
    int r10 = (a = 1, b = 2, c = 3);
    
    // Assignment chains
    a = b = c = d;
    
    // Compound assignment
    a += b *= c -= d;
    
    // Bitwise
    int r11 = a & b | c ^ d;      /* (a & b) | (c ^ d) */
    int r12 = a | b & c;          /* a | (b & c) */
    
    // Logical
    bool r13 = a && b || c && d;  /* (a && b) || (c && d) */
    
    // Pointer arithmetic
    int arr[10];
    int *p = arr;
    int r14 = *p++;               /* *(p++) */
    int r15 = (*p)++;             /* (*p)++ */
    int r16 = *++p;               /* *(++p) */
    int r17 = ++*p;               /* ++(*p) */
    
    // Array subscript vs dereference
    int r18 = p[1];               /* *(p + 1) */
    int r19 = 1[p];               /* *(1 + p), same as above */
    
    // Function call vs cast
    int (*fp)(int) = NULL;
    int r20 = (fp)(1);            /* function call */
    int r21 = ((int (*)(int))fp)(1); /* cast then call */
    
    // sizeof traps
    size_t s1 = sizeof(int);      /* size of type */
    size_t s2 = sizeof(int[10]);  /* size of array type */
    size_t s3 = sizeof a;         /* size of expression */
    size_t s4 = sizeof(a + b);    /* size of expression result */
    
    // _Alignof
    size_t a1 = alignof(int);
    size_t a2 = alignof(max_align_t);
    
    (void)r1; (void)r2; (void)r3; (void)r4; (void)r5;
    (void)r6; (void)r7; (void)r8; (void)r9; (void)r10;
    (void)r11; (void)r12; (void)r13; (void)r14; (void)r15;
    (void)r16; (void)r17; (void)r18; (void)r19; (void)r20;
    (void)r21; (void)s1; (void)s2; (void)s3; (void)s4;
    (void)a1; (void)a2;
}

/**
 * @brief Control flow complexity
 */

static void control_flow(int n) {
    // Labels and goto
    if (n < 0) goto error;
    
    // Duff's device
    int count = n;
    int *to = NULL;
    int *from = NULL;
    
    switch (count % 8) {
        case 0: do { *to++ = *from++;
        case 7:      *to++ = *from++;
        case 6:      *to++ = *from++;
        case 5:      *to++ = *from++;
        case 4:      *to++ = *from++;
        case 3:      *to++ = *from++;
        case 2:      *to++ = *from++;
        case 1:      *to++ = *from++;
                } while ((count -= 8) > 0);
    }
    
    // For with empty parts
    for (;;) {
        break;
    }
    
    // While with comma
    int i = 0, j = 10;
    while (i++, j--) {
        if (i > 5) break;
    }
    
    // Do-while with complex condition
    do {
        /* body */
    } while ((i = getchar()) != EOF && i != '\n');
    
    // Nested loops with multiple breaks
    for (int a = 0; a < 10; a++) {
        for (int b = 0; b < 10; b++) {
            if (a == 5 && b == 5) goto done;
        }
    }
done:
    
    // Switch with fallthrough
    switch (n) {
        case 1:
            /* fallthrough */
        case 2:
            /* fallthrough */
        case 3:
            printf("1-3\n");
            break;
        case 4 ... 10:  /* GNU extension, C23 */
            printf("4-10\n");
            break;
        default:
            printf("other\n");
    }
    
    return;
    
error:
    fprintf(stderr, "error\n");
}

/**
 * @brief typeof demonstration (C23/GNU)
 */
static void typeof_demo(void) {
#ifdef AUTO_VAR
    AUTO_VAR(x, 42);
    AUTO_VAR(y, 3.14);
    AUTO_VAR(z, "hello");
    
    (void)x;
    (void)y;
    (void)z;
#endif
}

/**
 * @brief Main entry
 */
int main(int argc, char **argv) {
    (void)argc;
    (void)argv;
    
    printf("Type of 42: %s\n", TYPE_NAME(42));
    printf("Type of 3.14: %s\n", TYPE_NAME(3.14));
    printf("Type of \"hello\": %s\n", TYPE_NAME("hello"));
    
    operator_stress();
    control_flow(10);
    typeof_demo();
    
    return 0;
}