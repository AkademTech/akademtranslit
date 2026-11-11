"""Changes in 0.3.0.

Each section pins one change: what it fixes, what it must leave alone, and,
where a function had two answers for one question, that it now has one.
"""

from __future__ import annotations

import pytest

from akademtranslit import LATIN_2026, _REFORM_LETTERS, detect_script

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
