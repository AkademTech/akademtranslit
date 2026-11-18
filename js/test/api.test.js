// The public API: the names, the signatures, the errors and the defaults.
//
// The exports are Python's __all__ in camelCase (the map is below); the
// tables, and calls that raise, are compared with fixtures made from the
// Python library by tools/make-fixtures.py.

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { test } from "node:test";

import * as lib from "../src/index.js";
import * as tables from "../src/tables.js";
import { CYRILLIC_FOLD, LATIN_2026_FOLD } from "../src/normalize.js";
import { STYLES } from "../src/apostrophes.js";
import { KINDS } from "../src/protect.js";
import { CODES, ROUND_TRIP, SEPARATOR } from "../src/checks.js";
import { outcome, readFixture, sameJson } from "./support.js";

const version = lib.VERSION.replaceAll(".", "\\.");
const tableFixture = readFixture(new RegExp(`^tables-${version}\\.json$`, "u"));
const traps = readFixture(new RegExp(`^traps-${version}\\.json$`, "u"));

// --- names ----------------------------------------------------------------------------

/** Python's name -> the port's: camelCase for functions, __version__ is VERSION. */
const NAMES = {
  CYRILLIC: "CYRILLIC",
  CYRILLIC_ALPHABET: "CYRILLIC_ALPHABET",
  LATIN_1995: "LATIN_1995",
  LATIN_1995_ALPHABET: "LATIN_1995_ALPHABET",
  LATIN_2026: "LATIN_2026",
  LATIN_2026_ALPHABET: "LATIN_2026_ALPHABET",
  Protect: "Protect",
  REFORM_PAIRS: "REFORM_PAIRS",
  RULES_VERSION: "RULES_VERSION",
  SCRIPTS: "SCRIPTS",
  TURNED_COMMA: "TURNED_COMMA",
  TUTUQ: "TUTUQ",
  __version__: "VERSION",
  convert: "convert",
  cyrillic_language: "cyrillicLanguage",
  detect_script: "detectScript",
  fold_cyrillic: "foldCyrillic",
  fold_homoglyphs: "foldHomoglyphs",
  homoglyph_spans: "homoglyphSpans",
  is_cyrillic: "isCyrillic",
  migration_report: "migrationReport",
  normalize: "normalize",
  normalize_apostrophes: "normalizeApostrophes",
  script_class: "scriptClass",
  script_for_tag: "scriptForTag",
  script_spans: "scriptSpans",
  segments: "segments",
  sort_key: "sortKey",
  tag_for_script: "tagForScript",
  to_ascii: "toAscii",
  to_cyrillic: "toCyrillic",
  to_latin: "toLatin",
  validate: "validate",
};

test("the exports are Python's __all__, mapped, and nothing else", () => {
  assert.deepEqual(Object.keys(NAMES).sort(), [...tableFixture.all].sort());
  assert.deepEqual(Object.keys(lib).sort(), Object.values(NAMES).sort());
  for (const [python, js] of Object.entries(NAMES)) {
    if (/^[a-z]/u.test(python)) assert.equal(js, python.replace(/_([a-z])/gu, (_, c) => c.toUpperCase()));
  }
});

test("index.d.ts declares every export", () => {
  const dts = readFileSync(new URL("../src/index.d.ts", import.meta.url), "utf8");
  const declared = new Set(
    [...dts.matchAll(/^export (?:declare )?(?:function|const|class|type|interface) ([A-Za-z0-9_]+)/gmu)].map(
      (m) => m[1],
    ),
  );
  for (const name of Object.keys(lib)) assert.ok(declared.has(name), name);
});

// --- constants and tables ---------------------------------------------------------------

const asJson = (value) => {
  if (value instanceof Map) return Object.fromEntries([...value].map(([k, v]) => [k, asJson(v)]));
  if (value instanceof Set) return [...value].sort();
  if (Array.isArray(value)) return value.map(asJson);
  return value;
};

test("the tables are Python's", () => {
  const python = tableFixture.tables;
  assert.deepEqual(Object.keys(python).filter((name) => !(name in tables)), []);
  for (const [name, value] of Object.entries(python)) {
    assert.deepEqual(asJson(tables[name]), value, name);
  }
  assert.deepEqual(asJson(CYRILLIC_FOLD), tableFixture.normalize._CYRILLIC_FOLD);
  assert.deepEqual(asJson(LATIN_2026_FOLD), tableFixture.normalize._LATIN_2026_FOLD);
  assert.deepEqual([...STYLES], tableFixture.apostrophes.STYLES);
  assert.deepEqual([...KINDS], tableFixture.protect.KINDS);
  assert.deepEqual([...CODES], tableFixture.checks.CODES);
  assert.equal(ROUND_TRIP, tableFixture.checks.ROUND_TRIP);
  assert.equal(SEPARATOR, tableFixture.checks.SEPARATOR);
});

