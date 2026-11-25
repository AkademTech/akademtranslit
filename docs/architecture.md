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
`cyrillic_language`), the script of each word (`script_spans`,
`fold_homoglyphs`, `homoglyph_spans`), checking (`validate`,
`migration_report`) and the command-line tool are described further down.

## Layout

Everything is in `src/akademtranslit/`. The library's only imports from
outside the package are `re`, `unicodedata` and `warnings`. The command-line
tool (`cli.py`, `__main__.py`) also imports `argparse`, `json` and `sys`, and
no library module imports it. `tests/test_privacy.py` pins both.

- `tables.py` is data only: orthography names, `RULES_VERSION`, the two
  marks and the eight `APOSTROPHE_VARIANTS`, `DEFAULT_IGNORABLE` (Unicode
  15.1), the Cyrillic range (`CYRILLIC_FIRST`, `CYRILLIC_LAST`), vowel sets,
  the context-free mapping tables, the reform steps, `ASCII_SCHEME` and
  `ASCII_CAPITALS`, `HOMOGLYPHS`, the three alphabets and
  `TS_LOANWORD_STEMS`. Apart from `__future__`, it imports nothing.
- `rules.py` is the word engine: the word pattern `_WORD_RE`,
  `canonicalize_marks`, the case of each letter (`_case_mask`, `apply_case`),
  `map_words`, `map_words_by` and `map_word`, `word_class` (the orthography
  one word shows), the four per-word conversion functions with the context
  rules and `convert_cyrillic_word`, the Cyrillic step of `convert`; and,
  from 0.3.2, the rules that look at a whole word or at the text around it:
  `is_roman_numeral`, `month_soft_sign` and `dates`. It uses `tables` and
  `re`.
- `normalize.py` has `normalize`, `fold_cyrillic`, `fold_latin_2026` and
  `is_cyrillic`. It uses `rules`, `tables`, `re` and `unicodedata`.
- `collation.py` has `sort_key` (uses `rules.map_words`, `tables`, `tags`,
  `unicodedata`); `apostrophes.py` has `normalize_apostrophes` (uses
  `rules._WORD_RE`, `tables` and `re`); `detection.py` has `script_class` and
  `cyrillic_language` (uses `tables` and `unicodedata`).
- `scripts.py` has `script_spans`, `homoglyph_spans` and `fold_homoglyphs`.
  It uses `rules` (`_WORD_RE`, `word_class`), `detection` (which letters are
  Latin and which Cyrillic) and `tables` (`HOMOGLYPHS`).
- `checks.py` has `validate`, `migration_report` and `CODES`, the codes of
  `validate`. It uses `apostrophes` (`_INVISIBLE_RE`), `detection`,
  `protect` (`_spans`, `_settings`), `rules` (`_WORD_RE`, `word_class`,
  `canonicalize_marks`), `scripts` (`_fold_word`), `tables`, `tags`
  (`_orthography`), `re` and `unicodedata`. It also calls `convert`, which it
  imports from the package inside the function that calls it, because the
  package imports `checks.py`.
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
  uses `unicodedata` for NFC in `convert` and `detect_script` and for
  `to_ascii`.
- `cli.py` is the command-line tool, `main(argv)`, and `__main__.py` runs it
  for `python -m akademtranslit`. `cli.py` uses the package's public
  functions, `checks.CODES`, `tags._orthography`, `argparse`, `json`, `sys`
  and `warnings`. The package does not import either file.

## Conversion pipeline

`latin_1995` is the pivot. Every conversion is a chain of word-level steps,
listed in `_PIPELINES` in `__init__.py`: Cyrillic and `latin_2026` each have
one step to and from `latin_1995`, so Cyrillic ↔ `latin_2026` is two steps
through it. `latin_2026` → `latin_2026` has one step,
`latin_2026_canonical_word`, which writes the other input forms of `ö` and
`ş` as those letters (`LATIN_2026_INPUT_ALIASES`: o with macron and o with
caron, s with comma below); it also runs first in `latin_1995` → `latin_2026` and last in
Cyrillic → `latin_2026` (a Latin word inside Cyrillic text). Cyrillic and
`latin_1995` to themselves are not in the table and have no steps. The step
from Cyrillic is `convert_cyrillic_word`; `normalize` reads Cyrillic with
`cyrillic_word_to_latin_1995` instead (see Normalization).

