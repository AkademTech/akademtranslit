"""The three alphabets, in their official order."""

from __future__ import annotations

import pytest

from akademtranslit import (
    CYRILLIC_ALPHABET,
    LATIN_1995_ALPHABET,
    LATIN_2026_ALPHABET,
    REFORM_PAIRS,
    TUTUQ,
)

ALPHABETS = {
    "LATIN_2026_ALPHABET": LATIN_2026_ALPHABET,
    "LATIN_1995_ALPHABET": LATIN_1995_ALPHABET,
    "CYRILLIC_ALPHABET": CYRILLIC_ALPHABET,
}


def test_latin_2026_is_in_the_order_of_the_law():
    """A B D E F G Ğ H I J K L M N O Ö P Q R S Ş Ç T U V X Y Z."""
    assert LATIN_2026_ALPHABET == (
        "a", "b", "d", "e", "f", "g", "ğ", "h", "i", "j", "k", "l", "m", "n",
        "o", "ö", "p", "q", "r", "s", "ş", "ç", "t", "u", "v", "x", "y", "z",
    )


def test_latin_1995_puts_the_four_compound_letters_last():
    assert LATIN_1995_ALPHABET == (
        "a", "b", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o",
        "p", "q", "r", "s", "t", "u", "v", "x", "y", "z",
        "oʻ", "gʻ", "sh", "ch",
    )


def test_cyrillic_puts_the_four_uzbek_letters_after_ya():
    assert CYRILLIC_ALPHABET == (
        "а", "б", "в", "г", "д", "е", "ё", "ж", "з", "и", "й", "к", "л", "м",
        "н", "о", "п", "р", "с", "т", "у", "ф", "х", "ц", "ч", "ш", "ъ", "ь",
        "э", "ю", "я", "ў", "қ", "ғ", "ҳ",
    )


@pytest.mark.parametrize(
    "name,length",
    [("LATIN_2026_ALPHABET", 28), ("LATIN_1995_ALPHABET", 28), ("CYRILLIC_ALPHABET", 35)],
)
def test_lengths(name, length):
    assert len(ALPHABETS[name]) == length


@pytest.mark.parametrize("name", sorted(ALPHABETS))
def test_letters_are_unique(name):
    alphabet = ALPHABETS[name]
    assert len(set(alphabet)) == len(alphabet)


@pytest.mark.parametrize("name", sorted(ALPHABETS))
def test_the_tutuq_belgisi_is_not_a_letter(name):
    assert TUTUQ not in ALPHABETS[name]
    assert not any(TUTUQ in letter for letter in ALPHABETS[name])


def test_the_reform_letters_are_in_the_2026_alphabet():
    for _old, new in REFORM_PAIRS:
        assert new in LATIN_2026_ALPHABET


def test_the_reformed_letters_replace_the_compound_ones():
    """Every 1995 letter is a 2026 letter, or the 1995 side of a reform pair."""
    reformed = dict(REFORM_PAIRS)
    for letter in LATIN_1995_ALPHABET:
        assert reformed.get(letter, letter) in LATIN_2026_ALPHABET
