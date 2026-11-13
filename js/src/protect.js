// Protected spans: the parts of a text that conversion leaves alone. A port of
// src/akademtranslit/protect.py; its docstring describes each kind of span and
// how overlapping spans are resolved.
//
// Python's re has call forms JavaScript lacks, and the port emulates them:
// - pattern.search(text, pos, endpos): the string ends at endpos for the
//   pattern (\S+ stops there, lookaheads see the end there) while lookbehinds
//   still see the text before pos. The nested scan of an ICU message text has
//   endpos < len(text). Scanner.view(end) is the text cut at end; searching it
//   from lastIndex = pos does both.
// - pattern.match(text, pos, endpos): anchored at pos -- a sticky (y) RegExp.
//   The ICU patterns here all stop at the } at endpos, so the full text is used.
// - m.start("tail"): the tail group always ends the match, so it starts at the
//   end of the match minus its length.
// - fullmatch: ^...$.
// - re.IGNORECASE: spelt out with ci() (see unicode.js).

import { APOSTROPHE_VARIANTS } from "./tables.js";
import {
  ASCII_ALNUM_CI_BODY,
  NOT_S,
  S,
  SPACE_BODY,
  W_BODY,
  ci,
  compareCodePoints,
  cpLength,
  escapeRegExp,
  pyCount,
  pyFind,
  readOptions,
  repr,
  requireString,
  typeName,
} from "./unicode.js";

export const URL = "url";
export const EMAIL = "email";
export const DOI = "doi";
export const MARKUP = "markup";
export const PLACEHOLDER = "placeholder";
export const PATH = "path";
export const TERM = "term";
export const TOKEN = "token";

/** The kinds of span, in order of precedence. */
export const KINDS = Object.freeze([URL, EMAIL, DOI, MARKUP, PLACEHOLDER, PATH, TERM, TOKEN]);

const RANK = new Map(KINDS.map((kind, rank) => [kind, rank]));

// --- Protect -------------------------------------------------------------------

const FLAGS = ["urls", "emails", "dois", "placeholders", "markup", "paths", "tokens"];

/**
 * Which spans segments() and the conversion functions protect. Every kind is
 * on by default; pass false to turn one off. ``terms`` is a list of strings
 * to keep as they are, matched exactly and only as whole words.
 * Protect.NONE protects nothing. Immutable; compare with equals().
 */
export class Protect {
  constructor(options = undefined) {
    const given = readOptions(options, [...FLAGS, "terms"], "Protect");
    let terms = given.terms === undefined ? [] : given.terms;
    if (typeof terms === "string") throw new TypeError("terms takes a sequence of strings, not one str");
    if (terms === null || typeof terms !== "object" || typeof terms[Symbol.iterator] !== "function") {
      throw new TypeError(`terms takes a sequence of strings, not ${typeName(terms)}`);
    }
    terms = Array.from(terms);
    for (const term of terms) {
      if (typeof term !== "string") throw new TypeError(`a term must be a str, not ${typeName(term)}`);
      if (!term) throw new RangeError("a term must not be empty");
    }
    for (const name of FLAGS) this[name] = given[name] === undefined ? true : Boolean(given[name]);
    this.terms = Object.freeze(terms);
    Object.defineProperty(this, "_termsRe", { value: termsPattern(terms) });
    Object.freeze(this);
  }

  /** True if ``other`` is a Protect with the same settings. */
  equals(other) {
    if (!(other instanceof Protect)) return false;
    return (
      FLAGS.every((name) => this[name] === other[name]) &&
      this.terms.length === other.terms.length &&
      this.terms.every((term, i) => term === other.terms[i])
    );
  }

  toString() {
    const parts = FLAGS.filter((name) => !this[name]).map((name) => `${name}: false`);
    if (this.terms.length) parts.push(`terms: ${JSON.stringify(this.terms)}`);
    return parts.length ? `Protect({ ${parts.join(", ")} })` : "Protect()";
  }
}

