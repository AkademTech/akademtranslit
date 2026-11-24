// Context-dependent transliteration rules and the word-level engine. A port of
// src/akademtranslit/rules.py; the module docstring there describes the seven
// positional rules (е, e, ц, ts, с before ҳ, ъ, ь).

import {
  APOSTROPHE_VARIANTS,
  CYRILLIC,
  CYRILLIC_FIRST,
  CYRILLIC_LAST,
  CYRILLIC_TO_LATIN_1995,
  CYRILLIC_VOWELS,
  LATIN_1995_TO_2026_STEPS,
  LATIN_1995_TO_CYRILLIC,
  LATIN_2026_INPUT_ALIASES,
  LATIN_2026_TO_1995_STEPS,
  LATIN_VOWELS,
  TS_LOANWORD_STEMS,
  TURNED_COMMA,
  TUTUQ,
} from "./tables.js";
import { LETTER, cpLength, escapeRegExp, hasCase, isUpper } from "./unicode.js";

// --- tokenisation ------------------------------------------------------------

/** The apostrophe marks, as a RegExp class. */
export const APOS_CLASS = "[" + escapeRegExp(APOSTROPHE_VARIANTS.join("")) + "]";

// A word is a run of letters, optionally joined by apostrophe-like marks, and
// optionally ending in one -- but only after o or g. Python's [^\W\d_] is
// LETTER (see unicode.js): letters and the numbers that are not digits.
const WORD_SOURCE = `${LETTER}+(?:${APOS_CLASS}${LETTER}+)*(?:(?<=[oOgG])${APOS_CLASS})?`;

/** A new global RegExp for words; each caller keeps its own (lastIndex is state). */
export function wordRegExp() {
  return new RegExp(WORD_SOURCE, "gu");
}

const WORD_RE = wordRegExp();
const MARKS = new Set(APOSTROPHE_VARIANTS);
const TURNED_COMMA_AFTER = new Set("og");

/** Rewrite every apostrophe variant to its canonical character. */
export function canonicalizeMarks(wordLower) {
  // Code points, as Python iterates: the mark looks at the character before it.
  let out = "";
  let prev = "";
  for (const ch of wordLower) {
    if (MARKS.has(ch)) {
      prev = TURNED_COMMA_AFTER.has(prev) ? TURNED_COMMA : TUTUQ;
    } else {
      prev = ch;
    }
    out += prev;
  }
  return out;
}

// --- case --------------------------------------------------------------------

const UPPER = "U";
const LOWER = "L";
const NO_CASE = "-";

/**
 * The case of each code point of ``chars`` (an array of code points), as a
 * string of U, L and - (no case). An h after a capital S or C is a capital if
 * the word has another capital: Sh and Ch are one letter in latin_1995.
 */
function caseMask(chars) {
  const mask = [];
  let capitals = 0;
  for (const ch of chars) {
    if (!hasCase(ch)) {
      mask.push(NO_CASE);
    } else if (isUpper(ch)) {
      mask.push(UPPER);
      capitals++;
    } else {
      mask.push(LOWER);
    }
  }
  if (capitals > 1) {
    for (let i = 1; i < chars.length; i++) {
      if (chars[i] === "h" && (chars[i - 1] === "S" || chars[i - 1] === "C")) mask[i] = UPPER;
    }
  }
  return mask.join("");
}

/** Where the letter units of a word start, as code point indices. */
function unitStarts(mask) {
  const starts = [0];
  let previous = NO_CASE;
  let capitals = 0;
  for (let i = 0; i < mask.length; i++) {
    const c = mask[i];
    if (c === NO_CASE) continue;
    if (c === UPPER && previous === LOWER) {
      starts.push(i);
    } else if (c === LOWER && capitals >= 2) {
      starts.push(i);
    }
    capitals = c === UPPER ? capitals + 1 : 0;
    previous = c;
  }
  return starts;
}

/** True if the case of ``chars`` is not all lowercase, all caps or an initial capital. */
function irregular(chars) {
  const cased = [];
  for (const ch of chars) if (hasCase(ch)) cased.push(isUpper(ch));
  return cased.slice(1).some(Boolean) && !cased.every(Boolean);
}

