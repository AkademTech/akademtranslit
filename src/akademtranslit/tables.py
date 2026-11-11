"""Character tables for the three Uzbek orthographies.

Everything context-free lives here as data; anything that needs to look at the
surrounding characters lives in :mod:`akademtranslit.rules`.

Three orthographies are supported:

``cyrillic``
    The Uzbek Cyrillic alphabet (35 letters), in official use 1940-1993 and
    still dominant in older literature, archives and much of the press.

``latin_1995``
    The Latin alphabet adopted in 1993 and revised in 1995. Four sounds are
    written as digraphs or with a modifier mark: ``sh``, ``ch``, ``gʻ``, ``oʻ``.

``latin_2026``
    The reformed Latin alphabet: the four multi-character forms above become
    single letters ``ş``, ``ç``, ``ğ``, ``ö`` -- 28 letters plus the tutuq
    belgisi.
"""

from __future__ import annotations

# --- orthography identifiers -------------------------------------------------

CYRILLIC = "cyrillic"
LATIN_1995 = "latin_1995"
LATIN_2026 = "latin_2026"

SCRIPTS = (CYRILLIC, LATIN_1995, LATIN_2026)

# --- the rules version -------------------------------------------------------

#: Which rules :func:`~akademtranslit.convert`, :func:`~akademtranslit.to_latin`
#: and :func:`~akademtranslit.to_cyrillic` follow. Before ``+``, the official
#: basis: ``uz-2026-alphabet`` is the 2026 alphabet of Law No. O'RQ-1184,
#: without official spelling rules. After it, this project's rule set, named by
#: the year and month of the release that last changed the output of those
#: three functions. A release that changes none of their output keeps the
#: value; ``tools/golden.py --check`` fails if one does and the value stays.
RULES_VERSION = "uz-2026-alphabet+project-2026.11"

# --- the two modifier marks --------------------------------------------------
#
# These are distinct characters with distinct jobs, and conflating them is the
# single most common defect in Uzbek text processing.

#: U+02BB MODIFIER LETTER TURNED COMMA -- part of the letters ``oʻ`` and ``gʻ``.
TURNED_COMMA = "ʻ"

#: U+02BC MODIFIER LETTER APOSTROPHE -- the tutuq belgisi (glottal stop / vowel
#: length), a letter in its own right. Survives the 2026 reform unchanged.
TUTUQ = "ʼ"

#: Everything seen in the wild for either mark: typewriter quotes, curly quotes,
#: grave and acute accents, prime. Input accepts all of them; output emits only
#: :data:`TURNED_COMMA` and :data:`TUTUQ`.
APOSTROPHE_VARIANTS = (
    "ʻ",  # ʻ turned comma (canonical for oʻ/gʻ)
    "ʼ",  # ʼ modifier apostrophe (canonical for tutuq belgisi)
    "’",  # ’ right single quotation mark
    "‘",  # ‘ left single quotation mark
    "´",  # ´ acute accent
    "ʹ",  # ʹ modifier letter prime
    "'",       # ' ASCII apostrophe
    "`",       # ` grave accent
)

# --- invisible characters --------------------------------------------------------

#: The Default_Ignorable_Code_Point characters of Unicode 15.1, as in ICU 74.2:
#: 4174 code points, as (first, last) ranges, that render as nothing.
#: :func:`~akademtranslit.normalize_apostrophes` removes them with
#: ``strip_invisible=True``. Changes only with the Unicode version it names.
DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD),  # soft hyphen
    (0x034F, 0x034F),  # combining grapheme joiner
    (0x061C, 0x061C),  # Arabic letter mark
    (0x115F, 0x1160),  # Hangul choseong and jungseong fillers
    (0x17B4, 0x17B5),  # Khmer inherent vowels
    (0x180B, 0x180F),  # Mongolian free variation selectors and vowel separator
    (0x200B, 0x200F),  # zero-width space, non-joiner and joiner; LRM, RLM
    (0x202A, 0x202E),  # bidirectional embeddings and overrides
    (0x2060, 0x206F),  # word joiner, invisible operators, bidirectional isolates
    (0x3164, 0x3164),  # Hangul filler
    (0xFE00, 0xFE0F),  # variation selectors
    (0xFEFF, 0xFEFF),  # byte order mark (zero-width no-break space)
    (0xFFA0, 0xFFA0),  # halfwidth Hangul filler
    (0xFFF0, 0xFFF8),  # unassigned specials
    (0x1BCA0, 0x1BCA3),  # shorthand format controls
    (0x1D173, 0x1D17A),  # musical symbol format controls
    (0xE0000, 0xE0FFF),  # tags, variation selectors supplement, unassigned
)

# --- Cyrillic ----------------------------------------------------------------

#: The code points every function counts as Cyrillic: the Cyrillic block
#: (U+0400-U+04FF) and Cyrillic Supplement (U+0500-U+052F).
CYRILLIC_FIRST = 0x0400
CYRILLIC_LAST = 0x052F

