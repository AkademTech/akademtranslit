"""Changes in 0.3.1: protected spans in linear time.

In 0.3.0 four inputs took time quadratic in their length: a URL, a DOI or a
path followed by a long run of ``)``; ``%`` followed by a long run of zeros; a
long run of labels with no ending (``a.a.a...``); and a long word of letters
joined by apostrophes (``a'a'a'...``). Each fix keeps the output. The 0.3.0 code
is kept below; the differential tests run it and the new code on the same
random inputs (fixed seeds) and compare, and the time tests time an input that
0.3.0 took tens of seconds over.
"""

from __future__ import annotations

import random
import re
import time
from types import SimpleNamespace

import pytest

from akademtranslit import protect, segments

# --- 0.3.0, as it was ----------------------------------------------------------------
#
# _L, _MARK, _TRAILING, _is_token and the other finders did not change.


def _trim_030(text, start, stop):
    while stop > start and text[stop - 1] in protect._TRAILING:
        if text[stop - 1] == ")" and text.count("(", start, stop) >= text.count(")", start, stop):
            break
        stop -= 1
    return stop


_PRINTF_030 = re.compile(
    r"(?<![\w%])%(?:[0-9]+\$)?(?:\([^()\s]+\))?[-+#0]*(?:[0-9]+|\*)?(?:\.(?:[0-9]+|\*))?"
    r"(?:hh|h|ll|l|L|q|j|z|t)?[diouxXeEfFgGcrsaAp]"
)

_LABEL_030 = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
_BARE_DOMAIN_030 = re.compile(
    r"(?<![\w@])(?P<tail>"
    + _LABEL_030
    + r"(?:\."
    + _LABEL_030
    + r")*\.(?:uz|com|org|net|ru|info|edu|gov|io)(?![\w-])(?:/\S*)?)",
    re.IGNORECASE,
)

_CHUNK_030 = re.compile(
    "(?<!" + protect._L + ")"
    + "(?=(?:" + protect._L + "|" + protect._MARK + ")*?(?:[0-9]|[a-z][A-Z]))"
    + protect._L + "+(?:" + protect._MARK + protect._L + "+)*(?:(?<=[oOgG])"
    + protect._MARK + ")?(?!" + protect._L + ")"
)


def _find_token_030(scanner, pos, end):
    text = scanner.text
    while True:
        m = _CHUNK_030.search(text, pos, end)
        if m is None:
            return None
        if protect._is_token(m.group()):
            return (m.start(), m.end(), protect.TOKEN, None)
        pos = m.end()


def _trimmed_030(regex, kind):
    def find(scanner, pos, end):
        text = scanner.text
        while True:
            m = regex.search(text, pos, end)
            if m is None:
                return None
            stop = _trim_030(text, m.start("tail"), m.end())
            if stop > m.start("tail"):
                return (m.start(), stop, kind, None)
            pos = m.start() + 1

    return find


def _plain_030(regex, kind):
    def find(scanner, pos, end):
        m = regex.search(scanner.text, pos, end)
        return None if m is None else (m.start(), m.end(), kind, None)

    return find


def _finders_030():
    """protect._finders(Protect()) of 0.3.0."""
    return [
        _trimmed_030(protect._SCHEME_URL.regex, protect.URL),
        _trimmed_030(_BARE_DOMAIN_030, protect.URL),
        protect._needs("@", _plain_030(protect._EMAIL.regex, protect.EMAIL)),
        protect._needs("10.", _trimmed_030(protect._DOI.regex, protect.DOI)),
        _plain_030(protect._TAG.regex, protect.MARKUP),
        protect._find_comment,
        protect._find_icu,
        protect._find_double_braces,
        protect._needs("%", _plain_030(_PRINTF_030, protect.PLACEHOLDER)),
        _trimmed_030(protect._PATH.regex, protect.PATH),
        _plain_030(protect._FILE_NAME.regex, protect.PATH),
        _find_token_030,
    ]


def _segments_030(text):
    pieces: list = []
    protect._Scanner(text, _finders_030()).scan(0, len(text), pieces)
    merged: list = []
    for start, stop, kind in pieces:
        if start == stop:
            continue
        if merged and merged[-1][2] == kind:
            merged[-1] = (merged[-1][0], stop, kind)
        else:
            merged.append((start, stop, kind))
    return [(text[start:stop], kind) for start, stop, kind in merged]


# --- random inputs -------------------------------------------------------------------

N = 20_000


def _text(rng, pieces, low=0, high=20):
    return "".join(rng.choice(pieces) for _ in range(rng.randint(low, high)))


def _bounds(rng, text):
    """``pos`` and ``end`` as the scanner passes them, pos <= end <= len: the
    whole text half the time, otherwise a random part."""
    if rng.random() < 0.5:
        return 0, len(text)
    end = rng.randint(0, len(text))
    return rng.randint(0, end), end


def _span(m):
    return None if m is None else (m.span(), m.span("tail") if "tail" in m.re.groupindex else None)


# --- differential tests -----------------------------------------------------------------


def test_the_kept_code_is_0_3_0():
    """Only _BARE_DOMAIN's search changed; its regular expression is 0.3.0's."""
    assert protect._BARE_DOMAIN.regex.pattern == _BARE_DOMAIN_030.pattern
    assert protect._BARE_DOMAIN.regex.flags == _BARE_DOMAIN_030.flags


def test_trim_matches_0_3_0():
    rng = random.Random(3101)
    pieces = list("((()))).,;:!?»\"'a/")
    for _ in range(N):
        text = _text(rng, pieces, 0, 24)
        start = rng.randint(0, len(text))
        stop = rng.randint(start, len(text))
        assert protect._trim(text, start, stop) == _trim_030(text, start, stop), (text, start, stop)