/** ``result`` with the case of ``source``, code point by code point. */
function copyCase(chars, result) {
  let out = "";
  let upper = false;
  const news = Array.from(result);
  const n = Math.min(chars.length, news.length);
  for (let i = 0; i < n; i++) {
    if (hasCase(chars[i])) upper = isUpper(chars[i]);
    out += upper ? news[i].toUpperCase() : news[i].toLowerCase();
  }
  return out;
}

/** Restore the casing of ``source`` onto ``result`` (see rules.py, apply_case). */
export function applyCase(source, result) {
  const chars = Array.from(source);
  return applyCaseMasked(chars, result, caseMask(chars));
}

function applyCaseMasked(chars, result, mask) {
  const cased = mask.replaceAll(NO_CASE, "");
  if (!cased || !result) return result;
  // Lengths in code points, as Python's len().
  if (cpLength(result) === chars.length && irregular(chars)) return copyCase(chars, result);
  if (cased.length > 1 && !cased.includes(LOWER)) return result.toUpperCase();
  if (cased[0] === UPPER) {
    const first = String.fromCodePoint(result.codePointAt(0));
    return first.toUpperCase() + result.slice(first.length);
  }
  return result;
}

/** Apply ``transform`` to each word of ``text``, preserving everything else. */
export function mapWords(text, transform) {
  return text.replace(WORD_RE, (word) => mapWord(word, transform));
}

/** mapWords() with a transform chosen for each word. */
export function mapWordsBy(text, transformFor) {
  return text.replace(WORD_RE, (word) => mapWord(word, transformFor(word)));
}

/** Apply ``transform`` to one word, as mapWords() does to each. */
export function mapWord(source, transform) {
  const lower = source.toLowerCase();
  if (lower === source) return transform(canonicalizeMarks(lower));
  const chars = Array.from(source);
  const mask = caseMask(chars);
  const starts = unitStarts(mask);
  if (starts.length === 1) {
    return applyCaseMasked(chars, transform(canonicalizeMarks(lower)), mask);
  }
  // Each unit is cased by its own letters: the h of Ter|Sh has no other
  // capital beside it in Sh.
  let out = "";
  for (let k = 0; k < starts.length; k++) {
    const unit = chars.slice(starts[k], k + 1 < starts.length ? starts[k + 1] : chars.length).join("");
    out += applyCase(unit, transform(canonicalizeMarks(unit.toLowerCase())));
  }
  return out;
}

// --- the orthography a word shows ---------------------------------------------

export const CYRILLIC_WORD = "C";
export const LATIN_2026_WORD = "N";
export const LATIN_1995_WORD = "O";
export const O_FORM_WORD = "D";
export const SH_CH_WORD = "W";
export const PLAIN_WORD = "-";

/** Any code point in CYRILLIC_FIRST..CYRILLIC_LAST, as a RegExp class. */
export const CYRILLIC_CLASS =
  `[\\u{${CYRILLIC_FIRST.toString(16)}}-\\u{${CYRILLIC_LAST.toString(16)}}]`;

const CYRILLIC_RE = new RegExp(CYRILLIC_CLASS, "u");
const LATIN_2026_LETTERS_RE = new RegExp("[şçğö\\u0219]", "u"); // and s with comma below
const O_FORMS_RE = /[ōǒ]/u;
const OI = "o" + TURNED_COMMA;
const GI = "g" + TURNED_COMMA;

/** Which orthography one word shows, as one of six classes (see rules.py). */
export function wordClass(word) {
  word = canonicalizeMarks(word.toLowerCase());
  if (CYRILLIC_RE.test(word)) return CYRILLIC_WORD;
  if (LATIN_2026_LETTERS_RE.test(word)) return LATIN_2026_WORD;
  if (word.includes(OI) || word.includes(GI)) return LATIN_1995_WORD;
  if (O_FORMS_RE.test(word)) return O_FORM_WORD;
  if (word.includes("sh") || word.includes("ch")) return SH_CH_WORD;
  return PLAIN_WORD;
}

