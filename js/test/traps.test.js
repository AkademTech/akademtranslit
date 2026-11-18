// The places where JavaScript and Python differ, each with a test.
//
// The golden inputs have no character outside the BMP, none of U+0085,
// U+001C-U+001F or U+FEFF, and no number that is a letter to Python's re, so
// the golden file alone cannot catch a port that gets these wrong.
// tools/make-fixtures.py writes three fixtures for them:
// - traps-<version>.json: inputs made for the traps, through every golden
//   field and every call the golden file does not make;
// - options-<version>.json: those calls on every golden input;
// - unicode-<unidata version>.json: Python's view of every code point.

import assert from "node:assert/strict";
import { test } from "node:test";

import * as lib from "../src/index.js";
import { LATIN_LETTER_RANGES, isLatinLetter } from "../src/detection.js";
import { LETTER, S, W_BODY, hasCase, isAlpha, isMark, isSpace, isUpper } from "../src/unicode.js";
import {
  FIELDS,
  differences,
  extraFields,
  readFixture,
  readGolden,
  sha256,
} from "./support.js";

const version = lib.VERSION.replaceAll(".", "\\.");
const traps = readFixture(new RegExp(`^traps-${version}\\.json$`, "u"));
const options = readFixture(new RegExp(`^options-${version}\\.json$`, "u"));
const unicode = readFixture(/^unicode-[0-9.]+\.json$/u);

// --- the fixtures -----------------------------------------------------------------------

test("trap fixture: header and fields", () => {
  assert.equal(traps.library_version, lib.VERSION);
  assert.equal(traps.rules_version, lib.RULES_VERSION);
  // The inputs as Python's json.dumps(..., ensure_ascii=False) wrote them.
  const inputs =
    "[" + traps.cases.map(({ id, text }) => `[${JSON.stringify(id)}, ${JSON.stringify(text)}]`).join(", ") + "]";
  assert.equal(sha256(Buffer.from(inputs, "utf8")), traps.inputs_sha256);
  const extras = extraFields(traps.terms);
  for (const field of traps.fields) assert.ok(field in FIELDS || field in extras, field);
  assert.ok(traps.cases.some(({ text }) => /[\u{10000}-\u{10FFFF}]/u.test(text)), "astral inputs");
});

test("trap inputs: every golden field and every extra call match Python", () => {
  const fields = { ...FIELDS, ...extraFields(traps.terms) };
  const misses = differences(traps.cases, fields, (item, field) => item.results[field]);
  const checked = traps.cases.length * Object.keys(traps.cases[0].results).length;
  assert.deepEqual(misses.slice(0, 5), [], `${misses.length} of ${checked} differ`);
});

test("options fixture: the calls the golden file does not make, on every golden input", (t) => {
  const inputs = readGolden("inputs.json");
  assert.equal(options.inputs_sha256, sha256(inputs));
  assert.equal(options.library_version, lib.VERSION);
  const cases = JSON.parse(inputs.toString("utf8")).cases;
  const all = extraFields(options.terms);
  const fields = Object.fromEntries(options.fields.map((name) => [name, all[name]]));
  const misses = differences(cases, fields, (item, field) => options.results[item.id][field]);
  t.diagnostic(`options — ${cases.length * options.fields.length - misses.length} / ${cases.length * options.fields.length}`);
  assert.deepEqual(misses.slice(0, 5), [], `${misses.length} differ`);
});

// --- Unicode: every code point -------------------------------------------------------

const MAX = 0x110000;

function flags(ranges) {
  const out = new Uint8Array(MAX);
  for (const [first, last] of ranges) out.fill(1, first, last + 1);
  return out;
}

const unassigned = flags(unicode.unassigned);

// Four lowercase letters of Unicode 15.0 got an uppercase partner later:
// ƛ U+019B (Ƛ U+A7DC) and ɤ U+0264 (Ɤ U+A7CB) in 16.0, ꟓ U+A7D3 and ꟕ U+A7D5
// (U+A7D2, U+A7D4) as Node's Unicode has them. Python 3.12 has no uppercase
// for them, so their case differs by Unicode version, not by port; measured,
// and the only assigned code points where any check below differs.
const CASE_ADDED_LATER = new Set([0x019b, 0x0264, 0xa7d3, 0xa7d5]);
for (const cp of CASE_ADDED_LATER) unassigned[cp] = 1;

const versionDifferences = (n) =>
  `differs only on ${n} code points that Python's Unicode ${unicode.unidata_version} leaves ` +
  "unassigned (or, for case, ƛ ɤ ꟓ ꟕ)";

/**
 * Compare a JavaScript predicate with Python's ranges over every code point.
 * A difference on a code point that Python's Unicode leaves unassigned is a
 * difference of Unicode versions (counted); anywhere else it fails.
 */
