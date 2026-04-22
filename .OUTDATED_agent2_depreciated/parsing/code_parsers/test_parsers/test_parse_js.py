# ────────── script_js_1 ──────────
script_js_1 = r'''
/**
 * Module-level JSDoc
 * Demonstrates almost every construct.
 */

import fs from 'fs';                    // plain import
import { join } from 'path';

export const VERSION = '1.0.0';         // still part of top_level_block_0

@moduleDecorator
export async function topLevel(name) {
    /** Docstring of topLevel */
    if (!name) return;

    async function nestedA(param) {
        /** Doc nestedA */
        return param.toUpperCase();
    }

    const arrowFun = (x) => {
        /** arrow doc */
        return nestedA(x);
    };

    class InlineClass {
        /** InlineClass doc */
        method() {}
    }

    return arrowFun(name);
}

@sealed
@logger('Outer')
class Outer {
    /** Docstring Outer */
    #secret = 42;

    @readonly
    static staticMeth() {}

    methodOne() {
        /** methodOne doc */
        function innerFn() {
            /** doc innerFn */
            return 'inner';
        }

        const innerArrow = (v) => {
            class DeepClass {
                deep() {}
            }
            return v + this.#secret;
        };

        return innerArrow(innerFn());
    }

    // nested class expressed as a static field
    static Nested = class Nested {
        /** Nested doc */
        @decor
        nestedMethod() {}
    };
}

const globalArrow = (a, b) => a + b;

export default class DefaultCls {
    constructor() {}
}
'''

# ────────── script_js_2 ──────────
script_js_2 = r'''
/** Second script doc */
const util = require('util');

function useless() {}

export default function () {
    /** anonymous default export doc */
    const local = () => 123;
    return local();
}

export class Alpha {
    beta() {
        const gamma = () => {
            function delta() {}
            return delta;                 // becomes top_level_block inside beta
        };
        return gamma();
    }
}

@decor
export const eps = (x) => {
    /** eps doc */
    return x * x;
};

if (import.meta.main) {
    console.log('run');
}
'''

from agent2.parsing.code_parsers.parse_javascript import parse_javascript_elements


def dump(elems, depth=0):
    pad = "    " * depth
    for e in elems:
        print(f"{pad}{e.identifier:55}  line={e.line_start:>3}  header={e.header!r}")
        if e.description:
            first = e.description.splitlines()[0]
            print(f"{pad}    docstring: {first!r}")
        dump(e.elements, depth + 1)


print("===============  SCRIPT JS-1  ===============\n")
elems1 = parse_javascript_elements(script_js_1)
dump(elems1)

print("\n===============  SCRIPT JS-2  ===============\n")
elems2 = parse_javascript_elements(script_js_2)
dump(elems2)
