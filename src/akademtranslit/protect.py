"""Protected spans: the parts of a text that conversion leaves alone.

A URL, an e-mail address, a DOI, a placeholder in a message template, a piece
of markup, a file path, a name the caller gives and a mixed-case or
alphanumeric token such as ``pH`` or ``SpO2`` are not Uzbek words, and
converting them breaks them. :func:`~akademtranslit.convert`,
:func:`~akademtranslit.to_latin` and :func:`~akademtranslit.to_cyrillic` split
the text into such spans and the rest with :func:`segments`, convert the rest
and put the spans back byte for byte. :class:`Protect` says which kinds to
look for.

>>> from akademtranslit import segments
>>> segments("Batafsil: https://shahar.uz, pH 7,4")
[('Batafsil: ', None), ('https://shahar.uz', 'url'), (', ', None), ('pH', 'token'), (' 7,4', None)]

The kinds:

``url``
    Starts with ``http://``, ``https://``, ``ftp://`` or ``www.`` (in any
    case) and runs to the next whitespace. A bare domain (``gazeta.uz``,
    ``kun.uz/oz/...``) counts only with one of the endings ``uz com org net
    ru info edu gov io`` and not right after a letter, a digit or ``@``.
    Trailing ``. , ; : ! ? ) » " '`` are left out, except a ``)`` that closes
    a ``(`` inside the URL.
``email``
    ``local@domain.tld``, the local part made of ``A-Z a-z 0-9 . _ % + -``,
    with ``mailto:`` in front if it is there.
``doi``
    ``10.``, four to nine digits, ``/`` and everything up to the next
    whitespace, with ``doi:`` in front if it is there (no space after the
    colon). Trailing punctuation as for a URL. A DOI inside a URL
    (``https://doi.org/...``) is part of the URL.
``markup``
    A tag -- ``<`` followed by a letter, ``/`` or ``!``, up to its ``>``, with
    quoted attribute values -- an HTML comment and an entity (``&amp;``,
    ``&#123;``, ``&#x1F;``). Text between tags is converted.
``placeholder``
    An ICU MessageFormat argument (``{name}``, ``{0}``, ``{n, number}``,
    ``{d, date, short}``), found by matching braces, not by a regular
    expression. In ``plural``, ``select`` and ``selectordinal`` the message
    texts inside the braces are converted; the argument name, the keywords,
    the selectors and ``#`` in a plural are protected. Arguments nest. A
    ``{`` that does not open a whole argument is an ordinary character. Also
    printf directives (``%s``, ``%d``, ``%1$s``, ``%(name)s``) not right after
    a letter or digit, so ``50%dan`` stays text, and ``{{ ... }}``.
``path``
    Starts with ``/``, ``./``, ``../``, ``~/`` or a drive such as ``C:\\`` at
    the start of the text or after whitespace, an opening bracket or a quote,
    and runs to the next whitespace (trailing punctuation as for a URL); or a
    file name with one of a fixed list of extensions (``hisobot.docx``).
    ``kirill/lotin`` is not a path.
``term``
    Each of :attr:`Protect.terms`, exactly, as a whole word.
``token``
    A word of ASCII letters and digits, with apostrophes inside, that has no
    ``o`` or ``g`` followed by an apostrophe (that would make it Uzbek) and
    either has both a letter and a digit (``SpO2``, ``B12``, ``3D``) or has a
    lowercase letter followed by a capital (``pH``, ``iPhone``,
    ``McDonald``). A capital ``S`` or ``C`` with ``h`` counts as one capital,
    so ``MChJ`` and ``AQSh`` are converted. Two shapes are not tokens and are
    converted: digits followed by lowercase letters only (``10ta``,
    ``2026yil``, ``100mg``), and an Uzbek abbreviation -- a capital, one to
    four lowercase letters and two or more capitals (``ToshDU``, ``SamDU``,
    ``ToshPTI``; but ``ChatGPT``, ``PhD`` and ``AkademID`` are tokens). A word
    with a letter from another alphabet is never a token.

The text is scanned as it is, without Unicode normalization. Where spans
overlap, the one that starts first wins; of two that start together, the
longer; of two that are also as long, the kind listed first above. Adjacent
pieces of one kind are joined.
"""

from __future__ import annotations

import re

from .tables import APOSTROPHE_VARIANTS

