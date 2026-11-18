// Changes in 0.3.1: protected spans in linear time (as tests/test_changes_0_3_1.py
// for the Python library).
//
// In 0.3.0 four inputs took time quadratic in their length: a URL, a DOI or a
// path followed by a long run of ")"; "%" followed by a long run of zeros; a
// long run of labels with no ending (a.a.a...); and a long word of letters
// joined by apostrophes (a'a'a'...). Each fix keeps the output. The 0.3.0 code
// is kept below; the differential tests run it and the new code on the same
// random inputs (fixed seeds) and compare, and the time tests time an input
// that 0.3.0 took seconds over.

import assert from "node:assert/strict";
import { test } from "node:test";

import * as lib from "../src/index.js";
import {
  BARE_DOMAIN_RE,
  PRINTF_RE,
  TOKEN,
  findToken,
  isToken,
  searchBareDomain,
  trim,
} from "../src/protect.js";
import { APOSTROPHE_VARIANTS } from "../src/tables.js";
import { ASCII_ALNUM_CI_BODY, NOT_S, SPACE_BODY, W_BODY, ci, escapeRegExp, pyCount } from "../src/unicode.js";

// --- 0.3.0, as it was ------------------------------------------------------------------

const TRAILING = new Set(".,;:!?)»\"'");

function trim030(text, start, stop) {
  while (stop > start && TRAILING.has(text[stop - 1])) {
    if (text[stop - 1] === ")" && pyCount(text, "(", start, stop) >= pyCount(text, ")", start, stop)) break;
    stop -= 1;
  }
  return stop;
}

const PRINTF_030 = new RegExp(
  `(?<![${W_BODY}%])%(?:[0-9]+\\$)?(?:\\([^()${SPACE_BODY}]+\\))?[\\-+#0]*(?:[0-9]+|\\*)?(?:\\.(?:[0-9]+|\\*))?` +
    "(?:hh|h|ll|l|L|q|j|z|t)?[diouxXeEfFgGcrsaAp]",
  "gu",
);

const LABEL_CI_030 = `[${ASCII_ALNUM_CI_BODY}](?:[${ASCII_ALNUM_CI_BODY}\\-]{0,61}[${ASCII_ALNUM_CI_BODY}])?`;
const TLDS_030 = ["uz", "com", "org", "net", "ru", "info", "edu", "gov", "io"];
const BARE_DOMAIN_030 = new RegExp(
  `(?<![${W_BODY}@])(?<tail>${LABEL_CI_030}(?:\\.${LABEL_CI_030})*\\.(?:${TLDS_030.map(ci).join("|")})` +
    `(?![${W_BODY}\\-])(?:\\/${NOT_S}*)?)`,
  "gu",
);

const LETTER_MARKS = "\\u02B9\\u02BB\\u02BC";
const L = `(?:(?![${LETTER_MARKS}])[\\p{L}\\p{N}])`;
const NOT_AFTER_L = `(?:(?<![\\p{L}\\p{N}])|(?<=[${LETTER_MARKS}]))`;
const NOT_BEFORE_L = `(?:(?![\\p{L}\\p{N}])|(?=[${LETTER_MARKS}]))`;
const MARK = "[" + escapeRegExp(APOSTROPHE_VARIANTS.join("")) + "]";
const L_OR_MARK = "[\\p{L}\\p{N}" + escapeRegExp(APOSTROPHE_VARIANTS.join("")) + "]";
const CHUNK_030 = new RegExp(
  NOT_AFTER_L +
    `(?=${L_OR_MARK}*?(?:[0-9]|[a-z][A-Z]))` +
    `${L}+(?:${MARK}${L}+)*(?:(?<=[oOgG])${MARK})?` +
    NOT_BEFORE_L,
  "gu",
);

/** Python's pattern.search(text, pos, end), as protect.js has it. */
function search030(regex, scanner, pos, end) {
  regex.lastIndex = pos;
  return regex.exec(scanner.view(end));
}

function findToken030(scanner, pos, end) {
  for (;;) {
    const m = search030(CHUNK_030, scanner, pos, end);
    if (m === null) return null;
    if (isToken(m[0])) return [m.index, m.index + m[0].length, TOKEN, null];
    pos = m.index + m[0].length;
  }
}

// --- random inputs -----------------------------------------------------------------------

const N = 20000;

/** mulberry32: a small generator with a seed, the same sequence on every run. */
function generator(seed) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const int = (low, high) => low + Math.floor(next() * (high - low + 1));
  const choice = (items) => items[int(0, items.length - 1)];
  return { next, int, choice };
}

const textOf = (rng, pieces, low, high) => {
  let out = "";
  for (let i = rng.int(low, high); i > 0; i--) out += rng.choice(pieces);
  return out;
};

/** pos <= end, both on code point boundaries: the whole text half the time. */
function bounds(rng, text) {
  const cuts = [0];
  for (let i = 0; i < text.length; ) {
    i += text.codePointAt(i) > 0xffff ? 2 : 1;
    cuts.push(i);
  }
  if (rng.next() < 0.5) return [0, text.length];
  const end = rng.int(0, cuts.length - 1);
  return [cuts[rng.int(0, end)], cuts[end]];
}

const scannerFor = (text) => ({ text, view: (end) => (end === text.length ? text : text.slice(0, end)) });
const spanOf = (m) => (m === null ? null : [m.index, m[0].length, m.groups?.tail ?? null]);

// --- differential tests ------------------------------------------------------------------

test("0.3.1: the bare domain's regular expression is 0.3.0's", () => {
  assert.equal(BARE_DOMAIN_RE.source, BARE_DOMAIN_030.source);
  assert.equal(BARE_DOMAIN_RE.flags, BARE_DOMAIN_030.flags);
});

