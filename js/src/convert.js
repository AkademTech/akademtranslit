// convert(), toLatin(), toCyrillic(), toAscii() and detectScript(). A port of
// the functions in src/akademtranslit/__init__.py; the docstrings there are
// the documentation.

import { orthography, SCRIPTS_REPR } from "./tags.js";
import { settingsFor, spans } from "./protect.js";
import {
  CYRILLIC_CLASS,
  CYRILLIC_WORD,
  LATIN_1995_WORD,
  LATIN_2026_WORD,
  O_FORM_WORD,
  PLAIN_WORD,
  SH_CH_WORD,
  cyrillicWordToLatin1995,
  latin1995WordTo2026,
  latin1995WordToCyrillic,
  latin2026CanonicalWord,
  latin2026WordTo1995,
  mapWords,
  mapWordsBy,
  wordClass,
  wordRegExp,
} from "./rules.js";
import {
  APOSTROPHE_VARIANTS,
  ASCII_CAPITALS,
  ASCII_SCHEME,
  CYRILLIC,
  LATIN_1995,
  LATIN_2026,
  SCRIPTS,
} from "./tables.js";
import { escapeRegExp, isUpper, readOptions, repr, requireString } from "./unicode.js";

// Letters that exist only in latin_2026, with the other input forms of ö (o
// with macron and caron) and ş (s with comma below).
const REFORM_LETTERS_RE = /[şçğöŞÇĞÖōǒŌǑșȘ]/u;
const CYRILLIC_RE = new RegExp(CYRILLIC_CLASS, "u");

// Every conversion is a chain of word-level steps; latin_1995 is the pivot.
const PIPELINES = new Map([
  [`${CYRILLIC}>${LATIN_1995}`, [cyrillicWordToLatin1995]],
  [`${CYRILLIC}>${LATIN_2026}`, [cyrillicWordToLatin1995, latin1995WordTo2026, latin2026CanonicalWord]],
  [`${LATIN_1995}>${CYRILLIC}`, [latin1995WordToCyrillic]],
  [`${LATIN_1995}>${LATIN_2026}`, [latin2026CanonicalWord, latin1995WordTo2026]],
  [`${LATIN_2026}>${LATIN_1995}`, [latin2026WordTo1995]],
  [`${LATIN_2026}>${LATIN_2026}`, [latin2026CanonicalWord]],
  [`${LATIN_2026}>${CYRILLIC}`, [latin2026WordTo1995, latin1995WordToCyrillic]],
]);

/** Which of the three orthographies ``text`` is written in (read in NFC). */
export function detectScript(text) {
  requireString(text, "text", "detectScript");
  text = text.normalize("NFC");
  if (CYRILLIC_RE.test(text)) return CYRILLIC;
  if (REFORM_LETTERS_RE.test(text)) return LATIN_2026;
  return LATIN_1995;
}

/** How source "auto" reads each word of ``pieces``: a Map word -> orthography. */
function autoSources(pieces, target) {
  const classes = new Map();
  const counts = {
    [CYRILLIC_WORD]: 0,
    [LATIN_2026_WORD]: 0,
    [LATIN_1995_WORD]: 0,
    [O_FORM_WORD]: 0,
    [SH_CH_WORD]: 0,
    [PLAIN_WORD]: 0,
  };
  const wordRe = wordRegExp();
  for (const piece of pieces) {
    for (const match of piece.matchAll(wordRe)) {
      const word = match[0];
      let kind = classes.get(word);
      if (kind === undefined) {
        kind = wordClass(word);
        classes.set(word, kind);
      }
      counts[kind] += 1;
    }
  }
  const cyrillic = counts[CYRILLIC_WORD];
  const others =
    counts[LATIN_2026_WORD] + counts[LATIN_1995_WORD] + counts[O_FORM_WORD] + counts[SH_CH_WORD] + counts[PLAIN_WORD];
  const mostlyCyrillic = cyrillic >= 1 && cyrillic >= others;
  const neu = counts[LATIN_2026_WORD];
  const old = counts[LATIN_1995_WORD];
  const either = old + counts[SH_CH_WORD];
  const latin = neu > 0 && (neu > either || (neu === either && old === 0)) ? LATIN_2026 : LATIN_1995;
  const other = target === CYRILLIC && mostlyCyrillic ? CYRILLIC : latin;
  const byClass = {
    [CYRILLIC_WORD]: CYRILLIC,
    [LATIN_2026_WORD]: LATIN_2026,
    [LATIN_1995_WORD]: LATIN_1995,
    [O_FORM_WORD]: LATIN_2026,
    [SH_CH_WORD]: other,
    [PLAIN_WORD]: other,
  };
  const sources = new Map();
  for (const [word, kind] of classes) sources.set(word, byClass[kind]);
  return sources;
}

/** The function that converts one lowercase word from ``source`` to ``target``. */
function steps(source, target) {
  const chain = PIPELINES.get(`${source}>${target}`) ?? [];
  return (word) => {
    for (const step of chain) word = step(word);
    return word;
  };
}

