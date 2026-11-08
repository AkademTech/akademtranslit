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
    # Inputs with U+00B4 (acute accent) are left out. normalize() applies NFKC
    # first, which turns U+00B4 into a space and a combining accent, so
    # normalize("o´zbek") is "o zbek" while normalize("oʻzbek") is "ozbek". That
    # is how normalize() already behaves; this function does not change it.
    for text in _golden_texts():
        if "´" in text:
            continue
        assert normalize(normalize_apostrophes(text, style)) == normalize(text), text
