#include <algorithm>
#include <array>
#include <iostream>
#include <map>
#include <string>
#include <tuple>
#include <vector>

// Macro hell
#define CONCAT(a, b) a##b
#define STRINGIFY(x) #x
#define MULTI_LINE_MACRO(x) \
    do { \
        auto _temp = (x); \
        (void)_temp; \
    } while(0)

// Macro that looks like a template
#define TEMPLATE_LIKE <

// Macro in function-like context
#define RETURN_TYPE(x) decltype(x)

// Template with dependent name disambiguation
template<typename T>
struct Container {
    using value_type = T;
    
    /**
     * @brief Nested template class
     */
    template<typename U>
    struct Inner {
        U value;
    };
    
    /**
     * @brief Function with dependent type
     * 
     * The 'typename' keyword is required here to disambiguate
     * that Inner<T>::type is a type, not a value.
     */
    template<typename U>
    typename Inner<U>::value_type getValue(const Inner<U>& inner) {
        return inner.value;
    }
    
    /**
     * @brief Function with template keyword disambiguation
     * 
     * The 'template' keyword tells the parser that getInner
     * is a template member, not a comparison.
     */
    template<typename U>
    void process() {
        Inner<U> inner;
        this->template getInner<U>(inner);
    }
    
    template<typename U>
    Inner<U> getInner(const Inner<U>&) {
        return Inner<U>{};
    }
};

// Most vexing parse demonstration
struct Timer {
    Timer() { std::cout << "Timer constructed\n"; }
};

void mostVexingParse() {
    // This is parsed as a function declaration, not an object!
    Timer timer();
    
    // These are objects
    Timer timer2{};
    Timer timer3 = Timer();
    Timer* timer4 = new Timer();
    
    (void)timer;
    (void)timer2;
    (void)timer3;
    delete timer4;
}

// Operator overloading galore
class Overloaded {
    int value_;
    
public:
    explicit Overloaded(int v) : value_(v) {}
    
    // Unary operators
    Overloaded operator+() const { return Overloaded(+value_); }
    Overloaded operator-() const { return Overloaded(-value_); }
    Overloaded operator~() const { return Overloaded(~value_); }
    Overloaded& operator++() { ++value_; return *this; }
    Overloaded operator++(int) { auto temp = *this; ++value_; return temp; }
    Overloaded& operator--() { --value_; return *this; }
    Overloaded operator--(int) { auto temp = *this; --value_; return temp; }
    
    // Binary arithmetic
    Overloaded operator+(const Overloaded& other) const {
        return Overloaded(value_ + other.value_);
    }
    Overloaded operator-(const Overloaded& other) const {
        return Overloaded(value_ - other.value_);
    }
    Overloaded operator*(const Overloaded& other) const {
        return Overloaded(value_ * other.value_);
    }
    Overloaded operator/(const Overloaded& other) const {
        return Overloaded(value_ / other.value_);
    }
    Overloaded operator%(const Overloaded& other) const {
        return Overloaded(value_ % other.value_);
    }
    
    // Bitwise
    Overloaded operator&(const Overloaded& other) const {
        return Overloaded(value_ & other.value_);
    }
    Overloaded operator|(const Overloaded& other) const {
        return Overloaded(value_ | other.value_);
    }
    Overloaded operator^(const Overloaded& other) const {
        return Overloaded(value_ ^ other.value_);
    }
    Overloaded operator<<(const Overloaded& other) const {
        return Overloaded(value_ << other.value_);
    }
    Overloaded operator>>(const Overloaded& other) const {
        return Overloaded(value_ >> other.value_);
    }
    
    // Comparison (C++20 style with spaceship)
    [[nodiscard]] auto operator<=>(const Overloaded&) const = default;
    [[nodiscard]] bool operator==(const Overloaded&) const = default;
    
    // Compound assignment
    Overloaded& operator+=(const Overloaded& other) {
        value_ += other.value_;
        return *this;
    }
    Overloaded& operator-=(const Overloaded& other) {
        value_ -= other.value_;
        return *this;
    }
    Overloaded& operator*=(const Overloaded& other) {
        value_ *= other.value_;
        return *this;
    }
    Overloaded& operator/=(const Overloaded& other) {
        value_ /= other.value_;
        return *this;
    }
    
    // Subscript (both const and non-const)
    int& operator[](std::size_t idx) {
        (void)idx;
        return value_;
    }
    const int& operator[](std::size_t idx) const {
        (void)idx;
        return value_;
    }
    
    // Function call
    int operator()(int x) const {
        return value_ + x;
    }
    
    // Dereference
    int operator*() const {
        return value_;
    }
    
    // Arrow operator (smart pointer-like)
    const Overloaded* operator->() const {
        return this;
    }
    
    // Address-of (unary & is built-in, but we can overload binary &)
    // Note: Cannot overload unary &
    
    // Comma operator
    Overloaded operator,(const Overloaded& other) const {
        return other;
    }
    
    // Member access through pointer
    int* operator->*(int Overloaded::* ptr) {
        return &(this->*ptr);
    }
    
    // Conversion operators
    explicit operator int() const { return value_; }
    operator bool() const { return value_ != 0; }
    
    // New/delete (class-specific)
    void* operator new(std::size_t size) {
        return ::operator new(size);
    }
    void operator delete(void* ptr) {
        ::operator delete(ptr);
    }
    void* operator new[](std::size_t size) {
        return ::operator new[](size);
    }
    void operator delete[](void* ptr) {
        ::operator delete[](ptr);
    }
    
