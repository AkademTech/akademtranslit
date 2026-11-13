// Alphabetical order for Uzbek text, in each of the three orthographies. A
// port of src/akademtranslit/collation.py; see sort_key there.

import { mapWords } from "./rules.js";
import {
  APOSTROPHE_VARIANTS,
  CYRILLIC,
  CYRILLIC_ALPHABET,
  LATIN_1995,
  LATIN_1995_ALPHABET,
  LATIN_2026,
  LATIN_2026_ALPHABET,
  LATIN_2026_INPUT_ALIASES,
  SCRIPTS,
  TURNED_COMMA,
  TUTUQ,
} from "./tables.js";
import { orthography as readOrthography, SCRIPTS_REPR } from "./tags.js";
import { cpLength, isAlpha, isSpace, repr, requireArgument, requireString, strip } from "./unicode.js";

// Weights: 0 for whitespace, 1-10 for the digits, 11 + k for the k-th unit of
// the alphabet, 1000 + code point for any other letter.
const SPACE = 0;
const FIRST_DIGIT = 1;
const FIRST_LETTER = 11;
const OTHER_LETTER = 1000;

const ALPHABETS = new Map([
  [CYRILLIC, CYRILLIC_ALPHABET],
  [LATIN_1995, LATIN_1995_ALPHABET],
  [LATIN_2026, LATIN_2026_ALPHABET],
]);

const WEIGHTS = new Map(
  [...ALPHABETS].map(([name, alphabet]) => [name, new Map(alphabet.map((unit, k) => [unit, FIRST_LETTER + k]))]),
);

// Units longer than one character (oʻ gʻ sh ch in latin_1995), longest first.
const COMPOUND_UNITS = new Map(
  [...ALPHABETS].map(([name, alphabet]) => [
    name,
    alphabet.filter((unit) => cpLength(unit) > 1).sort((a, b) => cpLength(b) - cpLength(a)),
  ]),
);

// Letters to Unicode (ʻ ʼ ʹ are category Lm), but never weighed as letters.
const MARKS = new Set([...APOSTROPHE_VARIANTS, TURNED_COMMA, TUTUQ]);

const same = (word) => word;

/**
 * Key that sorts Uzbek text in the alphabetical order of ``orthography``
 * (one of SCRIPTS or a tag for one; required). Returns [weights, text]:
 * weights is an array of integers, text the NFC, stripped input that breaks
 * ties. Compare two keys by their weights, element by element (a shorter
 * prefix first), then by text.
 */
export function sortKey(text, orthography) {
  requireString(text, "text", "sortKey");
  requireArgument(orthography, "orthography", "sortKey");
  if (!SCRIPTS.includes(orthography)) {
    orthography = readOrthography(
      orthography,
      `unknown orthography: ${repr(orthography)}; expected one of ${SCRIPTS_REPR}`,
    );
  }

  const s = strip(text.normalize("NFC"));
  let work = s.toLowerCase();
  if (orthography === LATIN_2026) {
    for (const [alias, letter] of LATIN_2026_INPUT_ALIASES) work = work.replaceAll(alias, letter);
  }
  work = mapWords(work, same);

  const table = WEIGHTS.get(orthography);
  const compounds = COMPOUND_UNITS.get(orthography);
  const weights = [];
  let i = 0;
  const length = work.length;
  while (i < length) {
    // Code points: an astral letter weighs 1000 + its code point, as in Python.
    const cp = work.codePointAt(i);
    const ch = String.fromCodePoint(cp);
    if (isSpace(ch)) {
      if (!weights.length || weights[weights.length - 1] !== SPACE) weights.push(SPACE);
      i += ch.length;
      continue;
    }
    let unit = ch;
    for (const compound of compounds) {
      if (work.startsWith(compound, i)) {
        unit = compound;
        break;
      }
    }
    const weight = table.get(unit);
    if (weight !== undefined) {
      weights.push(weight);
      i += unit.length;
      continue;
    }
    if (ch >= "0" && ch <= "9") {
      weights.push(FIRST_DIGIT + cp - 0x30);
    } else if (isAlpha(ch) && !MARKS.has(ch)) {
      weights.push(OTHER_LETTER + cp);
    }
    i += ch.length;
  }
  return [weights, s];
}
