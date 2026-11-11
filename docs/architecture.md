# Architecture

How the package is put together. For what it does and how to call it, see the
[README](../README.md).

## Purpose

The library does two jobs, and keeps them apart:

- **Transliteration** (`convert`, `to_latin`, `to_cyrillic`) writes text in
  another orthography, for people to read. It restores each word's case and
  leaves everything that is not a word unchanged. `latin_1995` ↔ `latin_2026`
  round-trips exactly for canonical text; the Cyrillic round trip has the
  gaps listed in the README under "Guarantees, and their limits".
- **Normalization** (`normalize`) is deliberately lossy. It gives one key for
  the same word in all three orthographies, for search and deduplication, and
  the key is never meant to be shown.

Sorting (`sort_key`) and detection (`detect_script`, `script_class`,
`cyrillic_language`) are described further down.

## Layout

Everything is in `src/akademtranslit/`. The only imports from outside the
package are `re` and `unicodedata`; `tests/test_privacy.py` pins that.

- `tables.py` is data only: orthography names, the two marks and the eight
  `APOSTROPHE_VARIANTS`, vowel sets, the context-free mapping tables, the
  reform steps, the three alphabets and `TS_LOANWORD_STEMS`. Apart from
  `__future__`, it imports nothing.
- `rules.py` is the word engine: the word pattern `_WORD_RE`,
  `canonicalize_marks`, `apply_case`, `map_words`, and the four per-word
  conversion functions with the context rules. It uses `tables` and `re`.
- `normalize.py` has `normalize`, `fold_cyrillic`, `fold_latin_2026` and
  `is_cyrillic`. It uses `rules`, `tables`, `re` and `unicodedata`.
- `collation.py` has `sort_key` (uses `rules.map_words`, `tables`,
  `unicodedata`); `apostrophes.py` has `normalize_apostrophes` (uses
  `rules._WORD_RE` and `tables`); `detection.py` has `script_class` and
  `cyrillic_language` (uses only `unicodedata`).
- `__init__.py` is the public API: it re-exports the public names, defines
  `__version__` and `__all__`, and holds `detect_script`, `convert`,
  `to_latin`, `to_cyrillic` and the `_PIPELINES` table.

## Conversion pipeline

`latin_1995` is the pivot. Every conversion is a chain of word-level steps,
listed in `_PIPELINES` in `__init__.py`: Cyrillic and `latin_2026` each have
one step to and from `latin_1995`, so Cyrillic ↔ `latin_2026` is two steps
through it. A pair not in the table (source and target the same) has no steps.

`convert` raises `ValueError` for an unknown script name, returns empty
text as it is, runs `detect_script` when `source` is `"auto"`, and calls
`map_words` with a function that applies the steps in order. `to_latin` and
`to_cyrillic` call `convert` with `source="auto"`.

`map_words` does the tokenising and the casing:

1. `_WORD_RE` finds words: runs of letters, joined by apostrophe-like marks,
   with a trailing mark kept only after `o` or `g` (so the quote in `'salom'`
   is not taken, while `togʻ` keeps its letter).
2. Each word is lowercased, and `canonicalize_marks` rewrites every variant
   to `ʻ` after `o` or `g` and to `ʼ` elsewhere.
3. The steps convert the lowercase word.
4. `apply_case` re-applies the source word's case (all caps, an initial
   capital, or lowercase) rather than copying it letter by letter, because
   the length changes: `ш` is one character, `sh` is two.

Text between words is never passed to a step, so digits, punctuation and
whitespace come through unchanged. Because the marks are canonicalised even
when there are no steps, converting text to its own orthography normalises
the marks rather than doing nothing.

## Context rules

The context-free readings are tables in `tables.py`. Five readings depend on
position and are code in `rules.py`; the module docstring describes each.

- `е`: `cyrillic_word_to_latin_1995` writes `ye` at the start of a word and
  after a vowel, `ъ` or `ь`, and `e` elsewhere. In the other direction,
  `latin_1995_word_to_cyrillic` checks `ye` (always `е`) and then a bare `e`
  (`э` at the start of a word, `е` elsewhere) before it looks at the table.
- `ц`: `cyrillic_word_to_latin_1995` writes `ts` after a vowel and `s`
  elsewhere.
- `ts`: in `latin_1995_word_to_cyrillic`, after the `e` checks, `_ts_splits`
  decides whether `t` is read alone as `т` or `ts` is the table's `ц`; its
  docstring lists the checks in order, and the first that applies decides.
- `с` + `ҳ`: `cyrillic_word_to_latin_1995` writes `sʼh`, and the first row of
  `LATIN_1995_TO_CYRILLIC` reads it back. `LATIN_1995_TO_2026_STEPS` replaces
  the four letters first and only then drops the separator; the comment in
  `tables.py` says why the order matters. `LATIN_2026_TO_1995_STEPS` puts the
  separator back before it expands the four letters.
- `ъ`: `cyrillic_word_to_latin_1995` drops it after `ў`, and after a
  consonant before `е ё ю я`; elsewhere the table gives `ʼ`.

`cyrillic_word_to_latin_1995` checks `е`, `ц`, `с` before `ҳ` and `ъ` in
that order, then the table; `LATIN_1995_TO_CYRILLIC` is tried row by row,
longer forms first. `latin_2026_word_to_1995` first rewrites the draft
glyphs `ō` and `ǒ` to `ö` (`LATIN_2026_INPUT_ALIASES`).

## Normalization

`normalize` runs these steps in order:

1. Empty or whitespace-only text gives `""`.
2. U+00B4 becomes U+02BC (`ʼ`); NFKC would make it a space and an accent.
3. NFKC, then lowercase.
4. If any character is in U+0400–U+04FF, the words go through
   `cyrillic_word_to_latin_1995` with `map_words`, so the positional rules
   reach the key (`Чоршанбиев` gives `chorshanbiyev`).
5. Every apostrophe variant and both canonical marks are removed.
6. `fold_latin_2026`: `ş` → `sh`, `ç` → `ch`, `ğ` → `g`, `ö` `ō` `ǒ` → `o`.
7. `fold_cyrillic` maps leftover Cyrillic, such as letters of neighbouring
   orthographies, and drops any other character in U+0400–U+04FF.
8. Every character other than `a`–`z` and `0`–`9` becomes a space; runs of
   whitespace become one space, and the ends are stripped.

Romanization variants (`kh`/`x`, `zh`/`j`) are not folded; the module
docstring says why. The README ("Versioning") promises that `normalize`
output does not change in a patch release: search indexes are built on it.

## Sorting and detection

`sort_key(text, orthography)` needs one of `SCRIPTS`; there is no default.
It puts the text in NFC, strips it, lowercases a working copy, reads `ō` and
`ǒ` as `ö` for `latin_2026`, and canonicalises the marks with `map_words`.
The weights are one `0` for a run of whitespace, `1`–`10` for the digits,
`11 + k` for the `k`-th unit of the orthography's alphabet, and
`1000 + code point` for any other letter. In `latin_1995`, `oʻ`, `gʻ`, `sh`
and `ch` are single units. Punctuation and the marks are not counted. The key
is `(weights, NFC text)`, so ties are broken by the text.

- `detect_script` (in `__init__.py`) returns `cyrillic` if any character is
  in U+0400–U+04FF, `latin_2026` if any character is in `_REFORM_LETTERS`
  (among them `ş ç ğ ö` in either case and the draft glyphs `ō` and `ǒ`),
  and `latin_1995` otherwise. A `latin_2026` text without them reads as
  `latin_1995`, which matters for a real s + h: pass `source` when known.
- `script_class` (in `detection.py`) counts a letter as Cyrillic if it is in
  U+0400–U+052F, and as Latin if its Unicode name starts with `LATIN`. Both
  kinds give `mixed`, only Cyrillic gives `cyrillic`, and anything else,
  including text without letters, gives `latin`.
- `cyrillic_language` looks only for `ў қ ғ ҳ` (Uzbek) and `щ ы` (Russian),
  in either case, so short text is often `unknown`; it is a routing
  heuristic, not a language identifier.

`normalize.py` (and so `detect_script`) takes Cyrillic as U+0400–U+04FF;
`detection.py` and `apostrophes.py` take U+0400–U+052F.

## Stability and compatibility

- The public API is the 22 names in `__all__` in `__init__.py`.
- `golden/` holds the output of eight public functions (12 fields, listed in
  `fields()` in `tools/golden.py`) on 1121 fixed inputs: `inputs.json`
  (append-only), `golden-0.1.1.json`, `golden-0.2.0.json` and `SHA256SUMS`.
  `tools/golden.py` writes them (`--write`), checks them against `src/`
  (`--check`) and lists what changed between two releases (`--diff`).
  `tests/test_golden.py` and CI run the check.
- Some code outside this repository imports module-level names, including
  private ones such as `normalize._MARKS`. `tests/test_public_api_compat.py`
  copies those import statements verbatim and checks that they still work;
  removing or renaming one of those names needs a major version.

## Tests

`pyproject.toml` runs pytest over `tests/` and `src/` with
`--doctest-modules` and puts `src/` on the path, so the docstring examples
run and no install is needed.

- Conversion: `test_to_latin.py`, `test_to_cyrillic.py` (letters, context
  rules, apostrophe variants), `test_roundtrip.py` (round-trip tiers, lossy
  letters), `test_alphabets.py` (the alphabets and their order).
- Normalization and helpers: `test_normalize.py` (the key contract and
  `detect_script`), `test_collation.py`, `test_apostrophes.py`,
  `test_detection.py`.
- Behaviour changes: `test_regressions.py` (0.1.1 fixes),
  `test_changes_0_2_0.py` (0.2.0 rule changes).
- Contracts: `test_golden.py`, `test_public_api_compat.py`, `test_readme.py`
  (README examples, via doctest), `test_privacy.py` (no I/O).

## Build and release

- `pyproject.toml` builds with setuptools. The version is read from
  `akademtranslit.__version__`, the package is found under `src/`, `py.typed`
  ships with it, and there are no runtime dependencies. `MANIFEST.in` adds
  the changelog, `PRIVACY.md`, `docs/`, `tests/`, `golden/` and `tools/` to
  the sdist.
- `ci.yml` runs on pushes to `main` and on pull requests: the tests and the
  golden check on Ubuntu with Python 3.9 to 3.14 and on macOS and Windows
  with 3.14, and a build job that validates the classifiers, builds the sdist
  and wheel, runs `twine check --strict` and tests the wheel in Python 3.9.
- `release.yml` runs on `v*` tags. Its build job checks that the tag matches
  `__version__` and repeats the golden, classifier, build, `twine check` and
  wheel steps. The publish job runs in the `pypi` environment and uploads
  with PyPI Trusted Publishing, with no API token in the workflow; the
  workflow's header comment says that environment needs approval. A last job
  creates the GitHub release with notes from `CHANGELOG.md`. Run by hand,
  the workflow only builds.
- Actions are pinned to commit hashes, and both workflows default to
  read-only repository permissions.