/** The Protect for a ``protect`` argument: true, false or a Protect. */
export function settingsFor(protect) {
  if (protect === true) return DEFAULT;
  if (protect === false) return Protect.NONE;
  if (protect instanceof Protect) return protect;
  throw new RangeError(`protect must be true, false or a Protect, not ${repr(protect)}`);
}

// --- segments ------------------------------------------------------------------

/**
 * Split ``text`` into protected spans and the text between them: a list of
 * [piece, kind] pairs, kind null for text that is converted. Joined, the
 * pieces give ``text`` back. ``protect`` is true, false or a Protect.
 */
export function segments(text, protect = true) {
  requireString(text, "text", "segments");
  const settings = settingsFor(protect);
  if (!text) return [];
  return spans(text, settings).map(([start, stop, kind]) => [text.slice(start, stop), kind]);
}

/** [start, stop, kind] for each piece of ``text`` (UTF-16 offsets), covering all of it. */
export function spans(text, settings) {
  const finders = findersFor(settings);
  if (!finders.length) return [[0, text.length, null]];
  const pieces = [];
  new Scanner(text, finders).scan(0, text.length, pieces);
  const merged = [];
  for (const [start, stop, kind] of pieces) {
    if (start === stop) continue;
    const last = merged[merged.length - 1];
    if (last !== undefined && last[2] === kind) {
      last[1] = stop;
    } else {
      merged.push([start, stop, kind]);
    }
  }
  return merged;
}

const NOTHING = [-1, -1, null, null]; // a finder that has nothing more to find
const MAX_DEPTH = 32;

class Scanner {
  constructor(text, finders) {
    this.text = text;
    this.finders = finders;
    this.closingMap = null;
    this.argumentsCache = new Map();
    this.views = new Map();
  }

  /** The text as Python's re sees it with endpos ``end``. */
  view(end) {
    if (end === this.text.length) return this.text;
    let cut = this.views.get(end);
    if (cut === undefined) {
      cut = this.text.slice(0, end);
      this.views.set(end, cut);
    }
    return cut;
  }

  /** Append the pieces of text[start:end] to ``out``. */
  scan(start, end, out) {
    const found = new Array(this.finders.length).fill(null);
    let pos = start;
    while (pos < end) {
      let best = null;
      for (let i = 0; i < this.finders.length; i++) {
        let match = found[i];
        if (match === NOTHING) continue;
        if (match === null || match[0] < pos) {
          match = this.finders[i](this, pos, end) ?? NOTHING;
          found[i] = match;
          if (match === NOTHING) continue;
        }
        if (best === null || better(match, best)) best = match;
      }
      if (best === null) break;
      const [begin, stop, kind, inner] = best;
      if (begin > pos) out.push([pos, begin, null]);
      if (inner === null) {
        out.push([begin, stop, kind]);
      } else {
        for (const [a, b, pieceKind] of inner) {
          if (pieceKind === null) {
            this.scan(a, b, out);
          } else {
            out.push([a, b, pieceKind]);
          }
        }
      }
      pos = stop;
    }
    if (pos < end) out.push([pos, end, null]);
  }

  /** Index of the } that closes the { at ``i``, or undefined. */
  closing(i) {
    if (this.closingMap === null) {
      const closing = new Map();
      const stack = [];
      const text = this.text;
      for (let k = 0; k < text.length; k++) {
        const c = text[k];
        if (c === "{") {
          stack.push(k);
        } else if (c === "}" && stack.length) {
          closing.set(stack.pop(), k);
        }
      }
      this.closingMap = closing;
    }
    return this.closingMap.get(i);
  }

  /** The ICU argument whose { is at ``i``: [stop, pieces] or null. */
  argument(i, end, plural, depth) {
    const key = `${i},${end},${plural}`;
    if (!this.argumentsCache.has(key)) {
      if (depth > MAX_DEPTH) return null;
      this.argumentsCache.set(key, this.icuArgument(i, end, plural, depth));
    }
    return this.argumentsCache.get(key);
  }