    // Placement new
    void* operator new(std::size_t, void* ptr) {
        return ptr;
    }
    void operator delete(void*, void*) {}
    
    // Stream operators (friend)
    friend std::ostream& operator<<(std::ostream& os, const Overloaded& o) {
        return os << "Overloaded(" << o.value_ << ")";
    }
    friend std::istream& operator>>(std::istream& is, Overloaded& o) {
        return is >> o.value_;
    }
};

// Trailing return type and decltype
template<typename T, typename U>
auto addWithTrailingReturn(T t, U u) -> decltype(t + u) {
    return t + u;
}

// decltype(auto) for perfect forwarding
template<typename T>
decltype(auto) forwardHelper(T&& t) {
    return static_cast<T&&>(t);
}

// if constexpr (C++17)
template<typename T>
auto getValue(T t) {
    if constexpr (std::is_pointer_v<T>) {
        return *t;
    } else if constexpr (std::is_array_v<T>) {
        return t[0];
    } else {
        return t;
    }
}

// Structured bindings (C++17)
void structuredBindingsDemo() {
    std::tuple<int, double, std::string> tup{1, 2.0, "hello"};
    auto [a, b, c] = tup;
    
    std::map<std::string, int> map{{"one", 1}, {"two", 2}};
    for (const auto& [key, value] : map) {
        std::cout << key << ": " << value << std::endl;
    }
    
    std::array<int, 3> arr{1, 2, 3};
    auto [x, y, z] = arr;
    
    struct S {
        int first;
        double second;
    };
    S s{10, 20.0};
    auto [f, sec] = s;
    
    (void)a; (void)b; (void)c;
    (void)x; (void)y; (void)z;
    (void)f; (void)sec;
}

// Fold expressions (C++17)
template<typename... Args>
auto sumFold(Args... args) {
    return (args + ...);  // Unary right fold
}

template<typename... Args>
auto sumFoldLeft(Args... args) {
    return (... + args);  // Unary left fold
}

template<typename... Args>
bool allTrue(Args... args) {
    return (args && ...);  // Fold over &&
}

template<typename... Args>
bool anyTrue(Args... args) {
    return (args || ...);  // Fold over ||
}

// Variadic template with pack expansion in lambda
template<typename... Args>
void variadicLambda(Args... args) {
    auto printer = [](auto... vals) {
        ((std::cout << vals << " "), ...);
    };
    printer(args...);
}

// Designated initializers (C++20)
struct Config {
    int timeout = 30;
    int retries = 3;
    const char* name = "default";
};

void designatedInit() {
    Config c1{.timeout = 60};
    Config c2{.retries = 5, .name = "custom"};
    Config c3{.name = "another", .timeout = 10};
    
    (void)c1; (void)c2; (void)c3;
}

// Concepts and constraints (C++20)
template<typename T>
concept Numeric = std::is_arithmetic_v<T>;

template<typename T>
concept Addable = requires(T a, T b) {
    { a + b } -> std::convertible_to<T>;
};

template<Numeric T>
T constrainedAdd(T a, T b) {
    return a + b;
}

template<typename T>
    requires Addable<T>
T addableAdd(T a, T b) {
    return a + b;
}

// Requires clause in function
template<typename T>
void processIfSortable(T& container)
    requires requires { std::sort(container.begin(), container.end()); }
{
    std::sort(container.begin(), container.end());
}

// Lambda with template parameters (C++20)
void templateLambda() {
    auto generic = []<typename T>(T val) {
        return val * 2;
    };
    
    auto explicitRet = []<typename T>(T a, T b) -> T {
        return a + b;
    };
    
    (void)generic(5);
    (void)explicitRet(1.0, 2.0);
}

// Attributes everywhere
[[nodiscard]] int attributedFunction([[maybe_unused]] int x) {
    [[likely]] if (x > 0) {
        return x;
    } [[unlikely]] {
        return -x;
    }
}

// Inline variables and inline namespaces
inline namespace v2 {
    inline constexpr int version = 2;
}

namespace v1 {
    inline constexpr int version = 1;
}

// Enum class with underlying type and attributes
enum class [[nodiscard]] Status : std::uint8_t {
    OK = 0,
    Warning = 1,
    Error = 2,
};

// Using enum (C++20)
void usingEnum() {
    using enum Status;
    auto s = OK;
    (void)s;
}

// Explicit object parameter (C++23 deducing this)
struct ExplicitThis {
    int value;
    
    void print(this auto& self) {
        std::cout << self.value << std::endl;
    }
};

// Main with complex initialization
int main(int argc, char* argv[]) {
    (void)argc;
    (void)argv;
    
    mostVexingParse();
    
    Overloaded o1{10}, o2{20};
    auto o3 = o1 + o2;
    std::cout << o3 << std::endl;
    
    structuredBindingsDemo();
    
    std::cout << sumFold(1, 2, 3, 4, 5) << std::endl;
    std::cout << allTrue(true, true, false) << std::endl;
    
    variadicLambda(1, 2.0, "hello");
    
    designatedInit();
    
    std::cout << constrainedAdd(5, 3) << std::endl;
    
    templateLambda();
    
    ExplicitThis et{42};
    et.print();
    
    return 0;
}