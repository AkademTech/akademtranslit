# akademtranslit for JavaScript

The JavaScript port of [akademtranslit](../README.md), the Python library for
Uzbek in its three orthographies: Cyrillic, the 1995 Latin alphabet and the
2026 Latin alphabet (Law No. O'RQ-1184). ES modules, no dependencies, the same
files in Node and in a browser.

Version 0.3.2, the same as the Python library. Not on npm: `"private": true`
until a decision to publish.

## What is measured

Every number below is the output of a test in this directory, run on Node
24.16 against the Python library at the same commit.

| Check | Result |
| --- | --- |
| `golden/golden-0.3.2.json`, every input and field (`test/golden.test.js`) | 37,680 / 37,680 values (30 fields x 1,256 inputs) |
| the same file, `tags` and `scripts` sections | 57 / 57 and 6 / 6 |
| `migrationReport`, with and without `protect`, on every golden input (`test/migration.test.js`) | 2,512 / 2,512 |
| calls the golden file does not make (`protect: false`, terms, the strip options, `homoglyphSpans`) on every golden input | 15,072 / 15,072 |
| 52 inputs made for the places where JavaScript differs from Python, through all of the above, and 42 calls that raise | all equal |
| `str.isalpha`, `isupper`, `isspace`, `re`'s `\w`, `\d`, `\s`, case mappings, NFC, NFKC, NFKD, on all 1,114,112 code points (`test/traps.test.js`) | equal wherever Python 3.12's Unicode 15.0 has a character, except the case of four letters (see below) |
| the four kinds of input on which 0.3.0 took quadratic time: the new code against the 0.3.0 code on 20,000 random inputs each, and six long inputs timed (`test/linear.test.js`) | the same results; each long input under 1 s |
| the rules of 0.3.2 (Roman numerals, month names, dates, a word-final ц, `toAscii` and U+2011), with the tables of `tests/test_changes_0_3_2.py` (`test/changes-0.3.2.test.js`) | all equal |
| the JavaScript examples in the library's README (`test/readme.test.js`) | all give what the README says |

The golden test compares values as JSON: a Python tuple is an array, `None`
is `null`, and order counts. The golden files are checked against
`golden/SHA256SUMS` first.

## Use

The port is not published to npm, so it is used from a clone of the
repository. The module is `js/src/index.js`, and it needs nothing else:

```sh
git clone https://github.com/AkademTech/akademtranslit.git
```

```js
// from a script next to the clone; any path to js/src/index.js will do
import { convert, normalize, toCyrillic, toLatin, validate } from "./akademtranslit/js/src/index.js";

toLatin("Тошкент давлат университети");               // "Toşkent davlat universiteti"
toLatin("Тошкент давлат университети", "latin_1995"); // "Toshkent davlat universiteti"
toCyrillic("Oʻzbekiston Respublikasi");                // "Ўзбекистон Республикаси"
convert("Gʻafurov", "latin_1995", "latin_2026");       // "Ğafurov"
normalize("Şoşimova") === normalize("Шошимова");      // true

convert("Manba: https://shahar.uz", "auto", "cyrillic");           // "Манба: https://shahar.uz"
convert("https://shahar.uz", "auto", "cyrillic", { protect: false }); // "ҳттпс://шаҳар.уз"

validate("Toshkent shahri", "latin_2026");
// [[0, 8, "digraph", "Toşkent"], [9, 15, "digraph", "şahri"]]
```

In a browser, serve `js/src/` with the page and import the same file from a
module script or a module Worker (see "Browsers" below).

What each function does is documented once, in the Python library's
docstrings and its [README](../README.md); the port does the same.

## The API, from Python

The exports are Python's `__all__`, and nothing else (`test/api.test.js`):

- functions in camelCase: `convert`, `toCyrillic`, `toLatin`, `toAscii`,
  `normalize`, `normalizeApostrophes`, `detectScript`, `scriptClass`,
  `scriptSpans`, `segments`, `isCyrillic`, `cyrillicLanguage`,
  `foldCyrillic`, `foldHomoglyphs`, `homoglyphSpans`, `sortKey`,
  `validate`, `migrationReport`, `scriptForTag`, `tagForScript`;
- constants as they are: `RULES_VERSION`, `CYRILLIC`, `LATIN_1995`,
  `LATIN_2026`, `SCRIPTS`, the three `*_ALPHABET`s, `TURNED_COMMA`, `TUTUQ`,
  `REFORM_PAIRS`, and `Protect`; `__version__` is `VERSION`.

Positional arguments come in Python's order, with Python's defaults.
Python's keyword-only arguments go in a last options object, in camelCase:

```js
convert(text, source = "auto", target = "latin_2026", { protect = true } = {})
toLatin(text, variant = "latin_2026", { protect })
toCyrillic(text, { protect })
normalizeApostrophes(text, style = "unicode", { stripInvisible = false, stripStress = false })
validate(text, orthography, { protect })
migrationReport(text, { protect })
segments(text, protect = true)          // positional, as in Python
sortKey(text, orthography)              // orthography is required
new Protect({ urls, emails, dois, placeholders, markup, paths, tokens, terms })
```

Values are Python's: `"cyrillic"`, `"latin_1995"`, `"latin_2026"`, `"auto"`,
and BCP 47 tags such as `"uz-Cyrl"` and `"uz-Latn-2026"`.

### Errors

| Python | JavaScript |
| --- | --- |
| `ValueError` | `RangeError` |
| `TypeError` | `TypeError` |

The port also throws `TypeError` for text that is not a string, for an
unknown option and for options that are not an object (Python: an unexpected
keyword argument), and for a missing required argument. The same table is in
`src/index.d.ts`.

### Where the result has another shape

- `scriptForTag(tag)` returns `{ script, warning }`. Python returns the
  orthography and emits a `FutureWarning` for `"uz"` and `"uz-Latn"`; here
  `warning` is `"FutureWarning"` for those and `null` otherwise, and nothing
  is written to the console. This is the shape the golden file records. The
  functions that take an orthography read those two tags silently.
- `migrationReport()` returns an object with Python's keys in Python's order:
  `words`, `changed`, `protected`, `round_trip`, `rules_version`, `check`,
  `result`.
- `sortKey()` returns `[weights, text]`, arrays for Python's tuples. To sort,
  compare the weights element by element (a prefix first), then the text.
- `Protect` is built with `new` and compared with `equals()`; it is frozen.
- Indices (`validate`, `homoglyphSpans`, `migrationReport().check`) count
  code points, as Python's do: in `"😀 Toshkent"` the word starts at 2, not 3.

## Unicode versions

Python 3.12 uses Unicode 15.0; Node 24.16 uses Unicode 17.0 (ICU 78.3). The
port does not pin either. Measured over every code point, the two disagree
only on code points that Unicode 15.0 leaves unassigned, and on the case of
four letters that got a capital later: ƛ U+019B, ɤ U+0264, ꟓ U+A7D3 and ꟕ
U+A7D5 (`toUpperCase()` gives a capital; Python 3.12 does not).

`src/unicode.js` holds Python's character classes as JavaScript sees them
(`re`'s `\w` is `[\p{L}\p{N}_]`, its `[^\W\d_]` is `[\p{L}\p{Nl}\p{No}]`,
`str.isspace()` is 29 code points, `re.IGNORECASE` also matches `İ ı ſ K`),
each with a comment and a test.

## Browsers

`src/` has only relative `.js` imports and no Node built-ins
(`test/api.test.js` checks it), so it runs as is in a module Worker. It needs
RegExp lookbehind and `\p{…}`, `String.prototype.replaceAll` and `??`:
Chrome 85, Firefox 78, Safari 16.4 or later.

## Speed

`convert` from Cyrillic to `latin_2026`, median of three runs on an Apple
Silicon Mac, Node 24.16 and Python 3.12.13, on the same text:

| Characters | JavaScript | Python |
| ---: | ---: | ---: |
| 10,000 | 0.015 s | 0.009 s |
| 100,000 | 0.060 s | 0.080 s |
| 1,000,000 | 0.544 s | 0.846 s |

## Tests

```sh
node --test test/             # in js/; npm test runs the same
```

The fixtures in `test/fixtures/` are made from the Python library, never by
hand:

```sh
.venv/bin/python js/tools/make-fixtures.py           # from the repository root
.venv/bin/python js/tools/make-fixtures.py --check
```

CI runs the check before the tests, with Python 3.12 (any 3.12.x).
`unicode-15.0.0.json` records the minor version of the Python that made it,
3.12, whose Unicode data the fixtures depend on: make the fixtures with a
3.12.x, or change the version in `.github/workflows/ci.yml` with them.

## License

MIT, as the Python library; see [LICENSE](LICENSE).
