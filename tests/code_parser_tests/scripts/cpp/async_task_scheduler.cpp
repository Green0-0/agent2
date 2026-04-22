#include <atomic>
#include <chrono>
#include <condition_variable>
#include <coroutine>
#include <exception>
#include <functional>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <queue>
#include <thread>
#include <type_traits>
#include <variant>
#include <vector>

/**
 * @brief Task scheduler namespace
 */
namespace scheduler {

using namespace std::chrono_literals;

/**
 * @brief Awaitable that suspends for a duration
 */
struct DelayAwaitable {
    std::chrono::milliseconds duration;
    
    /**
     * @brief Awaiter implementation
     */
    struct Awaiter {
        std::chrono::milliseconds duration;
        
        [[nodiscard]] bool await_ready() const noexcept {
            return duration.count() <= 0;
        }
        
        void await_suspend(std::coroutine_handle<> handle) const {
            std::thread([handle, duration = duration]() {
                std::this_thread::sleep_for(duration);
                handle.resume();
            }).detach();
        }
        
        void await_resume() const noexcept {}
    };
    
    [[nodiscard]] Awaiter operator co_await() const noexcept {
        return Awaiter{duration};
    }
};

/**
 * @brief Generator coroutine type
 * @tparam T Yield type
 */
template<typename T>
struct Generator {
    /**
     * @brief Promise type for generator coroutine
     */
    struct promise_type {
        T current_value_;
        std::exception_ptr exception_;
        
        Generator get_return_object() {
            return Generator{
                std::coroutine_handle<promise_type>::from_promise(*this)
            };
        }
        
        std::suspend_always initial_suspend() noexcept {
            return {};
        }
        
        std::suspend_always final_suspend() noexcept {
            return {};
        }
        
        void unhandled_exception() {
            exception_ = std::current_exception();
        }
        
        std::suspend_always yield_value(T value) {
            current_value_ = std::move(value);
            return {};
        }
        
        void return_void() {}
        
        // Prevent co_await in generator
        void await_transform() = delete;
    };
    
    using handle_type = std::coroutine_handle<promise_type>;
    
private:
    handle_type handle_;
    
public:
    explicit Generator(handle_type h) : handle_(h) {}
    
    ~Generator() {
        if (handle_) {
            handle_.destroy();
        }
    }
    
    // Move-only
    Generator(Generator&& other) noexcept : handle_(std::exchange(other.handle_, {})) {}
    
    Generator& operator=(Generator&& other) noexcept {
        if (this != &other) {
            if (handle_) handle_.destroy();
            handle_ = std::exchange(other.handle_, {});
        }
        return *this;
    }
    
    Generator(const Generator&) = delete;
    Generator& operator=(const Generator&) = delete;
    
    // Iterator interface
    class Iterator {
        handle_type handle_;
        
    public:
        using iterator_category = std::input_iterator_tag;
        using value_type = T;
        using difference_type = std::ptrdiff_t;
        using pointer = T*;
        using reference = T&;
        
        explicit Iterator(handle_type h = nullptr) : handle_(h) {}
        
        Iterator& operator++() {
            handle_.resume();
            if (handle_.done()) {
                handle_ = nullptr;
            }
            return *this;
        }
        
        [[nodiscard]] bool operator!=(const Iterator& other) const {
            return handle_ != other.handle_;
        }
        
        [[nodiscard]] T& operator*() const {
            return handle_.promise().current_value_;
        }
        
        [[nodiscard]] T* operator->() const {
            return &handle_.promise().current_value_;
        }
    };
    
    [[nodiscard]] Iterator begin() {
        if (handle_) {
            handle_.resume();
            if (!handle_.done()) {
                return Iterator(handle_);
            }
        }
        return Iterator(nullptr);
    }
    
    [[nodiscard]] Iterator end() const {
        return Iterator(nullptr);
    }
};

/**
 * @brief Task coroutine type with return value
 * @tparam T Return type
 */
template<typename T = void>
struct Task {
    /**
     * @brief Promise type for task coroutine
     */
    struct promise_type {
        std::variant<std::monostate, T, std::exception_ptr> result_;
        std::coroutine_handle<> continuation_;
        
