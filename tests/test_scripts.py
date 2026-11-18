"""script_spans, homoglyph_spans and fold_homoglyphs: the script of each word,
and letters typed from the wrong alphabet."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pytest

from akademtranslit import fold_homoglyphs, homoglyph_spans, script_spans
from akademtranslit.tables import CYRILLIC_FIRST, CYRILLIC_LAST, HOMOGLYPHS

GOLDEN_INPUTS = Path(__file__).resolve().parent.parent / "golden" / "inputs.json"

# Letters that look like a letter of the other alphabet, by code point.
LATIN_O = chr(0x006F)                    # LATIN SMALL LETTER O
CYRILLIC_IE = chr(0x0435)                # CYRILLIC SMALL LETTER IE
S_COMMA = chr(0x0219)                    # LATIN SMALL LETTER S WITH COMMA BELOW
CAPITAL_S_COMMA = chr(0x0218)            # LATIN CAPITAL LETTER S WITH COMMA BELOW
CYRILLIC_CAPITAL_O_DIAERESIS = chr(0x04E6)  # CYRILLIC CAPITAL LETTER O WITH DIAERESIS


def _golden_texts():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    return [case["text"] for case in doc["cases"]]


# --- the table ----------------------------------------------------------------------

# The pairs, (Latin, Cyrillic code point), as chosen from the Unicode
# confusables (UTS #39).
EXPECTED_PAIRS = [
    ("a", 0x0430), ("c", 0x0441), ("e", 0x0435), ("o", 0x043E), ("p", 0x0440),
    ("x", 0x0445), ("y", 0x0443), ("i", 0x0456), ("j", 0x0458), ("s", 0x0455),
    ("h", 0x04BB), ("q", 0x051B), ("w", 0x051D), ("ö", 0x04E7),
    ("A", 0x0410), ("B", 0x0412), ("C", 0x0421), ("E", 0x0415), ("H", 0x041D),
    ("I", 0x0406), ("J", 0x0408), ("K", 0x041A), ("M", 0x041C), ("O", 0x041E),
    ("P", 0x0420), ("S", 0x0405), ("T", 0x0422), ("X", 0x0425), ("Y", 0x0423),
    ("Ö", 0x04E6),
]


def test_the_homoglyph_table():
    assert isinstance(HOMOGLYPHS, tuple)
    assert [(latin, ord(cyrillic)) for latin, cyrillic in HOMOGLYPHS] == EXPECTED_PAIRS


def test_each_letter_of_the_table_is_in_its_alphabet_and_appears_once():
    latin = [pair[0] for pair in HOMOGLYPHS]
    cyrillic = [pair[1] for pair in HOMOGLYPHS]
    assert len(set(latin)) == len(latin) and len(set(cyrillic)) == len(cyrillic)
    for letter in latin:
        assert unicodedata.name(letter).startswith("LATIN "), letter
    for letter in cyrillic:
        assert CYRILLIC_FIRST <= ord(letter) <= CYRILLIC_LAST and letter.isalpha(), hex(ord(letter))


# --- the cases --------------------------------------------------------------------

CASES = [
    # (text, script_spans, fold_homoglyphs)
    ("Т" + LATIN_O + "шкент", [("Т" + LATIN_O + "шкент", "mixed")], "Тошкент"),
    ("Toshk" + CYRILLIC_IE + "nt", [("Toshk" + CYRILLIC_IE + "nt", "mixed")], "Toshkent"),
    ("To" + S_COMMA + "kent", [("To" + S_COMMA + "kent", "latin_2026")], "Toşkent"),
    (
        CYRILLIC_CAPITAL_O_DIAERESIS + "zbekiston",
        [(CYRILLIC_CAPITAL_O_DIAERESIS + "zbekiston", "mixed")],
        "Özbekiston",
    ),
    (
        "Тошкент va Toshkent",
        [("Тошкент", "cyrillic"), (" ", None), ("va", "latin"), (" ", None), ("Toshkent", "latin")],
        "Тошкент va Toshkent",
    ),
    ("Москва", [("Москва", "cyrillic")], "Москва"),
    ("Toshkent", [("Toshkent", "latin")], "Toshkent"),
]


@pytest.mark.parametrize("text,spans,folded", CASES)
def test_script_spans(text, spans, folded):
    assert script_spans(text) == spans


@pytest.mark.parametrize("text,spans,folded", CASES)
def test_fold_homoglyphs(text, spans, folded):
    assert fold_homoglyphs(text) == folded


@pytest.mark.parametrize("text,spans,folded", CASES)
def test_homoglyph_spans(text, spans, folded):
    expected = [] if folded == text else [(0, len(text), folded)]
    assert homoglyph_spans(text) == expected


# --- script_spans ---------------------------------------------------------------


@pytest.mark.parametrize(
    "word,kind",
    [
        ("Özbekiston", "latin_2026"),
        ("Şahar", "latin_2026"),
        ("T" + chr(0x014D) + "ky" + chr(0x014D), "latin_2026"),  # o with macron
        ("Oʻzbekiston", "latin_1995"),
        ("Gʻafur", "latin_1995"),
        ("o'zbek", "latin_1995"),   # any apostrophe after o or g
        ("Shahar", "latin"),        # sh: either Latin orthography
        ("kitob", "latin"),
        ("Самарқанд", "cyrillic"),
    ],
)
def test_the_kind_of_each_word(word, kind):
    assert script_spans(word) == [(word, kind)]


def test_the_text_between_words_is_none():
    assert script_spans("") == []
    assert script_spans("  2026-yil, ") == [("  2026-", None), ("yil", "latin"), (", ", None)]
    assert script_spans("«Тошкент»") == [("«", None), ("Тошкент", "cyrillic"), ("»", None)]


def test_script_spans_does_not_protect_anything():
    assert script_spans("https://shahar.uz") == [
        ("https", "latin"), ("://", None), ("shahar", "latin"), (".", None), ("uz", "latin")
    ]


def test_script_spans_on_the_golden_inputs_join_to_the_input():
    for text in _golden_texts():
        pieces = script_spans(text)
        assert "".join(piece for piece, _ in pieces) == text
        kinds = [kind for _, kind in pieces]
        assert all(a is not None or b is not None for a, b in zip(kinds, kinds[1:])), text


# --- fold_homoglyphs --------------------------------------------------------------


def test_a_word_with_a_letter_that_has_no_twin_is_left_as_it_is():
    # k has no Cyrillic twin (only capital K does): a mixed word, not a slip.
    word = "Тош" + "k" + "ент"
    assert fold_homoglyphs(word) == word and homoglyph_spans(word) == []
    assert script_spans(word) == [(word, "mixed")]
    # Not even the o, which has one, is replaced.
    word = "Т" + "k" + LATIN_O + "шкент"
    assert fold_homoglyphs(word) == word and homoglyph_spans(word) == []


def test_a_word_with_as_many_letters_of_each_is_left_as_it_is():
    word = "Т" + LATIN_O
    assert fold_homoglyphs(word) == word


def test_s_with_comma_below_becomes_s_with_cedilla_in_a_latin_word_only():
    assert fold_homoglyphs("TO" + CAPITAL_S_COMMA + "KENT") == "TOŞKENT"
    assert fold_homoglyphs("To" + S_COMMA + "kent va " + S_COMMA + "ahar") == "Toşkent va şahar"
    # In a Cyrillic word it is a Latin letter with no twin: the word stays.
    word = "То" + S_COMMA + "кент"
    assert fold_homoglyphs(word) == word


def test_only_the_changed_words_are_reported():
    text = "Toshk" + CYRILLIC_IE + "nt va Т" + LATIN_O + "шкент"
    assert homoglyph_spans(text) == [(0, 8, "Toshkent"), (12, 19, "Тошкент")]
    assert fold_homoglyphs(text) == "Toshkent va Тошкент"


def _mixed_words():
    """Each pair of the table inside a word of the other alphabet."""
    words = []
    for latin, cyrillic in HOMOGLYPHS:
        words.append("ab" + cyrillic + "dir")
        words.append("Тош" + latin + "кент")
    return words


@pytest.mark.parametrize("word", _mixed_words())
def test_each_pair_folds_into_the_majority_alphabet(word):
    folded = fold_homoglyphs(word)
    assert folded != word
    assert script_spans(folded)[0][1] != "mixed"


def test_fold_homoglyphs_is_idempotent():
    texts = _golden_texts() + [text for text, _, _ in CASES] + _mixed_words()
    assert [text for text in texts if fold_homoglyphs(fold_homoglyphs(text)) != fold_homoglyphs(text)] == []


def test_on_the_golden_inputs_only_mixed_words_and_s_with_comma_change():
    for text in _golden_texts():
        kinds = {piece: kind for piece, kind in script_spans(text)}
        for start, stop, _ in homoglyph_spans(text):
            word = text[start:stop]
            assert kinds[word] == "mixed" or S_COMMA in word or CAPITAL_S_COMMA in word, (text, word)
