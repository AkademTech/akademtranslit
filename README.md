# AkademTranslit

Uzbek transliteration across three orthographies — Cyrillic, the 1995 Latin
alphabet, and the 2026 reform — plus a normalization key that makes one word
searchable across all three.

Pure Python, standard library only, no dependencies.

```python
from akademtranslit import to_latin, to_cyrillic, convert, normalize

to_latin("Тошкент давлат университети")
# 'Toşkent davlat universiteti'

to_latin("Тошкент давлат университети", variant="latin_1995")
# 'Toshkent davlat universiteti'

to_cyrillic("Oʻzbekiston Respublikasi")
# 'Ўзбекистон Республикаси'

normalize("Şoşimova") == normalize("Shoshimova") == normalize("Шошимова")
# True
```

## Why

Uzbek is written three ways at once, and will be for years.

Cyrillic carries the archives, the older scholarly record and a large share of
the press. The Latin alphabet adopted in 1993 and revised in 1995 carries
official documents and most of the web; it writes four sounds with digraphs and
modifier marks — `sh`, `ch`, `gʻ`, `oʻ`. The 2026 reform replaces those four
with single letters — `ş`, `ç`, `ğ`, `ö` — giving 28 letters plus the tutuq
belgisi.

For a reader this is an inconvenience. For a search index it is a correctness
problem: the same author, journal or institution arrives spelled three
different ways in three different records, and string equality finds none of
the matches. `Шошимова`, `Shoshimova` and `Şoşimova` are one person.

This library does two separate jobs, and keeping them separate is the point:

- **Transliteration** (`to_latin`, `to_cyrillic`, `convert`) — reversible,
  display-grade, preserves case and punctuation. Use it to show text to people
  and to migrate a corpus from one alphabet to another.
- **Normalization** (`normalize`) — deliberately lossy, produces a match key
  nobody should ever display. Use it for search, deduplication and equality.

## Install

```bash
pip install akademtranslit
```

Or from a clone:

```bash
git clone https://github.com/akademtech/akademtranslit
cd akademtranslit
pip install -e .
```

Requires Python 3.9 or newer.

## Usage

### Convert between the three orthographies

```python
from akademtranslit import convert

convert("Тошкент", source="cyrillic", target="latin_2026")   # 'Toşkent'
convert("Toshkent", source="latin_1995", target="latin_2026") # 'Toşkent'
convert("Toşkent", source="latin_2026", target="cyrillic")    # 'Тошкент'
```

`source` defaults to `"auto"`, which runs script detection first, and `target`
defaults to `"latin_2026"`.

### Migrate an existing corpus to the reformed alphabet

The 1995 ↔ 2026 conversion is lossless in both directions, so a migration can
be verified and, if needed, reversed.

```python
old = "Mirzo Ulugʻbek nomidagi Oʻzbekiston Milliy universiteti"
new = convert(old, source="latin_1995", target="latin_2026")
# 'Mirzo Uluğbek nomidagi Özbekiston Milliy universiteti'

convert(new, source="latin_2026", target="latin_1995") == old
# True
```

### Build a cross-script search key

```python
from akademtranslit import normalize

index = {}
for record in ["Şoşimova N.", "Shoshimova N.", "Шошимова Н."]:
    index.setdefault(normalize(record), []).append(record)

# {'shoshimova n': ['Şoşimova N.', 'Shoshimova N.', 'Шошимова Н.']}
```

`normalize` is idempotent and folds orthography, case, punctuation and every
apostrophe style in use.

### Detect what you were handed

```python
from akademtranslit import detect_script

detect_script("Самарқанд")   # 'cyrillic'
detect_script("Oʻzbekiston") # 'latin_1995'
detect_script("Özbekiston")  # 'latin_2026'
```

## Supported orthographies

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

Only the four bolded rows change in the reform. Everything else is shared
between the two Latin orthographies, which is why `latin_1995` serves as the
pivot for every conversion.

### Context-dependent rules

Four readings depend on position rather than on the letter alone:

| Rule | Example |
| --- | --- |
| `е` is `ye` word-initially and after a vowel, `e` otherwise | Ер → Yer, поезд → poyezd, тезда → tezda |
| `ц` is `ts` after a vowel, `s` otherwise | милиция → militsiya, функция → funksiya, цирк → sirk |
| `ts` is `т` + `с` before an Uzbek suffix, `т` + `ш` before `h`, `ц` otherwise — a heuristic, see below | ketsa → кетса, hayotsiz → ҳаётсиз, adabiyotshunos → адабиётшунос, operatsiya → операция |
| `с` before `ҳ` takes a separator in `latin_1995` | Исҳоқ → Isʼhoq (not `Ishoq`) |

