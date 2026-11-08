# AkademTranslit

Uzbek transliteration across three orthographies — Cyrillic, the 1995 Latin
alphabet, and the 2026 Latin alphabet — plus a normalization key that makes one
word searchable across all three, and alphabetical sorting in each.

Pure Python, standard library only, no dependencies.

```python
>>> from akademtranslit import to_latin, to_cyrillic, convert, normalize
>>> to_latin("Тошкент давлат университети")
'Toşkent davlat universiteti'
>>> to_latin("Тошкент давлат университети", variant="latin_1995")
'Toshkent davlat universiteti'
>>> to_cyrillic("Oʻzbekiston Respublikasi")
'Ўзбекистон Республикаси'
>>> normalize("Şoşimova") == normalize("Shoshimova") == normalize("Шошимова")
True

```

## Why

Uzbek is written three ways at once, and will be for years.

Cyrillic carries the archives, the older scholarly record and a large share of
the press. The Latin alphabet adopted in 1993 and revised in 1995 carries
official documents and most of the web; it writes four sounds with digraphs and
modifier marks — `sh`, `ch`, `gʻ`, `oʻ`. The 2026 alphabet, set by Law No.
O'RQ-1184 (signed 21 October 2026, in force from 22 April 2027), replaces those
four with single letters — `ş`, `ç`, `ğ`, `ö` — giving 28 letters plus the
tutuq belgisi.

For a reader this is an inconvenience. For a search index it is a correctness
problem: the same author, journal or institution arrives spelled three
different ways in three different records, and string equality finds none of
the matches. `Шошимова`, `Shoshimova` and `Şoşimova` are one person.

This library does separate jobs, and keeping them separate is the point:

- **Transliteration** (`to_latin`, `to_cyrillic`, `convert`) — display-grade,
  preserves case and punctuation. Use it to show text to people and to migrate
  a corpus from one alphabet to another.
- **Normalization** (`normalize`) — deliberately lossy, produces a match key
  nobody should ever display. Use it for search, deduplication and equality.
- **Sorting** (`sort_key`) — the alphabetical order of each orthography, which
  code-point order gets wrong in all three.

## Install

```bash
pip install akademtranslit
```

Requires Python 3.9 or newer. No dependencies.

## Usage

### Convert between the three orthographies

```python
>>> from akademtranslit import convert
>>> convert("Тошкент", source="cyrillic", target="latin_2026")
'Toşkent'
>>> convert("Toshkent", source="latin_1995", target="latin_2026")
'Toşkent'
>>> convert("Toşkent", source="latin_2026", target="cyrillic")
'Тошкент'

```

`source` defaults to `"auto"`, which runs script detection first, and `target`
defaults to `"latin_2026"`.

### Migrate an existing corpus to the 2026 alphabet

The 1995 ↔ 2026 conversion is lossless in both directions, so a migration can
be verified and, if needed, reversed.

```python
>>> old = "Mirzo Ulugʻbek nomidagi Oʻzbekiston Milliy universiteti"
>>> new = convert(old, source="latin_1995", target="latin_2026")
>>> new
'Mirzo Uluğbek nomidagi Özbekiston Milliy universiteti'
>>> convert(new, source="latin_2026", target="latin_1995") == old
True

```

### Build a cross-script search key

```python
>>> from akademtranslit import normalize
>>> index = {}
>>> for record in ["Şoşimova N.", "Shoshimova N.", "Шошимова Н."]:
...     index.setdefault(normalize(record), []).append(record)
>>> index
{'shoshimova n': ['Şoşimova N.', 'Shoshimova N.', 'Шошимова Н.']}

```

`normalize` is idempotent and folds orthography, case, punctuation and every
apostrophe style in use: all eight accepted marks (see below) give the same
key, so `o'zbek`, `o’zbek`, `o´zbek` and `oʻzbek` all match.

### Sort in alphabetical order

`sort_key(text, orthography)` sorts by the alphabet of the orthography you
name. It has to be named — there is no detection — because the same string
sorts differently in different orthographies.

```python
>>> from akademtranslit import sort_key
>>> sorted(["tabiat", "çaqmoq", "sabr", "şahar"], key=lambda w: sort_key(w, "latin_2026"))
['sabr', 'şahar', 'çaqmoq', 'tabiat']
>>> sorted(["choy", "shamol", "zarar", "oʻrik", "gʻoz"], key=lambda w: sort_key(w, "latin_1995"))
['zarar', 'oʻrik', 'gʻoz', 'shamol', 'choy']
>>> sorted(["ҳаво", "ғоз", "ялпиз", "қовун", "ўрик"], key=lambda w: sort_key(w, "cyrillic"))
['ялпиз', 'ўрик', 'қовун', 'ғоз', 'ҳаво']

```

