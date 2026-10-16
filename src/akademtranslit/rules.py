"""Context-dependent transliteration rules and the word-level engine.

The tables in :mod:`akademtranslit.tables` cover characters whose reading never
changes. This module covers the ones that do, plus the machinery that applies
both: tokenisation, greedy longest-match rewriting, and case restoration.

Four positional rules are implemented:

``е``
    Read ``ye`` at the start of a word and after a vowel or a soft/hard sign
    (Ер -> Yer, поезд -> poyezd), ``e`` otherwise (тезда -> tezda). The reverse
    direction mirrors it: word-initial ``e`` is ``э``, elsewhere ``е``.

``ц``
    Read ``ts`` after a vowel (милиция -> militsiya) and ``s`` otherwise --
    word-initially or after a consonant (цирк -> sirk, функция -> funksiya).
    A heuristic, not a bijection: ц occurs only in loanwords and their spelling
    is genuinely inconsistent. See the lossy-mapping table in the README.

``ts``
    The Latin -> Cyrillic side of the same letter. ``ts`` is ц in loanwords
    (operatsiya -> операция, leykotsit -> лейкоцит) but т + с where a stem
    ending in t meets an Uzbek suffix beginning with s (ketsa -> кетса,
    hayotsiz -> ҳаётсиз), and т + ш where the s opens the ``sh`` digraph
    (adabiyotshunos -> адабиётшунос). Decided from the shape of the whole word,
    without a dictionary; :func:`_ts_splits` lists the checks in order.

``с`` before ``ҳ``
    Written ``sʼh`` in ``latin_1995`` so it is not misread as the ``sh``
    digraph (исҳоқ -> isʼhoq, not ishoq). In ``latin_2026`` the separator is
    unnecessary, because ``ş`` carries the digraph's sound.
"""

from __future__ import annotations

import re

from .tables import (
    APOSTROPHE_VARIANTS,
    CYRILLIC_TO_LATIN_1995,
    CYRILLIC_VOWELS,
    LATIN_1995_TO_2026_STEPS,
    LATIN_1995_TO_CYRILLIC,
    LATIN_2026_INPUT_ALIASES,
    LATIN_2026_TO_1995_STEPS,
    LATIN_VOWELS,
    TURNED_COMMA,
    TUTUQ,
)

# --- tokenisation ------------------------------------------------------------

_APOS_CLASS = "[" + re.escape("".join(APOSTROPHE_VARIANTS)) + "]"

# A word is a run of letters, optionally joined by apostrophe-like marks, and
# optionally ending in one -- but only after ``o`` or ``g``, so that a closing
# quote in 'salom' is not swallowed while the real letter in togʻ is kept.
_WORD_RE = re.compile(
    r"[^\W\d_]+(?:" + _APOS_CLASS + r"[^\W\d_]+)*(?:(?<=[oOgG])" + _APOS_CLASS + r")?",
    re.UNICODE,
)

# Marks that belong to a letter (oʻ, gʻ) versus the standalone tutuq belgisi.
# Input may spell either with any of the variants; this resolves which is which
# by looking at the preceding letter.
_TURNED_COMMA_AFTER = frozenset("og")


def canonicalize_marks(word_lower: str) -> str:
    """Rewrite every apostrophe variant to its canonical character.

    After ``o`` or ``g`` the mark is part of a letter and becomes
    :data:`~akademtranslit.tables.TURNED_COMMA`; anywhere else it is the tutuq
    belgisi and becomes :data:`~akademtranslit.tables.TUTUQ`.

    This is why ``o'zbek``, ``o’zbek`` and ``oʻzbek`` all read identically while
    ``ma'no`` still resolves to the tutuq belgisi in ``maʼno``.
    """
    out: list[str] = []
    for i, ch in enumerate(word_lower):
        if ch in APOSTROPHE_VARIANTS:
            prev = out[-1] if out else ""
            out.append(TURNED_COMMA if prev in _TURNED_COMMA_AFTER else TUTUQ)
        else:
            out.append(ch)
    return "".join(out)


def apply_case(source: str, result: str) -> str:
    """Restore ``source``'s casing onto ``result``.

    Per token, so a name in a sentence and the same name in a heading both come
    out right:

    * all-caps in, all-caps out -- ``ШОШИМОВА`` -> ``ŞOŞIMOVA``, never
      ``Şoşimova``;
    * initial capital in, initial capital out;
    * anything else lowercase.

    Length changes freely between input and output (``ш`` is one character,
    ``sh`` is two), so casing is decided from the source and re-applied, never
    copied position by position.

    Only letters that have case take part. ``ʻ`` and ``ʼ`` are letters to
    Unicode (category Lm) but have no case, so ``OʻZBEKISTON`` is all-caps and
    gives ``ЎЗБЕКИСТОН``, not ``Ўзбекистон``.
    """
    letters = [ch for ch in source if ch.lower() != ch.upper()]
    if not letters or not result:
        return result
    if len(letters) > 1 and all(ch.isupper() for ch in letters):
        return result.upper()
    if letters[0].isupper():
        return result[0].upper() + result[1:]
    return result


def map_words(text: str, transform) -> str:
    """Apply ``transform`` to each word of ``text``, preserving everything else.

    ``transform`` receives the lowercased, mark-canonicalised word and returns
    its converted form; casing is restored afterwards. Digits, punctuation and
    whitespace pass through untouched, which is what keeps mixed-script and
    mixed-content input (citations, DOIs, years) intact.
    """

    def _one(match: re.Match[str]) -> str:
        source = match.group(0)
        converted = transform(canonicalize_marks(source.lower()))
        return apply_case(source, converted)

    return _WORD_RE.sub(_one, text)


