"""Cross-script normalization -- one search key for all three orthographies.

Transliteration answers "how is this written in the other alphabet?".
Normalization answers a different question: "are these two strings the same
word?" -- across orthographies, apostrophe styles, casing and punctuation.

The two are not the same function and must not be confused.
:func:`~akademtranslit.to_latin` is reversible and display-grade;
:func:`normalize` is deliberately lossy and produces a key nobody should ever
show to a reader.

The key is what makes a search index work when the same author, journal or
institution is spelled three ways in three different records:

>>> normalize("Şoşimova") == normalize("Shoshimova") == normalize("Шошимова")
True

**Out of scope.** Romanization-variant folding (``kh`` <-> ``x``,
``zh`` <-> ``j``, ``ye`` <-> ``e``), translation, and fuzzy or edit-distance
matching are all deliberately excluded. Folding them here would collapse names
that are genuinely different -- ``Karimov`` and ``Xarimov`` are not the same
person. Handle those upstream, as scored candidates, not as an equality key.
"""

from __future__ import annotations

import re
import unicodedata

from .rules import cyrillic_word_to_latin_1995, map_words
from .tables import APOSTROPHE_VARIANTS, TURNED_COMMA, TUTUQ

# Cyrillic block bounds. Anything in this range that the table below does not
# cover is dropped rather than passed through, so a stray Old Church Slavonic
# letter cannot leak into a key.
_CYRILLIC_LO = 0x0400
_CYRILLIC_HI = 0x04FF

# Residual Cyrillic fold, applied AFTER the real transliteration has run. Its
# job is the leftovers: a homoglyph sitting inside an otherwise Latin word, or a
# letter from a neighbouring Cyrillic orthography. Context-free by design --
# anything positional was already handled by the transliterator.
_CYRILLIC_FOLD = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sh",
    "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    # Uzbek-specific letters, folded to their bare Latin base so that ў/oʻ/ö
    # and ғ/gʻ/ğ each collapse to one character.
    "ў": "o", "ғ": "g", "қ": "q", "ҳ": "h",
    # Homoglyphs from neighbouring Cyrillic orthographies, seen in metadata
    # harvested from mixed-script sources.
    "ј": "j", "і": "i", "ї": "i", "є": "e", "ѓ": "g", "ќ": "k",
}

# The reformed letters, folded to the same base the Cyrillic table produces.
# ``ş`` -> ``sh`` matches ``ш`` -> ``sh``; ``ö`` -> ``o`` matches ``ў`` -> ``o``
# and matches ``oʻ`` once the mark is stripped.
_LATIN_2026_FOLD = {
    "ş": "sh",
    "ç": "ch",
    "ğ": "g",
    "ö": "o",
    "ō": "o",  # the alternative reform draft's glyph for oʻ
    "ǒ": "o",
}

_MARKS = frozenset(APOSTROPHE_VARIANTS) | {TURNED_COMMA, TUTUQ}

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]")
_WHITESPACE_RE = re.compile(r"\s+")
_LATIN_RE = re.compile(r"[A-Za-z]")


def fold_cyrillic(text: str) -> str:
    """Fold Cyrillic characters to Latin; pass everything else through.

    Lowercase-oriented and lossy -- the building block for :func:`normalize`,
    which lowercases first. Cyrillic-block characters absent from the fold table
    are dropped.
    """
    out: list[str] = []
    for ch in text:
        if ch in _CYRILLIC_FOLD:
            out.append(_CYRILLIC_FOLD[ch])
        elif _CYRILLIC_LO <= ord(ch) <= _CYRILLIC_HI:
            continue
        else:
            out.append(ch)
    return "".join(out)


def fold_latin_2026(text: str) -> str:
    """Fold the reformed letters to their ``latin_1995``-shaped bases."""
    return "".join(_LATIN_2026_FOLD.get(ch, ch) for ch in text)


def normalize(text: str) -> str:
    """Return the cross-script match key for ``text``.

    Lowercase Latin alphanumerics, single-space separated. The same word written
    in Cyrillic, ``latin_1995`` or ``latin_2026`` yields the same key, and so do
    all the apostrophe styles and any amount of punctuation.

    Cyrillic is put through the real transliterator first, rather than a flat
    character table. That is what makes the positional rules carry into the key:
    Чоршанбиев folds to ``chorshanbiyev`` -- matching the Latin spelling
    ``Chorshanbiyev`` -- where a context-free table would produce
    ``chorshanbiev`` and miss the match. Marks are stripped afterwards, so
    ``oʻ``, ``ö`` and ``ў`` all converge on ``o``.

    >>> normalize("Oʻzbekiston Respublikasi")
    'ozbekiston respublikasi'
    >>> normalize("Ўзбекистон Республикаси")
    'ozbekiston respublikasi'
    >>> normalize("Özbekiston  Respublikasi!")
    'ozbekiston respublikasi'

    Idempotent: ``normalize(normalize(x)) == normalize(x)``.
    """
    if not text or not text.strip():
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    if is_cyrillic(text):
        text = map_words(text, cyrillic_word_to_latin_1995)
    text = "".join(ch for ch in text if ch not in _MARKS)
    text = fold_latin_2026(text)
    text = fold_cyrillic(text)
    text = _NON_ALNUM_RE.sub(" ", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def is_cyrillic(text: str) -> bool:
    """True if ``text`` contains any Cyrillic-block letter.

    First-hit detection is sufficient in practice: Uzbek Cyrillic strings are
    wholly Cyrillic, and a Latin string carrying one stray Cyrillic letter is a
    homoglyph contamination that should be treated as Cyrillic-adjacent anyway.
    """
    return any(_CYRILLIC_LO <= ord(ch) <= _CYRILLIC_HI for ch in text)
