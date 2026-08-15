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

# --- Cyrillic ----------------------------------------------------------------

#: Cyrillic vowels. Needed by the ``е`` rule: ``е`` is read ``ye`` at the start
#: of a word and after another vowel, ``e`` elsewhere.
CYRILLIC_VOWELS = frozenset("аеёиоуўэюяы")

#: Context-free Cyrillic to ``latin_1995``. Lowercase keys; case is restored by
#: the caller. Entries whose reading depends on position (``е``, ``ц``, and
#: ``с`` before ``ҳ``) are handled in :mod:`akademtranslit.rules` instead.
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
    "ь": "",    # not represented in the Latin orthographies
}

#: ``latin_1995`` to Cyrillic, longest match first. The engine tries these in
#: order at each position, so digraphs must precede their component letters.
#: Positional readings (``e`` vs ``ye``) are resolved in
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
    ("ts", "ц"),
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

# --- the 2026 reform ---------------------------------------------------------
#
# The whole reform is these four rows. Keeping it as one small table is
# deliberate: if the final decree settles on a different glyph for one of them,
# exactly one line here changes and the rest of the library follows.
#
# NOTE: an earlier draft of the reform proposed ``ō`` (o with macron) rather
# than ``ö`` for ``oʻ``. This library emits ``ö`` and accepts ``ō`` on input as
# an alias, so text written under either convention reads correctly.

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
#: output form. Applied before anything else when reading ``latin_2026`` text.
LATIN_2026_INPUT_ALIASES = (
    ("ō", "ö"),  # earlier reform draft used o-macron for oʻ
    ("ǒ", "ö"),
)

#: The 28 letters of the reformed alphabet, in alphabetical order, plus the
#: tutuq belgisi. Exposed for callers building keyboards, sort keys or
#: validators.
LATIN_2026_ALPHABET = (
    "a", "b", "ç", "d", "e", "f", "g", "ğ", "h", "i", "j", "k", "l", "m",
    "n", "o", "ö", "p", "q", "r", "s", "ş", "t", "u", "v", "x", "y", "z",
)
