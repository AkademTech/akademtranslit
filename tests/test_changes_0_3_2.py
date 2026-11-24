"""Changes in 0.3.2: Roman numerals, month names, dates and a word-final ц.

Each rule has a section: the examples it was made for, its boundaries, the
other direction, ``source="auto"``, and a protected span, which keeps its text
whatever the rule says. ``js/test/changes-0.3.2.test.js`` has the same tables
for the JavaScript port.
"""

from __future__ import annotations

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert, normalize, to_cyrillic, to_latin
from akademtranslit.rules import cyrillic_word_to_latin_1995, is_roman_numeral

LATIN = (LATIN_1995, LATIN_2026)


# --- TRANSLIT-24: a Roman numeral stays Latin in Cyrillic ------------------------------

ROMAN_NUMERALS = [
    ("XIX asr", "XIX аср"),
    ("IV bob", "IV боб"),
    ("Pyotr I", "Пётр I"),
    ("XXI asrning oxiri", "XXI асрнинг охири"),
    ("MMXXVI", "MMXXVI"),
    ("CD va DVD", "CD ва ДВД"),  # DVD is not a well-formed numeral
    ("XIX.", "XIX."),  # more than one letter: a full stop after it is a full stop
    ("I", "I"),
]

# Boundaries: an initial, a known limit, and what is not a numeral.
NOT_ROMAN_NUMERALS = [
    ("I. Boʻriyev", "И. Бўриев"),
    ("M. Asadullayev", "М. Асадуллаев"),
    ("V. I. Lenin", "В. И. Ленин"),
    ("Pyotr I.", "Пётр И."),  # known limit: read as an initial at the end of a sentence
    ("IIII", "ИИИИ"),
    ("Xix", "Хих"),
    ("XIXda", "ХИХда"),  # a numeral with a suffix in one word is not a numeral word
]


@pytest.mark.parametrize("source", LATIN + ("auto",))
@pytest.mark.parametrize("latin,cyrillic", ROMAN_NUMERALS + NOT_ROMAN_NUMERALS)
def test_roman_numerals_latin_to_cyrillic(latin, cyrillic, source):
    assert convert(latin, source, CYRILLIC) == cyrillic


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
    "word,after,expected",
    [
        ("XIX", "", True),
        ("MMMCMXCIX", "", True),
        ("I", "", True),
        ("I", " ", True),
        ("I", ".", False),
        ("XIX", ".", True),
        ("", "", False),
        ("IIII", "", False),
        ("MMMM", "", False),
        ("xix", "", False),
        ("XIx", "", False),
        ("IC", "", False),
    ],
)
def test_is_roman_numeral(word, after, expected):
    assert is_roman_numeral(word, after) is expected


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
        ("1-sentabr, 2-oktabrda", "1-сентябрь, 2-октябрда"),
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
