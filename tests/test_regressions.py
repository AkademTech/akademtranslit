"""Regressions found against 0.1.0, fixed in 0.1.1.

Each section pins one defect: the inputs that exposed it, the neighbouring
words the fix must leave alone, and the round trip the defect broke.
"""

from __future__ import annotations

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert

# The five spellings of the turned comma seen most in real input.
APOSTROPHES = ["ʻ", "'", "‘", "’", "ʼ"]
APOSTROPHE_IDS = ["U+02BB", "ASCII", "U+2018", "U+2019", "U+02BC"]

BOTH_LATINS = [LATIN_1995, LATIN_2026]


def _round_trip(text: str, via: str) -> str:
    latin = convert(text, source=CYRILLIC, target=via)
    return convert(latin, source=via, target=CYRILLIC)


# --- X1: y + oʻ is й + ў, not ё ----------------------------------------------
#
# The ``yo`` row matched before ``oʻ`` could, so yoʻq came out as ёʻқ: the o
# went into ё and the turned comma was stranded.

X1_CASES = [
    ("yoʻq", "йўқ"),
    ("yoʻl", "йўл"),
    ("Yoʻl", "Йўл"),
    ("Yoʻldosh", "Йўлдош"),
    ("yoʻtal", "йўтал"),
]


@pytest.mark.parametrize("mark", APOSTROPHES, ids=APOSTROPHE_IDS)
@pytest.mark.parametrize("latin,expected", X1_CASES)
def test_x1_y_before_o_turned_comma(latin, expected, mark):
    spelled = latin.replace("ʻ", mark)
    assert convert(spelled, source=LATIN_1995, target=CYRILLIC) == expected


def test_x1_from_latin_2026():
    assert convert("yöl", source=LATIN_2026, target=CYRILLIC) == "йўл"


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("boʻyoq", "бўёқ"),   # yo with no mark after it is still ё
        ("qoʻyosh", "қўёш"),
        ("yoz", "ёз"),
    ],
)
def test_x1_yo_without_a_following_mark_is_still_yo(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize("via", BOTH_LATINS)
@pytest.mark.parametrize("text", ["йўқ", "йўл", "Йўлдош", "йўтал"])
def test_x1_round_trip(text, via):
    assert _round_trip(text, via) == text