URL = "url"
EMAIL = "email"
DOI = "doi"
MARKUP = "markup"
PLACEHOLDER = "placeholder"
PATH = "path"
TERM = "term"
TOKEN = "token"

#: The kinds of span, in order of precedence.
KINDS = (URL, EMAIL, DOI, MARKUP, PLACEHOLDER, PATH, TERM, TOKEN)

_RANK = {kind: rank for rank, kind in enumerate(KINDS)}

# --- Protect -------------------------------------------------------------------

_FLAGS = ("urls", "emails", "dois", "placeholders", "markup", "paths", "tokens")


class Protect:
    """Which spans :func:`segments` and the conversion functions protect.

    Every kind is on by default; pass ``False`` to turn one off. ``terms`` is a
    sequence of strings to keep as they are, such as product or company
    names: each is matched exactly, case included, and only as a whole word.
    :attr:`Protect.NONE` protects nothing. The arguments are keywords only.

    >>> Protect(tokens=False, terms=("AslMatn",))
    Protect(tokens=False, terms=('AslMatn',))

    Immutable, comparable and hashable.
    """

    __slots__ = _FLAGS + ("terms", "_terms_re")

    def __init__(
        self,
        *,
        urls=True,
        emails=True,
        dois=True,
        placeholders=True,
        markup=True,
        paths=True,
        tokens=True,
        terms=(),
    ):
        if isinstance(terms, str):
            raise TypeError("terms takes a sequence of strings, not one str")
        terms = tuple(terms)
        for term in terms:
            if not isinstance(term, str):
                raise TypeError(f"a term must be a str, not {type(term).__name__}")
            if not term:
                raise ValueError("a term must not be empty")
        flags = (urls, emails, dois, placeholders, markup, paths, tokens)
        for name, value in zip(_FLAGS, flags):
            object.__setattr__(self, name, bool(value))
        object.__setattr__(self, "terms", terms)
        object.__setattr__(self, "_terms_re", _terms_pattern(terms))

    def __setattr__(self, name, value):
        raise AttributeError(f"Protect is immutable; cannot set {name!r}")

    def __delattr__(self, name):
        raise AttributeError(f"Protect is immutable; cannot delete {name!r}")

    def _key(self) -> tuple:
        return tuple(getattr(self, name) for name in _FLAGS) + (self.terms,)

    def __eq__(self, other):
        if not isinstance(other, Protect):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self):
        return hash(self._key())

    def __repr__(self):
        parts = [f"{name}=False" for name in _FLAGS if not getattr(self, name)]
        if self.terms:
            parts.append(f"terms={self.terms!r}")
        return f"Protect({', '.join(parts)})"

    def __reduce__(self):
        # The default would restore the attributes with setattr, which is refused.
        return (_rebuild, self._key())


def _rebuild(urls, emails, dois, placeholders, markup, paths, tokens, terms):
    return Protect(
        urls=urls,
        emails=emails,
        dois=dois,
        placeholders=placeholders,
        markup=markup,
        paths=paths,
        tokens=tokens,
        terms=terms,
    )


def _settings(protect) -> Protect:
    """The :class:`Protect` for a ``protect`` argument: True, False or a Protect."""
    if protect is True:
        return _DEFAULT
    if protect is False:
        return Protect.NONE
    if isinstance(protect, Protect):
        return protect
    raise ValueError(f"protect must be True, False or a Protect, not {protect!r}")


# --- segments ------------------------------------------------------------------


def segments(text: str, protect=True) -> list:
    """Split ``text`` into protected spans and the text between them.

    Returns a list of ``(piece, kind)`` pairs. Joined, the pieces give
    ``text`` back exactly. ``kind`` is ``None`` for text that the conversion
    functions convert, and otherwise one of ``"url"``, ``"email"``, ``"doi"``,
    ``"markup"``, ``"placeholder"``, ``"path"``, ``"term"`` and ``"token"``
    (see the module documentation for what each covers). Neighbouring pieces
    always differ in kind, and empty text gives ``[]``.

    ``protect`` is ``True`` (every kind, the default), ``False`` (none) or a
    :class:`Protect`; anything else raises :class:`ValueError`.

    >>> pieces = segments("{n, plural, one {# shahar} other {# shahar}}")
    >>> pieces  # doctest: +NORMALIZE_WHITESPACE
    [('{n, plural, one {#', 'placeholder'), (' shahar', None),
     ('} other {#', 'placeholder'), (' shahar', None), ('}}', 'placeholder')]
    >>> segments("AslMatn va shahar", Protect(terms=("AslMatn",)))
    [('AslMatn', 'term'), (' va shahar', None)]
    >>> segments("AslMatn va shahar", protect=False)
    [('AslMatn va shahar', None)]
    """
    settings = _settings(protect)
    if not text:
        return []
    return [(text[start:stop], kind) for start, stop, kind in _spans(text, settings)]


