"""Context-dependent transliteration rules and the word-level engine.

The tables in :mod:`akademtranslit.tables` cover characters whose reading never
changes. This module covers the ones that do, plus the machinery that applies
both: tokenisation, greedy longest-match rewriting, and case restoration.

Seven positional rules are implemented:

``е``
    Read ``ye`` at the start of a word and after a vowel or a soft/hard sign
    (Ер -> Yer, поезд -> poyezd), ``e`` otherwise (тезда -> tezda).

``e``
    The Latin -> Cyrillic side. ``ye`` is always ``е``. A bare ``e`` is ``э``
    at the start of a word (ekran -> экран) and after a vowel (poeziya ->
    поэзия, aeroport -> аэропорт), except before ``v`` (Aliev -> Алиев, so a
    surname romanized the Russian way keeps its Cyrillic form); ``е``
    everywhere else (tezda -> тезда).

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
    (adabiyotshunos -> адабиётшунос). Decided from the shape of the whole word
    and a short list of loanwords; :func:`_ts_splits` lists the checks in
    order.

``с`` before ``ҳ``
    Written ``sʼh`` in ``latin_1995`` so it is not misread as the ``sh``
    digraph (исҳоқ -> isʼhoq, not ishoq). In ``latin_2026`` the separator is
    unnecessary, because ``ş`` carries the digraph's sound.

``ъ``
    Dropped after a consonant before ``е ё ю я`` (объект -> obyekt, съёмка ->
    syomka) and after ``ў`` (мўъжиза -> moʻjiza); the tutuq belgisi ``ʼ``
    everywhere else (маъно -> maʼno, санъат -> sanʼat). Not reversible: the
    Latin side has nothing to restore it from.

``ь``
    Read ``y`` before ``о`` (бульон -> bulyon, павильон -> pavilyon) and
    dropped everywhere else (альбом -> albom). Not reversible: bulyon comes
    back as булён.
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
    TS_LOANWORD_STEMS,
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


# --- case --------------------------------------------------------------------

# The case of one character, as _case_mask writes it.
_UPPER = "U"
_LOWER = "L"
_NO_CASE = "-"


def _case_mask(word: str) -> str:
    """The case of each character of ``word``: ``U``, ``L`` or ``-`` (none).

    ``ʻ``, ``ʼ`` and digits have no case. One exception to a letter's own
    case: an ``h`` after a capital ``S`` or ``C`` is a capital if the word has
    another capital besides that ``S`` or ``C``. ``Sh`` and ``Ch`` are one
    letter in ``latin_1995``, so ``MChJ`` and ``AQSh`` are all caps, while
    ``Shahar`` -- and ``Sh``, which is s + h in ``latin_2026`` -- has an
    initial capital.
    """
    mask = []
    capitals = 0
    for ch in word:
        if ch.lower() == ch.upper():
            mask.append(_NO_CASE)
        elif ch.isupper():
            mask.append(_UPPER)
            capitals += 1
        else:
            mask.append(_LOWER)
    if capitals > 1:
        for i in range(1, len(word)):
            if word[i] == "h" and word[i - 1] in "SC":
                mask[i] = _UPPER
    return "".join(mask)


def _unit_starts(mask: str) -> list:
    """Where the letter units of a word start: at 0, and at each capital that
    follows a lowercase letter. Characters without case between the two do not
    count, and stay with the letter before them (``Oʻz|MU``)."""
    starts = [0]
    previous = _NO_CASE
    for i, case in enumerate(mask):
        if case == _NO_CASE:
            continue
        if case == _UPPER and previous == _LOWER:
            starts.append(i)
        previous = case
    return starts


def _irregular(source: str) -> bool:
    """True if ``source``'s own case is not all lowercase, all caps or an
    initial capital: ``MChJ``, ``ShAHAR``, ``McDonald``."""
    cased = [ch.isupper() for ch in source if ch.lower() != ch.upper()]
    return any(cased[1:]) and not all(cased)


def _copy_case(source: str, result: str) -> str:
    """``result`` with the case of ``source``, position by position. A
    character without case takes the case of the letter before it, and is
    lowercase at the start."""
    out = []
    upper = False
    for ch, new in zip(source, result):
        if ch.lower() != ch.upper():
            upper = ch.isupper()
        out.append(new.upper() if upper else new.lower())
    return "".join(out)


def apply_case(source: str, result: str) -> str:
    """Restore ``source``'s casing onto ``result``.

    ``source`` is a word, or one letter unit of a word (see :func:`map_words`).
    So that a name in a sentence and the same name in a heading both come out
    right:

    * irregular case -- not all lowercase, not all caps and not an initial
      capital -- is copied letter by letter when ``result`` is as long as
      ``source``: ``MChJ`` and ``McDonald`` stay as they are in
      ``latin_1995``. A character without case takes the case of the letter
      before it;
    * otherwise, all caps in, all caps out -- ``ШОШИМОВА`` -> ``ŞOŞIMOVA``,
      never ``Şoşimova``;
    * initial capital in, initial capital out;
    * anything else lowercase.

    Length changes freely between input and output (``ш`` is one character,
    ``sh`` is two), so only output as long as the input takes the case
    position by position; any other output has it decided from the source and
    re-applied.

    Only letters that have case take part. ``ʻ`` and ``ʼ`` are letters to
    Unicode (category Lm) but have no case, so ``OʻZBEKISTON`` is all caps and
    gives ``ЎЗБЕКИСТОН``, not ``Ўзбекистон``. An ``h`` after a capital ``S``
    or ``C`` is a capital when the word has another capital: ``Sh`` and ``Ch``
    are one letter, so ``MChJ`` is all caps and gives ``MÇJ``, while
    ``Shahar`` gives ``Şahar``.
    """
    return _apply_case(source, result, _case_mask(source))


def _apply_case(source: str, result: str, mask: str) -> str:
    cased = mask.replace(_NO_CASE, "")
    if not cased or not result:
        return result
    if len(result) == len(source) and _irregular(source):
        return _copy_case(source, result)
    if len(cased) > 1 and _LOWER not in cased:
        return result.upper()
    if cased[0] == _UPPER:
        return result[0].upper() + result[1:]
    return result


def map_words(text: str, transform) -> str:
    """Apply ``transform`` to each word of ``text``, preserving everything else.

    ``transform`` receives the lowercased, mark-canonicalised word and returns
    its converted form; casing is restored afterwards with :func:`apply_case`.
    Case is kept per letter unit: a word is split where a lowercase letter is
    followed by a capital, and each unit is converted and cased on its own --
    ``ToshDU`` is ``Tosh`` + ``DU``, ``OʻzMU`` is ``Oʻz`` + ``MU``, so they give
    ``ToşDU`` and ``ÖzMU``. Digits, punctuation and whitespace pass through
    untouched. It sees words only: URLs, DOIs and the other protected spans
    are cut out by :func:`~akademtranslit.convert` before it gets here (see
    :mod:`akademtranslit.protect`).
    """

    def _one(match: re.Match[str]) -> str:
        source = match.group(0)
        lower = source.lower()
        if lower == source:
            return transform(canonicalize_marks(lower))
        mask = _case_mask(source)
        starts = _unit_starts(mask)
        if len(starts) == 1:
            return _apply_case(source, transform(canonicalize_marks(lower)), mask)
        ends = starts[1:] + [len(source)]
        return "".join(
            _apply_case(
                source[a:b], transform(canonicalize_marks(source[a:b].lower())), mask[a:b]
            )
            for a, b in zip(starts, ends)
        )

    return _WORD_RE.sub(_one, text)


# --- Cyrillic -> latin_1995 --------------------------------------------------

# For the ъ rule: the consonants it may follow, and the letters that begin with
# a y sound in Latin.
_CYRILLIC_CONSONANTS = frozenset("бвгджзйклмнпрстфхцчшщқғҳ")
_CYRILLIC_IOTATED = frozenset("еёюя")


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
        elif ch == "ъ" and (
            prev == "ў" or (prev in _CYRILLIC_CONSONANTS and nxt in _CYRILLIC_IOTATED)
        ):
            # The 1995 spelling writes no mark here: объект -> obyekt,
            # мўъжиза -> moʻjiza. Elsewhere ъ is the tutuq belgisi.
            continue
        elif ch == "ь" and nxt == "о":
            # ь before о is y: бульон -> bulyon. Elsewhere it is dropped.
            out.append("y")
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
    "gina", "kina", "yu", "u", "ku", "yoq", "mikan",  # particles that close a verb form
)

_TS_SUFFIX_RE = re.compile(
    "(?:" + "|".join(_TS_SUFFIXES) + ")(?:" + "|".join(_TS_FOLLOWERS) + ")*"
)

_VOWELS_AND_Y = LATIN_VOWELS | {"y"}

# The vowels after which a bare e is э: poeziya -> поэзия.
_VOWELS_BEFORE_E = frozenset("aeiou")


def _ts_splits(word: str, i: int) -> bool:
    """True if the ``ts`` at ``word[i]`` is т + с rather than the letter ц.

    Checked in order; the first that applies decides:

    0. The s opens ``sh`` or ``sʼh``: т + ш (adabiyotshunos -> адабиётшунос).
    1. Word-initial: ц (tsement, tsinga).
    2. ``i`` and then a vowel or ``y`` follow: ц (operatsiya, ratsion,
       patsiyent).
    3. A known loan the suffix check would misread: ц. Each is matched where
       the ts is, so inflected forms hold too (azitromitsinni, tablitsada).

       a. ``-mitsin`` and ``-rubitsin``, plus ``glitsin``, ``oksitotsin`` and
          ``rifampitsin`` (azitromitsin, doksorubitsin). Exact names and
          endings only: a general ``-itsin`` rule would also take bitsin and
          the other verbs in ``-t`` + ``-sin``, which are т + с.
       b. ``-floksatsin``, ``-leytsin`` and ``amikatsin`` (levofloksatsin,
          izoleytsin).
       c. ``aktsiz`` (excise). Only this stem: a general "k before ts" rule
          would also take kontaktsiz and effektsiz, which are т + с.
       d. A stem from :data:`~akademtranslit.tables.TS_LOANWORD_STEMS`, the
          ``-ица`` nouns (tablitsa, teplitsalar).

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
    if word.startswith("in", i + 2) and (
        word.endswith(("mi", "rubi"), 0, i) or word[:i] in ("gli", "oksito", "rifampi")
    ):
        return False
    if word.startswith("in", i + 2) and (
        word.endswith(("floksa", "ley"), 0, i) or word[:i] == "amika"
    ):
        return False
    if word[:i] == "ak":
        return False
    if word[:i + 2] in TS_LOANWORD_STEMS:
        return False
    return _TS_SUFFIX_RE.fullmatch(rest) is not None


