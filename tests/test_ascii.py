"""to_ascii: ASCII for names and logins, by a frozen project scheme."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from akademtranslit import to_ascii
from akademtranslit.tables import APOSTROPHE_VARIANTS, ASCII_CAPITALS, ASCII_SCHEME

REPO = Path(__file__).resolve().parent.parent
GOLDEN_INPUTS = REPO / "golden" / "inputs.json"

SOFT_HYPHEN = chr(0x00AD)


def golden_texts():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    return [case["text"] for case in doc["cases"]]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Шавкат", "Shavkat"),
        ("Şavkat", "Shavkat"),
        ("Oʻktam", "Oktam"),
        ("Gʻafur Gʻulom", "Gafur Gulom"),
        ("Isʼhoq", "Ishoq"),
        ("Исҳоқ", "Ishoq"),
        ("Ёқуб", "Yoqub"),
        ("Çölpon", "Cholpon"),
        ("José", "Jose"),
        ("ŞOŞIMOVA", "SHOSHIMOVA"),
        ("Ўзбекистон", "Ozbekiston"),
        ("McDonald", "McDonald"),
    ],
)
def test_to_ascii(text, expected):
    assert to_ascii(text) == expected


@pytest.mark.parametrize("mark", APOSTROPHE_VARIANTS)
def test_every_apostrophe_mark_is_removed(mark):
    assert to_ascii(f"O{mark}zbek ma{mark}no") == "Ozbek mano"


def test_2026_letters_the_conversion_leaves_are_written_by_the_table():
    """A Latin word in Cyrillic text, and a protected span, keep their letters
    through to_latin; the table turns them into ASCII."""
    assert to_ascii("Тошкент Çölpon") == "Toshkent Cholpon"
    assert to_ascii("Тошкент şahar, ğoz") == "Toshkent shahar, goz"
    assert to_ascii("https://çölpon.uz") == "https://cholpon.uz"


def test_case_spaces_digits_and_ascii_punctuation_stay():
    assert to_ascii("OʻZBEKISTON Respublikasi, 2026-yil (rasmiy)!") == "OZBEKISTON Respublikasi, 2026-yil (rasmiy)!"
    assert to_ascii("pH va SpO2") == "pH va SpO2"


def test_accents_go_and_anything_else_not_ascii_is_removed():
    assert to_ascii("Ñandú, Zoë, Ångström") == "Nandu, Zoe, Angstrom"
    assert to_ascii("«Oʻzbekiston» — 2026") == "Ozbekiston  2026"
    assert to_ascii("Tosh" + SOFT_HYPHEN + "kent") == "Toshkent"


def test_empty():
    assert to_ascii("") == ""


def test_the_result_is_ascii_on_every_golden_input():
    assert [text for text in golden_texts() if not to_ascii(text).isascii()] == []


def test_idempotent_on_the_golden_inputs():
    assert [text for text in golden_texts() if to_ascii(to_ascii(text)) != to_ascii(text)] == []


def test_the_scheme_is_pairs_of_a_letter_and_its_ascii():
    assert all(len(pair) == 2 and pair[1].isascii() and not pair[0].isascii() for pair in ASCII_SCHEME)
    assert {source for source, _ in ASCII_SCHEME} == {
        "oʻ", "Oʻ", "gʻ", "Gʻ", "ş", "ç", "ğ", "Ğ", "ö", "Ö",
    }


def test_capital_s_and_c_cedilla_have_two_forms():
    assert ASCII_CAPITALS == (("Ş", "SH", "Sh"), ("Ç", "CH", "Ch"))


# --- capital Ş and Ç: by their neighbours -----------------------------------------
#
# Capital Ş and Ç are SH and CH when the character before or after is a
# capital, Sh and Ch otherwise -- the way latin_2026 -> latin_1995 writes them.
# They reach the scheme only from a Latin word in Cyrillic text or a protected
# span; an all-caps word came out as ShAHAR and was not idempotent.


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Тошкент ŞAHAR", "Toshkent SHAHAR"),
        ("MÇJ va AQŞ", "MCHJ va AQSH"),  # to_latin writes these itself
        ("Şavkat", "Shavkat"),
        ("Тошкент Şahar", "Toshkent Shahar"),
        ("Тошкент ÇÖLPON, Çölpon", "Toshkent CHOLPON, Cholpon"),
        ("Тошкент AŞ", "Toshkent ASH"),  # the character before is a capital
        ("Тошкент Ş", "Toshkent Sh"),
        ("https://ŞAHAR.uz", "https://SHAHAR.uz"),
    ],
)
def test_capital_s_and_c_cedilla_by_their_neighbours(text, expected):
    assert to_ascii(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        # the inputs added for case units, number suffixes and abbreviations
        "10ta kitob, 2026yil, 100mg",
        "ToshDU va SamDU",
        "ТошДУ ва ЎзМУ",
        "OʻzMU talabasi",
        "ChatGPT, PhD, AkademID",
        "MÇJ va AQŞ",
        "Тошкент ŞAHAR",
        "ShAHAR",
        # were not idempotent: ShAHAR -> Shahar, OZBEKISTONga -> Ozbekistonga
        "ТОШКЕНТ ŞAHAR",
        "«ЎЗБЕКИСТОН»га",
    ],
)
def test_idempotent_on_case_units(text):
    once = to_ascii(text)
    assert to_ascii(once) == once