function compareClass(name, predicate) {
  const python = flags(unicode.classes[name]);
  const wrong = [];
  let versionOnly = 0;
  for (let cp = 0; cp < MAX; cp++) {
    if (Boolean(python[cp]) === predicate(String.fromCodePoint(cp))) continue;
    if (unassigned[cp]) versionOnly++;
    else wrong.push(cp.toString(16));
  }
  return { wrong, versionOnly };
}

const W_RE = new RegExp(`^[${W_BODY}]$`, "u");
const S_RE = new RegExp(`^${S}$`, "u");
const LETTER_RE = new RegExp(`^${LETTER}$`, "u");

// Trap: Python's str predicates and re classes are not JavaScript's. Each
// helper in src/unicode.js is checked against Python on all 1,114,112 code
// points.
const CLASSES = {
  isalpha: isAlpha, // str.isalpha(): \p{L}
  isupper: isUpper, // str.isupper(): \p{Uppercase}, not \p{Lu} (Ⅰ, Ⓐ)
  isspace: isSpace, // str.isspace(): 29 code points, not JavaScript's \s
  has_case: hasCase, // ch.lower() != ch.upper()
  mark: isMark, // unicodedata.category(ch).startswith("M")
  re_w: (ch) => W_RE.test(ch), // re \w: [\p{L}\p{N}_]
  re_d: (ch) => /^\p{Nd}$/u.test(ch), // re \d: \p{Nd}
  re_s: (ch) => S_RE.test(ch), // re \s: as str.isspace()
  re_letter: (ch) => LETTER_RE.test(ch), // re [^\W\d_]: [\p{L}\p{Nl}\p{No}]
};

for (const [name, predicate] of Object.entries(CLASSES)) {
  test(`Unicode: ${name} matches Python ${unicode.python} on every assigned code point`, (t) => {
    const { wrong, versionOnly } = compareClass(name, predicate);
    t.diagnostic(`${name}: ${versionDifferences(versionOnly)}`);
    assert.deepEqual(wrong.slice(0, 10), [], `${wrong.length} assigned code points differ`);
  });
}

// Trap: a Latin letter is a letter whose Unicode name begins with LATIN; the
// port has the ranges as a table, which must be Python's exactly.
test("Unicode: the Latin letter table is Python's, exactly", () => {
  assert.deepEqual(LATIN_LETTER_RANGES.map((range) => [...range]), unicode.classes.latin_letter);
  const { wrong, versionOnly } = compareClass("latin_letter", isLatinLetter);
  assert.deepEqual(wrong, []);
  assert.equal(versionOnly, 0);
  // \p{Script=Latin} would be wrong: ª, º, ʰ and fullwidth A are Latin script.
  for (const ch of ["\u00aa", "\u00ba", "\u02b0", "\uff21"]) {
    assert.equal(/\p{Script=Latin}/u.test(ch), true, ch);
    assert.equal(isLatinLetter(ch), false, ch);
  }
});

function compareMapping(entries, compute) {
  const python = new Map(entries.map(([cp, ...values]) => [cp, values]));
  const wrong = [];
  let versionOnly = 0;
  for (let cp = 0; cp < MAX; cp++) {
    if (cp >= 0xd800 && cp <= 0xdfff) continue; // not in the fixture: not UTF-8
    const ch = String.fromCodePoint(cp);
    const expected = python.get(cp) ?? null;
    const actual = compute(ch);
    const same = expected === null ? actual.every((value) => value === ch) : actual.every((v, i) => v === expected[i]);
    if (same) continue;
    if (unassigned[cp]) versionOnly++;
    else wrong.push(cp.toString(16));
  }
  return { wrong, versionOnly };
}

// Trap: str.lower()/upper() and toLowerCase()/toUpperCase(): the same full
// mappings (ß -> SS, İ -> i + U+0307); toLocale* is never used.
test("Unicode: lower and upper case of every code point match Python", (t) => {
  const { wrong, versionOnly } = compareMapping(unicode.case, (ch) => [ch.toLowerCase(), ch.toUpperCase()]);
  t.diagnostic(`case: ${versionDifferences(versionOnly)}`);
  assert.deepEqual(wrong.slice(0, 10), [], `${wrong.length} assigned code points differ`);
});

// Trap: NFC, NFKC and NFKD come from ICU here and from unicodedata in Python.
for (const form of ["nfc", "nfkc", "nfkd"]) {
  test(`Unicode: ${form.toUpperCase()} of every code point matches Python`, (t) => {
    const { wrong, versionOnly } = compareMapping(unicode[form], (ch) => [ch.normalize(form.toUpperCase())]);
    t.diagnostic(`${form}: ${versionDifferences(versionOnly)}`);
    assert.deepEqual(wrong.slice(0, 10), [], `${wrong.length} assigned code points differ`);
  });
}