def _spans(text: str, settings: Protect) -> list:
    """``(start, stop, kind)`` for each piece of ``text``, covering all of it."""
    finders = _finders(settings)
    if not finders:
        return [(0, len(text), None)]
    pieces: list = []
    _Scanner(text, finders).scan(0, len(text), pieces)
    merged: list = []
    for start, stop, kind in pieces:
        if start == stop:
            continue
        if merged and merged[-1][2] == kind:
            merged[-1] = (merged[-1][0], stop, kind)
        else:
            merged.append((start, stop, kind))
    return merged


class _Scanner:
    """One pass over one text: finds the spans and remembers the braces."""

    __slots__ = ("text", "finders", "_closing", "_arguments")

    def __init__(self, text: str, finders: list):
        self.text = text
        self.finders = finders
        self._closing = None
        self._arguments: dict = {}

    def scan(self, start: int, end: int, out: list) -> None:
        """Append the pieces of ``text[start:end]`` to ``out``.

        Each finder gives the first span it sees at or after a position. Its
        answer is kept until the scan passes its start, so every finder walks
        the text once.
        """
        found: list = [None] * len(self.finders)
        pos = start
        while pos < end:
            best = None
            for i, find in enumerate(self.finders):
                match = found[i]
                if match is _NOTHING:
                    continue
                if match is None or match[0] < pos:
                    match = find(self, pos, end) or _NOTHING
                    found[i] = match
                    if match is _NOTHING:
                        continue
                if best is None or _better(match, best):
                    best = match
            if best is None:
                break
            begin, stop, kind, inner = best
            if begin > pos:
                out.append((pos, begin, None))
            if inner is None:
                out.append((begin, stop, kind))
            else:
                for a, b, piece_kind in inner:
                    if piece_kind is None:
                        self.scan(a, b, out)
                    else:
                        out.append((a, b, piece_kind))
            pos = stop
        if pos < end:
            out.append((pos, end, None))

    def closing(self, i: int):
        """Index of the ``}`` that closes the ``{`` at ``i``, or ``None``."""
        if self._closing is None:
            closing: dict = {}
            stack: list = []
            for match in _BRACE_RE.finditer(self.text):
                if match.group() == "{":
                    stack.append(match.start())
                elif stack:
                    closing[stack.pop()] = match.start()
            self._closing = closing
        return self._closing.get(i)

    def argument(self, i: int, end: int, plural: bool, depth: int):
        """The ICU argument whose ``{`` is at ``i``: ``(stop, pieces)`` or ``None``.

        ``pieces`` is ``None`` when the whole argument is protected, and
        otherwise lists its protected syntax and its message texts.
        """
        key = (i, end, plural)
        if key not in self._arguments:
            if depth > _MAX_DEPTH:
                return None
            self._arguments[key] = self._argument(i, end, plural, depth)
        return self._arguments[key]

    def _argument(self, i: int, end: int, plural: bool, depth: int):
        text = self.text
        close = self.closing(i)
        if close is None or close >= end:
            return None
        m = _ICU_NAME_RE.match(text, i + 1, close)
        if m is None:
            return None
        j = m.end()
        if j == close:
            return close + 1, None
        if text[j] != ",":
            return None
        m = _ICU_TYPE_RE.match(text, j + 1, close)
        if m is None:
            return None
        arg_type = m.group(1).lower()
        j = m.end()
        if arg_type in _ICU_SIMPLE_TYPES:
            if j == close or text[j] == ",":
                return close + 1, None
            return None
        if arg_type not in _ICU_PLURAL_TYPES and arg_type != _ICU_SELECT:
            return None
        if j == close or text[j] != ",":
            return None
        j += 1
        if arg_type in _ICU_PLURAL_TYPES:
            plural = True
            m = _ICU_OFFSET_RE.match(text, j, close)
            if m is not None:
                j = m.end()
        pieces: list = []
        syntax = i
        while True:
            m = _ICU_SELECTOR_RE.match(text, j, close)
            if m is None or m.end() == close or text[m.end()] != "{":
                break
            j = m.end()
            pieces.append((syntax, j + 1, PLACEHOLDER))
            message = self._message(j + 1, close, plural, depth)
            if message is None:
                return None
            message_close, message_pieces = message
            pieces.extend(message_pieces)
            syntax = message_close
            j = message_close + 1
        if not pieces or _SPACE_RE.match(text, j, close).end() != close:
            return None
        pieces.append((syntax, close + 1, PLACEHOLDER))
        return close + 1, pieces

    def _message(self, i: int, end: int, plural: bool, depth: int):
        """The message text from ``i`` to its ``}``: ``(close, pieces)`` or ``None``."""
        text = self.text
        pieces: list = []
        start = k = i
        while True:
            m = _MESSAGE_SYNTAX_RE.search(text, k, end)
            if m is None:
                return None
            k = m.start()
            if text[k] == "}":
                pieces.append((start, k, None))
                return k, pieces
            if text[k] == "#":
                if plural:
                    pieces.append((start, k, None))
                    pieces.append((k, k + 1, PLACEHOLDER))
                    start = k + 1
                k += 1
                continue
            nested = self.argument(k, end, plural, depth + 1)
            if nested is None:
                return None
            stop, nested_pieces = nested
            pieces.append((start, k, None))
            pieces.extend(nested_pieces if nested_pieces is not None else [(k, stop, PLACEHOLDER)])
            start = k = stop


