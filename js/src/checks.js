// Check a text against the orthography it is meant to be in. A port of
// src/akademtranslit/checks.py; see validate and migration_report there.
//
// Trap: indices. Python returns code point offsets. The findings are made
// with UTF-16 offsets and converted once, at the end, with codePointIndexer().

import { INVISIBLE_CLASS } from "./apostrophes.js";
import { convert } from "./convert.js";
import { settingsFor, spans } from "./protect.js";
import {
  CYRILLIC_WORD,
  LATIN_1995_WORD,
  LATIN_2026_WORD,
  O_FORM_WORD,
  canonicalizeMarks,
  wordClass,
  wordRegExp,
} from "./rules.js";
import { foldWord, hasLatinLetter } from "./scripts.js";
import {
  APOSTROPHE_VARIANTS,
  CYRILLIC,
  LATIN_1995,
  LATIN_2026,
  RULES_VERSION,
  SCRIPTS,
  TURNED_COMMA,
  TUTUQ,
} from "./tables.js";
import { orthography as readOrthography, SCRIPTS_REPR } from "./tags.js";
import { codePointIndexer, readOptions, repr, requireArgument, requireString } from "./unicode.js";

// The codes of validate, in the order of the documentation.
export const INVISIBLE = "invisible";
export const DECOMPOSED = "decomposed";
export const MIXED_SCRIPT = "mixed-script";
export const CYRILLIC_WORD_FOUND = "cyrillic-word";
export const LATIN_1995_WORD_FOUND = "latin-1995-word";
export const LATIN_2026_WORD_FOUND = "latin-2026-word";
export const LOOK_ALIKE = "look-alike";
export const LETTER_FORM = "letter-form";
export const DIGRAPH = "digraph";
export const WRONG_MARK = "wrong-mark";
export const MARK_FORM = "mark-form";

export const CODES = Object.freeze([
  INVISIBLE,
  DECOMPOSED,
  MIXED_SCRIPT,
  CYRILLIC_WORD_FOUND,
  LATIN_1995_WORD_FOUND,
  LATIN_2026_WORD_FOUND,
  LOOK_ALIKE,
  LETTER_FORM,
  DIGRAPH,
  WRONG_MARK,
  MARK_FORM,
]);

// The two codes migrationReport adds.
export const ROUND_TRIP = "round-trip";
export const SEPARATOR = "separator";

// A run of the characters strip_invisible removes.
const INVISIBLE_RUN_RE = new RegExp(INVISIBLE_CLASS + "+", "gu");

// A character and the combining marks after it, as Python's _decomposed walks
// the text: the first character, or any that is not a mark, then marks.
const COMBINING_RUN_RE = /(?:^[^]|\P{M})\p{M}+/gu;

// Letters that look like ö or ğ, and the letter each stands for.
const LOOK_ALIKES = new Map([
  [String.fromCodePoint(0x014f), "o"], // LATIN SMALL LETTER O WITH BREVE
  [String.fromCodePoint(0x00f3), "o"], // LATIN SMALL LETTER O WITH ACUTE
  [String.fromCodePoint(0x00f5), "o"], // LATIN SMALL LETTER O WITH TILDE
  [String.fromCodePoint(0x014e), "O"], // LATIN CAPITAL LETTER O WITH BREVE
  [String.fromCodePoint(0x00d3), "O"], // LATIN CAPITAL LETTER O WITH ACUTE
  [String.fromCodePoint(0x00d5), "O"], // LATIN CAPITAL LETTER O WITH TILDE
  [String.fromCodePoint(0x1e21), "g"], // LATIN SMALL LETTER G WITH MACRON
  [String.fromCodePoint(0x01f5), "g"], // LATIN SMALL LETTER G WITH ACUTE
  [String.fromCodePoint(0x1e20), "G"], // LATIN CAPITAL LETTER G WITH MACRON
  [String.fromCodePoint(0x01f4), "G"], // LATIN CAPITAL LETTER G WITH ACUTE
]);
const IN_2026 = new Map([
  ["o", "ö"],
  ["O", "Ö"],
  ["g", "ğ"],
  ["G", "Ğ"],
]);
const LOOK_ALIKE_FIXES = new Map([
  [LATIN_2026, new Map([...LOOK_ALIKES].map(([ch, base]) => [ch, IN_2026.get(base)]))],
  [LATIN_1995, new Map([...LOOK_ALIKES].map(([ch, base]) => [ch, base + TURNED_COMMA]))],
]);
const LOOK_ALIKE_RE = new RegExp("[" + [...LOOK_ALIKES.keys()].join("") + "]", "gu");

