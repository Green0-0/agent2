#pragma once
#ifndef ENTERPRISE_RENDER_ENGINE_HPP
#define ENTERPRISE_RENDER_ENGINE_HPP

#include <array>
#include <concepts>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <tuple>
#include <type_traits>
#include <utility>
#include <variant>
#include <vector>

// Forward declarations in nested namespace
namespace engine::gfx::detail {
    template<typename T>
    struct type_traits;
}

/**
 * @brief Core engine namespace with deep nesting
 */
namespace engine {

/**
 * @brief Version information structure
 */
struct Version {
    std::uint16_t major;
    std::uint16_t minor;
    std::uint16_t patch;
    
    /**
     * @brief Compare versions
     * @param other Version to compare against
     * @return Strong ordering result
     */
    [[nodiscard]] constexpr auto operator<=>(const Version& other) const = default;
    
    [[nodiscard]] constexpr bool operator==(const Version&) const = default;
};

/**
 * @brief Concept requiring arithmetic types
 */
template<typename T>
concept Arithmetic = std::is_arithmetic_v<T>;

/**
 * @brief Concept requiring vector-like container
 */
template<typename T>
concept VectorLike = requires(T t) {
    typename T::value_type;
    { t.size() } -> std::convertible_to<std::size_t>;
    { t[0] } -> std::convertible_to<typename T::value_type>;
};

/**
 * @brief Base CRTP interface for renderable objects
 * @tparam Derived The derived type (CRTP)
 */
template<typename Derived>
class Renderable {
public:
    /**
     * @brief Render the object
     * @param ctx Render context
     */
    void render(auto& ctx) const {
        static_cast<const Derived*>(this)->renderImpl(ctx);
    }
    
protected:
    ~Renderable() = default;
};

/**
 * @brief Color structure with template-based channel type
 * @tparam T Channel type (must be arithmetic)
 */
template<Arithmetic T>
struct Color {
    T r{};
    T g{};
    T b{};
    T a{static_cast<T>(255)};
    
    /**
     * @brief Nested iterator for channel access
     */
    class Iterator {
        Color* color_;
        std::size_t idx_;
        
    public:
        using iterator_category = std::random_access_iterator_tag;
        using value_type = T;
        using difference_type = std::ptrdiff_t;
        using pointer = T*;
        using reference = T&;
        
        Iterator(Color* c, std::size_t i) : color_(c), idx_(i) {}
        
        [[nodiscard]] reference operator*() const {
            return (*color_)[idx_];
        }
        
        Iterator& operator++() {
            ++idx_;
            return *this;
        }
        
        [[nodiscard]] bool operator!=(const Iterator& other) const {
            return idx_ != other.idx_;
        }
    };
    
    /**
     * @brief Access channel by index
     * @param idx Channel index (0=r, 1=g, 2=b, 3=a)
     * @return Reference to channel
     */
    [[nodiscard]] T& operator[](std::size_t idx) {
        switch (idx) {
            case 0: return r;
            case 1: return g;
            case 2: return b;
            case 3: return a;
            default: throw std::out_of_range("Invalid color channel");
        }
    }
    
    [[nodiscard]] const T& operator[](std::size_t idx) const {
        return const_cast<Color*>(this)->operator[](idx);
    }
    
    /**
     * @brief Blend two colors
     * @tparam U Other channel type
     * @param other Color to blend with
     * @param factor Blend factor [0, 1]
     * @return Blended color
     */
    template<Arithmetic U>
    [[nodiscard]] auto blend(const Color<U>& other, float factor) const {
        using ResultType = std::common_type_t<T, U>;
        return Color<ResultType>{
            static_cast<ResultType>(r + (other.r - r) * factor),
            static_cast<ResultType>(g + (other.g - g) * factor),
            static_cast<ResultType>(b + (other.b - b) * factor),
            static_cast<ResultType>(a + (other.a - a) * factor)
        };
    }
    
    /**
     * @brief Hidden friend for stream output
     */
    friend std::ostream& operator<<(std::ostream& os, const Color& c) {
        return os << "Color(" << +c.r << ", " << +c.g << ", " << +c.b << ", " << +c.a << ")";
    }
    
    [[nodiscard]] Iterator begin() { return Iterator(this, 0); }
    [[nodiscard]] Iterator end() { return Iterator(this, 4); }
};

/**
 * @brief Vertex structure with position, normal, and UV
 * @tparam T Coordinate type
 */
template<Arithmetic T>
struct Vertex {
    std::array<T, 3> position{};
    std::array<T, 3> normal{};
    std::array<T, 2> texcoord{};
    
    /**
     * @brief Nested builder pattern
     */
    class Builder {
        Vertex v_;
        
    public:
        Builder& position(T x, T y, T z) {
            v_.position = {x, y, z};
            return *this;
        }
        
        Builder& normal(T x, T y, T z) {
            v_.normal = {x, y, z};
            return *this;
        }
        
        Builder& texcoord(T u, T v) {
            v_.texcoord = {u, v};
            return *this;
        }
        
        [[nodiscard]] Vertex build() const {
            return v_;
        }
    };
    
