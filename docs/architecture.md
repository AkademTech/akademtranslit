# Architecture

How the package is put together. For what it does and how to call it, see the
[README](../README.md).

## Purpose

The library does two jobs, and keeps them apart:

- **Transliteration** (`convert`, `to_latin`, `to_cyrillic`) writes text in
  another orthography, for people to read. It restores each word's case and
  leaves unchanged everything that is not a word, as well as protected spans:
  URLs, e-mail addresses, DOIs, markup, placeholders, file paths, terms the
  caller names and tokens such as `pH`. `latin_1995` ↔ `latin_2026`
  round-trips exactly for canonical text; the Cyrillic round trip has the
  gaps listed in the README under "Guarantees, and their limits".
- **Normalization** (`normalize`) is deliberately lossy. It gives one key for
  the same word in all three orthographies, for search and deduplication, and
  the key is never meant to be shown.

Sorting (`sort_key`), detection (`detect_script`, `script_class`,
`cyrillic_language`) and the script of each word (`script_spans`,
`fold_homoglyphs`, `homoglyph_spans`) are described further down.

## Layout

Everything is in `src/akademtranslit/`. The only imports from outside the
package are `re`, `unicodedata` and `warnings`; `tests/test_privacy.py` pins
that.

- `tables.py` is data only: orthography names, `RULES_VERSION`, the two
  marks and the eight `APOSTROPHE_VARIANTS`, `DEFAULT_IGNORABLE` (Unicode
  15.1), the Cyrillic range (`CYRILLIC_FIRST`, `CYRILLIC_LAST`), vowel sets,
  the context-free mapping tables, the reform steps, `ASCII_SCHEME` and
  `ASCII_CAPITALS`, `HOMOGLYPHS`, the three alphabets and
  `TS_LOANWORD_STEMS`. Apart from `__future__`, it imports nothing.
- `rules.py` is the word engine: the word pattern `_WORD_RE`,
  `canonicalize_marks`, the case of each letter (`_case_mask`, `apply_case`),
  `map_words`, `map_words_by` and `map_word`, `word_class` (the orthography
  one word shows) and the four per-word conversion functions with the context
  rules. It uses `tables` and `re`.
- `normalize.py` has `normalize`, `fold_cyrillic`, `fold_latin_2026` and
  `is_cyrillic`. It uses `rules`, `tables`, `re` and `unicodedata`.
- `collation.py` has `sort_key` (uses `rules.map_words`, `tables`, `tags`,
  `unicodedata`); `apostrophes.py` has `normalize_apostrophes` (uses
  `rules._WORD_RE`, `tables` and `re`); `detection.py` has `script_class` and
  `cyrillic_language` (uses `tables` and `unicodedata`).
- `scripts.py` has `script_spans`, `homoglyph_spans` and `fold_homoglyphs`.
  It uses `rules` (`_WORD_RE`, `word_class`), `detection` (which letters are
  Latin and which Cyrillic) and `tables` (`HOMOGLYPHS`).
- `protect.py` finds protected spans: `Protect` (which kinds; immutable),
  `segments`, and `_spans` and `_settings`, which `convert` calls. Its module
  docstring gives the rule for each kind. It uses `tables` and `re`.
- `tags.py` reads BCP 47 language tags: `script_for_tag`, `tag_for_script`,
  and `_orthography`, which `convert`, `to_latin` and `sort_key` call for an
  argument that is not a name from `SCRIPTS`. It raises the `FutureWarning`
  for a tag without a variant (`uz-Latn`, `uz`), pointed at the line that
  called the public function. It uses `tables`, `re` and `warnings`.
- `__init__.py` is the public API: it re-exports the public names, defines
  `__version__` and `__all__`, and holds `detect_script`, `convert`,
  `to_latin`, `to_cyrillic`, `to_ascii`, the `_PIPELINES` table and
  `_auto_sources`, which decides how `source="auto"` reads each word. It
  uses `unicodedata` for `to_ascii`.

## Conversion pipeline