`convert` reads `source` or `target` as a language tag when it is not a name
from `SCRIPTS` (or `"auto"` for `source`) and `protect` as `True`, `False` or
a `Protect`, raising `ValueError` for anything it cannot read. It returns
empty text as it is. Otherwise it splits the text into protected spans and
the text between them (`protect._spans`), and composes each piece of that
text with `unicodedata.normalize("NFC", ...)`, so that a base letter and a
combining mark (`O` and U+0308) are one letter (`Ö`) before any step reads
them. It goes over the words of each piece of that text with `_WORD_RE` and
converts each with `map_word` and a function that applies the steps for its
source and `target` in order. With a named `source` that is the source of
every word. With `source="auto"`, `_auto_sources`
first decides a source for each word of that text (below), and each word is
converted with the steps for its own source. Each protected span is
copied as it is. `to_latin` and `to_cyrillic` call `convert` with
`source="auto"`; `to_latin` reads a tag in `variant` first.

Two rules need a word as it stands, before `map_word` lowercases it and
splits it into letter units, so `convert` applies them itself, to a word
read from a Latin orthography and converted to Cyrillic: a Roman numeral
stays as it is (`is_roman_numeral`, which also sees the character after the
word, and for one letter the words beside it), and a month name standing
alone gets its `ь` after the steps
(`month_soft_sign`). Then, on each converted piece of text, `dates` writes
the separator after the number of a year or of a day of the month as the
target does, where the word after the number was read in the other script.
`convert` goes over the words of the piece itself, so that it knows where
each converted word starts: it passes `dates` the offsets of the words read
in Cyrillic when the target is Latin, or in a Latin orthography when the
target is Cyrillic. Within one script the separator stays. The text between
protected spans is converted piece by piece, so a number and the word after
it count only within one piece.

`source="auto"` is decided in two passes over the words of the composed text
outside the protected spans. `word_class` puts each word, lowercased and with its
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
one kind are joined. Each finder takes time linear in the text; from 0.3.1
`tests/test_changes_0_3_1.py` times the inputs that took 0.3.0 quadratic time.

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
whitespace come through unchanged, except the hyphen or space after the
number of a date that changes script, which `dates` writes for the target.
Because the marks are canonicalised even when there are no steps,
converting text to its own orthography normalises the marks rather than
doing nothing. A date in its own script keeps its separator.

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

From 0.3.2 more rules look at a whole word or at the text around it:

- Word-final `ц`: `convert_cyrillic_word` writes `s` for a `ц` at the end of
  the word or followed by Uzbek suffixes only (`_FINAL_TS_SUFFIXES_RE`:
  `лар` with a possessive, then a case ending), and reads any other `ц` as
  above. `cyrillic_word_to_latin_1995` does not.
- Month names: `convert_cyrillic_word` writes the `я` of `сентябр` and
  `октябр` as `a` (`_CYRILLIC_MONTHS_WITH_A`), and
  `latin_1995_word_to_cyrillic` the `a` of `sentabr` and `oktabr` as `я`
  (`_LATIN_MONTHS_WITH_YA`), with any suffix. `month_soft_sign` adds `ь`,
  in the case of the letter before it, when the whole Latin word is a month
  name that Cyrillic writes with one (`_SOFT_SIGN_MONTHS`).
- Roman numerals: `is_roman_numeral(word, after, previous, following)` is
  true for a word of two letters or more that `_ROMAN_NUMERAL_RE` matches in
  full (1 to 3999, capitals). One letter is true only when `following`,
  lowercased and with its marks and 2026 input forms canonical, begins with
  a word of `_ROMAN_COUNTED` (the 1995 list and its 2026 forms, written by
  `latin_1995_word_to_2026`), or when `previous` begins with a capital, has
  two characters or more besides apostrophe marks, and `after` is not `.`.
  `convert` (`_roman_numeral`) looks up `previous` and `following` for one
  letter only, and passes them when one space or U+00A0 is all that
  separates them from it.
- Dates: `dates(text, target, crossed)` finds a number with no letter or
  digit before it and one separator after it (`_NUMBER_HYPHEN_RE` for
  Cyrillic, `_NUMBER_SPACE_RE` for Latin). If the word after it starts at
  an offset in `crossed` (a word read in the other script; with `crossed`
  left out, any word), it reads that word with `_WORD_RE`, lowercased, and
  changes the separator for a year (three or four digits and `йил…`; 1000
  to 2099 and `yil…`) or a day (`_DAYS` and `_CYRILLIC_MONTH_RE` or
  `_LATIN_MONTH_RE`). The word is lowercased rather than matched with
  `re.IGNORECASE`, so the JavaScript port reads it the same way. The JS
  port's offsets count UTF-16 units, as its `replace` callbacks do.

