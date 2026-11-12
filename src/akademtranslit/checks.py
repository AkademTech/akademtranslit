"""Check a text against the orthography it is meant to be in.

:func:`validate` lists what in a text does not belong to one orthography:
characters that hide or that NFC writes differently, and words that show
another orthography, a look-alike letter or another form of a mark. Each
finding comes with the form it suggests. :func:`migration_report` is for a
``latin_1995`` text on its way to ``latin_2026``: what conversion does to it,
and the words to look at first.

>>> from akademtranslit import validate
>>> validate("Oʻzbekiston Respublikasi", "latin_2026")
[(0, 11, 'latin-1995-word', 'Özbekiston')]

Neither function changes the text. Protected spans
(:mod:`akademtranslit.protect`) are not checked.
"""

from __future__ import annotations

import re
import unicodedata

from .apostrophes import _INVISIBLE_RE
from .detection import _is_latin_letter
from .protect import _settings, _spans
from .rules import (
    _WORD_RE,
    CYRILLIC_WORD,
    LATIN_1995_WORD,
    LATIN_2026_WORD,
    O_FORM_WORD,
    canonicalize_marks,
    word_class,
)
from .scripts import _fold_word
from .tables import (
    APOSTROPHE_VARIANTS,
    CYRILLIC,
    LATIN_1995,
    LATIN_2026,
    RULES_VERSION,
    SCRIPTS,
    TURNED_COMMA,
    TUTUQ,
)
from .tags import _orthography

# The codes of validate, in the order of the documentation.
INVISIBLE = "invisible"
DECOMPOSED = "decomposed"
MIXED_SCRIPT = "mixed-script"
CYRILLIC_WORD_FOUND = "cyrillic-word"
LATIN_1995_WORD_FOUND = "latin-1995-word"
LATIN_2026_WORD_FOUND = "latin-2026-word"
LOOK_ALIKE = "look-alike"
LETTER_FORM = "letter-form"
DIGRAPH = "digraph"
WRONG_MARK = "wrong-mark"
MARK_FORM = "mark-form"

CODES = (
    INVISIBLE,
    DECOMPOSED,
    MIXED_SCRIPT,
    CYRILLIC_WORD_FOUND,
    LATIN_1995_WORD_FOUND,
    LATIN_2026_WORD_FOUND,
    LOOK_ALIKE,
    LETTER_FORM,
    DIGRAPH,
    WRONG_MARK,
    MARK_FORM,
)

# The two codes migration_report adds.
ROUND_TRIP = "round-trip"
SEPARATOR = "separator"

# A run of the characters strip_invisible removes.
_INVISIBLE_RUN_RE = re.compile(_INVISIBLE_RE.pattern + "+")

# Letters that look like ö or ğ, by code point, and the letter each stands
# for: o with breve, acute and tilde; g with macron and acute.
_LOOK_ALIKES = {
    chr(0x014F): "o",  # LATIN SMALL LETTER O WITH BREVE
    chr(0x00F3): "o",  # LATIN SMALL LETTER O WITH ACUTE
    chr(0x00F5): "o",  # LATIN SMALL LETTER O WITH TILDE
    chr(0x014E): "O",  # LATIN CAPITAL LETTER O WITH BREVE
    chr(0x00D3): "O",  # LATIN CAPITAL LETTER O WITH ACUTE
    chr(0x00D5): "O",  # LATIN CAPITAL LETTER O WITH TILDE
    chr(0x1E21): "g",  # LATIN SMALL LETTER G WITH MACRON
    chr(0x01F5): "g",  # LATIN SMALL LETTER G WITH ACUTE
    chr(0x1E20): "G",  # LATIN CAPITAL LETTER G WITH MACRON
    chr(0x01F4): "G",  # LATIN CAPITAL LETTER G WITH ACUTE
}
_IN_2026 = {"o": "ö", "O": "Ö", "g": "ğ", "G": "Ğ"}
_LOOK_ALIKE_FIXES = {
    LATIN_2026: str.maketrans({ch: _IN_2026[base] for ch, base in _LOOK_ALIKES.items()}),
    LATIN_1995: str.maketrans({ch: base + TURNED_COMMA for ch, base in _LOOK_ALIKES.items()}),
}

