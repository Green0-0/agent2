#ifndef ENTERPRISE_KERNEL_MODULE_C
#define ENTERPRISE_KERNEL_MODULE_C

#include <stdatomic.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/**
 * @brief Module version information
 */
#define MODULE_NAME "enterprise_kernel"
#define MODULE_VERSION_MAJOR 1
#define MODULE_VERSION_MINOR 0
#define MODULE_VERSION_PATCH 0

/**
 * @brief Stringify macros
 */
#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#define CONCAT(a, b) a##b

/**
 * @brief Version string construction
 */
#define MODULE_VERSION_STRING \
    TOSTRING(MODULE_VERSION_MAJOR) "." \
    TOSTRING(MODULE_VERSION_MINOR) "." \
    TOSTRING(MODULE_VERSION_PATCH)

/**
 * @brief Alignment macro
 */
#define ALIGN_UP(x, align) (((x) + (align) - 1) & ~((align) - 1))
#define ALIGN_DOWN(x, align) ((x) & ~((align) - 1))

/**
 * @brief Container of macro (similar to Linux kernel)
 */
#define container_of(ptr, type, member) \
    ((type *)((char *)(ptr) - offsetof(type, member)))

/**
 * @brief Static assertion
 */
#define STATIC_ASSERT(expr) _Static_assert(expr, #expr)

/**
 * @brief Compile-time array size
 */
#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))

/**
 * @brief Min/max macros with safe double evaluation
 */
#define MIN(a, b) ({ \
    __typeof__(a) _a = (a); \
    __typeof__(b) _b = (b); \
    _a < _b ? _a : _b; \
})

#define MAX(a, b) ({ \
    __typeof__(a) _a = (a); \
    __typeof__(b) _b = (b); \
    _a > _b ? _a : _b; \
})

/**
 * @brief Memory barrier macro
 */
#define MEMORY_BARRIER() __atomic_thread_fence(__ATOMIC_SEQ_CST)

/**
 * @brief Error codes enumeration
 */
typedef enum {
    ERR_OK = 0,
    ERR_NOMEM = -1,
    ERR_INVAL = -2,
    ERR_BUSY = -3,
    ERR_NOTFOUND = -4,
    ERR_IO = -5,
    ERR_TIMEOUT = -6,
    ERR_OVERFLOW = -7,
    ERR_UNDERFLOW = -8,
} error_code_t;

/**
 * @brief Device state enumeration with explicit values
 */
typedef enum device_state {
    DEVICE_UNINITIALIZED = 0x00,
    DEVICE_INITIALIZING = 0x01,
    DEVICE_READY = 0x02,
    DEVICE_RUNNING = 0x03,
    DEVICE_SUSPENDED = 0x04,
    DEVICE_SHUTTING_DOWN = 0x05,
    DEVICE_DEAD = 0xFF,
} device_state_t;

/**
 * @brief Interrupt type flags (bitmask)
 */
typedef enum interrupt_flags {
    IRQ_NONE = 0x0000,
    IRQ_EDGE_RISING = 0x0001,
    IRQ_EDGE_FALLING = 0x0002,
    IRQ_LEVEL_HIGH = 0x0004,
    IRQ_LEVEL_LOW = 0x0008,
    IRQ_SHARED = 0x0010,
    IRQ_THREADED = 0x0020,
    IRQ_NO_SUSPEND = 0x0040,
} interrupt_flags_t;

/**
 * @brief Hardware register layout with bitfields
 * 
 * This structure demonstrates precise memory layout control
 * using bitfields and packed attributes.
 */
typedef struct __attribute__((packed)) hw_register {
    union {
        struct {
            uint32_t enable : 1;        /**< Module enable */
            uint32_t reset : 1;         /**< Soft reset */
            uint32_t mode : 3;          /**< Operating mode */
            uint32_t reserved1 : 3;     /**< Reserved */
            uint32_t irq_enable : 1;    /**< Interrupt enable */
            uint32_t dma_enable : 1;    /**< DMA enable */
            uint32_t reserved2 : 6;     /**< Reserved */
            uint32_t status : 8;        /**< Status code */
            uint32_t error : 8;         /**< Error code */
        } bits;
        uint32_t raw;                   /**< Raw 32-bit access */
    };
} hw_register_t;

STATIC_ASSERT(sizeof(hw_register_t) == 4);

/**
 * @brief Memory buffer descriptor with flexible array member
 */