// The other input forms of ö and ş, in both cases.
const LETTER_FORMS_RE = /[ōǒșŌǑȘ]/u;

// The letters of latin_2026 that latin_1995 writes with two characters.
const NEW_LETTERS_RE = /[şçğöŞÇĞÖ]/u;

const MARKS = new Set(APOSTROPHE_VARIANTS);
const CANONICAL_MARKS = new Set([TURNED_COMMA, TUTUQ]);

// s, the tutuq belgisi and h: s and h that latin_1995 keeps apart from sh.
const S_TUTUQ_H = "s" + TUTUQ + "h";

function convertWord(text, source, target) {
  return convert(text, source, target, { protect: false });
}

function resolve(orthography) {
  if (SCRIPTS.includes(orthography)) return orthography;
  return readOrthography(orthography, `unknown orthography: ${repr(orthography)}; expected one of ${SCRIPTS_REPR}`);
}

function byFinding(x, y) {
  return x[0] - y[0] || x[1] - y[1] || (x[2] < y[2] ? -1 : x[2] > y[2] ? 1 : 0);
}

/** Findings with UTF-16 offsets, sorted. */
function findings(text, orthography, settings) {
  if (!text) return [];
  const found = [];
  const wordRe = wordRegExp();
  for (const [a, b, kind] of spans(text, settings)) {
    if (kind !== null) continue;
    const piece = text.slice(a, b);
    for (const match of piece.matchAll(INVISIBLE_RUN_RE)) {
      found.push([a + match.index, a + match.index + match[0].length, INVISIBLE, ""]);
    }
    for (const [i, j, composed] of decomposed(piece)) found.push([a + i, a + j, DECOMPOSED, composed]);
    for (const match of piece.matchAll(wordRe)) {
      const finding = checkWord(match[0], orthography);
      if (finding !== null) found.push([a + match.index, a + match.index + match[0].length, ...finding]);
    }
  }
  // Array.prototype.sort is stable, as Python's sort is.
  found.sort(byFinding);
  return found;
}

/** Findings with code point offsets, as Python gives them. */
function inCodePoints(text, found) {
  if (!found.length) return found;
  const index = codePointIndexer(text);
  return found.map(([start, end, code, suggestion]) => [index(start), index(end), code, suggestion]);
}

/**
 * What in ``text`` does not belong to ``orthography`` (one of SCRIPTS or a tag
 * for one): a list of [start, end, code, suggestion], in order of
 * [start, end, code]; start and end count code points. options.protect is as
 * for convert(): protected spans are not checked.
 */
export function validate(text, orthography, options = undefined) {
  requireString(text, "text", "validate");
  requireArgument(orthography, "orthography", "validate");
  const { protect = true } = readOptions(options, ["protect"], "validate");
  orthography = resolve(orthography);
  const settings = settingsFor(protect);
  return inCodePoints(text, findings(text, orthography, settings));
}

/**
 * What converting a latin_1995 text to latin_2026 does to it: an object with
 * the keys of Python's dict, in its order -- words, changed, protected,
 * round_trip, rules_version, check, result.
 */
export function migrationReport(text, options = undefined) {
  requireString(text, "text", "migrationReport");
  const { protect = true } = readOptions(options, ["protect"], "migrationReport");
  const settings = settingsFor(protect);

  const result = convert(text, LATIN_1995, LATIN_2026, { protect: settings });
  const back = convert(result, LATIN_2026, LATIN_1995, { protect: settings });
  const check = findings(text, LATIN_1995, settings);
  const found = new Set(check.map(([start, end]) => `${start},${end}`));
  let words = 0;
  let changed = 0;
  let protectedSpans = 0;
  const wordRe = wordRegExp();
  for (const [a, b, kind] of text ? spans(text, settings) : []) {
    if (kind !== null) {
      protectedSpans += 1;
      continue;
    }
    for (const match of text.slice(a, b).matchAll(wordRe)) {
      const word = match[0];
      if (onlyMarks(word)) continue;
      words += 1;
      const neu = convertWord(word, LATIN_1995, LATIN_2026);
      const old = convertWord(word, LATIN_1995, LATIN_1995);
      if (neu !== old) changed += 1;
      const start = a + match.index;
      const end = start + word.length;
      if (found.has(`${start},${end}`)) continue;
      const again = convertWord(neu, LATIN_2026, LATIN_1995);
      if (again !== old) {
        check.push([start, end, ROUND_TRIP, again]);
      } else if (canonicalizeMarks(word.toLowerCase()).includes(S_TUTUQ_H)) {
        check.push([start, end, SEPARATOR, neu]);
      }
    }
  }
  check.sort(byFinding);
  return {
    words,
    changed,
    protected: protectedSpans,
    round_trip: back === convert(text, LATIN_1995, LATIN_1995, { protect: settings }),
    rules_version: RULES_VERSION,
    check: inCodePoints(text, check),
    result,
  };
}

