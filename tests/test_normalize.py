"""Cross-script normalization -- the search-key contract."""

from __future__ import annotations

import pytest

from akademtranslit import detect_script, normalize
from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026

# --- the headline guarantee --------------------------------------------------
#
# One word, three orthographies, one key. Each group below is a set of spellings
# a search index must treat as the same string.

EQUIVALENCE_GROUPS = [
    # The reform's four letters, one group each.
    ["Şoşimova", "Shoshimova", "Шошимова", "SHOSHIMOVA", "şoşimova"],
    ["Çorshanbiyev", "Chorshanbiyev", "Чоршанбиев"],
    ["Ğafurov", "Gʻafurov", "G'afurov", "Ғафуров", "Gafurov"],
    ["Özbekiston", "Oʻzbekiston", "O'zbekiston", "O’zbekiston", "Ўзбекистон"],
    # Institutions and titles, as they appear across bibliographic records.
    ["Toşkent davlat universiteti", "Toshkent davlat universiteti",
     "Тошкент давлат университети"],
    ["ilmiy tadqiqot", "Ilmiy Tadqiqot", "ИЛМИЙ ТАДҚИҚОТ", "илмий тадқиқот"],
    ["Qaşqadaryo", "Qashqadaryo", "Қашқадарё"],
    ["Uluğbek", "Ulugʻbek", "Улуғбек"],
]


@pytest.mark.parametrize("group", EQUIVALENCE_GROUPS)
def test_all_spellings_share_one_key(group):
    keys = {normalize(spelling) for spelling in group}
    assert len(keys) == 1, f"{group} produced {len(keys)} keys: {sorted(keys)}"


def test_the_readme_example():
    assert normalize("Şoşimova") == normalize("Shoshimova") == normalize("Шошимова")


# --- what the key looks like -------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Oʻzbekiston Respublikasi", "ozbekiston respublikasi"),
        ("Ўзбекистон Республикаси", "ozbekiston respublikasi"),
        ("Özbekiston Respublikasi", "ozbekiston respublikasi"),
        ("Тошкент тиббиёт академияси", "toshkent tibbiyot akademiyasi"),
        ("Toshkent tibbiyot akademiyasi", "toshkent tibbiyot akademiyasi"),
        ("", ""),
        ("   ", ""),
        ("\t\n", ""),
    ],
)
def test_key_shape(text, expected):
    assert normalize(text) == expected


def test_punctuation_and_whitespace_collapse():
    assert normalize("...Toshkent,   davlat!!!") == normalize("Toshkent davlat")
    assert normalize("«Oʻzbekiston» — 2026") == "ozbekiston 2026"


def test_case_is_folded():
    assert normalize("TOSHKENT") == normalize("toshkent") == "toshkent"
    assert normalize("ŞOŞIMOVA") == normalize("şoşimova")


def test_digits_survive():
    """Volume and issue numbers are part of the key, not noise."""
    assert normalize("Ilmiy jurnal, 2026-yil, 12-son") == "ilmiy jurnal 2026 yil 12 son"


# --- homoglyph contamination -------------------------------------------------


def test_a_cyrillic_letter_hiding_in_latin_text_is_folded():
    """Metadata harvested from mixed-script sources carries these constantly."""
    contaminated = "Tаshkent"  # the "а" is Cyrillic U+0430
    assert any("Ѐ" <= ch <= "ӿ" for ch in contaminated)
    assert normalize(contaminated) == normalize("Tashkent")


def test_unmapped_cyrillic_is_dropped_rather_than_leaked():
    assert normalize("aѫb") == "ab"  # ѫ U+046B, big yus


def test_combining_marks_are_composed_first():
    """ö typed as o + combining diaeresis must fold like a precomposed ö."""
    decomposed = "O\u0308zbekiston"   # O + COMBINING DIAERESIS
    precomposed = "\u00d6zbekiston"   # LATIN CAPITAL LETTER O WITH DIAERESIS
    assert decomposed != precomposed  # sanity: genuinely different strings
    assert normalize(decomposed) == normalize(precomposed) == "ozbekiston"


# --- the reform-draft alias --------------------------------------------------


def test_the_alternative_reform_glyph_folds_the_same_way():
    """An earlier draft used o-macron for oʻ; text written that way must match."""
    assert normalize("Ōzbekiston") == normalize("Özbekiston") == normalize("Ўзбекистон")


# --- deliberate non-goals ----------------------------------------------------
#
# normalize() folds ORTHOGRAPHY, not romanization choice. Collapsing these
# would merge names that belong to different people.


def test_romanization_variants_are_not_folded():
    assert normalize("Xomidov") != normalize("Khomidov")
    assert normalize("Jasur") != normalize("Zhasur")


# --- script detection --------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Самарқанд", CYRILLIC),
        ("Тошкент 2026", CYRILLIC),
        ("Toshkent", LATIN_1995),
        ("Oʻzbekiston", LATIN_1995),
        ("Toşkent", LATIN_2026),
        ("Özbekiston", LATIN_2026),
        ("Uluğbek", LATIN_2026),
        ("2026", LATIN_1995),
        ("", LATIN_1995),
    ],
)
def test_detect_script(text, expected):
    assert detect_script(text) == expected


def test_one_cyrillic_letter_decides_the_whole_string():
    assert detect_script("Toshkent viloyati Тошкент") == CYRILLIC
