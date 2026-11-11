# Uzbek, 2026 orthography — data for Unicode CLDR

Prepared by AkademTranslit (AkademTech) on 8 November 2026 as the data for a
CLDR ticket. The ticket and the proposal text are AkademTech's; this folder
holds the rules, the tests and the measurements behind them.

Law of the Republic of Uzbekistan No. ZRU-1184 (OʻRQ-1184; signed
21 October 2026, in force 22 April 2027; https://lex.uz/docs/-8548754)
changes four letters of the Uzbek Latin alphabet:
oʻ → ö, gʻ → ğ, sh → ş, ch → ç. The alphabet becomes A B D E F G Ğ H I J K L
M N O Ö P Q R S Ş Ç T U V X Y Z (28 letters) plus the tutuq belgisi ʼ (U+02BC).
CLDR today has the 1995 orthography only.

## Contents

| Path | What |
| --- | --- |
| `transforms/uz_Latn_1995-uz_Latn_2026.xml` | new: 1995 ↔ 2026, both directions |
| `transforms/uz_Cyrl-uz_Latn_2026.xml` | new: Cyrillic ↔ 2026, both directions; based on the existing `uz_Cyrl-uz_Latn` |
| `collation/uz.xml` | option A: the existing `uz` collation plus the 2026 letters |
| `collation/uz_Latn_2026-option-b.xml` | option B: a separate 2026-only tailoring, for comparison |
| `collation/uz_Cyrl.xml` | new: Uzbek Cyrillic alphabetical order |
| `exemplars.md` | exemplar characters to enter in the Survey Tool |
| `tests/cldr/` | test cases in CLDR's `common/testData/transforms` format |
| `tests/*.tsv`, `tests/collation-*.txt` | the same cases with ids; sorted word lists |
| `tests/check-report.txt` | the output of the check below |
| `tools/check_cldr.py` | the check |
| `reference/` | the current CLDR files these build on, unchanged |

`reference/` was taken from `unicode-org/cldr`, branch `main`, on 8 November
2026:

```
8faa52fe0086206f1556700b8cad03f91135817b59acdffd9f46fc03054afd0c  reference/uz_Cyrl-uz_Latn.xml   (common/transforms/)
a6bcec2e3cb99486882f310685fe3ec8f643e4918acf613ca01d62467fcc195e  reference/collation_uz.xml      (common/collation/uz.xml)
```

## Identifiers

Following UTS #35 (General, "Transforms"): source and target are locale
identifiers, and the BCP 47 alias reverses the order around `-t-`.

| Transform | `alias` | `backwardAlias` |
| --- | --- | --- |
| `uz_Latn_1995-uz_Latn_2026` | `uz-Latn-2026-t-uz-latn-1995` | `uz-Latn-1995-t-uz-latn-2026` |
| `uz_Cyrl-uz_Latn_2026` | `uz-Latn-2026-t-uz-cyrl` | `uz-Cyrl-t-uz-latn-2026` |

The aliases need the variant subtags `1995` and `2026` for `uz` in the IANA
Language Subtag Registry. They were requested on the ietf-languages list on
22 October 2026 (revised on 25 October). On 9 November 2026 the Language
Subtag Reviewer posted the proposed records, unchanged from the request, and
extended the review period to 15 November 2026, Anywhere on Earth. Until IANA
adds them, the aliases are not valid BCP 47 tags.

| Subtag | Description | Prefix | Comments |
| --- | --- | --- | --- |
| `1995` | Uzbek Latin orthography of 1995 | `uz`, `uz-Latn` | Uzbek Latin orthography with the digraphs sh and ch and the letters oʻ and gʻ |
| `2026` | Uzbek Latin orthography of 2026 | `uz`, `uz-Latn` | Uzbek Latin orthography with the letters ö, ğ, ş and ç in place of oʻ, gʻ, sh and ch |

The existing transform calls the 1995 orthography plain `uz_Latn`. The new
files name it `uz_Latn_1995`, so that `uz_Latn` can later follow whichever
orthography is in common use.

## The transforms

### 1995 ↔ 2026

- The four letters. Going back to 1995, the second letter of SH and CH is
  capital next to another capital (ŞOŞIMOVA → SHOSHIMOVA, IŞ → ISH) and small
  otherwise (Şoşimova → Shoshimova, Ş. → Sh.).
- A real s + h: written sʼh in 1995 (Isʼhoq), plain sh in 2026 (Ishoq), where
  ş is the digraph.
- Input marks, 1995 → 2026: after o or g any apostrophe-like mark
  (ʻ ʼ ‘ ’ ' \` ´ ʹ) is read as the turned comma of oʻ or gʻ; between other
  letters it is the tutuq belgisi. The standard `uz` collation already treats
  o' and o‘ as oʻ for the same reason: people type them.
- Input marks, 2026 → 1995: the 2026 orthography has no turned comma, so a mark
  inside a word is the tutuq belgisi (except after o or g).
- ō and ǒ, used for ö in drafts of the reform, are read as ö.

Both directions are lossless for text in canonical form.

### Cyrillic ↔ 2026

The existing `uz_Cyrl-uz_Latn` with these changes:

- ў → ö, ғ → ğ, ш → ş, ч → ç. These are single letters, so the Sh/SH and Ch/CH
  case rules are gone.
- с + ҳ → sh. The 1995 transform writes it as sh too, which reads back as ш
  (Исҳоқ → Ishoq → Ишоқ); in 2026 sh is unambiguous, so Исҳоқ round-trips.
- Ё Ю Я Ц and the word-initial Е: both Latin letters capital only next to
  another capital, so initials are Yo. Yu. Ya. Ts. Ye. (the existing transform
  gives YO. YU. …).
- Latin → Cyrillic: e is э only at the start of a word and е elsewhere
  (tezda → тезда); yö is йў (yöl → йўл); t before ş is т (adabiyotşunos →
  адабиётшунос); an apostrophe-like mark inside a word is the tutuq belgisi.
- A word boundary is "not a letter and not a combining mark". The rules run on
  NFD text, where ş is s + U+0327; with the existing `[:^L:]` boundary, Алишер
  would come out as Alişyer.

## Collation: two options

**Option A — extend the standard `uz` collation** (`collation/uz.xml`). Add
`&g<ğ`, `&o<ö`, `&s<ş<ç` to the existing tailoring, which keeps oʻ gʻ sh ch
after z. ğ ö ş ç do not occur in 1995 text, so one tailoring sorts both
orthographies, each in its own order, and mixed lists stay sensible during the
transition. The cost: in 2026 text a real s + h (Ishoq, ashob, Ishoqov) meets
the 1995 contraction sh and sorts after z. Such words are rare.

**Option B — a separate 2026 tailoring** (`collation/uz_Latn_2026-option-b.xml`).
Exact for 2026 text. CLDR would need a place for it: a variant locale or a new
collation type.

In both options the tutuq belgisi ʼ differs from a letter only at the
secondary level (`&[last primary ignorable]<<ʼ`): maʼno sorts next to mano,
after it. Today root gives ʼ a primary weight after the letters, so maʼno
sorts after maqol.

**`uz_Cyrl`** (`collation/uz_Cyrl.xml`, new): Ё after Е, and Ў Қ Ғ Ҳ after Я,
as in the Uzbek Cyrillic alphabet. There is no `uz_Cyrl` collation today, so
root order applies: ё sorts as a variant of е, and ў қ ғ ҳ right after у к г х.

## Results

ICU 74.2 (Unicode 15.1), `akademtranslit` 0.2.0 and its golden vectors
(1121 inputs; plus 545 inputs in the 2026 orthography: the golden ones and the
library's 2026 output for every Cyrillic and 1995 input). Full output:
`tests/check-report.txt`.

| Check | Result |
| --- | --- |
| 1995 → 2026, against the library | 572 inputs; 10 differ, all explained: the library re-cases mixed-case words (pH → ph), the transform keeps each letter's case (7); decomposed input (2); a lone mark (1) |
| 2026 → 1995, against the library | 545 inputs; 2 differ: decomposed input, which the transform normalizes and the library does not |
| Cyrillic → 2026 = existing `uz_Cyrl-uz_Latn` then 1995 → 2026 | 435 inputs; 9 differ, all intended: с + ҳ (4), a single capital Е Ё Ю Я Ц (5) |
| Cyrillic → 2026 → Cyrillic | 357 of 435 come back unchanged; the existing Cyrillic → 1995 → Cyrillic: 290 |
| 2026 → 1995 → 2026 | 536 of 545 unchanged; the other 9 are ō ǒ, which come back as ö |
| Collation, option A | 1995 words: 442, same order as the library; 2026 words: 442, 4 pairs differ (the s + h words above) |
| Collation, option B | 2026 words: 442, same order as the library |
| Collation, `uz_Cyrl` | 425 words, same order as the library |

The test files in `tests/` are the output of the proposed rules under ICU. The
check regenerates them and fails if they change.

## Left as in the existing transform

Three choices follow the existing `uz_Cyrl-uz_Latn` rather than the rules of
the AkademTranslit library, because CLDR's guidelines put a lossless round
trip first for script transliterations. The numbers are the differences from
the library. The library's rules are meant to follow the 1995 spelling rules
(Cabinet of Ministers resolution No. 339 of 24 August 1995,
https://lex.uz/docs/-1625271); that has not been checked against the text of
the resolution.

| | Existing transform and this proposal | AkademTranslit library | Differences |
| --- | --- | --- | --- |
| ц | always ts: tsirk, funktsiya | s at the start of a word and after a consonant: sirk, funksiya; ts after a vowel | 29 of 435 Cyrillic inputs |
| ъ | always ʼ: obʼyekt, möʼjiza | dropped before е ё ю я after a consonant, and after ў: obyekt, möjiza | 9 of 435 |
| Latin ts | always ц: ketsa → кеца | т + с before an Uzbek suffix: ketsa → кетса | 57 of 545 2026 inputs |

Following the library would make Cyrillic → Latin closer to published
spelling, but those words would no longer come back to the same Cyrillic. The
choice is CLDR's; the library's behaviour is documented in its README.

## Defects in the existing `uz` transforms

Outside the 2026 proposal, but found by the same check. All are in the current
`uz_Cyrl-uz_Latn` (CLDR `main`, 8 November 2026; identical to the one in ICU
74.2 on all 1121 inputs, both directions):

1. Latin → Cyrillic writes every e that is not after a vowel as э:
   tezda → тэзда, Oʻzbekiston → Ўзбэкистон, kelajak → кэлажак. Of 548 golden
   1995 inputs that contain letters, 110 come out with a wrong э.
2. yoʻl → ёʻл (should be йўл): yo is taken before oʻ.
3. Исҳоқ → Ishoq, which reads back as Ишоқ. The 1995 orthography writes
   Isʼhoq; Isʼhoq → Исъҳоқ.
4. Initials: Ш. Рашидов → SH. Rashidov (should be Sh.).
5. An ASCII apostrophe is not read as part of oʻ or gʻ: o'zbek → о'збэк.

The new transforms do not have 1–4, and the 1995 → 2026 transform reads o'
and g' as oʻ and gʻ. The same fixes could be proposed for `uz_Cyrl-uz_Latn` in
a separate ticket.

## Running the check

```bash
pip install PyICU akademtranslit==0.2.0     # PyICU needs the ICU library
python tools/check_cldr.py PATH/TO/golden    # golden/ of the akademtranslit repository
python tools/check_cldr.py PATH/TO/golden --write-tests
```

Exit code 0 means every difference is one of the explained kinds and the test
files match.

## Licence

The files in `transforms/`, `collation/` and `reference/` are CLDR data or
derived from it, under the Unicode License v3, and keep its notice. The check
and the test cases are AkademTranslit's (MIT). A pull request to
`unicode-org/cldr` needs a Unicode Contributor License Agreement (individual or
corporate) on file first.
