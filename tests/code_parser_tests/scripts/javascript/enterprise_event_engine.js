import { EventEmitter } from "events";
import { promisify } from "util";

/**
 * Base mixin factory that adds timestamp functionality.
 * @param {typeof BaseEntity} Base - The base class to extend.
 * @returns {typeof TimestampedEntity} The mixed-in class.
 */
const Timestamped = (Base) => class TimestampedEntity extends Base {
  /** @type {number} Epoch ms at creation. */
  createdAt = Date.now();

  /**
   * Get elapsed time since creation.
   * @returns {number} Milliseconds elapsed.
   */
  getAge() {
    return Date.now() - this.createdAt;
  }
};

/**
 * Abstract base for all entities in the system.
 * @abstract
 */
class BaseEntity {
  /** @type {string} Unique identifier. */
  #id;

  /**
   * @param {string} id - The entity identifier.
   */
  constructor(id) {
    if (new.target === BaseEntity) {
      throw new TypeError("Cannot instantiate abstract BaseEntity directly");
    }
    this.#id = id;
    Object.defineProperty(this, "uuid", {
      value: `${id}-${Math.random().toString(36).slice(2)}`,
      writable: false,
      configurable: true
    });
  }

  /**
   * Retrieve the private ID.
   * @protected
   * @returns {string}
   */
  _getId() {
    return this.#id;
  }

  /**
   * Abstract serialization method.
   * @abstract
   * @returns {object}
   */
  toJSON() {
    throw new Error("Must implement toJSON");
  }
}

/**
 * Concrete entity with timestamp mixin.
 * @extends BaseEntity
 */
class EventTarget extends Timestamped(BaseEntity) {
  /** @type {Map<string, Function[]>} */
  #listeners = new Map();
  /** @type {WeakMap<object, symbol>} */
  static #tokenMap = new WeakMap();

  /**
   * Static initialization block with complex logic.
   */
  static {
    const meta = import.meta;
    this.platform = meta?.url ? "module" : "script";
    this.registry = new FinalizationRegistry((heldValue) => {
      console.log(`Cleaned up: ${heldValue}`);
    });
  }

  /**
   * @param {string} name - Event target name.
   * @param {object} [options={}] - Configuration options.
   * @param {boolean} [options.capture=false] - Use capture phase.
   * @param {number} [options.priority=0] - Handler priority.
   */
  constructor(name, options = {}) {
    super(name);
    this.name = name;
    this.options = options;
  }

  /**
   * Register an event listener.
   * @param {string} type - Event type.
   * @param {Function} callback - Handler function.
   * @param {object} [opts] - Listener options.
   * @returns {symbol} Cancellation token.
   */
  on(type, callback, opts = {}) {
    const token = Symbol(type);
    if (!this.#listeners.has(type)) {
      this.#listeners.set(type, []);
    }
    this.#listeners.get(type).push({ callback, opts, token });
    EventTarget.#tokenMap.set(callback, token);
    return token;
  }

  /**
   * Emit an event synchronously.
   * @param {string} type - Event type.
   * @param  {...any} args - Arguments to handlers.
   * @returns {boolean} Whether any listener was called.
   */
  emit(type, ...args) {
    const listeners = this.#listeners.get(type) || [];
    for (const { callback } of listeners) {
      try {
        callback.apply(this, args);
      } catch (err) {
        console.error(err);
      }
    }
    return listeners.length > 0;
  }

  /**
   * Async generator yielding events of a given type.
   * @async
   * @generator
   * @param {string} type - Event type to listen for.
   * @yields {object} Event payload.
   */
  async *events(type) {
    const buffer = [];
    this.on(type, (payload) => buffer.push(payload));
    while (true) {
      if (buffer.length > 0) {
        yield buffer.shift();
      } else {
        await new Promise((r) => setTimeout(r, 10));
      }
    }
  }

  /** @override */
  toJSON() {
    return {
      name: this.name,
      id: this._getId(),
      age: this.getAge(),
      options: this.options
    };
  }
}

/**
 * Advanced event engine with scheduling, debouncing, and proxy interception.
 * @extends EventTarget
 */
class EventEngine extends EventTarget {
  /** @type {Set<symbol>} Active timer symbols. */
  #timers = new Set();
  /** @type {number} Internal counter. */
  static #instanceCount = 0;

