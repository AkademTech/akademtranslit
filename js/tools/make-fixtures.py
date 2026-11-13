#!/usr/bin/env python3
"""Test vectors for the JavaScript port that the golden file does not hold.

    .venv/bin/python js/tools/make-fixtures.py           # write the fixtures
    .venv/bin/python js/tools/make-fixtures.py --check   # exit 1 if one differs

The library is imported from ``src/`` of this repository, as
``tools/golden.py`` imports it, and its output is written under
``js/test/fixtures/``. Each file is program output: never edit one by hand.

``migration-<version>.json``
    ``migration_report(text)`` and ``migration_report(text, protect=False)``
    for every input of ``golden/inputs.json``.
``options-<version>.json``
    The calls the golden file does not make -- ``protect=False``, a
    ``Protect`` with terms, the ``strip_*`` options, ``homoglyph_spans`` --
    on every input of ``golden/inputs.json``.
``traps-<version>.json``
    Inputs that the golden inputs lack and on which a JavaScript port is
    likely to differ (characters outside the BMP, the characters Python's
    ``re.IGNORECASE`` and ``str.isspace()`` treat specially, numbers that are
    letters to ``re``, special casing), through every golden field and every
    call above; and calls that raise, with the exception they raise.
``tables-<version>.json``
    The library's tables, for comparison with the port's constants.
``unicode-<unidata version>.json``
    Python's view of every code point: the character classes of ``str`` and
    ``re`` the library relies on, case mappings and NFC, NFKC and NFKD of
    single code points; and the code points the Unicode version leaves
    unassigned, where another Unicode version may differ.

Every file has a header with the library version, the rules version and the
SHA-256 of the inputs it was made from.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import platform
import re
import sys
import unicodedata
import warnings
from pathlib import Path

JS = Path(__file__).resolve().parent.parent
REPO = JS.parent
FIXTURES = JS / "test" / "fixtures"
INPUTS = REPO / "golden" / "inputs.json"

sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

import akademtranslit as lib  # noqa: E402
import golden  # noqa: E402  tools/golden.py: the golden fields, as the golden file has them

golden.lib = lib

ORTHOGRAPHIES = ("cyrillic", "latin_1995", "latin_2026")

# --- serialisation -------------------------------------------------------------------


def dump(obj, compact: bool = False) -> bytes:
    """Like the golden files, but keys keep their order: the order of a
    migration_report dict is part of the result. The two large tables are
    written ``compact``, without whitespace."""
    if compact:
        text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(obj, ensure_ascii=False, indent=1)
    return (text + "\n").encode("utf-8")


#: The calls of extra_fields() that options-<version>.json makes on every
#: golden input; traps-<version>.json makes all of them.
OPTION_FIELDS = (
    "convert_auto_to_cyrillic_protect_false",
    "convert_auto_to_latin_1995_protect_false",
    "convert_auto_to_latin_2026_protect_false",
    "convert_terms_to_cyrillic",
    "segments_terms",
    "validate_cyrillic_protect_false",
    "validate_latin_1995_protect_false",
    "validate_latin_2026_protect_false",
    "normalize_apostrophes_unicode_strip_both",
    "normalize_apostrophes_ascii_strip_invisible",
    "normalize_apostrophes_unicode_strip_stress",
    "homoglyph_spans",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def plain(value):
    """Tuples to lists, recursively, as JSON writes them anyway."""
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    return value


def outcome(call):
    """The value of ``call()``, or ``{"error": name}``: an error is an output too."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        try:
            return plain(call())
        except Exception as exc:  # recorded, not raised
            return {"error": type(exc).__name__}


def header(kind: str, inputs: bytes) -> dict:
    return {
        "schema": f"akademtranslit-js-fixture-{kind}/1",
        "library_version": lib.__version__,
        "rules_version": lib.RULES_VERSION,
        "inputs_sha256": sha256(inputs),
        "made_by": "js/tools/make-fixtures.py",
    }


# --- the calls the golden file does not make ---------------------------------------

#: Terms for the Protect calls: an ASCII name, a Cyrillic one and one outside the BMP.
TERMS = ("AslMatn", "Ўзбек", "\U0001d400\U0001d401C", "ToshDU")


