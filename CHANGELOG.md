# Changelog

## 0.3.0 — unreleased

### Added

- Language tags: every `source`, `target`, `variant` and `orthography`
  argument also takes a BCP 47 tag (`uz-Cyrl`, `uz-Latn-1995`,
  `uz-Latn-2026`, `uz-1995`, `uz-2026`). `script_for_tag()` and
  `tag_for_script()` convert between tags and orthography names. `uz-Latn` and
  `uz` without a variant are read as the 1995 orthography with a
  `FutureWarning`: from 1.0.0 they will mean the 2026 one.
- `RULES_VERSION`: which rules the conversion functions follow.
- Golden vectors, schema 2: `convert` for all nine source and target pairs,
  `fold_cyrillic`, `is_cyrillic`, the tag functions on
  `golden/tag-inputs.json`, and the rules version.
- Protected spans: `convert`, `to_latin` and `to_cyrillic` leave URLs,
  e-mail addresses, DOIs, ICU and printf placeholders, HTML and XML markup,
  file paths, mixed-case and alphanumeric tokens (`pH`, `SpO2`, `iPhone`) and
  caller-given terms unchanged, byte for byte. `Protect` sets which;
  `protect=False` turns it off. `segments()` shows how a text is split.
- `to_ascii()`: ASCII for names and logins (`Çölpon`, `Чўлпон` → `Cholpon`), a
  project scheme with a frozen table.
- `normalize_apostrophes(..., strip_invisible=True)` removes default-ignorable
  characters (zero-width space, soft hyphen, BOM, …);
  `strip_stress=True` removes the combining acute accent used as a stress mark.
- `script_spans()`: the words of a text and the orthography each one shows
  (`cyrillic`, `latin_2026`, `latin_1995`, `latin`, or `mixed` for a word
  with letters from both alphabets). `fold_homoglyphs()` writes such a word in
  the alphabet most of its letters are in, by the look-alike pairs of
  `HOMOGLYPHS` (from the Unicode confusables), and leaves a word alone when a
  letter has no look-alike; `homoglyph_spans()` says which words it changes.
- `ș` (s with comma below, U+0219, the Romanian letter that looks like `ş`) is
  an input form of `ş`, as o with macron and o with caron are of `ö`:
  `detect_script` counts it as a 2026 letter, conversion reads it as `ş`, and
  `normalize` and `sort_key` read it as `ş`.
- `validate(text, orthography)`: what in a text does not belong to the
  orthography it is meant to be in, as `(start, end, code, suggestion)`:
  invisible characters, decomposed letters, words with letters from both
  alphabets, words that show another orthography, look-alike letters, other
  forms of `ö` and `ş`, `sh` and `ch` in 2026 text, and other forms of the
  two marks. Eleven codes; protected spans are not checked.
- `migration_report(text)`: what converting a 1995 text to the 2026
  orthography does to it: the words, how many change, the protected spans,
  whether the result comes back, the rules version, the result, and the
  words to check (`validate` in 1995, `round-trip` and `separator`).
- A command-line tool, `akademtranslit` (and `python -m akademtranslit`):
  `convert`, `validate`, `report` and `normalize`. It reads one file or
  standard input as UTF-8, writes to standard output, keeps line ends, writes
  no file, and exits with 1 when `validate` or `report` finds something and 2
  on an error. The library does not import it.

### Fixed

- `detect_script` did not recognise capital `Ǒ` (U+01D1) as a 2026 letter.
- `ō` and `ǒ` came out unchanged when the input was already in the 2026
  orthography: `to_latin("ōrdak")` gave `ōrdak`; it now gives `ördak`.
- The `convert` docstring said DOIs pass through untouched; in 0.2.0 they
  did not. Now they do, as protected spans (see Added).
- Latin to Cyrillic: `e` after a vowel is `э`: `aeroport` → `аэропорт`,
  `poeziya` → `поэзия` (were `аеропорт`, `поезия`). Before `v` it stays `е`:
  `Aliev` → `Алиев`.
- Cyrillic to Latin: `ь` before `о` is `y`: `бульон` → `bulyon` (was `bulon`).
- `ō` and `ǒ` in a Latin word inside Cyrillic text are read as `ö` when the
  text is converted to the 2026 orthography: `to_latin("Тошкент ōrdak")` gives
  `Toşkent ördak`.
