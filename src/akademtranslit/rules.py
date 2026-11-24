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

More rules look at the whole word, or at the text around it (0.3.2):

``ц`` at the end of a word
    Read ``s`` at the end of a word and where only Uzbek suffixes follow it
    (марганец -> marganes, шприц -> shpris, ненецлар -> neneslar, шприцни ->
    shprisni), whatever comes before it: :func:`convert_cyrillic_word`. Not
    reversible: marganes comes back as марганес.

Month names
    ``сентябр`` and ``октябр`` are read ``sentabr`` and ``oktabr``, with any
    suffix (сентябрда -> sentabrda): :func:`convert_cyrillic_word`. The other
    direction writes я again (sentabr, sentyabr -> сентябр), and a month name
    standing alone gets the ``ь`` the Latin side has nothing to restore it
    from (yanvar -> январь, iyun -> июнь); with a suffix it has none (yanvarda
    -> январда): :func:`month_soft_sign`.

Roman numerals
    A word that is a Roman numeral in capitals stays as it is when Latin is
    converted to Cyrillic (XIX asr -> XIX аср), unless it is one letter
    followed by a full stop, an initial (I. Boʻriyev -> И. Бўриев):
    :func:`is_roman_numeral`.

Dates
    Cyrillic writes no hyphen after the number of a year or of a day of the
    month (1956 йил 22 сентябрь, the 1956 rules), Latin writes one
    (1956-yil 22-sentabr): :func:`dates` writes the separator as the target
    does, after the words are converted.
"""

from __future__ import annotations

import re

from .tables import (
    APOSTROPHE_VARIANTS,
    CYRILLIC,
    CYRILLIC_FIRST,
    CYRILLIC_LAST,
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
    """Where the letter units of a word start: at 0, at each capital that
    follows a lowercase letter (``Tosh|DU``), and at each lowercase letter that
    follows two or more capitals in a row (``AQSh|da``, ``Tosh|DU|ga``; not
    ``Shahar``). Characters without case between the two do not count, and
    stay with the letter before them (``Oʻz|MU``)."""
    starts = [0]
    previous = _NO_CASE
    capitals = 0  # capitals in a row up to here
    for i, case in enumerate(mask):
        if case == _NO_CASE:
            continue
        if case == _UPPER and previous == _LOWER:
            starts.append(i)
        elif case == _LOWER and capitals >= 2:
            starts.append(i)
        capitals = capitals + 1 if case == _UPPER else 0
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
    or ``C`` is a capital when ``source`` has another capital: ``Sh`` and
    ``Ch`` are one letter, so ``MChJ`` is all caps and gives ``MÇJ``, while
    ``Shahar``, and the unit ``Sh`` of ``TerSh``, have an initial capital.
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
    followed by a capital, and where two or more capitals are followed by a
    lowercase letter, and each unit is converted and cased on its own --
    ``ToshDU`` is ``Tosh`` + ``DU``, ``OʻzMU`` is ``Oʻz`` + ``MU`` and
    ``AQShda`` is ``AQSh`` + ``da``, so they give ``ToşDU``, ``ÖzMU`` and
    ``AQŞda``. Digits, punctuation and whitespace pass through
    untouched. It sees words only: URLs, DOIs and the other protected spans
    are cut out by :func:`~akademtranslit.convert` before it gets here (see
    :mod:`akademtranslit.protect`).
    """

    return _WORD_RE.sub(lambda match: map_word(match.group(0), transform), text)


def map_words_by(text: str, transform_for) -> str:
    """:func:`map_words` with a transform chosen for each word.

    ``transform_for`` receives each word of ``text`` as it stands and returns
    the transform for it; :func:`~akademtranslit.convert` uses it to read each
    word in its own orthography when the source is ``"auto"``.
    """
    return _WORD_RE.sub(
        lambda match: map_word(match.group(0), transform_for(match.group(0))), text
    )


def map_word(source: str, transform) -> str:
    """Apply ``transform`` to one word, as :func:`map_words` does to each."""
    lower = source.lower()
    if lower == source:
        return transform(canonicalize_marks(lower))
    mask = _case_mask(source)
    starts = _unit_starts(mask)
    if len(starts) == 1:
        return _apply_case(source, transform(canonicalize_marks(lower)), mask)
    # Each unit is cased by its own letters: the h of Ter|Sh has no other
    # capital beside it in Sh.
    ends = starts[1:] + [len(source)]
    return "".join(
        apply_case(source[a:b], transform(canonicalize_marks(source[a:b].lower())))
        for a, b in zip(starts, ends)
    )


