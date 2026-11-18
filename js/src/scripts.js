// The script of each word, and letters typed from the wrong alphabet. A port
// of src/akademtranslit/scripts.py; see the docstrings there.

import { LATIN_LETTER_CLASS, isCyrillicLetter, isLatinLetter } from "./detection.js";
import { CYRILLIC_WORD, LATIN_1995_WORD, LATIN_2026_WORD, O_FORM_WORD, wordClass, wordRegExp } from "./rules.js";
import { HOMOGLYPHS } from "./tables.js";
import { codePointIndexer, requireString } from "./unicode.js";

// What scriptSpans calls each class of wordClass(); the rest are "latin".
const KINDS = new Map([
  [CYRILLIC_WORD, "cyrillic"],
  [LATIN_2026_WORD, "latin_2026"],
  [O_FORM_WORD, "latin_2026"],
  [LATIN_1995_WORD, "latin_1995"],
]);

const TO_CYRILLIC = new Map(HOMOGLYPHS.map(([latin, cyrillic]) => [latin, cyrillic]));
const TO_LATIN = new Map(HOMOGLYPHS.map(([latin, cyrillic]) => [cyrillic, latin]));

// s with comma below, U+0219 and U+0218, an input form of s with cedilla.
const S_WITH_CEDILLA = new Map([
  [String.fromCodePoint(0x0219), "ş"],
  [String.fromCodePoint(0x0218), "Ş"],
]);

const HAS_LATIN_LETTER_RE = new RegExp(LATIN_LETTER_CLASS, "u");

/** True if ``word`` has a Latin letter (a letter whose name begins with LATIN). */
export function hasLatinLetter(word) {
  return HAS_LATIN_LETTER_RE.test(word);
}

/** Split ``text`` into its words and the text between them: [piece, kind] pairs. */
export function scriptSpans(text) {
  requireString(text, "text", "scriptSpans");
  const pieces = [];
  let end = 0;
  for (const match of text.matchAll(wordRegExp())) {
    if (match.index > end) pieces.push([text.slice(end, match.index), null]);
    const word = match[0];
    pieces.push([word, kindOf(word)]);
    end = match.index + word.length;
  }
  if (end < text.length) pieces.push([text.slice(end), null]);
  return pieces;
}

function kindOf(word) {
  const kind = wordClass(word);
  if (kind === CYRILLIC_WORD && hasLatinLetter(word)) return "mixed";
  return KINDS.get(kind) ?? "latin";
}

/** The changes foldHomoglyphs() makes, as [start, stop, word] with UTF-16 offsets. */
function changes(text) {
  const out = [];
  for (const match of text.matchAll(wordRegExp())) {
    const word = match[0];
    const folded = foldWord(word);
    if (folded !== word) out.push([match.index, match.index + word.length, folded]);
  }
  return out;
}

/**
 * Where foldHomoglyphs() changes ``text``: [start, stop, word] for each word
 * it changes, with start and stop counted in code points, as in Python.
 */
export function homoglyphSpans(text) {
  requireString(text, "text", "homoglyphSpans");
  const found = changes(text);
  if (!found.length) return found;
  const index = codePointIndexer(text);
  return found.map(([start, stop, word]) => [index(start), index(stop), word]);
}

/** Write each word that has both Latin and Cyrillic letters in one of them. */
export function foldHomoglyphs(text) {
  requireString(text, "text", "foldHomoglyphs");
  let out = "";
  let end = 0;
  for (const [start, stop, word] of changes(text)) {
    out += text.slice(end, start) + word;
    end = stop;
  }
  return out + text.slice(end);
}

/** One word, folded (see scripts.py, _fold_word). */
export function foldWord(word) {
  const chars = Array.from(word);
  let latin = 0;
  let cyrillic = 0;
  for (const ch of chars) {
    if (isLatinLetter(ch)) latin++;
    if (isCyrillicLetter(ch)) cyrillic++;
  }
  if (latin && cyrillic) {
    if (latin === cyrillic) return word;
    const [table, minority] = latin > cyrillic ? [TO_LATIN, isCyrillicLetter] : [TO_CYRILLIC, isLatinLetter];
    const out = [];
    for (let ch of chars) {
      if (minority(ch)) {
        const twin = table.get(ch);
        if (twin === undefined) return word;
        ch = twin;
      }
      out.push(ch);
    }
    word = out.join("");
    if (cyrillic > latin) return word;
  } else if (cyrillic) {
    return word;
  }
  let folded = "";
  for (const ch of word) folded += S_WITH_CEDILLA.get(ch) ?? ch;
  return folded;
}