- A letter typed as a base letter and a combining mark was not converted:
  `O` + U+0308 + `zbekiston` gave Cyrillic O (U+041E) + U+0308 + `збекистон`
  in Cyrillic, not `Ўзбекистон`, and `detect_script` did not read it as 2026.
  `convert`, `to_latin` and `to_cyrillic` now compose the text outside
  protected spans (NFC) before converting it, so their output is in NFC
  there; `detect_script` reads the text in NFC. Protected spans still come out
  byte for byte.

### Changed

- Cyrillic is U+0400–U+052F in every function. `is_cyrillic`, and through it
  `detect_script` and `normalize`, used U+0400–U+04FF, so a letter from the
  Cyrillic Supplement block now counts as Cyrillic there too.
- The library imports `warnings`, for the `FutureWarning` above, besides `re`
  and `unicodedata`.
- `normalize` gives a different key for words with `ьо` (`бульон`: `bulon` →
  `bulyon`, now the same key as Latin `bulyon`) and for words with a letter
  from U+0500–U+052F inside (`тош` + U+0501 + `кент`: `tosh kent` →
  `toshkent`). Rebuild search keys made with 0.2.0 for such words.
- Case is kept per letter unit, not re-applied to the whole word: `MChJ` →
  `MÇJ`, `AQSh` → `АҚШ`, `ToshDU` → `ToşDU`, `pH` and `McDonald` stay as they
  are (were `Mçj`, `Ақш`, `Toşdu`, `ph`, `Mcdonald`). A word with irregular
  case keeps it: `OʻzBEKISTON` → `ÖzBEKISTON`.
- An abbreviation keeps its case before a suffix: a word is also split where
  two or more capitals are followed by a lowercase letter, and each unit is
  cased by its own letters. `AQShda` → `AQŞda`, `MChJning` → `МЧЖнинг`,
  `ToshDUga` → `ToşDUga`, `TerSh` → `TerŞ` (were `Aqşda`, `Мчжнинг`,
  `Toşduga`, `Terş`). An Uzbek abbreviation with a suffix is not a token
  (`ToshDUga`, `SamDUda`); `ChatGPTda` is.
- With `source="auto"` each word is read in its own orthography: a Latin word
  in Cyrillic text is converted when it shows its orthography (`ŞAHAR`,
  `oʻrdak`), and a 1995 text with a foreign `ö` or `ō` stays 1995.
  `detect_script` is unchanged.

### Output changes

Golden diff 0.2.0 → 0.3.0, on 1188 inputs (67 added in 0.3.0):
`detect_script` 5, `normalize` 7, `sort_key_latin_2026` 1, `to_cyrillic` 64,
`to_latin_1995` 38, `to_latin_2026` 52. `detect_script` changes on capital o
with caron (2), on `ș` (1) and on decomposed letters (2), `normalize` on `ьо`
(6) and on `ș` (1), and `sort_key_latin_2026` on `ș` (1). Of the last three:

- the rule changes under Fixed: 11, 8 and 16;
- protected spans: 32, 11 and 19 — 13, 6 and 6 on inputs that 0.2.0 already
  had (the tokens `McDonald`, `ToshKent`, `tOSHKENT`, `SpO2`, `pH`, `B12` and
  `PaCO2`, two DOIs, two URLs, three e-mail addresses) and 19, 5 and 13 on the
  28 inputs added for them;
- case per letter unit: 3 in each (`OʻzBEKISTON`, `«AKADEMTECH» MChJ`,
  `AQSh va BMT`);
- the 8 inputs added for case units, numbers with a suffix and Uzbek
  abbreviations: 5 in each;
- word-level `auto`: 3, 2 and 0 on inputs added before it
  (`Toshkent viloyati Тошкент`, `Тошкент ŞAHAR`, and a Latin word with o with
  macron in Cyrillic text);
- the 13 inputs added for abbreviations with a suffix, word-level `auto`,
  `ș` and homoglyphs: 8, 7 and 7;
- decomposed letters, composed before converting: 2 in each (`O` + U+0308 +
  `zbekiston` and `o` + U+0308 + `zbek`, inputs that 0.2.0 already had).

The other `sort_key` fields, `normalize_apostrophes`, `script_class` and
`cyrillic_language` are unchanged. Schema 2 has seven new fields, `segments`,
`to_ascii`, `script_spans`, `fold_homoglyphs`, `validate_cyrillic`,
`validate_latin_1995` and `validate_latin_2026`.

### Documentation

- `PRIVACY.md`: what the library does and does not do with data, with
  answers to the six privacy questions of the Digital Public Goods Standard.