#: Cyrillic vowels. Needed by the ``е`` rule: ``е`` is read ``ye`` at the start
#: of a word and after another vowel, ``e`` elsewhere.
CYRILLIC_VOWELS = frozenset("аеёиоуўэюяы")

#: Context-free Cyrillic to ``latin_1995``. Lowercase keys; case is restored by
#: the caller. Entries whose reading depends on position (``е``, ``ц``, ``с``
#: before ``ҳ``, ``ъ`` where it is dropped, and ``ь`` before ``о``) are handled
#: in :mod:`akademtranslit.rules` instead.
CYRILLIC_TO_LATIN_1995 = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "ё": "yo",
    "ж": "j",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "x",
    "ч": "ch",
    "ш": "sh",
    "ъ": TUTUQ,
    "э": "e",
    "ю": "yu",
    "я": "ya",
    # Uzbek-specific letters
    "ў": "o" + TURNED_COMMA,
    "қ": "q",
    "ғ": "g" + TURNED_COMMA,
    "ҳ": "h",
    # Letters that occur only in Russian loanwords. These folds are LOSSY --
    # see "Known lossy mappings" in the README.
    "щ": "sh",  # merges with ш
    "ы": "i",   # merges with и
    "ь": "",    # not represented in the Latin orthographies, except y before о
}

#: ``latin_1995`` to Cyrillic, longest match first. The engine tries these in
#: order at each position, so digraphs must precede their component letters.
#: Positional readings (``e`` vs ``ye``, ``ts`` as ц or т + с) are resolved in
#: :mod:`akademtranslit.rules`.
LATIN_1995_TO_CYRILLIC = (
    # The s+h sequence, written with a tutuq belgisi so it is not read as the
    # ``sh`` digraph. Must be tried before ``sh`` and before the bare tutuq.
    ("s" + TUTUQ + "h", "сҳ"),
    # Letters written with the turned comma.
    ("o" + TURNED_COMMA, "ў"),
    ("g" + TURNED_COMMA, "ғ"),
    # Digraphs.
    ("sh", "ш"),
    ("ch", "ч"),
    # The default only: rules.py splits ts into т + с at a suffix boundary.
    ("ts", "ц"),
    # y before oʻ is й + ў, not ё: yoʻq -> йўқ, yoʻl -> йўл. Must precede
    # ``yo``, which would otherwise take the o and strand the turned comma.
    ("y" + "o" + TURNED_COMMA, "йў"),
    ("yo", "ё"),
    ("yu", "ю"),
    ("ya", "я"),
    # Single letters.
    ("a", "а"),
    ("b", "б"),
    ("d", "д"),
    ("f", "ф"),
    ("g", "г"),
    ("h", "ҳ"),
    ("i", "и"),
    ("j", "ж"),
    ("k", "к"),
    ("l", "л"),
    ("m", "м"),
    ("n", "н"),
    ("o", "о"),
    ("p", "п"),
    ("q", "қ"),
    ("r", "р"),
    ("s", "с"),
    ("t", "т"),
    ("u", "у"),
    ("v", "в"),
    ("x", "х"),
    ("y", "й"),
    ("z", "з"),
    (TUTUQ, "ъ"),
)

#: Latin vowels, for the reverse ``e``/``ye`` rule.
LATIN_VOWELS = frozenset("aeiouö")

#: Loanword stems whose final ``ts`` is ц even though the rest of the word reads
#: like an Uzbek suffix: without this, tablitsa would be tablit + -sa. These are
#: the Russian ``-ица`` nouns common in Uzbek text, and a word must begin with
#: one. The list exists to split ts, not as a dictionary, and is meant to stay
#: this short.
TS_LOANWORD_STEMS = (
    "tablits", "teplits", "stolits", "ulits", "bolnits", "granits", "gostinits",
)

# --- the 2026 reform ---------------------------------------------------------
#
# The whole reform is these four rows, as set by Law No. O'RQ-1184 (signed
# 21 October 2026, in force from 22 April 2027). Keeping it as one small table
# means a change to a glyph is one line here.
#
# The law writes ``ö`` for ``oʻ`` and ``ş`` for ``sh``. A few other glyphs are
# accepted for them on input as aliases (LATIN_2026_INPUT_ALIASES); none of
# them is ever output.

#: The four letters the reform changes, as a plain correspondence table. This is
#: the reform, and it is exposed for callers that want to render it (keyboards,
#: cheat sheets, migration reports).
REFORM_PAIRS = (
    ("sh", "ş"),
    ("ch", "ç"),
    ("g" + TURNED_COMMA, "ğ"),
    ("o" + TURNED_COMMA, "ö"),
)

