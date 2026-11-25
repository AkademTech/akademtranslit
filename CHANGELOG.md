# Changelog

## 0.3.2 — 2026-11-25

### Changed

The output of `convert`, `to_latin` and `to_cyrillic` changes in four rules,
and `to_ascii` writes U+2011 as a hyphen. `RULES_VERSION` is `uz-2026-alphabet+project-2026.11.2`: the release that
changes the output is the second in November 2026, and from now on such a
release adds its number in the month.

- Roman numerals stay Latin in Cyrillic: converting `latin_1995` or
  `latin_2026` to Cyrillic keeps a word that is a well-formed Roman numeral
  in capitals, `XIX asr` → `XIX аср`, `IV bob` → `IV боб` (were `ХИХ аср`,
  `ИВ боб`). Two letters or more are a numeral wherever they stand. One
  `L`, `C`, `D` or `M` is a letter wherever it stands, as before:
  `D guruhida` → `Д гуруҳида`, `M harfi` → `М ҳарфи`. One `I`, `V` or `X`
  is most often the letter itself, so it is a numeral only in context:
  - before a word that begins with `asr`, `ming`, `bob`, `qism`, `jild`,
    `tom`, `sinf`, `kurs`, `boʻlim`, `guruh`, `chorak`, `bosqich`,
    `daraja`, `toifa`, `qurultoy`, `syezd`, `sessiya`, `chaqiriq`,
    `jahon`, `kvartal`, `semestr`, `smena`, `kitob`, `kategoriya`,
    `oʻrin`, `yarim`, `yarmi`, `xalqaro`, `respublika`, `konferensiya`,
    `kongress`, `anjuman` or `simpozium` (or the 2026 form of one:
    `bölim`, `çorak`, `bosqiç`, `çaqiriq`, `örin`), after one space,
    U+00A0, `-` or U+2011: `V asr` → `V аср`, `V-asr` → `V-аср`,
    `I jahon urushi` → `I жаҳон уруши`, `I Xalqaro ilmiy-amaliy
    konferensiya` → `I Халқаро илмий-амалий конференсия`;
  - after a word of two letters or more that begins with a capital, with
    one space or U+00A0 between and no full stop after: `Pyotr I` →
    `Пётр I`, `Nikolay I` → `Николай I`;
  - in a series with a numeral: two numerals or more linked by a hyphen or
    dash (U+002D, U+2010 to U+2014) with no space around it or with one
    space on each side, by a comma and one space, or by `va` or `yoki`,
    in any case, with one space on each side, of which one is a numeral
    on its own: `V–VI asrlar` → `V–VI асрлар`, `V – VI asrlar` →
    `V – VI асрлар`, `I, II va III boblar` → `I, II ва III боблар`,
    `I va II jahon urushlari` → `I ва II жаҳон урушлари`,
    `I VA II JAHON URUSHLARI` → `I ВА II ЖАҲОН УРУШЛАРИ` (were `В аср`,
    `И жаҳон уруши`, `Пётр И`, `В–ВИ асрлар`, `И, ИИ ва ИИИ боблар`). A
    dash before a word that is not a numeral links nothing:
    `X – nomaʼlum, V – tezlik` → `Х – номаълум, В – тезлик`.

  Before a word that begins with `harf` or `tovush` it is a letter even
  so, and after a series every member of one letter is a letter, while
  those of two letters or more stay numerals: `V harfi` → `В ҳарфи`,
  `Lotin V harfi` → `Лотин В ҳарфи`, `Ushbu V va X harflari` →
  `Ушбу В ва Х ҳарфлари`, `V, X va XV harflari` → `В, Х ва XV ҳарфлари`.
  Otherwise it is a letter, as before: `V` → `В`, `V va X` → `В ва Х`,
  `I. Boʻriyev` → `И. Бўриев`. Known limits: `Pyotr I.` and `Karl V.` at
  the end of a sentence are read as initials; any capitalised word before
  one letter makes it a numeral, the first of a sentence too,
  `Variant V` → `Вариант V`; a ruler's numeral linked by a comma to a
  letter before `harf` is read as a letter, `Nikolay I, V harfi` →
  `Николай И, В ҳарфи`.
