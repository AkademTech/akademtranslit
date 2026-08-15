"""Cyrillic -> Latin, in both Latin orthographies."""

from __future__ import annotations

import pytest

from akademtranslit import LATIN_1995, LATIN_2026, to_latin
from akademtranslit.tables import CYRILLIC_TO_LATIN_1995

# --- the alphabet, letter by letter ------------------------------------------

# Every letter of the Uzbek Cyrillic alphabet in a real word, so the table is
# exercised in context rather than in isolation. Columns: Cyrillic, latin_1995,
# latin_2026.
ALPHABET_CASES = [
    ("аср", "asr", "asr"),
    ("бахт", "baxt", "baxt"),
    ("вақт", "vaqt", "vaqt"),
    ("гул", "gul", "gul"),
    ("дала", "dala", "dala"),
    ("тезда", "tezda", "tezda"),
    ("ёзма", "yozma", "yozma"),
    ("жасур", "jasur", "jasur"),
    ("замин", "zamin", "zamin"),
    ("илм", "ilm", "ilm"),
    ("майдон", "maydon", "maydon"),
    ("китоб", "kitob", "kitob"),
    ("лаган", "lagan", "lagan"),
    ("макон", "makon", "makon"),
    ("нур", "nur", "nur"),
    ("олма", "olma", "olma"),
    ("пахта", "paxta", "paxta"),
    ("рақам", "raqam", "raqam"),
    ("сано", "sano", "sano"),
    ("тил", "til", "til"),
    ("уста", "usta", "usta"),
    ("фан", "fan", "fan"),
    ("хона", "xona", "xona"),
    ("чора", "chora", "çora"),
    ("шамол", "shamol", "şamol"),
    ("эшик", "eshik", "eşik"),
    ("юлдуз", "yulduz", "yulduz"),
    ("яшил", "yashil", "yaşil"),
    ("ўрик", "oʻrik", "örik"),
    ("қалам", "qalam", "qalam"),
    ("ғалаба", "gʻalaba", "ğalaba"),
    ("ҳаёт", "hayot", "hayot"),
]


@pytest.mark.parametrize("cyrillic,expected", [(c, l) for c, l, _ in ALPHABET_CASES])
def test_alphabet_to_latin_1995(cyrillic, expected):
    assert to_latin(cyrillic, variant=LATIN_1995) == expected


@pytest.mark.parametrize("cyrillic,expected", [(c, l) for c, _, l in ALPHABET_CASES])
def test_alphabet_to_latin_2026(cyrillic, expected):
    assert to_latin(cyrillic, variant=LATIN_2026) == expected


def test_every_cyrillic_letter_is_covered():
    """No letter of the Cyrillic alphabet may fall through untranslated."""
    alphabet = "абвгдеёжзийклмнопрстуфхцчшъэюяўқғҳ"
    for letter in alphabet:
        result = to_latin(letter + "a", variant=LATIN_1995)
        assert not any("Ѐ" <= ch <= "ӿ" for ch in result), (
            f"{letter!r} was not transliterated: {result!r}"
        )


def test_table_covers_the_full_alphabet():
    """The table itself, not just the words above -- catches a deleted row."""
    alphabet = "абвгдёжзийклмнопрстуфхчшъьыэюяўқғҳщ"
    missing = [ch for ch in alphabet if ch not in CYRILLIC_TO_LATIN_1995]
    assert missing == [], f"letters missing from the table: {missing}"


# --- real scholarly and geographic material ----------------------------------

REAL_CASES = [
    # Historical scholars -- these names appear in citations in every script.
    ("Алишер Навоий", "Alisher Navoiy", "Alişer Navoiy"),
    ("Мирзо Улуғбек", "Mirzo Ulugʻbek", "Mirzo Uluğbek"),
    ("Абу Райҳон Беруний", "Abu Rayhon Beruniy", "Abu Rayhon Beruniy"),
    ("Заҳириддин Муҳаммад Бобур", "Zahiriddin Muhammad Bobur", "Zahiriddin Muhammad Bobur"),
    # Places.
    ("Тошкент", "Toshkent", "Toşkent"),
    ("Самарқанд", "Samarqand", "Samarqand"),
    ("Қашқадарё", "Qashqadaryo", "Qaşqadaryo"),
    ("Сурхондарё", "Surxondaryo", "Surxondaryo"),
    ("Ўзбекистон", "Oʻzbekiston", "Özbekiston"),
    # Institutional and article-title language.
    ("Ўзбекистон Республикаси", "Oʻzbekiston Respublikasi", "Özbekiston Respublikasi"),
    (
        "Тошкент давлат университети",
        "Toshkent davlat universiteti",
        "Toşkent davlat universiteti",
    ),
    ("илмий тадқиқот", "ilmiy tadqiqot", "ilmiy tadqiqot"),
    ("Ўзбек тили ва адабиёти", "Oʻzbek tili va adabiyoti", "Özbek tili va adabiyoti"),
]


@pytest.mark.parametrize("cyrillic,expected", [(c, l) for c, l, _ in REAL_CASES])
def test_real_material_1995(cyrillic, expected):
    assert to_latin(cyrillic, variant=LATIN_1995) == expected


@pytest.mark.parametrize("cyrillic,expected", [(c, l) for c, _, l in REAL_CASES])
def test_real_material_2026(cyrillic, expected):
    assert to_latin(cyrillic, variant=LATIN_2026) == expected


# --- defaults and argument validation ----------------------------------------


def test_default_variant_is_the_reformed_alphabet():
    assert to_latin("Шошимова") == to_latin("Шошимова", variant=LATIN_2026) == "Şoşimova"


def test_unknown_variant_is_rejected():
    with pytest.raises(ValueError, match="unknown Latin variant"):
        to_latin("Тошкент", variant="latin_1940")


def test_to_latin_accepts_latin_input_as_a_migration_function():
    """1995 text handed to to_latin() is upgraded rather than mangled."""
    assert to_latin("Ulugʻbek", variant=LATIN_2026) == "Uluğbek"
    assert to_latin("Shoshimova", variant=LATIN_2026) == "Şoşimova"
