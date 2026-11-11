"""AkademTranslit -- Uzbek transliteration across three orthographies.

Uzbek is written three ways at once. Cyrillic still carries the archives, the
older scholarly record and much of the press. The 1995 Latin alphabet carries
official documents and the web. The 2026 reform replaces that alphabet's four
multi-character letters (``sh``, ``ch``, ``gʻ``, ``oʻ``) with single ones
(``ş``, ``ç``, ``ğ``, ``ö``). All three will coexist for years.

This library converts between them and, separately, produces a normalization
key that makes one word searchable across all three.

    >>> from akademtranslit import to_latin, to_cyrillic, convert, normalize
    >>> to_latin("Тошкент давлат университети")
    'Toşkent davlat universiteti'
    >>> to_latin("Тошкент давлат университети", variant="latin_1995")
    'Toshkent davlat universiteti'
    >>> to_cyrillic("Oʻzbekiston Respublikasi")
    'Ўзбекистон Республикаси'
    >>> convert("Gʻafurov", source="latin_1995", target="latin_2026")
    'Ğafurov'
    >>> normalize("Şoşimova") == normalize("Shoshimova") == normalize("Шошимова")
    True
"""

from __future__ import annotations

from .apostrophes import normalize_apostrophes
from .collation import sort_key
from .detection import cyrillic_language, script_class
from .normalize import fold_cyrillic, is_cyrillic, normalize
from .rules import (
    cyrillic_word_to_latin_1995,
    latin_1995_word_to_2026,
    latin_1995_word_to_cyrillic,
    latin_2026_canonical_word,
    latin_2026_word_to_1995,
    map_words,
)
from .tables import (
    CYRILLIC,
    CYRILLIC_ALPHABET,
    LATIN_1995,
    LATIN_1995_ALPHABET,
    LATIN_2026,
    LATIN_2026_ALPHABET,
    REFORM_PAIRS,
    RULES_VERSION,
    SCRIPTS,
    TURNED_COMMA,
    TUTUQ,
)
from .tags import _orthography, script_for_tag, tag_for_script

__version__ = "0.3.0"

__all__ = [
    "CYRILLIC",
    "CYRILLIC_ALPHABET",
    "LATIN_1995",
    "LATIN_1995_ALPHABET",
    "LATIN_2026",
    "LATIN_2026_ALPHABET",
    "REFORM_PAIRS",
    "RULES_VERSION",
    "SCRIPTS",
    "TURNED_COMMA",
    "TUTUQ",
    "__version__",
    "convert",
    "cyrillic_language",
    "detect_script",
    "fold_cyrillic",
    "is_cyrillic",
    "normalize",
    "normalize_apostrophes",
    "script_class",
    "script_for_tag",
    "sort_key",
    "tag_for_script",
    "to_cyrillic",
    "to_latin",
]

# Letters that exist only in latin_2026. One of them anywhere in the text is
# conclusive: no other Uzbek orthography uses them. The escapes are the draft
# glyphs for ö: ō U+014D, ǒ U+01D2, Ō U+014C and Ǒ U+01D1.
_REFORM_LETTERS = frozenset("şçğöŞÇĞÖ" "\u014d\u01d2\u014c\u01d1")

# Every conversion is expressed as a chain of word-level steps. latin_1995 is
# the pivot -- it is the only orthography that shares a boundary with both of
# the others, so no pair needs a table of its own. The draft glyphs ō and ǒ
# are read as ö whenever the source or the target is latin_2026; a pair not
# listed (cyrillic or latin_1995 to itself) has no steps.
_PIPELINES: dict[tuple[str, str], tuple] = {
    (CYRILLIC, LATIN_1995): (cyrillic_word_to_latin_1995,),
    (CYRILLIC, LATIN_2026): (
        cyrillic_word_to_latin_1995,
        latin_1995_word_to_2026,
        latin_2026_canonical_word,  # ō U+014D, ǒ U+01D2 in a Latin word of Cyrillic text
    ),
    (LATIN_1995, CYRILLIC): (latin_1995_word_to_cyrillic,),
    (LATIN_1995, LATIN_2026): (latin_2026_canonical_word, latin_1995_word_to_2026),
    (LATIN_2026, LATIN_1995): (latin_2026_word_to_1995,),
    (LATIN_2026, LATIN_2026): (latin_2026_canonical_word,),
    (LATIN_2026, CYRILLIC): (latin_2026_word_to_1995, latin_1995_word_to_cyrillic),
}