        Task get_return_object() {
            return Task{
                std::coroutine_handle<promise_type>::from_promise(*this)
            };
        }
        
        std::suspend_always initial_suspend() noexcept {
            return {};
        }
        
        auto final_suspend() noexcept {
            struct FinalAwaiter {
                [[nodiscard]] bool await_ready() const noexcept {
                    return false;
                }
                
                void await_suspend(std::coroutine_handle<promise_type> handle) const {
                    if (auto cont = handle.promise().continuation_) {
                        cont.resume();
                    }
                }
                
                void await_resume() const noexcept {}
            };
            return FinalAwaiter{};
        }
        
        void unhandled_exception() {
            result_.template emplace<2>(std::current_exception());
        }
        
        template<typename U>
        void return_value(U&& value) {
            result_.template emplace<1>(std::forward<U>(value));
        }
        
        // Await transform for chaining
        template<typename U>
        auto await_transform(Task<U>&& task) {
            struct TaskAwaiter {
                Task<U> task_;
                
                [[nodiscard]] bool await_ready() const noexcept {
                    return task_.handle_.done();
                }
                
                void await_suspend(std::coroutine_handle<promise_type> handle) {
                    task_.handle_.promise().continuation_ = handle;
                }
                
                U await_resume() {
                    return task_.get_result();
                }
            };
            return TaskAwaiter{std::move(task)};
        }
    };
    
    using handle_type = std::coroutine_handle<promise_type>;
    
private:
    handle_type handle_;
    
public:
    explicit Task(handle_type h) : handle_(h) {}
    
    ~Task() {
        if (handle_) {
            handle_.destroy();
        }
    }
    
    Task(Task&& other) noexcept : handle_(std::exchange(other.handle_, {})) {}
    
    Task& operator=(Task&& other) noexcept {
        if (this != &other) {
            if (handle_) handle_.destroy();
            handle_ = std::exchange(other.handle_, {});
        }
        return *this;
    }
    
    Task(const Task&) = delete;
    Task& operator=(const Task&) = delete;
    
    [[nodiscard]] T get_result() {
        if (handle_.promise().result_.index() == 2) {
            std::rethrow_exception(std::get<2>(handle_.promise().result_));
        }
        return std::move(std::get<1>(handle_.promise().result_));
    }
    
    // Make task awaitable
    struct Awaiter {
        handle_type handle_;
        
        [[nodiscard]] bool await_ready() const noexcept {
            return handle_.done();
        }
        
        void await_suspend(std::coroutine_handle<> handle) const {
            handle_.promise().continuation_ = handle;
        }
        
        T await_resume() {
            if (handle_.promise().result_.index() == 2) {
                std::rethrow_exception(std::get<2>(handle_.promise().result_));
            }
            return std::move(std::get<1>(handle_.promise().result_));
        }
    };
    
    [[nodiscard]] Awaiter operator co_await() && {
        return Awaiter{handle_};
    }
};

// Specialization for void
template<>
struct Task<void> {
    struct promise_type {
        std::exception_ptr exception_;
        std::coroutine_handle<> continuation_;
        
        Task get_return_object() {
            return Task{
                std::coroutine_handle<promise_type>::from_promise(*this)
            };
        }
        
        std::suspend_always initial_suspend() noexcept {
            return {};
        }
        
        auto final_suspend() noexcept {
            struct FinalAwaiter {
                [[nodiscard]] bool await_ready() const noexcept {
                    return false;
                }
                
                void await_suspend(std::coroutine_handle<promise_type> handle) const {
                    if (auto cont = handle.promise().continuation_) {
                        cont.resume();
                    }
                }
                
                void await_resume() const noexcept {}
            };
            return FinalAwaiter{};
        }
        
        void unhandled_exception() {
            exception_ = std::current_exception();
        }
        
        void return_void() {}
    };
    
    using handle_type = std::coroutine_handle<promise_type>;
    
private:
    handle_type handle_;
    
public:
    explicit Task(handle_type h) : handle_(h) {}
    ~Task() { if (handle_) handle_.destroy(); }
    
