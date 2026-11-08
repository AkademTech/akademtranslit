# Changelog

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

### Output changes

Golden diff, 0.1.1 → 0.2.0, over 1121 inputs
(`python tools/golden.py --diff golden/golden-0.1.1.json golden/golden-0.2.0.json`):

| Field | Changed |
| --- | ---: |
| `normalize` | 0 |
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

### Packaging

- License metadata in the PEP 639 form (`license = "MIT"`,
  `license-files`); the license classifier is gone, as PEP 639 asks.
- `py.typed` is shipped. The sdist includes `CHANGELOG.md`, `tests/`, `golden/`
  and `tools/`, so the test suite can run from it.
- The version is read from `akademtranslit.__version__`; the build needs
  `setuptools>=77`.
- Version classifiers name only the Python versions the test suite has run on.
- Still Python 3.9 or newer, and still no dependencies.

## 0.1.1 — 2026-10-16

### Fixed

- Latin → Cyrillic: `y` before `oʻ` is `й` + `ў` (`yoʻq` → `йўқ`), not `ё` and a stray mark (`ёʻқ`).
- Latin → Cyrillic: `ts` is `т` + `с` before an Uzbek suffix (`ketsa` → `кетса`, `hayotsiz` → `ҳаётсиз`) and `т` + `ш` before `h` (`adabiyotshunos` → `адабиётшунос`); loanwords keep `ц`, with the misses listed in the README. A short list of loanwords whose tail reads like a suffix keeps `ц` as well (`aktsiz`, `tablitsa`, `levofloksatsin`, `leytsin`).
- Words in all caps that contain `ʻ` or `ʼ` stay in all caps (`OʻZBEKISTON` → `ЎЗБЕКИСТОН`, `ÖZBEKISTON`); they came out as `Ўзбекистон`.

## 0.1.0 — 2026-08-15

First release.
