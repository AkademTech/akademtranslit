// AkademTranslit -- Uzbek transliteration across three orthographies.
//
// The JavaScript port of the Python library akademtranslit (src/akademtranslit
// in the same repository). The public API is Python's __all__, in camelCase:
// positional arguments in Python's order, Python's keyword-only arguments in a
// last options object, and the same values ("latin_1995", "cyrillic", BCP 47
// tags). Python's ValueError is RangeError here; TypeError is TypeError.
//
// The port reproduces golden/golden-<version>.json byte for byte;
// test/golden.test.js checks every input and field.
//
// Only relative imports and no Node built-ins: the same files run in Node and
// in a browser (a module Worker).

export const VERSION = "0.3.0";

export {
  CYRILLIC,
  CYRILLIC_ALPHABET,
  LATIN_1995,
  LATIN_1995_ALPHABET,
  LATIN_2026,
  LATIN_2026_ALPHABET,
  REFORM_PAIRS,
  RULES_VERSION,
  SCRIPTS,
  TURNED_COMMA,
  TUTUQ,
} from "./tables.js";
export { Protect, segments } from "./protect.js";
export { convert, detectScript, toAscii, toCyrillic, toLatin } from "./convert.js";
export { cyrillicLanguage, scriptClass } from "./detection.js";
export { foldCyrillic, isCyrillic, normalize } from "./normalize.js";
export { foldHomoglyphs, homoglyphSpans, scriptSpans } from "./scripts.js";
export { migrationReport, validate } from "./checks.js";
export { normalizeApostrophes } from "./apostrophes.js";
export { sortKey } from "./collation.js";
export { scriptForTag, tagForScript } from "./tags.js";