typedef struct buffer_desc {
    size_t capacity;                    /**< Total capacity */
    size_t used;                        /**< Currently used bytes */
    uint32_t flags;                     /**< Buffer flags */
    atomic_uint ref_count;              /**< Reference count */
    
    /**
     * @brief Anonymous union for different access modes
     */
    union {
        uint8_t *bytes;                 /**< Byte access */
        uint16_t *words;                /**< Word access */
        uint32_t *dwords;               /**< Dword access */
        void *generic;                  /**< Generic pointer */
    };
    
    /**
     * @brief Flexible array member for inline storage
     */
    alignas(64) uint8_t inline_data[];
} buffer_desc_t;

/**
 * @brief I/O operation types
 */
typedef enum io_op_type {
    IO_OP_READ,
    IO_OP_WRITE,
    IO_OP_FLUSH,
    IO_OP_SEEK,
    IO_OP_IOCTL,
    IO_OP_MMAP,
} io_op_type_t;

/**
 * @brief I/O request structure
 */
typedef struct io_request {
    io_op_type_t type;                  /**< Operation type */
    uint64_t offset;                    /**< Device offset */
    size_t length;                      /**< Transfer length */
    void *buffer;                       /**< User buffer */
    uint32_t flags;                     /**< Request flags */
    
    /**
     * @brief Completion callback
     */
    void (*complete)(struct io_request *req, error_code_t status, size_t transferred);
    
    /**
     * @brief Private data for callback
     */
    void *private_data;
    
    /**
     * @brief Linked list node
     */
    struct io_request *next;
    struct io_request **pprev;
} io_request_t;

/**
 * @brief Device operations vtable (like Linux file_operations)
 */
typedef struct device_ops {
    /**
     * @brief Open device
     */
    int (*open)(void *dev, uint32_t flags);
    
    /**
     * @brief Close device
     */
    int (*release)(void *dev);
    
    /**
     * @brief Read from device
     */
    ssize_t (*read)(void *dev, char *buf, size_t len, uint64_t offset);
    
    /**
     * @brief Write to device
     */
    ssize_t (*write)(void *dev, const char *buf, size_t len, uint64_t offset);
    
    /**
     * @brief Control device
     */
    long (*ioctl)(void *dev, unsigned int cmd, unsigned long arg);
    
    /**
     * @brief Memory map
     */
    int (*mmap)(void *dev, void *vma);
    
    /**
     * @brief Poll/select
     */
    unsigned int (*poll)(void *dev, unsigned int events);
    
    /**
     * @brief Asynchronous I/O
     */
    int (*aio_read)(void *dev, io_request_t *req);
    int (*aio_write)(void *dev, io_request_t *req);
    
    /**
     * @brief Splice (zero-copy transfer)
     */
    ssize_t (*splice_read)(void *dev, uint64_t *offset, void *pipe, size_t len, unsigned int flags);
    
    /**
     * @brief Compatibility ioctl
     */
    long (*compat_ioctl)(void *dev, unsigned int cmd, unsigned long arg);
    
    /**
     * @brief Lock operation
     */
    int (*lock)(void *dev, int cmd, void *flock);
    
    /**
     * @brief Fsync
     */
    int (*fsync)(void *dev, uint64_t start, uint64_t end, int datasync);
    
    /**
     * @brief Fasync (async notification)
     */
    int (*fasync)(int fd, void *filp, int on);
    
    /**
     * @brief Check flags
     */
    int (*check_flags)(int flags);
    
    /**
     * @brief Flock
     */
    int (*flock)(void *dev, int cmd, void *flock);
    
    /**
     * @brief Sendpage
     */
    ssize_t (*sendpage)(void *dev, void *page, int offset, size_t size, uint64_t *pos, int more);
    
    /**
     * @brief Get unmapped area
     */
    unsigned long (*get_unmapped_area)(void *dev, unsigned long addr, unsigned long len, unsigned long pgoff, unsigned long flags);
    
    /**
     * @brief Copy file range
     */
    ssize_t (*copy_file_range)(void *dev_in, uint64_t *pos_in, void *dev_out, uint64_t *pos_out, size_t len, unsigned int flags);
    
    /**
     * @brief Clone file range
     */
    int (*clone_file_range)(void *dev_in, uint64_t pos_in, void *dev_out, uint64_t pos_out, uint64_t len);
    
    /**
     * @brief Dedupe file range
     */
    int (*dedupe_file_range)(void *dev_src, uint64_t pos_src, void *dev_dst, uint64_t pos_dst, uint64_t len);
    
    /**
     * @brief Iterate directory
     */
    int (*iterate)(void *dev, void *ctx);
    
    /**
     * @brief Iterate shared
     */
    int (*iterate_shared)(void *dev, void *ctx);
} device_ops_t;