## Normalization

`normalize` runs these steps in order:

1. Empty or whitespace-only text gives `""`.
2. U+00B4 becomes U+02BC (`ʼ`); NFKC would make it a space and an accent.
3. NFKC, then lowercase.
4. If any character is in U+0400–U+052F, the words go through
   `cyrillic_word_to_latin_1995` with `map_words`, so the positional rules
   reach the key (`Чоршанбиев` gives `chorshanbiyev`). It is the 0.3.1
   reading: the word-final `ц` and the month names of 0.3.2 are
   `convert_cyrillic_word`'s, so `марганец` and `сентябрь` still give
   `marganets` and `sentyabr` here, while `convert` writes `marganes` and
   `sentabr`.
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

- `detect_script` (in `__init__.py`) composes the text (NFC) as `convert`
  does, then returns `cyrillic` if any character is in U+0400–U+052F, `latin_2026` if any character is in `_REFORM_LETTERS`
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
`tables.py`. `script_spans`, `homoglyph_spans`, `fold_homoglyphs`,
`segments` and `normalize_apostrophes` do not compose the text: their pieces
join to the input as it was.

## Checking

`validate(text, orthography)` reads `orthography` with `tags._orthography`
(`"auto"` is an error) and `protect` with `protect._settings`, then goes over
the pieces of text between the protected spans:

1. each run of `_INVISIBLE_RE` (the characters `strip_invisible` removes) is
   an `invisible` finding;
2. each character followed by one or more characters of Unicode category `M`
   is a `decomposed` finding if NFC changes the run;
3. each word of `_WORD_RE`, unless it is made of marks only, goes to
   `_check_word`, which returns the first row of the table in the README
   ("Check a text") that applies, or nothing. The row is chosen by
   `word_class` and by the characters of the word (the look-alikes of `ö`
   and `ğ`, the other forms of `ö` and `ş`, `sh`, `ch`, `sʼh`); the
   suggestion is `convert` of the word with `protect=False`. In 1995 text a
   word with a 2026 letter goes to `latin_2026` and back, so that an `sh`
   beside it stays `sh` (`Qashqadaryö` → `Qashqadaryoʻ`). For a Latin word
   that no earlier row takes but that its suggestion changes, `_check_word`
   compares the word in NFC (which may change its length) with the
   suggestion: it is `wrong-mark` if a changed character is `ʻ` or `ʼ`,
   `mark-form` if it is another form of a mark, and otherwise `decomposed`,
   for the whole word, because only NFC changes it (U+212A KELVIN SIGN). So
   the codes cover every Latin word that its suggestion changes.

The findings are sorted by `(start, end, code)`.

`migration_report` converts the text to `latin_2026` and back with the same
`protect`, takes `validate(text, "latin_1995")`, and goes over the words
again: it counts them and the ones that change, and adds `round-trip` for a
word without a finding that does not come back from `latin_2026` as it was,
and `separator` for one with `sʼh`.

Neither looks at the separator between the number and the word of a date.
`convert` keeps it within one script (0.3.2), so `1956 yil` in Latin text is
not a `validate` finding and the report's `result` has `1956 yil` too.

## Command line

`cli.main` parses the arguments with `argparse`. A command reads its
orthography arguments first, with `tags._orthography`, so that a bad one is
an error before standard input is read. It then reads the file, or
standard input, as bytes and decodes them as strict UTF-8, calls the library,
and writes the result encoded as UTF-8 to `sys.stdout.buffer`, so line ends
are not translated. The library's warnings are caught with
`warnings.catch_warnings` and written to standard error after the output. A
`ValueError` from the library, a file that cannot be read and input that is
not UTF-8 are `argparse` errors: exit code 2. For `validate` and `report`,
line and column are counted from the `\n` characters before each finding.

## Stability and compatibility

- The public API is the 33 names in `__all__` in `__init__.py`, and the
  command line as the README describes it.