    static Builder builder() {
        return Builder{};
    }
};

/**
 * @brief Mesh class with CRTP-based rendering
 * @tparam T Vertex type
 * @tparam IndexType Index buffer type
 */
template<typename T, typename IndexType = std::uint32_t>
class Mesh : public Renderable<Mesh<T, IndexType>> {
public:
    using vertex_type = T;
    using index_type = IndexType;
    using size_type = std::size_t;
    
private:
    std::vector<T> vertices_;
    std::vector<IndexType> indices_;
    
    /**
     * @brief Private nested class for GPU buffer management
     */
    class GpuBuffer {
        std::size_t handle_{0};
        bool mapped_{false};
        
    public:
        explicit GpuBuffer(std::size_t size) {
            // Allocation logic
            (void)size;
        }
        
        ~GpuBuffer() {
            if (handle_) {
                // Deallocation
            }
        }
        
        // Move-only
        GpuBuffer(GpuBuffer&& other) noexcept 
            : handle_(std::exchange(other.handle_, 0))
            , mapped_(std::exchange(other.mapped_, false)) {}
        
        GpuBuffer& operator=(GpuBuffer&& other) noexcept {
            if (this != &other) {
                handle_ = std::exchange(other.handle_, 0);
                mapped_ = std::exchange(other.mapped_, false);
            }
            return *this;
        }
        
        GpuBuffer(const GpuBuffer&) = delete;
        GpuBuffer& operator=(const GpuBuffer&) = delete;
        
        void* map() {
            mapped_ = true;
            return nullptr;
        }
        
        void unmap() {
            mapped_ = false;
        }
        
        [[nodiscard]] explicit operator bool() const noexcept {
            return handle_ != 0;
        }
        
        [[nodiscard]] bool operator!() const noexcept {
            return handle_ == 0;
        }
    };
    
    std::optional<GpuBuffer> vbo_;
    std::optional<GpuBuffer> ibo_;
    
public:
    Mesh() = default;
    
    explicit Mesh(std::vector<T> verts) : vertices_(std::move(verts)) {}
    
    Mesh(std::vector<T> verts, std::vector<IndexType> idxs)
        : vertices_(std::move(verts))
        , indices_(std::move(idxs)) {}
    
    /**
     * @brief Add vertex with perfect forwarding
     */
    template<typename... Args>
    void emplaceVertex(Args&&... args) {
        vertices_.emplace_back(std::forward<Args>(args)...);
    }
    
    /**
     * @brief Add multiple vertices from initializer list
     */
    void addVertices(std::initializer_list<T> verts) {
        vertices_.insert(vertices_.end(), verts);
    }
    
    [[nodiscard]] size_type vertexCount() const noexcept {
        return vertices_.size();
    }
    
    [[nodiscard]] size_type indexCount() const noexcept {
        return indices_.size();
    }
    
    /**
     * @brief Access vertex by index with bounds checking
     */
    [[nodiscard]] T& at(size_type idx) {
        return vertices_.at(idx);
    }
    
    [[nodiscard]] const T& at(size_type idx) const {
        return vertices_.at(idx);
    }
    
    /**
     * @brief Render implementation (CRTP)
     */
    void renderImpl(auto& ctx) const {
        if (vbo_ && ibo_) {
            ctx.drawIndexed(indices_.size());
        } else {
            ctx.drawArrays(vertices_.size());
        }
    }
    
    /**
     * @brief Variadic template for multi-buffer upload
     */
    template<typename... Buffers>
    void upload(Buffers&&... buffers) {
        (uploadBuffer(buffers), ...);
    }
    
private:
    void uploadBuffer(const auto& buffer) {
        (void)buffer;
        // Upload logic
    }
};

/**
 * @brief Shader program with type-erased uniform storage
 */
class ShaderProgram {
public:
    /**
     * @brief Uniform value variant type
     */
    using UniformValue = std::variant<
        int,
        float,
        std::array<float, 2>,
        std::array<float, 3>,
        std::array<float, 4>,
        std::vector<float>
    >;
    
private:
    std::uint32_t handle_{0};
    std::unordered_map<std::string, UniformValue> uniforms_;
    
public:
    ShaderProgram() = default;
    
    explicit ShaderProgram(std::uint32_t handle) : handle_(handle) {}
    
    /**
     * @brief Compile from vertex and fragment shader sources
     * @param vertSrc Vertex shader GLSL source
     * @param fragSrc Fragment shader GLSL source
     * @return Compiled program or nullopt on failure
     */
    [[nodiscard]] static std::optional<ShaderProgram> compile(
        std::string_view vertSrc,
        std::string_view fragSrc
    );
    
    /**
     * @brief Set uniform value with type deduction
     */
    template<typename T>
    void setUniform(std::string_view name, T&& value) {
        uniforms_[std::string(name)] = std::forward<T>(value);
    }
    
    /**
     * @brief Apply all uniforms to GPU
     */
    void applyUniforms() const;
    
    // Conversion operators
    [[nodiscard]] explicit operator std::uint32_t() const noexcept {
        return handle_;
    }
    
    [[nodiscard]] bool operator==(const ShaderProgram& other) const noexcept {
        return handle_ == other.handle_;
    }
    