`latin_1995` is the pivot. Every conversion is a chain of word-level steps,
listed in `_PIPELINES` in `__init__.py`: Cyrillic and `latin_2026` each have
one step to and from `latin_1995`, so Cyrillic ↔ `latin_2026` is two steps
through it. `latin_2026` → `latin_2026` has one step,
`latin_2026_canonical_word`, which writes the other input forms of `ö` and
`ş` as those letters (`LATIN_2026_INPUT_ALIASES`: o with macron and o with
caron, s with comma below); it also runs first in `latin_1995` → `latin_2026` and last in
Cyrillic → `latin_2026` (a Latin word inside Cyrillic text). Cyrillic and
`latin_1995` to themselves are not in the table and have no steps.

`convert` reads `source` or `target` as a language tag when it is not a name
from `SCRIPTS` (or `"auto"` for `source`) and `protect` as `True`, `False` or
a `Protect`, raising `ValueError` for anything it cannot read. It returns
empty text as it is. Otherwise it splits the text into protected spans and
the text between them (`protect._spans`). With a named `source`, it calls
`map_words` on each piece of that text with a function that applies the steps
for `source` and `target` in order. With `source="auto"`, `_auto_sources`
first decides a source for each word of that text (below), and `map_words_by`
converts each word with the steps for its own source. Each protected span is
copied as it is. `to_latin` and `to_cyrillic` call `convert` with
`source="auto"`; `to_latin` reads a tag in `variant` first.

`source="auto"` is decided in two passes over the words of the text outside
the protected spans. `word_class` puts each word, lowercased and with its
marks canonicalised, in the first class that fits: `C` (a letter in
U+0400–U+052F), `N` (`ş ç ğ ö` or s with comma below), `O` (`oʻ` or `gʻ`),
`D` (o with macron or o with caron), `W` (`sh` or `ch`) or `-` (none). The
counts decide two things:

- the Latin orthography of the text: `latin_2026` if `N > 0` and either
  `N > O + W`, or `N = O + W` and `O = 0`; otherwise `latin_1995`. `D` is not
  counted: foreign names have those letters;
- whether the text is mostly Cyrillic: `C ≥ 1` and `C ≥ N + O + D + W + -`.

Then `C` words are read as Cyrillic, `N` and `D` words as `latin_2026`, `O`
words as `latin_1995`, and `W` and `-` words in the Latin orthography of the
text, except that they keep no steps (stay as they are) when the target is
Cyrillic and the text is mostly Cyrillic. `detect_script` is not used and
does not change: it still answers for the whole text.

`segments` scans once per call. Each kind has one or more finders: regular
expressions, a brace matcher for ICU MessageFormat, and plain string search
for `{{`, `<!--` and the like. A finder reports the first span it sees from a
position, and the scanner takes the one that starts first, then the longest,
then the kind listed first in `protect.KINDS`. The message texts inside an ICU
`plural` or `select` are scanned again, for every kind, and adjacent pieces of
one kind are joined.

`to_ascii` calls `to_latin` with `variant="latin_1995"`, applies
`ASCII_SCHEME`, writes capital `Ş` and `Ç` by `ASCII_CAPITALS` (`SH`, `CH`
beside a capital, `Sh`, `Ch` otherwise, judged on the characters around them),
removes the apostrophe marks, decomposes with NFKD and keeps only ASCII
characters.

`map_words` does the tokenising and the casing:

1. `_WORD_RE` finds words: runs of letters, joined by apostrophe-like marks,
   with a trailing mark kept only after `o` or `g` (so the quote in `'salom'`
   is not taken, while `togʻ` keeps its letter).
2. `_case_mask` gives each character its case: capital, lowercase, or none
   (`ʻ`, `ʼ`). An `h` after a capital `S` or `C` is a capital when the word
   has another capital, since `Sh` and `Ch` are one letter: `MChJ` and `AQSh`
   are all caps, `Shahar` is not. Where a lowercase letter is followed by a
   capital, and where two or more capitals are followed by a lowercase
   letter, the word is split into letter units (`Tosh|DU|ga`, `Oʻz|MU`,
   `AQSh|da`); a character without case stays with the letter before it. A
   word without a capital is one unit and skips this step.