// --- Cyrillic -> latin_1995 --------------------------------------------------

const CYRILLIC_CONSONANTS = new Set("бвгджзйклмнпрстфхцчшщқғҳ");
const CYRILLIC_IOTATED = new Set("еёюя");

// The month names whose я latin_1995 writes as a, and where the я is.
const CYRILLIC_MONTHS_WITH_A = [["сентябр", 4], ["октябр", 3]];

/**
 * Convert one lowercase Cyrillic word to latin_1995, by the positional rules,
 * as 0.3.1 had them. normalize() reads Cyrillic with it; convert() uses
 * convertCyrillicWord() (see rules.py).
 */
export function cyrillicWordToLatin1995(word) {
  return cyrillicWord(word, false);
}

/** Convert one lowercase Cyrillic word to latin_1995, as convert() does (see rules.py). */
export function convertCyrillicWord(word) {
  return cyrillicWord(word, true);
}

/**
 * The two above: ``whole`` adds the rules for whole words.
 *
 * Iterates UTF-16 units. That gives Python's result: every rule compares a
 * character with Cyrillic letters, which are all in the BMP, so half of a
 * surrogate pair matches none of them, just as the whole astral character does
 * not, and both halves are copied through. A month name is in the BMP, so its
 * я is at the same index as in Python.
 */
function cyrillicWord(word, whole) {
  let a = -1;
  if (whole) {
    for (const [stem, at] of CYRILLIC_MONTHS_WITH_A) if (word.startsWith(stem)) a = at;
  }
  let out = "";
  const n = word.length;
  for (let i = 0; i < n; i++) {
    const ch = word[i];
    const prev = i ? word[i - 1] : "";
    const nxt = i + 1 < n ? word[i + 1] : "";
    if (i === a) {
      // The я of сентябр, октябр: sentabr, oktabr.
      out += "a";
    } else if (ch === "е") {
      const initialOrAfterVowel = i === 0 || CYRILLIC_VOWELS.has(prev) || prev === "ъ" || prev === "ь";
      out += initialOrAfterVowel ? "ye" : "e";
    } else if (ch === "ц") {
      // ts only after a vowel; word-initially and after a consonant, s.
      out += i > 0 && CYRILLIC_VOWELS.has(prev) ? "ts" : "s";
    } else if (ch === "с" && nxt === "ҳ") {
      out += "s" + TUTUQ;
    } else if (ch === "ъ" && (prev === "ў" || (CYRILLIC_CONSONANTS.has(prev) && CYRILLIC_IOTATED.has(nxt)))) {
      // No mark here in 1995: объект -> obyekt, мўъжиза -> moʻjiza.
      continue;
    } else if (ch === "ь" && nxt === "о") {
      out += "y";
    } else {
      const mapped = CYRILLIC_TO_LATIN_1995.get(ch);
      out += mapped === undefined ? ch : mapped;
    }
  }
  return out;
}

// --- latin_1995 -> Cyrillic --------------------------------------------------

const TS_SUFFIXES = [
  "sa", "sak", "sam", "sang", "sangiz", "salar",
  "sin", "sinlar",
  "siz", "sizlik",
  "sevar",
];

const TS_FOLLOWERS = [
  "lik", "ligi", "lar", "roq",
  "ga", "ka", "da", "dan", "ni", "ning",
  "man", "san", "miz", "siz", "dir",
  "mi", "chi",
  "gina", "kina", "yu", "u", "ku", "yoq", "mikan",
];

// fullmatch: anchored at both ends.
const TS_SUFFIX_RE = new RegExp(
  "^(?:" + TS_SUFFIXES.join("|") + ")(?:" + TS_FOLLOWERS.join("|") + ")*$",
  "u",
);

const VOWELS_AND_Y = new Set([...LATIN_VOWELS, "y"]);
const VOWELS_BEFORE_E = new Set("aeiou");