  icuArgument(i, end, plural, depth) {
    const text = this.text;
    const close = this.closing(i);
    if (close === undefined || close >= end) return null;
    let m = matchAt(ICU_NAME_RE, text, i + 1, close);
    if (m === null) return null;
    let j = m.end;
    if (j === close) return [close + 1, null];
    if (text[j] !== ",") return null;
    m = matchAt(ICU_TYPE_RE, text, j + 1, close);
    if (m === null) return null;
    const argType = m.groups[1].toLowerCase();
    j = m.end;
    if (ICU_SIMPLE_TYPES.has(argType)) {
      if (j === close || text[j] === ",") return [close + 1, null];
      return null;
    }
    if (!ICU_PLURAL_TYPES.has(argType) && argType !== ICU_SELECT) return null;
    if (j === close || text[j] !== ",") return null;
    j += 1;
    if (ICU_PLURAL_TYPES.has(argType)) {
      plural = true;
      m = matchAt(ICU_OFFSET_RE, text, j, close);
      if (m !== null) j = m.end;
    }
    const pieces = [];
    let syntax = i;
    for (;;) {
      m = matchAt(ICU_SELECTOR_RE, text, j, close);
      if (m === null || m.end === close || text[m.end] !== "{") break;
      j = m.end;
      pieces.push([syntax, j + 1, PLACEHOLDER]);
      const message = this.message(j + 1, close, plural, depth);
      if (message === null) return null;
      const [messageClose, messagePieces] = message;
      pieces.push(...messagePieces);
      syntax = messageClose;
      j = messageClose + 1;
    }
    const space = matchAt(SPACE_RE, text, j, close);
    if (!pieces.length || space === null || space.end !== close) return null;
    pieces.push([syntax, close + 1, PLACEHOLDER]);
    return [close + 1, pieces];
  }

  /** The message text from ``i`` to its }: [close, pieces] or null. */
  message(i, end, plural, depth) {
    const text = this.text;
    const pieces = [];
    let start = i;
    let k = i;
    for (;;) {
      MESSAGE_SYNTAX_RE.lastIndex = k;
      const m = MESSAGE_SYNTAX_RE.exec(text);
      if (m === null || m.index >= end) return null;
      k = m.index;
      if (text[k] === "}") {
        pieces.push([start, k, null]);
        return [k, pieces];
      }
      if (text[k] === "#") {
        if (plural) {
          pieces.push([start, k, null]);
          pieces.push([k, k + 1, PLACEHOLDER]);
          start = k + 1;
        }
        k += 1;
        continue;
      }
      const nested = this.argument(k, end, plural, depth + 1);
      if (nested === null) return null;
      const [stop, nestedPieces] = nested;
      pieces.push([start, k, null]);
      pieces.push(...(nestedPieces !== null ? nestedPieces : [[k, stop, PLACEHOLDER]]));
      start = k = stop;
    }
  }
}

/** Whether span ``a`` wins over span ``b``: first, then longest, then by kind. */
function better(a, b) {
  if (a[0] !== b[0]) return a[0] < b[0];
  if (a[1] !== b[1]) return a[1] > b[1];
  return RANK.get(a[2]) < RANK.get(b[2]);
}

/** A sticky match of ``regex`` at ``pos``: { end, groups } or null. */
function matchAt(regex, text, pos, endpos) {
  regex.lastIndex = pos;
  const m = regex.exec(text);
  if (m === null) return null;
  const end = m.index + m[0].length;
  return end > endpos ? null : { end, groups: m };
}

/** The first match of global ``regex`` in text[pos:end], Python's search(text, pos, end). */
function search(regex, scanner, pos, end) {
  regex.lastIndex = pos;
  return regex.exec(scanner.view(end));
}

// --- the finders -----------------------------------------------------------------
//
// Each takes the scanner, a start and an end, and returns the first span it
// finds in text[start:end] as [start, stop, kind, inner], or null.

