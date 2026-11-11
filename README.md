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
  preserves case and punctuation, and leaves URLs, markup, placeholders and
  the like alone. Use it to show text to people and to migrate a corpus from
  one alphabet to another.
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

### Protect URLs, code and names

Text to be converted often carries things that are not Uzbek words: a URL, an
e-mail address, a DOI, a placeholder in a message template, HTML, a file path,
a brand name, a lab value. Converting them breaks them, so `convert`,
`to_latin` and `to_cyrillic` leave them as they are, byte for byte, and convert
the text around them:

```python
>>> from akademtranslit import to_cyrillic
>>> to_cyrillic("Batafsil: https://shahar.uz, info@shahar.uz")
'Батафсил: https://shahar.uz, info@shahar.uz'
>>> to_cyrillic("{count, plural, one {# ta shahar} other {# ta shahar}}")
'{count, plural, one {# та шаҳар} other {# та шаҳар}}'
>>> to_cyrillic("SpO2 92%, pH 7,35")
'SpO2 92%, pH 7,35'

```

| Kind | What is protected | Example |
| --- | --- | --- |
| `url` | `http://`, `https://`, `ftp://` or `www.` up to the next space; a bare domain only with `.uz .com .org .net .ru .info .edu .gov .io` | `https://gazeta.uz/oz/`, `kun.uz` |
| `email` | `local@domain.tld`, with `mailto:` if it is there | `info@shahar.uz` |
| `doi` | `10.`, 4–9 digits, `/` and the rest up to a space, with `doi:` if it is there | `doi:10.1234/chashma.2026.01` |
| `markup` | tags, comments and entities; the text between tags is converted | `<b>`, `<a href="…">`, `&nbsp;` |
| `placeholder` | ICU MessageFormat arguments (in `plural` and `select`, only the messages are converted), printf directives, `{{ … }}` | `{name}`, `{n, number}`, `%s`, `%(soni)d` |
| `path` | `/`, `./`, `../`, `~/` or `C:\` up to the next space; a file name with a known extension | `/home/user/shahar.txt`, `hisobot.docx` |
| `term` | a string you name, exactly and as a whole word | `Protect(terms=("AslMatn",))` |
| `token` | an ASCII word with both a letter and a digit, or with a lowercase letter before a capital, and no `oʻ` or `gʻ`; not a number with a suffix, not an Uzbek abbreviation | `SpO2`, `B12`, `pH`, `iPhone`, `McDonald`, `ChatGPT` |

Trailing punctuation is not part of a URL, DOI or path (`https://shahar.uz.`
ends before the dot), except a `)` that closes a `(` inside it. `kirill/lotin`
is not a path, `a < b` is not a tag, and a `{` without its `}` is an ordinary
character. The module `akademtranslit.protect` gives the exact rules.

Three kinds of word look like tokens and are converted instead: an Uzbek
abbreviation with `Sh` or `Ch` (`MChJ`, `AQSh`: `Sh` and `Ch` after a capital
count as one capital); a number with a suffix or a unit, digits followed by
lowercase letters only (`10ta`, `2026yil`, `100mg`); and an Uzbek abbreviation
of a capital, one to four lowercase letters and two or more capitals
(`ToshDU`, `SamDU`, `ToshPTI`). `ChatGPT`, `PhD` and `AkademID` do not have
that shape and stay tokens:

```python
>>> to_cyrillic("10ta kitob, ToshDU va MChJ, ChatGPT")
'10та китоб, ТошДУ ва МЧЖ, ChatGPT'

```

`segments` shows how a text is split; `None` marks the pieces that are
converted:

```python
>>> from akademtranslit import segments
>>> segments("Salom, {name}! pH 7,4")
[('Salom, ', None), ('{name}', 'placeholder'), ('! ', None), ('pH', 'token'), (' 7,4', None)]

```

`Protect` chooses the kinds, all of them on by default. `terms` adds strings
of your own, matched exactly, case included:

```python
>>> from akademtranslit import Protect, convert
>>> convert("Toshkent shahri", source="latin_1995", target="latin_2026",
...         protect=Protect(terms=("Toshkent",)))
'Toshkent şahri'
>>> convert("pH va https://shahar.uz", source="latin_1995", target="cyrillic",
...         protect=Protect(urls=False))
'pH ва ҳттпс://шаҳар.уз'

```

