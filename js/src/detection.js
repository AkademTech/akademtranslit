// Closed-set answers about which script, and which Cyrillic, a text is in.
// A port of src/akademtranslit/detection.py.

import { CYRILLIC_CLASS } from "./rules.js";
import { requireString } from "./unicode.js";

// Trap: Python's "Latin letter" is unicodedata.name(ch).startswith("LATIN ")
// for a letter (str.isalpha()). JavaScript has no character names, and
// \p{Script=Latin} is a different set (it has ª, º, fullwidth A and the
// modifier letters, whose names do not start with LATIN). These are the 28
// ranges of the Python definition in Unicode 15.0, 1213 code points;
// test/traps.test.js compares them with test/fixtures/unicode-15.0.json.
export const LATIN_LETTER_RANGES = Object.freeze([
  [0x41, 0x5a], [0x61, 0x7a], [0xc0, 0xd6], [0xd8, 0xf6], [0xf8, 0x2af],
  [0x1d00, 0x1d25], [0x1d62, 0x1d65], [0x1d6b, 0x1d77], [0x1d79, 0x1d9a],
  [0x1e00, 0x1eff], [0x2090, 0x209c], [0x2184, 0x2184], [0x2c60, 0x2c7c],
  [0x2c7e, 0x2c7f], [0xa722, 0xa76f], [0xa771, 0xa787], [0xa78b, 0xa7ca],
  [0xa7d0, 0xa7d1], [0xa7d3, 0xa7d3], [0xa7d5, 0xa7d9], [0xa7f5, 0xa7f7],
  [0xa7fa, 0xa7ff], [0xab30, 0xab5a], [0xab60, 0xab64], [0xab66, 0xab68],
  [0xfb00, 0xfb06], [0x1df00, 0x1df1e], [0x1df25, 0x1df2a],
].map((range) => Object.freeze(range)));

/** A Latin letter, as a RegExp class (u flag). */
export const LATIN_LETTER_CLASS =
  "[" +
  LATIN_LETTER_RANGES.map(([a, b]) =>
    a === b ? `\\u{${a.toString(16)}}` : `\\u{${a.toString(16)}}-\\u{${b.toString(16)}}`,
  ).join("") +
  "]";

const LATIN_LETTER_RE = new RegExp(`^${LATIN_LETTER_CLASS}$`, "u");
const CYRILLIC_LETTER_RE = new RegExp(`^(?=\\p{L})${CYRILLIC_CLASS}$`, "u");
const ANY_LATIN_LETTER_RE = new RegExp(LATIN_LETTER_CLASS, "u");
const ANY_CYRILLIC_LETTER_RE = new RegExp(`(?=\\p{L})${CYRILLIC_CLASS}`, "u");

const UZBEK_LETTERS_RE = /[ўқғҳЎҚҒҲ]/u;
const RUSSIAN_LETTERS_RE = /[щыЩЫ]/u;

/** A letter in U+0400-U+052F (one code point). */
export function isCyrillicLetter(ch) {
  return CYRILLIC_LETTER_RE.test(ch);
}

/** A letter whose Unicode name begins with LATIN (one code point). */
export function isLatinLetter(ch) {
  return LATIN_LETTER_RE.test(ch);
}

/** Return "latin", "cyrillic" or "mixed" -- always one of the three. */
export function scriptClass(text) {
  requireString(text, "text", "scriptClass");
  // Python stops at the first character that makes the text mixed; whether a
  // kind of letter occurs at all is the same question.
  const cyrillic = ANY_CYRILLIC_LETTER_RE.test(text);
  const latin = ANY_LATIN_LETTER_RE.test(text);
  if (cyrillic && latin) return "mixed";
  return cyrillic ? "cyrillic" : "latin";
}

/** Return "uz", "ru", "mixed" or "unknown" for Cyrillic text. */
export function cyrillicLanguage(text) {
  requireString(text, "text", "cyrillicLanguage");
  const uzbek = UZBEK_LETTERS_RE.test(text);
  const russian = RUSSIAN_LETTERS_RE.test(text);
  if (uzbek && russian) return "mixed";
  if (uzbek) return "uz";
  if (russian) return "ru";
  return "unknown";
}