def extra_fields() -> dict:
    """Field name -> function of the text, for the calls the golden file lacks."""
    terms = lib.Protect(terms=TERMS)
    out = {}
    for target in ORTHOGRAPHIES:
        out[f"convert_auto_to_{target}_protect_false"] = (
            lambda text, t=target: lib.convert(text, target=t, protect=False)
        )
    out["convert_terms_to_cyrillic"] = lambda text: lib.convert(text, target="cyrillic", protect=terms)
    out["convert_tags_latin_1995_to_cyrillic"] = lambda text: lib.convert(text, "uz-Latn-1995", "uz-Cyrl")
    out["to_latin_tag_latin_1995"] = lambda text: lib.to_latin(text, variant="uz-Latn-1995")
    out["to_cyrillic_protect_false"] = lambda text: lib.to_cyrillic(text, protect=False)
    out["segments_protect_false"] = lambda text: lib.segments(text, protect=False)
    out["segments_terms"] = lambda text: lib.segments(text, terms)
    out["segments_no_tokens_no_paths"] = lambda text: lib.segments(text, lib.Protect(tokens=False, paths=False))
    out["segments_placeholders_only"] = lambda text: lib.segments(
        text,
        lib.Protect(urls=False, emails=False, dois=False, markup=False, paths=False, tokens=False),
    )
    for orthography in ORTHOGRAPHIES:
        out[f"validate_{orthography}_protect_false"] = (
            lambda text, o=orthography: lib.validate(text, o, protect=False)
        )
    out["validate_tag_cyrillic"] = lambda text: lib.validate(text, "UZ_cyrl")
    out["sort_key_tag_latin_2026"] = lambda text: lib.sort_key(text, "uz-2026")[0]
    out["sort_key_text_latin_1995"] = lambda text: lib.sort_key(text, "latin_1995")[1]
    out["normalize_apostrophes_unicode_strip_both"] = lambda text: lib.normalize_apostrophes(
        text, strip_invisible=True, strip_stress=True
    )
    out["normalize_apostrophes_ascii_strip_invisible"] = lambda text: lib.normalize_apostrophes(
        text, "ascii", strip_invisible=True
    )
    out["normalize_apostrophes_unicode_strip_stress"] = lambda text: lib.normalize_apostrophes(
        text, strip_stress=True
    )
    out["homoglyph_spans"] = lib.homoglyph_spans
    return out


# --- traps: inputs the golden file lacks ------------------------------------------------