That last one is worth a note. In `latin_1995`, `sh` is a digraph, so a genuine
s+h sequence has to be separated with the tutuq belgisi or it reads as `ш`. The
2026 alphabet does not need the separator, because `ş` carries that sound —
`Isʼhoq` becomes simply `Ishoq`, while `ish` (work) becomes `iş`. The pair
survives the round trip in both directions.

The `ts` rule needs a note of its own. In loanwords `ts` is the letter `ц`;
where a stem ending in `t` meets a suffix beginning with `s` it is two letters:
`ketsa` (if he goes) is кетса, not кеца. There is no dictionary, so the reading
comes from the shape of the word. The checks run in order and the first that
applies wins:

- the `s` starts `sh` → `т` + `ш`: adabiyotshunos → адабиётшунос;
- the word starts with `ts` → `ц`: tsement → цемент;
- `i` and then a vowel or `y` follow → `ц`: operatsiya → операция, ratsion → рацион;
- `-mitsin` and `glitsin` → `ц`: azitromitsin → азитромицин, glitsin → глицин;
- the rest of the word is Uzbek suffixes → `т` + `с`. The `s` must open one of
  `-sa`, `-sak`, `-sam`, `-sang`, `-sangiz`, `-salar`, `-sin`, `-sinlar`,
  `-siz`, `-sizlik` or `-sevar`, and anything after it must be further suffixes
  (`-lik`, `-lar`, `-ga`, `-da`, `-ni`, `-man`, `-mi`, …): ketsinmi → кетсинми,
  hayotsizlik → ҳаётсизлик. Starting with the right letters is not enough, so
  meditsina (`sin` + `a`) and natsizm (`siz` + `m`) keep `ц`;
- otherwise `ц`: leykotsit → лейкоцит, protsent → процент.

The known misses:

- A loanword whose tail looks like a suffix gets `т` + `с`: aktsiz → актсиз
  (акциз), teplitsa → теплитса (теплица), siprofloksatsin → сипрофлоксатсин
  (ципрофлоксацин). Before 0.1.1 these came out right.
- An Uzbek word whose `t` + `s` boundary is not in the list keeps `ц`:
  compounds such as oʻtsoʻndirgich → ўцўндиргич (ўтсўндиргич) and
  soatsoz → соацоз (соатсоз), and suffixes such as `-simon` (otsimon → оцимон).
- pitsa is wrong either way: питса now, пица before 0.1.1, пицца in fact.

### The two modifier marks

`ʻ` (U+02BB, turned comma) is part of the letters `oʻ` and `gʻ`. `ʼ` (U+02BC,
modifier apostrophe) is the tutuq belgisi, a letter in its own right. Most
people type both as a plain `'`, so the library recovers the distinction from
context: after `o` or `g` the mark is a turned comma, elsewhere it is the tutuq
belgisi.

Input accepts `ʻ ʼ ' ’ ‘ \` ´ ʹ`. Output always emits the canonical two, which
makes the conversion idempotent and its output safe to store.

## Guarantees, and their limits

**Lossless.** `latin_1995` ↔ `latin_2026` round-trips exactly for text in
canonical form: marks written as `ʻ` and `ʼ`, and each word in lower case,
with an initial capital, or in all caps (`OʻZBEKISTON` included). Other input
comes back canonicalised — `o'zbek` as `oʻzbek`, `McDonald` as `Mcdonald`.
Cyrillic → Latin → Cyrillic round-trips exactly over the native Uzbek letter
inventory, with one gap: `т` followed by `с` comes back as `ц` unless the `s`
starts a suffix the `ts` rule knows (`ўтсўндиргич`, `соатсоз`; see
Context-dependent rules). Both are enforced by the test suite.

**Known lossy mappings.** Four Cyrillic letters occur only in Russian
loanwords, and folding them is deliberate:

| Letter | Behaviour | Reason |
| --- | --- | --- |
| щ | merges with ш → `sh` | no distinct sound in Uzbek |
| ы | merges with и → `i` | no distinct sound in Uzbek |
| ь | dropped | not represented in either Latin alphabet |
| ц | positional `ts`/`s`, not reversible | a heuristic; loanword spelling is genuinely inconsistent |

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

**A note on `ö`.** An earlier draft of the reform proposed `ō` (o with macron)
rather than `ö` for `oʻ`. This library emits `ö` and accepts `ō` on input as an
alias, so text written under either convention reads correctly. The reform is
one four-row table in `tables.py`; if the final decree settles differently, one
table changes and the rest of the library follows.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[test]"
.venv/bin/python -m pytest
```

The suite covers the alphabet letter by letter in both directions, the four
context rules, the round-trip tiers above, casing (including ALL-CAPS, where
`ШОШИМОВА` must give `ŞOŞIMOVA` and not `Şoşimova`, and `OʻZBEKISTON` must give
`ЎЗБЕКИСТОН`), and the cross-script normalization contract.
`tests/test_regressions.py` pins every defect fixed since 0.1.0; see
[CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).

## Who

Built by [AkademTech](https://akademtech.org).