    [[nodiscard]] bool operator!=(const ShaderProgram& other) const noexcept {
        return !(*this == other);
    }
    
    // Three-way comparison
    [[nodiscard]] auto operator<=>(const ShaderProgram&) const = default;
    
    // Function call operator for binding
    void operator()() const;
    
    // Subscript operator for uniform access
    [[nodiscard]] const UniformValue& operator[](std::string_view name) const;
    
    // Arrow operator (smart pointer-like)
    [[nodiscard]] const ShaderProgram* operator->() const {
        return this;
    }
    
    // Dereference operator
    [[nodiscard]] const ShaderProgram& operator*() const {
        return *this;
    }
};

/**
 * @brief Scene graph node with transform hierarchy
 */
class SceneNode {
public:
    using NodePtr = std::shared_ptr<SceneNode>;
    using WeakPtr = std::weak_ptr<SceneNode>;
    
private:
    std::string name_;
    SceneNode* parent_{nullptr};
    std::vector<NodePtr> children_;
    std::array<float, 16> localTransform_{};
    mutable std::optional<std::array<float, 16>> worldTransform_;
    
public:
    explicit SceneNode(std::string name) : name_(std::move(name)) {}
    
    /**
     * @brief Factory method with shared_ptr
     */
    template<typename... Args>
    [[nodiscard]] static NodePtr create(Args&&... args) {
        return std::make_shared<SceneNode>(std::forward<Args>(args)...);
    }
    
    /**
     * @brief Add child node
     */
    NodePtr addChild(NodePtr child) {
        child->parent_ = this;
        children_.push_back(std::move(child));
        return children_.back();
    }
    
    /**
     * @brief Create and add child in one operation
     */
    template<typename... Args>
    NodePtr emplaceChild(Args&&... args) {
        auto child = create(std::forward<Args>(args)...);
        return addChild(std::move(child));
    }
    
    /**
     * @brief Depth-first traversal with callback
     */
    template<typename Func>
    void traverse(Func&& func) {
        func(*this);
        for (auto& child : children_) {
            child->traverse(func);
        }
    }
    
    /**
     * @brief Const traversal
     */
    template<typename Func>
    void traverse(Func&& func) const {
        func(*this);
        for (const auto& child : children_) {
            child->traverse(func);
        }
    }
    
    [[nodiscard]] const std::string& name() const noexcept {
        return name_;
    }
    
    [[nodiscard]] SceneNode* parent() const noexcept {
        return parent_;
    }
    
    [[nodiscard]] const auto& children() const noexcept {
        return children_;
    }
    
    /**
     * @brief Compute world transform matrix
     */
    [[nodiscard]] const std::array<float, 16>& worldTransform() const;
};

/**
 * @brief Rendering context with state management
 */
class RenderContext {
public:
    /**
     * @brief Scoped state guard (RAII)
     */
    template<typename State>
    class StateGuard {
        RenderContext* ctx_;
        State oldState_;
        
    public:
        StateGuard(RenderContext& ctx, State newState)
            : ctx_(&ctx)
            , oldState_(ctx.state<State>()) {
            ctx.setState(newState);
        }
        
        ~StateGuard() {
            ctx_->setState(oldState_);
        }
        
        // No copy, no move
        StateGuard(const StateGuard&) = delete;
        StateGuard& operator=(const StateGuard&) = delete;
        StateGuard(StateGuard&&) = delete;
        StateGuard& operator=(StateGuard&&) = delete;
    };
    
private:
    std::uint32_t fbo_{0};
    std::uint32_t viewport_[4]{};
    ShaderProgram* currentShader_{nullptr};
    
public:
    RenderContext() = default;
    
    /**
     * @brief Begin render pass
     */
    void beginPass(std::uint32_t fbo, const std::uint32_t viewport[4]);
    
    /**
     * @brief End render pass
     */
    void endPass();
    
    /**
     * @brief Bind shader program
     */
    void bindShader(ShaderProgram& shader);
    
    /**
     * @brief Draw arrays
     */
    void drawArrays(std::size_t count);
    
    /**
     * @brief Draw indexed
     */
    void drawIndexed(std::size_t count);
    
    /**
     * @brief Get current state
     */
    template<typename State>
    [[nodiscard]] State state() const;
    
    /**
     * @brief Set state
     */
    template<typename State>
    void setState(State state);
    
    /**
     * @brief Create state guard
     */
    template<typename State>
    [[nodiscard]] StateGuard<State> scopedState(State newState) {
        return StateGuard<State>(*this, newState);
    }
};

// Inline namespace for versioning
inline namespace v2 {
    /**
     * @brief Current version of the render engine
     */
    constexpr Version currentVersion{1, 0, 0};
}

// Anonymous namespace for internal linkage
namespace {
    /**
     * @brief Internal helper for format conversion
     */
    constexpr auto internalFormat = [](std::uint32_t fmt) -> std::uint32_t {
        return fmt == 0 ? 6408 : fmt;  // GL_RGBA = 6408
    };
}

} // namespace engine

#endif // ENTERPRISE_RENDER_ENGINE_HPP