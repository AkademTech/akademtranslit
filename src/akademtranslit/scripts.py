"""The script of each word, and letters typed from the wrong alphabet.

:func:`script_spans` splits a text into its words and the text between them
and names the orthography each word shows. A word with letters from both
alphabets is ``"mixed"``: usually a slip, such as a Cyrillic o (U+043E) typed
in a Latin word, which looks right and matches nothing. :func:`fold_homoglyphs`
repairs such words with :data:`~akademtranslit.tables.HOMOGLYPHS`, and
:func:`homoglyph_spans` says which words it changes.

>>> from akademtranslit import fold_homoglyphs, script_spans
>>> text = "Toshk" + chr(0x0435) + "nt va Toshkent"  # U+0435 is Cyrillic
>>> [kind for piece, kind in script_spans(text)]
['mixed', None, 'latin', None, 'latin']
>>> fold_homoglyphs(text)
'Toshkent va Toshkent'

Neither looks for protected spans (:mod:`akademtranslit.protect`): a URL is
words and punctuation to them.
"""

from __future__ import annotations

from .detection import _is_cyrillic_letter, _is_latin_letter
from .rules import (
    _WORD_RE,
    CYRILLIC_WORD,
    LATIN_1995_WORD,
    LATIN_2026_WORD,
    O_FORM_WORD,
    word_class,
)
from .tables import HOMOGLYPHS

# What script_spans calls each class of rules.word_class; the rest are "latin".
_KINDS = {
    CYRILLIC_WORD: "cyrillic",
    LATIN_2026_WORD: "latin_2026",
    O_FORM_WORD: "latin_2026",
    LATIN_1995_WORD: "latin_1995",
}

_TO_CYRILLIC = {latin: cyrillic for latin, cyrillic in HOMOGLYPHS}
_TO_LATIN = {cyrillic: latin for latin, cyrillic in HOMOGLYPHS}

# s with comma below, U+0219 and U+0218, an input form of s with cedilla.
_S_WITH_CEDILLA = {chr(0x0219): "ş", chr(0x0218): "Ş"}


def script_spans(text: str) -> list:
    """Split ``text`` into its words and the text between them.

    Returns a list of ``(piece, kind)`` pairs; joined, the pieces give
    ``text`` back exactly, and empty text gives ``[]``. A word -- a run of
    letters, joined by apostrophe marks, as conversion sees it -- has one of
    these kinds:

    * ``"cyrillic"``: Cyrillic letters (U+0400-U+052F);
    * ``"latin_2026"``: one of ``ş ç ğ ö``, or another input form of them
      (s with comma below, o with macron, o with caron);
    * ``"latin_1995"``: ``oʻ`` or ``gʻ``, with any apostrophe mark;
    * ``"latin"``: any other word without a Cyrillic letter, which is
      written the same way in both Latin orthographies, or which only has
      ``sh`` or ``ch``, a letter in one and two in the other (``Shahar``);
    * ``"mixed"``: both Cyrillic and Latin letters (see
      :func:`fold_homoglyphs`).

    The text between words has the kind ``None``. Protected spans are not
    looked for.

    >>> script_spans("Oʻzbekiston va Özbekiston, Ўзбекистон")  # doctest: +NORMALIZE_WHITESPACE
    [('Oʻzbekiston', 'latin_1995'), (' ', None), ('va', 'latin'), (' ', None),
     ('Özbekiston', 'latin_2026'), (', ', None), ('Ўзбекистон', 'cyrillic')]
    """
    pieces = []
    end = 0
    for match in _WORD_RE.finditer(text):
        if match.start() > end:
            pieces.append((text[end:match.start()], None))
        word = match.group()
        pieces.append((word, _kind(word)))
        end = match.end()
    if end < len(text):
        pieces.append((text[end:], None))
    return pieces


def _kind(word: str) -> str:
    kind = word_class(word)
    if kind == CYRILLIC_WORD and any(_is_latin_letter(ch) for ch in word):
        return "mixed"
    return _KINDS.get(kind, "latin")


def homoglyph_spans(text: str) -> list:
    """Where :func:`fold_homoglyphs` changes ``text``.

    Returns a list of ``(start, stop, word)``: for each word it changes, where
    the word is in ``text`` and how it is written after the change, in order.
    No change gives ``[]``.

    >>> homoglyph_spans("Toshk" + chr(0x0435) + "nt va Toshkent")
    [(0, 8, 'Toshkent')]
    """
    spans = []
    for match in _WORD_RE.finditer(text):
        word = match.group()
        folded = _fold_word(word)
        if folded != word:
            spans.append((match.start(), match.end(), folded))
    return spans


def fold_homoglyphs(text: str) -> str:
    """Write each word that has both Latin and Cyrillic letters in one of them.

    For such a word:

    1. the alphabet with more letters in the word wins; with as many of each,
       the word is left as it is;
    2. each letter of the other alphabet is replaced by its look-alike from
       :data:`~akademtranslit.tables.HOMOGLYPHS`;
    3. if one of them has no look-alike there, the word is left as it is: it
       is a mixed word, not a slip.

    In a Latin word, s with comma below (U+0219, U+0218) also becomes ``ş``
    (``Ş``), the letter it stands for. Everything else is left as it is, and
    the function is idempotent. Run it on text that people type before
    :func:`~akademtranslit.convert`: a Latin word with a Cyrillic letter in it
    is read as Cyrillic.

    >>> fold_homoglyphs("Т" + chr(0x006F) + "шкент")  # U+006F is Latin
    'Тошкент'
    """
    out = []
    end = 0
    for start, stop, word in homoglyph_spans(text):
        out.append(text[end:start])
        out.append(word)
        end = stop
    out.append(text[end:])
    return "".join(out)


def _fold_word(word: str) -> str:
    latin = sum(1 for ch in word if _is_latin_letter(ch))
    cyrillic = sum(1 for ch in word if _is_cyrillic_letter(ch))
    if latin and cyrillic:
        if latin == cyrillic:
            return word
        if latin > cyrillic:
            table, minority = _TO_LATIN, _is_cyrillic_letter
        else:
            table, minority = _TO_CYRILLIC, _is_latin_letter
        out = []
        for ch in word:
            if minority(ch):
                twin = table.get(ch)
                if twin is None:
                    return word
                ch = twin
            out.append(ch)
        word = "".join(out)
        if cyrillic > latin:
            return word
    elif cyrillic:
        return word
    return "".join(_S_WITH_CEDILLA.get(ch, ch) for ch in word)