# The other input forms of ö and ş (LATIN_2026_INPUT_ALIASES): o with macron
# and with caron, s with comma below, in both cases.
_LETTER_FORMS = frozenset(chr(c) for c in (0x014D, 0x01D2, 0x0219, 0x014C, 0x01D1, 0x0218))

# The letters of latin_2026 that latin_1995 writes with two characters.
_NEW_LETTERS = frozenset("şçğöŞÇĞÖ")

_MARKS = frozenset(APOSTROPHE_VARIANTS)
_CANONICAL_MARKS = frozenset((TURNED_COMMA, TUTUQ))

# s, the tutuq belgisi and h: s and h that latin_1995 keeps apart from sh.
_S_TUTUQ_H = "s" + TUTUQ + "h"


def _convert(text: str, source: str, target: str) -> str:
    # The package imports this module, so convert is looked up when called.
    from . import convert

    return convert(text, source, target, protect=False)


def validate(text: str, orthography: str, *, protect=True) -> list:
    """What in ``text`` does not belong to ``orthography``.

    ``orthography`` is one of :data:`~akademtranslit.tables.SCRIPTS` or a
    language tag for one of them; ``"auto"`` and anything else raise
    :class:`ValueError`. ``protect`` is as for
    :func:`~akademtranslit.convert`: protected spans are not checked.

    Returns a list of ``(start, end, code, suggestion)``, in order of
    ``(start, end, code)``: ``text[start:end]`` is what was found, ``code``
    says what it is, and ``suggestion`` is how it would be written in
    ``orthography``, or ``None``. Empty text gives ``[]``.

    In any orthography:

    * ``"invisible"``: a run of the characters that
      :func:`~akademtranslit.normalize_apostrophes` removes with
      ``strip_invisible=True``; the suggestion is ``""``.
    * ``"decomposed"``: a character and the combining marks after it, which
      NFC writes as one character (``O`` and U+0308 COMBINING DIAERESIS are
      ``Ö``); the suggestion is the NFC form.

    Each word gets at most one more finding, the first that applies. In
    ``cyrillic`` text:

    * ``"mixed-script"``: Cyrillic and Latin letters in one word; the
      suggestion is :func:`~akademtranslit.fold_homoglyphs` on the word, or
      ``None`` if that does not change it;
    * ``"latin-1995-word"``: a word with ``oʻ`` or ``gʻ``, and
      ``"latin-2026-word"``: a word with ``ş ç ğ ö`` or another form of
      them; the suggestion is the word in Cyrillic.

    Other Latin words (``Google``) are not findings. In ``latin_1995`` and
    ``latin_2026`` text, after ``"mixed-script"``:

    * ``"cyrillic-word"``: a Cyrillic word, converted;
    * ``"latin-1995-word"`` (2026 text): ``oʻ``, ``gʻ`` or ``sʼh``;
    * ``"latin-2026-word"`` (1995 text): ``ş ç ğ ö`` themselves;
    * ``"look-alike"``: o with breve, acute or tilde, g with macron or acute,
      in place of ``ö`` and ``ğ`` (``oʻ`` and ``gʻ``);
    * ``"letter-form"``: o with macron or caron, or s with comma below, the
      other input forms of ``ö`` and ``ş``;
    * ``"digraph"`` (2026 text): ``sh`` or ``ch``;
    * ``"wrong-mark"``: ``ʻ`` where ``ʼ`` belongs, or the other way round;
    * ``"mark-form"``: another character for one of the two marks
      (``o'zbek``).

    Their suggestion is the word in ``orthography``. Two of them call for a
    reader, not a fix: a ``"digraph"`` may be left from 1995, a real s and h
    (``Ishoq``, ``ashob``) or a foreign name (``Chrome``); and a
    ``"look-alike"`` letter may be a real one, in a foreign word.

    >>> validate("Toshkent shahri", "latin_2026")
    [(0, 8, 'digraph', 'Toşkent'), (9, 15, 'digraph', 'şahri')]
    >>> validate("Тошкент oʻrdak", "cyrillic")
    [(8, 14, 'latin-1995-word', 'ўрдак')]
    """
    if orthography not in SCRIPTS:
        orthography = _orthography(
            orthography, f"unknown orthography: {orthography!r}; expected one of {SCRIPTS}", stacklevel=2
        )
    settings = _settings(protect)
    if not text:
        return []
    found = []
    for a, b, kind in _spans(text, settings):
        if kind is not None:
            continue
        piece = text[a:b]
        for match in _INVISIBLE_RUN_RE.finditer(piece):
            found.append((a + match.start(), a + match.end(), INVISIBLE, ""))
        found.extend((a + i, a + j, DECOMPOSED, composed) for i, j, composed in _decomposed(piece))
        for match in _WORD_RE.finditer(piece):
            finding = _check_word(match.group(), orthography)
            if finding is not None:
                found.append((a + match.start(), a + match.end()) + finding)
    found.sort(key=lambda finding: finding[:3])
    return found