#: Ordered rewrite steps for ``latin_1995`` -> ``latin_2026``.
#:
#: Order is load-bearing. ``sh`` -> ``ş`` must run BEFORE the separator step, so
#: that the genuine digraph in ``ish`` (work) becomes ``iş`` while the separated
#: s+h in ``isʼhoq`` is left alone and only then loses its now-redundant tutuq
#: belgisi. Reversing the two steps turns ``isʼhoq`` into ``işoq``.
LATIN_1995_TO_2026_STEPS = REFORM_PAIRS + (
    # The separator exists only because ``sh`` is a digraph in latin_1995. Once
    # ``ş`` carries that sound, plain ``sh`` is unambiguous again.
    ("s" + TUTUQ + "h", "sh"),
)

#: Ordered rewrite steps for ``latin_2026`` -> ``latin_1995``. The mirror image:
#: re-introduce the separator first, then expand the four single letters.
LATIN_2026_TO_1995_STEPS = (("sh", "s" + TUTUQ + "h"),) + tuple(
    (new, old) for old, new in REFORM_PAIRS
)

#: Accepted input spellings of the reformed letters that are not the canonical
#: output form. Applied before anything else when reading ``latin_2026`` text:
#: o with macron (U+014D) and o with caron (U+01D2) are read as ``ö``, and s
#: with comma below (U+0219), the Romanian letter, which keyboards and fonts
#: show like ``ş`` (s with cedilla, U+015F), is read as ``ş``.
LATIN_2026_INPUT_ALIASES = (
    ("\u014d", "ö"),  # o with macron
    ("\u01d2", "ö"),  # o with caron
    ("\u0219", "ş"),  # s with comma below
)

# --- ASCII for names and logins -------------------------------------------------

#: How :func:`~akademtranslit.to_ascii` writes in ASCII the letters that
#: conversion to ``latin_1995`` leaves: the 1995 letters with the turned comma,
#: and a 2026 letter in a protected span or in a Latin word of Cyrillic text.
#: Capital ``Ş`` and ``Ç`` are in :data:`ASCII_CAPITALS`. The apostrophe marks
#: are removed after it. A project scheme for names and logins, not a passport
#: standard. Frozen: it changes only in a major release.
ASCII_SCHEME = (
    ("o" + TURNED_COMMA, "o"),
    ("O" + TURNED_COMMA, "O"),
    ("g" + TURNED_COMMA, "g"),
    ("G" + TURNED_COMMA, "G"),
    ("ş", "sh"),
    ("ç", "ch"),
    ("ğ", "g"),
    ("Ğ", "G"),
    ("ö", "o"),
    ("Ö", "O"),
)

#: Capital ``Ş`` and ``Ç`` for :func:`~akademtranslit.to_ascii`, as (letter,
#: beside a capital, otherwise). Contextual: ``SH`` and ``CH`` when the
#: character before or after is a capital letter (``ŞAHAR`` -> ``SHAHAR``),
#: ``Sh`` and ``Ch`` otherwise (``Şavkat`` -> ``Shavkat``), the way
#: ``latin_2026`` -> ``latin_1995`` writes them. Applied after
#: :data:`ASCII_SCHEME`. Frozen like it: it changes only in a major release.
ASCII_CAPITALS = (
    ("Ş", "SH", "Sh"),
    ("Ç", "CH", "Ch"),
)

# --- alphabets -----------------------------------------------------------------
#
# The letters of each orthography in its alphabetical order. Exposed for callers
# building keyboards, sort keys or validators; :func:`akademtranslit.sort_key`
# sorts by them.

#: The 28 letters of the 2026 alphabet, in the order of Law No. O'RQ-1184.
#: The tutuq belgisi belongs to the alphabet but is not a letter: see TUTUQ.
LATIN_2026_ALPHABET = (
    "a", "b", "d", "e", "f", "g", "ğ", "h", "i", "j", "k", "l", "m", "n",
    "o", "ö", "p", "q", "r", "s", "ş", "ç", "t", "u", "v", "x", "y", "z",
)

#: The 1995 alphabet in sorting order: 24 letters, then oʻ gʻ sh ch
#: (the order of the CLDR "uz" collation). The tutuq belgisi and ng are not units.
LATIN_1995_ALPHABET = (
    "a", "b", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o",
    "p", "q", "r", "s", "t", "u", "v", "x", "y", "z",
    "o" + TURNED_COMMA, "g" + TURNED_COMMA, "sh", "ch",
)

#: The 35 letters of the Uzbek Cyrillic alphabet; Ў Қ Ғ Ҳ follow Я.
CYRILLIC_ALPHABET = (
    "а", "б", "в", "г", "д", "е", "ё", "ж", "з", "и", "й", "к", "л", "м",
    "н", "о", "п", "р", "с", "т", "у", "ф", "х", "ц", "ч", "ш", "ъ", "ь",
    "э", "ю", "я", "ў", "қ", "ғ", "ҳ",
)