- `docs/architecture.md`: how the package is put together.
- README: who owns and maintains the library; the 2026 spelling rules are
  not adopted yet, and what the library does until they are.
- `LICENSE`: the copyright line names the legal owner, AKADEMTECH MChJ.
- README: language tags, the rules version, the CLDR licence.
- `PRIVACY.md`: the `warnings` module.
- README: protected spans and their limits, `to_ascii`, invisible characters
  and stress marks.
- README: case per letter unit; numbers with a suffix and Uzbek abbreviations
  are not tokens.
- README: text in more than one orthography and `source="auto"`;
  abbreviations with a suffix; `ș`; homoglyphs. The README and the comments
  no longer say that drafts of the reform used o with macron and o with
  caron (no source was found for o with caron); both are described as
  input forms only.
- README: checking a text (`validate` and its codes), `migration_report`,
  the command line, and that conversion composes the text (NFC).
  `PRIVACY.md`: the command-line tool.

### Tests

- `tests/test_privacy.py` fails if the library imports a module other than
  `re`, `unicodedata` and `warnings`, or calls `open`, `exec`, `eval`,
  `compile`, `__import__`, `input` or `breakpoint`.
- `tests/test_protect.py`: every kind of protected span, with the cases that
  must stay text; on every golden input, each protected piece comes out of
  all nine conversions unchanged; `protect=False` gives the output from
  before protected spans, except the case of seven mixed-case inputs, three
  inputs that word-level `auto` reads differently and two inputs with a
  decomposed letter.
  `tests/test_ascii.py`: `to_ascii`.
- `tests/test_scripts.py`: `script_spans`, `homoglyph_spans`,
  `fold_homoglyphs` and the `HOMOGLYPHS` table; `fold_homoglyphs` is
  idempotent on every golden input.
- `tests/test_checks.py`: `validate` and `migration_report`; on every golden
  input, a text without findings is its own conversion (but for a lone mark).
  `tests/test_cli.py`: the command-line tool, in this process and through
  `python -m akademtranslit`.
- `tests/test_privacy.py` checks the library and the command-line tool
  apart: the tool may also import `argparse`, `json` and `sys`, and may open
  a file only to read it; no library module imports it.

### Data

- `cldr/`: data for a Unicode CLDR proposal for the 2026 orthography
  (transforms, collation, exemplar characters, tests).
- `cldr/`: the e and ьо rules follow the library; checked against 0.3.0 and
  its 1139 golden inputs.
- `cldr/`: checked against 1175 golden inputs, with the library's output taken
  with `protect=False`, since the transforms protect nothing.
- `cldr/`: checked against 1188 golden inputs, with the library composing its
  input (NFC) and reading each word in its own orthography; `ș` is read as
  `ş` in both 2026 transforms.

## 0.2.0 — 2026-11-08

### Added

- `sort_key(text, orthography)`: alphabetical order in `cyrillic`,
  `latin_1995` or `latin_2026`. In `latin_2026`, `ç` comes after `ş`. In
  `latin_1995`, `oʻ gʻ sh ch` are single letters after `z`. In Cyrillic,
  `Ў Қ Ғ Ҳ` come after `Я`. The orthography is required; there is no
  detection.
- `normalize_apostrophes(text, style="unicode")`: rewrites the marks in Latin
  words to `ʻ`/`ʼ` (`"unicode"`) or `'` (`"ascii"`) without converting anything
  else.
- `script_class(text)` (`latin`, `cyrillic` or `mixed`) and
  `cyrillic_language(text)` (`uz`, `ru`, `mixed` or `unknown`): closed-set
  answers for routing. `detect_script` is unchanged.
- `LATIN_1995_ALPHABET` (28 units: 24 letters, then `oʻ gʻ sh ch`) and
  `CYRILLIC_ALPHABET` (35 letters).
- Golden vectors in `golden/`: 1121 inputs, the 0.1.1 and 0.2.0 outputs and
  their SHA-256 sums, with `tools/golden.py` to write, check and diff them.
- The README examples and the docstring examples run as tests. A test pins the
  module-level names that downstream code imports.

### Changed

- `LATIN_2026_ALPHABET` is in the order of Law No. O'RQ-1184: `ç` moved from
  after `b` to after `ş`. No conversion output depends on it.
- `__version__` is the only place the version is written.

### Fixed

