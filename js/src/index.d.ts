// Type declarations for akademtranslit, the JavaScript port of the Python
// library. Written by hand; test/api.test.js checks that every export is here.
//
// Errors: where the Python library raises ValueError, the port throws
// RangeError; where it raises TypeError, the port throws TypeError. The port
// also throws TypeError for text that is not a string, for an unknown option
// and for options that are not an object (Python: an unexpected keyword
// argument).
//
// Indices (validate, homoglyphSpans, migrationReport().check) count code
// points, as Python's do -- not UTF-16 units: "\u{1F600}a" has "a" at 1.

/** One of the three orthographies. */
export type Script = "cyrillic" | "latin_1995" | "latin_2026";

/**
 * An orthography, or a BCP 47 language tag for one: "uz-Cyrl",
 * "uz-Latn-1995", "uz-Latn-2026" (also "uz-1995", "uz-2026"; any case, "-" or
 * "_"). "uz" and "uz-Latn" are read as latin_1995 in 0.x (see scriptForTag).
 */
export type Orthography = Script | (string & {});

/** A source orthography: "auto" reads each word in the orthography it shows. */
export type Source = Orthography | "auto";

/** The kinds of protected span, in order of precedence. */
export type SpanKind = "url" | "email" | "doi" | "markup" | "placeholder" | "path" | "term" | "token";

/** The kind scriptSpans() gives a word. */
export type WordKind = "cyrillic" | "latin_1995" | "latin_2026" | "latin" | "mixed";

/** The codes of validate(), in the order of the documentation. */
export type ValidateCode =
  | "invisible"
  | "decomposed"
  | "mixed-script"
  | "cyrillic-word"
  | "latin-1995-word"
  | "latin-2026-word"
  | "look-alike"
  | "letter-form"
  | "digraph"
  | "wrong-mark"
  | "mark-form";

/** The codes of migrationReport().check: validate's and two more. */
export type MigrationCode = ValidateCode | "round-trip" | "separator";

/** One finding: text.slice by code points [start, end) is what was found. */
export type Finding<Code extends string = ValidateCode> = [
  start: number,
  end: number,
  code: Code,
  suggestion: string | null,
];

/** The options of new Protect(): Python's keyword arguments. */
export interface ProtectOptions {
  urls?: boolean;
  emails?: boolean;
  dois?: boolean;
  placeholders?: boolean;
  markup?: boolean;
  paths?: boolean;
  tokens?: boolean;
  /** Names to keep as they are, matched exactly and as whole words. Not one string. */
  terms?: Iterable<string>;
}

/**
 * Which spans segments() and the conversion functions protect. Every kind is
 * on by default. Immutable (frozen).
 * @throws {TypeError} terms is a string, or holds something else than strings.
 * @throws {RangeError} a term is empty.
 */
export declare class Protect {
  constructor(options?: ProtectOptions);
  readonly urls: boolean;
  readonly emails: boolean;
  readonly dois: boolean;
  readonly placeholders: boolean;
  readonly markup: boolean;
  readonly paths: boolean;
  readonly tokens: boolean;
  readonly terms: readonly string[];
  /** True if other is a Protect with the same settings (Python's ==). */
  equals(other: unknown): boolean;
  toString(): string;
  /** Protects nothing. */
  static readonly NONE: Protect;
}

/** The protect argument: true (every kind, the default), false (none) or a Protect. */
export type ProtectArgument = boolean | Protect;

/** The options of the functions that take Python's keyword-only protect. */
export interface ProtectOption {
  protect?: ProtectArgument;
}

/** The result of migrationReport(): Python's dict, with its keys in its order. */
export interface MigrationReport {
  words: number;
  changed: number;
  protected: number;
  round_trip: boolean;
  rules_version: string;
  check: Finding<MigrationCode>[];
  result: string;
}

/** The library version, as the Python library's __version__. */
export declare const VERSION: string;
/** Which rules convert(), toLatin() and toCyrillic() follow. */
export declare const RULES_VERSION: string;

export declare const CYRILLIC: "cyrillic";
export declare const LATIN_1995: "latin_1995";
export declare const LATIN_2026: "latin_2026";
export declare const SCRIPTS: readonly ["cyrillic", "latin_1995", "latin_2026"];

/** U+02BB MODIFIER LETTER TURNED COMMA: part of oʻ and gʻ. */
export declare const TURNED_COMMA: "ʻ";
/** U+02BC MODIFIER LETTER APOSTROPHE: the tutuq belgisi. */
export declare const TUTUQ: "ʼ";

