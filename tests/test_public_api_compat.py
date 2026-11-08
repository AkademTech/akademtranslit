"""The names downstream code imports, pinned.

The import statements below are copied verbatim from code that depends on this
library (each distinct statement once). Some reach into modules and private
names; that is how they are used today, so they are kept working. Removing or
renaming any of them is a breaking change and needs a major version.
"""

from __future__ import annotations

import re

import pytest

# --- verbatim -----------------------------------------------------------------

import akademtranslit
from akademtranslit import convert as _at_convert
from akademtranslit import normalize as _at_normalize
from akademtranslit.normalize import _LATIN_2026_FOLD
from akademtranslit.normalize import _MARKS as _AT_MARKS
from akademtranslit.normalize import _NON_ALNUM_RE as _AT_NON_ALNUM_RE
from akademtranslit.normalize import _WHITESPACE_RE as _AT_WHITESPACE_RE
from akademtranslit.normalize import fold_cyrillic
from akademtranslit.normalize import fold_cyrillic as _at_fold_cyrillic
from akademtranslit.normalize import fold_latin_2026 as _at_fold_latin_2026
from akademtranslit.normalize import is_cyrillic as _at_is_cyrillic
from akademtranslit.normalize import normalize as lib_normalize
from akademtranslit.rules import (
    cyrillic_word_to_latin_1995 as _at_cyrillic_word_to_latin_1995,
)
from akademtranslit.rules import CYRILLIC_VOWELS as _AT_CYRILLIC_VOWELS
from akademtranslit.rules import cyrillic_word_to_latin_1995
from akademtranslit.rules import cyrillic_word_to_latin_1995 as _at_word_1995
from akademtranslit.rules import map_words as _at_map_words
from akademtranslit.tables import APOSTROPHE_VARIANTS
from akademtranslit.tables import APOSTROPHE_VARIANTS as _AT_APOSTROPHES
from akademtranslit.tables import CYRILLIC_TO_LATIN_1995 as _AT_TABLE_1995


def test_the_import_made_inside_a_function():
    from akademtranslit.normalize import _MARKS
    assert "ʻ" in _MARKS and "ʼ" in _MARKS


# --- the imported objects still do their job ------------------------------------


def test_functions():
    assert _at_convert("Тошкент", target="latin_1995") == "Toshkent"
    assert _at_normalize("Тошкент") == lib_normalize("Toshkent") == "toshkent"
    assert fold_cyrillic("тош") == _at_fold_cyrillic("тош") == "tosh"
    assert _at_fold_latin_2026("şoş") == "shosh"
    assert _at_is_cyrillic("Тошкент") and not _at_is_cyrillic("Toshkent")
    assert cyrillic_word_to_latin_1995("тошкент") == "toshkent"
    assert _at_word_1995 is cyrillic_word_to_latin_1995
    assert _at_cyrillic_word_to_latin_1995 is cyrillic_word_to_latin_1995
    assert _at_map_words("O'zbek tili", lambda word: word) == "Oʻzbek tili"


def test_data():
    assert _LATIN_2026_FOLD["ş"] == "sh" and _LATIN_2026_FOLD["ö"] == "o"
    assert {"ʻ", "ʼ", "'"} <= _AT_MARKS
    assert isinstance(_AT_NON_ALNUM_RE, re.Pattern) and _AT_NON_ALNUM_RE.sub(" ", "a-b") == "a b"
    assert isinstance(_AT_WHITESPACE_RE, re.Pattern) and _AT_WHITESPACE_RE.sub(" ", "a \t b") == "a b"
    assert "а" in _AT_CYRILLIC_VOWELS and "б" not in _AT_CYRILLIC_VOWELS
    assert len(APOSTROPHE_VARIANTS) == 8 and _AT_APOSTROPHES is APOSTROPHE_VARIANTS
    assert _AT_TABLE_1995["ш"] == "sh" and _AT_TABLE_1995["ъ"] == "ʼ"


# --- every public name of 0.1.0 is still public --------------------------------

ALL_0_1_0 = [
    "CYRILLIC",
    "LATIN_1995",
    "LATIN_2026",
    "LATIN_2026_ALPHABET",
    "REFORM_PAIRS",
    "SCRIPTS",
    "TURNED_COMMA",
    "TUTUQ",
    "__version__",
    "convert",
    "detect_script",
    "fold_cyrillic",
    "is_cyrillic",
    "normalize",
    "to_cyrillic",
    "to_latin",
]


@pytest.mark.parametrize("name", ALL_0_1_0)
def test_0_1_0_names_are_still_exported(name):
    assert hasattr(akademtranslit, name)
    assert name in akademtranslit.__all__


def test_star_import_gives_every_exported_name():
    namespace: dict = {}
    exec("from akademtranslit import *", namespace)
    assert [name for name in akademtranslit.__all__ if name not in namespace] == []