test("constants: values, versions and immutability", () => {
  assert.equal(lib.VERSION, tableFixture.library_version);
  assert.equal(lib.RULES_VERSION, tableFixture.rules_version);
  assert.deepEqual([...lib.SCRIPTS], ["cyrillic", "latin_1995", "latin_2026"]);
  assert.equal(lib.TURNED_COMMA, "ʻ");
  assert.equal(lib.TUTUQ, "ʼ");
  for (const value of [lib.SCRIPTS, lib.REFORM_PAIRS, lib.REFORM_PAIRS[0], lib.LATIN_2026_ALPHABET]) {
    assert.ok(Object.isFrozen(value));
  }
  assert.throws(() => {
    lib.SCRIPTS.push("x");
  }, TypeError);
});

// --- calls that raise, against Python ---------------------------------------------------

const camel = (name) => name.replace(/_([a-z])/gu, (_, c) => c.toUpperCase());

/** Each Python function: its positional parameters, then its keyword-only ones. */
const SIGNATURES = {
  convert: [lib.convert, ["text", "source", "target"], ["protect"]],
  to_latin: [lib.toLatin, ["text", "variant"], ["protect"]],
  to_cyrillic: [lib.toCyrillic, ["text"], ["protect"]],
  sort_key: [lib.sortKey, ["text", "orthography"], []],
  validate: [lib.validate, ["text", "orthography"], ["protect"]],
  migration_report: [lib.migrationReport, ["text"], ["protect"]],
  normalize_apostrophes: [lib.normalizeApostrophes, ["text", "style"], ["strip_invisible", "strip_stress"]],
  segments: [lib.segments, ["text", "protect"], []],
  script_for_tag: [lib.scriptForTag, ["tag"], []],
  tag_for_script: [lib.tagForScript, ["script"], []],
};

const decode = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value) && "Protect" in value
    ? new lib.Protect(value.Protect)
    : value;

/** The port's call for one Python call of the fixture. */
function jsCall({ call, args, kwargs }) {
  if (call === "Protect") return new lib.Protect(Object.fromEntries(Object.entries(kwargs).map(([k, v]) => [camel(k), v])));
  const [func, positional, keywordOnly] = SIGNATURES[call];
  const values = args.map(decode);
  let options;
  for (const [key, value] of Object.entries(kwargs)) {
    const at = positional.indexOf(key);
    if (at >= 0) {
      while (values.length < at) values.push(undefined);
      values[at] = decode(value);
    } else {
      assert.ok(keywordOnly.includes(key), key);
      (options ??= {})[camel(key)] = decode(value);
    }
  }
  if (options !== undefined) {
    while (values.length < positional.length) values.push(undefined);
    values.push(options);
  }
  return func(...values);
}

const protectSettings = (value) =>
  value instanceof lib.Protect
    ? {
        Protect: {
          urls: value.urls,
          emails: value.emails,
          dois: value.dois,
          placeholders: value.placeholders,
          markup: value.markup,
          paths: value.paths,
          tokens: value.tokens,
          terms: [...value.terms],
        },
      }
    : value;

test("each call of the fixture gives Python's value or Python's error", () => {
  assert.ok(traps.calls.length >= 40);
  const misses = [];
  for (const call of traps.calls) {
    const actual = protectSettings(outcome(() => jsCall(call)));
    if (!sameJson(actual, call.outcome)) misses.push({ call, actual });
  }
  assert.deepEqual(misses, []);
});

// --- argument checks the port adds ------------------------------------------------------

const TEXT_FUNCTIONS = {
  convert: (text) => lib.convert(text),
  toLatin: (text) => lib.toLatin(text),
  toCyrillic: (text) => lib.toCyrillic(text),
  toAscii: (text) => lib.toAscii(text),
  normalize: (text) => lib.normalize(text),
  normalizeApostrophes: (text) => lib.normalizeApostrophes(text),
  detectScript: (text) => lib.detectScript(text),
  scriptClass: (text) => lib.scriptClass(text),
  scriptSpans: (text) => lib.scriptSpans(text),
  segments: (text) => lib.segments(text),
  isCyrillic: (text) => lib.isCyrillic(text),
  cyrillicLanguage: (text) => lib.cyrillicLanguage(text),
  foldCyrillic: (text) => lib.foldCyrillic(text),
  foldHomoglyphs: (text) => lib.foldHomoglyphs(text),
  homoglyphSpans: (text) => lib.homoglyphSpans(text),
  sortKey: (text) => lib.sortKey(text, "latin_2026"),
  validate: (text) => lib.validate(text, "latin_2026"),
  migrationReport: (text) => lib.migrationReport(text),
};