/** The four letters the 2026 reform changes: [1995, 2026] pairs. */
export declare const REFORM_PAIRS: readonly (readonly [string, string])[];
/** The 35 letters of the Uzbek Cyrillic alphabet, in order. */
export declare const CYRILLIC_ALPHABET: readonly string[];
/** The 1995 alphabet in sorting order: 24 letters, then oʻ gʻ sh ch. */
export declare const LATIN_1995_ALPHABET: readonly string[];
/** The 28 letters of the 2026 alphabet, in the order of Law No. O'RQ-1184. */
export declare const LATIN_2026_ALPHABET: readonly string[];

/**
 * Convert text from one orthography to another.
 * @throws {RangeError} an unknown source or target, or a bad protect.
 */
export declare function convert(
  text: string,
  source?: Source,
  target?: Orthography,
  options?: ProtectOption,
): string;

/**
 * Convert text to Latin, in variant (default latin_2026, or a tag for a Latin orthography).
 * @throws {RangeError} variant is not a Latin orthography.
 */
export declare function toLatin(text: string, variant?: Orthography, options?: ProtectOption): string;

/** Convert text to Cyrillic from either Latin orthography. */
export declare function toCyrillic(text: string, options?: ProtectOption): string;

/** Write text in ASCII, for names and logins (a project scheme, not a passport standard). */
export declare function toAscii(text: string): string;

/** The cross-script search key: lowercase Latin alphanumerics, single-spaced. Never shown. */
export declare function normalize(text: string): string;

/**
 * Rewrite the apostrophe marks in Latin words to one form.
 * @throws {RangeError} an unknown style.
 */
export declare function normalizeApostrophes(
  text: string,
  style?: "unicode" | "ascii",
  options?: { stripInvisible?: boolean; stripStress?: boolean },
): string;

/** Which orthography the text is written in (read in NFC). */
export declare function detectScript(text: string): Script;

/** "latin", "cyrillic" or "mixed": which letters the text has. */
export declare function scriptClass(text: string): "latin" | "cyrillic" | "mixed";

/** The words of text and the text between them, with the kind of each word. */
export declare function scriptSpans(text: string): [piece: string, kind: WordKind | null][];

/**
 * The protected spans of text and the text between them.
 * @throws {RangeError} protect is not true, false or a Protect.
 */
export declare function segments(text: string, protect?: ProtectArgument): [piece: string, kind: SpanKind | null][];

/** True if text has a character in U+0400-U+052F. */
export declare function isCyrillic(text: string): boolean;

/** "uz", "ru", "mixed" or "unknown": a routing heuristic for Cyrillic text. */
export declare function cyrillicLanguage(text: string): "uz" | "ru" | "mixed" | "unknown";

/** Fold Cyrillic characters to Latin (lossy); everything else passes through. */
export declare function foldCyrillic(text: string): string;

/** Write each word with both Latin and Cyrillic letters in one of them. */
export declare function foldHomoglyphs(text: string): string;

/** Where foldHomoglyphs() changes text: [start, stop, word], in code points. */
export declare function homoglyphSpans(text: string): [start: number, stop: number, word: string][];

/**
 * The key that sorts text in the alphabetical order of orthography (required):
 * [weights, text]. Compare the weights element by element, then the text.
 * @throws {RangeError} an unknown orthography.
 * @throws {TypeError} orthography is missing.
 */
export declare function sortKey(text: string, orthography: Orthography): [weights: number[], text: string];

/**
 * What in text does not belong to orthography, in order of [start, end, code].
 * @throws {RangeError} an unknown orthography, "auto" included.
 * @throws {TypeError} orthography is missing.
 */
export declare function validate(text: string, orthography: Orthography, options?: ProtectOption): Finding[];

/** What converting a latin_1995 text to latin_2026 does to it. */
export declare function migrationReport(text: string, options?: ProtectOption): MigrationReport;

/**
 * The orthography a language tag names. Python's FutureWarning for "uz" and
 * "uz-Latn" is returned as warning: "FutureWarning" (null otherwise); nothing
 * is written to the console.
 * @throws {RangeError} the tag breaks a rule.
 * @throws {TypeError} tag is not a string.
 */
export declare function scriptForTag(tag: string): { script: Script; warning: "FutureWarning" | null };

/**
 * The language tag for an orthography.
 * @throws {RangeError} anything but one of SCRIPTS.
 */
export declare function tagForScript(script: Script): "uz-Cyrl" | "uz-Latn-1995" | "uz-Latn-2026";