def _decomposed(piece: str):
    """``(start, end, NFC form)`` of each character with combining marks
    after it that NFC writes differently."""
    i = 0
    while i < len(piece):
        j = i + 1
        while j < len(piece) and unicodedata.category(piece[j]).startswith("M"):
            j += 1
        if j > i + 1:
            composed = unicodedata.normalize("NFC", piece[i:j])
            if composed != piece[i:j]:
                yield i, j, composed
        i = j


def _only_marks(word: str) -> bool:
    return all(ch in _MARKS for ch in word)


def _check_word(word: str, orthography: str):
    """``(code, suggestion)`` for one word, or ``None``."""
    if _only_marks(word):
        return None
    kind = word_class(word)
    if kind == CYRILLIC_WORD and any(_is_latin_letter(ch) for ch in word):
        folded = _fold_word(word)
        return MIXED_SCRIPT, (folded if folded != word else None)
    if orthography == CYRILLIC:
        if kind not in (LATIN_1995_WORD, LATIN_2026_WORD, O_FORM_WORD):
            return None
        code = LATIN_1995_WORD_FOUND if kind == LATIN_1995_WORD else LATIN_2026_WORD_FOUND
        return code, _convert(_convert(word, LATIN_1995, LATIN_2026), LATIN_2026, CYRILLIC)
    if kind == CYRILLIC_WORD:
        return CYRILLIC_WORD_FOUND, _convert(word, CYRILLIC, orthography)

    fixed = word.translate(_LOOK_ALIKE_FIXES[orthography])
    if orthography == LATIN_2026:
        suggestion = _convert(fixed, LATIN_1995, LATIN_2026)
    elif word_class(fixed) in (LATIN_2026_WORD, O_FORM_WORD):
        # Through latin_2026 and back, so that an sh beside ş or ö stays sh.
        suggestion = _convert(_convert(fixed, LATIN_1995, LATIN_2026), LATIN_2026, LATIN_1995)
    else:
        suggestion = _convert(fixed, LATIN_1995, LATIN_1995)
    low = canonicalize_marks(word.lower())

    if orthography == LATIN_2026 and (kind == LATIN_1995_WORD or _S_TUTUQ_H in low):
        return LATIN_1995_WORD_FOUND, suggestion
    if orthography == LATIN_1995 and any(ch in _NEW_LETTERS for ch in word):
        return LATIN_2026_WORD_FOUND, suggestion
    if fixed != word:
        return LOOK_ALIKE, suggestion
    if any(ch in _LETTER_FORMS for ch in word):
        return LETTER_FORM, suggestion
    if orthography == LATIN_2026 and ("sh" in low or "ch" in low):
        return DIGRAPH, suggestion
    if suggestion != word:
        changed = {ch for ch, new in zip(word, suggestion) if ch != new}
        return (WRONG_MARK if changed & _CANONICAL_MARKS else MARK_FORM), suggestion
    return None