// A letter or digit, not counting the three apostrophe marks that Unicode
// calls letters (U+02B9, U+02BB, U+02BC): Python's [^\W_ʹʻʼ]. As a guard on
// either side of a word: not after / not before such a character.
const LETTER_MARKS = "\\u02B9\\u02BB\\u02BC";
const L = `(?:(?![${LETTER_MARKS}])[\\p{L}\\p{N}])`;
const NOT_AFTER_L = `(?:(?<![\\p{L}\\p{N}])|(?<=[${LETTER_MARKS}]))`;
const NOT_BEFORE_L = `(?:(?![\\p{L}\\p{N}])|(?=[${LETTER_MARKS}]))`;
const MARK = "[" + escapeRegExp(APOSTROPHE_VARIANTS.join("")) + "]";
// (?:L|MARK): every mark is a letter or one of the three.
const L_OR_MARK = "[\\p{L}\\p{N}" + escapeRegExp(APOSTROPHE_VARIANTS.join("")) + "]";

// Left out at the end of a URL, a DOI or a path.
const TRAILING = new Set(".,;:!?)»\"'");

/** ``stop`` moved back past trailing punctuation, but not before ``start``. */
function trim(text, start, stop) {
  while (stop > start && TRAILING.has(text[stop - 1])) {
    if (text[stop - 1] === ")" && pyCount(text, "(", start, stop) >= pyCount(text, ")", start, stop)) break;
    stop -= 1;
  }
  return stop;
}

/** A finder for a pattern with a group ``tail`` that ends it; each match is trimmed. */
function trimmed(regex, kind) {
  return (scanner, pos, end) => {
    for (;;) {
      const m = search(regex, scanner, pos, end);
      if (m === null) return null;
      const matchEnd = m.index + m[0].length;
      const tailStart = matchEnd - m.groups.tail.length;
      const stop = trim(scanner.text, tailStart, matchEnd);
      if (stop > tailStart) return [m.index, stop, kind, null];
      // Every pattern here starts with an ASCII character, so +1 is the next
      // code point, as in Python.
      pos = m.index + 1;
    }
  };
}

/** A finder whose first match is the span. */
function plain(regex, kind) {
  return (scanner, pos, end) => {
    const m = search(regex, scanner, pos, end);
    return m === null ? null : [m.index, m.index + m[0].length, kind, null];
  };
}

/** ``finder``, skipped when ``literal``, which every match contains, is absent. */
function needs(literal, finder) {
  return (scanner, pos, end) => (pyFind(scanner.text, literal, pos, end) === -1 ? null : finder(scanner, pos, end));
}

const DOMAIN_LABEL = "[A-Za-z0-9](?:[A-Za-z0-9\\-]{0,61}[A-Za-z0-9])?";
// The same under re.IGNORECASE (the bare domain): İ ı ſ K are letters too.
const DOMAIN_LABEL_CI =
  `[${ASCII_ALNUM_CI_BODY}](?:[${ASCII_ALNUM_CI_BODY}\\-]{0,61}[${ASCII_ALNUM_CI_BODY}])?`;

const SCHEME_URL_RE = new RegExp(
  `(?<![${W_BODY}])(?:(?:${ci("http")}${ci("s")}?|${ci("ftp")}):\\/\\/|${ci("www")}\\.)(?<tail>${NOT_S}+)`,
  "gu",
);

const TLDS = ["uz", "com", "org", "net", "ru", "info", "edu", "gov", "io"];
const BARE_DOMAIN_RE = new RegExp(
  `(?<![${W_BODY}@])(?<tail>${DOMAIN_LABEL_CI}(?:\\.${DOMAIN_LABEL_CI})*\\.(?:${TLDS.map(ci).join("|")})` +
    `(?![${W_BODY}\\-])(?:\\/${NOT_S}*)?)`,
  "gu",
);

const EMAIL_RE = new RegExp(
  `(?:${ci("mailto")}:)?(?<![A-Za-z0-9._%+\\-])[A-Za-z0-9._%+\\-]+@` +
    `${DOMAIN_LABEL}(?:\\.${DOMAIN_LABEL})*\\.[A-Za-z]{2,63}(?![${W_BODY}\\-])`,
  "gu",
);

const DOI_RE = new RegExp(`(?:${ci("doi")}:)?(?<![${W_BODY}.])10\\.[0-9]{4,9}\\/(?<tail>${NOT_S}+)`, "gu");