`protect=False` (or `Protect.NONE`) converts everything, as versions before
0.3.0 did; only the case of a mixed-case word comes out differently, kept per
letter unit (`McDonald`, where 0.2.0 gave `Mcdonald`; see Case below):

```python
>>> to_cyrillic("https://shahar.uz", protect=False)
'ҳттпс://шаҳар.уз'

```

With `source="auto"`, only the text outside the protected spans decides the
orthography, so a `ş` inside a URL does not make the text 2026. `normalize` and
`sort_key` do not use protection: a search key and a sort order treat the whole
text alike.

**Known limitations.** Whether a word is a token is decided by its shape, not
by a dictionary:

- An Uzbek abbreviation with five or more lowercase letters, such as
  `TermizDU`, is a token and is not converted.
- An Uzbek word typed with broken case, such as `ToshKent` or `tOSHKENT`, looks
  like a token and is left unconverted.

### Name the orthography with a language tag

Wherever a function takes an orthography, it also takes a BCP 47 language
tag:

```python
>>> from akademtranslit import convert, script_for_tag, tag_for_script
>>> convert("Тошкент", source="uz-Cyrl", target="uz-Latn-2026")
'Toşkent'
>>> script_for_tag("uz-Latn-1995")
'latin_1995'
>>> tag_for_script("latin_2026")
'uz-Latn-2026'

```

| Tag | Orthography |
| --- | --- |
| `uz-Cyrl` | `cyrillic` |
| `uz-Latn-1995`, `uz-1995` | `latin_1995` |
| `uz-Latn-2026`, `uz-2026` | `latin_2026` |
| `uz-Latn`, `uz` | `latin_1995` in 0.x, `latin_2026` from 1.0.0 |

Tags are matched without regard to case, and `_` is accepted in place of `-`.
A region (`uz-Latn-UZ`), extensions (`-t-…`, `-u-…`) and a private-use part
(`-x-…`) do not change the orthography and are ignored. Anything else raises
`ValueError`: another language or script, an unknown variant, a variant on
`uz-Cyrl`, a malformed tag. Nothing is guessed.

`uz-Latn` and `uz` name no orthography. In 0.x the library reads them as the
1995 orthography and raises a `FutureWarning`: version 1.0.0, due after Law
No. O'RQ-1184 takes effect on 22 April 2027, will read them as the 2026 one.
Name the variant to avoid both the warning and the change. The library never
decides by the date: a call gives the same output on any day.

The variant subtags `1995` and `2026` were requested from IANA in October
2026; registration is pending.

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

### ASCII for names and logins

`to_ascii` writes a name in plain ASCII, for logins, file names and systems
that take nothing else:

```python
>>> from akademtranslit import to_ascii
>>> to_ascii("Чўлпон"), to_ascii("Çölpon"), to_ascii("Gʻafur Gʻulom")
('Cholpon', 'Cholpon', 'Gafur Gulom')

```

It converts the text to the 1995 orthography with `to_latin`, keeping protected
spans, so `McDonald` keeps its case. Then it writes `oʻ` and `gʻ` as `o` and
`g`, and any `ş ç ğ ö` still there as `sh ch g o`; a capital `Ş` or `Ç` is
`SH` or `CH` when the character before or after it is a capital, `Sh` or `Ch`
otherwise. It removes the tutuq belgisi and the other apostrophe marks, takes
the accents off other letters (`é` → `e`), and removes whatever is still not
ASCII. Case, spaces, digits and ASCII punctuation stay.

| Input | Output |
| --- | --- |
| Шавкат, Şavkat | Shavkat |
| Oʻktam | Oktam |
| Gʻafur Gʻulom | Gafur Gulom |
| Isʼhoq, Исҳоқ | Ishoq |
| Ёқуб | Yoqub |
| Çölpon | Cholpon |
| José | Jose |
| ŞOŞIMOVA | SHOSHIMOVA |
| Ўзбекистон | Ozbekiston |
| McDonald | McDonald |
| Тошкент ŞAHAR | Toshkent SHAHAR |

