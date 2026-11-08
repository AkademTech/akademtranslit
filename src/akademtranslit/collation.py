"""Alphabetical order for Uzbek text, in each of the three orthographies.

Code-point order is wrong for Uzbek in every script: it puts ``ç`` before ``d``
and ``ö`` after ``z``, splits ``sh`` into ``s`` + ``h`` and sends ``Ў Қ Ғ Ҳ`` to
the end of the Cyrillic block in the wrong order. :func:`sort_key` sorts by
the alphabets in :mod:`akademtranslit.tables` instead.
"""

from __future__ import annotations

import unicodedata

from .rules import map_words
from .tables import (
    APOSTROPHE_VARIANTS,
    CYRILLIC,
    CYRILLIC_ALPHABET,
    LATIN_1995,
    LATIN_1995_ALPHABET,
    LATIN_2026,
    LATIN_2026_ALPHABET,
    LATIN_2026_INPUT_ALIASES,
    SCRIPTS,
    TURNED_COMMA,
    TUTUQ,
)

# Weights: 0 for whitespace, 1-10 for the digits, 11 + k for the k-th unit of
# the alphabet, 1000 + code point for any other letter.
_SPACE = 0
_FIRST_DIGIT = 1
_FIRST_LETTER = 11
_OTHER_LETTER = 1000

_ALPHABETS = {
    CYRILLIC: CYRILLIC_ALPHABET,
    LATIN_1995: LATIN_1995_ALPHABET,
    LATIN_2026: LATIN_2026_ALPHABET,
}

_WEIGHTS = {
    orthography: {unit: _FIRST_LETTER + k for k, unit in enumerate(alphabet)}
    for orthography, alphabet in _ALPHABETS.items()
}

# Units longer than one character (oʻ gʻ sh ch in latin_1995), longest first.
_COMPOUND_UNITS = {
    orthography: tuple(sorted((u for u in alphabet if len(u) > 1), key=len, reverse=True))
    for orthography, alphabet in _ALPHABETS.items()
}

# Letters to Unicode (ʻ ʼ ʹ are category Lm), but never weighed as letters.
_MARKS = frozenset(APOSTROPHE_VARIANTS) | {TURNED_COMMA, TUTUQ}


def _same(word: str) -> str:
    return word


def sort_key(text: str, orthography: str) -> tuple:
    """Key that sorts Uzbek text in the alphabetical order of ``orthography``.

    ``orthography`` is one of :data:`~akademtranslit.tables.SCRIPTS` and is
    required: there is no default and no detection, because the same string
    sorts differently in different orthographies (``sh`` is one letter in
    ``latin_1995`` and two in ``latin_2026``). Anything else raises
    :class:`ValueError`.

    The key is ``(weights, text)``:

    1. ``text`` is put in NFC and stripped; the weights are computed from its
       lowercase form.
    2. For ``latin_2026``, the draft glyphs ``ō`` and ``ǒ`` read as ``ö``.
    3. Apostrophe variants inside a word are resolved as everywhere else in the
       library: after ``o`` or ``g`` a turned comma, elsewhere the tutuq
       belgisi.
    4. In ``latin_1995``, ``oʻ``, ``gʻ``, ``sh`` and ``ch`` are single letters
       (``sʼh`` is ``s``, the tutuq belgisi, ``h``). Everywhere else a letter
       is one character.
    5. Weights, in order: a run of whitespace is ``0`` (once, however long);
       the ASCII digits ``0``-``9`` are ``1``-``10``; the ``k``-th letter of
       the orthography's alphabet is ``11 + k``; any other letter is
       ``1000 + ord(letter)``. Everything else -- punctuation, symbols, the
       tutuq belgisi and the other apostrophe marks -- is not counted, so the
       whitespace on either side of it is one run.
    6. When the weights are equal, the NFC text decides, so the order is total
       and deterministic.

    >>> words = ["tabiat", "çaqmoq", "sabr", "şahar"]
    >>> sorted(words, key=lambda w: sort_key(w, "latin_2026"))
    ['sabr', 'şahar', 'çaqmoq', 'tabiat']
    >>> words = ["shamol", "zarar", "choy", "oʻrik"]
    >>> sorted(words, key=lambda w: sort_key(w, "latin_1995"))
    ['zarar', 'oʻrik', 'shamol', 'choy']
    >>> sorted(["қовун", "ўрик", "ялпиз"], key=lambda w: sort_key(w, "cyrillic"))
    ['ялпиз', 'ўрик', 'қовун']
    >>> sort_key("Isʼhoq", "latin_1995") < sort_key("Ishonch", "latin_1995")
    True
    """
    if orthography not in SCRIPTS:
        raise ValueError(f"unknown orthography: {orthography!r}; expected one of {SCRIPTS}")

    s = unicodedata.normalize("NFC", text).strip()
    work = s.lower()
    if orthography == LATIN_2026:
        for alias, letter in LATIN_2026_INPUT_ALIASES:
            work = work.replace(alias, letter)
    work = map_words(work, _same)

    table = _WEIGHTS[orthography]
    compounds = _COMPOUND_UNITS[orthography]
    weights: list[int] = []
    i = 0
    length = len(work)
    while i < length:
        ch = work[i]
        if ch.isspace():
            if not weights or weights[-1] != _SPACE:
                weights.append(_SPACE)
            i += 1
            continue
        unit = ch
        for compound in compounds:
            if work.startswith(compound, i):
                unit = compound
                break
        if unit in table:
            weights.append(table[unit])
            i += len(unit)
            continue
        if "0" <= ch <= "9":
            weights.append(_FIRST_DIGIT + ord(ch) - ord("0"))
        elif ch.isalpha() and ch not in _MARKS:
            weights.append(_OTHER_LETTER + ord(ch))
        i += 1
    return (tuple(weights), s)
