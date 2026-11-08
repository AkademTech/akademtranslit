"""Rule changes in 0.2.0.

Each section pins one change: the words it fixes, the neighbouring words it
must leave alone, and what it does to the round trip.
"""

from __future__ import annotations

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert, normalize

# --- ъ: dropped where the 1995 spelling drops it ------------------------------
#
# ъ was always the tutuq belgisi, so объект came out as obʼyekt and мўъжиза as
# moʻʼjiza. The 1995 spelling writes no mark in two places: after a consonant
# before е ё ю я, where ъ only separates the consonant from the y sound, and
# after ў.

HARD_SIGN_DROPPED = [
    ("объект", "obyekt"),
    ("подъезд", "podyezd"),
    ("инъекция", "inyeksiya"),
    ("съёмка", "syomka"),
    ("адъютант", "adyutant"),
    ("мўъжиза", "moʻjiza"),
    ("мўътабар", "moʻtabar"),
]

HARD_SIGN_KEPT = [
    ("маъюс", "maʼyus"),     # after a vowel
    ("санъат", "sanʼat"),    # after a consonant, before а
    ("таъсир", "taʼsir"),
    ("маъно", "maʼno"),
    ("шеър", "sheʼr"),
    ("аъзо", "aʼzo"),
    ("қатъий", "qatʼiy"),    # after a consonant, before и
]


@pytest.mark.parametrize("cyrillic,latin", HARD_SIGN_DROPPED)
def test_hard_sign_is_dropped_after_a_consonant_before_ye_or_after_u_breve(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin


@pytest.mark.parametrize("cyrillic,latin", HARD_SIGN_KEPT)
def test_hard_sign_is_the_tutuq_belgisi_everywhere_else(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin


@pytest.mark.parametrize(
    "cyrillic,latin",
    [("объект", "obyekt"), ("мўъжиза", "möjiza"), ("съёмка", "syomka"), ("санъат", "sanʼat")],
)
def test_hard_sign_in_latin_2026(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_2026) == latin


def test_hard_sign_case():
    assert convert("ОБЪЕКТ", source=CYRILLIC, target=LATIN_1995) == "OBYEKT"
    assert convert("Мўъжиза", source=CYRILLIC, target=LATIN_1995) == "Moʻjiza"
    assert convert("МЎЪЖИЗА", source=CYRILLIC, target=LATIN_2026) == "MÖJIZA"


def test_hard_sign_the_reverse_direction_is_unchanged():
    """Latin has nothing to restore ъ from: these come back without it."""
    assert convert("obyekt", source=LATIN_1995, target=CYRILLIC) == "обект"
    assert convert("moʻjiza", source=LATIN_1995, target=CYRILLIC) == "мўжиза"
    assert convert("maʼno", source=LATIN_1995, target=CYRILLIC) == "маъно"


def test_hard_sign_normalize_is_unchanged():
    """normalize() strips the tutuq belgisi anyway, so its keys do not move."""
    assert normalize("объект") == normalize("obyekt") == "obyekt"
    assert normalize("мўъжиза") == normalize("moʻjiza") == "mojiza"
