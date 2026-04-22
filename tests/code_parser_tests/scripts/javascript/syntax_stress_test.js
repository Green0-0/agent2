// ASI trap: return on its own line followed by object literal
function asiTrap() {
  return
  {
    status: "success"
  }
}

// ASI trap with regex
function asiRegex() {
  return
  /regex/g
}

// Division vs regex ambiguity
const divideThenRegex = 1 / 2 / /three/.exec("three").length;
const regexThenDivide = /abc/ / 2;
const ambiguous = (1) / /abc/g.exec("abc").length;

// Ternary vs object literal ambiguity
const ternaryObj = condition
  ? {a: 1, b: 2}
  : condition2
    ? {c: 3}
    : {d: 4};

// Nested ternaries without grouping
const nestedTernary = a ? b ? c ? d : e : f : g ? h : i;

// Block statement vs object literal in arrow bodies
const blockArrow = (x) => { x = x + 1; return x; };
const objArrow = (x) => ({ value: x, doubled: x * 2 });

// Concise body with implicit return of object
const conciseObj = x => ({
  original: x,
  negated: -x,
  boolean: !!x
});

// Labeled statement (not object)
function labeledBreak() {
  outer: while (true) {
    inner: for (let i = 0; i < 10; i++) {
      if (i === 5) break outer;
      if (i % 2 === 0) continue inner;
      console.log(i);
    }
  }
}

// Switch with default in middle and fallthrough
function switchMess(x) {
  switch (x) {
    case 1:
      console.log("one");
    case 2:
      console.log("two");
      break;
    default:
      console.log("default");
    case 3:
      console.log("three");
      // falls through
    case 4:
      console.log("four");
      break;
  }
}

// Empty function bodies and statements
function empty() {}
const emptyArrow = () => {};
if (true) /* empty */; else /* also empty */;
for (;;) break;
while (false) /* never */;
do { /* once */ } while (false);

// Debugger statement
debugger;

// Double arrow chain with grouping ambiguity
const curry = (a) => (b) => (c) => (d) => a + b + c + d;

// Unary operator chains
const bitwise = ~~x;
const neg = - -x;
const notnot = !! !!y;
const typeVoid = typeof void 0;
const deleteProp = delete obj.prop;
const expPrecedence = 2 ** 3 ** 2; // 512, not 64

// Parenthesized destructuring (valid in assignment contexts)
let pDestruct;
({ a: pDestruct } = { a: 1 });
[pDestruct] = [2];

// Complex destructuring in parameters with rest and defaults
const complexParams = (
  {
    host = "localhost",
    port = 3000,
    ssl: {
      cert = "",
      key = "",
      ca = []
    } = {},
    middleware: [firstMw, ...restMw] = []
  } = {},
  ...extraArgs
) => {
  return { host, port, cert, key, ca, firstMw, restMw, extraArgs };
};

// Spread in all valid positions
const spreadArr = [1, ...[2, 3], 4];
const spreadObj = { a: 1, ...{ b: 2 }, c: 3 };
const spreadCall = Math.max(...spreadArr, ...spreadObj);

// Empty class and subclass
class Empty {}
class EmptyExtends extends EventTarget {}

// Class with all member types
class FullClass {
  static staticField = 42;
  static {
    this.staticField = this.compute();
  }
  static compute() { return 42; }

  instanceField = "field";
  boundMethod = (e) => this.handle(e);
  #privateField = 0;
  #privateMethod() {
    return this.#privateField++;
  }

  constructor(value) {
    this.value = value;
  }

  get accessor() {
    return this.value;
  }

  set accessor(v) {
    this.value = v;
  }

  async asyncMethod() {
    return await Promise.resolve(this.value);
  }

  *generatorMethod() {
    yield this.value;
    yield* [1, 2, 3];
  }

  async *asyncGeneratorMethod() {
    yield await Promise.resolve(this.value);
  }

  handle(e) {
    return e.type;
  }
}

// Function named 'async' (identifier, not keyword)
function async() {
  return 1;
}

// Object with async-named properties
const asyncObj = {
  async: function() {},
  async async() {},
  get async() { return 1; },
  set async(v) { this._v = v; }
};

// Unicode escapes in identifiers
const \u0061 = 1; // 'a'
const \u{62} = 2; // 'b'
const ℮ = 2.71828;

// Template literals with nested expressions and line breaks
const name = "world";
const nestedTemplate = `Hello ${`inner ${name.toUpperCase()}`}, 
  ${(() => "IIFE in template")()},
  ${complexParams({ host: "test" }).host}`;

// Tagged template literal with complex tag
function sqlTag(strings, ...values) {
  return { query: strings.join("?"), values };
}
const query = sqlTag`SELECT * FROM users WHERE id = ${userId} AND name = ${name}`;

// Regex with character classes that look like comments/division
const regex1 = /a[b/*]c/;
const regex2 = /\/\//g;
const regex3 = /[\]]/;

// New.target and import.meta
function ConstructorCheck() {
  if (new.target) {
    this.createdWithNew = true;
  }
}
const metaUrl = import.meta.url;

// IIFE variations
const iife1 = (function() { return 1; })();
const iife2 = (function namedIIFE() { return 2; }());
const iife3 = ((x) => x + 1)(5);
const iife4 = (async function() { return await 1; })();

// Sequence expressions
const seq = (1, 2, 3, 4);

// New without parentheses
const date1 = new Date;
const anonClass = new class { value = 42; };

// Complex try/catch/finally with nested functions
function errorProne() {
  try {
    return (function() {
      try {
        throw new Error("inner");
      } catch (e) {
        return e.message;
      }
    })();
  } catch (outer) {
    return "outer caught";
  } finally {
    console.log("finally runs");
  }
}

// Comma-first style object (valid, weird layout)
const commaFirst = {
    first: 1
  , second: 2
  , third: 3
};

// Operators at start of line (ASI-sensitive)
const math = 1
  + 2
  - 3
  * 4
  / 5
  % 6
  ** 7;

// Chained optional chaining and nullish coalescing
const deepOptional = obj
  ?.prop
  ?.method?.()
  ?? "fallback";

// Logical assignment operators
let la1 = null;
let la2 = 0;
let la3 = "";
la1 ??= "default";
la2 ||= 1;
la3 &&= "filled";

// BigInt and numeric separators
const bigNum = 1_000_000_000n;
const hex = 0xFF_FF;
const binary = 0b1010_1010;

// Export everything stress-test relevant
export {
  asiTrap,
  curry,
  FullClass,
  complexParams,
  labeledBreak,
  switchMess,
  errorProne
};
export default FullClass;