def latin_1995_word_to_cyrillic(word: str) -> str:
    """Convert one lowercase ``latin_1995`` word to Cyrillic."""
    out: list[str] = []
    i = 0
    length = len(word)
    while i < length:
        # The e/ye rule outranks the table: ``ye`` is always е. A bare ``e`` is
        # э word-initially and after a vowel, except before v (Aliev ->
        # Алиев), and е everywhere else.
        if word.startswith("ye", i):
            out.append("е")
            i += 2
            continue
        if word[i] == "e":
            after_a_vowel = (
                i > 0 and word[i - 1] in _VOWELS_BEFORE_E and not word.startswith("v", i + 1)
            )
            out.append("э" if i == 0 or after_a_vowel else "е")
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


def latin_2026_canonical_word(word: str) -> str:
    """Write the draft glyphs in one lowercase word as ``ö``.

    Applies :data:`~akademtranslit.tables.LATIN_2026_INPUT_ALIASES`: ``ō`` and
    ``ǒ``, which drafts of the reform used for ``oʻ``. Run whenever the source
    or the target is ``latin_2026``, so the glyphs never reach 2026 output.
    """
    for source, target in LATIN_2026_INPUT_ALIASES:
        word = word.replace(source, target)
    return word


def latin_2026_word_to_1995(word: str) -> str:
    """Convert one lowercase ``latin_2026`` word to ``latin_1995``."""
    word = latin_2026_canonical_word(word)
    for source, target in LATIN_2026_TO_1995_STEPS:
        word = word.replace(source, target)
    return word
