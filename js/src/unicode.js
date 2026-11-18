// Python's view of characters, for a port that must match it byte for byte.
//
// The Python library runs on CPython's `str` and `re`. JavaScript differs in
// ways that change output, so every module of the port takes its character
// classes and string helpers from here instead of using the JavaScript ones
// directly. Each equivalence below was measured over every code point with
// Python 3.12 (unicodedata 15.0.0); test/fixtures/unicode-15.0.json holds the
// measurement and test/traps.test.js checks this file against it.
//
// Trap: Python `re` and JavaScript RegExp do not mean the same thing by
// \w, \d, \s and \b. In Python, for str patterns:
//   \w         == [\p{L}\p{N}_]        (str.isalnum() or "_")
//   \d         == \p{Nd}               (str.isdecimal())
//   \s         == the 29 code points of str.isspace() (SPACE below)
//   [^\W\d_]   == [\p{L}\p{Nl}\p{No}]  (a letter, or a number that is not a digit)
// JavaScript's \w and \d are ASCII only even with the u flag, and its \s adds
// U+FEFF and leaves out U+0085 and U+001C-U+001F. None of them is used in src/.
//
// Trap: re.IGNORECASE. Python matches the ASCII letters i, k and s
// case-insensitively also against U+0130, U+0131 (i), U+212A KELVIN SIGN (k)
// and U+017F LONG S (s). JavaScript's i flag (with u) takes U+212A and U+017F
// but not U+0130 or U+0131. So the port never uses the i flag: ci() spells
// each letter out as Python matches it.
//
// Trap: indices. A Python str is indexed by code point; a JavaScript string by
// UTF-16 code unit, so a character outside the BMP (U+10000 and up) counts 1
// in Python and 2 here. The port computes in UTF-16 internally and converts
// the indices it returns with codePointIndexer(); the per-word rules iterate
// code points wherever Python looks at a neighbouring character.
//
// Trap: case. str.lower()/str.upper() and toLowerCase()/toUpperCase() apply
// the same full mappings (ß -> SS, İ -> i + U+0307, final sigma); the
// locale-sensitive toLocale* functions are never used. Python's str.isupper()
// on one character is the Unicode property Uppercase (Lu and Other_Uppercase:
// Ⅰ, Ⓐ), not the category Lu. Titlecase letters (ǅ) have case and are not
// upper.
//
// Unicode versions differ (Python 3.12: 15.0; Node 24: 17.0). The two can only
// disagree on code points that Unicode 15.0 leaves unassigned; nothing here
// pins either version.

// --- character classes, as RegExp source (always used with the u flag) ---------

/** The body of a class matching Python's whitespace (str.isspace(), re \s). */
export const SPACE_BODY =
  "\\t\\n\\v\\f\\r\\x1C-\\x20\\x85\\xA0\\u1680\\u2000-\\u200A\\u2028\\u2029\\u202F\\u205F\\u3000";
/** Python \s and \S. */
export const S = `[${SPACE_BODY}]`;
export const NOT_S = `[^${SPACE_BODY}]`;
/** The body of a class matching Python \w. */
export const W_BODY = "\\p{L}\\p{N}_";
/** Python [^\W\d_]: a letter, or a number that is not a decimal digit. */
export const LETTER = "[\\p{L}\\p{Nl}\\p{No}]";

const SPACE_RE = new RegExp(`^${S}$`, "u");
const ALPHA_RE = /^\p{L}$/u;
const UPPER_RE = /^\p{Uppercase}$/u;
const MARK_RE = /^\p{M}$/u;

/** str.isspace() for one character. */
export function isSpace(ch) {
  return SPACE_RE.test(ch);
}

/** str.isalpha() for one character: the categories Lu, Ll, Lt, Lm, Lo. */
export function isAlpha(ch) {
  return ALPHA_RE.test(ch);
}

/** str.isupper() for one character: the Unicode property Uppercase. */
export function isUpper(ch) {
  return UPPER_RE.test(ch);
}

/** unicodedata.category(ch).startswith("M") for one character. */
export function isMark(ch) {
  return MARK_RE.test(ch);
}

/** ch.lower() != ch.upper(): whether a character has case. */
export function hasCase(ch) {
  return ch.toLowerCase() !== ch.toUpperCase();
}

const SPACE_UNITS = new Set(
  [0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x1c, 0x1d, 0x1e, 0x1f, 0x20, 0x85, 0xa0, 0x1680,
    0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200a,
    0x2028, 0x2029, 0x202f, 0x205f, 0x3000],
);

/** str.strip() with no argument: Python whitespace at both ends removed. */
export function strip(text) {
  let start = 0;
  let end = text.length;
  while (start < end && SPACE_UNITS.has(text.charCodeAt(start))) start++;
  while (end > start && SPACE_UNITS.has(text.charCodeAt(end - 1))) end--;
  return start === 0 && end === text.length ? text : text.slice(start, end);
}

// --- code points ------------------------------------------------------------------

