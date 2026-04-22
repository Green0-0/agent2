/**
 * @fileoverview Data Stream Processor
 * Exhaustive coverage of module syntax, async/generator patterns,
 * destructuring, and control flow.
 */

// Every import variant
import defaultLogger from "./logger";
import * as utils from "./utils";
import { parse, stringify, transform as tx } from "./transforms";
import { fetchStream as fetcher, retry } from "./network";
import { default as Config, version as VER } from "./config";
import DefaultExport, { named1, named2 } from "./mixed";
import DefaultAll, * as AllNs from "./namespace";
import "./side-effects";

// Re-exports
export * from "./types";
export { helper, utility } from "./helpers";
export { default as Primary, named as Secondary } from "./primary";

// Local bindings for re-export
const localA = 1;
let localB = 2;
var localC = 3;

/**
 * Stream configuration with deep defaults.
 * @param {object} options
 * @param {string} [options.endpoint]
 * @param {object} [options.auth]
 * @param {string} [options.auth.token]
 * @param {number} [options.auth.expiresIn=3600]
 * @param {string[]} [options.auth.scopes=[]]
 * @param {object} [options.retry]
 * @param {number} [options.retry.max=3]
 * @param {number} [options.retry.delay=1000]
 * @param {boolean} [options.retry.exponential=true]
 */
function createConfig({
  endpoint = "https://api.example.com",
  auth: {
    token = "",
    expiresIn = 3600,
    scopes = []
  } = {},
  retry: {
    max = 3,
    delay = 1000,
    exponential = true
  } = {},
  ...unknownOptions
} = {}) {
  return {
    endpoint,
    auth: { token, expiresIn, scopes },
    retry: { max, delay, exponential },
    extras: unknownOptions
  };
}

/**
 * Async generator with error boundaries and delegation.
 * @async
 * @generator
 * @param {ReadableStream} stream
 * @yields {object}
 */
async function* streamChunks(stream) {
  const reader = stream.getReader();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      yield value;
    }
  } catch (streamError) {
    console.error("Stream failure:", streamError);
    throw streamError;
  } finally {
    reader.releaseLock();
  }
}

/**
 * Generator delegating to multiple sources.
 * @generator
 * @param {any[]} sources
 * @yields {any}
 */
function* multiplex(...sources) {
  for (const source of sources) {
    if (source[Symbol.asyncIterator]) {
      yield* (async function* () {
        for await (const item of source) {
          yield { type: "async", item };
        }
      })();
    } else if (source[Symbol.iterator]) {
      yield* (function* () {
        for (const item of source) {
          yield { type: "sync", item };
        }
      })();
    } else {
      yield { type: "scalar", item: source };
    }
  }
}

/**
 * Complex class with async iterator protocol.
 */
class DataPipeline {
  /** @type {Array<{stage: string, fn: Function}>} */
  #stages = [];
  /** @type {AbortController|null} */
  #controller = null;

  /**
   * @param {object} [config]
   */
  constructor(config) {
    this.config = createConfig(config);
    this.#controller = new AbortController();
    const { signal } = this.#controller;

    // Closure capturing signal
    this.isAborted = () => signal.aborted;
  }

  /**
   * Add a processing stage.
   * @param {string} name
   * @param {Function} processor
   * @returns {DataPipeline}
   */
  stage(name, processor) {
    this.#stages.push({ stage: name, fn: processor });
    return this;
  }

  /**
   * Process iterable through all stages.
   * @async
   * @generator
   * @param {AsyncIterable<any>} input
   */
  async *process(input) {
    let stream = input;
    for (const { stage, fn } of this.#stages) {
      stream = await this.#applyStage(stream, fn, stage);
    }
    yield* stream;
  }

  /**
   * @private
   * @async
   * @generator
   */
  async *#applyStage(source, fn, stageName) {
    let index = 0;
    for await (const item of source) {
      try {
        const result = await fn(item, index++, stageName);
        if (result !== undefined) yield result;
      } catch (err) {
        if (this.config.retry.max > 0) {
          yield await this.#retry(fn, item, index, stageName);
        } else {
          throw err;
        }
      }
    }
  }

  /**
   * Retry wrapper with exponential backoff.
   * @private
   * @async
   */
  async #retry(fn, item, index, stageName) {
    let attempt = 0;
    let wait = this.config.retry.delay;
    while (attempt < this.config.retry.max) {
      try {
        return await fn(item, index, stageName);
      } catch {
        attempt++;
        if (attempt >= this.config.retry.max) throw new Error("Max retries");
        await new Promise((r) => setTimeout(r, wait));
        wait *= this.config.retry.exponential ? 2 : 1;
      }
    }
  }

  /**
   * Dynamic import with top-level await pattern (inside async method).
   * @async
   */
  async loadPlugin(name) {
    const module = await import(`./plugins/${name}.js`);
    if (module.default) {
      await module.default(this);
    }
    return module;
  }

  /**
   * Cleanup.
   */
  abort() {
    this.#controller?.abort();
  }
}

// Top-level complex expressions with destructuring
const pipeline = new DataPipeline({
  endpoint: "wss://stream.example.com",
  auth: {
    token: process.env.TOKEN,
    scopes: ["read", "write"]
  }
});

// Complex destructuring with renaming and nesting
const {
  endpoint: url,
  auth: {
    token: authToken,
    scopes: [firstScope, ...otherScopes]
  },
  retry: { max: maxRetries }
} = pipeline.config;

// Array destructuring with defaults and rest
const [head = "default", second, , fourth, ...tail] = await (async () => {
  return [1, 2, 3, 4, 5, 6];
})();

// Sequence expression in variable init
const sequence = (console.log("side effect"), 42);

// Void and typeof expressions
const undefinedCheck = void 0;
const typeName = typeof pipeline;

// Export the pipeline instance and classes
export { DataPipeline, createConfig, streamChunks, multiplex };
export const configuredPipeline = pipeline;
export default DataPipeline;