This is a project scheme, not a passport standard. Its tables, `ASCII_SCHEME`
and `ASCII_CAPITALS` in `tables.py`, change only in a major release.

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

Text copied from web pages and documents also carries characters nobody can
see: a soft hyphen or a zero-width space splits a word in two, a byte order
mark sits before the first letter. `strip_invisible=True` removes them, all
4174 default-ignorable code points of Unicode 15.1, from the whole text.
`strip_stress=True` removes the combining acute accent (U+0301) after a letter,
the stress mark of dictionaries. Both are off by default:

```python
>>> text = "Tosh" + chr(0x00AD) + "kent"
>>> normalize_apostrophes(text, strip_invisible=True)
'Toshkent'
>>> normalize_apostrophes("То" + chr(0x0301) + "шкент", strip_stress=True)
'Тошкент'

```

Run it before `normalize` on such text: `normalize` reads a soft hyphen as a
space, so `text` above gives the key `tosh kent`.

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

Seven readings depend on position rather than on the letter alone:

| Rule | Example |
| --- | --- |
| `е` is `ye` word-initially and after a vowel, `e` otherwise | Ер → Yer, поезд → poyezd, тезда → tezda |
| `ц` is `ts` after a vowel, `s` otherwise | милиция → militsiya, функция → funksiya, цирк → sirk |
| `ts` is `т` + `с` before an Uzbek suffix, `т` + `ш` before `h`, `ц` otherwise — a heuristic, see below | ketsa → кетса, hayotsiz → ҳаётсиз, adabiyotshunos → адабиётшунос, operatsiya → операция |
| `с` before `ҳ` takes a separator in `latin_1995` | Исҳоқ → Isʼhoq (not `Ishoq`) |
| `ъ` is dropped after a consonant before `е ё ю я` and after `ў`, `ʼ` otherwise | объект → obyekt, мўъжиза → moʻjiza, маъно → maʼno |
| `ь` is `y` before `о` and is dropped otherwise | бульон → bulyon, павильон → pavilyon, альбом → albom |
| `e` is `э` word-initially and after a vowel, except before `v`; `е` otherwise | ekran → экран, poeziya → поэзия, aeroport → аэропорт, tezda → тезда, Aliev → Алиев |

The `v` exception keeps surnames romanized the Russian way as they are written
in Cyrillic: Aliev, Alievning and Kiev give Алиев, Алиевнинг and Киев. The
standard spellings Aliyev and Kiyev give the same Cyrillic.

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
canonical form: marks written as `ʻ` and `ʼ`, and each word, or each letter
unit of it (`ToshDU`, `OʻzBEKISTON`; see Case below), in lower case, with an
initial capital, or in all caps (`OʻZBEKISTON` included); protected spans,
such as `McDonald`, come back as they were. Other input comes back
canonicalised — `o'zbek` as `oʻzbek`, `MChJ` as `MCHJ`.
Cyrillic → Latin → Cyrillic round-trips exactly over the native Uzbek letter
inventory, with two gaps: `т` followed by `с` comes back as `ц` unless the `s`
starts a suffix the `ts` rule knows (`ўтсўндиргич`, `соатсоз`; see
Context-dependent rules), and `ъ` after `ў` does not come back (`мўъжиза` →
`moʻjiza` → `мўжиза`). Both are enforced by the test suite.

**Case.** Case is kept per letter unit, not re-applied to the whole word. A
word is split where a lowercase letter is followed by a capital, and each part
keeps its own case. `Sh` and `Ch` are one letter in `latin_1995`, so the `h`
after a capital `S` or `C` counts as a capital when the word has another
capital. A word with irregular case keeps it letter by letter when the output
is as long as the input:

```python
>>> to_latin("«AKADEMTECH» MChJ, AQSh va ToshDU")
'«AKADEMTEÇ» MÇJ, AQŞ va ToşDU'
>>> to_cyrillic("OʻzMU va AQSh"), to_latin("OʻzBEKISTON", variant="latin_1995")
('ЎзМУ ва АҚШ', 'OʻzBEKISTON')

```

A word typed with broken case keeps it too: `OʻzBEKISTON` gives `ÖzBEKISTON`,
as the CLDR transform does. One known limitation: `МЧЖ` and `MÇJ` have a
single letter for `Ch`, so they give `MCHJ` in `latin_1995`, where the
official spelling is `MChJ`. Telling the two apart takes a dictionary.