#: (id, text, what it is for). Characters outside the BMP are written as \U escapes.
TRAPS = [
    ("j001", "\U0001d400\U0001d401 Toshkent shahri", "astral capitals before a digraph (validate indices)"),
    ("j002", "\U00010400\U00010428 o\u02bbzbek \U00010428\U00010400", "Deseret: cased letters outside the BMP"),
    ("j003", "\U0001f600 Toshkent, \U0001f600 O\u02bbzbekiston, \U0001f600 \u0422\u043e\u0448\u043a\u0435\u043d\u0442",
     "emoji before findings in every orthography"),
    ("j004", "\U0001d41a'b o'zbek \U0001d41a'", "an apostrophe between an astral letter and a letter"),
    ("j005", "\u015eAHAR\U0001d400 \u015e\U0001d400 \U0001d400\u015e \u015eavkat \u00c7\U0001d400",
     "to_ascii: Ş and Ç beside an astral capital"),
    ("j006", "Ta\U0001d400sh\U0001d401kent \U0001d41a\U0001d41b", "sort keys of astral letters"),
    ("j007", "\u0422\U0001d400\u0448\u043a\u0435\u043d\u0442 \U0001f600 \u040e\u0437\u0431\u0435\u043a\u0438\u0441\u0442\u043e\u043d",
     "Cyrillic word with an astral letter"),
    ("j008", "\U0001f600 Toshk\u0435nt va T\u043eshkent", "homoglyphs after an emoji (homoglyph_spans indices)"),
    ("j009", "\U0001f600 Tosh\u00adkent \U000e0001x \u200bshahar", "invisible characters after an emoji, one outside the BMP"),
    ("j010", "\U0001f600 O\u0308zbek \U0001d400\u0301 \U0001d165\U0001d16d \u0308abc",
     "combining marks: after an astral base, astral marks, a piece that starts with one"),
    ("j011", "Sayt: Kun.uz, KUN.\u0130NFO, \u017fhahar.uz, HTTP\u017f://x.uz/a, www.\u212aun.uz, \u0130nfo.uz",
     "re.IGNORECASE: \u0130 \u0131 \u017f \u212a in URLs"),
    ("j012", "fayl.Z\u0130P, rasm.PNG, hujjat.doc\u212a? MAILTO:a@b.uz DO\u0130:10.1234/abc doi:10.12345/x.y.",
     "re.IGNORECASE: file names, mailto, doi"),
    ("j013", "Tosh\x85kent\x1cshahar\ufeffuz \x1fqishloq", "Python whitespace: U+0085, U+001C-U+001F; not U+FEFF"),
    ("j014", "\x85 Toshkent \x1f", "strip() and \\s+ with U+0085 and U+001F"),
    ("j015", "{n,\x85plural, one {# kitob} other {# kitob}}", "ICU syntax with U+0085 as space"),
    ("j016", "https://x.uz\x85matn https://y.uz\ufeffmatn", "\\S in URLs: U+0085 ends one, U+FEFF does not"),
    ("j017", "\u216b asr, x\u00b2 va \u00bd qism, \u2163-bob, \u00b2shahar \u2167\u2167",
     "numbers that are letters to re ([^\\W\\d_]): Nl and No"),
    ("j018", "STRASSE Stra\u00dfe \u01c5emal \u0130stanbul \u0149 \u0130SH", "special casing: \u00df, \u01c5, \u0130, \u0149"),
    ("j019", "\u03a3\u0391\u03a3 \u03c3\u03b1\u03c2 \u039f\u0394\u039f\u03a3 \u0391\u03a3.\u0392", "final sigma in lower()"),
    ("j020", "\u01c5amol \u01c4AMOL \u01c6amol", "titlecase letters"),
    ("j021", "\u212aelvin \u212aASR \u212a", "KELVIN SIGN"),
    ("j022", "{n, plural, one {https://x.uz/a} other {sayt https://shahar.uz/b}}",
     "a URL inside an ICU message ends at the message (search with endpos)"),
    ("j023", "{n, select, a {fayl.docx} other {x}} {g, selectordinal, offset:1 one {#chi} other {#-chi}}",
     "select, selectordinal and offset"),
    ("j024", "{a, plural, one {{b, select, x {{c, plural, one {# ta} other {# ta}}} other {y}}} other {z}}",
     "nested ICU arguments"),
    ("j025", "%1$s va %(name)s, 50%dan {{ ism }} <!-- izoh --> <b class=\"x>y\">matn</b> &amp; &#x1F;",
     "printf, double braces, a comment, a tag with > in a quoted value, entities"),
    ("j026", "C:\\Users\\Ali\\hujjat.docx ~/papka/fayl ../a/b \u00ab/c/d\u00bb kirill/lotin",
     "paths"),
    ("j027", "pH 7,4 SpO2 B12 3D iPhone McDonald MChJ AQSh ToshDU ChatGPT PhD AkademID 10ta 2026yil "
     "100mg ToshDUga ChatGPTda", "tokens"),
    ("j028", "AslMatn va \u040e\u0437\u0431\u0435\u043a, \U0001d400\U0001d401C va ToshDUga",
     "terms, one outside the BMP"),
    ("j029", "ShAHAR ToshDU O\u02bbzMU AQShda TerSh MChJ McDonald \U00010400SH",
     "letter units and irregular case"),
    ("j030", "O\u0308ZBEK o\u0308zbek G\u02bbO\u02bbZA", "combining diaeresis in capitals"),
    ("j031", "\ufb01le \ufb00 \u2163 \u00aa \u00ba", "compatibility characters (NFKC)"),
    ("j032", "\uff21\uff22\uff23 Toshkent \uff21\u0431", "fullwidth Latin: not Latin letters by name"),
    ("j033", "1\u00aa 2\u00ba \u0422\u043e\u0448\u043a\u0435\u043d\u0442 \u02b0", "\u00aa \u00ba \u02b0: Script=Latin, not LATIN by name"),
    ("j034", "\u00a0\u2028 Toshkent \u3000", "Python whitespace at both ends"),
    ("j035", "\U0001f600'salom' \U0001f600bog' \U0001f600o\u2019zbek", "marks after an emoji"),
    ("j036", "Isʼhoq va asʼhob, ish, Ishoq \U0001f600 sʼh", "separator words after an emoji (migration_report check)"),
    ("j037", "o\u0301zbek O\u0301ZBEK g\u0303ul \u014fzbek \u1e21ayrat", "look-alikes and stress"),
    ("j038", "\u0130stanbul\u0131 \u0131\u015f\u0131k", "dotted and dotless i"),
    ("j039", "\U0001d400 \U0001d41a \U0001d7ce \U00010400",
     "astral letter, digit (Nd, not a word) and cased letter alone"),
    ("j040", "", "empty text"),
    ("j041", "https://" + chr(0x015E) + chr(0x1D400) + ".uz https://" + chr(0x1D400) + chr(0xC7)
     + "x.uz https://" + chr(0x015E) + "x.uz", "to_ascii: Ş and Ç left in a URL, beside an astral capital"),
]


