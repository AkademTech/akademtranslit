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

import unicodedata

from .apostrophes import normalize_apostrophes
from .checks import migration_report, validate
from .collation import sort_key
from .detection import cyrillic_language, script_class
from .normalize import fold_cyrillic, is_cyrillic, normalize
from .protect import Protect, _settings, _spans, segments
from .rules import (
    _WORD_RE,
    CYRILLIC_WORD,
    LATIN_1995_WORD,
    LATIN_2026_WORD,
    O_FORM_WORD,
    PLAIN_WORD,
    SH_CH_WORD,
    convert_cyrillic_word,
    cyrillic_word_to_latin_1995,
    dates,
    is_roman_numeral,
    latin_1995_word_to_2026,
    latin_1995_word_to_cyrillic,
    latin_2026_canonical_word,
    latin_2026_word_to_1995,
    map_word,
    map_words,
    map_words_by,
    month_soft_sign,
    word_class,
)
from .scripts import fold_homoglyphs, homoglyph_spans, script_spans
from .tables import (
    APOSTROPHE_VARIANTS,
    ASCII_CAPITALS,
    ASCII_SCHEME,
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

__version__ = "0.3.2"

__all__ = [
    "CYRILLIC",
    "CYRILLIC_ALPHABET",
    "LATIN_1995",
    "LATIN_1995_ALPHABET",
    "LATIN_2026",
    "LATIN_2026_ALPHABET",
    "Protect",
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
    "fold_homoglyphs",
    "homoglyph_spans",
    "is_cyrillic",
    "migration_report",
    "normalize",
    "normalize_apostrophes",
    "script_class",
    "script_for_tag",
    "script_spans",
    "segments",
    "sort_key",
    "tag_for_script",
    "to_ascii",
    "to_cyrillic",
    "to_latin",
    "validate",
]

# Letters that exist only in latin_2026. One of them anywhere in the text is
# conclusive: no other Uzbek orthography uses them. The escapes are the other
# input forms of two of them (LATIN_2026_INPUT_ALIASES): of ö, o with macron
# and o with caron, U+014D, U+01D2, U+014C and U+01D1; of ş, s with comma
# below, U+0219 and U+0218.
_REFORM_LETTERS = frozenset("şçğöŞÇĞÖ" "\u014d\u01d2\u014c\u01d1" "\u0219\u0218")

# Every conversion is expressed as a chain of word-level steps. latin_1995 is
# the pivot -- it is the only orthography that shares a boundary with both of
# the others, so no pair needs a table of its own. The other input forms of ö
# and ş (LATIN_2026_INPUT_ALIASES) are read as those letters whenever the
# source or the target is latin_2026; a pair not listed (cyrillic or
# latin_1995 to itself) has no steps. Cyrillic is read with
# convert_cyrillic_word; normalize keeps cyrillic_word_to_latin_1995.
_PIPELINES: dict[tuple[str, str], tuple] = {
    (CYRILLIC, LATIN_1995): (convert_cyrillic_word,),
    (CYRILLIC, LATIN_2026): (
        convert_cyrillic_word,
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

    The text is read in NFC, as :func:`convert` reads it: ``O`` followed by
    U+0308 COMBINING DIAERESIS is ``Ö``.
    """
    text = unicodedata.normalize("NFC", text)
    if is_cyrillic(text):
        return CYRILLIC
    if any(ch in _REFORM_LETTERS for ch in text):
        return LATIN_2026
    return LATIN_1995


def _auto_sources(pieces: list, target: str) -> dict:
    """How ``source="auto"`` reads the words of ``pieces``, the text outside
    the protected spans: each word, as it stands, to its source orthography.

    A word that shows its orthography is read in it (see
    :func:`~akademtranslit.rules.word_class`): a Cyrillic letter, a 2026
    letter, ``oʻ`` or ``gʻ``; o with macron and o with caron are read as 2026.
    The others, with only ``sh`` or ``ch`` or with nothing, are read in the
    Latin orthography of the text: ``latin_2026`` if the words with a 2026
    letter outnumber those with ``oʻ``, ``gʻ``, ``sh`` or ``ch``, or match the
    ones with ``sh`` or ``ch`` when there is no ``oʻ`` or ``gʻ``; otherwise
    ``latin_1995``. Words with o with macron or o with caron are not counted.
    When the target is Cyrillic and the text is mostly Cyrillic -- at least
    one Cyrillic word, and no fewer than Latin ones -- they stay as they are.
    """
    classes = {}
    counts = dict.fromkeys(
        (CYRILLIC_WORD, LATIN_2026_WORD, LATIN_1995_WORD, O_FORM_WORD, SH_CH_WORD, PLAIN_WORD), 0
    )
    for piece in pieces:
        for word in _WORD_RE.findall(piece):
            kind = classes.get(word)
            if kind is None:
                kind = classes[word] = word_class(word)
            counts[kind] += 1
    cyrillic = counts.pop(CYRILLIC_WORD)
    mostly_cyrillic = cyrillic >= 1 and cyrillic >= sum(counts.values())
    new, old = counts[LATIN_2026_WORD], counts[LATIN_1995_WORD]
    either = old + counts[SH_CH_WORD]
    if new > 0 and (new > either or (new == either and old == 0)):
        latin = LATIN_2026
    else:
        latin = LATIN_1995
    other = CYRILLIC if target == CYRILLIC and mostly_cyrillic else latin
    by_class = {
        CYRILLIC_WORD: CYRILLIC,
        LATIN_2026_WORD: LATIN_2026,
        LATIN_1995_WORD: LATIN_1995,
        O_FORM_WORD: LATIN_2026,
        SH_CH_WORD: other,
        PLAIN_WORD: other,
    }
    return {word: by_class[kind] for word, kind in classes.items()}


def _steps(source: str, target: str):
    """The function that converts one lowercase word from ``source`` to
    ``target``: the steps of ``_PIPELINES``, in order."""
    steps = _PIPELINES.get((source, target), ())

    def _word(word: str) -> str:
        for step in steps:
            word = step(word)
        return word

    return _word


def convert(text: str, source: str = "auto", target: str = LATIN_2026, *, protect=True) -> str:
    """Convert ``text`` from one orthography to another.

    ``source`` may be ``"auto"`` (the default) to read each word in the
    orthography it shows (see below). Both ``source`` and ``target`` otherwise
    take one of the values in :data:`~akademtranslit.tables.SCRIPTS`, or a
    language tag for one of them
    (``uz-Cyrl``, ``uz-Latn-1995``, ``uz-Latn-2026``; see
    :mod:`akademtranslit.tags`).

    Digits, punctuation and whitespace pass through untouched, so mixed content
    survives intact:

    >>> convert("Ilmiy jurnal, 2026-yil, 12-son", target="latin_2026")
    'Ilmiy jurnal, 2026-yil, 12-son'

    The one exception is a date that changes script. Cyrillic writes no
    hyphen after the number of a year or of a day of the month, Latin writes
    one (see :func:`~akademtranslit.rules.dates`):

    >>> convert("1991-yilning 1-sentabri", target="cyrillic")
    '1991 йилнинг 1 сентябри'
    >>> convert("1956 йил 22 сентябрь", target="latin_2026")
    '1956-yil 22-sentabr'

    Within one script the separator is the author's and stays as it is:

    >>> convert("2026 yil", source="latin_1995", target="latin_2026")
    '2026 yil'

    URLs, e-mail addresses, DOIs, placeholders, markup, file paths and tokens
    such as ``pH`` and ``SpO2`` come out byte for byte (see
    :mod:`akademtranslit.protect`); with ``source="auto"`` only the rest of the
    text decides the orthography. ``protect`` is ``True`` (the default),
    ``False`` to convert everything, or a :class:`~akademtranslit.Protect`
    that names the kinds to keep:

    >>> convert("Manba: https://shahar.uz, doi:10.1234/shahar.2026", target="cyrillic")
    'Манба: https://shahar.uz, doi:10.1234/shahar.2026'
    >>> convert("https://shahar.uz", target="cyrillic", protect=False)
    'ҳттпс://шаҳар.уз'

    With ``source="auto"``, a word with a Cyrillic letter is read as
    Cyrillic, one with ``ş ç ğ ö`` as ``latin_2026`` and one with ``oʻ`` or
    ``gʻ`` as ``latin_1995``. The other words are read as ``latin_2026`` when
    the words with ``ş ç ğ ö`` outnumber those with ``oʻ``, ``gʻ``, ``sh`` or
    ``ch``, or, with no ``oʻ`` or ``gʻ`` in the text, equal them; as
    ``latin_1995`` otherwise. So a Latin word in Cyrillic text is converted
    when it shows its orthography, and one foreign ``ö`` does not make a 1995
    text 2026:

    >>> to_cyrillic("Тошкент ŞAHAR")
    'Тошкент ШАҲАР'
    >>> to_latin("Gödel teoremasi Toshkentda oʻqitiladi", variant="latin_1995")
    'Goʻdel teoremasi Toshkentda oʻqitiladi'

    In mostly Cyrillic text converted to Cyrillic, a Latin word that does not
    show its orthography (``Google``) stays as it is. :func:`detect_script`
    still reads the text as a whole.

    Converting to the orthography the text is already in is not a no-op: it
    canonicalises the apostrophe marks, so ``o'zbek``, ``o’zbek`` and ``oʻzbek``
    all come out as ``oʻzbek``. That makes the function idempotent and makes its
    output safe to use as a stored form.

    The text outside the protected spans is composed (Unicode NFC) before it
    is converted, so what is converted comes out in NFC, while the protected
    spans still come out byte for byte. A letter typed as a base letter and a
    combining mark is converted as that letter:

    >>> to_cyrillic("O" + chr(0x0308) + "zbekiston")  # O, U+0308 COMBINING DIAERESIS
    'Ўзбекистон'
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
    settings = _settings(protect)
    if not text:
        return text

    # Protected spans are cut out first and put back unchanged; only the text
    # between them is converted, and only it decides the orthography. It is
    # composed (NFC) first, so a letter typed as a base and a combining mark
    # (O and U+0308) is read as the one letter (Ö).
    pieces = [
        (text[a:b], kind) if kind is not None else (unicodedata.normalize("NFC", text[a:b]), None)
        for a, b, kind in _spans(text, settings)
    ]
    if source == "auto":
        sources = _auto_sources([piece for piece, kind in pieces if kind is None], target)
        source_of = sources.__getitem__
    else:

        def source_of(word: str) -> str:
            return source

    transforms = {script: _steps(script, target) for script in SCRIPTS}
    to_cyrillic = target == CYRILLIC

    def _word(match) -> str:
        word = match.group()
        script = source_of(word)
        if to_cyrillic and script != CYRILLIC:
            # The rules that need the whole word as it stands, and what follows it.
            end = match.end()
            if is_roman_numeral(word, match.string[end:end + 1]):
                return word
            return month_soft_sign(word, map_word(word, transforms[script]))
        return map_word(word, transforms[script])

    def _piece(piece: str) -> str:
        # map_word canonicalises the marks even when there are no steps, which
        # is what makes a same-script conversion a normalising pass rather
        # than a no-op. Then dates: the separator after the number of a year
        # or a day of the month, as the target writes it, before a word read
        # in the other script; crossed holds where those words start in out.
        out = []
        crossed = set()
        size = last = 0
        for match in _WORD_RE.finditer(piece):
            between = piece[last:match.start()]
            word = _word(match)
            if (source_of(match.group()) == CYRILLIC) != to_cyrillic:
                crossed.add(size + len(between))
            out += (between, word)
            size += len(between) + len(word)
            last = match.end()
        out.append(piece[last:])
        return dates("".join(out), target, crossed)

    return "".join(piece if kind is not None else _piece(piece) for piece, kind in pieces)


def to_latin(text: str, variant: str = LATIN_2026, *, protect=True) -> str:
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
    return convert(text, source="auto", target=variant, protect=protect)


def to_cyrillic(text: str, *, protect=True) -> str:
    """Convert ``text`` to Cyrillic from either Latin orthography.

    >>> to_cyrillic("Abu Rayhon Beruniy")
    'Абу Райҳон Беруний'
    >>> to_cyrillic("Qaşqadaryo")
    'Қашқадарё'
    """
    return convert(text, source="auto", target=CYRILLIC, protect=protect)


_NO_MARKS = str.maketrans("", "", "".join(APOSTROPHE_VARIANTS))
_ASCII_CAPITALS = {letter: forms for letter, *forms in ASCII_CAPITALS}


def _ascii_capitals(text: str) -> str:
    """Write capital ``Ş`` and ``Ç`` by the characters around them in ``text``
    (see :data:`~akademtranslit.tables.ASCII_CAPITALS`)."""
    if not any(letter in text for letter in _ASCII_CAPITALS):
        return text
    out = []
    for i, ch in enumerate(text):
        forms = _ASCII_CAPITALS.get(ch)
        if forms is None:
            out.append(ch)
            continue
        beside_a_capital = text[i - 1:i].isupper() or text[i + 1:i + 2].isupper()
        out.append(forms[0] if beside_a_capital else forms[1])
    return "".join(out)


def to_ascii(text: str) -> str:
    """Write ``text`` in ASCII, for names and logins.

    A project scheme, not a passport standard, and deterministic:

    1. :func:`to_latin` converts the text to ``latin_1995``, keeping protected
       spans as they are, so ``McDonald`` keeps its case.
    2. :data:`~akademtranslit.tables.ASCII_SCHEME` writes ``oʻ`` and ``gʻ`` as
       ``o`` and ``g``, and any ``ş ç ğ ö`` left in the text as ``sh ch g o``
       (``G O`` for ``Ğ Ö``). Capital ``Ş`` and ``Ç`` are ``SH`` and ``CH``
       when the character before or after is a capital, ``Sh`` and ``Ch``
       otherwise (:data:`~akademtranslit.tables.ASCII_CAPITALS`). The tutuq
       belgisi and the other apostrophe marks are removed.
    3. Other letters lose their accents (``é`` -> ``e``, by NFKD), and
       whatever is still not ASCII is removed.

    Case is kept; spaces, digits and ASCII punctuation stay.

    >>> to_ascii("Чўлпон")
    'Cholpon'
    >>> to_ascii("Gʻafur Gʻulom")
    'Gafur Gulom'
    >>> to_ascii("Isʼhoq José")
    'Ishoq Jose'
    >>> to_ascii("Тошкент ŞAHAR")
    'Toshkent SHAHAR'

    The table changes only in a major release.
    """
    text = to_latin(text, variant=LATIN_1995)
    if not text:
        return text
    for letter, ascii_form in ASCII_SCHEME:
        text = text.replace(letter, ascii_form)
    text = _ascii_capitals(text)
    text = unicodedata.normalize("NFKD", text.translate(_NO_MARKS))
    return "".join(ch for ch in text if ch.isascii())
