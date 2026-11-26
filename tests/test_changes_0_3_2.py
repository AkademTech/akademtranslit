"""Changes in 0.3.2: Roman numerals, month names, dates and a word-final ц,
and to_ascii writing U+2011 as a hyphen.

Each rule has a section: the examples it was made for, its boundaries, the
other direction, ``source="auto"``, and a protected span, which keeps its text
whatever the rule says. ``js/test/changes-0.3.2.test.js`` has the same tables
for the JavaScript port.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert, normalize, to_ascii, to_cyrillic, to_latin
from akademtranslit.rules import cyrillic_word_to_latin_1995, dates, is_roman_numeral

LATIN = (LATIN_1995, LATIN_2026)
NBSP, NB_HYPHEN = "\N{NO-BREAK SPACE}", "\N{NON-BREAKING HYPHEN}"


# --- TRANSLIT-24: a Roman numeral stays Latin in Cyrillic ------------------------------

ROMAN_NUMERALS = [
    ("XIX asr", "XIX аср"),
    ("IV bob", "IV боб"),
    ("XXI asrning oxiri", "XXI асрнинг охири"),
    ("MMXXVI", "MMXXVI"),
    ("CD va DVD", "CD ва ДВД"),  # DVD is not a well-formed numeral
    ("XIX.", "XIX."),  # more than one letter: a full stop after it is a full stop
    ("II", "II"),  # two letters: a numeral wherever they stand
    # One letter, in context: (a) the word after it ...
    ("V asr", "V аср"),
    ("X sinf", "X синф"),
    ("I jahon", "I жаҳон"),
    ("V ASR", "V АСР"),
    ("V Asrda", "V Асрда"),
    ("V\N{NO-BREAK SPACE}asr", "V\N{NO-BREAK SPACE}аср"),
    ("V-asr", "V-аср"),
    (f"V{NB_HYPHEN}asr", f"V{NB_HYPHEN}аср"),
    ("V bo'lim, V bo‘lim", "V бўлим, V бўлим"),
    # ... (b) the word before it.
    ("Pyotr I", "Пётр I"),
    ("Nikolay I", "Николай I"),
    ("Pyotr\N{NO-BREAK SPACE}I", "Пётр\N{NO-BREAK SPACE}I"),
    ("Pyotr I, Nikolay II", "Пётр I, Николай II"),
    ("Пётр I", "Пётр I"),  # a Cyrillic word before it, with a Latin source
    # Known limit (README): a capitalised word before a letter makes it a numeral.
    ("Variant V", "Вариант V"),
]

# Boundaries: an initial, a letter, a known limit, and what is not a numeral.
NOT_ROMAN_NUMERALS = [
    ("I. Boʻriyev", "И. Бўриев"),
    ("M. Asadullayev", "М. Асадуллаев"),
    ("V. I. Lenin", "В. И. Ленин"),
    ("Pyotr I.", "Пётр И."),  # known limit: read as an initial at the end of a sentence
    ("IIII", "ИИИИ"),
    ("Xix", "Хих"),
    ("XIXda", "ХИХда"),  # a numeral with a suffix in one word is not a numeral word
    # One letter out of context is a letter.
    ("I", "И"),
    ("V", "В"),
    ("X", "Х"),
    ("V harfi", "В ҳарфи"),
    ("V  asr", "В  аср"),  # two spaces
    ("V–asr", "В–аср"),  # a dash is not a hyphen
    ("V- asr", "В- аср"),
    ("V. asr", "В. аср"),
    ("V, asr", "В, аср"),
    ("Pyotr  I", "Пётр  И"),  # two spaces
    ("Pyotr, I", "Пётр, И"),
    ("Pyotr-I", "Пётр-И"),  # the word before counts after one space only
    ("pyotr I", "пётр И"),  # no capital before it
    ("A I", "А И"),  # one letter before it
    ("Oʻ I", "Ў И"),  # oʻ is one letter
    ("I va V", "И ва В"),
    ("V basr", "В баср"),  # asr inside a word does not count
    # One L, C, D or M is a letter wherever it stands (C is not in the alphabet and stays).
    ("D guruhida", "Д гуруҳида"),
    ("M harfi", "М ҳарфи"),
    ("A, B, C va D toifalar", "А, Б, C ва Д тоифалар"),
    ("L asr", "Л аср"),
    ("Karl D", "Карл Д"),
    # Before harf or tovush one I, V or X is a letter, after a name too.
    ("Lotin V harfi", "Лотин В ҳарфи"),
    ("V va X harflari", "В ва Х ҳарфлари"),
    ("V, X harflari", "В, Х ҳарфлари"),
    ("Pyotr I harfi", "Пётр И ҳарфи"),
    ("Lotin X HARFLARI", "Лотин Х ҲАРФЛАРИ"),
    ("V\N{NO-BREAK SPACE}Harflari", "В\N{NO-BREAK SPACE}Ҳарфлари"),
]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("latin,cyrillic", ROMAN_NUMERALS + NOT_ROMAN_NUMERALS)
def test_roman_numerals_latin_to_cyrillic(latin, cyrillic, source):
    assert convert(latin, source, CYRILLIC) == cyrillic


# Section 6 of the 0.3.2c task: what one letter or a numeral gave at ba40a26 and still
# gives, and the known limits.
ROMAN_AS_AT_BA40A26 = [
    ("V harfi", "В ҳарфи"),
    ("V asr", "V аср"),
    ("Nikolay I", "Николай I"),
    ("Pyotr, I", "Пётр, И"),
    ("X", "Х"),
    ("D I L M V X", "Д И Л М В Х"),
    ("XIX asr, IV bob", "XIX аср, IV боб"),
    ("MIX", "MIX"),
    ("CD va DVD", "CD ва ДВД"),
    ("Karl V", "Карл V"),
    ("Lyudovik XIV va Lyudovik XV", "Людовик XIV ва Людовик XV"),
    ("C toifa", "C тоифа"),
    ("B toifali", "Б тоифали"),
    ("C va D", "C ва Д"),
    # Known limits (README): an initial at the end of a sentence, and a capitalised
    # word at the start of one.
    ("Pyotr I.", "Пётр И."),
    ("Karl V.", "Карл В."),
    ("Variant V", "Вариант V"),
]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("latin,cyrillic", ROMAN_AS_AT_BA40A26)
def test_roman_numerals_as_before(latin, cyrillic, source):
    assert convert(latin, source, CYRILLIC) == cyrillic


# The words that make one letter before them a numeral (the last 14 since 0.3.2c), and
# their 2026 forms.
COUNTED = [
    "asr", "ming", "bob", "qism", "jild", "tom", "sinf", "kurs", "boʻlim", "guruh", "chorak",
    "bosqich", "daraja", "toifa", "qurultoy", "syezd", "sessiya", "chaqiriq", "jahon",
    "kvartal", "semestr", "smena", "kitob", "kategoriya", "oʻrin", "yarim", "yarmi", "xalqaro",
    "respublika", "konferensiya", "kongress", "anjuman", "simpozium",
]
COUNTED_2026 = ["bölim", "çorak", "bosqiç", "çaqiriq", "örin"]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("word", COUNTED + COUNTED_2026)
def test_one_letter_before_a_counted_word(word, source):
    for letter in "IVX":
        for text in (f"{letter} {word}", f"{letter} {word.upper()}", f"{letter} {word}lar"):
            rest = text[2:]
            assert convert(text, source, CYRILLIC) == f"{letter} " + convert(rest, source, CYRILLIC), text


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("word", COUNTED + COUNTED_2026)
def test_one_l_c_d_or_m_before_a_counted_word_is_a_letter(word, source):
    for letter in "LCDM":
        for text in (f"{letter} {word}", f"Pyotr {letter} {word}"):
            expected = " ".join(convert(part, source, CYRILLIC) for part in text.split(" "))
            assert convert(text, source, CYRILLIC) == expected, text
    assert convert(f"L {word}", source, CYRILLIC).startswith("Л ")
    assert convert(f"D {word}", source, CYRILLIC).startswith("Д ")
    assert convert(f"M {word}", source, CYRILLIC).startswith("М ")


@pytest.mark.parametrize("word", ["harfi", "va", "as", "asos", "boshqa", "minora", "to", "sin", "jahl", "bo"])
def test_one_letter_before_another_word_is_a_letter(word):
    """Only a word that begins with a whole counted word: minora is not ming,
    to is not tom."""
    assert to_cyrillic(f"V {word}").startswith("В ")


# The words that make one letter before them a letter, and the 2026 form.
LETTER_WORDS = ["harf", "harfi", "harflari", "harfini", "tovush", "tovushi", "tovushlar"]
LETTER_WORDS_2026 = ["tovuş", "tovuşi", "tovuşlar"]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("word", LETTER_WORDS + LETTER_WORDS_2026)
def test_one_letter_before_harf_or_tovush_is_a_letter(word, source):
    """Before harf or tovush, in any case, nothing makes one letter a numeral:
    not the name before it (b), and not a counted word, which cannot follow."""
    if source == LATIN_1995 and word in LETTER_WORDS_2026:
        return  # ş is not a latin_1995 letter
    for letter, cyrillic in (("I", "И"), ("V", "В"), ("X", "Х")):
        for form in (word, word.upper(), word.capitalize()):
            for before in ("", "Lotin ", "Pyotr\N{NO-BREAK SPACE}"):
                text = f"{before}{letter} {form}"
                got = convert(text, source, CYRILLIC)
                assert got == convert(before, source, CYRILLIC) + f"{cyrillic} " + convert(form, source, CYRILLIC), text


def test_a_word_that_only_begins_like_harf_counts():
    """As with the counted words, the word after the letter begins with harf
    or tovush; harfiy (literal) does too."""
    assert to_cyrillic("Lotin V harfiy") == "Лотин В ҳарфий"
    assert to_cyrillic("Lotin V harakat") == "Лотин V ҳаракат"  # not harf


@pytest.mark.parametrize("latin_1995,latin_2026,cyrillic", [
    ("I jahon urushi", "I jahon uruşi", "I жаҳон уруши"),
    ("V boʻlim", "V bölim", "V бўлим"),
    ("II chorak va I chorak", "II çorak va I çorak", "II чорак ва I чорак"),
    ("I bosqich", "I bosqiç", "I босқич"),
    ("V harfi", "V harfi", "В ҳарфи"),
    ("Nikolay I", "Nikolay I", "Николай I"),
    ("I tovushi", "I tovuşi", "И товуши"),
    ("Lotin X TOVUSHI", "Lotin X TOVUŞI", "Лотин Х ТОВУШИ"),
])
def test_roman_numerals_one_letter_in_both_latin_orthographies(latin_1995, latin_2026, cyrillic):
    assert convert(latin_1995, LATIN_1995, CYRILLIC) == cyrillic
    assert convert(latin_2026, LATIN_2026, CYRILLIC) == cyrillic
    assert to_cyrillic(latin_1995) == cyrillic
    assert to_cyrillic(latin_2026) == cyrillic


def test_a_word_in_capitals_that_is_a_numeral_stays_latin():
    """Known limit (README): MIX is 1009, so it stays."""
    assert to_cyrillic("MIX") == "MIX"


@pytest.mark.parametrize("target", LATIN)
@pytest.mark.parametrize("cyrillic,latin", [("XIX аср", "XIX asr"), ("Пётр I", "Pyotr I"), ("IV боб", "IV bob")])
def test_roman_numerals_cyrillic_to_latin_are_already_latin(cyrillic, latin, target):
    assert convert(cyrillic, CYRILLIC, target) == latin
    assert convert(cyrillic, "auto", target) == latin


@pytest.mark.parametrize("source", (CYRILLIC, "auto"))
def test_roman_numerals_in_cyrillic_text_stay(source):
    assert convert("XIX аср ва Пётр I", source, CYRILLIC) == "XIX аср ва Пётр I"


def test_roman_numerals_latin_to_latin():
    assert convert("XIX asr, I. Boʻriyev", LATIN_1995, LATIN_2026) == "XIX asr, I. Böriyev"
    assert convert("XIX asr, I. Böriyev", LATIN_2026, LATIN_1995) == "XIX asr, I. Boʻriyev"


def test_roman_numerals_in_a_2026_text():
    assert to_cyrillic("XIX asr Toşkentda") == "XIX аср Тошкентда"


def test_roman_numerals_in_a_protected_span():
    text = "https://shahar.uz/XIX-asr va XIX asr"
    assert to_cyrillic(text) == "https://shahar.uz/XIX-asr ва XIX аср"
    assert convert("IV", LATIN_1995, CYRILLIC, protect=False) == "IV"


@pytest.mark.parametrize(
    "word,after,previous,following,expected",
    [
        ("XIX", "", "", "", True),
        ("MMMCMXCIX", "", "", "", True),
        ("II", " ", "", "harfi", True),
        ("XIX", ".", "", "", True),
        ("I", "", "", "", False),
        ("I", " ", "", "", False),
        ("I", ".", "", "", False),
        ("I", " ", "", "asr", True),
        ("I", " ", "", "Asrlar", True),
        ("I", " ", "", "bo'lim", True),
        ("I", " ", "", "BOʼLIM", True),
        ("I", " ", "", "bōlim", True),  # o with macron: ö in latin_2026
        ("I", " ", "", "çaqiriq", True),
        ("I", " ", "", "kvartal", True),
        ("I", " ", "", "Xalqaro", True),
        ("I", " ", "", "o'rinni", True),
        ("I", " ", "", "örin", True),
        ("I", " ", "", "yarmi", True),
        ("I", "-", "", "asr", True),  # the caller passes the word after a hyphen
        ("I", " ", "", "harfi", False),
        ("I", " ", "", "as", False),
        ("I", "", "Pyotr", "", True),
        ("I", ",", "Pyotr", "", True),
        ("I", ".", "Pyotr", "", False),
        ("I", " ", "Pyotr", "harfi", False),
        ("V", " ", "Lotin", "Harflari", False),
        ("X", " ", "", "TOVUSHI", False),
        ("X", " ", "", "tovuşi", False),
        ("X", " ", "", "harakat", False),
        ("X", " ", "Pyotr", "harakat", True),
        ("L", " ", "", "asr", False),
        ("C", "", "Pyotr", "", False),
        ("D", " ", "", "guruhida", False),
        ("M", " ", "Karl", "toifa", False),
        ("I", "", "Пётр", "", True),
        ("I", "", "pyotr", "", False),
        ("I", "", "A", "", False),
        ("I", "", "Oʻ", "", False),
        ("I", "", "Ab", "", True),
        ("", "", "Pyotr", "asr", False),
        ("IIII", "", "Pyotr", "asr", False),
        ("MMMM", "", "", "", False),
        ("xix", "", "", "", False),
        ("XIx", "", "", "", False),
        ("IC", "", "", "", False),
        ("i", " ", "Pyotr", "asr", False),
    ],
)
def test_is_roman_numeral(word, after, previous, following, expected):
    assert is_roman_numeral(word, after, previous, following) is expected


def test_is_roman_numeral_takes_the_character_after_alone():
    assert is_roman_numeral("XIX") is True
    assert is_roman_numeral("XIX", ".") is True
    assert is_roman_numeral("I") is False
    assert is_roman_numeral("I", ".") is False


# (a) after a hyphen: the word after one letter counts after one space, U+00A0, a
# hyphen or U+2011; the word before it, for (b), after one space or U+00A0 only.
HYPHENATED = [
    ("V-asr", "V-аср"),
    ("I-jahon urushi", "I-жаҳон уруши"),
    (f"X{NB_HYPHEN}sinf", f"X{NB_HYPHEN}синф"),
    ("I-kvartal", "I-квартал"),
    ("V-harfi", "В-ҳарфи"),  # harf counts after a hyphen too
    ("D-guruh", "Д-гуруҳ"),
    ("V‐asr", "В‐аср"),  # U+2010 is not one of them
    ("V–asr", "В–аср"),
    ("V- asr", "В- аср"),
    ("V -asr", "В -аср"),
    ("Pyotr-I", "Пётр-И"),
    (f"Pyotr{NB_HYPHEN}I", f"Пётр{NB_HYPHEN}И"),
]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("latin,cyrillic", HYPHENATED)
def test_one_letter_and_a_hyphen(latin, cyrillic, source):
    if source == LATIN_2026:
        latin = convert(latin, LATIN_1995, LATIN_2026)  # urushi -> uruşi
    assert convert(latin, source, CYRILLIC) == cyrillic


# Series: numerals linked by a dash with no space around it or with one space on each
# side, a comma and one space, or va or yoki in any case with one space on each side,
# go together.
SERIES = [
    # The 0.3.2c task.
    ("V–VI asrlar", "V–VI асрлар"),
    ("X–XII asrlarda", "X–XII асрларда"),
    ("I-II kurs talabalari", "I-II курс талабалари"),
    ("I–V asrlar", "I–V асрлар"),
    ("I, II va III boblar", "I, II ва III боблар"),
    ("I va II jahon urushlari", "I ва II жаҳон урушлари"),
    ("I yoki II guruh", "I ёки II гуруҳ"),
    ("V, X va XV asrlar", "V, X ва XV асрлар"),
    ("I–II.", "I–II."),
    ("V–VI", "V–VI"),
    ("V va X", "В ва Х"),  # no member is a numeral on its own
    ("I. Karimov va V. Ivanov", "И. Каримов ва В. Иванов"),
    ("Karimov I. va Ivanov V.", "Каримов И. ва Иванов В."),
    # One member a numeral on its own: two letters, (a) or (b).
    ("V va X asrlar", "V ва X асрлар"),
    ("Karl V va X", "Карл V ва X"),
    ("I, I, I va II", "I, I, I ва II"),
    ("Pyotr I, II", "Пётр I, II"),
    ("Тошкент I–II асрлар, V va VI", "Тошкент I–II асрлар, V ва VI"),
    # U+00A0 for the space.
    ("V,\N{NO-BREAK SPACE}X va XV asrlar", "V,\N{NO-BREAK SPACE}X ва XV асрлар"),
    ("I\N{NO-BREAK SPACE}va\N{NO-BREAK SPACE}II", "I\N{NO-BREAK SPACE}ва\N{NO-BREAK SPACE}II"),
    # What is not a member: one letter before a full stop, and one L, C, D or M.
    ("II va V.", "II ва В."),
    ("V.–VI", "В.–VI"),
    ("L–LI", "Л–LI"),
    ("C–CI", "C–CI"),
    ("D va DI", "Д ва DI"),
    ("M, MI", "М, MI"),
    # Section 2 of the 0.3.2d task: a dash with one space or U+00A0 on each side links,
    # and va or yoki in any case.
    ("V – VI asrlar", "V – VI асрлар"),
    ("V - VI asrlar", "V - VI асрлар"),
    ("V — VI asrlar", "V — VI асрлар"),
    ("I\N{NO-BREAK SPACE}–\N{NO-BREAK SPACE}II kurs", "I\N{NO-BREAK SPACE}–\N{NO-BREAK SPACE}II курс"),
    ("I VA II JAHON URUSHLARI", "I ВА II ЖАҲОН УРУШЛАРИ"),
    ("I Va II", "I Ва II"),
    ("I YOKI II GURUH", "I ЁКИ II ГУРУҲ"),
    ("X – nomaʼlum, V – tezlik", "Х – номаълум, В – тезлик"),  # no numeral after the dash
    ("Pyotr I – rus podshosi", "Пётр I – рус подшоси"),  # as before
    # A spaced dash links only a member, and like the other links.
    ("X – nomaʼlum, V – tezlik, XX asr", "Х – номаълум, В – тезлик, XX аср"),
    ("I – II asrlar", "I – II асрлар"),
    ("I – II va III boblar", "I – II ва III боблар"),
    ("V – X", "В – Х"),  # no member is a numeral on its own
    ("V – VI harflari", "В – VI ҳарфлари"),
    ("I\N{NO-BREAK SPACE}– II", "I\N{NO-BREAK SPACE}– II"),
    ("I Yoki II", "I Ёки II"),
    # What does not link.
    ("I -II asrlar", "И -II асрлар"),
    ("I- II asrlar", "И- II асрлар"),
    ("I  – II asrlar", "И  – II асрлар"),
    ("I –  II asrlar", "И –  II асрлар"),
    ("I –– II asrlar", "И –– II асрлар"),
    ("I II asrlar", "И II асрлар"),
    ("I,II", "И,II"),
    ("I ,II", "И ,II"),
    ("I,  II", "И,  II"),
    ("I  va II", "И  ва II"),
    ("I va  II", "И ва  II"),
    ("I VA  II", "И ВА  II"),
    ("I va-II", "И ва-II"),
    ("I ham II", "И ҳам II"),
    ("I va asr II", "И ва аср II"),
    # harf or tovush after the series: every member of one letter is a letter, even
    # one that is a numeral on its own (0.3.2d); two letters or more stay numerals.
    ("V, X va XV harflari", "В, Х ва XV ҳарфлари"),
    ("V–VI harflari", "В–VI ҳарфлари"),
    ("V yoki X tovushi", "В ёки Х товуши"),
    ("Nikolay I, V harfi", "Николай И, В ҳарфи"),  # known limit (README)
    ("Karl V, X harfi", "Карл В, Х ҳарфи"),
    ("Lotin V va X harflari", "Лотин В ва Х ҳарфлари"),
    ("V–VI-harflar", "В–VI-ҳарфлар"),
    ("V–VI asrlar harflari", "V–VI асрлар ҳарфлари"),  # not the word after the series
]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("latin,cyrillic", SERIES)
def test_roman_numerals_in_a_series(latin, cyrillic, source):
    if source == LATIN_2026:
        latin = convert(latin, LATIN_1995, LATIN_2026)  # urushlari -> uruşlari
    assert convert(latin, source, CYRILLIC) == cyrillic


# Section 1 of the 0.3.2d task: harf or tovush after a series makes every member of
# one letter a letter, one that (a) or (b) makes a numeral on its own too; members of
# two letters or more stay numerals.
SERIES_BEFORE_HARF = [
    ("Ushbu V va X harflari", "Ушбу В ва Х ҳарфлари"),  # (b): Ushbu, first word of a sentence
    ("Lotin V va X harflari", "Лотин В ва Х ҳарфлари"),
    ("Lotin V, X harflari", "Лотин В, Х ҳарфлари"),
    ("V, X va XV harflari", "В, Х ва XV ҳарфлари"),  # as before
    ("Nikolay I, V harfi", "Николай И, В ҳарфи"),  # known limit (README)
    ("Pyotr I yoki V TOVUSHLARI", "Пётр И ёки В ТОВУШЛАРИ"),
    ("Lotin V\N{NO-BREAK SPACE}va X\N{NO-BREAK SPACE}Harflari", "Лотин В\N{NO-BREAK SPACE}ва Х\N{NO-BREAK SPACE}Ҳарфлари"),
    ("XX, V va X harflari", "XX, В ва Х ҳарфлари"),
    ("Lotin V va X harflari, Karl V", "Лотин В ва Х ҳарфлари, Карл V"),  # only the series before harf
]

# Section 3 of the 0.3.2d task: as at bfcbb9f.
ROMAN_AS_AT_BFCBB9F = [
    ("Masalan, V va X harflari", "Масалан, В ва Х ҳарфлари"),
    ("Lotin V va X", "Лотин V ва X"),
    ("Karl V, X", "Карл V, X"),
    ("IV – V asrlar", "IV – V асрлар"),
]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("latin,cyrillic", SERIES_BEFORE_HARF + ROMAN_AS_AT_BFCBB9F)
def test_roman_numerals_in_a_series_before_harf_and_as_at_bfcbb9f(latin, cyrillic, source):
    if source == LATIN_2026:
        latin = convert(latin, LATIN_1995, LATIN_2026)  # tovushlari -> tovuşlari
    assert convert(latin, source, CYRILLIC) == cyrillic


@pytest.mark.parametrize("dash", ["-", "\N{HYPHEN}", NB_HYPHEN, "\N{FIGURE DASH}", "\N{EN DASH}", "\N{EM DASH}"])
def test_every_dash_links_a_series(dash):
    assert to_cyrillic(f"I{dash}II asrlar") == f"I{dash}II асрлар"
    assert to_cyrillic(f"V{dash}VI") == f"V{dash}VI"
    assert to_cyrillic(f"V{dash}X{dash}XV") == f"V{dash}X{dash}XV"
    assert to_cyrillic(f"V{dash}X") == f"В{dash}Х"
    assert to_cyrillic(f"V{dash}VI harflari") == f"В{dash}VI ҳарфлари"
    # One space or U+00A0 on each side links too (0.3.2d), on one side only or two do not.
    for a in (" ", NBSP):
        for b in (" ", NBSP):
            assert to_cyrillic(f"V{a}{dash}{b}VI asrlar") == f"V{a}{dash}{b}VI асрлар"
            assert to_cyrillic(f"V{a}{dash}{b}X") == f"В{a}{dash}{b}Х"
            assert to_cyrillic(f"V{a}{dash}{b}tezlik, XV") == f"В{a}{dash}{b}тезлик, XV"
        assert to_cyrillic(f"V{a}{dash}VI") == f"В{a}{dash}VI"
        assert to_cyrillic(f"V{dash}{a}VI") == f"В{dash}{a}VI"
        assert to_cyrillic(f"V{a}{a}{dash} VI") == f"В{a}{a}{dash} VI"
        assert to_cyrillic(f"V {dash}{a}{a}VI") == f"В {dash}{a}{a}VI"


def test_a_series_in_a_2026_text():
    text = "V–VI asrlar, I bölim, I çorak"
    assert convert(text, LATIN_2026, CYRILLIC) == "V–VI асрлар, I бўлим, I чорак"
    assert to_cyrillic(text) == "V–VI асрлар, I бўлим, I чорак"
    assert convert("V–VI asrlar, I boʻlim, I chorak", LATIN_1995, CYRILLIC) == "V–VI асрлар, I бўлим, I чорак"


def test_a_series_in_the_other_directions_and_in_a_protected_span():
    assert convert("V–VI asrlar", LATIN_1995, LATIN_2026) == "V–VI asrlar"
    assert convert("V–VI асрлар", CYRILLIC, CYRILLIC) == "V–VI асрлар"
    assert to_latin("V–VI асрлар, V va X") == "V–VI asrlar, V va X"
    assert to_cyrillic("https://shahar.uz/V–VI va V–VI asrlar") == "https://shahar.uz/V–VI ва V–VI асрлар"
    # A series does not reach across a protected span.
    assert to_cyrillic("V–https://shahar.uz VI") == "В–https://shahar.uz VI"


# The words added to (a) in 0.3.2c: the task's table.
COUNTED_0_3_2C = [
    ("I kvartal", "I квартал"),
    ("I semestr", "I семестр"),
    ("I smenada", "I сменада"),
    ("I kitob", "I китоб"),
    ("I kategoriya", "I категория"),
    ("I oʻrinni egalladi", "I ўринни эгаллади"),
    ("I o'rin", "I ўрин"),
    ("XX asrning I yarmi", "XX асрнинг I ярми"),
    ("I yarim yillik", "I ярим йиллик"),
    ("I Xalqaro ilmiy-amaliy konferensiya", "I Халқаро илмий-амалий конференсия"),
    ("I Respublika anjumani", "I Республика анжумани"),
    ("I kongress", "I конгресс"),
    ("I simpozium", "I симпозиум"),
]


@pytest.mark.parametrize("source", (LATIN_1995, "auto"))
@pytest.mark.parametrize("latin,cyrillic", COUNTED_0_3_2C)
def test_the_new_counted_words(latin, cyrillic, source):
    assert convert(latin, source, CYRILLIC) == cyrillic
    in_2026 = convert(latin, LATIN_1995, LATIN_2026)
    assert convert(in_2026, LATIN_2026, CYRILLIC) == cyrillic


def test_series_take_linear_time():
    start = time.perf_counter()
    for text in ("I, " * 10_000 + "II", "I va " * 10_000 + "II", "V–" * 10_000 + "VI", "I, " * 10_000 + "V"):
        convert(text, LATIN_1995, CYRILLIC)
    assert time.perf_counter() - start < 1


def test_series_with_a_spaced_dash_or_va_in_capitals_take_linear_time():
    start = time.perf_counter()
    for text in ("V – " * 10_000 + "VI", "I VA " * 10_000 + "II"):
        convert(text, LATIN_1995, CYRILLIC)
    assert time.perf_counter() - start < 1


# --- TRANSLIT-26: month names: sentabr, oktabr; the Cyrillic ь restored -----------------

# Cyrillic -> Latin: сентябр and октябр with any suffix, case kept. The other
# months were right already.
CYRILLIC_MONTHS = [
    ("Сентябрь", "Sentabr"),
    ("сентябрда", "sentabrda"),
    ("сентябри", "sentabri"),
    ("октябрнинг", "oktabrning"),
    ("Октябрь", "Oktabr"),
    ("СЕНТЯБРЬ", "SENTABR"),
    ("СЕНТЯБРда", "SENTABRda"),
    ("ноябрь", "noyabr"),
    (
        "январь, февраль, март, апрель, май, июнь, июль, август, декабрь",
        "yanvar, fevral, mart, aprel, may, iyun, iyul, avgust, dekabr",
    ),
]


@pytest.mark.parametrize("target", LATIN)
@pytest.mark.parametrize("source", (CYRILLIC, "auto"))
@pytest.mark.parametrize("cyrillic,latin", CYRILLIC_MONTHS)
def test_month_names_cyrillic_to_latin(cyrillic, latin, source, target):
    assert convert(cyrillic, source, target) == latin


# Latin -> Cyrillic: a month name standing alone takes ь, with a suffix it has
# none; sentabr and oktabr take я.
LATIN_MONTHS = [
    ("yanvar", "январь", "yanvarda", "январда"),
    ("fevral", "февраль", "fevralda", "февралда"),
    ("aprel", "апрель", "aprelda", "апрелда"),
    ("iyun", "июнь", "iyunda", "июнда"),
    ("iyul", "июль", "iyulda", "июлда"),
    ("sentabr", "сентябрь", "sentabrda", "сентябрда"),
    ("sentyabr", "сентябрь", "sentyabrda", "сентябрда"),
    ("oktabr", "октябрь", "oktabrdagi", "октябрдаги"),
    ("oktyabr", "октябрь", "oktyabrdagi", "октябрдаги"),
    ("noyabr", "ноябрь", "noyabrda", "ноябрда"),
    ("dekabr", "декабрь", "dekabrda", "декабрда"),
    ("mart", "март", "martda", "мартда"),
    ("may", "май", "mayda", "майда"),
    ("avgust", "август", "avgustda", "августда"),
]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("alone,alone_cyrillic,suffixed,suffixed_cyrillic", LATIN_MONTHS)
def test_month_names_latin_to_cyrillic(alone, alone_cyrillic, suffixed, suffixed_cyrillic, source):
    assert convert(alone, source, CYRILLIC) == alone_cyrillic
    assert convert(suffixed, source, CYRILLIC) == suffixed_cyrillic


@pytest.mark.parametrize(
    "latin,cyrillic",
    [
        ("SENTABR", "СЕНТЯБРЬ"),
        ("Sentabr", "Сентябрь"),
        ("Iyun", "Июнь"),
        ("SENTABRda", "СЕНТЯБРда"),  # two letter units: the suffix still drops ь
        ("sentabri", "сентябри"),
        ("sentabr, oktabrda", "сентябрь, октябрда"),
        ("Martaba, mayda, iyuncha", "Мартаба, майда, июнча"),  # no ь: not month names alone
    ],
)
def test_month_names_latin_to_cyrillic_case_and_boundaries(latin, cyrillic):
    assert to_cyrillic(latin) == cyrillic


@pytest.mark.parametrize("word", ["январь", "февраль", "апрель", "июнь", "июль", "сентябрь", "октябрь", "ноябрь", "декабрь"])
@pytest.mark.parametrize("latin", LATIN)
def test_month_names_come_back(word, latin):
    """Cyrillic -> Latin -> Cyrillic gives the month name back, ь included."""
    assert convert(convert(word, CYRILLIC, latin), latin, CYRILLIC) == word


@pytest.mark.parametrize("word", ["sentabr", "sentyabr", "oktabrda", "oktyabrda", "yanvar"])
def test_month_names_latin_to_latin_do_not_change(word):
    assert convert(word, LATIN_1995, LATIN_2026) == word
    assert convert(word, LATIN_2026, LATIN_1995) == word


def test_month_names_in_cyrillic_text():
    assert to_cyrillic("Сентябрь ва октябрь") == "Сентябрь ва октябрь"
    assert to_latin("Тошкентда сентябрь ойи") == "Toşkentda sentabr oyi"


def test_month_names_in_a_protected_span():
    assert to_cyrillic("https://shahar.uz/sentabr va sentabr") == "https://shahar.uz/sentabr ва сентябрь"
    assert to_latin("https://shahar.uz/сентябрь ва сентябрь") == "https://shahar.uz/сентябрь va sentabr"


def test_normalize_keeps_its_key():
    """normalize does not change in a patch release (README, Versioning): its
    key for сентябрь is still sentyabr, and cyrillic_word_to_latin_1995, which
    code outside the library builds keys with, reads the word as before."""
    assert normalize("Сентябрь") == "sentyabr"
    assert normalize("октябрнинг") == "oktyabrning"
    assert cyrillic_word_to_latin_1995("сентябрь") == "sentyabr"


# --- TRANSLIT-20: dates: no hyphen after the number in Cyrillic --------------------------

# One date in latin_1995, latin_2026 and Cyrillic.
DATES = [
    ("1991-yilning 1-sentabri", "1991-yilning 1-sentabri", "1991 йилнинг 1 сентябри"),
    ("1956-yil 22-sentabr", "1956-yil 22-sentabr", "1956 йил 22 сентябрь"),
    ("2026-yilda", "2026-yilda", "2026 йилда"),
    ("1941–1945-yillar", "1941–1945-yillar", "1941–1945 йиллар"),  # an en dash before 1945
    ("1990-1991-yillarda", "1990-1991-yillarda", "1990-1991 йилларда"),
    ("1-may", "1-may", "1 май"),
    ("8-martda", "8-martda", "8 мартда"),
    ("9-mayi", "9-mayi", "9 майи"),
    ("31-dekabrgacha", "31-dekabrgaça", "31 декабргача"),
    ("15-iyundagi", "15-iyundagi", "15 июндаги"),
    ("2-oktabrning", "2-oktabrning", "2 октябрнинг"),
    ("21–22-noyabr", "21–22-noyabr", "21–22 ноябрь"),
    ("1-YANVAR, 2026-YIL", "1-YANVAR, 2026-YIL", "1 ЯНВАРЬ, 2026 ЙИЛ"),
    # U+2011 NON-BREAKING HYPHEN and U+00A0 NO-BREAK SPACE stay unbreakable.
    (f"1991{NB_HYPHEN}yil 1{NB_HYPHEN}sentabr", f"1991{NB_HYPHEN}yil 1{NB_HYPHEN}sentabr", f"1991{NBSP}йил 1{NBSP}сентябрь"),
]


@pytest.mark.parametrize("latin_1995,latin_2026,cyrillic", DATES)
def test_dates_latin_to_cyrillic(latin_1995, latin_2026, cyrillic):
    assert convert(latin_1995, LATIN_1995, CYRILLIC) == cyrillic
    assert convert(latin_2026, LATIN_2026, CYRILLIC) == cyrillic
    assert to_cyrillic(latin_1995) == cyrillic


@pytest.mark.parametrize("latin_1995,latin_2026,cyrillic", DATES)
def test_dates_cyrillic_to_latin(latin_1995, latin_2026, cyrillic):
    assert convert(cyrillic, CYRILLIC, LATIN_1995) == latin_1995
    assert convert(cyrillic, CYRILLIC, LATIN_2026) == latin_2026
    assert to_latin(cyrillic, LATIN_1995) == latin_1995
    assert to_latin(cyrillic) == latin_2026


@pytest.mark.parametrize(
    "text,orthography",
    [
        ("1991-йилнинг 1-сентябри", CYRILLIC),
        ("1991-йил", CYRILLIC),
        (f"1991{NB_HYPHEN}йил 1{NB_HYPHEN}сентябрь", CYRILLIC),
        ("1991 йилнинг 1 сентябри", CYRILLIC),
        ("1956 yil 22 sentabr", LATIN_1995),
        ("ilmiy jurnal 2026 yil 12 son", LATIN_1995),
        (f"1956{NBSP}yil 22{NBSP}sentabr", LATIN_1995),
        ("2026 yil 1 iyun", LATIN_2026),
        ("2026-yil 1-iyun", LATIN_2026),
    ],
)
def test_dates_in_their_own_orthography(text, orthography):
    """Within one script the separator is the author's: converting to the
    orthography the text is in leaves it as it is."""
    assert convert(text, orthography, orthography) == text
    assert convert(text, "auto", orthography) == text


@pytest.mark.parametrize(
    "latin_1995,latin_2026",
    [
        ("2026 yil", "2026 yil"),
        ("1956 yil 22 sentabr", "1956 yil 22 sentabr"),
        ("ilmiy jurnal 2026 yil 12 son", "ilmiy jurnal 2026 yil 12 son"),
        ("1991-yilning 1-sentabri", "1991-yilning 1-sentabri"),
        (f"1956{NBSP}yil 22{NBSP}sentabr", f"1956{NBSP}yil 22{NBSP}sentabr"),
        (f"1991{NB_HYPHEN}yil 1{NB_HYPHEN}sentabr", f"1991{NB_HYPHEN}yil 1{NB_HYPHEN}sentabr"),
        ("31 dekabrgacha, 2026 yil", "31 dekabrgaça, 2026 yil"),
    ],
)
def test_dates_latin_1995_to_latin_2026(latin_1995, latin_2026):
    """latin_1995 <-> latin_2026 is one script: the separator stays."""
    assert convert(latin_1995, LATIN_1995, LATIN_2026) == latin_2026
    assert convert(latin_2026, LATIN_2026, LATIN_1995) == latin_1995
    assert to_latin(latin_1995) == latin_2026
    assert to_latin(latin_2026, LATIN_1995) == latin_1995


def test_dates_are_read_in_the_named_source():
    """A word counts in the script it is read in: with a named source, that
    source, whatever its letters (c0307 read as Cyrillic)."""
    assert convert("ilmiy jurnal 2026 yil 12 son", CYRILLIC, LATIN_1995) == "ilmiy jurnal 2026-yil 12 son"
    assert convert("1956 yil 22 sentabr", CYRILLIC, LATIN_2026) == "1956-yil 22-sentabr"
    assert convert("1991-йил", LATIN_1995, CYRILLIC) == "1991 йил"
    assert convert("1991-йил", LATIN_2026, CYRILLIC) == "1991 йил"


# Each is converted from the first to the second; nothing else about the
# separator changes.
DATE_BOUNDARIES = [
    # Other ordinals keep the hyphen in both.
    ("60-yillar", CYRILLIC, "60-йиллар"),
    ("60-йиллар", LATIN_1995, "60-yillar"),
    ("5-sinf, 39-son", CYRILLIC, "5-синф, 39-сон"),
    ("5-синф, 39-сон", LATIN_1995, "5-sinf, 39-son"),
    # A small number before yil is a count in Latin: no hyphen added.
    ("5 yil ishladi", CYRILLIC, "5 йил ишлади"),
    ("5 йил ишлади", LATIN_1995, "5 yil ishladi"),
    ("476 йил", LATIN_1995, "476 yil"),
    ("2100 йил", LATIN_1995, "2100 yil"),
    # Three digits are a year to Cyrillic, below 1000 they are not to Latin.
    ("476-yil", CYRILLIC, "476 йил"),
    # Known limit: a count of 1000 to 2099 years is read as a year.
    ("2000 йил давомида", LATIN_1995, "2000-yil davomida"),
    ("2000 йиллик тарих", LATIN_1995, "2000-yillik tarix"),
    # Not a day of a month, not a number as written, not one separator.
    ("32 sentabr", CYRILLIC, "32 сентябрь"),
    ("32 сентябрь", LATIN_1995, "32 sentabr"),
    ("32-sentabr", CYRILLIC, "32-сентябрь"),
    ("01-sentabr, 0991-yil, 12345-yil", CYRILLIC, "01-сентябрь, 0991-йил, 12345-йил"),
    ("1991  йил", LATIN_1995, "1991  yil"),
    ("1991 - yil", CYRILLIC, "1991 - йил"),
    ("№1991-yil", CYRILLIC, "№1991 йил"),
    ("1,5-yil", CYRILLIC, "1,5-йил"),
    # Words that begin like a month name but are not one: no date.
    ("3 марта", LATIN_1995, "3 marta"),
    ("5-martaba, 2-maydon", CYRILLIC, "5-мартаба, 2-майдон"),
    ("5-мартаба, 2-майдон", LATIN_1995, "5-martaba, 2-maydon"),
    # mayda is May with -da here; it is also "small" (5 майда тош): read as May.
    ("5 майда", LATIN_1995, "5-mayda"),
]


@pytest.mark.parametrize("text,target,expected", DATE_BOUNDARIES)
def test_date_boundaries(text, target, expected):
    assert convert(text, "auto", target) == expected


def test_a_letter_or_digit_before_the_number():
    assert dates("ҳ1991-йил", CYRILLIC) == "ҳ1991-йил"
    assert dates("21991-йил", CYRILLIC) == "21991-йил"
    assert dates("x1991 yil", LATIN_1995) == "x1991 yil"
    assert dates("_1991 yil", LATIN_1995) == "_1991-yil"


def test_dates_only_before_a_word_from_the_other_script():
    # crossed: where a word read in the other script starts.
    assert dates("1991-йил", CYRILLIC, set()) == "1991-йил"
    assert dates("1991-йил", CYRILLIC, {5}) == "1991 йил"
    assert dates("1991-йил 1991-йил", CYRILLIC, {14}) == "1991-йил 1991 йил"
    assert dates("1991 yil 1 sentabr", LATIN_1995, {5}) == "1991-yil 1 sentabr"
    assert dates("1991 yil 1 sentabr", LATIN_1995, {11}) == "1991 yil 1-sentabr"


def test_dates_with_source_auto():
    assert to_cyrillic("Toşkentda 2026-yil 1-sentabr") == "Тошкентда 2026 йил 1 сентябрь"
    assert to_latin("1991 йил 1 сентябрда", LATIN_1995) == "1991-yil 1-sentabrda"
    # Mostly Cyrillic: a Latin word that shows nothing is read as Cyrillic and
    # stays, and a date in Cyrillic is in its own script: both keep the hyphen.
    assert to_cyrillic("Тошкентда 2026-йил ва 2026-yil") == "Тошкентда 2026-йил ва 2026-yil"
    # Each date by the script its word is read in.
    assert to_latin("1956 йил va 1956 yil", LATIN_1995) == "1956-yil va 1956 yil"
    assert to_latin("1956 йил va 1956 yil") == "1956-yil va 1956 yil"
    assert to_cyrillic("1956-yil va 1956-йил") == "1956 йил ва 1956-йил"
    assert to_cyrillic("1 sentabr, 1-сентябрь, 1-sentabr") == "1 сентябрь, 1-сентябрь, 1 сентябрь"


def test_dates_in_a_protected_span():
    assert to_cyrillic("https://shahar.uz/1991-yil va 1991-yil") == "https://shahar.uz/1991-yil ва 1991 йил"
    assert to_latin('<a title="1991 йил">1991 йил</a>', LATIN_1995) == '<a title="1991 йил">1991-yil</a>'
    # The number and the word must be in one piece of text between protected spans.
    assert to_cyrillic("<b>1991</b>-yil") == "<b>1991</b>-йил"
    assert convert("https://x.uz/1991-yil", LATIN_1995, CYRILLIC, protect=False) == "ҳттпс://х.уз/1991 йил"


@pytest.mark.parametrize("latin", LATIN)
def test_a_cyrillic_date_with_a_hyphen_comes_back_without_it(latin):
    """Cyrillic -> Latin -> Cyrillic writes the date as the 1956 rules do
    (tests/test_roundtrip.py has the form without the hyphen)."""
    text = "Тошкент давлат университети, 2026-йил"
    assert convert(convert(text, CYRILLIC, latin), latin, CYRILLIC) == "Тошкент давлат университети, 2026 йил"


def test_dates_take_linear_time():
    text = "1" * 200_000 + "-йил " + "1-" * 100_000 + "1 " * 100_000
    start = time.perf_counter()
    for target in (CYRILLIC, LATIN_1995):
        dates(text, target)
    assert time.perf_counter() - start < 1


# --- TRANSLIT-25: a word-final ц is s -------------------------------------------------

FINAL_TS = [
    ("марганец", "marganes"),
    ("ненец", "nenes"),
    ("шприц", "shpris"),
    ("кварц", "kvars"),  # s before, s now
    ("ненецлар", "neneslar"),
    ("шприцни", "shprisni"),
    ("ненецларнинг", "neneslarning"),
    ("ненецларимизга", "neneslarimizga"),
    ("шприцдаги", "shprisdagi"),
    ("шприцгача", "shprisgacha"),
    ("МАРГАНЕЦ", "MARGANES"),
    ("Марганец", "Marganes"),
    ("Кац, Швец", "Kas, Shves"),  # surnames too (README)
]

# Not at the end, and not before Uzbek suffixes only: as before.
TS_AS_BEFORE = [
    ("лицей", "litsey"),
    ("боцман", "botsman"),  # ман is not one of the suffixes
    ("плацдарм", "platsdarm"),
    ("пицца", "pitssa"),
    ("милиция", "militsiya"),
    ("цирк", "sirk"),
    ("функция", "funksiya"),
    ("шприци", "shpritsi"),  # the possessive -i alone is not one of the suffixes
]


@pytest.mark.parametrize("source", (CYRILLIC, "auto"))
@pytest.mark.parametrize("cyrillic,latin", FINAL_TS + TS_AS_BEFORE)
def test_ts_cyrillic_to_latin_1995(cyrillic, latin, source):
    assert convert(cyrillic, source, LATIN_1995) == latin


@pytest.mark.parametrize("cyrillic,latin", [("шприц", "şpris"), ("шприцни", "şprisni"), ("марганец", "marganes")])
def test_ts_cyrillic_to_latin_2026(cyrillic, latin):
    assert convert(cyrillic, CYRILLIC, LATIN_2026) == latin
    assert to_latin(cyrillic) == latin


def test_ts_latin_to_cyrillic_does_not_change():
    """Known loss (README): marganes comes back as марганес."""
    assert to_cyrillic("marganes") == "марганес"
    assert to_cyrillic("neneslar va shpris") == "ненеслар ва шприс"
    assert to_cyrillic("litsey, botsman") == "лицей, боцман"


def test_ts_in_cyrillic_text_and_in_a_protected_span():
    assert to_cyrillic("марганец") == "марганец"
    assert to_latin("https://shahar.uz/марганец ва марганец", LATIN_1995) == "https://shahar.uz/марганец va marganes"


def test_normalize_keeps_its_key_for_ts():
    """normalize does not change in a patch release: марганец is still
    marganets there, and so in cyrillic_word_to_latin_1995."""
    assert normalize("Марганец") == "marganets"
    assert normalize("шприцни") == "shpritsni"
    assert cyrillic_word_to_latin_1995("марганец") == "marganets"


def test_ts_takes_linear_time():
    start = time.perf_counter()
    convert("ц" * 200_000, CYRILLIC, LATIN_1995)
    convert("а" + "цлар" * 50_000, CYRILLIC, LATIN_1995)
    assert time.perf_counter() - start < 1


# --- the golden inputs added in 0.3.2 ---------------------------------------------------

# --- to_ascii: U+2011 is a hyphen ----------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        # c1211: the date converted to Latin has U+2011, which to_ascii writes as -.
        (f"1956{NBSP}йил 22{NBSP}сентябрь", "1956-yil 22-sentabr"),
        (f"1991{NB_HYPHEN}yil 1{NB_HYPHEN}sentabr", "1991-yil 1-sentabr"),  # c1210
        (f"1991{NB_HYPHEN}йил", "1991-yil"),
        (f"a{NB_HYPHEN}b", "a-b"),
        # U+00A0 is a space, as in 0.3.1 (NFKD).
        (f"1991{NBSP}yil", "1991 yil"),
        (f"a{NBSP}b", "a b"),
        ("1956 йил 22 сентябрь", "1956-yil 22-sentabr"),
    ],
)
def test_to_ascii_writes_the_non_breaking_hyphen_as_a_hyphen(text, expected):
    assert to_ascii(text) == expected


def test_to_ascii_after_to_latin():
    latin = to_latin(f"1956{NBSP}йил 22{NBSP}сентябрь", LATIN_1995)
    assert latin == f"1956{NB_HYPHEN}yil 22{NB_HYPHEN}sentabr"
    assert to_ascii(latin) == "1956-yil 22-sentabr"
    assert to_ascii(to_latin("1956 йил 22 сентябрь", LATIN_1995)) == "1956-yil 22-sentabr"


GOLDEN_INPUTS = Path(__file__).resolve().parent.parent / "golden" / "inputs.json"

# id -> (text, tag, orthography), and (to_cyrillic, to_latin_1995,
# to_latin_2026), where None is the text itself.
NEW_INPUTS = {
    "c1189": ("XIX asr", "roman", "latin_1995", ("XIX аср", None, None)),
    "c1190": ("IV bob, Pyotr I", "roman", "latin_1995", ("IV боб, Пётр I", None, None)),
    "c1191": ("I. Boʻriyev va M. Asadullayev", "roman", "latin_1995",
              ("И. Бўриев ва М. Асадуллаев", None, "I. Böriyev va M. Asadullayev")),
    "c1192": ("Pyotr I.", "roman", "latin_1995", ("Пётр И.", None, None)),
    "c1193": ("MIX", "roman", "latin_1995", (None, None, None)),
    "c1194": ("XIX аср ва Пётр I", "roman", "cyrillic", (None, "XIX asr va Pyotr I", "XIX asr va Pyotr I")),
    "c1195": ("CD va DVD, IIII, Xix, XIXda", "roman", "latin_1995", ("CD ва ДВД, ИИИИ, Хих, ХИХда", None, None)),
    "c1196": ("XXI asr Toşkentda", "roman", "latin_2026", ("XXI аср Тошкентда", "XXI asr Toshkentda", None)),
    "c1197": ("Сентябрь, сентябрда, октябрнинг, ноябрь", "month", "cyrillic",
              (None, "Sentabr, sentabrda, oktabrning, noyabr", "Sentabr, sentabrda, oktabrning, noyabr")),
    "c1198": ("СЕНТЯБРЬ, СЕНТЯБРда", "month", "cyrillic", (None, "SENTABR, SENTABRda", "SENTABR, SENTABRda")),
    "c1199": ("yanvar fevral mart aprel may iyun iyul avgust sentabr oktabr noyabr dekabr", "month", "latin_1995",
              ("январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь", None, None)),
    "c1200": ("yanvarda fevralda aprelda iyunda iyulda sentabrda sentyabrda oktabrdagi noyabrda dekabrda",
              "month", "latin_1995",
              ("январда февралда апрелда июнда июлда сентябрда сентябрда октябрдаги ноябрда декабрда", None, None)),
    "c1201": ("SENTABR, Sentyabr, SENTABRda, sentabri", "month", "latin_1995",
              ("СЕНТЯБРЬ, Сентябрь, СЕНТЯБРда, сентябри", None, None)),
    "c1202": ("Martaba, mayda, iyuncha", "month", "latin_1995", ("Мартаба, майда, июнча", None, "Martaba, mayda, iyunça")),
    "c1203": ("1991-yilning 1-sentabri", "date", "latin_1995", ("1991 йилнинг 1 сентябри", None, None)),
    "c1204": ("1956 йил 22 сентябрь", "date", "cyrillic", (None, "1956-yil 22-sentabr", "1956-yil 22-sentabr")),
    "c1205": ("1991-йилнинг 1-сентябри", "date", "cyrillic",
              (None, "1991-yilning 1-sentabri", "1991-yilning 1-sentabri")),
    "c1206": ("1956 yil 22 sentabr", "date", "latin_1995", ("1956 йил 22 сентябрь", None, None)),
    "c1207": ("5 yil ishladi", "date", "latin_1995", ("5 йил ишлади", None, "5 yil işladi")),
    "c1208": ("2000 йил давомида", "date", "cyrillic", (None, "2000-yil davomida", "2000-yil davomida")),
    "c1209": ("32 sentabr, 32-сентябрь", "date", "mixed",
              (None, "32 sentabr, 32-sentabr", "32 sentabr, 32-sentabr")),
    "c1210": (f"1991{NB_HYPHEN}yil 1{NB_HYPHEN}sentabr", "date", "latin_1995",
              (f"1991{NBSP}йил 1{NBSP}сентябрь", None, None)),
    "c1211": (f"1956{NBSP}йил 22{NBSP}сентябрь", "date", "cyrillic",
              (None, f"1956{NB_HYPHEN}yil 22{NB_HYPHEN}sentabr", f"1956{NB_HYPHEN}yil 22{NB_HYPHEN}sentabr")),
    "c1212": ("60-yillar, 5-sinf, 39-son", "date", "latin_1995", ("60-йиллар, 5-синф, 39-сон", None, None)),
    "c1213": ("60-йиллар, 5-синф, 39-сон", "date", "cyrillic",
              (None, "60-yillar, 5-sinf, 39-son", "60-yillar, 5-sinf, 39-son")),
    # Mostly Cyrillic: the Latin yil stays as it is in Cyrillic, and so does its hyphen.
    "c1214": ("476-yil, 476 йил, 2100 йил", "date", "mixed",
              (None, "476-yil, 476 yil, 2100 yil", "476-yil, 476 yil, 2100 yil")),
    "c1215": ("3 марта, 5-мартаба, 2-майдон, 5 майда", "date", "cyrillic",
              (None, "3 marta, 5-martaba, 2-maydon, 5-mayda", "3 marta, 5-martaba, 2-maydon, 5-mayda")),
    "c1216": ("1941–1945-yillar, 1990-1991-yillarda, 21–22-noyabr", "date", "latin_1995",
              ("1941–1945 йиллар, 1990-1991 йилларда, 21–22 ноябрь", None, None)),
    "c1217": ("8-martda, 9-mayi, 31-dekabrgacha, 15-iyundagi", "date", "latin_1995",
              ("8 мартда, 9 майи, 31 декабргача, 15 июндаги", None, "8-martda, 9-mayi, 31-dekabrgaça, 15-iyundagi")),
    "c1218": ("1-YANVAR, 2026-YIL", "date", "latin_1995", ("1 ЯНВАРЬ, 2026 ЙИЛ", None, None)),
    "c1219": ("https://x.uz/1991-yil va 1991-yil", "date", "latin_1995", ("https://x.uz/1991-yil ва 1991 йил", None, None)),
    "c1220": ("01-sentabr, 0991-yil, 12345-yil, 1991  yil, №1991-yil", "date", "latin_1995",
              ("01-сентябрь, 0991-йил, 12345-йил, 1991  йил, №1991 йил", None, None)),
    "c1221": ("Toşkentda 2026-yil 1-sentabr", "date", "latin_2026",
              ("Тошкентда 2026 йил 1 сентябрь", "Toshkentda 2026-yil 1-sentabr", None)),
    "c1222": ("марганец, ненец, шприц, кварц", "ts", "cyrillic",
              (None, "marganes, nenes, shpris, kvars", "marganes, nenes, şpris, kvars")),
    "c1223": ("ненецлар, шприцни, ненецларнинг, шприцдаги", "ts", "cyrillic",
              (None, "neneslar, shprisni, neneslarning, shprisdagi", "neneslar, şprisni, neneslarning, şprisdagi")),
    "c1224": ("лицей, боцман, плацдарм, пицца, шприци", "ts", "cyrillic",
              (None, "litsey, botsman, platsdarm, pitssa, shpritsi", "litsey, botsman, platsdarm, pitssa, şpritsi")),
    "c1225": ("МАРГАНЕЦ, Марганец", "ts", "cyrillic", (None, "MARGANES, Marganes", "MARGANES, Marganes")),
    "c1226": ("marganes, neneslar, shpris", "ts", "latin_1995", ("марганес, ненеслар, шприс", None, "marganes, neneslar, şpris")),
    # One letter is a numeral only in context; a date's separator stays within one script.
    "c1227": ("V harfi", "roman", "latin_1995", ("В ҳарфи", None, None)),
    "c1228": ("V asr", "roman", "latin_1995", ("V аср", None, None)),
    "c1229": ("I jahon urushi", "roman", "latin_1995", ("I жаҳон уруши", None, "I jahon uruşi")),
    "c1230": ("Nikolay I", "roman", "latin_1995", ("Николай I", None, None)),
    "c1231": ("X", "roman", "latin_1995", ("Х", None, None)),
    "c1232": ("2026 yil", "date", "latin_1995", ("2026 йил", None, None)),
    "c1233": ("1991-йил", "date", "cyrillic", (None, "1991-yil", "1991-yil")),
    # 0.3.2c: one letter is I, V or X; harf and tovush; a hyphen; series; more counted words.
    "c1234": ("V–VI asrlar", "roman", "latin_1995", ("V–VI асрлар", None, None)),
    "c1235": ("X–XII asrlarda", "roman", "latin_1995", ("X–XII асрларда", None, None)),
    "c1236": ("I-II kurs talabalari", "roman", "latin_1995", ("I-II курс талабалари", None, None)),
    "c1237": ("I, II va III boblar", "roman", "latin_1995", ("I, II ва III боблар", None, None)),
    "c1238": ("I va II jahon urushlari", "roman", "latin_1995",
              ("I ва II жаҳон урушлари", None, "I va II jahon uruşlari")),
    "c1239": ("V va X harflari", "roman", "latin_1995", ("В ва Х ҳарфлари", None, None)),
    "c1240": ("Lotin V harfi", "roman", "latin_1995", ("Лотин В ҳарфи", None, None)),
    "c1241": ("D guruhida, M harfi", "roman", "latin_1995", ("Д гуруҳида, М ҳарфи", None, None)),
    "c1242": ("V-asr, I-jahon urushi", "roman", "latin_1995", ("V-аср, I-жаҳон уруши", None, "V-asr, I-jahon uruşi")),
    "c1243": ("I kvartal, I semestr, I smenada", "roman", "latin_1995", ("I квартал, I семестр, I сменада", None, None)),
    "c1244": ("I oʻrinni egalladi", "roman", "latin_1995", ("I ўринни эгаллади", None, "I örinni egalladi")),
    "c1245": ("XX asrning I yarmi", "roman", "latin_1995", ("XX асрнинг I ярми", None, None)),
    "c1246": ("I Xalqaro ilmiy-amaliy konferensiya", "roman", "latin_1995",
              ("I Халқаро илмий-амалий конференсия", None, None)),
    "c1247": ("I. Karimov va V. Ivanov", "roman", "latin_1995", ("И. Каримов ва В. Иванов", None, None)),
    "c1248": ("A, B, C va D toifalar", "roman", "latin_1995", ("А, Б, C ва Д тоифалар", None, None)),
    "c1249": ("V va X", "roman", "latin_1995", ("В ва Х", None, None)),
    "c1250": ("V–VI asrlar, I bölim, I çorak", "roman", "latin_2026",
              ("V–VI асрлар, I бўлим, I чорак", "V–VI asrlar, I boʻlim, I chorak", None)),
    # 0.3.2d: harf after a series; a spaced dash; VA in capitals; a dash before a word.
    "c1251": ("Ushbu V va X harflari", "roman", "latin_1995", ("Ушбу В ва Х ҳарфлари", None, "Uşbu V va X harflari")),
    "c1252": ("Lotin V, X harflari", "roman", "latin_1995", ("Лотин В, Х ҳарфлари", None, None)),
    "c1253": ("V – VI asrlar, V - VI asrlar", "roman", "latin_1995", ("V – VI асрлар, V - VI асрлар", None, None)),
    "c1254": ("I VA II JAHON URUSHLARI", "roman", "latin_1995",
              ("I ВА II ЖАҲОН УРУШЛАРИ", None, "I VA II JAHON URUŞLARI")),
    "c1255": ("X – nomaʼlum, V – tezlik", "roman", "latin_1995", ("Х – номаълум, В – тезлик", None, None)),
    "c1256": ("Nikolay I, V harfi", "roman", "latin_1995", ("Николай И, В ҳарфи", None, None)),
}


def test_the_new_inputs_are_golden_inputs():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    cases = {case["id"]: case for case in doc["cases"]}
    assert [case["id"] for case in doc["cases"]][-len(NEW_INPUTS):] == list(NEW_INPUTS)
    assert {i: (cases[i]["text"], cases[i]["tags"]) for i in NEW_INPUTS} == {
        i: (text, [f"{tag}-0.3.2", orthography]) for i, (text, tag, orthography, _) in NEW_INPUTS.items()
    }


@pytest.mark.parametrize("case_id", sorted(NEW_INPUTS))
def test_the_new_inputs_convert(case_id):
    text, _, _, expected = NEW_INPUTS[case_id]
    got = (to_cyrillic(text), to_latin(text, LATIN_1995), to_latin(text))
    assert got == tuple(text if value is None else value for value in expected)
