"""Closed-set answers about which script, and which Cyrillic, a text is in.

:func:`~akademtranslit.detect_script` answers in orthographies and is a
contract that does not change. The two functions here answer narrower
questions for routing: is this Latin, Cyrillic or both, and is a Cyrillic text
Uzbek or Russian.
"""

from __future__ import annotations

import unicodedata

_CYRILLIC_LO = 0x0400
_CYRILLIC_HI = 0x052F

_UZBEK_LETTERS = frozenset("ўқғҳЎҚҒҲ")
_RUSSIAN_LETTERS = frozenset("щыЩЫ")


def _is_cyrillic_letter(ch: str) -> bool:
    return ch.isalpha() and _CYRILLIC_LO <= ord(ch) <= _CYRILLIC_HI


def _is_latin_letter(ch: str) -> bool:
    return ch.isalpha() and unicodedata.name(ch, "").startswith("LATIN ")


def script_class(text: str) -> str:
    """Return ``"latin"``, ``"cyrillic"`` or ``"mixed"`` -- always one of the three.

    A Cyrillic letter is a letter in U+0400-U+052F; a Latin letter is a letter
    whose Unicode name begins with ``LATIN``. Nothing else is counted: not the
    modifier letters ``ʻ`` ``ʼ`` ``ʹ``, not other scripts, not digits or
    punctuation. Text with both kinds of letter is ``"mixed"``, with Cyrillic
    only ``"cyrillic"``, and anything else -- Latin only, or no letters at all
    -- ``"latin"``.

    >>> script_class("Тошкент")
    'cyrillic'
    >>> script_class("Toshkent")
    'latin'
    >>> script_class("Аliyev")  # the first letter is Cyrillic
    'mixed'
    >>> script_class("2026")
    'latin'
    """
    cyrillic = latin = False
    for ch in text:
        if _is_cyrillic_letter(ch):
            cyrillic = True
        elif _is_latin_letter(ch):
            latin = True
        if cyrillic and latin:
            return "mixed"
    return "cyrillic" if cyrillic else "latin"


def cyrillic_language(text: str) -> str:
    """Return ``"uz"``, ``"ru"``, ``"mixed"`` or ``"unknown"`` for Cyrillic text.

    A heuristic for routing, not a language identifier. It looks for letters
    only one of the two alphabets has: ``ў қ ғ ҳ`` for Uzbek, ``щ ы`` for
    Russian, in either case. Uzbek letters only give ``"uz"``, Russian letters
    only ``"ru"``, both ``"mixed"``, and neither ``"unknown"``. Most of the
    letters are shared, so short text is often ``"unknown"`` -- and so is any
    text with no Cyrillic at all.

    >>> cyrillic_language("Ўзбекистон")
    'uz'
    >>> cyrillic_language("Мы здесь")
    'ru'
    >>> cyrillic_language("бир")
    'unknown'
    """
    uzbek = any(ch in _UZBEK_LETTERS for ch in text)
    russian = any(ch in _RUSSIAN_LETTERS for ch in text)
    if uzbek and russian:
        return "mixed"
    if uzbek:
        return "uz"
    if russian:
        return "ru"
    return "unknown"