const TAG_RE = new RegExp(
  "<[A-Za-z\\/!](?:[^<>\"']|\"[^\"<]*\"|'[^'<]*')*>" + // quoted values may hold >
    "|<[A-Za-z\\/!][^<>]*>" + // an unmatched quote: up to the first >
    "|&(?:[A-Za-z][A-Za-z0-9]{1,31}|#[0-9]{1,7}|#[xX][0-9A-Fa-f]{1,6});",
  "gu",
);

const PRINTF_RE = new RegExp(
  `(?<![${W_BODY}%])%(?:[0-9]+\\$)?(?:\\([^()${SPACE_BODY}]+\\))?[\\-+#0]*(?:[0-9]+|\\*)?(?:\\.(?:[0-9]+|\\*))?` +
    "(?:hh|h|ll|l|L|q|j|z|t)?[diouxXeEfFgGcrsaAp]",
  "gu",
);

const PATH_RE = new RegExp(
  `(?<![^${SPACE_BODY}(\\[{"'«“‘„])(?:\\.{1,2}\\/|~\\/|\\/|[A-Za-z]:\\\\)(?<tail>${NOT_S}+)`,
  "gu",
);

const EXTENSIONS = [
  "docx", "doc", "pdf", "txt", "xlsx", "xls", "pptx", "csv", "json", "xml", "html", "md", "py", "js",
  "zip", "png", "jpg", "jpeg", "odt",
];
const FILE_NAME_RE = new RegExp(
  `(?<![${W_BODY}.\\-])[${W_BODY}.\\-]+\\.(?:${EXTENSIONS.map(ci).join("|")})(?![${W_BODY}])`,
  "gu",
);

// A run of letters and digits, joined by apostrophes, with a final apostrophe
// after o or g -- the shape of a word in rules.js. The lookahead skips every
// run without a digit or a lowercase letter before a capital.
const CHUNK_RE = new RegExp(
  NOT_AFTER_L +
    `(?=${L_OR_MARK}*?(?:[0-9]|[a-z][A-Z]))` +
    `${L}+(?:${MARK}${L}+)*(?:(?<=[oOgG])${MARK})?` +
    NOT_BEFORE_L,
  "gu",
);
const ASCII_CHUNK_RE = new RegExp("^[A-Za-z0-9" + escapeRegExp(APOSTROPHE_VARIANTS.join("")) + "]+$", "u");
const UZBEK_RE = new RegExp("[oOgG]" + MARK, "u");
const DIGIT_RE = /[0-9]/u;
const LETTER_RE = /[A-Za-z]/u;
const LOWER_THEN_UPPER_RE = /[a-z][A-Z]/u;
const H_OF_SH_CH_RE = /(?<=[SC])h/gu;
const NUMBER_WITH_SUFFIX_RE = /^[0-9]+[a-z]+$/u;
const UZBEK_ABBREVIATION_RE = /^[A-Z][a-z]{1,4}[A-Z]{2,}[a-z]*$/u;

