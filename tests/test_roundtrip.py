"""Round-trip guarantees, stated in tiers.

Uzbek Cyrillic and Latin are not in bijection, and pretending otherwise would
make the library wrong rather than convenient. This file states exactly what is
guaranteed and exactly what is not.

Tier 1  latin_1995 <-> latin_2026 is lossless in both directions, always.
Tier 2  cyrillic -> latin -> cyrillic is lossless over the native Uzbek letter
        inventory.
Tier 3  Four Cyrillic letters that occur only in Russian loanwords are lossy by
        design. Those are asserted here as lossy, so a future change that
        silently alters the behaviour fails the suite.
"""

from __future__ import annotations

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert, normalize

# --- tier 1: the two Latin orthographies are in bijection --------------------

LATIN_1995_WORDS = [
    "Oʻzbekiston",
    "Toshkent",
    "Shoshimova",
    "SHOSHIMOVA",
    "Mirzo Ulugʻbek",
    "Alisher Navoiy",
    "ilmiy tadqiqot",
    "Qashqadaryo",
    "togʻ",
    "yogʻ",
    "maʼno",
    "Isʼhoq",
    "choʻqqi",
    "gʻishtli",
    "Oʻzbek tili va adabiyoti",
    "Ilmiy jurnal, 2026-yil, 12-son",
]


@pytest.mark.parametrize("word", LATIN_1995_WORDS)
def test_tier1_1995_to_2026_and_back(word):
    reformed = convert(word, source=LATIN_1995, target=LATIN_2026)
    assert convert(reformed, source=LATIN_2026, target=LATIN_1995) == word


@pytest.mark.parametrize(
    "word",
    # Isʼhoq is excluded on purpose: its "sh" is a separated s+h pair, not the
    # digraph, so it is *supposed* to survive as "sh" in latin_2026.
    [w for w in LATIN_1995_WORDS if "sʼh" not in w],
)
def test_tier1_reform_actually_changes_the_four_letters(word):
    """A round trip through an identity function would also pass the test above."""
    reformed = convert(word, source=LATIN_1995, target=LATIN_2026)
    for digraph in ("sh", "ch", "gʻ", "oʻ"):
        assert digraph not in reformed.lower(), (
            f"{digraph!r} survived the reform in {reformed!r}"
        )


def test_tier1_holds_for_the_reverse_starting_point():
    for word in ["Şoşimova", "Toşkent", "Uluğbek", "Özbekiston", "Ishoq", "iş"]:
        legacy = convert(word, source=LATIN_2026, target=LATIN_1995)
        assert convert(legacy, source=LATIN_1995, target=LATIN_2026) == word


# --- tier 2: Cyrillic round trip over the native inventory -------------------

NATIVE_CYRILLIC = [
    "Тошкент",
    "Самарқанд",
    "Бухоро",
    "Қашқадарё",
    "Сурхондарё",
    "Ўзбекистон Республикаси",
    "Алишер Навоий",
    "Мирзо Улуғбек",
    "Абу Райҳон Беруний",
    "Заҳириддин Муҳаммад Бобур",
    "Шошимова",
    "ШОШИМОВА",
    "илмий тадқиқот",
    "маъно",
    "шеър",
    "тоғ",
    "поезд",
    "тезда",
    "Эркин",
    "эшик",
    "Ер",
    "Исҳоқ",
    "юлдуз",
    "яшил",
    "ҳаёт",
    "Ўзбек тили ва адабиёти",
    "Тошкент давлат университети, 2026-йил",
]


@pytest.mark.parametrize("text", NATIVE_CYRILLIC)
def test_tier2_via_latin_1995(text):
    latin = convert(text, source=CYRILLIC, target=LATIN_1995)
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == text


@pytest.mark.parametrize("text", NATIVE_CYRILLIC)
def test_tier2_via_latin_2026(text):
    latin = convert(text, source=CYRILLIC, target=LATIN_2026)
    assert convert(latin, source=LATIN_2026, target=CYRILLIC) == text


@pytest.mark.parametrize("text", NATIVE_CYRILLIC)
def test_tier2_via_both_latin_orthographies_in_sequence(text):
    """cyrillic -> 1995 -> 2026 -> 1995 -> cyrillic, the migration path."""
    step = convert(text, source=CYRILLIC, target=LATIN_1995)
    step = convert(step, source=LATIN_1995, target=LATIN_2026)
    step = convert(step, source=LATIN_2026, target=LATIN_1995)
    assert convert(step, source=LATIN_1995, target=CYRILLIC) == text


# --- tier 3: documented lossy mappings ---------------------------------------
#
# These are asserted as lossy on purpose. If someone "fixes" one of them, this
# file tells them what they broke and why it was that way.


def test_tier3_shcha_merges_with_sha():
    """щ occurs only in Russian loanwords; both letters give sh."""
    assert convert("щ", source=CYRILLIC, target=LATIN_1995) == "sh"
    assert convert("ш", source=CYRILLIC, target=LATIN_1995) == "sh"
    assert convert("borsh", source=LATIN_1995, target=CYRILLIC) == "борш"


def test_tier3_yeru_merges_with_i():
    assert convert("ы", source=CYRILLIC, target=LATIN_1995) == "i"
    assert convert("и", source=CYRILLIC, target=LATIN_1995) == "i"


def test_tier3_soft_sign_is_not_recoverable():
    assert convert("альбом", source=CYRILLIC, target=LATIN_1995) == "albom"
    assert convert("albom", source=LATIN_1995, target=CYRILLIC) == "албом"


def test_tier3_tse_is_positional_and_not_reversible():
    """ц is ts after a vowel and s otherwise -- a heuristic, not a rule."""
    assert convert("цирк", source=CYRILLIC, target=LATIN_1995) == "sirk"
    assert convert("функция", source=CYRILLIC, target=LATIN_1995) == "funksiya"
    assert convert("концерт", source=CYRILLIC, target=LATIN_1995) == "konsert"
    assert convert("милиция", source=CYRILLIC, target=LATIN_1995) == "militsiya"
    assert convert("революция", source=CYRILLIC, target=LATIN_1995) == "revolyutsiya"
    # The s reading does not survive the return trip -- it is indistinguishable
    # from a genuine с once written.
    assert convert("sirk", source=LATIN_1995, target=CYRILLIC) == "сирк"


# --- idempotence -------------------------------------------------------------


@pytest.mark.parametrize("text", NATIVE_CYRILLIC + LATIN_1995_WORDS)
def test_conversion_to_the_same_script_is_idempotent(text):
    once = convert(text, target=LATIN_2026)
    assert convert(once, source=LATIN_2026, target=LATIN_2026) == once


def test_auto_detection_cannot_resolve_a_separated_s_plus_h():
    """The one place `source="auto"` is not enough, stated as a test.

    "Ishoq" is valid latin_2026 (Исҳоқ) and valid latin_1995 (Ишоқ), and nothing
    in the string says which. Detection picks latin_1995, so a caller who knows
    the orthography from context has to say so.
    """
    assert convert("Ishoq", source=LATIN_2026, target=CYRILLIC) == "Исҳоқ"
    assert convert("Ishoq", source=LATIN_1995, target=CYRILLIC) == "Ишоқ"
    assert convert("Ishoq", target=CYRILLIC) == "Ишоқ"  # auto -> latin_1995


@pytest.mark.parametrize("text", NATIVE_CYRILLIC + LATIN_1995_WORDS)
def test_normalize_is_idempotent(text):
    once = normalize(text)
    assert normalize(once) == once