In `latin_1995`, `oʻ`, `gʻ`, `sh` and `ch` are single letters after `z`, while
a separated `sʼh` is two: `Isʼhoq` sorts before `Ishonch`. Whitespace sorts
before digits, digits before letters, and letters outside the alphabet after
it; punctuation and the tutuq belgisi are not counted. When two keys tie on
letters, the text itself decides, so the order is total.

### Put the apostrophes in one form

```python
>>> from akademtranslit import normalize_apostrophes
>>> normalize_apostrophes("O'zbekiston, ma'no, bog'")
'Oʻzbekiston, maʼno, bogʻ'
>>> normalize_apostrophes("Oʻzbekiston, maʼno", style="ascii")
"O'zbekiston, ma'no"

```

Only marks inside Latin words change; quotes around a word, digits,
punctuation and words with a Cyrillic letter are left as they are. It does not
convert anything, so it is safe on text whose orthography is unknown.

### Detect what you were handed

```python
>>> from akademtranslit import detect_script, script_class, cyrillic_language
>>> detect_script("Самарқанд"), detect_script("Oʻzbekiston"), detect_script("Özbekiston")
('cyrillic', 'latin_1995', 'latin_2026')
>>> script_class("Тошкент"), script_class("Toshkent"), script_class("Tоshkent")
('cyrillic', 'latin', 'mixed')
>>> cyrillic_language("Ўзбекистон"), cyrillic_language("Мы здесь"), cyrillic_language("бир")
('uz', 'ru', 'unknown')

```

`detect_script` names an orthography. `script_class` answers a narrower
question with a closed set — `latin`, `cyrillic` or `mixed` — and is the one to
use for catching homoglyphs: the `о` in the third example is Cyrillic.
`cyrillic_language` tells Uzbek Cyrillic from Russian by the letters only one
of them has (`ў қ ғ ҳ` against `щ ы`); it is a routing heuristic, not a
language identifier, and short text is often `unknown`.

## Supported orthographies

The three alphabets, in their alphabetical order, are exposed as
`LATIN_2026_ALPHABET`, `LATIN_1995_ALPHABET` and `CYRILLIC_ALPHABET`:

| Orthography | Letters, in order |
| --- | --- |
| `latin_2026` (28) | A B D E F G Ğ H I J K L M N O Ö P Q R S Ş Ç T U V X Y Z |
| `latin_1995` (28) | A B D E F G H I J K L M N O P Q R S T U V X Y Z Oʻ Gʻ Sh Ch |
| `cyrillic` (35) | А Б В Г Д Е Ё Ж З И Й К Л М Н О П Р С Т У Ф Х Ц Ч Ш Ъ Ь Э Ю Я Ў Қ Ғ Ҳ |

The tutuq belgisi `ʼ` belongs to both Latin alphabets but is not a letter: it
is a separate sign, `TUTUQ`, and is in neither list.

| Sound | `cyrillic` | `latin_1995` | `latin_2026` |
| --- | --- | --- | --- |
| /ʃ/ | ш | sh | **ş** |
| /tʃ/ | ч | ch | **ç** |
| /ʁ/ | ғ | gʻ | **ğ** |
| /oʻ/ | ў | oʻ | **ö** |
| /q/ | қ | q | q |
| /h/ | ҳ | h | h |
| /x/ | х | x | x |
| /dʒ/ | ж | j | j |
| glottal stop | ъ | ʼ | ʼ |

Only the four bolded rows differ between the two Latin alphabets. Everything
else is shared, which is why `latin_1995` serves as the pivot for every
conversion.

### Context-dependent rules

Five readings depend on position rather than on the letter alone:

| Rule | Example |
| --- | --- |
| `е` is `ye` word-initially and after a vowel, `e` otherwise | Ер → Yer, поезд → poyezd, тезда → tezda |
| `ц` is `ts` after a vowel, `s` otherwise | милиция → militsiya, функция → funksiya, цирк → sirk |
| `ts` is `т` + `с` before an Uzbek suffix, `т` + `ш` before `h`, `ц` otherwise — a heuristic, see below | ketsa → кетса, hayotsiz → ҳаётсиз, adabiyotshunos → адабиётшунос, operatsiya → операция |
| `с` before `ҳ` takes a separator in `latin_1995` | Исҳоқ → Isʼhoq (not `Ishoq`) |
| `ъ` is dropped after a consonant before `е ё ю я` and after `ў`, `ʼ` otherwise | объект → obyekt, мўъжиза → moʻjiza, маъно → maʼno |