test("text that is not a string is a TypeError", () => {
  for (const [name, call] of Object.entries(TEXT_FUNCTIONS)) {
    for (const value of [undefined, null, 5, ["a"], { toString: () => "a" }]) {
      assert.throws(() => call(value), TypeError, `${name}(${String(value)})`);
    }
  }
});

test("options: an unknown key, or options that are not an object, is a TypeError", () => {
  assert.throws(() => lib.convert("x", "auto", "latin_2026", { protekt: true }), TypeError);
  assert.throws(() => lib.convert("x", "auto", "latin_2026", false), TypeError);
  assert.throws(() => lib.convert("x", "auto", "latin_2026", new lib.Protect()), TypeError);
  assert.throws(() => lib.toLatin("x", "latin_1995", { strip_invisible: true }), TypeError);
  assert.throws(() => lib.normalizeApostrophes("x", "unicode", { strip_invisible: true }), TypeError);
  assert.throws(() => lib.validate("x", "latin_2026", []), TypeError);
  assert.throws(() => new lib.Protect({ url: false }), TypeError);
});

test("a missing required argument is a TypeError, as in Python", () => {
  assert.throws(() => lib.sortKey("x"), TypeError);
  assert.throws(() => lib.validate("x"), TypeError);
  assert.throws(() => lib.scriptForTag(), TypeError);
  assert.throws(() => lib.tagForScript(), TypeError);
});

test("errors: ValueError is RangeError, TypeError is TypeError", () => {
  assert.throws(() => lib.convert("x", "auto2"), RangeError);
  assert.throws(() => lib.toLatin("x", "cyrillic"), RangeError);
  assert.throws(() => lib.sortKey("x", "auto"), RangeError);
  assert.throws(() => lib.normalizeApostrophes("x", "fancy"), RangeError);
  assert.throws(() => lib.segments("x", null), RangeError);
  assert.throws(() => lib.scriptForTag("en"), RangeError);
  assert.throws(() => lib.scriptForTag(5), TypeError);
  assert.throws(() => lib.tagForScript("auto"), RangeError);
  assert.throws(() => new lib.Protect({ terms: "AslMatn" }), TypeError);
  assert.throws(() => new lib.Protect({ terms: [""] }), RangeError);
});

// --- defaults -----------------------------------------------------------------------------

test("defaults: source auto, target latin_2026, protect true, style unicode", () => {
  const text = "Тошкент https://shahar.uz Oʻzbekiston pH";
  assert.equal(lib.convert(text), lib.convert(text, "auto", "latin_2026", { protect: true }));
  assert.equal(lib.convert(text, undefined, undefined, {}), lib.convert(text));
  assert.equal(lib.toLatin(text), lib.toLatin(text, "latin_2026", { protect: true }));
  assert.equal(lib.toCyrillic(text), lib.toCyrillic(text, { protect: true }));
  assert.notEqual(lib.toCyrillic(text), lib.toCyrillic(text, { protect: false }));
  assert.deepEqual(lib.segments(text), lib.segments(text, true));
  assert.deepEqual(lib.validate(text, "latin_2026"), lib.validate(text, "latin_2026", { protect: true }));
  assert.deepEqual(lib.migrationReport(text), lib.migrationReport(text, { protect: true }));
  const marks = "O'zbek­ ma'no Tóshkent";
  assert.equal(lib.normalizeApostrophes(marks), lib.normalizeApostrophes(marks, "unicode", {}));
  assert.equal(
    lib.normalizeApostrophes(marks),
    lib.normalizeApostrophes(marks, "unicode", { stripInvisible: false, stripStress: false }),
  );
  assert.equal(lib.convert(""), "");
});

test("tags name orthographies wherever one is taken", () => {
  assert.equal(lib.convert("Gʻafur", "uz-Latn-1995", "uz-Latn-2026"), "Ğafur");
  assert.equal(lib.toLatin("Тошкент", "uz-Latn-1995"), "Toshkent");
  assert.deepEqual(lib.sortKey("şahar", "UZ_latn_2026"), lib.sortKey("şahar", "latin_2026"));
  assert.deepEqual(lib.validate("Тошкент oʻrdak", "uz-Cyrl"), lib.validate("Тошкент oʻrdak", "cyrillic"));
});