_NOTHING = (-1, -1, None, None)  # a finder that has nothing more to find


def _better(a: tuple, b: tuple) -> bool:
    """Whether span ``a`` wins over span ``b``: first, then longest, then by kind."""
    if a[0] != b[0]:
        return a[0] < b[0]
    if a[1] != b[1]:
        return a[1] > b[1]
    return _RANK[a[2]] < _RANK[b[2]]


# --- the finders -----------------------------------------------------------------
#
# Each takes the scanner, a start and an end, and returns the first span it
# finds in text[start:end] as (start, stop, kind, inner), or None. inner is None
# unless the span has pieces of its own (an ICU plural or select).

# A letter or digit, not counting the three apostrophe marks that Unicode
# calls letters (U+02B9, U+02BB, U+02BC).
_LETTER_MARKS = "".join(mark for mark in APOSTROPHE_VARIANTS if mark.isalpha())
_L = "[^\\W_" + re.escape(_LETTER_MARKS) + "]"
_MARK = "[" + re.escape("".join(APOSTROPHE_VARIANTS)) + "]"

# Left out at the end of a URL, a DOI or a path.
_TRAILING = frozenset(".,;:!?)»\"'")


def _trim(text: str, start: int, stop: int) -> int:
    """``stop`` moved back past trailing punctuation, but not before ``start``.

    A ``)`` stays if the span has at least as many ``(`` as ``)``.
    """
    while stop > start and text[stop - 1] in _TRAILING:
        if text[stop - 1] == ")" and text.count("(", start, stop) >= text.count(")", start, stop):
            break
        stop -= 1
    return stop


def _trimmed(pattern):
    """A finder for ``pattern`` that trims each match; its group ``tail`` must
    not be trimmed away."""

    def find(scanner, pos, end):
        text = scanner.text
        while True:
            m = pattern.search(text, pos, end)
            if m is None:
                return None
            stop = _trim(text, m.start("tail"), m.end())
            if stop > m.start("tail"):
                return (m.start(), stop, pattern.kind, None)
            pos = m.start() + 1

    return find


class _Pattern:
    """A compiled pattern with the kind of span it finds."""

    __slots__ = ("regex", "kind")

    def __init__(self, source: str, kind: str, flags: int = 0):
        self.regex = re.compile(source, flags)
        self.kind = kind

    def search(self, text, pos, end):
        return self.regex.search(text, pos, end)


def _plain(pattern):
    """A finder for ``pattern``: its first match is the span."""

    def find(scanner, pos, end):
        m = pattern.search(scanner.text, pos, end)
        return None if m is None else (m.start(), m.end(), pattern.kind, None)

    return find