    Task(Task&& other) noexcept : handle_(std::exchange(other.handle_, {})) {}
    Task& operator=(Task&& other) noexcept {
        if (this != &other) {
            if (handle_) handle_.destroy();
            handle_ = std::exchange(other.handle_, {});
        }
        return *this;
    }
    Task(const Task&) = delete;
    Task& operator=(const Task&) = delete;
    
    struct Awaiter {
        handle_type handle_;
        [[nodiscard]] bool await_ready() const noexcept { return handle_.done(); }
        void await_suspend(std::coroutine_handle<> handle) const {
            handle_.promise().continuation_ = handle;
        }
        void await_resume() const {
            if (handle_.promise().exception_) {
                std::rethrow_exception(handle_.promise().exception_);
            }
        }
    };
    
    [[nodiscard]] Awaiter operator co_await() && {
        return Awaiter{handle_};
    }
};

/**
 * @brief Thread pool with work stealing
 */
class ThreadPool {
public:
    /**
     * @brief Work item type
     */
    using WorkItem = std::function<void()>;
    
private:
    std::vector<std::thread> workers_;
    std::queue<WorkItem> tasks_;
    std::mutex mutex_;
    std::condition_variable cv_;
    std::atomic<bool> stop_{false};
    
public:
    explicit ThreadPool(std::size_t numThreads = std::thread::hardware_concurrency()) {
        for (std::size_t i = 0; i < numThreads; ++i) {
            workers_.emplace_back([this] {
                while (true) {
                    WorkItem task;
                    {
                        std::unique_lock lock(mutex_);
                        cv_.wait(lock, [this] {
                            return stop_ || !tasks_.empty();
                        });
                        
                        if (stop_ && tasks_.empty()) {
                            return;
                        }
                        
                        task = std::move(tasks_.front());
                        tasks_.pop();
                    }
                    task();
                }
            });
        }
    }
    
    ~ThreadPool() {
        {
            std::lock_guard lock(mutex_);
            stop_ = true;
        }
        cv_.notify_all();
        for (auto& worker : workers_) {
            if (worker.joinable()) {
                worker.join();
            }
        }
    }
    
    /**
     * @brief Submit work to the pool
     */
    template<typename F, typename... Args>
    auto submit(F&& f, Args&&... args) -> std::future<std::invoke_result_t<F, Args...>> {
        using ReturnType = std::invoke_result_t<F, Args...>;
        
        auto task = std::make_shared<std::packaged_task<ReturnType()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );
        
        std::future<ReturnType> result = task->get_future();
        {
            std::lock_guard lock(mutex_);
            tasks_.emplace([task]() { (*task)(); });
        }
        cv_.notify_one();
        return result;
    }
    
    /**
     * @brief Submit work returning a task coroutine
     */
    template<typename F, typename... Args>
    auto submitTask(F&& f, Args&&... args) -> Task<std::invoke_result_t<F, Args...>> {
        co_return co_await std::async(std::launch::deferred, std::forward<F>(f), std::forward<Args>(args)...);
    }
};

/**
 * @brief Timer class with callback scheduling
 */
class Timer {
public:
    using Clock = std::chrono::steady_clock;
    using TimePoint = Clock::time_point;
    using Duration = Clock::duration;
    
private:
    TimePoint start_;
    std::function<void()> callback_;
    std::atomic<bool> active_{false};
    std::thread thread_;
    
public:
    Timer() : start_(Clock::now()) {}
    
    explicit Timer(std::function<void()> callback) 
        : start_(Clock::now())
        , callback_(std::move(callback)) {}
    
    ~Timer() {
        stop();
    }
    
    // Move semantics
    Timer(Timer&& other) noexcept
        : start_(other.start_)
        , callback_(std::move(other.callback_))
        , active_(other.active_.load()) {}
    
    Timer& operator=(Timer&& other) noexcept {
        if (this != &other) {
            stop();
            start_ = other.start_;
            callback_ = std::move(other.callback_);
            active_ = other.active_.load();
        }
        return *this;
    }
    
