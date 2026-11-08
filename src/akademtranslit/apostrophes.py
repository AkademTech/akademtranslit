"""One output form for the apostrophe marks in Latin Uzbek text.

Input arrives with any of eight characters for ``ʻ`` and ``ʼ`` (see
:data:`~akademtranslit.tables.APOSTROPHE_VARIANTS`). Conversion already emits
the canonical two; :func:`normalize_apostrophes` does the same to Latin text
without converting it, in either of the two forms in use for display.
"""

from __future__ import annotations

from .rules import _WORD_RE
from .tables import APOSTROPHE_VARIANTS, TURNED_COMMA, TUTUQ

STYLES = ("unicode", "ascii")

_ASCII_APOSTROPHE = "'"
_MARKS = frozenset(APOSTROPHE_VARIANTS)
_TURNED_COMMA_AFTER = frozenset("oOgG")

_CYRILLIC_LO = 0x0400
_CYRILLIC_HI = 0x052F


def _is_letter(ch: str) -> bool:
    # ʻ ʼ ʹ are letters to Unicode (category Lm); here they are marks.
    return ch.isalpha() and ch not in _MARKS


def _has_cyrillic(word: str) -> bool:
    return any(_CYRILLIC_LO <= ord(ch) <= _CYRILLIC_HI for ch in word)


def normalize_apostrophes(text: str, style: str = "unicode") -> str:
    """Rewrite the apostrophe marks in Latin words to one form.

    ``style="unicode"`` writes U+02BB (``ʻ``, turned comma) after ``o`` or
    ``g`` in either case -- the letters ``oʻ`` and ``gʻ`` -- and U+02BC (``ʼ``,
    the tutuq belgisi) everywhere else. ``style="ascii"`` writes U+0027 (``'``)
    for both. Any other style raises :class:`ValueError`.

    Only marks inside a Latin word change: a mark between two letters, and a
    mark at the end of a word after ``o`` or ``g`` (``bogʻ``). Any of the eight
    :data:`~akademtranslit.tables.APOSTROPHE_VARIANTS` is read as a mark.
    Everything else is left as it is: letters and their case, quotes around a
    word (``'salom'``), digits, punctuation, and every word that contains a
    Cyrillic letter.

    >>> normalize_apostrophes("O'zbekiston, ma’no, bog`")
    'Oʻzbekiston, maʼno, bogʻ'
    >>> normalize_apostrophes("Oʻzbekiston, maʼno", style="ascii")
    "O'zbekiston, ma'no"
    >>> normalize_apostrophes("'salom'")
    "'salom'"

    Idempotent in both styles. Unlike :func:`~akademtranslit.convert`, it does
    not touch anything but the marks, so it is safe on text whose orthography
    is unknown.
    """
    if style not in STYLES:
        raise ValueError(f"unknown style: {style!r}; expected one of {STYLES}")

    def _one(match) -> str:
        word = match.group(0)
        if _has_cyrillic(word):
            return word
        out = list(word)
        last = len(word) - 1
        for i, ch in enumerate(word):
            if ch not in _MARKS:
                continue
            prev = word[i - 1] if i else ""
            nxt = word[i + 1] if i < last else ""
            inside = _is_letter(prev) and _is_letter(nxt)
            final = i == last and prev in _TURNED_COMMA_AFTER
            if not (inside or final):
                continue
            if style == "ascii":
                out[i] = _ASCII_APOSTROPHE
            else:
                out[i] = TURNED_COMMA if prev in _TURNED_COMMA_AFTER else TUTUQ
        return "".join(out)

    return _WORD_RE.sub(_one, text)