# --- the orthography a word shows ---------------------------------------------

# The classes of word_class.
CYRILLIC_WORD = "C"
LATIN_2026_WORD = "N"
LATIN_1995_WORD = "O"
O_FORM_WORD = "D"
SH_CH_WORD = "W"
PLAIN_WORD = "-"

# Letters that only latin_2026 has: ş ç ğ ö, and s with comma below (U+0219),
# an input form of ş.
_LATIN_2026_LETTERS = frozenset("şçğö" "\u0219")

# The input forms of ö: o with macron (U+014D) and o with caron (U+01D2).
_O_FORMS = frozenset("\u014d\u01d2")

_OI = "o" + TURNED_COMMA
_GI = "g" + TURNED_COMMA


def word_class(word: str) -> str:
    """Which orthography one word shows, as one of six classes.

    The word is lowercased and its marks canonicalised; the first class that
    applies is the answer:

    ``"C"``
        a Cyrillic letter (U+0400-U+052F);
    ``"N"``
        one of ``ş ç ğ ö``, or s with comma below: ``latin_2026``;
    ``"O"``
        ``oʻ`` or ``gʻ``: ``latin_1995``;
    ``"D"``
        o with macron or o with caron, input forms of ``ö``: ``latin_2026``,
        but foreign names have them too, so they say little about a text;
    ``"W"``
        ``sh`` or ``ch``, which both Latin orthographies write, as one letter
        in ``latin_1995`` and as two in ``latin_2026``;
    ``"-"``
        none of these: the word is written the same in both.
    """
    word = canonicalize_marks(word.lower())
    if any(CYRILLIC_FIRST <= ord(ch) <= CYRILLIC_LAST for ch in word):
        return CYRILLIC_WORD
    if any(ch in _LATIN_2026_LETTERS for ch in word):
        return LATIN_2026_WORD
    if _OI in word or _GI in word:
        return LATIN_1995_WORD
    if any(ch in _O_FORMS for ch in word):
        return O_FORM_WORD
    if "sh" in word or "ch" in word:
        return SH_CH_WORD
    return PLAIN_WORD


# --- Cyrillic -> latin_1995 --------------------------------------------------

# For the ъ rule: the consonants it may follow, and the letters that begin with
# a y sound in Latin.
_CYRILLIC_CONSONANTS = frozenset("бвгджзйклмнпрстфхцчшщқғҳ")
_CYRILLIC_IOTATED = frozenset("еёюя")

# The month names whose я latin_1995 writes as a, and where the я is:
# сентябр -> sentabr, октябр -> oktabr, as the Katta lugʻat writes them.
_CYRILLIC_MONTHS_WITH_A = (("сентябр", 4), ("октябр", 3))

# What may follow a ц that is still read as at the end of a word: nothing, or
# Uzbek suffixes only -- the plural with a possessive, then a case ending, each
# if it is there. Each begins with a consonant. The Katta lugʻat writes
# ненецлар as neneslar.
_FINAL_TS_SUFFIXES_RE = re.compile(
    "(?:лар(?:и|им|инг|имиз|ингиз)?)?(?:нинг|ни|га|да|дан|даги|гача)?"
)


def cyrillic_word_to_latin_1995(word: str) -> str:
    """Convert one lowercase Cyrillic word to ``latin_1995``, by the
    positional rules of the module docstring, as 0.3.1 had them.

    :func:`~akademtranslit.normalize` reads Cyrillic with it, and so does code
    that builds its own search key from it: its output does not change in a
    patch release. :func:`~akademtranslit.convert` uses
    :func:`convert_cyrillic_word`, which reads some words as wholes.
    """
    return _cyrillic_word_to_latin_1995(word, False)


def convert_cyrillic_word(word: str) -> str:
    """Convert one lowercase Cyrillic word to ``latin_1995``, as
    :func:`~akademtranslit.convert` does: as :func:`cyrillic_word_to_latin_1995`,
    except that

    * the month names ``сентябр`` and ``октябр``, with any suffix, are
      ``sentabr`` and ``oktabr`` (сентябрь -> sentabr, октябрнинг ->
      oktabrning);
    * a ``ц`` at the end of the word, or followed by Uzbek suffixes only
      (``лар`` with a possessive, then a case ending), is ``s`` (марганец ->
      marganes, ненецлар -> neneslar, шприцни -> shprisni; not
      боцман, плацдарм, лицей: botsman, platsdarm, litsey).
    """
    return _cyrillic_word_to_latin_1995(word, True)


