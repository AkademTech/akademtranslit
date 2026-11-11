"""BCP 47 language tags for the three orthographies.

Every argument that names an orthography -- ``source`` and ``target`` of
:func:`~akademtranslit.convert`, ``variant`` of :func:`~akademtranslit.to_latin`,
``orthography`` of :func:`~akademtranslit.sort_key` -- also takes a language
tag for it:

==================  ==============
Tag                 Orthography
==================  ==============
``uz-Cyrl``         ``cyrillic``
``uz-Latn-1995``    ``latin_1995``
``uz-Latn-2026``    ``latin_2026``
==================  ==============

>>> script_for_tag("uz-Latn-2026")
'latin_2026'
>>> script_for_tag("UZ_cyrl_UZ")
'cyrillic'
>>> tag_for_script("latin_1995")
'uz-Latn-1995'

A tag is read strictly, and nothing is guessed:

1. Only ASCII letters, digits, ``-`` and ``_`` (``_`` is ``-``, as in UTS #35).
   Subtags are 1 to 8 characters and are compared without regard to case.
2. The language is ``uz``. ``uzb``, ``uzn`` and ``uzs`` are refused with a
   hint to use ``uz``; so is an extended language subtag (``uz-uzn``).
3. The script, if there is one, is ``Latn`` or ``Cyrl``.
4. A region (two letters or three digits) is ignored.
5. The variant, if there is one, is ``1995`` or ``2026``: at most one, and
   none with ``Cyrl``.
6. Extensions (a singleton other than ``x`` and at least one subtag of 2 to 8
   characters, each singleton once) and a private-use part (``x`` and at
   least one subtag, to the end) are ignored.
7. Subtags come in that order; anything else is an error.

A ``str`` that breaks a rule raises :class:`ValueError`, which names the tag
and the forms that are read; anything but a ``str`` raises :class:`TypeError`.

``uz-Latn`` and ``uz`` name no orthography. In 0.x they are read as
``latin_1995`` with a :class:`FutureWarning`; from 1.0.0 they will be read as
``latin_2026``. Name the variant to avoid both. The library never decides by
the date: a call gives the same result on any day.
"""

from __future__ import annotations

import re
import warnings

from .tables import CYRILLIC, LATIN_1995, LATIN_2026, SCRIPTS

_TAG_FOR_SCRIPT = (
    (CYRILLIC, "uz-Cyrl"),
    (LATIN_1995, "uz-Latn-1995"),
    (LATIN_2026, "uz-Latn-2026"),
)

_VARIANTS = {"1995": LATIN_1995, "2026": LATIN_2026}
_SCRIPT_SUBTAGS = ("latn", "cyrl")
_OTHER_CODES_FOR_UZBEK = ("uzb", "uzn", "uzs")

# ASCII only, checked before anything is lowercased: str.lower() would turn
# some non-ASCII letters (U+212A KELVIN SIGN) into ASCII ones.
_TAG_CHARACTERS = re.compile(r"[A-Za-z0-9_-]+")

_FORMS = (
    "'uz-Cyrl', 'uz-Latn-1995' or 'uz-Latn-2026' (or 'uz-1995', 'uz-2026'), "
    "in any case, with '-' or '_'"
)

_NAMES_NO_ORTHOGRAPHY = (
    "{tag!r} names no orthography: akademtranslit 0.x reads it as 'uz-Latn-1995', "
    "and from 1.0.0 it will read it as 'uz-Latn-2026'. "
    "Pass 'uz-Latn-1995' or 'uz-Latn-2026' to choose."
)


class _NotRead(ValueError):
    """Why a tag was not read; the callers put it in their own message."""


def _is_variant(subtag: str) -> bool:
    # RFC 5646: 5 to 8 alphanumerics, or a digit and 3 alphanumerics.
    return 5 <= len(subtag) <= 8 or (len(subtag) == 4 and subtag[0].isdigit())