  /**
   * Nested helper class for scheduled tasks.
   * Not exported directly.
   */
  static Task = class ScheduledTask {
    /**
     * @param {Function} fn - Function to execute.
     * @param {number} delay - Delay in ms.
     * @param {boolean} [recurring=false] - Whether to repeat.
     */
    constructor(fn, delay, recurring = false) {
      this.fn = fn;
      this.delay = delay;
      this.recurring = recurring;
      this.executions = 0;
    }

    /**
     * Execute the task.
     * @param {any} context - `this` context.
     * @returns {any} Result of execution.
     */
    execute(context) {
      this.executions++;
      return this.fn.call(context);
    }
  };

  /**
   * @param {string} namespace - Engine namespace.
   * @param {object} config - Engine configuration.
   * @param {number} [config.debounceMs=100] - Default debounce window.
   * @param {boolean} [config.strict=true] - Strict mode enabled.
   */
  constructor(namespace, config) {
    super(namespace, { capture: true, priority: 10 });
    EventEngine.#instanceCount++;
    this.config = {
      debounceMs: 100,
      strict: true,
      ...config
    };
    this.history = [];
    return new Proxy(this, {
      get(target, prop, receiver) {
        if (prop === "state") {
          return "proxied";
        }
        return Reflect.get(target, prop, receiver);
      },
      set(target, prop, value) {
        if (prop === "frozen") {
          throw new Error("Cannot modify frozen engine");
        }
        return Reflect.set(target, prop, value);
      }
    });
  }

  /**
   * Debounced event emission.
   * @param {string} type - Event type.
   * @param {object} payload - Event payload.
   * @param {object} [opts] - Debounce options.
   * @param {number} [opts.wait] - Override wait time.
   */
  debounce(type, payload, opts = {}) {
    const wait = opts.wait ?? this.config.debounceMs;
    const key = Symbol.for(`${type}:debounce`);
    if (this.#timers.has(key)) {
      clearTimeout(key);
      this.#timers.delete(key);
    }
    const timer = setTimeout(() => {
      this.emit(type, payload);
      this.#timers.delete(key);
    }, wait);
    this.#timers.add(key);
  }

  /**
   * Complex pipeline: async generator with delegation.
   * @async
   * @generator
   * @param {AsyncIterable<any>} source - Source stream.
   * @yields {any} Processed values.
   */
  async *pipe(source) {
    let count = 0;
    yield* (async function* () {
      for await (const chunk of source) {
        if (chunk == null) continue;
        yield chunk;
      }
    })();
    yield { done: true, count };
  }

  /**
   * Get instance count.
   * @static
   * @returns {number}
   */
  static getInstanceCount() {
    return this.#instanceCount;
  }

  /** @returns {string} */
  get [Symbol.toStringTag]() {
    return "EventEngine";
  }

  /** @async */
  async [Symbol.asyncIterator]() {
    return this.events("*");
  }
}

/**
 * Singleton registry managing all engines.
 */
class Registry {
  /** @type {Registry|null} */
  static #instance = null;
  /** @type {Map<string, EventEngine>} */
  #engines = new Map();

  /** @private */
  constructor() {
    if (Registry.#instance) {
      throw new Error("Use Registry.getInstance()");
    }
  }

  /** @returns {Registry} */
  static getInstance() {
    return this.#instance ??= new Registry();
  }

  /**
   * Register an engine.
   * @param {EventEngine} engine
   */
  register(engine) {
    this.#engines.set(engine.name, engine);
  }

  /**
   * Retrieve engine by path-like string.
   * @param {string} path - Dot-separated path.
   * @returns {EventEngine|undefined}
   */
  resolve(path) {
    return path.split(".").reduce((curr, part) => {
      return curr?.[part];
    }, { root: Object.fromEntries(this.#engines) }).root;
  }
}

// Top-level execution block
const engine = new EventEngine("main", { debounceMs: 250, strict: false });
const registry = Registry.getInstance();
registry.register(engine);

// Arrow function with complex destructuring and defaults
const init = async ({ debug = false, plugins = [] } = {}) => {
  if (debug) debugger;
  for (const plugin of plugins) {
    await plugin(engine);
  }
  return engine;
};

export { EventEngine, Registry, init };
export default EventEngine;