The separator needs a note. In `latin_1995`, `sh` is a digraph, so a genuine
s+h sequence has to be separated with the tutuq belgisi or it reads as `ш`. The
2026 alphabet does not need the separator, because `ş` carries that sound —
`Isʼhoq` becomes simply `Ishoq`, while `ish` (work) becomes `iş`. The pair
survives the round trip in both directions.

The `ts` rule needs a note of its own. In loanwords `ts` is the letter `ц`;
where a stem ending in `t` meets a suffix beginning with `s` it is two letters:
`ketsa` (if he goes) is кетса, not кеца. There is no dictionary, only a short
list of loanwords, so the reading comes from the shape of the word. The checks
run in order and the first that applies wins:

- the `s` starts `sh` → `т` + `ш`: adabiyotshunos → адабиётшунос;
- the word starts with `ts` → `ц`: tsement → цемент;
- `i` and then a vowel or `y` follow → `ц`: operatsiya → операция, ratsion →
  рацион;
- a loanword whose tail would pass for suffixes → `ц`. The list: names in
  `-mitsin`, `-rubitsin`, `-floksatsin` and `-leytsin`, plus `glitsin`,
  `oksitotsin`, `rifampitsin`, `amikatsin` and `aktsiz`; and words beginning
  with one of the `-ица` stems `tablits`, `teplits`, `stolits`, `ulits`,
  `bolnits`, `granits`, `gostinits` (`TS_LOANWORD_STEMS` in `tables.py`).
  Inflected forms count too: levofloksatsinni → левофлоксацинни, tablitsada →
  таблицада. The list exists to split `ts`; it is not a dictionary and is not
  meant to grow. Uzbek words with the same endings keep `т` + `с` — bitsa,
  bitsin, oʻqitsa, koʻrsatsin, and nouns in `-kt` with `-siz` such as
  kontaktsiz;
- the rest of the word is Uzbek suffixes → `т` + `с`. The `s` must open one of
  `-sa`, `-sak`, `-sam`, `-sang`, `-sangiz`, `-salar`, `-sin`, `-sinlar`,
  `-siz`, `-sizlik` or `-sevar`, and anything after it must be further suffixes
  or particles (`-lik`, `-lar`, `-ga`, `-da`, `-ni`, `-man`, `-mi`, `-gina`,
  `-yu`, `-ku`, `-yoq`, `-mikan`, …): ketsinmi → кетсинми, hayotsizlik →
  ҳаётсизлик, aytsangizgina → айтсангизгина. Starting with the right letters is
  not enough, so meditsina (`sin` + `a`) and natsizm (`siz` + `m`) keep `ц`;
- otherwise `ц`: leykotsit → лейкоцит, protsent → процент.

The known misses:

- A loanword off that list whose tail looks like a suffix gets `т` + `с`:
  karbetotsin → карбетотсин (карбетоцин). oksitotsin, rifampitsin and the
  `-rubitsin` names had this problem in 0.1.1 and are on the list since 0.2.0.
- A stem on the list also takes a native ending: granitsiz (granite + `-siz`)
  → границиз, not гранитсиз.
- An Uzbek word whose `t` + `s` boundary is not in the list keeps `ц`:
  compounds such as oʻtsoʻndirgich → ўцўндиргич (ўтсўндиргич) and
  soatsoz → соацоз (соатсоз), and suffixes such as `-simon` (otsimon → оцимон).
- pitsa and nitsa are wrong either way: питса and нитса now, пица and ница
  before 0.1.1, пицца and Ницца in fact.

### The two modifier marks

`ʻ` (U+02BB, turned comma) is part of the letters `oʻ` and `gʻ`. `ʼ` (U+02BC,
modifier apostrophe) is the tutuq belgisi. Most people type both as a plain
`'`, so the library recovers the distinction from context: after `o` or `g` the
mark is a turned comma, elsewhere it is the tutuq belgisi.

Input accepts eight characters for either mark: `ʻ` U+02BB, `ʼ` U+02BC, `’`
U+2019, `‘` U+2018, `´` U+00B4, `ʹ` U+02B9, `'` U+0027 and `` ` `` U+0060.
Conversion always emits the canonical two, which makes it idempotent and its
output safe to store; `normalize_apostrophes` does the same without converting,
or writes `'` for both with `style="ascii"`. `normalize` drops all eight, so the
mark a word was typed with never changes its key (since 0.2.0 this includes
`´`, which Unicode normalization used to turn into a space).

## Guarantees, and their limits