/** [start, end, NFC form] of each character with combining marks after it that NFC changes. */
function* decomposed(piece) {
  for (const match of piece.matchAll(COMBINING_RUN_RE)) {
    const composed = match[0].normalize("NFC");
    if (composed !== match[0]) yield [match.index, match.index + match[0].length, composed];
  }
}

function onlyMarks(word) {
  for (const ch of word) if (!MARKS.has(ch)) return false;
  return true;
}

/** [code, suggestion] for one word, or null. */
function checkWord(word, orthography) {
  if (onlyMarks(word)) return null;
  const kind = wordClass(word);
  if (kind === CYRILLIC_WORD && hasLatinLetter(word)) {
    const folded = foldWord(word);
    return [MIXED_SCRIPT, folded !== word ? folded : null];
  }
  if (orthography === CYRILLIC) {
    if (kind !== LATIN_1995_WORD && kind !== LATIN_2026_WORD && kind !== O_FORM_WORD) return null;
    const code = kind === LATIN_1995_WORD ? LATIN_1995_WORD_FOUND : LATIN_2026_WORD_FOUND;
    return [code, convertWord(convertWord(word, LATIN_1995, LATIN_2026), LATIN_2026, CYRILLIC)];
  }
  if (kind === CYRILLIC_WORD) return [CYRILLIC_WORD_FOUND, convertWord(word, CYRILLIC, orthography)];

  const fixes = LOOK_ALIKE_FIXES.get(orthography);
  const fixed = word.replace(LOOK_ALIKE_RE, (ch) => fixes.get(ch));
  let suggestion;
  if (orthography === LATIN_2026) {
    suggestion = convertWord(fixed, LATIN_1995, LATIN_2026);
  } else if ([LATIN_2026_WORD, O_FORM_WORD].includes(wordClass(fixed))) {
    // Through latin_2026 and back, so that an sh beside ş or ö stays sh.
    suggestion = convertWord(convertWord(fixed, LATIN_1995, LATIN_2026), LATIN_2026, LATIN_1995);
  } else {
    suggestion = convertWord(fixed, LATIN_1995, LATIN_1995);
  }
  const low = canonicalizeMarks(word.toLowerCase());

  if (orthography === LATIN_2026 && (kind === LATIN_1995_WORD || low.includes(S_TUTUQ_H))) {
    return [LATIN_1995_WORD_FOUND, suggestion];
  }
  if (orthography === LATIN_1995 && NEW_LETTERS_RE.test(word)) return [LATIN_2026_WORD_FOUND, suggestion];
  if (fixed !== word) return [LOOK_ALIKE, suggestion];
  if (LETTER_FORMS_RE.test(word)) return [LETTER_FORM, suggestion];
  if (orthography === LATIN_2026 && (low.includes("sh") || low.includes("ch"))) return [DIGRAPH, suggestion];
  if (suggestion !== word) {
    // Compared in NFC, code point by code point, as Python's zip().
    const composed = Array.from(word.normalize("NFC"));
    const proposed = Array.from(suggestion);
    const changed = new Set();
    const n = Math.min(composed.length, proposed.length);
    for (let i = 0; i < n; i++) if (composed[i] !== proposed[i]) changed.add(composed[i]);
    if ([...changed].some((ch) => CANONICAL_MARKS.has(ch))) return [WRONG_MARK, suggestion];
    if ([...changed].some((ch) => MARKS.has(ch))) return [MARK_FORM, suggestion];
    // Only NFC changes the word: a compatibility character such as U+212A.
    return [DECOMPOSED, suggestion];
  }
  return null;
}