/**
 * @brief Hardware device structure
 */
typedef struct hw_device {
    /**
     * @brief Device metadata
     */
    struct {
        char name[64];
        char vendor[64];
        uint32_t device_id;
        uint32_t vendor_id;
        uint32_t revision;
    } info;
    
    /**
     * @brief Current state (atomic)
     */
    _Atomic device_state_t state;
    
    /**
     * @brief Reference count
     */
    atomic_uint ref_count;
    
    /**
     * @brief Hardware registers (volatile)
     */
    volatile hw_register_t *regs;
    
    /**
     * @brief Base memory address
     */
    void __iomem *base_addr;
    
    /**
     * @brief Memory region size
     */
    size_t mem_size;
    
    /**
     * @brief IRQ number
     */
    int irq;
    
    /**
     * @brief IRQ flags
     */
    interrupt_flags_t irq_flags;
    
    /**
     * @brief Device operations
     */
    const device_ops_t *ops;
    
    /**
     * @brief Private driver data
     */
    void *driver_data;
    
    /**
     * @brief DMA pool
     */
    struct {
        void *pool;
        size_t pool_size;
        atomic_size_t used;
    } dma;
    
    /**
     * @brief Power management
     */
    struct {
        uint32_t current_state;
        uint32_t target_state;
        void (*suspend)(struct hw_device *dev);
        void (*resume)(struct hw_device *dev);
        void (*shutdown)(struct hw_device *dev);
    } pm;
    
    /**
     * @brief Statistics
     */
    struct {
        atomic_uint_fast64_t bytes_read;
        atomic_uint_fast64_t bytes_written;
        atomic_uint_fast64_t io_errors;
        atomic_uint_fast64_t irq_count;
    } stats;
    
    /**
     * @brief Linked list of devices
     */
    struct hw_device *next;
    struct hw_device **pprev;
    
    /**
     * @brief Lock
     */
    atomic_flag lock;
} hw_device_t;

/**
 * @brief Interrupt handler type
 */
typedef irqreturn_t (*irq_handler_t)(int irq, void *dev_id);

/**
 * @brief IRQ return values
 */
typedef enum irqreturn {
    IRQ_NONE = 0,
    IRQ_HANDLED = 1,
    IRQ_WAKE_THREAD = 2,
} irqreturn_t;

/**
 * @brief Work queue item
 */
typedef struct work_struct {
    struct list_head entry;
    void (*func)(struct work_struct *work);
    atomic_t pending;
} work_struct_t;

/**
 * @brief Timer structure
 */
typedef struct timer_list {
    struct hlist_node entry;
    unsigned long expires;
    void (*function)(struct timer_list *timer);
    uint32_t flags;
} timer_list_t;

/**
 * @brief Simple list head
 */
typedef struct list_head {
    struct list_head *next;
    struct list_head *prev;
} list_head_t;

/**
 * @brief Hash list node
 */
typedef struct hlist_node {
    struct hlist_node *next;
    struct hlist_node **pprev;
} hlist_node_t;

/**
 * @brief Initialize list head
 */
static inline void INIT_LIST_HEAD(list_head_t *list) {
    list->next = list;
    list->prev = list;
}

/**
 * @brief List for each macro
 */
#define list_for_each(pos, head) \
    for (pos = (head)->next; pos != (head); pos = pos->next)

#define list_for_each_safe(pos, n, head) \
    for (pos = (head)->next, n = pos->next; pos != (head); pos = n, n = pos->next)

#define list_for_each_entry(pos, head, member) \
    for (pos = container_of((head)->next, __typeof__(*pos), member); \
         &pos->member != (head); \
         pos = container_of(pos->member.next, __typeof__(*pos), member))

/**
 * @brief Initialize device
 */
static int hw_device_init(hw_device_t *dev, const char *name, const device_ops_t *ops) {
    if (!dev || !name || !ops) {
        return ERR_INVAL;
    }
    
    memset(dev, 0, sizeof(*dev));
    
    strncpy(dev->info.name, name, sizeof(dev->info.name) - 1);
    dev->info.name[sizeof(dev->info.name) - 1] = '\0';
    
    atomic_init(&dev->ref_count, 1);
    atomic_init(&dev->state, DEVICE_UNINITIALIZED);
    
    INIT_LIST_HEAD((list_head_t *)&dev->next);
    
    dev->ops = ops;
    
    atomic_flag_clear(&dev->lock);
    
    return ERR_OK;
}

/**
 * @brief Reference counting
 */