def _parse(tag: str) -> tuple:
    """``(orthography, names_it)`` for ``tag``: ``names_it`` is False for a
    Latin tag without a variant. Raises TypeError or _NotRead."""
    if not isinstance(tag, str):
        raise TypeError(f"a language tag must be a str, not {type(tag).__name__}")
    if not tag:
        raise _NotRead("it is empty")
    if not _TAG_CHARACTERS.fullmatch(tag):
        raise _NotRead("only ASCII letters, digits, '-' and '_' may appear in a tag")
    subtags = tag.replace("_", "-").lower().split("-")
    for subtag in subtags:
        if not subtag:
            raise _NotRead("it has an empty subtag")
        if len(subtag) > 8:
            raise _NotRead(f"the subtag {subtag!r} is longer than 8 characters")

    language, rest = subtags[0], subtags[1:]
    if language in _OTHER_CODES_FOR_UZBEK:
        raise _NotRead(f"{language!r} is Uzbek too, but use 'uz'")
    if language != "uz":
        raise _NotRead(f"the language is {language!r}, not 'uz'")

    i = 0
    n = len(rest)
    if i < n and len(rest[i]) == 3 and rest[i].isalpha():
        raise _NotRead(f"an extended language subtag ({rest[i]!r}) is not supported")

    script = None
    if i < n and len(rest[i]) == 4 and rest[i].isalpha():
        if rest[i] not in _SCRIPT_SUBTAGS:
            raise _NotRead(f"the script {rest[i]!r} is not supported; use 'Latn' or 'Cyrl'")
        script = rest[i]
        i += 1

    if i < n and (
        (len(rest[i]) == 2 and rest[i].isalpha()) or (len(rest[i]) == 3 and rest[i].isdigit())
    ):
        i += 1  # a region: it does not change the orthography

    variant = None
    while i < n and _is_variant(rest[i]):
        if rest[i] not in _VARIANTS:
            raise _NotRead(f"the variant {rest[i]!r} is not supported; use '1995' or '2026'")
        if variant is not None:
            raise _NotRead("it has more than one variant")
        variant = rest[i]
        i += 1

    singletons = set()
    while i < n and len(rest[i]) == 1 and rest[i] != "x":
        singleton = rest[i]
        if singleton in singletons:
            raise _NotRead(f"the extension {singleton!r} appears twice")
        singletons.add(singleton)
        i += 1
        first = i
        while i < n and len(rest[i]) >= 2:
            i += 1
        if i == first:
            raise _NotRead(f"the extension {singleton!r} has no subtags")

    if i < n and rest[i] == "x":
        if i + 1 == n:
            raise _NotRead("the private-use part 'x' has no subtags")
        i = n  # private use runs to the end; every subtag is 1 to 8 characters

    if i < n:
        raise _NotRead(f"the subtag {rest[i]!r} is out of place")

    if script == "cyrl":
        if variant is not None:
            raise _NotRead(f"the variant {variant!r} is a Latin orthography; 'uz-Cyrl' takes none")
        return CYRILLIC, True
    if variant is None:
        return LATIN_1995, False
    return _VARIANTS[variant], True


def _warn_names_no_orthography(tag: str, stacklevel: int) -> None:
    # ``stacklevel`` is what the caller would pass to warnings.warn itself.
    warnings.warn(
        _NAMES_NO_ORTHOGRAPHY.format(tag=tag), FutureWarning, stacklevel=stacklevel + 1
    )


def script_for_tag(tag: str) -> str:
    """Return the orthography -- one of ``SCRIPTS`` -- that ``tag`` names.

    >>> script_for_tag("uz-Cyrl")
    'cyrillic'
    >>> script_for_tag("uz-1995")
    'latin_1995'

    The rules are in the module docstring. A tag that breaks one raises
    :class:`ValueError`, and anything but a ``str`` :class:`TypeError`.
    ``uz-Latn`` and ``uz`` give ``latin_1995`` with a :class:`FutureWarning`:
    from 1.0.0 they will give ``latin_2026``.
    """
    try:
        script, names_it = _parse(tag)
    except _NotRead as exc:
        raise ValueError(
            f"{tag!r} is not a language tag for an Uzbek orthography: {exc}; expected {_FORMS}"
        ) from None
    if not names_it:
        _warn_names_no_orthography(tag, stacklevel=2)
    return script


def tag_for_script(script: str) -> str:
    """Return the language tag for ``script``, one of ``SCRIPTS``.

    >>> tag_for_script("cyrillic")
    'uz-Cyrl'
    >>> tag_for_script("latin_2026")
    'uz-Latn-2026'

    Anything else -- ``"auto"``, a tag, another name -- raises
    :class:`ValueError`.
    """
    for name, tag in _TAG_FOR_SCRIPT:
        if script == name:
            return tag
    raise ValueError(f"unknown orthography: {script!r}; expected one of {SCRIPTS}")


def _orthography(value: str, unknown: str, stacklevel: int) -> str:
    """The orthography an argument names, for the functions that take one.

    Called only when ``value`` is not in ``SCRIPTS``. ``unknown`` is the
    caller's error message for a value it does not take; it is raised as it
    is for ``"auto"``, and with the reason added for a tag that is not read.
    ``stacklevel`` is what the caller would pass to :func:`warnings.warn`
    itself: 2 points the warning at the line that called the caller.
    """
    if value == "auto":
        raise ValueError(unknown)
    try:
        script, names_it = _parse(value)
    except _NotRead as exc:
        raise ValueError(
            f"{unknown}, or a language tag for one of them; {value!r} is not one: {exc}"
        ) from None
    if not names_it:
        _warn_names_no_orthography(value, stacklevel=stacklevel + 1)
    return script
