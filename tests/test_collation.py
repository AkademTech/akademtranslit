"""sort_key: alphabetical order in each of the three orthographies."""

from __future__ import annotations

import functools
import random

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, sort_key


def _shuffles(items):
    """The list reversed and in a few fixed random orders (never the sorted one)."""
    yield list(reversed(items))
    rng = random.Random(1184)
    for _ in range(5):
        shuffled = list(items)
        rng.shuffle(shuffled)
        yield shuffled


def assert_sorts(expected, orthography):
    key = functools.partial(sort_key, orthography=orthography)
    for shuffled in _shuffles(expected):
        assert sorted(shuffled, key=key) == expected


def primary(text, orthography):
    return sort_key(text, orthography)[0]


# --- latin_2026 --------------------------------------------------------------


@pytest.mark.parametrize(
    "expected",
    [
        ["sabr", "şahar", "çaqmoq", "tabiat"],   # s < ş < ç < t
        ["gul", "ğoz", "hayot"],                 # g < ğ < h
        ["olma", "ördak", "paxta"],              # o < ö < p
        ["bola", "daryo", "ezgu", "fan"],        # no c between b and d any more
    ],
)
def test_latin_2026_order(expected):
    assert_sorts(expected, LATIN_2026)


def test_latin_2026_ignores_case_at_the_primary_level():
    assert_sorts(["Sabr", "şahar", "ÇAQMOQ", "tabiat"], LATIN_2026)
    assert primary("Ördak", LATIN_2026) == primary("ördak", LATIN_2026) == primary("ÖRDAK", LATIN_2026)


def test_latin_2026_reads_the_draft_glyphs_as_o_umlaut():
    assert primary("ōrdak", LATIN_2026) == primary("ördak", LATIN_2026)
    assert primary("ǒrdak", LATIN_2026) == primary("ördak", LATIN_2026)


# --- latin_1995 --------------------------------------------------------------


def test_latin_1995_puts_the_compound_letters_after_z():
    assert_sorts(["zarar", "oʻrik", "gʻoz", "shamol", "choy"], LATIN_1995)


def test_latin_1995_compound_letters_are_single_units():
    # sh is one letter after z, so shamol sorts after every s-word.
    assert_sorts(["sabr", "suv", "zarar", "shamol"], LATIN_1995)
    assert_sorts(["olma", "ota", "oʻrik"], LATIN_1995)


def test_latin_1995_separated_s_and_h_are_two_letters():
    """Isʼhoq is s + h (the tutuq belgisi keeps them apart); Ishonch has sh."""
    assert sort_key("Isʼhoq", LATIN_1995) < sort_key("Ishonch", LATIN_1995)
    assert_sorts(["Isʼhoq", "Ishonch"], LATIN_1995)


def test_latin_1995_apostrophe_variants_have_one_primary_key():
    assert primary("o'rik", LATIN_1995) == primary("oʻrik", LATIN_1995)
    assert primary("o’rik", LATIN_1995) == primary("oʻrik", LATIN_1995)
    assert primary("ma'no", LATIN_1995) == primary("maʼno", LATIN_1995)


def test_the_tutuq_belgisi_is_not_counted():
    assert primary("maʼno", LATIN_1995) == primary("mano", LATIN_1995)


# --- cyrillic ----------------------------------------------------------------


@pytest.mark.parametrize(
    "expected",
    [
        ["ялпиз", "ўрик", "қовун", "ғоз", "ҳаво"],   # Ў Қ Ғ Ҳ after Я
        ["ер", "ёз", "жуда"],                        # е < ё < ж
        ["шамол", "эшик", "юлдуз", "яшил"],
    ],
)
def test_cyrillic_order(expected):
    assert_sorts(expected, CYRILLIC)


def test_russian_only_letters_sort_after_the_whole_alphabet():
    assert_sorts(["ҳаво", "щи"], CYRILLIC)
    assert_sorts(["ҳаво", "ы"], CYRILLIC)
    assert_sorts(["ҳ", "щ"], CYRILLIC)


# --- every orthography -------------------------------------------------------


@pytest.mark.parametrize("orthography", [CYRILLIC, LATIN_1995, LATIN_2026])
def test_a_space_sorts_before_any_letter(orthography):
    assert sort_key("Ali Valiyev", orthography) < sort_key("Alijon", orthography)


@pytest.mark.parametrize("orthography", [LATIN_1995, LATIN_2026])
def test_a_run_of_spaces_counts_once(orthography):
    assert primary("Ali  Valiyev", orthography) == primary("Ali Valiyev", orthography)
    assert primary("Ali\tValiyev", orthography) == primary("Ali Valiyev", orthography)


@pytest.mark.parametrize("orthography", [CYRILLIC, LATIN_1995, LATIN_2026])
def test_digits_sort_before_letters(orthography):
    assert sort_key("2-son", orthography) < sort_key("a", orthography)
    assert sort_key("2-son", orthography) < sort_key("а", orthography)  # Cyrillic а
    assert_sorts(["0", "1", "9", "a"], orthography)


@pytest.mark.parametrize("orthography", [CYRILLIC, LATIN_1995, LATIN_2026])
def test_the_empty_string_sorts_first(orthography):
    assert_sorts(["", "0", "a", "z"], orthography)
    assert sort_key("", orthography) == ((), "")


@pytest.mark.parametrize("orthography", [CYRILLIC, LATIN_1995, LATIN_2026])
def test_punctuation_is_not_counted(orthography):
    assert primary("«Toshkent»", orthography) == primary("Toshkent", orthography)
    assert primary("Toshkent - Samarqand", orthography) == primary("Toshkent Samarqand", orthography)


@pytest.mark.parametrize("orthography", [CYRILLIC, LATIN_1995, LATIN_2026])
def test_ties_are_broken_by_the_text_itself(orthography):
    a, b = sort_key("olma", orthography), sort_key("Olma", orthography)
    assert a[0] == b[0] and a != b
    assert sort_key("  olma ", orthography) == sort_key("olma", orthography)


def test_letters_outside_the_alphabet_sort_after_it():
    assert_sorts(["zarar", "choy", "wifi"], LATIN_1995)
    assert_sorts(["zarar", "wifi"], LATIN_2026)
    assert_sorts(["ҳаво", "Toshkent"], CYRILLIC)


def test_the_key_is_the_nfc_text():
    decomposed = "ördak"
    assert sort_key(decomposed, LATIN_2026) == sort_key("ördak", LATIN_2026)


@pytest.mark.parametrize("bad", ["auto", "latin", "", "LATIN_2026"])
def test_an_unknown_orthography_is_rejected(bad):
    with pytest.raises(ValueError):
        sort_key("olma", bad)


def test_orthography_is_required():
    with pytest.raises(TypeError):
        sort_key("olma")  # type: ignore[call-arg]