static inline void hw_device_get(hw_device_t *dev) {
    if (dev) {
        atomic_fetch_add_explicit(&dev->ref_count, 1, memory_order_relaxed);
    }
}

static inline void hw_device_put(hw_device_t *dev) {
    if (dev && atomic_fetch_sub_explicit(&dev->ref_count, 1, memory_order_release) == 1) {
        MEMORY_BARRIER();
        /* Free device */
        free(dev);
    }
}

/**
 * @brief Lock device
 */
static inline void hw_device_lock(hw_device_t *dev) {
    while (atomic_flag_test_and_set_explicit(&dev->lock, memory_order_acquire)) {
        /* Spin */
    }
}

static inline void hw_device_unlock(hw_device_t *dev) {
    atomic_flag_clear_explicit(&dev->lock, memory_order_release);
}

/**
 * @brief Default device operations
 */
static int default_open(void *dev, uint32_t flags) {
    (void)dev;
    (void)flags;
    return ERR_OK;
}

static int default_release(void *dev) {
    (void)dev;
    return ERR_OK;
}

static ssize_t default_read(void *dev, char *buf, size_t len, uint64_t offset) {
    (void)dev;
    (void)buf;
    (void)len;
    (void)offset;
    return ERR_NOTFOUND;
}

static ssize_t default_write(void *dev, const char *buf, size_t len, uint64_t offset) {
    (void)dev;
    (void)buf;
    (void)len;
    (void)offset;
    return ERR_NOTFOUND;
}

static long default_ioctl(void *dev, unsigned int cmd, unsigned long arg) {
    (void)dev;
    (void)cmd;
    (void)arg;
    return ERR_INVAL;
}

/**
 * @brief Default operations vtable
 */
static const device_ops_t default_device_ops = {
    .open = default_open,
    .release = default_release,
    .read = default_read,
    .write = default_write,
    .ioctl = default_ioctl,
    .mmap = NULL,
    .poll = NULL,
    .aio_read = NULL,
    .aio_write = NULL,
    .splice_read = NULL,
    .compat_ioctl = NULL,
    .lock = NULL,
    .fsync = NULL,
    .fasync = NULL,
    .check_flags = NULL,
    .flock = NULL,
    .sendpage = NULL,
    .get_unmapped_area = NULL,
    .copy_file_range = NULL,
    .clone_file_range = NULL,
    .dedupe_file_range = NULL,
    .iterate = NULL,
    .iterate_shared = NULL,
};

/**
 * @brief Interrupt handler
 */
static irqreturn_t hw_irq_handler(int irq, void *dev_id) {
    hw_device_t *dev = dev_id;
    (void)irq;
    
    if (!dev) {
        return IRQ_NONE;
    }
    
    atomic_fetch_add_explicit(&dev->stats.irq_count, 1, memory_order_relaxed);
    
    hw_register_t reg = { .raw = dev->regs->raw };
    
    if (reg.bits.irq_enable && reg.bits.status) {
        /* Handle interrupt */
        reg.bits.status = 0;
        dev->regs->raw = reg.raw;
        return IRQ_HANDLED;
    }
    
    return IRQ_NONE;
}

/**
 * @brief Allocate buffer with flexible array member
 */
static buffer_desc_t *buffer_alloc(size_t capacity, uint32_t flags) {
    size_t size = sizeof(buffer_desc_t) + ALIGN_UP(capacity, 64);
    
    buffer_desc_t *buf = aligned_alloc(64, size);
    if (!buf) {
        return NULL;
    }
    
    memset(buf, 0, sizeof(*buf));
    buf->capacity = capacity;
    buf->used = 0;
    buf->flags = flags;
    atomic_init(&buf->ref_count, 1);
    buf->bytes = buf->inline_data;
    
    return buf;
}

/**
 * @brief Main module entry
 */
int module_init(void) {
    printf("Loading %s version %s\n", MODULE_NAME, MODULE_VERSION_STRING);
    
    hw_device_t *dev = calloc(1, sizeof(*dev));
    if (!dev) {
        return ERR_NOMEM;
    }
    
    int ret = hw_device_init(dev, "test-device", &default_device_ops);
    if (ret != ERR_OK) {
        free(dev);
        return ret;
    }
    
    /* Set state */
    atomic_store(&dev->state, DEVICE_READY);
    
    printf("Device %s initialized\n", dev->info.name);
    
    hw_device_put(dev);
    
    return ERR_OK;
}

/**
 * @brief Module exit
 */
void module_exit(void) {
    printf("Unloading %s\n", MODULE_NAME);
}

#endif /* ENTERPRISE_KERNEL_MODULE_C */