- Cyrillic → Latin: `ъ` is dropped after a consonant before `е ё ю я`
  (`объект` → `obyekt`, `съёмка` → `syomka`) and after `ў` (`мўъжиза` →
  `moʻjiza`), as the 1995 spelling writes them; it was `ʼ` everywhere
  (`obʼyekt`, `moʻʼjiza`). Elsewhere it is still `ʼ` (`маъно` → `maʼno`). The
  reverse direction is unchanged (`obyekt` → `обект`), so this is a documented
  lossy mapping.
- Latin → Cyrillic: `ts` is `т` + `с` before the particles `-gina`, `-kina`,
  `-yu`, `-u`, `-ku`, `-yoq` and `-mikan` after a suffix: `aytsangizgina` →
  `айтсангизгина`, `ketsayu` → `кетсаю`, `tutsinmikan` → `тутсинмикан`; they
  came out with `ц`.
- Latin → Cyrillic: `oksitotsin`, `rifampitsin` and the `-rubitsin` drugs keep
  `ц` again (`окситоцин`, `рифампицин`, `доксорубицин`), as in 0.1.0; 0.1.1
  gave `окситотсин`. Verbs with the same ending (`bitsin`, `ketsin`) keep
  `т` + `с`.
- `normalize`: `´` (U+00B4) reads as an apostrophe, like the other seven
  marks. Unicode normalization (NFKC) used to turn it into a space and a
  combining accent, so `normalize("o´zbek")` was `"o zbek"`; it is now
  `"ozbek"`, the same key as `oʻzbek` and `o'zbek`. No other input's key
  changes.

### Output changes

Golden diff, 0.1.1 → 0.2.0, over 1121 inputs
(`python tools/golden.py --diff golden/golden-0.1.1.json golden/golden-0.2.0.json`):

| Field | Changed |
| --- | ---: |
| `normalize` | 5 |
| `detect_script` | 0 |
| `to_cyrillic` | 13 |
| `to_latin_1995` | 9 |
| `to_latin_2026` | 9 |

- `to_latin_1995` and `to_latin_2026`: the nine inputs with a dropped `ъ`, e.g.
  `объект` `obʼyekt` → `obyekt`, `мўъжиза` `moʻʼjiza` → `moʻjiza` (2026:
  `möʼjiza` → `möjiza`).
- `to_cyrillic`: seven particle forms (`aytsangizgina` `айцангизгина` →
  `айтсангизгина`) and six drug names (`oksitotsin` `окситотсин` →
  `окситоцин`).
- `normalize`: the five inputs with `´` inside a word: `o´zbek` `o zbek` →
  `ozbek`, `g´alaba`, `ma´no`, `jur´at` and `O´ZBEKISTON` likewise. A search
  index built with 0.1.x needs these keys rebuilt.

### Packaging

- License metadata in the PEP 639 form (`license = "MIT"`,
  `license-files`); the license classifier is gone, as PEP 639 asks.
- `py.typed` is shipped. The sdist includes `CHANGELOG.md`, `tests/`, `golden/`
  and `tools/`, so the test suite can run from it.
- The version is read from `akademtranslit.__version__`; the build needs
  `setuptools>=77`.
- Version classifiers name only the Python versions the test suite has run on.
- Dropped the `Natural Language :: Uzbek` classifier: it is not in the PyPI
  classifier list, and PyPI rejects uploads that carry it.
  `tools/check_classifiers.py` now checks the list in CI and before every
  release.
- Still Python 3.9 or newer, and still no dependencies.

## 0.1.1 — 2026-10-16

### Fixed

- Latin → Cyrillic: `y` before `oʻ` is `й` + `ў` (`yoʻq` → `йўқ`), not `ё` and a stray mark (`ёʻқ`).
- Latin → Cyrillic: `ts` is `т` + `с` before an Uzbek suffix (`ketsa` → `кетса`, `hayotsiz` → `ҳаётсиз`) and `т` + `ш` before `h` (`adabiyotshunos` → `адабиётшунос`); loanwords keep `ц`, with the misses listed in the README. A short list of loanwords whose tail reads like a suffix keeps `ц` as well (`aktsiz`, `tablitsa`, `levofloksatsin`, `leytsin`).
- Words in all caps that contain `ʻ` or `ʼ` stay in all caps (`OʻZBEKISTON` → `ЎЗБЕКИСТОН`, `ÖZBEKISTON`); they came out as `Ўзбекистон`.

## 0.1.0 — 2026-08-15

First release.