# --- Cyrillic -> latin_1995 --------------------------------------------------


def cyrillic_word_to_latin_1995(word: str) -> str:
    """Convert one lowercase Cyrillic word to ``latin_1995``."""
    out: list[str] = []
    for i, ch in enumerate(word):
        prev = word[i - 1] if i else ""
        nxt = word[i + 1] if i + 1 < len(word) else ""

        if ch == "е":
            initial_or_after_vowel = i == 0 or prev in CYRILLIC_VOWELS or prev in "ъь"
            out.append("ye" if initial_or_after_vowel else "e")
        elif ch == "ц":
            # ts only after a vowel: милиция -> militsiya, революция ->
            # revolyutsiya. Word-initially and after a consonant it reduces to
            # s: цирк -> sirk, функция -> funksiya, концерт -> konsert.
            after_vowel = i > 0 and prev in CYRILLIC_VOWELS
            out.append("ts" if after_vowel else "s")
        elif ch == "с" and nxt == "ҳ":
            # Emit the separator now; the ҳ that follows supplies the h.
            out.append("s" + TUTUQ)
        else:
            out.append(CYRILLIC_TO_LATIN_1995.get(ch, ch))
    return "".join(out)


# --- latin_1995 -> Cyrillic --------------------------------------------------

# Suffixes that begin with s and attach to a stem ending in t. A ``ts`` whose s
# opens one of these is т + с: ketsa, ketsin, hayotsiz, mehnatsevar.
_TS_SUFFIXES = (
    "sa", "sak", "sam", "sang", "sangiz", "salar",  # conditional
    "sin", "sinlar",                                # third-person imperative
    "siz", "sizlik",                                # privative
    "sevar",                                        # -loving
)

# What may follow those, any number of times. No bare vowel or lone consonant
# belongs here: that is what keeps meditsina (sin + a) and natsizm (siz + m) ц.
_TS_FOLLOWERS = (
    "lik", "ligi", "lar", "roq",                    # derivation, plural
    "ga", "ka", "da", "dan", "ni", "ning",          # case
    "man", "san", "miz", "siz", "dir",              # person
    "mi", "chi",                                    # particles
)

_TS_SUFFIX_RE = re.compile(
    "(?:" + "|".join(_TS_SUFFIXES) + ")(?:" + "|".join(_TS_FOLLOWERS) + ")*"
)

_VOWELS_AND_Y = LATIN_VOWELS | {"y"}


def _ts_splits(word: str, i: int) -> bool:
    """True if the ``ts`` at ``word[i]`` is т + с rather than the letter ц.

    Checked in order; the first that applies decides:

    0. The s opens ``sh`` or ``sʼh``: т + ш (adabiyotshunos -> адабиётшунос).
    1. Word-initial: ц (tsement, tsinga).
    2. ``i`` and then a vowel or ``y`` follow: ц (operatsiya, ratsion,
       patsiyent).
    3. A known loan the suffix check would misread: ц in ``-mitsin``
       (azitromitsin, and azitromitsinni) and in ``glitsin``.
    4. The s opens an Uzbek suffix and everything after it is suffixes: т + с
       (ketsa, ketsinmi, hayotsizlik). Starting with the right letters is not
       enough -- meditsina and natsizm stay ц.
    5. Otherwise ц, the table's reading (leykotsit, protsent, litsey).
    """
    rest = word[i + 1:]
    if rest.startswith("sh") or rest.startswith("s" + TUTUQ + "h"):
        return True
    if i == 0:
        return False
    if word[i + 2:i + 3] == "i" and word[i + 3:i + 4] in _VOWELS_AND_Y:
        return False
    if word.startswith("in", i + 2) and (word.endswith("mi", 0, i) or word[:i] == "gli"):
        return False
    return _TS_SUFFIX_RE.fullmatch(rest) is not None


def latin_1995_word_to_cyrillic(word: str) -> str:
    """Convert one lowercase ``latin_1995`` word to Cyrillic."""
    out: list[str] = []
    i = 0
    length = len(word)
    while i < length:
        # The e/ye rule outranks the table: ``ye`` is always е, a bare ``e`` is
        # э word-initially and е everywhere else.
        if word.startswith("ye", i):
            out.append("е")
            i += 2
            continue
        if word[i] == "e":
            out.append("э" if i == 0 else "е")
            i += 1
            continue
        # ts is ц (the table's row) unless the word splits it. Then only the t
        # is taken here, and the table reads what follows as s or sh.
        if word.startswith("ts", i) and _ts_splits(word, i):
            out.append("т")
            i += 1
            continue

        for source, target in LATIN_1995_TO_CYRILLIC:
            if word.startswith(source, i):
                out.append(target)
                i += len(source)
                break
        else:
            # Not Uzbek-Latin (a digit, a borrowed w/c, a stray glyph) -- keep it.
            out.append(word[i])
            i += 1
    return "".join(out)


# --- latin_1995 <-> latin_2026 -----------------------------------------------


def latin_1995_word_to_2026(word: str) -> str:
    """Convert one lowercase ``latin_1995`` word to ``latin_2026``."""
    for source, target in LATIN_1995_TO_2026_STEPS:
        word = word.replace(source, target)
    return word


def latin_2026_word_to_1995(word: str) -> str:
    """Convert one lowercase ``latin_2026`` word to ``latin_1995``."""
    for source, target in LATIN_2026_INPUT_ALIASES:
        word = word.replace(source, target)
    for source, target in LATIN_2026_TO_1995_STEPS:
        word = word.replace(source, target)
    return word
