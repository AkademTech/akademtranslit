"""Changes in 0.3.0.

Each section pins one change: what it fixes, what it must leave alone, and,
where a function had two answers for one question, that it now has one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from akademtranslit import (
    CYRILLIC,
    LATIN_1995,
    LATIN_2026,
    _REFORM_LETTERS,
    convert,
    detect_script,
    to_latin,
)

GOLDEN_INPUTS = Path(__file__).resolve().parent.parent / "golden" / "inputs.json"

# The draft glyphs for oʻ, written as escapes because they look alike:
O_MACRON = "\u014d"            # ō LATIN SMALL LETTER O WITH MACRON
O_CARON = "\u01d2"             # ǒ LATIN SMALL LETTER O WITH CARON
CAPITAL_O_MACRON = "\u014c"    # Ō LATIN CAPITAL LETTER O WITH MACRON
CAPITAL_O_CARON = "\u01d1"     # Ǒ LATIN CAPITAL LETTER O WITH CARON

DRAFT_GLYPHS = [O_MACRON, O_CARON, CAPITAL_O_MACRON, CAPITAL_O_CARON]


# --- detect_script: every draft glyph is a 2026 letter, in either case --------
#
# The set of 2026-only letters held U+01D3 (Ǔ, U with caron) where U+01D1
# (Ǒ, O with caron) belonged, so text with a capital Ǒ was read as 1995.


@pytest.mark.parametrize("glyph", DRAFT_GLYPHS)
def test_a_draft_glyph_alone_is_latin_2026(glyph):
    assert detect_script(glyph) == LATIN_2026


@pytest.mark.parametrize("glyph", DRAFT_GLYPHS)
def test_a_draft_glyph_in_a_word_is_latin_2026(glyph):
    assert detect_script(glyph + "zbekiston") == LATIN_2026
    assert detect_script("t" + glyph + "rt") == LATIN_2026


@pytest.mark.parametrize("letter", sorted(_REFORM_LETTERS))
def test_the_2026_letters_are_there_in_both_cases(letter):
    assert letter.lower() in _REFORM_LETTERS
    assert letter.upper() in _REFORM_LETTERS


# --- ō and ǒ come out as ö in every 2026 output -------------------------------
#
# The draft glyphs were read as ö only on the way out of latin_2026. Converting
# latin_2026 text to latin_2026 (which is what to_latin does with it) had no
# step to run, so to_latin("ōrdak") gave "ōrdak". They are now read as ö
# whenever the source or the target is latin_2026.

# The golden inputs with a draft glyph: id -> (input, 2026 output).
DRAFT_GLYPH_INPUTS = {
    "c0328": (CAPITAL_O_MACRON + "zbekiston", "Özbekiston"),
    "c1077": (O_MACRON, "ö"),
    "c1078": (O_CARON, "ö"),
    "c1079": (CAPITAL_O_MACRON, "Ö"),
    "c1080": (CAPITAL_O_CARON, "Ö"),
    "c1081": (O_MACRON + "rdak", "ördak"),
    "c1082": (O_CARON + "rdak", "ördak"),
    "c1083": (CAPITAL_O_MACRON + "RDAK", "ÖRDAK"),
    "c1084": (CAPITAL_O_CARON + "zbekiston", "Özbekiston"),
}
DRAFT_GLYPH_CASES = sorted(DRAFT_GLYPH_INPUTS.values())


def test_the_draft_glyph_cases_are_the_golden_inputs():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    texts = {case["id"]: case["text"] for case in doc["cases"]}
    assert {i: texts[i] for i in DRAFT_GLYPH_INPUTS} == {
        i: text for i, (text, _) in DRAFT_GLYPH_INPUTS.items()
    }


@pytest.mark.parametrize("text,expected", DRAFT_GLYPH_CASES)
def test_to_latin_writes_the_draft_glyphs_as_o_umlaut(text, expected):
    assert to_latin(text) == expected


@pytest.mark.parametrize("text,expected", DRAFT_GLYPH_CASES)
def test_latin_2026_to_latin_2026_writes_the_draft_glyphs_as_o_umlaut(text, expected):
    assert convert(text, source=LATIN_2026, target=LATIN_2026) == expected


def test_latin_1995_to_latin_2026_writes_the_draft_glyphs_as_o_umlaut():
    """The source is given as latin_1995, but the text has a draft glyph."""
    assert convert(O_MACRON + "zbek", source=LATIN_1995, target=LATIN_2026) == "özbek"
    assert convert(O_CARON + "zbek", source=LATIN_1995, target=LATIN_2026) == "özbek"


@pytest.mark.parametrize("text,expected", DRAFT_GLYPH_CASES)
def test_the_2026_output_is_idempotent(text, expected):
    once = convert(text)
    assert convert(once) == once


def test_a_given_latin_1995_source_is_kept_when_the_target_is_not_2026():
    """Neither side is latin_2026, so the glyph is not read as ö.

    The caller said the text is latin_1995, and in latin_1995 ō is not a letter;
    the source they give wins over what the text looks like.
    """
    assert convert(O_MACRON + "zbek", source=LATIN_1995, target=LATIN_1995) == O_MACRON + "zbek"
    assert convert(O_MACRON + "zbek", source=LATIN_1995, target=CYRILLIC) == O_MACRON + "збек"