def _needs(literal: str, finder):
    """``finder``, skipped when ``literal``, which every match contains, is absent."""

    def find(scanner, pos, end):
        if scanner.text.find(literal, pos, end) == -1:
            return None
        return finder(scanner, pos, end)

    return find


_DOMAIN_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"

_SCHEME_URL = _Pattern(r"(?<!\w)(?:(?:https?|ftp)://|www\.)(?P<tail>\S+)", URL, re.IGNORECASE)

_BARE_DOMAIN = _Pattern(
    r"(?<![\w@])(?P<tail>"
    + _DOMAIN_LABEL
    + r"(?:\."
    + _DOMAIN_LABEL
    + r")*\.(?:uz|com|org|net|ru|info|edu|gov|io)(?![\w-])(?:/\S*)?)",
    URL,
    re.IGNORECASE,
)

_EMAIL = _Pattern(
    r"(?:(?i:mailto):)?(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@"
    + _DOMAIN_LABEL
    + r"(?:\."
    + _DOMAIN_LABEL
    + r")*\.[A-Za-z]{2,63}(?![\w-])",
    EMAIL,
)

_DOI = _Pattern(r"(?:(?i:doi):)?(?<![\w.])10\.[0-9]{4,9}/(?P<tail>\S+)", DOI)

_TAG = _Pattern(
    r"<[A-Za-z/!](?:[^<>\"']|\"[^\"<]*\"|'[^'<]*')*>"  # quoted values may hold >
    r"|<[A-Za-z/!][^<>]*>"  # an unmatched quote: up to the first >
    r"|&(?:[A-Za-z][A-Za-z0-9]{1,31}|#[0-9]{1,7}|#[xX][0-9A-Fa-f]{1,6});",
    MARKUP,
)

_PRINTF = _Pattern(
    r"(?<![\w%])%(?:[0-9]+\$)?(?:\([^()\s]+\))?[-+#0]*(?:[0-9]+|\*)?(?:\.(?:[0-9]+|\*))?"
    r"(?:hh|h|ll|l|L|q|j|z|t)?[diouxXeEfFgGcrsaAp]",
    PLACEHOLDER,
)

_PATH = _Pattern(
    r"(?<![^\s(\[{\"'«“‘„])(?:\.{1,2}/|~/|/|[A-Za-z]:\\)(?P<tail>\S+)",
    PATH,
)

_FILE_NAME = _Pattern(
    r"(?<![\w.-])[\w.-]+\.(?:docx|doc|pdf|txt|xlsx|xls|pptx|csv|json|xml|html|md|py|js|zip|png"
    r"|jpg|jpeg|odt)(?!\w)",
    PATH,
    re.IGNORECASE,
)

# A run of letters and digits, joined by apostrophes, with a final apostrophe
# after o or g -- the same shape as a word in rules._WORD_RE. The lookahead
# skips, inside the regular expression engine, every run without a digit or a
# lowercase letter before a capital: most words, and none of them a token.
_CHUNK_RE = re.compile(
    "(?<!" + _L + ")"
    + "(?=(?:" + _L + "|" + _MARK + ")*?(?:[0-9]|[a-z][A-Z]))"
    + _L + "+(?:" + _MARK + _L + "+)*(?:(?<=[oOgG])" + _MARK + ")?(?!" + _L + ")"
)
_ASCII_CHUNK_RE = re.compile("[A-Za-z0-9" + re.escape("".join(APOSTROPHE_VARIANTS)) + "]+")
_UZBEK_RE = re.compile("[oOgG]" + _MARK)
_DIGIT_RE = re.compile("[0-9]")
_LETTER_RE = re.compile("[A-Za-z]")
_LOWER_THEN_UPPER_RE = re.compile("[a-z][A-Z]")
_H_OF_SH_CH_RE = re.compile("(?<=[SC])h")
_NUMBER_WITH_SUFFIX_RE = re.compile("[0-9]+[a-z]+")
_UZBEK_ABBREVIATION_RE = re.compile("[A-Z][a-z]{1,4}[A-Z]{2,}")