def trap_results(fields: dict) -> list:
    out = []
    for case_id, text, about in TRAPS:
        row = {name: outcome(lambda f=func: f(text)) for name, func in fields.items()}
        row["migration_report"] = outcome(lambda: lib.migration_report(text))
        row["migration_report_protect_false"] = outcome(lambda: lib.migration_report(text, protect=False))
        row["str_lower"] = text.lower()
        row["str_upper"] = text.upper()
        out.append({"id": case_id, "about": about, "text": text, "results": row})
    return out


# --- calls that raise ------------------------------------------------------------------
#
# Each is {"call": name, "args": [...], "kwargs": {...}}. A Protect is written
# {"Protect": {keyword arguments}}; the port's test builds the same object.

CALLS = [
    {"call": "convert", "args": ["Toshkent"], "kwargs": {"source": "auto2"}},
    {"call": "convert", "args": ["Toshkent"], "kwargs": {"source": 5}},
    {"call": "convert", "args": ["Toshkent"], "kwargs": {"target": "auto"}},
    {"call": "convert", "args": ["Toshkent"], "kwargs": {"target": "uz-Latn-1996"}},
    {"call": "convert", "args": ["Toshkent"], "kwargs": {"source": "uz-Latn", "target": "uz-Cyrl"}},
    {"call": "convert", "args": ["Toshkent"], "kwargs": {"protect": 1}},
    {"call": "convert", "args": ["Toshkent"], "kwargs": {"protect": None}},
    {"call": "convert", "args": ["https://x.uz Toshkent"], "kwargs": {"target": "cyrillic",
                                                                      "protect": {"Protect": {"urls": False}}}},
    {"call": "convert", "args": [""], "kwargs": {"target": "cyrillic"}},
    {"call": "to_latin", "args": ["Тошкент"], "kwargs": {"variant": "cyrillic"}},
    {"call": "to_latin", "args": ["Тошкент"], "kwargs": {"variant": "uz-Cyrl"}},
    {"call": "to_latin", "args": ["Тошкент"], "kwargs": {"variant": "uz-latn-1995"}},
    {"call": "to_latin", "args": ["Тошкент"], "kwargs": {"variant": "auto"}},
    {"call": "to_latin", "args": ["Тошкент"], "kwargs": {"variant": None}},
    {"call": "to_latin", "args": ["https://x.uz"], "kwargs": {"protect": False}},
    {"call": "to_cyrillic", "args": ["https://x.uz"], "kwargs": {"protect": False}},
    {"call": "to_cyrillic", "args": ["Toshkent"], "kwargs": {"protect": "yes"}},
    {"call": "sort_key", "args": ["Toshkent", "auto"], "kwargs": {}},
    {"call": "sort_key", "args": ["Toshkent", "uz"], "kwargs": {}},
    {"call": "sort_key", "args": ["Toshkent", "Latin"], "kwargs": {}},
    {"call": "sort_key", "args": ["Toshkent", None], "kwargs": {}},
    {"call": "validate", "args": ["Toshkent", "auto"], "kwargs": {}},
    {"call": "validate", "args": ["Toshkent", "uz-Latn-2026"], "kwargs": {"protect": 0}},
    {"call": "validate", "args": ["", "latin_2026"], "kwargs": {}},
    {"call": "validate", "args": ["", "nonsense"], "kwargs": {}},
    {"call": "migration_report", "args": ["Toshkent"], "kwargs": {"protect": "no"}},
    {"call": "migration_report", "args": [""], "kwargs": {}},
    {"call": "normalize_apostrophes", "args": ["o'zbek", "fancy"], "kwargs": {}},
    {"call": "normalize_apostrophes", "args": ["o'zbek", "ASCII"], "kwargs": {}},
    {"call": "segments", "args": ["https://x.uz", None], "kwargs": {}},
    {"call": "segments", "args": ["https://x.uz", 1], "kwargs": {}},
    {"call": "segments", "args": ["", True], "kwargs": {}},
    {"call": "script_for_tag", "args": [5], "kwargs": {}},
    {"call": "script_for_tag", "args": [None], "kwargs": {}},
    {"call": "script_for_tag", "args": ["uz-Latn-1995-x"], "kwargs": {}},
    {"call": "tag_for_script", "args": ["auto"], "kwargs": {}},
    {"call": "tag_for_script", "args": [None], "kwargs": {}},
    {"call": "Protect", "args": [], "kwargs": {"terms": "AslMatn"}},
    {"call": "Protect", "args": [], "kwargs": {"terms": [""]}},
    {"call": "Protect", "args": [], "kwargs": {"terms": [1]}},
    {"call": "Protect", "args": [], "kwargs": {"terms": None}},
    {"call": "Protect", "args": [], "kwargs": {"terms": ["AslMatn", "AslMatn"], "urls": 0}},
]