def _cyrillic_word_to_latin_1995(word: str, whole: bool) -> str:
    """The two above: ``whole`` adds the rules for whole words."""
    a = -1
    if whole:
        for stem, at in _CYRILLIC_MONTHS_WITH_A:
            if word.startswith(stem):
                a = at
    out: list[str] = []
    for i, ch in enumerate(word):
        prev = word[i - 1] if i else ""
        nxt = word[i + 1] if i + 1 < len(word) else ""

        if i == a:
            # The я of сентябр, октябр: sentabr, oktabr.
            out.append("a")
        elif ch == "е":
            initial_or_after_vowel = i == 0 or prev in CYRILLIC_VOWELS or prev in "ъь"
            out.append("ye" if initial_or_after_vowel else "e")
        elif ch == "ц":
            if whole and _FINAL_TS_SUFFIXES_RE.fullmatch(word, i + 1):
                # At the end of the word, before Uzbek suffixes only: s
                # (марганец -> marganes, ненецлар -> neneslar).
                out.append("s")
                continue
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


# The month names whose a Cyrillic writes as я, and where the a is: sentabr
# -> сентябр, oktabr -> октябр. sentyabr and oktyabr have it already.
_LATIN_MONTHS_WITH_YA = (("sentabr", 4), ("oktabr", 3))