/** True if the ts at word[i] is т + с rather than the letter ц (see rules.py). */
function tsSplits(word, i) {
  const rest = word.slice(i + 1);
  if (rest.startsWith("sh") || rest.startsWith("s" + TUTUQ + "h")) return true;
  if (i === 0) return false;
  if (word.slice(i + 2, i + 3) === "i" && VOWELS_AND_Y.has(word.slice(i + 3, i + 4))) return false;
  const stem = word.slice(0, i);
  if (
    word.startsWith("in", i + 2) &&
    (stem.endsWith("mi") || stem.endsWith("rubi") || stem === "gli" || stem === "oksito" || stem === "rifampi")
  ) {
    return false;
  }
  if (word.startsWith("in", i + 2) && (stem.endsWith("floksa") || stem.endsWith("ley") || stem === "amika")) {
    return false;
  }
  if (stem === "ak") return false;
  if (TS_LOANWORD_STEMS.includes(word.slice(0, i + 2))) return false;
  return TS_SUFFIX_RE.test(rest);
}

// The table as one sticky alternation, in its order: at each position the
// first source that matches wins, as in Python's loop over the table.
const LATIN_1995_TABLE_RE = new RegExp(
  LATIN_1995_TO_CYRILLIC.map(([source]) => escapeRegExp(source)).join("|"),
  "uy",
);
const LATIN_1995_TABLE = new Map(LATIN_1995_TO_CYRILLIC);

// The month names whose a Cyrillic writes as я, and where the a is.
const LATIN_MONTHS_WITH_YA = [["sentabr", 4], ["oktabr", 3]];

/**
 * Convert one lowercase latin_1995 word to Cyrillic (sentabr, oktabr with any
 * suffix: сентябр, октябр; see rules.py).
 *
 * Iterates UTF-16 units; as in cyrillicWordToLatin1995(), every comparison is
 * with ASCII letters or the two marks, so the result is Python's.
 */
export function latin1995WordToCyrillic(word) {
  let out = "";
  let i = 0;
  const n = word.length;
  let ya = -1;
  for (const [stem, at] of LATIN_MONTHS_WITH_YA) if (word.startsWith(stem)) ya = at;
  while (i < n) {
    if (i === ya) {
      // The a of sentabr, oktabr: сентябр, октябр.
      out += "я";
      i += 1;
      continue;
    }
    if (word.startsWith("ye", i)) {
      out += "е";
      i += 2;
      continue;
    }
    if (word[i] === "e") {
      const afterAVowel = i > 0 && VOWELS_BEFORE_E.has(word[i - 1]) && !word.startsWith("v", i + 1);
      out += i === 0 || afterAVowel ? "э" : "е";
      i += 1;
      continue;
    }
    if (word.startsWith("ts", i) && tsSplits(word, i)) {
      out += "т";
      i += 1;
      continue;
    }
    LATIN_1995_TABLE_RE.lastIndex = i;
    const m = LATIN_1995_TABLE_RE.exec(word);
    if (m !== null) {
      out += LATIN_1995_TABLE.get(m[0]);
      i += m[0].length;
    } else {
      // Not Uzbek-Latin (a digit, a borrowed w/c, a stray glyph) -- keep it.
      out += word[i];
      i += 1;
    }
  }
  return out;
}

// --- latin_1995 <-> latin_2026 -----------------------------------------------

/** Convert one lowercase latin_1995 word to latin_2026. */
export function latin1995WordTo2026(word) {
  for (const [source, target] of LATIN_1995_TO_2026_STEPS) word = word.replaceAll(source, target);
  return word;
}

/** Write the other input forms of ö and ş in one lowercase word as those letters. */
export function latin2026CanonicalWord(word) {
  for (const [source, target] of LATIN_2026_INPUT_ALIASES) word = word.replaceAll(source, target);
  return word;
}

/** Convert one lowercase latin_2026 word to latin_1995. */
export function latin2026WordTo1995(word) {
  word = latin2026CanonicalWord(word);
  for (const [source, target] of LATIN_2026_TO_1995_STEPS) word = word.replaceAll(source, target);
  return word;
}

// --- whole words -----------------------------------------------------------------
//
// Rules that need the word as it was written, before mapWord() lowercases it
// and splits it into letter units. convert() applies them.