def detect_script(text: str) -> str:
    """Return which of the three orthographies ``text`` is written in.

    A single Cyrillic letter is enough to call it Cyrillic, and a single
    reformed letter is enough to call it ``latin_2026``. Text with neither --
    including text with no letters at all -- is reported as ``latin_1995``,
    which is the safe default: ``latin_1995`` is a superset of plain ASCII
    Uzbek, so treating unmarked Latin as ``latin_1995`` never mis-reads it.

    >>> detect_script("Самарқанд")
    'cyrillic'
    >>> detect_script("Toʻqqiz")
    'latin_1995'
    >>> detect_script("Töqqiz")
    'latin_2026'

    **The one ambiguous case.** A ``latin_2026`` string that happens to contain
    none of the four reformed letters is indistinguishable from ``latin_1995``.
    That is harmless for almost every word, because the two orthographies write
    such words identically -- but not for a word containing a real s+h sequence:
    ``Ishoq`` is the name Исҳоқ in ``latin_2026`` and the non-word Ишоқ in
    ``latin_1995``. Pass ``source`` explicitly to :func:`convert` when the
    orthography is known from context (a document's encoding, a database
    column) rather than relying on detection.
    """
    if is_cyrillic(text):
        return CYRILLIC
    if any(ch in _REFORM_LETTERS for ch in text):
        return LATIN_2026
    return LATIN_1995


def convert(text: str, source: str = "auto", target: str = LATIN_2026) -> str:
    """Convert ``text`` from one orthography to another.

    ``source`` may be ``"auto"`` (the default) to run :func:`detect_script`
    first. Both ``source`` and ``target`` otherwise take one of the values in
    :data:`~akademtranslit.tables.SCRIPTS`, or a language tag for one of them
    (``uz-Cyrl``, ``uz-Latn-1995``, ``uz-Latn-2026``; see
    :mod:`akademtranslit.tags`).

    Digits, punctuation and whitespace pass through untouched, so mixed content
    survives intact:

    >>> convert("Ilmiy jurnal, 2026-yil, 12-son", target="latin_2026")
    'Ilmiy jurnal, 2026-yil, 12-son'

    Converting to the orthography the text is already in is not a no-op: it
    canonicalises the apostrophe marks, so ``o'zbek``, ``o’zbek`` and ``oʻzbek``
    all come out as ``oʻzbek``. That makes the function idempotent and makes its
    output safe to use as a stored form.
    """
    if source not in SCRIPTS and source != "auto":
        source = _orthography(
            source,
            f"unknown source script: {source!r}; expected one of {SCRIPTS} or 'auto'",
            stacklevel=2,
        )
    if target not in SCRIPTS:
        target = _orthography(
            target, f"unknown target script: {target!r}; expected one of {SCRIPTS}", stacklevel=2
        )
    if not text:
        return text

    if source == "auto":
        source = detect_script(text)

    steps = _PIPELINES.get((source, target), ())

    def _word(word: str) -> str:
        for step in steps:
            word = step(word)
        return word

    # map_words canonicalises the marks even when `steps` is empty, which is
    # what makes a same-script conversion a normalising pass rather than a no-op.
    return map_words(text, _word)


def to_latin(text: str, variant: str = LATIN_2026) -> str:
    """Convert ``text`` to Latin, in ``variant`` (default: the 2026 alphabet).

    Accepts Cyrillic or either Latin orthography as input, so it doubles as the
    1995 -> 2026 migration function. ``variant`` may also be a language tag
    for a Latin orthography (``uz-Latn-1995``, ``uz-Latn-2026``).

    >>> to_latin("Мирзо Улуғбек")
    'Mirzo Uluğbek'
    >>> to_latin("Мирзо Улуғбек", variant="latin_1995")
    'Mirzo Ulugʻbek'
    >>> to_latin("Ulugʻbek", variant="latin_2026")
    'Uluğbek'
    """
    if variant not in (LATIN_1995, LATIN_2026):
        unknown = f"unknown Latin variant: {variant!r}; expected {LATIN_1995!r} or {LATIN_2026!r}"
        if variant in SCRIPTS:
            raise ValueError(unknown)
        script = _orthography(variant, unknown, stacklevel=2)
        if script not in (LATIN_1995, LATIN_2026):
            raise ValueError(
                f"{variant!r} names {script!r}, not a Latin orthography; "
                f"expected {LATIN_1995!r} or {LATIN_2026!r}, or a tag for one of them"
            )
        variant = script
    return convert(text, source="auto", target=variant)


def to_cyrillic(text: str) -> str:
    """Convert ``text`` to Cyrillic from either Latin orthography.

    >>> to_cyrillic("Abu Rayhon Beruniy")
    'Абу Райҳон Беруний'
    >>> to_cyrillic("Qaşqadaryo")
    'Қашқадарё'
    """
    return convert(text, source="auto", target=CYRILLIC)
