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
  convertCyrillicWord,
  dates,
  isRomanNumeral,
  latin1995WordTo2026,
  latin1995WordToCyrillic,
  latin2026CanonicalWord,
  latin2026WordTo1995,
  mapWord,
  monthSoftSign,
  namesALetter,
  romanSeriesMember,
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
const REFORM_LETTERS_RE = new RegExp("[şçğöŞÇĞÖ\\u014D\\u01D2\\u014C\\u01D1\\u0219\\u0218]", "u");
const CYRILLIC_RE = new RegExp(CYRILLIC_CLASS, "u");

// Every conversion is a chain of word-level steps; latin_1995 is the pivot.
// Cyrillic is read with convertCyrillicWord; normalize keeps cyrillicWordToLatin1995.
const PIPELINES = new Map([
  [`${CYRILLIC}>${LATIN_1995}`, [convertCyrillicWord]],
  [`${CYRILLIC}>${LATIN_2026}`, [convertCyrillicWord, latin1995WordTo2026, latin2026CanonicalWord]],
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

// What separates one letter from the words that make it a Roman numeral or a
// letter: the word before it after one space or U+00A0, the word after it
// after one of those, a hyphen or U+2011 (see __init__.py).
const ONE_SPACE = new Set([" ", "\u{A0}"]);
const BEFORE_FOLLOWING = new Set([...ONE_SPACE, "-", "\u{2011}"]);

// What links two numerals in a series: one hyphen or dash with no space
// around it, a comma and one space or U+00A0, or va or yoki with one space
// or U+00A0 on each side.
const SERIES_LINKS = new Set(["-", "\u{2010}", "\u{2011}", "\u{2012}", "\u{2013}", "\u{2014}", ", ", ",\u{A0}"]);
const SERIES_WORDS = new Set(["va", "yoki"]);

/**
 * The indices in ``matches`` (from matchAll over ``piece``, in order) of the
 * words that conversion to Cyrillic keeps as Roman numerals: a word that is
 * one on its own (isRomanNumeral), and the members of a series of two or more
 * of which one is, unless the word after the series begins with harf or
 * tovush, when each member is what it is on its own (see __init__.py,
 * _roman_numerals). Linear in the length of the
 * piece. The characters beside a word here are one UTF-16 unit each: only
 * ".", the spaces, the hyphens and dashes and "," count.
 */
function romanNumerals(piece, matches) {
  const count = matches.length;
  const end = (i) => matches[i].index + matches[i][0].length;
  const between = (i, j) => piece.slice(end(i), matches[j].index);
  const after = (i) => piece.slice(end(i), end(i) + 1);
  const following = (i) => (i + 1 < count && BEFORE_FOLLOWING.has(between(i, i + 1)) ? matches[i + 1][0] : "");
  const alone = (i) => {
    const word = matches[i][0];
    if (word.length !== 1) return isRomanNumeral(word, after(i));
    const before = i > 0 && ONE_SPACE.has(between(i - 1, i)) ? matches[i - 1][0] : "";
    return isRomanNumeral(word, after(i), before, following(i));
  };
  const member = (i) => romanSeriesMember(matches[i][0], after(i));
  const linked = (i) => {
    if (i + 1 < count && SERIES_LINKS.has(between(i, i + 1)) && member(i + 1)) return i + 1;
    if (
      i + 2 < count &&
      SERIES_WORDS.has(matches[i + 1][0]) &&
      ONE_SPACE.has(between(i, i + 1)) &&
      ONE_SPACE.has(between(i + 1, i + 2)) &&
      member(i + 2)
    ) {
      return i + 2;
    }
    return null;
  };

  const kept = new Set();
  let i = 0;
  while (i < count) {
    const series = [i];
    if (member(i)) {
      for (let link = linked(i); link !== null; link = linked(link)) series.push(link);
    }
    if (series.length === 1) {
      if (alone(i)) kept.add(i);
    } else if (namesALetter(following(series.at(-1)))) {
      for (const k of series) if (alone(k)) kept.add(k);
    } else if (series.some(alone)) {
      for (const k of series) kept.add(k);
    }
    i = series.at(-1) + 1;
  }
  return kept;
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
  let sourceOf;
  if (source === "auto") {
    const sources = autoSources(
      pieces.filter(([, kind]) => kind === null).map(([piece]) => piece),
      target,
    );
    sourceOf = (word) => sources.get(word);
  } else {
    sourceOf = () => source;
  }
  const transforms = {};
  for (const script of SCRIPTS) transforms[script] = steps(script, target);
  const toCyrillic = target === CYRILLIC;
  const wordRe = wordRegExp();
  const convertWord = (match, numeral) => {
    const word = match[0];
    const script = sourceOf(word);
    if (toCyrillic && script !== CYRILLIC) {
      // The rules that need the whole word as it stands, and the text around
      // it: a Roman numeral (numeral, from romanNumerals) stays as it is.
      if (numeral) return word;
      return monthSoftSign(word, mapWord(word, transforms[script]));
    }
    return mapWord(word, transforms[script]);
  };
  // mapWord canonicalises the marks even when there are no steps. Then dates:
  // the separator after the number of a year or a day of the month, before a
  // word read in the other script; crossed holds where those words start in
  // the converted piece (UTF-16 offsets, as dates() reads them).
  const convertPiece = (piece) => {
    let converted = "";
    const crossed = new Set();
    let last = 0;
    const matches = [...piece.matchAll(wordRe)];
    const numerals = toCyrillic ? romanNumerals(piece, matches) : new Set();
    for (const [index, match] of matches.entries()) {
      const between = piece.slice(last, match.index);
      if ((sourceOf(match[0]) === CYRILLIC) !== toCyrillic) crossed.add(converted.length + between.length);
      converted += between + convertWord(match, numerals.has(index));
      last = match.index + match[0].length;
    }
    converted += piece.slice(last);
    return dates(converted, target, crossed);
  };
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
  // Before NFKD, which makes U+2011 U+2010 HYPHEN, not ASCII.
  text = text.replaceAll("\u{2011}", "-");
  text = text.replace(NO_MARKS_RE, "").normalize("NFKD");
  return text.replace(NOT_ASCII_RE, "");
}
