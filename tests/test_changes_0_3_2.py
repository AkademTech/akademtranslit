"""Changes in 0.3.2: Roman numerals, month names, dates and a word-final ц.

Each rule has a section: the examples it was made for, its boundaries, the
other direction, ``source="auto"``, and a protected span, which keeps its text
whatever the rule says. ``js/test/changes-0.3.2.test.js`` has the same tables
for the JavaScript port.
"""

from __future__ import annotations

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert, to_cyrillic, to_latin
from akademtranslit.rules import is_roman_numeral

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