def latin_1995_word_to_cyrillic(word: str) -> str:
    """Convert one lowercase ``latin_1995`` word to Cyrillic.

    The month names ``sentabr`` and ``oktabr``, with any suffix, are
    ``сентябр`` and ``октябр``. The ``ь`` of a month name standing alone is
    added to the whole word by :func:`month_soft_sign`.
    """
    out: list[str] = []
    i = 0
    length = len(word)
    ya = -1
    for stem, at in _LATIN_MONTHS_WITH_YA:
        if word.startswith(stem):
            ya = at
    while i < length:
        if i == ya:
            # The a of sentabr, oktabr: сентябр, октябр.
            out.append("я")
            i += 1
            continue
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
    """Write the other input forms of ``ö`` and ``ş`` in one lowercase word as
    those letters.

    Applies :data:`~akademtranslit.tables.LATIN_2026_INPUT_ALIASES`: o with
    macron and o with caron are ``ö``, s with comma below is ``ş``. Run
    whenever the source or the target is ``latin_2026``, so these glyphs
    never reach 2026 output.
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


# --- whole words -----------------------------------------------------------------
#
# Rules that need the word as it was written, before map_word lowercases it and
# splits it into letter units. convert applies them.

# A Roman numeral, 1 to 3999, in capitals.
_ROMAN_NUMERAL_RE = re.compile(r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})")


def is_roman_numeral(word: str, after: str = "") -> bool:
    """True if ``word`` is a Roman numeral, which conversion from Latin to
    Cyrillic keeps as it is (XIX asr -> XIX аср, Pyotr I -> Пётр I).

    ``word`` is a word as it stands in the text and ``after`` the character
    that follows it, or ``""``. The word must be only the capitals
    ``I V X L C D M`` and a well-formed numeral (``XIX``, ``IV``, ``MMXXVI``;
    not ``IIII`` or ``Xix``). One letter followed by a full stop is an initial,
    not a numeral: ``I. Boʻriyev`` -> ``И. Бўриев``. Known limits: an Uzbek word
    in capitals that is also a numeral stays Latin (``MIX``), and ``Pyotr I.``
    at the end of a sentence is read as an initial.
    """
    if not word or _ROMAN_NUMERAL_RE.fullmatch(word) is None:
        return False
    return len(word) > 1 or after != "."


# The month names that Cyrillic writes with ь when they stand alone (январь,
# сентябрь); with a suffix they have none (январда, сентябрда). mart, may and
# avgust have none.
_SOFT_SIGN_MONTHS = frozenset((
    "yanvar", "fevral", "aprel", "iyun", "iyul",
    "sentabr", "sentyabr", "oktabr", "oktyabr", "noyabr", "dekabr",
))


def month_soft_sign(word: str, cyrillic: str) -> str:
    """``cyrillic``, the Cyrillic of the Latin ``word``, with the ``ь`` of a
    month name that stands alone: yanvar -> январь, SENTABR -> СЕНТЯБРЬ.

    ``word`` is the word as it stands in the text. Only a whole word that is a
    month name gets the ``ь``: with a suffix it has none (yanvarda ->
    январда, SENTABRda -> СЕНТЯБРда), and ``mart``, ``may`` and ``avgust``
    have none. It takes the case of the letter before it.
    """
    if word.lower() not in _SOFT_SIGN_MONTHS:
        return cyrillic
    return cyrillic + ("Ь" if cyrillic[-1:].isupper() else "ь")


# --- dates -------------------------------------------------------------------------

# A number with no letter or digit before it, and the one hyphen (U+002D, or
# U+2011 NON-BREAKING HYPHEN) or the one space (U+0020, or U+00A0 NO-BREAK
# SPACE) after it. [^\W_] is a letter or a digit.
_NUMBER_HYPHEN_RE = re.compile(r"(?<![^\W_])([0-9]+)([-‑])")
_NUMBER_SPACE_RE = re.compile(r"(?<![^\W_])([0-9]+)([  ])")

# The days of a month as they are written: 1 to 31, without a leading zero.
_DAYS = frozenset(str(day) for day in range(1, 32))

# A month name, lowercase, with the possessive -i and a case ending, each if
# it is there. A closed list, not any letters: 3 marta (three times), 5-martaba,
# 2-maydon are not dates. The Latin side has both spellings of sentabr and
# oktabr, which latin_1995 <-> latin_2026 keeps, and gacha in both alphabets.
_CYRILLIC_MONTH_RE = re.compile(
    "(?:январ|феврал|март|апрел|май|июн|июл|август|сентябр|октябр|ноябр|декабр)ь?"
    "и?(?:нинг|ни|га|да|дан|даги|гача)?"
)
_LATIN_MONTH_RE = re.compile(
    "(?:yanvar|fevral|mart|aprel|may|iyun|iyul|avgust|sentabr|sentyabr|oktabr|oktyabr|noyabr|dekabr)"
    "i?(?:ning|ni|ga|da|dan|dagi|gacha|gaça)?"
)


def dates(text: str, target: str) -> str:
    """``text``, converted to ``target``, with the separator after the number
    of a year or of a day of the month as ``target`` writes it.

    Cyrillic writes no hyphen there (the 1956 spelling rules, paragraph 47):
    ``1956 йил 22 сентябрь``. Latin writes one (Resolution No. 339 of 1995,
    rule 56): ``1991-yil 1-sentabr``. Other ordinals keep the hyphen in both:
    ``5-sinf``, ``39-son``, ``60-yillar``.

    A number counts when no letter or digit comes before it and one hyphen or
    one space comes after it, and then:

    * to Cyrillic, ``-`` becomes a space and U+2011 NON-BREAKING HYPHEN
      becomes U+00A0 NO-BREAK SPACE, after a number of three or four digits
      (no leading zero) followed by a word that begins with ``йил``, or after
      a day, 1 to 31, followed by a month name;
    * to ``latin_1995`` and ``latin_2026``, a space becomes ``-`` and U+00A0
      becomes U+2011, after a year from 1000 to 2099 followed by a word that
      begins with ``yil`` -- a smaller number is a count, ``5 yil`` -- or
      after a day followed by a month name.

    A month name is one of the twelve, with ``ь``, the possessive ``-i`` and
    a case ending (``нинг ни га да дан даги гача``), each if it is there; the
    word is compared in lowercase. Known limit: ``2000 йил давомида`` (for 2000
    years) is read as a year and becomes ``2000-yil davomida``.
    """
    if target == CYRILLIC:
        return _NUMBER_HYPHEN_RE.sub(_cyrillic_date, text)
    return _NUMBER_SPACE_RE.sub(_latin_date, text)


def _word_after(match) -> str:
    """The word right after ``match``, lowercase, or ``""``."""
    word = _WORD_RE.match(match.string, match.end())
    return word.group().lower() if word else ""


def _cyrillic_date(match) -> str:
    number, word = match.group(1), _word_after(match)
    year = 3 <= len(number) <= 4 and number[0] != "0" and word.startswith("йил")
    day = number in _DAYS and _CYRILLIC_MONTH_RE.fullmatch(word) is not None
    if not (year or day):
        return match.group()
    return number + (" " if match.group(2) == "-" else " ")


def _latin_date(match) -> str:
    number, word = match.group(1), _word_after(match)
    year = len(number) == 4 and 1000 <= int(number) <= 2099 and word.startswith("yil")
    day = number in _DAYS and _LATIN_MONTH_RE.fullmatch(word) is not None
    if not (year or day):
        return match.group()
    return number + ("-" if match.group(2) == " " else "‑")