**Lossless.** `latin_1995` ↔ `latin_2026` round-trips exactly for text in
canonical form: marks written as `ʻ` and `ʼ`, and each word in lower case,
with an initial capital, or in all caps (`OʻZBEKISTON` included). Other input
comes back canonicalised — `o'zbek` as `oʻzbek`, `McDonald` as `Mcdonald`.
Cyrillic → Latin → Cyrillic round-trips exactly over the native Uzbek letter
inventory, with two gaps: `т` followed by `с` comes back as `ц` unless the `s`
starts a suffix the `ts` rule knows (`ўтсўндиргич`, `соатсоз`; see
Context-dependent rules), and `ъ` after `ў` does not come back (`мўъжиза` →
`moʻjiza` → `мўжиза`). Both are enforced by the test suite.

**Known lossy mappings.** Four Cyrillic letters occur only in Russian
loanwords, and folding them is deliberate; `ъ` is dropped where the 1995
spelling drops it:

| Letter | Behaviour | Reason |
| --- | --- | --- |
| щ | merges with ш → `sh` | no distinct sound in Uzbek |
| ы | merges with и → `i` | no distinct sound in Uzbek |
| ь | dropped | not represented in either Latin alphabet |
| ц | positional `ts`/`s`, not reversible | a heuristic; loanword spelling is genuinely inconsistent |
| ъ | dropped after a consonant before `е ё ю я` and after `ў` (`объект` → `obyekt`, `мўъжиза` → `moʻjiza`), `ʼ` elsewhere; not reversible | the 1995 spelling writes no mark there, so the Latin side has nothing to restore it from |

**Script detection is a heuristic.** A `latin_2026` string containing none of
the four reformed letters is indistinguishable from a `latin_1995` one. That is
harmless for nearly every word — the two orthographies write them identically —
but not for a separated s+h: `Ishoq` is Исҳоқ in `latin_2026` and Ишоқ in
`latin_1995`. Pass `source` explicitly when the orthography is known from
context.

**Out of scope.** `normalize` folds orthography, not romanization choice. It
does not treat `Xomidov` and `Khomidov`, or `Jasur` and `Zhasur`, as the same
string — those are different transcription conventions, and collapsing them
would merge names belonging to different people. Handle them upstream as scored
candidates. Translation matching and fuzzy or edit-distance matching are
likewise out of scope.

**A note on `ö`.** Law No. O'RQ-1184 writes the letter as `ö`, and that is
what this library emits. Earlier drafts of the reform used `ō` (o with macron)
or `ǒ`; both are accepted on input as aliases of `ö`, so text written under a
draft reads correctly, but they are never output.

## Golden vectors

`golden/` holds the library's output, sealed:

- `inputs.json` — the inputs: every letter of the three alphabets, the context
  rules, every apostrophe form, mixed content, ecosystem traps. Append-only: an
  `id` never changes and is never reused.
- `golden-<version>.json` — the output of every public function on every input,
  for that release.
- `SHA256SUMS` — the hashes of those files.

Check them with:

```bash
cd golden
shasum -a 256 -c SHA256SUMS    # or: sha256sum -c SHA256SUMS
```

The files are the shared reference for code that switches to this library and
for the ports to other languages (JavaScript, PHP): a port is correct when it
reproduces `golden-<version>.json` byte for byte. `python tools/golden.py
--check` regenerates the file from the source and compares;
`python tools/golden.py --diff OLD NEW` lists every output that changed between
two releases.

## Versioning

[Semantic versioning](https://semver.org). The output of `normalize()` never
changes in a patch release (0.y.Z): search indexes are built on it. Every
change to any output is listed in [CHANGELOG.md](CHANGELOG.md) with its golden
diff.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/python -m pytest
```

Or with [uv](https://docs.astral.sh/uv/): `uv run --with pytest -- python -m
pytest`.

The suite covers the alphabet letter by letter in both directions, the context
rules, the round-trip tiers above, casing (including ALL-CAPS, where `ШОШИМОВА`
must give `ŞOŞIMOVA` and not `Şoşimova`, and `OʻZBEKISTON` must give
`ЎЗБЕКИСТОН`), the cross-script normalization contract, sorting, and the
golden vectors. The examples in this README and in the docstrings run as tests.
`tests/test_regressions.py` and `tests/test_changes_0_2_0.py` pin every
behaviour change since 0.1.0; see [CHANGELOG.md](CHANGELOG.md).

## Security

See [SECURITY.md](SECURITY.md). The library does not use the network and
stores nothing.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). This project follows a
[code of conduct](CODE_OF_CONDUCT.md).

## License

MIT — see [LICENSE](LICENSE).

## Who

Built by [AkademTech](https://akademtech.org).
