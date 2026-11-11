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

### Fixed

- `detect_script` did not recognise capital `Ǒ` (U+01D1) as a 2026 letter.
- `ō` and `ǒ` came out unchanged when the input was already in the 2026
  orthography: `to_latin("ōrdak")` gave `ōrdak`; it now gives `ördak`.
- The `convert` docstring said DOIs pass through untouched; they do not.
- Latin to Cyrillic: `e` after a vowel is `э`: `aeroport` → `аэропорт`,
  `poeziya` → `поэзия` (were `аеропорт`, `поезия`). Before `v` it stays `е`:
  `Aliev` → `Алиев`.
- Cyrillic to Latin: `ь` before `о` is `y`: `бульон` → `bulyon` (was `bulon`).
- `ō` and `ǒ` in a Latin word inside Cyrillic text are read as `ö` when the
  text is converted to the 2026 orthography: `to_latin("Тошкент ōrdak")` gives
  `Toşkent ördak`.

### Changed

- Cyrillic is U+0400–U+052F in every function. `is_cyrillic`, and through it
  `detect_script` and `normalize`, used U+0400–U+04FF, so a letter from the
  Cyrillic Supplement block now counts as Cyrillic there too.
- The package imports `warnings`, for the `FutureWarning` above, besides `re`
  and `unicodedata`.
- `normalize` gives a different key for words with `ьо` (`бульон`: `bulon` →
  `bulyon`, now the same key as Latin `bulyon`) and for words with a letter
  from U+0500–U+052F inside (`тош` + U+0501 + `кент`: `tosh kent` →
  `toshkent`). Rebuild search keys made with 0.2.0 for such words.

### Output changes

Golden diff 0.2.0 → 0.3.0, on 1139 inputs (18 added in 0.3.0):
`detect_script` 2, `normalize` 6, `to_cyrillic` 11, `to_latin_1995` 8,
`to_latin_2026` 16. `sort_key`, `normalize_apostrophes`, `script_class` and
`cyrillic_language` are unchanged.

### Documentation

- `PRIVACY.md`: what the library does and does not do with data, with
  answers to the six privacy questions of the Digital Public Goods Standard.
- `docs/architecture.md`: how the package is put together.
- README: who owns and maintains the library; the 2026 spelling rules are
  not adopted yet, and what the library does until they are.
- `LICENSE`: the copyright line names the legal owner, AKADEMTECH MChJ.
- README: language tags, the rules version, the CLDR licence.
- `PRIVACY.md`: the `warnings` module.

### Tests

- `tests/test_privacy.py` fails if the package imports a module other than
  `re`, `unicodedata` and `warnings`, or calls `open`, `exec`, `eval`,
  `compile`, `__import__`, `input` or `breakpoint`.

### Data

- `cldr/`: data for a Unicode CLDR proposal for the 2026 orthography
  (transforms, collation, exemplar characters, tests).

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