**Protected spans.** Every span that `segments` finds — a URL, an e-mail
address, a DOI, markup, a placeholder, a path, a term, a token — comes out of
`convert`, `to_latin` and `to_cyrillic` byte for byte, for every source and
target; the test suite checks this on every golden input.

**Known lossy mappings.** Four Cyrillic letters occur only in Russian
loanwords, and folding them is deliberate; `ъ` is dropped where the 1995
spelling drops it:

| Letter | Behaviour | Reason |
| --- | --- | --- |
| щ | merges with ш → `sh` | no distinct sound in Uzbek |
| ы | merges with и → `i` | no distinct sound in Uzbek |
| ь | dropped, except `y` before `о` (`бульон` → `bulyon`); not reversible | not represented in either Latin alphabet |
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
or `ǒ`. Both are read as `ö` whenever the text is read as, or converted to,
the 2026 orthography, so text written under a draft reads correctly and they
never appear in 2026 output:

```python
>>> from akademtranslit import to_latin
>>> to_latin("ōrdak")
'ördak'

```

**The 2026 spelling rules.** Law No. O'RQ-1184 fixes the 2026 alphabet.
Detailed spelling rules for it have not been adopted yet (November 2026). Until
they are, the library applies the 1995 rules with the four letters replaced,
and writes a real s + h without the separator. When official rules are
published, the outputs they change will change in a minor release, with a
golden diff.

**Rules version.** `RULES_VERSION` names the rules the conversion functions
follow:

```python
>>> from akademtranslit import RULES_VERSION
>>> RULES_VERSION
'uz-2026-alphabet+project-2026.11'

```

The part before `+` is the official basis: `uz-2026-alphabet` is the 2026
alphabet of Law No. O'RQ-1184, without official spelling rules. The part after
it is this project's rule set, named by the year and month of the release that
last changed the output of `convert`, `to_latin` or `to_cyrillic`; a release
that changes none of their output keeps the value. Store it next to converted
text to know which rules produced it.

## Golden vectors

`golden/` holds the library's output, sealed:

- `inputs.json` — the inputs: every letter of the three alphabets, the context
  rules, every apostrophe form, mixed content, ecosystem traps. Append-only: an
  `id` never changes and is never reused.
- `tag-inputs.json` — language tags: every accepted form and the ways a tag
  can be wrong. Append-only, like `inputs.json`.
- `golden-<version>.json` — for that release: the output of each public text
  function on every input (`convert` for all nine source and target pairs),
  of `script_for_tag` and `tag_for_script` on every tag, and, from 0.3.0,
  `RULES_VERSION`.
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

`cldr/` holds the data for a Unicode CLDR proposal for the 2026 orthography:
transform rules, collation tailorings and exemplar characters, with tests
checked against ICU and against these golden vectors. See
[cldr/README.md](cldr/README.md).

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
`ЎЗБЕКИСТОН`; and case per letter unit, where `MChJ` must give `MÇJ`), the
cross-script normalization contract, sorting, and the golden vectors. The
examples in this README and in the docstrings run as tests.
`tests/test_regressions.py`, `tests/test_changes_0_2_0.py`,
`tests/test_changes_0_3_0.py` and, for protected spans, `tests/test_protect.py`
pin every behaviour change since 0.1.0; see [CHANGELOG.md](CHANGELOG.md).

How the package is put together: [docs/architecture.md](docs/architecture.md).

## Security

See [SECURITY.md](SECURITY.md). The library does not use the network and
stores nothing; see [PRIVACY.md](PRIVACY.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). This project follows a
[code of conduct](CODE_OF_CONDUCT.md).

## License

MIT — see [LICENSE](LICENSE).

The files in `cldr/transforms/`, `cldr/collation/` and `cldr/reference/` are
Unicode CLDR data or derived from it, under the Unicode License v3 (see
[cldr/LICENSE](cldr/LICENSE)). They are not part of the Python package.

## Who

AkademTranslit is owned and maintained by AKADEMTECH MChJ, a limited
liability company registered in Uzbekistan
([akademtech.org](https://akademtech.org)). Contact: contact@akademtech.org.