    Timer(const Timer&) = delete;
    Timer& operator=(const Timer&) = delete;
    
    /**
     * @brief Start periodic timer
     */
    void startPeriodic(Duration interval) {
        active_ = true;
        thread_ = std::thread([this, interval] {
            while (active_) {
                std::this_thread::sleep_for(interval);
                if (active_ && callback_) {
                    callback_();
                }
            }
        });
    }
    
    /**
     * @brief Stop the timer
     */
    void stop() {
        active_ = false;
        if (thread_.joinable()) {
            thread_.join();
        }
    }
    
    /**
     * @brief Get elapsed time
     */
    [[nodiscard]] Duration elapsed() const {
        return Clock::now() - start_;
    }
    
    /**
     * @brief Reset the timer
     */
    void reset() {
        start_ = Clock::now();
    }
};

/**
 * @brief Coroutine-based async generator for Fibonacci
 */
Generator<std::uint64_t> fibonacci(std::size_t n) {
    std::uint64_t a = 0, b = 1;
    for (std::size_t i = 0; i < n; ++i) {
        co_yield a;
        auto next = a + b;
        a = b;
        b = next;
    }
}

/**
 * @brief Async task that delays and returns value
 */
Task<int> asyncCompute(int value) {
    co_await DelayAwaitable{100ms};
    co_return value * 2;
}

/**
 * @brief Chained async tasks
 */
Task<int> chainedTasks() {
    auto a = co_await asyncCompute(21);
    auto b = co_await asyncCompute(a);
    co_return b;
}

/**
 * @brief Lambda demonstration with all capture types
 */
void lambdaDemonstration() {
    int x = 1, y = 2, z = 3;
    
    // No capture
    auto noCapture = []() { return 42; };
    
    // Capture by value
    auto captureValue = [x]() { return x; };
    
    // Capture by reference
    auto captureRef = [&x]() { return ++x; };
    
    // Capture all by value
    auto captureAllValue = [=]() { return x + y + z; };
    
    // Capture all by reference
    auto captureAllRef = [&]() { return ++x + ++y + ++z; };
    
    // Mixed capture
    auto mixedCapture = [x, &y, z]() { return x + y + z; };
    
    // Init capture (C++14)
    auto initCapture = [ptr = std::make_unique<int>(42)]() {
        return *ptr;
    };
    
    // Generic lambda (C++14)
    auto generic = [](auto a, auto b) {
        return a + b;
    };
    
    // Template lambda (C++20)
    auto templateLambda = []<typename T>(T a, T b) {
        return a + b;
    };
    
    // Mutable lambda
    auto mutableLambda = [x]() mutable {
        return ++x;
    };
    
    // Immediately invoked lambda
    auto iife = [](int n) { return n * n; }(5);
    
    // Recursive lambda via Y-combinator pattern
    auto factorial = [](auto self, int n) -> int {
        return n <= 1 ? 1 : n * self(self, n - 1);
    };
    
    // Lambda returning lambda
    auto makeAdder = [](int x) {
        return [x](int y) { return x + y; };
    };
    
    (void)noCapture;
    (void)captureValue;
    (void)captureRef;
    (void)captureAllValue;
    (void)captureAllRef;
    (void)mixedCapture;
    (void)initCapture;
    (void)generic;
    (void)templateLambda;
    (void)mutableLambda;
    (void)iife;
    (void)factorial;
    (void)makeAdder;
}

} // namespace scheduler

/**
 * @brief Main function demonstrating usage
 */
int main() {
    using namespace scheduler;
    
    ThreadPool pool{4};
    
    // Submit work
    auto future = pool.submit([]() { return 42; });
    std::cout << "Result: " << future.get() << std::endl;
    
    // Use generator
    for (auto val : fibonacci(10)) {
        std::cout << val << " ";
    }
    std::cout << std::endl;
    
    // Run coroutine
    auto task = chainedTasks();
    // In real code, would need a coroutine runner
    
    lambdaDemonstration();
    
    return 0;
}