test("0.3.1: trim matches 0.3.0", () => {
  const rng = generator(3101);
  const pieces = [..."((()))).,;:!?»\"'a/"];
  for (let i = 0; i < N; i++) {
    const text = textOf(rng, pieces, 0, 24);
    const start = rng.int(0, text.length);
    const stop = rng.int(start, text.length);
    assert.equal(trim(text, start, stop), trim030(text, start, stop), JSON.stringify([text, start, stop]));
  }
});

const PRINTF_PIECES = [
  ...Array(6).fill("%"),
  ..."0 0 00 000 1 12 - + # * . .5 .0 1$ 0$ (n) ( ) h hh l ll L z q d d s s x f a p ! _".split(" "),
  " ",
];

function directive(rng) {
  const parts = [
    rng.choice(["", "", "1$", "0$", "12$"]),
    rng.choice(["", "", "(n)", "("]),
    textOf(rng, ["-", "+", "#", "0", "0"], 0, 4),
    rng.choice(["", "", "*", "1", "5", "10", "0", "05", "007", "120"]),
    rng.choice(["", "", ".", ".*", ".0", ".25", ".00"]),
    rng.choice(["", "", "", "h", "hh", "l", "ll", "L", "q", "j", "z", "t"]),
    rng.choice(["d", "s", "x", "f", "p", "a", "!", "", "y", " "]),
  ];
  return rng.choice(["", "", "a", "%", " "]) + "%" + parts.join("") + rng.choice(["", "", "x", "%"]);
}

test("0.3.1: PRINTF_RE matches 0.3.0", () => {
  const rng = generator(3102);
  for (let i = 0; i < N; i++) {
    const text = i % 2 ? directive(rng) : textOf(rng, PRINTF_PIECES, 1, 8);
    const [pos, end] = bounds(rng, text);
    const scanner = scannerFor(text);
    const old = spanOf(search030(PRINTF_030, scanner, pos, end));
    const now = spanOf(search030(PRINTF_RE, scanner, pos, end));
    assert.deepEqual(now, old, JSON.stringify([text, pos, end]));
  }
});

const DOMAIN_PIECES = [
  ..."a b1 x-y - . . uz com io UZ Org @ / _ 1 K ſ İ ı é ш".split(" "),
  ..."a. a.a. -. .uz .uz .com .uz- .uzb .Io/x a.uz x-y.com/p".split(" "),
  " ",
  ".uz ",
  "x".repeat(40) + "-" + "y".repeat(30),
  "x".repeat(62) + "-",
  "z".repeat(63),
  "z".repeat(64),
  "q-".repeat(20),
];

test("0.3.1: the bare domain search matches 0.3.0", () => {
  const rng = generator(3103);
  for (let i = 0; i < N; i++) {
    const text = textOf(rng, DOMAIN_PIECES, 1, 10);
    const [pos, end] = bounds(rng, text);
    const scanner = scannerFor(text);
    const old = spanOf(search030(BARE_DOMAIN_030, scanner, pos, end));
    const now = spanOf(searchBareDomain(BARE_DOMAIN_RE, scanner, pos, end));
    assert.deepEqual(now, old, JSON.stringify([text, pos, end]));
  }
});

const WORD_PIECES = [
  ..."aabbABoOgG12'ʻ’`ʼ-._SCDhUT",
  " ",
  ..."Ş ш \u{1D400} o' g' '' 1a aB Sh MChJ ToshDU pH x2".split(" "),
];

test("0.3.1: findToken matches 0.3.0", () => {
  const rng = generator(3104);
  for (let i = 0; i < N; i++) {
    const text = textOf(rng, WORD_PIECES, 0, 20);
    const [pos, end] = bounds(rng, text);
    const scanner = scannerFor(text);
    assert.deepEqual(findToken(scanner, pos, end), findToken030(scanner, pos, end), JSON.stringify([text, pos, end]));
  }
});

// --- time tests ----------------------------------------------------------------------------
//
// Measured on one machine, 0.3.0 took 254 s, 11 s, 8 s, 7 s, 11 s and 19 s
// over these, and 0.3.1 takes 12 ms, 3 ms, 1 ms, 7 ms, 2 ms and 18 ms. Of the
// two for the bare domain, the first has no ending at all, the second has one
// that no label before it reaches; and of the two for the token, the first has
// no sign of a token, the second has one at the end of the word.

const LIMIT = 1.0; // seconds

const TIMED = [
  ["a URL and 200 000 closing brackets", "https://akademtech.org/a" + ")".repeat(200000), [
    ["https://akademtech.org/a", "url"],
    [")".repeat(200000), null],
  ]],
  ["% and 80 000 zeros", "%" + "0".repeat(80000) + "!", null],
  ["40 000 labels and no ending", "a.".repeat(40000) + "a", null],
  ["40 000 labels and an ending out of reach", "a.".repeat(40000) + "a-.uz", null],
  ["80 000 apostrophes in a word", "a'".repeat(80000), null],
  ["60 000 apostrophe pairs, then a digit", "a''".repeat(60000) + "1", null],
];

for (const [name, text, expected] of TIMED) {
  test(`0.3.1: linear time: ${name}`, () => {
    const start = performance.now();
    const pieces = lib.segments(text);
    const elapsed = (performance.now() - start) / 1000;
    assert.ok(elapsed < LIMIT, `${name}: ${elapsed.toFixed(2)} s`);
    assert.deepEqual(pieces, expected ?? [[text, null]]);
  });
}
