// One output form for the apostrophe marks in Latin Uzbek text. A port of
// src/akademtranslit/apostrophes.py.

import { APOS_CLASS, CYRILLIC_CLASS, wordRegExp } from "./rules.js";
import { APOSTROPHE_VARIANTS, DEFAULT_IGNORABLE, TURNED_COMMA, TUTUQ } from "./tables.js";
import { LETTER, isAlpha, readOptions, repr, requireString } from "./unicode.js";

export const STYLES = Object.freeze(["unicode", "ascii"]);

const ASCII_APOSTROPHE = "'";
const MARKS = new Set(APOSTROPHE_VARIANTS);
const TURNED_COMMA_AFTER = new Set("oOgG");

/** The characters strip_invisible removes, as a RegExp class. */
export const INVISIBLE_CLASS =
  "[" +
  DEFAULT_IGNORABLE.map(([first, last]) =>
    first === last ? `\\u{${first.toString(16)}}` : `\\u{${first.toString(16)}}-\\u{${last.toString(16)}}`,
  ).join("") +
  "]";

const INVISIBLE_RE = new RegExp(INVISIBLE_CLASS, "gu");

// U+0301 COMBINING ACUTE ACCENT, the stress mark, after a letter.
const STRESS_RE = new RegExp(`(?<=${LETTER})\\u0301`, "gu");

const HAS_CYRILLIC_RE = new RegExp(CYRILLIC_CLASS, "u");
const WORD_RE = wordRegExp();

// ʻ ʼ ʹ are letters to Unicode (category Lm); here they are marks.
function isLetter(ch) {
  return ch !== "" && isAlpha(ch) && !MARKS.has(ch);
}

/**
 * Rewrite the apostrophe marks in Latin words to one form (see
 * apostrophes.py, normalize_apostrophes).
 */
export function normalizeApostrophes(text, style = "unicode", options = undefined) {
  requireString(text, "text", "normalizeApostrophes");
  const { stripInvisible = false, stripStress = false } = readOptions(
    options,
    ["stripInvisible", "stripStress"],
    "normalizeApostrophes",
  );
  if (!STYLES.includes(style)) {
    throw new RangeError(`unknown style: ${repr(style)}; expected one of ('unicode', 'ascii')`);
  }
  if (stripInvisible) text = text.replace(INVISIBLE_RE, "");
  if (stripStress) text = text.replace(STRESS_RE, "");

  return text.replace(WORD_RE, (word) => {
    if (HAS_CYRILLIC_RE.test(word)) return word;
    // Code points: the neighbours of a mark may be outside the BMP (U+1D41A is
    // a letter), and Python sees them as one character.
    const chars = Array.from(word);
    const last = chars.length - 1;
    let changed = false;
    for (let i = 0; i < chars.length; i++) {
      const ch = chars[i];
      if (!MARKS.has(ch)) continue;
      const prev = i ? chars[i - 1] : "";
      const nxt = i < last ? chars[i + 1] : "";
      const inside = isLetter(prev) && isLetter(nxt);
      const final = i === last && TURNED_COMMA_AFTER.has(prev);
      if (!(inside || final)) continue;
      chars[i] = style === "ascii" ? ASCII_APOSTROPHE : TURNED_COMMA_AFTER.has(prev) ? TURNED_COMMA : TUTUQ;
      changed = true;
    }
    return changed ? chars.join("") : word;
  });
}

export { APOS_CLASS };