_BRACE_RE = re.compile("[{}]")
_MESSAGE_SYNTAX_RE = re.compile("[{}#]")
_SPACE_RE = re.compile(r"\s*")
_ICU_NAME_RE = re.compile(r"\s*\w+\s*")
_ICU_TYPE_RE = re.compile(r"\s*([A-Za-z]+)\s*")
_ICU_OFFSET_RE = re.compile(r"\s*offset\s*:\s*-?[0-9]+")
_ICU_SELECTOR_RE = re.compile(r"\s*(?:=-?[0-9]+(?:\.[0-9]+)?|\w+)\s*")
_ICU_SIMPLE_TYPES = frozenset(("number", "date", "time", "spellout", "ordinal", "duration"))
_ICU_PLURAL_TYPES = frozenset(("plural", "selectordinal"))
_ICU_SELECT = "select"
_MAX_DEPTH = 32


def _find_icu(scanner, pos, end):
    text = scanner.text
    i = text.find("{", pos, end)
    while i != -1:
        argument = scanner.argument(i, end, False, 0)
        if argument is not None:
            stop, pieces = argument
            return (i, stop, PLACEHOLDER, pieces)
        i = text.find("{", i + 1, end)
    return None


def _find_double_braces(scanner, pos, end):
    text = scanner.text
    i = text.find("{{", pos, end)
    if i == -1:
        return None
    close = text.find("}}", i + 2, end)
    if close == -1:
        return None
    return (i, close + 2, PLACEHOLDER, None)


def _find_comment(scanner, pos, end):
    text = scanner.text
    i = text.find("<!--", pos, end)
    if i == -1:
        return None
    close = text.find("-->", i + 4, end)
    if close == -1:
        return None
    return (i, close + 3, MARKUP, None)


def _is_token(chunk: str) -> bool:
    if _ASCII_CHUNK_RE.fullmatch(chunk) is None or _UZBEK_RE.search(chunk):
        return False
    if _NUMBER_WITH_SUFFIX_RE.fullmatch(chunk):
        return False  # a number with a suffix or a unit: 10ta, 2026yil, 100mg
    if _DIGIT_RE.search(chunk) and _LETTER_RE.search(chunk):
        return True
    # Sh and Ch after a capital are one capital letter: MChJ, AQSh.
    chunk = _H_OF_SH_CH_RE.sub("H", chunk)
    if _UZBEK_ABBREVIATION_RE.fullmatch(chunk):
        return False  # an Uzbek abbreviation: ToshDU, SamDU, ToshPTI
    return _LOWER_THEN_UPPER_RE.search(chunk) is not None


def _find_token(scanner, pos, end):
    text = scanner.text
    while True:
        m = _CHUNK_RE.search(text, pos, end)
        if m is None:
            return None
        if _is_token(m.group()):
            return (m.start(), m.end(), TOKEN, None)
        pos = m.end()


def _terms_pattern(terms: tuple):
    if not terms:
        return None
    longest_first = sorted(set(terms), key=lambda term: (-len(term), term))
    alternatives = "|".join(re.escape(term) for term in longest_first)
    return _Pattern("(?<!" + _L + ")(?:" + alternatives + ")(?!" + _L + ")", TERM)


_URL_FINDERS = (_trimmed(_SCHEME_URL), _trimmed(_BARE_DOMAIN))
_EMAIL_FINDERS = (_needs("@", _plain(_EMAIL)),)
_DOI_FINDERS = (_needs("10.", _trimmed(_DOI)),)
_MARKUP_FINDERS = (_plain(_TAG), _find_comment)
_PLACEHOLDER_FINDERS = (_find_icu, _find_double_braces, _needs("%", _plain(_PRINTF)))
_PATH_FINDERS = (_trimmed(_PATH), _plain(_FILE_NAME))
_TOKEN_FINDERS = (_find_token,)


def _finders(settings: Protect) -> list:
    finders: list = []
    if settings.urls:
        finders.extend(_URL_FINDERS)
    if settings.emails:
        finders.extend(_EMAIL_FINDERS)
    if settings.dois:
        finders.extend(_DOI_FINDERS)
    if settings.markup:
        finders.extend(_MARKUP_FINDERS)
    if settings.placeholders:
        finders.extend(_PLACEHOLDER_FINDERS)
    if settings.paths:
        finders.extend(_PATH_FINDERS)
    if settings._terms_re is not None:
        finders.append(_plain(settings._terms_re))
    if settings.tokens:
        finders.extend(_TOKEN_FINDERS)
    return finders


Protect.NONE = Protect(
    urls=False,
    emails=False,
    dois=False,
    placeholders=False,
    markup=False,
    paths=False,
    tokens=False,
)

_DEFAULT = Protect()
