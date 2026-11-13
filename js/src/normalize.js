// Cross-script normalization -- one search key for all three orthographies.
// A port of src/akademtranslit/normalize.py; see the docstring there.

import { CYRILLIC_CLASS, cyrillicWordToLatin1995, mapWords } from "./rules.js";
import { APOSTROPHE_VARIANTS, TURNED_COMMA, TUTUQ } from "./tables.js";
import { requireString, strip } from "./unicode.js";

// Residual Cyrillic fold, applied after the real transliteration has run.
// Anything in U+0400-U+052F that it does not cover is dropped.
export const CYRILLIC_FOLD = new Map([
  ["а", "a"], ["б", "b"], ["в", "v"], ["г", "g"], ["д", "d"], ["е", "e"], ["ё", "yo"],
  ["ж", "j"], ["з", "z"], ["и", "i"], ["й", "y"], ["к", "k"], ["л", "l"], ["м", "m"],
  ["н", "n"], ["о", "o"], ["п", "p"], ["р", "r"], ["с", "s"], ["т", "t"], ["у", "u"],
  ["ф", "f"], ["х", "x"], ["ц", "ts"], ["ч", "ch"], ["ш", "sh"], ["щ", "sh"],
  ["ъ", ""], ["ы", "i"], ["ь", ""], ["э", "e"], ["ю", "yu"], ["я", "ya"],
  // Uzbek-specific letters, folded to their bare Latin base.
  ["ў", "o"], ["ғ", "g"], ["қ", "q"], ["ҳ", "h"],
  // Homoglyphs from neighbouring Cyrillic orthographies.
  ["ј", "j"], ["і", "i"], ["ї", "i"], ["є", "e"], ["ѓ", "g"], ["ќ", "k"],
]);

// The reformed letters, folded to the same base the Cyrillic table produces.
export const LATIN_2026_FOLD = new Map([
  ["ş", "sh"],
  ["ç", "ch"],
  ["ğ", "g"],
  ["ö", "o"],
  // The other input forms (LATIN_2026_INPUT_ALIASES).
  [String.fromCodePoint(0x014d), "o"], // o with macron
  [String.fromCodePoint(0x01d2), "o"], // o with caron
  [String.fromCodePoint(0x0219), "sh"], // s with comma below
]);

const MARKS_RE = new RegExp(
  "[" + [...new Set([...APOSTROPHE_VARIANTS, TURNED_COMMA, TUTUQ])].join("") + "]",
  "gu",
);

// U+00B4 ACUTE ACCENT, the one apostrophe variant that NFKC decomposes.
const ACUTE_ACCENT = "´";

const CYRILLIC_ANY_RE = new RegExp(CYRILLIC_CLASS, "gu");
const CYRILLIC_TEST_RE = new RegExp(CYRILLIC_CLASS, "u");
const LATIN_2026_FOLD_RE = new RegExp("[" + [...LATIN_2026_FOLD.keys()].join("") + "]", "gu");
const NON_ALNUM_RE = /[^a-z0-9]/gu;
const SPACES_RE = / +/g; // after NON_ALNUM_RE only ASCII spaces are left

/** Fold Cyrillic characters to Latin; pass everything else through. */
export function foldCyrillic(text) {
  requireString(text, "text", "foldCyrillic");
  return text.replace(CYRILLIC_ANY_RE, (ch) => CYRILLIC_FOLD.get(ch) ?? "");
}

/** Fold the reformed letters to their latin_1995-shaped bases. */
export function foldLatin2026(text) {
  return text.replace(LATIN_2026_FOLD_RE, (ch) => LATIN_2026_FOLD.get(ch));
}

/** Return the cross-script match key for ``text``. */
export function normalize(text) {
  requireString(text, "text", "normalize");
  if (!text || !strip(text)) return "";
  // U+00B4 is an apostrophe variant, but NFKC would turn it into a space and
  // a combining accent. Make it a mark first.
  text = text.replaceAll(ACUTE_ACCENT, TUTUQ);
  text = text.normalize("NFKC");
  text = text.toLowerCase();
  if (CYRILLIC_TEST_RE.test(text)) text = mapWords(text, cyrillicWordToLatin1995);
  text = text.replace(MARKS_RE, "");
  text = foldLatin2026(text);
  text = text.replace(CYRILLIC_ANY_RE, (ch) => CYRILLIC_FOLD.get(ch) ?? "");
  text = text.replace(NON_ALNUM_RE, " ");
  // Python: \s+ -> " ", then strip(); only ASCII spaces remain at this point.
  return strip(text.replace(SPACES_RE, " "));
}

/** True if ``text`` contains any character in U+0400-U+052F. */
export function isCyrillic(text) {
  requireString(text, "text", "isCyrillic");
  return CYRILLIC_TEST_RE.test(text);
}