def decode(value):
    if isinstance(value, dict) and set(value) == {"Protect"}:
        return lib.Protect(**value["Protect"])
    return value


def protect_repr(value):
    """A Protect as the port's test reads it back: its settings."""
    return {
        "Protect": {
            "urls": value.urls,
            "emails": value.emails,
            "dois": value.dois,
            "placeholders": value.placeholders,
            "markup": value.markup,
            "paths": value.paths,
            "tokens": value.tokens,
            "terms": list(value.terms),
        }
    }


def call_results() -> list:
    out = []
    for call in CALLS:
        func = lib.Protect if call["call"] == "Protect" else getattr(lib, call["call"])
        args = [decode(arg) for arg in call["args"]]
        kwargs = {key: decode(value) for key, value in call["kwargs"].items()}
        result = outcome(lambda: func(*args, **kwargs))
        if isinstance(result, lib.Protect):
            result = protect_repr(result)
        out.append(dict(call, outcome=result))
    return out


# --- tables ------------------------------------------------------------------------------


def jsonable(value):
    if isinstance(value, (frozenset, set)):
        return sorted(value)
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def tables() -> dict:
    # By module name: the package's normalize() hides the module of that name.
    module = lambda name: importlib.import_module(f"akademtranslit.{name}")  # noqa: E731
    apostrophes, checks, collation = module("apostrophes"), module("checks"), module("collation")
    detection, normalize, protect = module("detection"), module("normalize"), module("protect")
    rules, t = module("rules"), module("tables")

    public = {
        name: jsonable(getattr(t, name))
        for name in sorted(dir(t))
        if name.isupper() and not name.startswith("_")
    }
    return {
        "tables": public,
        "rules": {
            "_TS_SUFFIXES": jsonable(rules._TS_SUFFIXES),
            "_TS_FOLLOWERS": jsonable(rules._TS_FOLLOWERS),
            "_CYRILLIC_CONSONANTS": jsonable(rules._CYRILLIC_CONSONANTS),
            "_CYRILLIC_IOTATED": jsonable(rules._CYRILLIC_IOTATED),
        },
        "normalize": {
            "_CYRILLIC_FOLD": jsonable(normalize._CYRILLIC_FOLD),
            "_LATIN_2026_FOLD": jsonable(normalize._LATIN_2026_FOLD),
        },
        "apostrophes": {"STYLES": jsonable(apostrophes.STYLES)},
        "detection": {
            "_UZBEK_LETTERS": jsonable(detection._UZBEK_LETTERS),
            "_RUSSIAN_LETTERS": jsonable(detection._RUSSIAN_LETTERS),
        },
        "protect": {"KINDS": jsonable(protect.KINDS), "_TRAILING": jsonable(protect._TRAILING)},
        "checks": {
            "CODES": jsonable(checks.CODES),
            "ROUND_TRIP": checks.ROUND_TRIP,
            "SEPARATOR": checks.SEPARATOR,
            "_LOOK_ALIKES": jsonable(checks._LOOK_ALIKES),
        },
        "collation": {"_COMPOUND_UNITS": jsonable(collation._COMPOUND_UNITS)},
        "all": sorted(lib.__all__),
    }


# --- Unicode ----------------------------------------------------------------------------

_RE_W = re.compile(r"\w")
_RE_D = re.compile(r"\d")
_RE_S = re.compile(r"\s")
_RE_LETTER = re.compile(r"[^\W\d_]")