- `golden/` holds the output of the public functions on 1226 fixed inputs,
  `inputs.json`, and of the tag functions on 57 tags and 6 names,
  `tag-inputs.json` (both append-only), one file per release
  (`golden-0.1.1.json`, `golden-0.2.0.json`, `golden-0.3.0.json`,
  `golden-0.3.1.json`, `golden-0.3.2.json`; when inputs are added, the files
  of earlier releases are made again from their tagged code with `--src`),
  and
  `SHA256SUMS`. From 0.3.0 the files have schema 2: 30 fields (listed in
  `fields()` in `tools/golden.py`; `convert` for all nine pairs, `segments`,
  `to_ascii`, `script_spans`, `fold_homoglyphs` and `validate` in the three
  orthographies among them),
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
- Checking and the command line: `test_checks.py` (`validate`, its codes on
  every golden input, `migration_report`), `test_cli.py` (each command in
  this process with `main(argv)`, exit codes, line ends, and
  `python -m akademtranslit --version` in a subprocess, with `PYTHONPATH` set
  to wherever the imported package is, `src/` or an installed wheel).
- Behaviour changes: `test_regressions.py` (0.1.1 fixes),
  `test_changes_0_2_0.py` (0.2.0 rule changes), `test_changes_0_3_0.py`
  (0.3.0: the other input forms of `ö` and `ş`, the Cyrillic range, language tags, the `e` and
  `ьо` rules, `ValueError` for a non-string orthography, case per letter
  unit, abbreviations with a suffix, s with comma below, word-level `auto`,
  decomposed letters), `test_changes_0_3_1.py` (0.3.1: the inputs on which
  protected spans took quadratic time, timed, and the new code against the
  0.3.0 code on random inputs), `test_changes_0_3_2.py` (0.3.2: Roman
  numerals, month names, dates and the word-final `ц`, each with its
  boundaries, the other direction, `source="auto"` and a protected span; the
  golden inputs added for them; and that `normalize` keeps its key).
- Contracts: `test_golden.py`, `test_public_api_compat.py`, `test_readme.py`
  (README examples, via doctest), `test_privacy.py` (no I/O in the library;
  the command-line tool imports only what it may and opens files only to
  read them).

## Build and release

- `pyproject.toml` builds with setuptools. The version is read from
  `akademtranslit.__version__`, the package is found under `src/`, `py.typed`
  ships with it, and there are no runtime dependencies. `[project.scripts]`
  installs the console script `akademtranslit`, which runs
  `akademtranslit.cli:main`. `MANIFEST.in` adds
  the changelog, `PRIVACY.md`, `docs/`, `tests/`, `golden/` and `tools/` to
  the sdist, and leaves `js/` out.
- `ci.yml` runs on pushes to `main` and on pull requests: the tests and the
  golden check on Ubuntu with Python 3.9 to 3.14 and on macOS and Windows
  with 3.14, the JavaScript port's tests on Node 24 after a check that its
  fixtures match the library (`js/tools/make-fixtures.py --check` on
  Python 3.12, the minor version that made them), and a build job that
  validates the classifiers, builds the sdist
  and wheel, runs `twine check --strict` and tests the wheel in Python 3.9.
- `release.yml` runs on `v*` tags. Its build job checks that the tag matches
  `__version__` and repeats the golden, classifier, build, `twine check` and
  wheel steps; it builds with `SOURCE_DATE_EPOCH` set to the time of the
  commit and writes the packages' SHA-256 to `SHA256SUMS-dist`, outside
  `dist/`. The publish job runs in the `pypi` environment and uploads
  `dist/` with PyPI Trusted Publishing, with no API token in the workflow; the
  workflow's header comment says that environment needs approval. A last job
  checks the packages against `SHA256SUMS-dist` and creates the GitHub
  release with notes from `CHANGELOG.md`, the packages, `SHA256SUMS-dist`,
  `inputs.json`, `golden-<version>.json` and `golden/SHA256SUMS`, which lists
  every golden file, not only those two (the README checks it with
  `--ignore-missing`). Run by hand, the workflow only builds.
- Actions are pinned to commit hashes, and both workflows default to
  read-only repository permissions.

## The JavaScript port

`js/` is a port of `src/akademtranslit/` to JavaScript, module by module, with
no dependencies. Like the library, it uses no network and stores nothing. Its
tests check it byte for byte against the same golden vectors, and against
fixtures that `js/tools/make-fixtures.py` makes from the library; see
[js/README.md](../js/README.md). `js/test/changes-0.3.2.test.js` has the
tables of `tests/test_changes_0_3_2.py`, and `js/test/readme.test.js` runs
the JavaScript examples of the README, as `test_readme.py` runs the Python
ones.