- Dates: Cyrillic writes no hyphen after the number of a year or of a day of
  the month, as the 1956 spelling rules do, and Latin writes one:
  `1991-yilning 1-sentabri` → `1991 йилнинг 1 сентябри`,
  `1956 йил 22 сентябрь` → `1956-yil 22-sentabr` (were
  `1991-йилнинг 1-сентабри`, `1956 yil 22 sentyabr`). The separator changes
  only when the date changes script: the word after the number was read in
  Latin and the target is Cyrillic, or the other way round. Within one
  script — `latin_1995` ↔ `latin_2026`, or an orthography to itself — it is
  the author's and stays: `2026 yil` stays `2026 yil`, `1991-йил` stays
  `1991-йил`. With `source="auto"` each date goes by the script its word is
  read in. A year is three or four digits and a word in `йил…` to Cyrillic,
  1000 to 2099 and a word in `yil…` to Latin; a day is 1 to 31 and a month
  name. U+2011 NON-BREAKING HYPHEN and U+00A0 NO-BREAK SPACE take each
  other's place. Other ordinals keep the hyphen (`5-sinf`, `60-yillar`).
- Month names: Cyrillic `сентябр` and `октябр` are `sentabr` and `oktabr`,
  with any suffix: `Сентябрь` → `Sentabr`, `октябрнинг` → `oktabrning` (were
  `Sentyabr`, `oktyabrning`). From Latin, `sentabr` and `oktabr` are
  `сентябр` and `октябр`, and a month name standing alone gets its `ь`:
  `iyun` → `июнь`, `sentabr` → `сентябрь` (were `июн`, `сентабр`).
- A word-final `ц` is `s` from Cyrillic to Latin, and so is a `ц` followed
  by Uzbek suffixes only: `марганец` → `marganes`, `шприц` → `shpris`,
  `ненецлар` → `neneslar`, `шприцни` → `shprisni` (were `marganets`,
  `shprits`, `nenetslar`, `shpritsni`). Surnames too: `Кац` → `Kas`, `Швец`
  → `Şves`. Latin to Cyrillic does not change: `marganes` → `марганес`.
- `to_ascii` writes U+2011 NON-BREAKING HYPHEN as `-`. It removed it before,
  with the other characters that are not ASCII, so a date that Latin writes
  with it ran together: `1956` U+00A0 `йил 22` U+00A0 `сентябрь` →
  `1956-yil 22-sentabr` (was `1956yil 22sentabr`). U+00A0 is a space, as
  before.

`to_ascii`, `migration_report` and the suggestions of `validate` follow
`convert`. `migration_report` converts within the Latin script, so it keeps
a date's separator, as `validate` does. `normalize` does not
change, as in every patch release: it reads
`марганец` and `сентябрь` as before (`marganets`, `sentyabr`), so their
keys are not the keys of the new Latin spellings. The same holds for
`rules.cyrillic_word_to_latin_1995`, which code outside the library builds
keys with; `convert` reads Cyrillic with the new
`rules.convert_cyrillic_word`.

### Output changes

Golden diff 0.3.1 → 0.3.2, on 1256 inputs (68 added in 0.3.2):
`to_cyrillic` 36, `to_latin_1995` 11, `to_latin_2026` 11, `to_ascii` 12,
`validate_latin_1995` 9, `validate_latin_2026` 9, and `convert` from
Cyrillic to `latin_1995` and `latin_2026` 14 each and from `latin_1995`
and `latin_2026` to Cyrillic 43 each. `convert` within one script —
Cyrillic to Cyrillic and among the Latin orthographies — changes nothing.
On the 1188 inputs that 0.3.1 had, 6 change, each only where it changes
script:

- Roman numerals: 2 — `XXI asr` and `XXI аср`, in the Cyrillic fields;
- dates: 3 — `ilmiy jurnal 2026 yil 12 son` read as Cyrillic and
  converted to Latin, `Ilmiy jurnal, 2026-yil, 12-son` converted to
  Cyrillic, and `Тошкент давлат университети, 2026-йил` read as Latin and
  converted to Cyrillic;
- month names: 1 — `iyun`;
- word-final `ц`: none.

The 68 new inputs cover each rule and its limits; 48 of them convert
differently from 0.3.1. `normalize`, the `sort_key` fields,
`normalize_apostrophes`, `segments`, `script_spans`, `fold_homoglyphs` and
the other fields are unchanged. The golden files of 0.1.1, 0.2.0, 0.3.0 and
0.3.1 are made again from their tags with the new inputs; their results on
the earlier inputs are unchanged.

### Documentation

- README and `cldr/README.md`: IANA added the variant subtags `1995` and
  `2026` to the Language Subtag Registry on 18 November 2026. Tags that use
  them are valid BCP 47.
- `CONTRIBUTING.md`: contributions are accepted under the MIT license, the
  project's license.
- README: dates and month names, Roman numerals, the `ц` rule as a table,
  the rules version with a number in the month, their known limits, and
  that `normalize` keeps its key. `docs/architecture.md`: where the rules
  for whole words and the date step run.

### Development

- The JavaScript port's Unicode fixture records only the minor version of
  the Python that made it (`3.12`, not `3.12.13`). CI checks the fixtures on
  any Python 3.12.x.
- `tests/test_changes_0_3_2.py` and `js/test/changes-0.3.2.test.js` pin the
  four rules and `to_ascii`'s U+2011; `js/test/readme.test.js` runs the
  README's JavaScript examples. The JS fixtures are named for 0.3.2 and
  have six more trap inputs, for the new rules; `.gitleaks.toml` names the
  renamed trap fixture.

## 0.3.1 — 2026-11-18

### Fixed

- Protected spans: a URL, a DOI or a file path followed by a very long run of
  closing brackets took time quadratic in the run (the known issue of 0.3.0).
  It now takes linear time. The output is unchanged.
- Protected spans: `%` followed by a very long run of zeros (`%000…0!`) took
  time quadratic in the run. It now takes linear time. The output is
  unchanged.
- Protected spans: a very long run of dot-separated labels with no ending of
  a bare domain (`a.a.a…`) took time quadratic in the run. It now takes
  linear time. The output is unchanged.
- Protected spans: a very long word of letters joined by apostrophes
  (`a'a'a'…`) took time quadratic in its length. It now takes linear time.
  The output is unchanged.

### Added

- `js/`: the JavaScript port (ES modules, no dependencies, Node and
  browsers). It reproduces the golden vectors byte for byte. It is not on
  npm.

### Release

- The GitHub release also has `SHA256SUMS-dist`, the SHA-256 of the wheel and
  the sdist; `SHA256SUMS` keeps the hashes of the golden files.
- The wheel is built with `SOURCE_DATE_EPOCH` set to the time of the tagged
  commit, so that it can be built again from the tag; the README says how.

## 0.3.0 — 2026-11-18

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
- README and `docs/architecture.md`: the command line (its commands,
  options, exit codes and output formats) is public interface and falls
  under semantic versioning.
- README and `cldr/README.md`: the variant subtags `1995` and `2026` were
  approved by the Language Subtag Reviewer on 18 November 2026; IANA has yet
  to add them to the Language Subtag Registry.

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

### Known issues

- Protected spans: a URL, DOI or file path followed by a very long run of
  closing brackets (tens of thousands) takes time quadratic in the run.
  Output is unaffected. Fixed in the next release.

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