// --- scriptForTag: the warning is data ---------------------------------------------------

test("scriptForTag returns { script, warning } and writes nothing to the console", () => {
  const written = [];
  const saved = { warn: console.warn, error: console.error, log: console.log };
  console.warn = console.error = console.log = (...args) => written.push(args);
  try {
    assert.deepEqual(lib.scriptForTag("uz-Latn-2026"), { script: "latin_2026", warning: null });
    assert.deepEqual(lib.scriptForTag("uz"), { script: "latin_1995", warning: "FutureWarning" });
    assert.deepEqual(lib.scriptForTag("uz-Latn"), { script: "latin_1995", warning: "FutureWarning" });
    assert.deepEqual(Object.keys(lib.scriptForTag("uz-Cyrl")), ["script", "warning"]);
    assert.equal(lib.convert("Toshkent", "uz-Latn", "uz-Cyrl"), "Тошкент");
  } finally {
    Object.assign(console, saved);
  }
  assert.deepEqual(written, []);
});

// --- Protect --------------------------------------------------------------------------------

test("Protect: keywords, immutable, comparable", () => {
  const p = new lib.Protect({ tokens: false, terms: ["AslMatn"] });
  assert.equal(p.tokens, false);
  assert.equal(p.urls, true);
  assert.deepEqual([...p.terms], ["AslMatn"]);
  assert.ok(Object.isFrozen(p) && Object.isFrozen(p.terms));
  assert.throws(() => {
    p.urls = false;
  }, TypeError);
  assert.ok(p.equals(new lib.Protect({ tokens: 0, terms: ["AslMatn"] })));
  assert.ok(!p.equals(new lib.Protect()));
  assert.ok(new lib.Protect().equals(new lib.Protect({})));
  assert.equal(lib.Protect.NONE.urls, false);
  assert.equal(lib.Protect.NONE.tokens, false);
  assert.deepEqual(lib.segments("AslMatn va shahar", p), [
    ["AslMatn", "term"],
    [" va shahar", null],
  ]);
  assert.deepEqual(lib.segments("AslMatn va shahar", false), [["AslMatn va shahar", null]]);
  assert.equal(String(p), 'Protect({ tokens: false, terms: ["AslMatn"] })');
});

// --- the same files in Node and in a browser ------------------------------------------------

const SRC = new URL("../src/", import.meta.url);
const sources = readdirSync(SRC)
  .filter((name) => name.endsWith(".js"))
  .map((name) => [name, readFileSync(new URL(name, SRC), "utf8")]);

/** The code of a source file without its comments (// to the end of a line). */
const code = (text) =>
  text
    .split("\n")
    .map((line) => line.replace(/(^|\s)\/\/.*$/u, "$1"))
    .join("\n")
    .replace(/\/\*\*[^\n]*\*\//gu, "");

test("src/ runs in a browser: relative .js imports only, no Node built-ins", () => {
  for (const [name, text] of sources) {
    for (const m of text.matchAll(/^\s*(?:import|export)\b[^;]*?\bfrom\s+"([^"]+)"/gmu)) {
      assert.match(m[1], /^\.\/[a-z0-9-]+\.js$/u, `${name}: ${m[1]}`);
    }
    const body = code(text);
    for (const banned of ["node:", "process.", "Buffer", "require(", "import.meta", "globalThis.", "window.", "self."]) {
      assert.ok(!body.includes(banned), `${name} uses ${banned}`);
    }
  }
});

test("src/ uses none of the JavaScript forms that differ from Python", () => {
  for (const [name, text] of sources) {
    const body = code(text);
    // \w \d \s \b (in a RegExp literal or a pattern string), trim(), toLocale*.
    assert.doesNotMatch(body, /\\\\?[wWdDsSbB](?![a-zA-Z])/u, `${name}: a JavaScript character class shorthand`);
    assert.ok(!body.includes(".trim"), `${name}: trim()`);
    assert.ok(!body.includes("toLocale"), `${name}: toLocale*`);
    // No case-insensitive flag: every RegExp is built with explicit flags.
    for (const m of body.matchAll(/new RegExp\([\s\S]*?,\s*"([a-z]*)"\s*,?\s*\)/gu)) {
      assert.ok(!m[1].includes("i"), `${name}: flags ${m[1]}`);
    }
    for (const m of body.matchAll(/\/[^/\n]+\/([dgimsuvy]+)/gu)) {
      assert.ok(!m[1].includes("i"), `${name}: flags ${m[1]} in ${m[0]}`);
    }
  }
});