const MESSAGE_SYNTAX_RE = /[{}#]/gu;
const SPACE_RE = new RegExp(`${S}*`, "uy");
const ICU_NAME_RE = new RegExp(`${S}*[${W_BODY}]+${S}*`, "uy");
const ICU_TYPE_RE = new RegExp(`${S}*([A-Za-z]+)${S}*`, "uy");
const ICU_OFFSET_RE = new RegExp(`${S}*offset${S}*:${S}*-?[0-9]+`, "uy");
const ICU_SELECTOR_RE = new RegExp(`${S}*(?:=-?[0-9]+(?:\\.[0-9]+)?|[${W_BODY}]+)${S}*`, "uy");
const ICU_SIMPLE_TYPES = new Set(["number", "date", "time", "spellout", "ordinal", "duration"]);
const ICU_PLURAL_TYPES = new Set(["plural", "selectordinal"]);
const ICU_SELECT = "select";

function findIcu(scanner, pos, end) {
  const text = scanner.text;
  let i = pyFind(text, "{", pos, end);
  while (i !== -1) {
    const argument = scanner.argument(i, end, false, 0);
    if (argument !== null) {
      const [stop, pieces] = argument;
      return [i, stop, PLACEHOLDER, pieces];
    }
    i = pyFind(text, "{", i + 1, end);
  }
  return null;
}

function findDoubleBraces(scanner, pos, end) {
  const text = scanner.text;
  const i = pyFind(text, "{{", pos, end);
  if (i === -1) return null;
  const close = pyFind(text, "}}", i + 2, end);
  if (close === -1) return null;
  return [i, close + 2, PLACEHOLDER, null];
}

function findComment(scanner, pos, end) {
  const text = scanner.text;
  const i = pyFind(text, "<!--", pos, end);
  if (i === -1) return null;
  const close = pyFind(text, "-->", i + 4, end);
  if (close === -1) return null;
  return [i, close + 3, MARKUP, null];
}

function isToken(chunk) {
  if (!ASCII_CHUNK_RE.test(chunk) || UZBEK_RE.test(chunk)) return false;
  if (NUMBER_WITH_SUFFIX_RE.test(chunk)) return false; // 10ta, 2026yil, 100mg
  if (DIGIT_RE.test(chunk) && LETTER_RE.test(chunk)) return true;
  // Sh and Ch after a capital are one capital letter: MChJ, AQSh.
  chunk = chunk.replace(H_OF_SH_CH_RE, "H");
  if (UZBEK_ABBREVIATION_RE.test(chunk)) return false; // ToshDU, SamDU, ToshPTI, ToshDUga
  return LOWER_THEN_UPPER_RE.test(chunk);
}

function findToken(scanner, pos, end) {
  for (;;) {
    const m = search(CHUNK_RE, scanner, pos, end);
    if (m === null) return null;
    if (isToken(m[0])) return [m.index, m.index + m[0].length, TOKEN, null];
    pos = m.index + m[0].length;
  }
}

function termsPattern(terms) {
  if (!terms.length) return null;
  // Longest first, by code points, then by code point order: Python's
  // sorted(set(terms), key=lambda term: (-len(term), term)).
  const longestFirst = [...new Set(terms)].sort(
    (a, b) => cpLength(b) - cpLength(a) || compareCodePoints(a, b),
  );
  const alternatives = longestFirst.map(escapeRegExp).join("|");
  return new RegExp(`${NOT_AFTER_L}(?:${alternatives})${NOT_BEFORE_L}`, "gu");
}

const URL_FINDERS = [trimmed(SCHEME_URL_RE, URL), trimmed(BARE_DOMAIN_RE, URL)];
const EMAIL_FINDERS = [needs("@", plain(EMAIL_RE, EMAIL))];
const DOI_FINDERS = [needs("10.", trimmed(DOI_RE, DOI))];
const MARKUP_FINDERS = [plain(TAG_RE, MARKUP), findComment];
const PLACEHOLDER_FINDERS = [findIcu, findDoubleBraces, needs("%", plain(PRINTF_RE, PLACEHOLDER))];
const PATH_FINDERS = [trimmed(PATH_RE, PATH), plain(FILE_NAME_RE, PATH)];
const TOKEN_FINDERS = [findToken];

function findersFor(settings) {
  const finders = [];
  if (settings.urls) finders.push(...URL_FINDERS);
  if (settings.emails) finders.push(...EMAIL_FINDERS);
  if (settings.dois) finders.push(...DOI_FINDERS);
  if (settings.markup) finders.push(...MARKUP_FINDERS);
  if (settings.placeholders) finders.push(...PLACEHOLDER_FINDERS);
  if (settings.paths) finders.push(...PATH_FINDERS);
  if (settings._termsRe !== null) finders.push(plain(settings._termsRe, TERM));
  if (settings.tokens) finders.push(...TOKEN_FINDERS);
  return finders;
}

Object.defineProperty(Protect, "NONE", {
  value: new Protect({
    urls: false,
    emails: false,
    dois: false,
    placeholders: false,
    markup: false,
    paths: false,
    tokens: false,
  }),
  enumerable: true,
});

const DEFAULT = new Protect();