/**
 * Convert ``text`` from one orthography to another. ``source`` is "auto" (the
 * default: each word is read in the orthography it shows) or one of SCRIPTS or
 * a language tag; so is ``target`` (default latin_2026). options.protect is
 * true (the default), false or a Protect.
 */
export function convert(text, source = "auto", target = LATIN_2026, options = undefined) {
  requireString(text, "text", "convert");
  const { protect = true } = readOptions(options, ["protect"], "convert");
  if (!SCRIPTS.includes(source) && source !== "auto") {
    source = orthography(source, `unknown source script: ${repr(source)}; expected one of ${SCRIPTS_REPR} or 'auto'`);
  }
  if (!SCRIPTS.includes(target)) {
    target = orthography(target, `unknown target script: ${repr(target)}; expected one of ${SCRIPTS_REPR}`);
  }
  const settings = settingsFor(protect);
  if (!text) return text;

  // Protected spans come out as they are; the text between them is composed
  // (NFC) and converted, and only it decides the orthography.
  const pieces = spans(text, settings).map(([a, b, kind]) =>
    kind !== null ? [text.slice(a, b), kind] : [text.slice(a, b).normalize("NFC"), null],
  );
  let convertPiece;
  if (source === "auto") {
    const sources = autoSources(
      pieces.filter(([, kind]) => kind === null).map(([piece]) => piece),
      target,
    );
    const transforms = {};
    for (const script of SCRIPTS) transforms[script] = steps(script, target);
    convertPiece = (piece) => mapWordsBy(piece, (word) => transforms[sources.get(word)]);
  } else {
    const transform = steps(source, target);
    convertPiece = (piece) => mapWords(piece, transform);
  }
  // mapWords canonicalises the marks even when there are no steps.
  let out = "";
  for (const [piece, kind] of pieces) out += kind !== null ? piece : convertPiece(piece);
  return out;
}

/** Convert ``text`` to Latin, in ``variant`` (default latin_2026, or a tag for one). */
export function toLatin(text, variant = LATIN_2026, options = undefined) {
  requireString(text, "text", "toLatin");
  const { protect = true } = readOptions(options, ["protect"], "toLatin");
  if (variant !== LATIN_1995 && variant !== LATIN_2026) {
    const unknown = `unknown Latin variant: ${repr(variant)}; expected 'latin_1995' or 'latin_2026'`;
    if (SCRIPTS.includes(variant)) throw new RangeError(unknown);
    const script = orthography(variant, unknown);
    if (script !== LATIN_1995 && script !== LATIN_2026) {
      throw new RangeError(
        `${repr(variant)} names ${repr(script)}, not a Latin orthography; ` +
          "expected 'latin_1995' or 'latin_2026', or a tag for one of them",
      );
    }
    variant = script;
  }
  return convert(text, "auto", variant, { protect });
}

/** Convert ``text`` to Cyrillic from either Latin orthography. */
export function toCyrillic(text, options = undefined) {
  requireString(text, "text", "toCyrillic");
  const { protect = true } = readOptions(options, ["protect"], "toCyrillic");
  return convert(text, "auto", CYRILLIC, { protect });
}

const NO_MARKS_RE = new RegExp("[" + escapeRegExp(APOSTROPHE_VARIANTS.join("")) + "]", "gu");
const ASCII_CAPITAL_FORMS = new Map(ASCII_CAPITALS.map(([letter, ...forms]) => [letter, forms]));
const NOT_ASCII_RE = /[^\x00-\x7F]/gu;

/** Write capital Ş and Ç by the characters around them (see ASCII_CAPITALS). */
function asciiCapitals(text) {
  if (![...ASCII_CAPITAL_FORMS.keys()].some((letter) => text.includes(letter))) return text;
  // Code points: a neighbour outside the BMP (U+1D400 is a capital) is one
  // character to Python.
  const chars = Array.from(text);
  let out = "";
  for (let i = 0; i < chars.length; i++) {
    const forms = ASCII_CAPITAL_FORMS.get(chars[i]);
    if (forms === undefined) {
      out += chars[i];
      continue;
    }
    const besideACapital = (i > 0 && isUpper(chars[i - 1])) || (i + 1 < chars.length && isUpper(chars[i + 1]));
    out += besideACapital ? forms[0] : forms[1];
  }
  return out;
}

/** Write ``text`` in ASCII, for names and logins (see __init__.py, to_ascii). */
export function toAscii(text) {
  requireString(text, "text", "toAscii");
  text = toLatin(text, LATIN_1995);
  if (!text) return text;
  for (const [letter, asciiForm] of ASCII_SCHEME) text = text.replaceAll(letter, asciiForm);
  text = asciiCapitals(text);
  text = text.replace(NO_MARKS_RE, "").normalize("NFKD");
  return text.replace(NOT_ASCII_RE, "");
}