_PRINTF_PIECES = (
    ["%"] * 6
    + ["0", "0", "00", "000", "1", "12", "-", "+", "#", "*", ".", ".5", ".0", "1$", "0$", "(n)", "("]
    + [")", "h", "hh", "l", "ll", "L", "z", "q", "d", "d", "s", "s", "x", "f", "a", "p", "!", " ", "_"]
)


def _directive(rng):
    """Something shaped like a printf directive, often one."""
    parts = [
        rng.choice(["", "", "1$", "0$", "12$"]),
        rng.choice(["", "", "(n)", "("]),
        _text(rng, ["-", "+", "#", "0", "0"], 0, 4),
        rng.choice(["", "", "*", "1", "5", "10", "0", "05", "007", "120"]),
        rng.choice(["", "", ".", ".*", ".0", ".25", ".00"]),
        rng.choice(["", "", "", "h", "hh", "l", "ll", "L", "q", "j", "z", "t"]),
        rng.choice(["d", "s", "x", "f", "p", "a", "!", "", "y", " "]),
    ]
    return rng.choice(["", "", "a", "%", " "]) + "%" + "".join(parts) + rng.choice(["", "", "x", "%"])


def test_printf_matches_0_3_0():
    rng = random.Random(3102)
    for i in range(N):
        text = _directive(rng) if i % 2 else _text(rng, _PRINTF_PIECES, 1, 8)
        pos, end = _bounds(rng, text)
        old = _PRINTF_030.search(text, pos, end)
        new = protect._PRINTF.search(text, pos, end)
        assert (None if old is None else old.span()) == (None if new is None else new.span()), (text, pos, end)


_DOMAIN_PIECES = (
    ["a", "b1", "x-y", "-", ".", ".", "uz", "com", "io", "UZ", "Org", "@", " ", "/", "_", "1"]
    + ["K", "ſ", "İ", "ı", "é", "ш", "a.", "a.a.", "-.", ".uz", ".uz", ".com", ".uz-", ".uzb", ".Io/x"]
    + [".uz ", "a.uz", "x-y.com/p"]
    + ["x" * 40 + "-" + "y" * 30, "x" * 62 + "-", "z" * 63, "z" * 64, "q-" * 20]
)


def test_bare_domain_matches_0_3_0():
    rng = random.Random(3103)
    for _ in range(N):
        text = _text(rng, _DOMAIN_PIECES, 1, 10)
        pos, end = _bounds(rng, text)
        old = _BARE_DOMAIN_030.search(text, pos, end)
        new = protect._BARE_DOMAIN.search(text, pos, end)
        assert _span(old) == _span(new), (text, pos, end)


_WORD_PIECES = (
    list("aabbABoOgG12'ʻ’`ʼ -._SCDhUT")
    + ["Ş", "ш", "\U0001d400", "o'", "g'", "''", "1a", "aB", "Sh", "MChJ", "ToshDU", "pH", "x2"]
)


def test_find_token_matches_0_3_0():
    rng = random.Random(3104)
    for _ in range(N):
        text = _text(rng, _WORD_PIECES, 0, 20)
        pos, end = _bounds(rng, text)
        scanner = SimpleNamespace(text=text)
        assert protect._find_token(scanner, pos, end) == _find_token_030(scanner, pos, end), (text, pos, end)


_MIXED_PIECES = (
    _DOMAIN_PIECES
    + _WORD_PIECES
    + ["https://x.uz", "www.", "10.1234/", "doi:", "/", "./", "~/", "C:\\", "a@b.uz", "(", ")", ")))"]
    + ["%s", "%0", "%(n)d", "{n}", "{n, plural, one {#} other {#}}", "{{x}}", "<b>", "<!-- c -->"]
    + ["fayl.docx", "soʻz", "Toshkent", "\n", "\t"]
)


def test_segments_match_0_3_0():
    """segments() with every kind, against 0.3.0's finders through the same scanner."""
    rng = random.Random(3105)
    for _ in range(N):
        text = _text(rng, _MIXED_PIECES, 1, 16)
        assert segments(text) == _segments_030(text), text


# --- time tests ----------------------------------------------------------------------------
#
# Measured on one machine, 0.3.0 took 61 s, 15 s, 16 s, 13 s, 13 s and 14 s
# over these, and 0.3.1 takes 58 ms, 4 ms, 5 ms, 14 ms, 3 ms and 16 ms. Of the
# two for the bare domain, the first has no ending at all, the second has one
# that no label before it reaches; and of the two for the token, the first has
# no sign of a token, the second has one at the end of the word.

LIMIT = 1.0  # seconds

TIMED = {
    "url-and-200000-closing-brackets": (
        "https://akademtech.org/a" + ")" * 200_000,
        [("https://akademtech.org/a", "url"), (")" * 200_000, None)],
    ),
    "percent-and-20000-zeros": ("%" + "0" * 20_000 + "!", None),
    "15000-labels-no-ending": ("a." * 15_000 + "a", None),
    "15000-labels-an-ending-out-of-reach": ("a." * 15_000 + "a-.uz", None),
    "15000-apostrophes-in-a-word": ("a'" * 15_000, None),
    "10000-apostrophe-pairs-then-a-digit": ("a''" * 10_000 + "1", None),
}


@pytest.mark.parametrize("name", list(TIMED))
def test_linear_time(name):
    text, expected = TIMED[name]
    start = time.perf_counter()
    pieces = segments(text)
    elapsed = time.perf_counter() - start
    assert elapsed < LIMIT, f"{name}: {elapsed:.2f} s"
    assert pieces == (expected if expected is not None else [(text, None)])