3. Each unit is lowercased, and `canonicalize_marks` rewrites every variant
   to `ʻ` after `o` or `g` and to `ʼ` elsewhere.
4. The steps convert the lowercase unit.
5. `apply_case` puts the unit's case back, judged by the unit's own letters
   (the `Sh` of `Ter|Sh` has no other capital, so its `h` is lowercase).
   Irregular case (`MChJ`, `ShAHAR`, `McDonald`) is copied letter by letter
   when the output is as long as the input. Otherwise it is re-applied as all
   caps (judged by the mask), an initial capital or lowercase, because the
   length changes: `ш` is one character, `sh` is two.

Text between words is never passed to a step, so digits, punctuation and
whitespace come through unchanged. Because the marks are canonicalised even
when there are no steps, converting text to its own orthography normalises
the marks rather than doing nothing.

## Context rules

The context-free readings are tables in `tables.py`. Seven readings depend on
position and are code in `rules.py`; the module docstring describes each.

- `е`: `cyrillic_word_to_latin_1995` writes `ye` at the start of a word and
  after a vowel, `ъ` or `ь`, and `e` elsewhere. In the other direction,
  `latin_1995_word_to_cyrillic` checks `ye` (always `е`) and then a bare `e`
  (`э` at the start of a word and after `a e i o u` unless `v` follows, `е`
  elsewhere) before it looks at the table.
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
- `ь`: `cyrillic_word_to_latin_1995` writes `y` before `о`; elsewhere the
  table drops it.

`cyrillic_word_to_latin_1995` checks `е`, `ц`, `с` before `ҳ`, `ъ` and `ь`
in that order, then the table; `LATIN_1995_TO_CYRILLIC` is tried row by row,
longer forms first. `latin_2026_word_to_1995` first calls
`latin_2026_canonical_word`, which rewrites the other input forms of `ö` and
`ş` (`LATIN_2026_INPUT_ALIASES`).

## Normalization

`normalize` runs these steps in order:

1. Empty or whitespace-only text gives `""`.
2. U+00B4 becomes U+02BC (`ʼ`); NFKC would make it a space and an accent.
3. NFKC, then lowercase.
4. If any character is in U+0400–U+052F, the words go through
   `cyrillic_word_to_latin_1995` with `map_words`, so the positional rules
   reach the key (`Чоршанбиев` gives `chorshanbiyev`).
5. Every apostrophe variant and both canonical marks are removed.
6. `fold_latin_2026`: `ş` → `sh`, `ç` → `ch`, `ğ` → `g`, `ö` → `o`, and the
   other input forms the same way (o with macron and o with caron → `o`, s
   with comma below → `sh`).
7. `fold_cyrillic` maps leftover Cyrillic, such as letters of neighbouring
   orthographies, and drops any other character in U+0400–U+052F.
8. Every character other than `a`–`z` and `0`–`9` becomes a space; runs of
   whitespace become one space, and the ends are stripped.

Romanization variants (`kh`/`x`, `zh`/`j`) are not folded; the module
docstring says why. The README ("Versioning") promises that `normalize`
output does not change in a patch release: search indexes are built on it.

## Sorting and detection

`sort_key(text, orthography)` needs one of `SCRIPTS` or a language tag for
one; there is no default.
It puts the text in NFC, strips it, lowercases a working copy, reads the
other input forms of `ö` and `ş` as those letters for `latin_2026`, and
canonicalises the marks with `map_words`.
The weights are one `0` for a run of whitespace, `1`–`10` for the digits,
`11 + k` for the `k`-th unit of the orthography's alphabet, and
`1000 + code point` for any other letter. In `latin_1995`, `oʻ`, `gʻ`, `sh`
and `ch` are single units. Punctuation and the marks are not counted. The key
is `(weights, NFC text)`, so ties are broken by the text.