test("Unicode versions", (t) => {
  t.diagnostic(`Python ${unicode.python}: Unicode ${unicode.unidata_version}`);
  t.diagnostic(`Node ${process.versions.node}: Unicode ${process.versions.unicode}, ICU ${process.versions.icu}`);
  // Each of the four still has no case in Python's table.
  const python = new Set(unicode.case.map(([cp]) => cp));
  for (const cp of CASE_ADDED_LATER) assert.equal(python.has(cp), false, cp.toString(16));
});

// --- each trap, by hand --------------------------------------------------------------

// Trap: indices count code points, as Python's do. U+1D400 is one character
// to Python and two UTF-16 units here.
test("validate, homoglyphSpans and migrationReport count code points", () => {
  const astral = "\u{1D400}\u{1D401} ";
  assert.deepEqual(lib.validate(astral + "Toshkent", "latin_2026"), [[3, 11, "digraph", "Toşkent"]]);
  assert.deepEqual(lib.homoglyphSpans("\u{1F600} Toshk\u0435nt"), [[2, 10, "Toshkent"]]);
  assert.deepEqual(lib.migrationReport("\u{1F600} Isʼhoq").check, [[2, 8, "separator", "Ishoq"]]);
  // segments and scriptSpans give pieces, not indices: the pieces are the same.
  assert.deepEqual(lib.scriptSpans("\u{1F600}ab").map(([piece]) => piece), ["\u{1F600}", "ab"]);
});

// Trap: a neighbour outside the BMP is one character.
test("an apostrophe after a letter outside the BMP is inside a word", () => {
  assert.equal(lib.normalizeApostrophes("\u{1D41A}'b"), "\u{1D41A}ʼb");
  // Ş left in a URL, beside U+1D400, a capital: SH (Python), not Sh.
  assert.equal(lib.toAscii("https://Ş\u{1D400}.uz"), "https://SHA.uz");
  assert.equal(lib.toAscii("https://\u{1D400}Çx.uz"), "https://ACHx.uz");
  assert.deepEqual(lib.sortKey("\u{1D41A}", "latin_2026")[0], [1000 + 0x1d41a]);
});

// Trap: re.IGNORECASE matches U+0130, U+0131 (i), U+212A (k), U+017F (s);
// JavaScript's i flag takes only the last two.
test("URLs, file names, mailto and doi: Python's case-insensitive letters", () => {
  assert.deepEqual(lib.segments("x.\u0130NFO")[0], ["x.\u0130NFO", "url"]);
  assert.deepEqual(lib.segments("HTTP\u017F://x")[0], ["HTTP\u017F://x", "url"]);
  assert.deepEqual(lib.segments("fayl.Z\u0130P")[0], ["fayl.Z\u0130P", "path"]);
  assert.deepEqual(lib.segments("DO\u0130:10.1234/x")[0], ["DO\u0130:10.1234/x", "doi"]);
});

// Trap: Python's whitespace has U+0085 and U+001C-U+001F, not U+FEFF.
test("whitespace is Python's", () => {
  assert.deepEqual(lib.sortKey("a\u0085b", "latin_2026")[0], [11, 0, 12]);
  assert.deepEqual(lib.sortKey("a\uFEFFb", "latin_2026")[0], [11, 12]);
  assert.equal(lib.normalize("\u0085 Toshkent \u001F"), "toshkent");
  assert.deepEqual(lib.segments("https://x.uz\u0085y")[0], ["https://x.uz", "url"]);
  assert.deepEqual(lib.segments("https://x.uz\uFEFFy")[0], ["https://x.uz\uFEFFy", "url"]);
});

// Trap: Python's [^\W\d_] takes the numbers that are not digits (Nl, No).
test("a word may hold Ⅻ, ² and ½, as in Python's re", () => {
  assert.deepEqual(lib.scriptSpans("x² Ⅻ")[0], ["x²", "latin"]);
  assert.deepEqual(lib.scriptSpans("Ⅻ")[0], ["Ⅻ", "latin"]);
  assert.equal(lib.toCyrillic("Ⅻ"), "Ⅻ".toLowerCase().toUpperCase());
});

// Trap: str.isupper() is the property Uppercase: Ⅻ (Nl) is a capital.
test("case: Ⅻ is a capital, ǅ is not", () => {
  assert.equal(isUpper("Ⅻ"), true);
  assert.equal(isUpper("ǅ"), false);
  assert.equal(hasCase("ǅ"), true);
});

// Trap: search(text, pos, endpos) -- a URL inside an ICU message ends where
// the message does.
test("a span inside an ICU message ends at the message", () => {
  const pieces = lib.segments("{n, plural, one {https://x.uz/a} other {b}}");
  assert.deepEqual(pieces[1], ["https://x.uz/a", "url"]);
});

// Trap: the sort key is an array of integers, exactly.
test("sortKey gives integers and the NFC, stripped text", () => {
  const [weights, text] = lib.sortKey("  O\u0308zbek  ", "latin_2026");
  assert.ok(weights.every(Number.isInteger));
  assert.deepEqual(weights, [26, 38, 12, 14, 21]);
  assert.equal(text, "Özbek");
});
