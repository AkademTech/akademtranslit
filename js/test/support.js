// Shared by the tests: the golden fields, Python's error names and the
// fixtures made by tools/make-fixtures.py. Not a test file itself.

import { createHash } from "node:crypto";
import { readFileSync, readdirSync } from "node:fs";

import * as lib from "../src/index.js";

export const GOLDEN_DIR = new URL("../../golden/", import.meta.url);
export const FIXTURES_DIR = new URL("./fixtures/", import.meta.url);

export const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");

export const readGolden = (name) => readFileSync(new URL(name, GOLDEN_DIR));

/** A fixture, parsed; ``pattern`` picks the one file whose name matches it. */
export function readFixture(pattern) {
  const names = readdirSync(FIXTURES_DIR).filter((name) => pattern.test(name));
  if (names.length !== 1) throw new Error(`expected one fixture matching ${pattern}, found ${names.length}`);
  return JSON.parse(readFileSync(new URL(names[0], FIXTURES_DIR), "utf8"));
}

export const ORTHOGRAPHIES = ["cyrillic", "latin_1995", "latin_2026"];

/** The golden fields: name -> function of the input text, as tools/golden.py has them. */
export const FIELDS = {
  detect_script: (text) => lib.detectScript(text),
  normalize: (text) => lib.normalize(text),
  to_cyrillic: (text) => lib.toCyrillic(text),
  to_latin_1995: (text) => lib.toLatin(text, "latin_1995"),
  to_latin_2026: (text) => lib.toLatin(text, "latin_2026"),
  ...Object.fromEntries(ORTHOGRAPHIES.map((o) => [`sort_key_${o}`, (text) => lib.sortKey(text, o)[0]])),
  ...Object.fromEntries(
    ["unicode", "ascii"].map((s) => [`normalize_apostrophes_${s}`, (text) => lib.normalizeApostrophes(text, s)]),
  ),
  script_class: (text) => lib.scriptClass(text),
  cyrillic_language: (text) => lib.cyrillicLanguage(text),
  ...Object.fromEntries(
    ORTHOGRAPHIES.flatMap((s) =>
      ORTHOGRAPHIES.map((t) => [`convert_from_${s}_to_${t}`, (text) => lib.convert(text, s, t)]),
    ),
  ),
  fold_cyrillic: (text) => lib.foldCyrillic(text),
  is_cyrillic: (text) => lib.isCyrillic(text),
  segments: (text) => lib.segments(text),
  to_ascii: (text) => lib.toAscii(text),
  script_spans: (text) => lib.scriptSpans(text),
  fold_homoglyphs: (text) => lib.foldHomoglyphs(text),
  ...Object.fromEntries(ORTHOGRAPHIES.map((o) => [`validate_${o}`, (text) => lib.validate(text, o)])),
};

/**
 * The calls tools/make-fixtures.py makes beyond the golden fields (its
 * extra_fields() and trap_results()), for ``terms``, the terms it used.
 */
export function extraFields(terms) {
  const withTerms = new lib.Protect({ terms });
  return {
    ...Object.fromEntries(
      ORTHOGRAPHIES.map((t) => [`convert_auto_to_${t}_protect_false`, (text) => lib.convert(text, "auto", t, { protect: false })]),
    ),
    convert_terms_to_cyrillic: (text) => lib.convert(text, "auto", "cyrillic", { protect: withTerms }),
    convert_tags_latin_1995_to_cyrillic: (text) => lib.convert(text, "uz-Latn-1995", "uz-Cyrl"),
    to_latin_tag_latin_1995: (text) => lib.toLatin(text, "uz-Latn-1995"),
    to_cyrillic_protect_false: (text) => lib.toCyrillic(text, { protect: false }),
    segments_protect_false: (text) => lib.segments(text, false),
    segments_terms: (text) => lib.segments(text, withTerms),
    segments_no_tokens_no_paths: (text) => lib.segments(text, new lib.Protect({ tokens: false, paths: false })),
    segments_placeholders_only: (text) =>
      lib.segments(
        text,
        new lib.Protect({ urls: false, emails: false, dois: false, markup: false, paths: false, tokens: false }),
      ),
    ...Object.fromEntries(
      ORTHOGRAPHIES.map((o) => [`validate_${o}_protect_false`, (text) => lib.validate(text, o, { protect: false })]),
    ),
    validate_tag_cyrillic: (text) => lib.validate(text, "UZ_cyrl"),
    sort_key_tag_latin_2026: (text) => lib.sortKey(text, "uz-2026")[0],
    sort_key_text_latin_1995: (text) => lib.sortKey(text, "latin_1995")[1],
    normalize_apostrophes_unicode_strip_both: (text) =>
      lib.normalizeApostrophes(text, "unicode", { stripInvisible: true, stripStress: true }),
    normalize_apostrophes_ascii_strip_invisible: (text) =>
      lib.normalizeApostrophes(text, "ascii", { stripInvisible: true }),
    normalize_apostrophes_unicode_strip_stress: (text) => lib.normalizeApostrophes(text, "unicode", { stripStress: true }),
    homoglyph_spans: (text) => lib.homoglyphSpans(text),
    migration_report: (text) => lib.migrationReport(text),
    migration_report_protect_false: (text) => lib.migrationReport(text, { protect: false }),
    // Python's str.lower()/str.upper() on the whole text.
    str_lower: (text) => text.toLowerCase(),
    str_upper: (text) => text.toUpperCase(),
  };
}

/** Python's name for a JavaScript error: ValueError is RangeError here. */
export function pythonError(error) {
  if (error instanceof RangeError) return "ValueError";
  if (error instanceof TypeError) return "TypeError";
  return error?.name ?? String(error);
}

/** The result of ``call`` as the fixtures record it: the value, or {"error": name}. */
export function outcome(call) {
  try {
    return call();
  } catch (error) {
    return { error: pythonError(error) };
  }
}

/** Equal as JSON values: arrays for tuples, null for None, order counts. */
export const sameJson = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/** Compare ``fields`` on ``cases`` with ``expected(case, field)``; the cases that differ. */
export function differences(cases, fields, expected) {
  const misses = [];
  for (const item of cases) {
    for (const [field, func] of Object.entries(fields)) {
      const want = expected(item, field);
      if (want === undefined) continue;
      const got = outcome(() => func(item.text));
      if (!sameJson(got, want)) misses.push({ id: item.id, field, text: item.text, want, got });
    }
  }
  return misses;
}