- `detect_script` (in `__init__.py`) returns `cyrillic` if any character is
  in U+0400–U+052F, `latin_2026` if any character is in `_REFORM_LETTERS`
  (among them `ş ç ğ ö` in either case and the other input forms of `ö` and
  `ş`),
  and `latin_1995` otherwise. A `latin_2026` text without them reads as
  `latin_1995`, which matters for a real s + h: pass `source` when known.
- `script_class` (in `detection.py`) counts a letter as Cyrillic if it is in
  U+0400–U+052F, and as Latin if its Unicode name starts with `LATIN`. Both
  kinds give `mixed`, only Cyrillic gives `cyrillic`, and anything else,
  including text without letters, gives `latin`.
- `cyrillic_language` looks only for `ў қ ғ ҳ` (Uzbek) and `щ ы` (Russian),
  in either case, so short text is often `unknown`; it is a routing
  heuristic, not a language identifier.
- `script_spans` (in `scripts.py`) splits the text with `_WORD_RE` and names
  each word by `word_class`: `cyrillic` for `C`, or `mixed` if the word also
  has a Latin letter; `latin_2026` for `N` and `D`; `latin_1995` for `O`;
  `latin` for `W` and `-`. The text between words is `None`.
- `fold_homoglyphs` takes each word with both Latin and Cyrillic letters (by
  the two tests of `script_class`), keeps the alphabet with more letters in
  it, and replaces each letter of the other by its pair in `HOMOGLYPHS`. A tie,
  or a letter without a pair, leaves the word as it is. In a Latin word it
  also writes s with comma below as `ş`. `homoglyph_spans` gives
  `(start, stop, word)` for each word it changes, and `fold_homoglyphs`
  splices them in.

Every function takes Cyrillic to be U+0400–U+052F, the Cyrillic and
Cyrillic Supplement blocks: `CYRILLIC_FIRST` and `CYRILLIC_LAST` in
`tables.py`.

## Stability and compatibility

- The public API is the 31 names in `__all__` in `__init__.py`.
- `golden/` holds the output of the public functions on 1188 fixed inputs,
  `inputs.json`, and of the tag functions on 57 tags and 6 names,
  `tag-inputs.json` (both append-only), one file per release
  (`golden-0.1.1.json`, `golden-0.2.0.json`, `golden-0.3.0.json`), and
  `SHA256SUMS`. From 0.3.0 the files have schema 2: 27 fields (listed in
  `fields()` in `tools/golden.py`; `convert` for all nine pairs, `segments`,
  `to_ascii`, `script_spans` and `fold_homoglyphs` among them),
  the tag results and `RULES_VERSION`. `tools/golden.py` writes them
  (`--write`, from another `src/` with `--src`), checks them against `src/`
  and checks that a change to conversion output comes with a new rules
  version (`--check`), and lists what changed between two releases
  (`--diff`). `tests/test_golden.py` and CI run the check.
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
  `detect_script`), `test_collation.py`, `test_apostrophes.py` (with
  `strip_invisible` and `strip_stress`), `test_detection.py`.
- Protected spans and ASCII: `test_protect.py` (each kind, what stays text,
  the shapes that are not tokens, each protected piece unchanged in all nine
  conversions, `protect=False` against the output from before),
  `test_ascii.py`.
- Words and homoglyphs: `test_scripts.py` (`script_spans`, `homoglyph_spans`,
  `fold_homoglyphs`, the `HOMOGLYPHS` table).
- Behaviour changes: `test_regressions.py` (0.1.1 fixes),
  `test_changes_0_2_0.py` (0.2.0 rule changes), `test_changes_0_3_0.py`
  (0.3.0: the other input forms of `ö` and `ş`, the Cyrillic range, language tags, the `e` and
  `ьо` rules, `ValueError` for a non-string orthography, case per letter
  unit, abbreviations with a suffix, s with comma below, word-level `auto`).
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
