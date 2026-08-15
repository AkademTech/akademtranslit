"""Latin -> Cyrillic, from both Latin orthographies, plus the context rules."""

from __future__ import annotations

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert, to_cyrillic

# --- from latin_1995 ---------------------------------------------------------

FROM_1995 = [
    ("Alisher Navoiy", "Алишер Навоий"),
    ("Mirzo Ulugʻbek", "Мирзо Улуғбек"),
    ("Abu Rayhon Beruniy", "Абу Райҳон Беруний"),
    ("Toshkent", "Тошкент"),
    ("Samarqand", "Самарқанд"),
    ("Oʻzbekiston Respublikasi", "Ўзбекистон Республикаси"),
    ("ilmiy tadqiqot", "илмий тадқиқот"),
    ("Qashqadaryo", "Қашқадарё"),
]


@pytest.mark.parametrize("latin,expected", FROM_1995)
def test_from_latin_1995(latin, expected):
    assert to_cyrillic(latin) == expected


# --- from latin_2026 ---------------------------------------------------------

FROM_2026 = [
    ("Alişer Navoiy", "Алишер Навоий"),
    ("Mirzo Uluğbek", "Мирзо Улуғбек"),
    ("Toşkent", "Тошкент"),
    ("Qaşqadaryo", "Қашқадарё"),
    ("Özbekiston Respublikasi", "Ўзбекистон Республикаси"),
    ("Şoşimova", "Шошимова"),
]


@pytest.mark.parametrize("latin,expected", FROM_2026)
def test_from_latin_2026(latin, expected):
    assert to_cyrillic(latin) == expected


# --- the e / ye rule ---------------------------------------------------------
#
# Cyrillic writes one letter, е, for a sound the Latin orthographies write two
# ways depending on position. Getting this wrong is the most visible defect a
# transliterator can have, because it hits everyday words.


@pytest.mark.parametrize(
    "cyrillic,latin",
    [
        ("Ер", "Yer"),           # word-initial -> ye
        ("ер", "yer"),
        ("поезд", "poyezd"),     # after a vowel -> ye
        ("тезда", "tezda"),      # after a consonant -> e
        ("театр", "teatr"),
        ("Эркин", "Erkin"),      # word-initial э -> bare e
        ("эшик", "eshik"),
        ("муаллиф", "muallif"),
    ],
)
def test_e_ye_rule_both_directions(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == cyrillic


# --- ъ and ь -----------------------------------------------------------------


def test_tutuq_belgisi_is_a_letter_not_punctuation():
    """ъ carries meaning in Uzbek words and survives the round trip."""
    assert convert("маъно", source=CYRILLIC, target=LATIN_1995) == "maʼno"
    assert to_cyrillic("maʼno") == "маъно"
    assert convert("аъзо", source=CYRILLIC, target=LATIN_1995) == "aʼzo"
    assert convert("шеър", source=CYRILLIC, target=LATIN_1995) == "sheʼr"


def test_soft_sign_is_dropped():
    """ь appears only in Russian loanwords and has no Latin counterpart."""
    assert convert("альбом", source=CYRILLIC, target=LATIN_1995) == "albom"


# --- the s + h separator -----------------------------------------------------
#
# сҳ must not be read as the sh digraph. latin_1995 separates them with the
# tutuq belgisi; latin_2026 does not need to, because ş carries that sound.


def test_s_plus_h_is_separated_in_1995():
    assert convert("Исҳоқ", source=CYRILLIC, target=LATIN_1995) == "Isʼhoq"
    assert convert("Исҳоқ", source=CYRILLIC, target=LATIN_2026) == "Ishoq"


def test_s_plus_h_survives_the_return_trip():
    assert convert("Isʼhoq", source=LATIN_1995, target=CYRILLIC) == "Исҳоқ"
    assert convert("Ishoq", source=LATIN_2026, target=CYRILLIC) == "Исҳоқ"


def test_the_sh_digraph_is_not_confused_with_the_separated_pair():
    assert convert("иш", source=CYRILLIC, target=LATIN_2026) == "iş"
    assert convert("Исҳоқ", source=CYRILLIC, target=LATIN_2026) == "Ishoq"
    # The two must not collapse into each other.
    assert convert("iş", source=LATIN_2026, target=CYRILLIC) == "иш"
    assert convert("ishoq", source=LATIN_2026, target=CYRILLIC) == "исҳоқ"


# --- apostrophe variants -----------------------------------------------------


@pytest.mark.parametrize(
    "spelling",
    ["Oʻzbekiston", "O'zbekiston", "O’zbekiston", "O‘zbekiston", "O`zbekiston"],
)
def test_every_apostrophe_variant_is_accepted(spelling):
    assert to_cyrillic(spelling) == "Ўзбекистон"


def test_the_two_marks_are_distinguished_by_position():
    """After o/g the mark is part of a letter; elsewhere it is the tutuq belgisi.

    Both are typed as a plain ' by most people, so the distinction has to be
    recovered from context rather than trusted from the input.
    """
    assert to_cyrillic("o'zbek") == "ўзбек"   # turned comma -> ў
    assert to_cyrillic("ma'no") == "маъно"     # tutuq belgisi -> ъ
    assert to_cyrillic("g'alaba") == "ғалаба"


def test_output_uses_the_canonical_marks():
    """Input may be sloppy; output is always U+02BB and U+02BC."""
    assert convert("o'zbek", source=LATIN_1995, target=LATIN_1995) == "oʻzbek"
    assert convert("ma'no", source=LATIN_1995, target=LATIN_1995) == "maʼno"


def test_word_final_turned_comma_is_kept():
    """togʻ, yogʻ, sogʻ -- the mark at the end of a word is a letter, not a quote."""
    assert to_cyrillic("togʻ") == "тоғ"
    assert to_cyrillic("yogʻ") == "ёғ"
    assert convert("тоғ", source=CYRILLIC, target=LATIN_1995) == "togʻ"


def test_a_closing_quote_is_not_mistaken_for_a_letter():
    assert to_cyrillic("'salom'") == "'салом'"