def ranges(predicate) -> list:
    out = []
    for cp in range(0x110000):
        if predicate(chr(cp)):
            if out and out[-1][1] == cp - 1:
                out[-1][1] = cp
            else:
                out.append([cp, cp])
    return out


def unicode_tables() -> dict:
    def latin(ch):
        return ch.isalpha() and unicodedata.name(ch, "").startswith("LATIN ")

    case, nfc, nfkc, nfkd = [], [], [], []
    for cp in range(0x110000):
        ch = chr(cp)
        if 0xD800 <= cp <= 0xDFFF:
            continue  # a lone surrogate cannot be written as UTF-8
        lower, upper = ch.lower(), ch.upper()
        if lower != ch or upper != ch:
            case.append([cp, lower, upper])
        for form, out in (("NFC", nfc), ("NFKC", nfkc), ("NFKD", nfkd)):
            normal = unicodedata.normalize(form, ch)
            if normal != ch:
                out.append([cp, normal])
    return {
        "schema": "akademtranslit-js-fixture-unicode/1",
        "python": platform.python_version(),
        "unidata_version": unicodedata.unidata_version,
        "made_by": "js/tools/make-fixtures.py",
        "unassigned": ranges(lambda ch: unicodedata.category(ch) == "Cn"),
        "classes": {
            "isalpha": ranges(str.isalpha),
            "isupper": ranges(str.isupper),
            "isspace": ranges(str.isspace),
            "has_case": ranges(lambda ch: ch.lower() != ch.upper()),
            "mark": ranges(lambda ch: unicodedata.category(ch).startswith("M")),
            "re_w": ranges(lambda ch: _RE_W.match(ch) is not None),
            "re_d": ranges(lambda ch: _RE_D.match(ch) is not None),
            "re_s": ranges(lambda ch: _RE_S.match(ch) is not None),
            "re_letter": ranges(lambda ch: _RE_LETTER.match(ch) is not None),
            "latin_letter": ranges(latin),
        },
        "case": case,
        "nfc": nfc,
        "nfkc": nfkc,
        "nfkd": nfkd,
    }


# --- files --------------------------------------------------------------------------------


def documents() -> dict:
    inputs = INPUTS.read_bytes()
    cases = json.loads(inputs.decode("utf-8"))["cases"]
    version = lib.__version__
    extras = extra_fields()

    migration = header("migration", inputs)
    migration["results"] = {
        case["id"]: {
            "protect": outcome(lambda c=case: lib.migration_report(c["text"])),
            "no_protect": outcome(lambda c=case: lib.migration_report(c["text"], protect=False)),
        }
        for case in cases
    }

    options = header("options", inputs)
    options["terms"] = list(TERMS)
    options["fields"] = list(OPTION_FIELDS)
    options["results"] = {
        case["id"]: {name: outcome(lambda f=extras[name], c=case: f(c["text"])) for name in OPTION_FIELDS}
        for case in cases
    }

    traps_inputs = json.dumps([[i, t] for i, t, _ in TRAPS], ensure_ascii=False).encode("utf-8")
    traps = header("traps", traps_inputs)
    traps["terms"] = list(TERMS)
    traps["fields"] = sorted(golden.fields()) + sorted(extras)
    traps["cases"] = trap_results({**golden.fields(), **extras})
    traps["calls"] = call_results()

    table_doc = header("tables", inputs)
    table_doc.update(tables())

    return {
        f"migration-{version}.json": dump(migration),
        f"options-{version}.json": dump(options, compact=True),
        f"traps-{version}.json": dump(traps),
        f"tables-{version}.json": dump(table_doc),
        f"unicode-{unicodedata.unidata_version}.json": dump(unicode_tables(), compact=True),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 unless every fixture matches")
    args = parser.parse_args(argv)
    docs = documents()
    if args.check:
        ok = True
        for name, data in docs.items():
            path = FIXTURES / name
            if not path.exists() or path.read_bytes() != data:
                print(f"differs: js/test/fixtures/{name}")
                ok = False
        if ok:
            print(f"ok: {len(docs)} fixtures match")
        return 0 if ok else 1
    FIXTURES.mkdir(parents=True, exist_ok=True)
    for name, data in docs.items():
        (FIXTURES / name).write_bytes(data)
        print(f"wrote js/test/fixtures/{name} ({len(data):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
