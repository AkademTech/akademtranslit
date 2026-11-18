"""normalize_apostrophes: one output form for the marks in Latin words."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from akademtranslit import normalize, normalize_apostrophes
from akademtranslit.tables import APOSTROPHE_VARIANTS

GOLDEN_INPUTS = Path(__file__).resolve().parent.parent / "golden" / "inputs.json"

# Word, its unicode form, its ascii form. "_" marks where the apostrophe goes.
WORDS = [
    ("o_zbek", "oʻzbek", "o'zbek"),
    ("g_alaba", "gʻalaba", "g'alaba"),
    ("ma_no", "maʼno", "ma'no"),
    ("jur_at", "jurʼat", "jur'at"),
    ("bog_", "bogʻ", "bog'"),            # word-final, after g
    ("O_ZBEKISTON", "OʻZBEKISTON", "O'ZBEKISTON"),
    ("G_ALLA", "GʻALLA", "G'ALLA"),
    ("MA_NO", "MAʼNO", "MA'NO"),
    ("to_g_", "toʻgʻ", "to'g'"),
]


def test_there_are_eight_accepted_forms():
    assert len(APOSTROPHE_VARIANTS) == 8


@pytest.mark.parametrize("mark", APOSTROPHE_VARIANTS, ids=[f"U+{ord(m):04X}" for m in APOSTROPHE_VARIANTS])
@pytest.mark.parametrize("template,unicode_form,ascii_form", WORDS)
def test_every_form_gives_one_result_in_each_style(template, unicode_form, ascii_form, mark):
    word = template.replace("_", mark)
    assert normalize_apostrophes(word) == unicode_form
    assert normalize_apostrophes(word, "unicode") == unicode_form
    assert normalize_apostrophes(word, style="ascii") == ascii_form


def test_the_default_style_is_unicode():
    assert normalize_apostrophes("o'zbek") == normalize_apostrophes("o'zbek", "unicode")


@pytest.mark.parametrize("text", ["‘salom’", "'salom'", '"salom"', "“salom”", "«salom»"])
def test_quotes_around_a_word_are_left_alone(text):
    assert normalize_apostrophes(text) == text
    assert normalize_apostrophes(text, "ascii") == text


def test_all_caps():
    assert normalize_apostrophes("O'ZBEKISTON") == "OʻZBEKISTON"
    assert normalize_apostrophes("O'ZBEKISTON", "ascii") == "O'ZBEKISTON"
    assert normalize_apostrophes("OʻZBEKISTON", "ascii") == "O'ZBEKISTON"


def test_only_marks_inside_latin_words_change():
    text = "«O'zbekiston» — 2'3, ma'no; 'jur'at' va bog' 10'"
    assert normalize_apostrophes(text) == "«Oʻzbekiston» — 2'3, maʼno; 'jurʼat' va bogʻ 10'"
    assert normalize_apostrophes(text, "ascii") == text


def test_a_mark_not_after_o_or_g_at_the_end_of_a_word_is_a_quote():
    assert normalize_apostrophes("ma'") == "ma'"
    assert normalize_apostrophes("'salom' dedi") == "'salom' dedi"


def test_letters_case_digits_and_punctuation_are_unchanged():
    text = "Ilmiy jurnal, 2026-yil, 12-son: Oʻzbek tili!"
    assert normalize_apostrophes(text) == text
    assert normalize_apostrophes(text, "ascii") == "Ilmiy jurnal, 2026-yil, 12-son: O'zbek tili!"


@pytest.mark.parametrize("text", ["маъно", "Ўзбекистон", "ма'но", "Аli'yev", "o'zbekча"])
def test_a_word_with_a_cyrillic_letter_is_unchanged(text):
    assert normalize_apostrophes(text) == text
    assert normalize_apostrophes(text, "ascii") == text


def test_cyrillic_and_latin_words_side_by_side():
    assert normalize_apostrophes("маъно ma'no") == "маъно maʼno"


@pytest.mark.parametrize("mark", ["‛", "′"])
def test_marks_outside_the_eight_forms_are_not_read(mark):
    word = "o" + mark + "zbek"
    assert normalize_apostrophes(word) == word
    assert normalize_apostrophes(word, "ascii") == word


@pytest.mark.parametrize("style", ["", "Unicode", "ASCII", "html", None])
def test_an_unknown_style_is_rejected(style):
    with pytest.raises(ValueError):
        normalize_apostrophes("o'zbek", style)


def test_normalize_is_not_changed_by_it():
    assert normalize("o'zbek") == normalize("oʻzbek") == "ozbek"


# --- properties over every golden input ---------------------------------------


def _golden_texts():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    return [case["text"] for case in doc["cases"]]


@pytest.mark.parametrize("style", ["unicode", "ascii"])
def test_idempotent(style):
    for text in _golden_texts():
        once = normalize_apostrophes(text, style)
        assert normalize_apostrophes(once, style) == once, text


def test_ascii_unicode_ascii_round_trip():
    for text in _golden_texts():
        as_ascii = normalize_apostrophes(text, "ascii")
        back = normalize_apostrophes(normalize_apostrophes(as_ascii, "unicode"), "ascii")
        assert back == as_ascii, text


def test_unicode_ascii_unicode_round_trip():
    for text in _golden_texts():
        as_unicode = normalize_apostrophes(text, "unicode")
        back = normalize_apostrophes(normalize_apostrophes(as_unicode, "ascii"), "unicode")
        assert back == as_unicode, text


@pytest.mark.parametrize("style", ["unicode", "ascii"])
def test_normalize_gives_the_same_key_either_way(style):
    for text in _golden_texts():
        assert normalize(normalize_apostrophes(text, style)) == normalize(text), text


# --- strip_invisible and strip_stress ---------------------------------------------
#
# Invisible characters and the stress mark, built from their code points so the
# source shows them.

SOFT_HYPHEN = chr(0x00AD)
ZERO_WIDTH_SPACE = chr(0x200B)
ZERO_WIDTH_JOINER = chr(0x200D)
BYTE_ORDER_MARK = chr(0xFEFF)
COMBINING_ACUTE = chr(0x0301)

# Default_Ignorable_Code_Point in Unicode 15.1, written out once more here.
DEFAULT_IGNORABLE_15_1 = [
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160),
    (0x17B4, 0x17B5), (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E),
    (0x2060, 0x206F), (0x3164, 0x3164), (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3), (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
]


def _ignorable() -> list:
    return [chr(c) for first, last in DEFAULT_IGNORABLE_15_1 for c in range(first, last + 1)]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("shahar" + ZERO_WIDTH_SPACE + " choy", "shahar choy"),
        ("Tosh" + SOFT_HYPHEN + "kent", "Toshkent"),
        (BYTE_ORDER_MARK + "Oʻzbekiston", "Oʻzbekiston"),
        ("O" + ZERO_WIDTH_JOINER + "'zbekiston", "Oʻzbekiston"),
        ("Тош" + SOFT_HYPHEN + "кент" + ZERO_WIDTH_SPACE, "Тошкент"),
    ],
)
def test_strip_invisible(text, expected):
    assert normalize_apostrophes(text, strip_invisible=True) == expected


def test_strip_invisible_removes_the_4174_default_ignorable_code_points():
    ignorable = _ignorable()
    assert len(ignorable) == 4174
    assert normalize_apostrophes("a" + "".join(ignorable) + "b", strip_invisible=True) == "ab"


def test_strip_invisible_keeps_their_neighbours():
    neighbours = [0x00AC, 0x00AE, 0x034E, 0x0350, 0x200A, 0x2010, 0x2029, 0x205F, 0xFDFF, 0xFE10,
                  0xFFF9, 0x1D172, 0x1D17B, 0xDFFFF, 0xE1000]
    text = "".join(chr(c) for c in neighbours)
    assert normalize_apostrophes(text, strip_invisible=True) == text


def test_strip_stress():
    assert normalize_apostrophes("То" + COMBINING_ACUTE + "шкент", strip_stress=True) == "Тошкент"
    assert normalize_apostrophes("ша" + COMBINING_ACUTE + "ҳар", strip_stress=True) == "шаҳар"
    assert normalize_apostrophes("ka" + COMBINING_ACUTE + "lit", strip_stress=True) == "kalit"


def test_strip_stress_takes_only_a_mark_after_a_letter():
    for text in (COMBINING_ACUTE + "a", "5" + COMBINING_ACUTE, " " + COMBINING_ACUTE):
        assert normalize_apostrophes(text, strip_stress=True) == text
    assert normalize_apostrophes("ó", strip_stress=True) == "ó"  # precomposed U+00F3


def test_the_two_are_separate():
    stressed = "То" + COMBINING_ACUTE + "ш" + SOFT_HYPHEN + "кент"
    assert normalize_apostrophes(stressed, strip_stress=True) == "Тош" + SOFT_HYPHEN + "кент"
    assert normalize_apostrophes(stressed, strip_invisible=True) == "То" + COMBINING_ACUTE + "шкент"


def test_both_together():
    text = BYTE_ORDER_MARK + "То" + ZERO_WIDTH_SPACE + COMBINING_ACUTE + "шкент, o" + SOFT_HYPHEN + "'zbek"
    assert normalize_apostrophes(text, strip_invisible=True, strip_stress=True) == "Тошкент, oʻzbek"
    assert normalize_apostrophes(text, "ascii", strip_invisible=True, strip_stress=True) == "Тошкент, o'zbek"


def test_off_by_default():
    text = "То" + COMBINING_ACUTE + "ш" + SOFT_HYPHEN + "кент" + ZERO_WIDTH_SPACE
    assert normalize_apostrophes(text) == text


def test_the_new_arguments_are_keywords_only():
    with pytest.raises(TypeError):
        normalize_apostrophes("shahar", "unicode", True)


@pytest.mark.parametrize("style", ["unicode", "ascii"])
def test_idempotent_with_both(style):
    texts = _golden_texts() + ["То" + COMBINING_ACUTE + SOFT_HYPHEN + "шкент"]
    once = [normalize_apostrophes(t, style, strip_invisible=True, strip_stress=True) for t in texts]
    twice = [normalize_apostrophes(t, style, strip_invisible=True, strip_stress=True) for t in once]
    assert once == twice