/** A Roman numeral, 1 to 3999, in capitals (fullmatch: anchored at both ends). */
export const ROMAN_NUMERAL_RE = /^M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$/u;

/**
 * True if ``word``, followed by the character ``after`` (or ""), is a Roman
 * numeral, which conversion from Latin to Cyrillic keeps (see rules.py).
 */
export function isRomanNumeral(word, after = "") {
  if (!word || !ROMAN_NUMERAL_RE.test(word)) return false;
  return word.length > 1 || after !== ".";
}

// The month names that Cyrillic writes with ь when they stand alone.
const SOFT_SIGN_MONTHS = new Set([
  "yanvar", "fevral", "aprel", "iyun", "iyul",
  "sentabr", "sentyabr", "oktabr", "oktyabr", "noyabr", "dekabr",
]);

/**
 * ``cyrillic``, the Cyrillic of the Latin ``word``, with the ь of a month name
 * that stands alone, in the case of the letter before it (see rules.py).
 */
export function monthSoftSign(word, cyrillic) {
  if (!SOFT_SIGN_MONTHS.has(word.toLowerCase())) return cyrillic;
  // The last letter of a month name in Cyrillic is in the BMP.
  return cyrillic + (isUpper(cyrillic.slice(-1)) ? "Ь" : "ь");
}

// --- dates -------------------------------------------------------------------------

// A number with no letter or digit before it (Python's [^\W_]), and the one
// hyphen (U+002D or U+2011) or the one space (U+0020 or U+00A0) after it.
const NUMBER_HYPHEN_RE = /(?<![\p{L}\p{N}])([0-9]+)([-‑])/gu;
const NUMBER_SPACE_RE = /(?<![\p{L}\p{N}])([0-9]+)([  ])/gu;
const WORD_AT_RE = new RegExp(WORD_SOURCE, "uy");

const DAYS = new Set(Array.from({ length: 31 }, (_, k) => String(k + 1)));

// A month name, lowercase, with the possessive and a case ending, each if it
// is there (fullmatch: anchored at both ends).
export const CYRILLIC_MONTH_RE = new RegExp(
  "^(?:январ|феврал|март|апрел|май|июн|июл|август|сентябр|октябр|ноябр|декабр)ь?" +
    "и?(?:нинг|ни|га|да|дан|даги|гача)?$",
  "u",
);
export const LATIN_MONTH_RE = new RegExp(
  "^(?:yanvar|fevral|mart|aprel|may|iyun|iyul|avgust|sentabr|sentyabr|oktabr|oktyabr|noyabr|dekabr)" +
    "i?(?:ning|ni|ga|da|dan|dagi|gacha|gaça)?$",
  "u",
);

/** The word of ``text`` that starts at ``at``, lowercase, or "". */
function wordAt(text, at) {
  WORD_AT_RE.lastIndex = at;
  const m = WORD_AT_RE.exec(text);
  return m === null ? "" : m[0].toLowerCase();
}

/**
 * ``text``, converted to ``target``, with the separator after the number of a
 * year or of a day of the month as ``target`` writes it (see rules.py, dates).
 */
export function dates(text, target) {
  if (target === CYRILLIC) {
    return text.replace(NUMBER_HYPHEN_RE, (all, number, hyphen, offset) => {
      const word = wordAt(text, offset + all.length);
      const year = number.length >= 3 && number.length <= 4 && number[0] !== "0" && word.startsWith("йил");
      const day = DAYS.has(number) && CYRILLIC_MONTH_RE.test(word);
      if (!(year || day)) return all;
      return number + (hyphen === "-" ? " " : " ");
    });
  }
  return text.replace(NUMBER_SPACE_RE, (all, number, space, offset) => {
    const word = wordAt(text, offset + all.length);
    const year = number.length === 4 && Number(number) >= 1000 && Number(number) <= 2099 && word.startsWith("yil");
    const day = DAYS.has(number) && LATIN_MONTH_RE.test(word);
    if (!(year || day)) return all;
    return number + (space === " " ? "-" : "‑");
  });
}