/** The number of code points in ``text``: Python's len(). */
export function cpLength(text) {
  let n = text.length;
  for (let i = 0; i < text.length - 1; i++) {
    const c = text.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      const d = text.charCodeAt(i + 1);
      if (d >= 0xdc00 && d <= 0xdfff) {
        n--;
        i++;
      }
    }
  }
  return n;
}

const SURROGATE_RE = /[\uD800-\uDFFF]/;

/**
 * A function from a UTF-16 offset in ``text`` to the code point offset Python
 * would give: the identity when ``text`` has no surrogates, and otherwise a
 * table built in one pass. Offsets inside a surrogate pair are never asked for.
 */
export function codePointIndexer(text) {
  if (!SURROGATE_RE.test(text)) return (i) => i;
  const table = new Uint32Array(text.length + 1);
  let cp = 0;
  for (let i = 0; i < text.length; i++) {
    table[i] = cp;
    const c = text.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff && i + 1 < text.length) {
      const d = text.charCodeAt(i + 1);
      if (d >= 0xdc00 && d <= 0xdfff) {
        i++;
        table[i] = cp;
      }
    }
    cp++;
  }
  table[text.length] = cp;
  return (i) => table[i];
}

/** Python's comparison of two str: by code point, not by UTF-16 unit. */
export function compareCodePoints(a, b) {
  const x = Array.from(a);
  const y = Array.from(b);
  const n = Math.min(x.length, y.length);
  for (let i = 0; i < n; i++) {
    const d = x[i].codePointAt(0) - y[i].codePointAt(0);
    if (d !== 0) return d;
  }
  return x.length - y.length;
}

// --- str methods with positions ----------------------------------------------------

/** str.find(sub, start, end): the first ``sub`` wholly inside [start, end), or -1. */
export function pyFind(text, sub, start, end) {
  const i = text.indexOf(sub, start);
  return i === -1 || i + sub.length > end ? -1 : i;
}

/** str.count(ch, start, end) for one UTF-16 unit ``ch``. */
export function pyCount(text, ch, start, end) {
  let n = 0;
  for (let i = start; i < end; i++) if (text[i] === ch) n++;
  return n;
}

// --- regular expressions -------------------------------------------------------------

/** re.escape() for a pattern used with the u flag. */
export function escapeRegExp(text) {
  return text.replace(/[\\^$.*+?()[\]{}|/]/g, "\\$&");
}

// What Python's re.IGNORECASE adds to an ASCII letter, measured over every
// code point: re.fullmatch(letter, ch, re.I) for ch other than the letter in
// either case.
// By code point, since they look like ASCII letters.
const IGNORECASE_EXTRA = {
  i: String.fromCodePoint(0x0130, 0x0131), // LATIN CAPITAL LETTER I WITH DOT ABOVE, SMALL LETTER DOTLESS I
  k: String.fromCodePoint(0x212a), // KELVIN SIGN
  s: String.fromCodePoint(0x017f), // LATIN SMALL LETTER LONG S
};
// The same, as text: { i: "İı", k: "K", s: "ſ" };

/** A pattern that matches ``literal`` as Python does with re.IGNORECASE. */
export function ci(literal) {
  let out = "";
  for (const ch of literal) {
    const lower = ch.toLowerCase();
    if (lower >= "a" && lower <= "z" && lower.length === 1) {
      out += `[${lower}${lower.toUpperCase()}${IGNORECASE_EXTRA[lower] ?? ""}]`;
    } else {
      out += escapeRegExp(ch);
    }
  }
  return out;
}

/** The body of [A-Za-z0-9] under re.IGNORECASE. */
export const ASCII_ALNUM_CI_BODY = "A-Za-z0-9\\u0130\\u0131\\u017F\\u212A";

// --- arguments ----------------------------------------------------------------------

/** The name of a value's type, for messages. */
export function typeName(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "Array";
  return typeof value;
}

/** Python's repr() of a string, for messages. */
export function repr(value) {
  if (typeof value !== "string") return String(value);
  if (value.includes("'") && !value.includes('"')) return `"${value}"`;
  return `'${value.replace(/\\/g, "\\\\").replace(/'/g, "\\'")}'`;
}

/** TypeError unless ``value`` is a string: the text argument of every function. */
export function requireString(value, name, where) {
  if (typeof value !== "string") {
    throw new TypeError(`${where}(): ${name} must be a string, not ${typeName(value)}`);
  }
  return value;
}

/** TypeError if a required positional argument is missing, as in Python. */
export function requireArgument(value, name, where) {
  if (value === undefined) {
    throw new TypeError(`${where}() missing 1 required positional argument: '${name}'`);
  }
  return value;
}

/**
 * The options object that holds Python's keyword-only arguments. Undefined is
 * no options; anything but a plain object, and an unknown key, raise
 * TypeError, as Python does for an unexpected keyword argument.
 */
export function readOptions(options, allowed, where) {
  if (options === undefined) return {};
  if (options === null || typeof options !== "object" || Array.isArray(options)) {
    throw new TypeError(`${where}(): options must be an object, not ${typeName(options)}`);
  }
  for (const key of Object.keys(options)) {
    if (!allowed.includes(key)) {
      throw new TypeError(`${where}() got an unexpected option '${key}'`);
    }
  }
  return options;
}
