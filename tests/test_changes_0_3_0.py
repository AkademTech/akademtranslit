"""Changes in 0.3.0.

Each section pins one change: what it fixes, what it must leave alone, and,
where a function had two answers for one question, that it now has one.
"""

from __future__ import annotations

import importlib.util
import json
import re
import unicodedata
import warnings
from pathlib import Path

import pytest

from akademtranslit import (
    CYRILLIC,
    LATIN_1995,
    LATIN_2026,
    RULES_VERSION,
    SCRIPTS,
    _REFORM_LETTERS,
    convert,
    detect_script,
    is_cyrillic,
    normalize,
    script_class,
    script_for_tag,
    sort_key,
    tag_for_script,
    to_ascii,
    to_cyrillic,
    to_latin,
)

REPO = Path(__file__).resolve().parent.parent
GOLDEN_INPUTS = REPO / "golden" / "inputs.json"

# The draft glyphs for oʻ, written as escapes because they look alike:
O_MACRON = "\u014d"            # ō LATIN SMALL LETTER O WITH MACRON
O_CARON = "\u01d2"             # ǒ LATIN SMALL LETTER O WITH CARON
CAPITAL_O_MACRON = "\u014c"    # Ō LATIN CAPITAL LETTER O WITH MACRON
CAPITAL_O_CARON = "\u01d1"     # Ǒ LATIN CAPITAL LETTER O WITH CARON

DRAFT_GLYPHS = [O_MACRON, O_CARON, CAPITAL_O_MACRON, CAPITAL_O_CARON]


# --- detect_script: every draft glyph is a 2026 letter, in either case --------
#
# The set of 2026-only letters held U+01D3 (Ǔ, U with caron) where U+01D1
# (Ǒ, O with caron) belonged, so text with a capital Ǒ was read as 1995.


@pytest.mark.parametrize("glyph", DRAFT_GLYPHS)
def test_a_draft_glyph_alone_is_latin_2026(glyph):
    assert detect_script(glyph) == LATIN_2026


@pytest.mark.parametrize("glyph", DRAFT_GLYPHS)
def test_a_draft_glyph_in_a_word_is_latin_2026(glyph):
    assert detect_script(glyph + "zbekiston") == LATIN_2026
    assert detect_script("t" + glyph + "rt") == LATIN_2026


@pytest.mark.parametrize("letter", sorted(_REFORM_LETTERS))
def test_the_2026_letters_are_there_in_both_cases(letter):
    assert letter.lower() in _REFORM_LETTERS
    assert letter.upper() in _REFORM_LETTERS


# --- ō and ǒ come out as ö in every 2026 output -------------------------------
#
# The draft glyphs were read as ö only on the way out of latin_2026. Converting
# latin_2026 text to latin_2026 (which is what to_latin does with it) had no
# step to run, so to_latin("ōrdak") gave "ōrdak". They are now read as ö
# whenever the source or the target is latin_2026.

# The golden inputs with a draft glyph: id -> (input, 2026 output).
DRAFT_GLYPH_INPUTS = {
    "c0328": (CAPITAL_O_MACRON + "zbekiston", "Özbekiston"),
    "c1077": (O_MACRON, "ö"),
    "c1078": (O_CARON, "ö"),
    "c1079": (CAPITAL_O_MACRON, "Ö"),
    "c1080": (CAPITAL_O_CARON, "Ö"),
    "c1081": (O_MACRON + "rdak", "ördak"),
    "c1082": (O_CARON + "rdak", "ördak"),
    "c1083": (CAPITAL_O_MACRON + "RDAK", "ÖRDAK"),
    "c1084": (CAPITAL_O_CARON + "zbekiston", "Özbekiston"),
}
DRAFT_GLYPH_CASES = sorted(DRAFT_GLYPH_INPUTS.values())


def test_the_draft_glyph_cases_are_the_golden_inputs():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    texts = {case["id"]: case["text"] for case in doc["cases"]}
    assert {i: texts[i] for i in DRAFT_GLYPH_INPUTS} == {
        i: text for i, (text, _) in DRAFT_GLYPH_INPUTS.items()
    }


@pytest.mark.parametrize("text,expected", DRAFT_GLYPH_CASES)
def test_to_latin_writes_the_draft_glyphs_as_o_umlaut(text, expected):
    assert to_latin(text) == expected


@pytest.mark.parametrize("text,expected", DRAFT_GLYPH_CASES)
def test_latin_2026_to_latin_2026_writes_the_draft_glyphs_as_o_umlaut(text, expected):
    assert convert(text, source=LATIN_2026, target=LATIN_2026) == expected


def test_latin_1995_to_latin_2026_writes_the_draft_glyphs_as_o_umlaut():
    """The source is given as latin_1995, but the text has a draft glyph."""
    assert convert(O_MACRON + "zbek", source=LATIN_1995, target=LATIN_2026) == "özbek"
    assert convert(O_CARON + "zbek", source=LATIN_1995, target=LATIN_2026) == "özbek"


@pytest.mark.parametrize("text,expected", DRAFT_GLYPH_CASES)
def test_cyrillic_to_latin_2026_writes_the_draft_glyphs_as_o_umlaut(text, expected):
    """A Latin word inside Cyrillic text: the target is latin_2026."""
    assert convert(text, source=CYRILLIC, target=LATIN_2026) == expected


def test_a_draft_glyph_in_cyrillic_text_comes_out_as_o_umlaut():
    assert to_latin("Тошкент " + O_MACRON + "rdak") == "Toşkent ördak"
    assert to_latin("ТОШКЕНТ " + CAPITAL_O_CARON + "RDAK") == "TOŞKENT ÖRDAK"


@pytest.mark.parametrize("text,expected", DRAFT_GLYPH_CASES)
def test_the_2026_output_is_idempotent(text, expected):
    once = convert(text)
    assert convert(once) == once


def test_a_given_latin_1995_source_is_kept_when_the_target_is_not_2026():
    """Neither side is latin_2026, so the glyph is not read as ö.

    The caller said the text is latin_1995, and in latin_1995 ō is not a letter;
    the source they give wins over what the text looks like.
    """
    assert convert(O_MACRON + "zbek", source=LATIN_1995, target=LATIN_1995) == O_MACRON + "zbek"
    assert convert(O_MACRON + "zbek", source=LATIN_1995, target=CYRILLIC) == O_MACRON + "збек"


# --- one Cyrillic range: U+0400-U+052F everywhere ------------------------------
#
# is_cyrillic, and through it detect_script and normalize, took Cyrillic to be
# U+0400-U+04FF; script_class and normalize_apostrophes took U+0400-U+052F. A
# letter from the Cyrillic Supplement block was Cyrillic to one function and
# not to another. All of them now use U+0400-U+052F.

# Every letter from the end of Greek to the start of Armenian.
LETTERS_AROUND_CYRILLIC = [
    chr(cp) for cp in range(0x0370, 0x0561) if unicodedata.category(chr(cp)).startswith("L")
]


def test_is_cyrillic_detect_script_and_script_class_agree():
    disagree = []
    for letter in LETTERS_AROUND_CYRILLIC:
        answers = (
            is_cyrillic(letter),
            detect_script(letter) == CYRILLIC,
            script_class(letter) == "cyrillic",
        )
        if answers not in ((True, True, True), (False, False, False)):
            disagree.append((f"U+{ord(letter):04X}", answers))
    assert disagree == []


def test_the_cyrillic_supplement_is_cyrillic():
    assert is_cyrillic("\u0501")         # CYRILLIC SMALL LETTER KOMI DE
    assert detect_script("\u051a") == CYRILLIC   # CYRILLIC CAPITAL LETTER QA


# --- language tags --------------------------------------------------------------
#
# Every argument that names an orthography also takes a BCP 47 language tag.
# The tag is read strictly: anything not in the table below as valid is a
# ValueError. uz-Latn and uz name no orthography; 0.x reads them as 1995 and
# says, with a FutureWarning, that 1.0.0 will read them as 2026.

W = "FutureWarning"

# golden/tag-inputs.json, with the result each tag must give:
# (id, tag, orthography or the exception's name, warning or None).
TAG_CASES = [
    ("t001", "uz", LATIN_1995, W),
    ("t002", "UZ", LATIN_1995, W),
    ("t003", "uz-Latn", LATIN_1995, W),
    ("t004", "uz-latn", LATIN_1995, W),
    ("t005", "UZ-LATN", LATIN_1995, W),
    ("t006", "uz-Latn-UZ", LATIN_1995, W),
    ("t007", "uz-UZ", LATIN_1995, W),
    ("t008", "uz_Latn", LATIN_1995, W),
    ("t009", "uz-Cyrl", CYRILLIC, None),
    ("t010", "uz-cyrl", CYRILLIC, None),
    ("t011", "UZ-CYRL-UZ", CYRILLIC, None),
    ("t012", "uz_Cyrl_UZ", CYRILLIC, None),
    ("t013", "uz-1995", LATIN_1995, None),
    ("t014", "uz-Latn-1995", LATIN_1995, None),
    ("t015", "uz-latn-1995", LATIN_1995, None),
    ("t016", "uz-Latn-UZ-1995", LATIN_1995, None),
    ("t017", "uz-2026", LATIN_2026, None),
    ("t018", "uz-Latn-2026", LATIN_2026, None),
    ("t019", "UZ-LATN-2026", LATIN_2026, None),
    ("t020", "uz-UZ-2026", LATIN_2026, None),
    ("t021", "uz-Latn-UZ-2026", LATIN_2026, None),
    ("t022", "uz_Latn_2026", LATIN_2026, None),
    ("t023", "uz-Latn-2026-t-uz-cyrl", LATIN_2026, None),
    ("t024", "uz-Latn-1995-x-akadem", LATIN_1995, None),
    ("t025", "uz-Latn-u-co-standard", LATIN_1995, W),
    ("t026", "uz-Cyrl-t-uz-latn-2026", CYRILLIC, None),
    ("t027", "uz-860", LATIN_1995, W),
    ("t028", "", "ValueError", None),
    ("t029", "uz-", "ValueError", None),
    ("t030", "-uz", "ValueError", None),
    ("t031", "uz--Latn", "ValueError", None),
    ("t032", " uz-Latn", "ValueError", None),
    ("t033", "uz-Latn ", "ValueError", None),
    ("t034", "uz-Cyrl-1995", "ValueError", None),
    ("t035", "uz-Cyrl-2026", "ValueError", None),
    ("t036", "uz-Latn-1995-2026", "ValueError", None),
    ("t037", "uz-2026-2026", "ValueError", None),
    ("t038", "uz-Latn-1940", "ValueError", None),
    ("t039", "uz-Latn-1996", "ValueError", None),
    ("t040", "uz-Arab", "ValueError", None),
    ("t041", "uz-Arab-AF", "ValueError", None),
    ("t042", "uz-Latn-Cyrl", "ValueError", None),
    ("t043", "uz-Latn-UZ-AF", "ValueError", None),
    ("t044", "uz-2026-Latn", "ValueError", None),
    ("t045", "uzb", "ValueError", None),
    ("t046", "uzn-Latn", "ValueError", None),
    ("t047", "uz-uzn", "ValueError", None),
    ("t048", "en", "ValueError", None),
    ("t049", "ru-Cyrl", "ValueError", None),
    ("t050", "x-uz", "ValueError", None),
    ("t051", "uz-Latn-2026-t", "ValueError", None),
    ("t052", "uz-Latn-2026-x", "ValueError", None),
    ("t053", "uz_UZ@latin", "ValueError", None),
    ("t054", "uz-Latn-2026-abcdefghi", "ValueError", None),
    ("t055", "latin_2026", "ValueError", None),
    ("t056", "uz-\uff2catn", "ValueError", None),   # U+FF2C FULLWIDTH LATIN CAPITAL LETTER L
    ("t057", "uz-Latn-2026-t-uz-cyrl-t-ru", "ValueError", None),
]

# (id, orthography name, tag_for_script's result or the exception's name).
SCRIPT_CASES = [
    ("s01", "cyrillic", "uz-Cyrl"),
    ("s02", "latin_1995", "uz-Latn-1995"),
    ("s03", "latin_2026", "uz-Latn-2026"),
    ("s04", "auto", "ValueError"),
    ("s05", "uz-Latn-2026", "ValueError"),
    ("s06", "Cyrillic", "ValueError"),
]

UNNAMED_MESSAGE = (
    "{tag!r} names no orthography: akademtranslit 0.x reads it as 'uz-Latn-1995', "
    "and from 1.0.0 it will read it as 'uz-Latn-2026'. "
    "Pass 'uz-Latn-1995' or 'uz-Latn-2026' to choose."
)


def _call(func, *args, **kwargs):
    """func's result, and the warnings it raised, every one of them recorded."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = func(*args, **kwargs)
    return result, caught


@pytest.mark.parametrize(
    "tag,expected,warning",
    [case[1:] for case in TAG_CASES if case[2] != "ValueError"],
    ids=[case[0] for case in TAG_CASES if case[2] != "ValueError"],
)
def test_a_valid_tag_names_its_orthography(tag, expected, warning):
    script, caught = _call(script_for_tag, tag)
    assert script == expected
    assert [w.category.__name__ for w in caught] == ([warning] if warning else [])
    if warning:
        assert str(caught[0].message) == UNNAMED_MESSAGE.format(tag=tag)


@pytest.mark.parametrize(
    "tag",
    [case[1] for case in TAG_CASES if case[2] == "ValueError"],
    ids=[case[0] for case in TAG_CASES if case[2] == "ValueError"],
)
def test_an_invalid_tag_is_a_value_error_that_names_it(tag):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError) as excinfo:
            script_for_tag(tag)
    message = str(excinfo.value)
    assert repr(tag) in message
    assert "'uz-Latn-2026'" in message      # and the forms it takes
    assert caught == []


@pytest.mark.parametrize("hint", ["uzb", "uzn-Latn", "uzs-Arab"])
def test_the_other_codes_for_uzbek_get_a_hint(hint):
    with pytest.raises(ValueError, match="use 'uz'"):
        script_for_tag(hint)


@pytest.mark.parametrize("value", [None, b"uz-Latn-2026", 2026, ["uz"]])
def test_a_tag_that_is_not_a_str_is_a_type_error(value):
    with pytest.raises(TypeError):
        script_for_tag(value)


# The functions that take an orthography raise ValueError for a value that is
# not a str, as they did before tags; only script_for_tag raises TypeError.
ORTHOGRAPHY_ARGUMENTS = [
    ("convert source", lambda value: convert("Toshkent", source=value)),
    ("convert target", lambda value: convert("Toshkent", target=value)),
    ("to_latin variant", lambda value: to_latin("Toshkent", variant=value)),
    ("sort_key orthography", lambda value: sort_key("Toshkent", value)),
]


@pytest.mark.parametrize(
    "call", [a[1] for a in ORTHOGRAPHY_ARGUMENTS], ids=[a[0] for a in ORTHOGRAPHY_ARGUMENTS]
)
@pytest.mark.parametrize("value", [None, 123, b"uz-Latn-2026"], ids=["None", "int", "bytes"])
def test_an_orthography_argument_that_is_not_a_str_is_a_value_error(call, value):
    with pytest.raises(ValueError):
        call(value)


def test_script_for_tag_still_raises_type_error_for_a_non_str():
    with pytest.raises(TypeError):
        script_for_tag(None)


@pytest.mark.parametrize("case_id,script,expected", SCRIPT_CASES, ids=[c[0] for c in SCRIPT_CASES])
def test_tag_for_script(case_id, script, expected):
    if expected == "ValueError":
        with pytest.raises(ValueError):
            tag_for_script(script)
    else:
        assert tag_for_script(script) == expected


@pytest.mark.parametrize("value", [None, 1995, ["cyrillic"], ("latin_2026",)])
def test_tag_for_script_takes_only_the_three_names(value):
    with pytest.raises(ValueError):
        tag_for_script(value)


@pytest.mark.parametrize("script", SCRIPTS)
def test_tag_for_script_and_back(script):
    assert script_for_tag(tag_for_script(script)) == script


# The four ways in: each must point the warning at the line that called it.
ENTRY_POINTS = [
    ("script_for_tag", lambda tag: script_for_tag(tag)),
    ("convert source", lambda tag: convert("Toshkent", source=tag, target=LATIN_2026)),
    ("convert target", lambda tag: convert("Тошкент", source=CYRILLIC, target=tag)),
    ("convert, empty text", lambda tag: convert("", source=tag)),
    ("to_latin", lambda tag: to_latin("Тошкент", variant=tag)),
    ("sort_key", lambda tag: sort_key("Toshkent", tag)),
]


@pytest.mark.parametrize("call", [e[1] for e in ENTRY_POINTS], ids=[e[0] for e in ENTRY_POINTS])
@pytest.mark.parametrize("tag", ["uz", "uz-Latn"])
def test_the_warning_points_at_the_caller(call, tag):
    _, caught = _call(call, tag)
    assert [w.category for w in caught] == [FutureWarning]
    assert Path(caught[0].filename).resolve() == Path(__file__).resolve()


@pytest.mark.parametrize("call", [e[1] for e in ENTRY_POINTS], ids=[e[0] for e in ENTRY_POINTS])
@pytest.mark.parametrize("tag", ["uz-Latn-1995", "uz-2026"])
def test_a_tag_with_a_variant_does_not_warn(call, tag):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        call(tag)


def test_orthography_names_do_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for source in SCRIPTS + ("auto",):
            for target in SCRIPTS:
                convert("Toshkent", source=source, target=target)
        to_latin("Toshkent", variant=LATIN_1995)
        sort_key("Toshkent", LATIN_2026)


def test_to_latin_refuses_a_cyrillic_tag():
    with pytest.raises(ValueError, match="not a Latin orthography"):
        to_latin("Toshkent", variant="uz-Cyrl")


@pytest.mark.parametrize(
    "value,match",
    [
        ("latin_1940", "unknown Latin variant"),
        ("cyrillic", "unknown Latin variant"),
        ("auto", "unknown Latin variant"),
        ("uz-Latn-1940", "unknown Latin variant"),
    ],
)
def test_to_latin_keeps_its_error_for_other_values(value, match):
    with pytest.raises(ValueError, match=match):
        to_latin("Toshkent", variant=value)


def test_convert_and_sort_key_keep_their_errors():
    with pytest.raises(ValueError, match="unknown source script"):
        convert("Toshkent", source="uz-Arab")
    with pytest.raises(ValueError, match="unknown target script"):
        convert("Toshkent", target="auto")
    with pytest.raises(ValueError, match="unknown target script"):
        convert("Toshkent", target="uz-Cyrl-2026")
    with pytest.raises(ValueError, match="unknown orthography"):
        sort_key("Toshkent", "uz-Latn-1940")


TAG_FOR = {CYRILLIC: "uz-Cyrl", LATIN_1995: "uz-Latn-1995", LATIN_2026: "uz-Latn-2026"}
SAMPLES = ["Тошкент", "Oʻzbekiston", "Özbekiston", "Isʼhoq", "ŞOŞIMOVA", "ketsa"]


@pytest.mark.parametrize("source", SCRIPTS)
@pytest.mark.parametrize("target", SCRIPTS)
def test_convert_gives_the_same_with_a_tag_or_a_name(source, target):
    for text in SAMPLES:
        assert convert(text, source=TAG_FOR[source], target=TAG_FOR[target]) == convert(
            text, source=source, target=target
        )


@pytest.mark.parametrize("script", SCRIPTS)
def test_sort_key_gives_the_same_with_a_tag_or_a_name(script):
    for text in SAMPLES:
        assert sort_key(text, TAG_FOR[script]) == sort_key(text, script)


def test_to_latin_gives_the_same_with_a_tag_or_a_name():
    for text in SAMPLES:
        assert to_latin(text, variant="uz-Latn-1995") == to_latin(text, variant=LATIN_1995)
        assert to_latin(text, variant="uz-2026") == to_latin(text, variant=LATIN_2026)


# --- RULES_VERSION ----------------------------------------------------------------
#
# Which rules the conversion functions follow: the official basis, then this
# project's rule set, named by the release that last changed the output of
# convert, to_latin or to_cyrillic. tools/golden.py --check fails if two
# consecutive golden files differ in that output but not in RULES_VERSION.


def test_rules_version_has_the_documented_shape():
    assert re.fullmatch(r"[a-z0-9-]+\+project-\d{4}\.\d{2}", RULES_VERSION)
    assert RULES_VERSION.startswith("uz-2026-alphabet+")


def _golden_tool():
    """tools/golden.py, loaded from its path: it is not part of the package, and
    the release workflow runs the tests against the installed wheel."""
    spec = importlib.util.spec_from_file_location("golden_tool", REPO / "tools" / "golden.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_golden(directory, version, rules_version, row):
    doc = {"library_version": version, "results": {"c0001": row}}
    if rules_version is not None:
        doc["rules_version"] = rules_version
    path = directory / f"golden-{version}.json"
    path.write_bytes(json.dumps(doc, ensure_ascii=False).encode("utf-8"))


def test_a_changed_conversion_needs_a_new_rules_version(tmp_path):
    _write_golden(tmp_path, "0.3.0", "uz+project-2026.11", {"to_latin_2026": "ōrdak"})
    _write_golden(tmp_path, "0.3.1", "uz+project-2026.11", {"to_latin_2026": "ördak"})
    assert _golden_tool().rules_version_problems(tmp_path) != []


def test_a_changed_convert_field_needs_a_new_rules_version(tmp_path):
    _write_golden(tmp_path, "0.3.0", "uz+project-2026.11", {"convert_from_cyrillic_to_cyrillic": "a"})
    _write_golden(tmp_path, "0.3.1", "uz+project-2026.11", {"convert_from_cyrillic_to_cyrillic": "b"})
    assert _golden_tool().rules_version_problems(tmp_path) != []


def test_a_new_rules_version_allows_the_change(tmp_path):
    _write_golden(tmp_path, "0.3.0", "uz+project-2026.11", {"to_latin_2026": "ōrdak"})
    _write_golden(tmp_path, "0.3.1", "uz+project-2026.12", {"to_latin_2026": "ördak"})
    assert _golden_tool().rules_version_problems(tmp_path) == []


def test_a_changed_normalize_does_not_need_a_new_rules_version(tmp_path):
    _write_golden(tmp_path, "0.3.0", "uz+project-2026.11", {"to_latin_2026": "a", "normalize": "a"})
    _write_golden(tmp_path, "0.3.1", "uz+project-2026.11", {"to_latin_2026": "a", "normalize": "b"})
    assert _golden_tool().rules_version_problems(tmp_path) == []


def test_files_without_a_rules_version_and_the_version_order(tmp_path):
    """0.2.0 has no rules_version and is skipped; 0.10.0 comes after 0.9.0."""
    _write_golden(tmp_path, "0.2.0", None, {"to_latin_2026": "x"})
    _write_golden(tmp_path, "0.9.0", "uz+project-2026.11", {"to_latin_2026": "a"})
    _write_golden(tmp_path, "0.10.0", "uz+project-2027.01", {"to_latin_2026": "b"})
    _write_golden(tmp_path, "0.10.1", "uz+project-2027.01", {"to_latin_2026": "b"})
    assert _golden_tool().rules_version_problems(tmp_path) == []
    _write_golden(tmp_path, "0.10.2", "uz+project-2027.01", {"to_latin_2026": "c"})
    problems = _golden_tool().rules_version_problems(tmp_path)
    assert len(problems) == 1 and "0.10.1" in problems[0] and "0.10.2" in problems[0]


# --- Latin to Cyrillic: e after a vowel is э -----------------------------------
#
# A bare e (not part of ye) was э only at the start of a word, so poeziya came
# out as поезия and aeroport as аеропорт. After a vowel it is now э as well,
# except before v: surnames romanized the Russian way keep their Cyrillic
# form (Aliev -> Алиев).

E_AFTER_A_VOWEL = [
    ("aeroport", "аэропорт"),
    ("poeziya", "поэзия"),
    ("POEZIYA", "ПОЭЗИЯ"),
    ("duel", "дуэл"),
    ("koeffitsiyent", "коэффициент"),
    ("reemigratsiya", "реэмиграция"),
    ("siluet", "силуэт"),
    ("Rafael", "Рафаэл"),
    ("EEG", "ЭЭГ"),
    ("Aliev", "Алиев"),         # before v: е, as before
    ("Alievning", "Алиевнинг"),
    ("Alieva", "Алиева"),
    ("Kiev", "Киев"),
    ("tezda", "тезда"),         # after a consonant: е, as before
    ("ekran", "экран"),         # at the start of a word: э, as before
    ("poyezd", "поезд"),        # ye: е, as before
    ("teatr", "театр"),
]


@pytest.mark.parametrize("latin,cyrillic", E_AFTER_A_VOWEL)
def test_e_after_a_vowel_latin_1995_to_cyrillic(latin, cyrillic):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == cyrillic
    assert convert(latin.upper(), source=LATIN_1995, target=CYRILLIC) == cyrillic.upper()


def test_e_after_a_vowel_latin_2026_to_cyrillic():
    assert convert("poeziya", source=LATIN_2026, target=CYRILLIC) == "поэзия"
    assert convert("Poeziya", source=LATIN_2026, target=CYRILLIC) == "Поэзия"


def test_e_after_a_vowel_round_trip():
    latin = convert("поэзия", source=CYRILLIC, target=LATIN_1995)
    assert latin == "poeziya"
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == "поэзия"


# --- Cyrillic to Latin: ь before о is y -----------------------------------------
#
# ь was always dropped, so бульон came out as bulon. Before о it is y, as the
# Latin spelling writes these loanwords: bulyon, pavilyon. Elsewhere it is
# still dropped.

SOFT_SIGN_BEFORE_O = [
    # (cyrillic, latin_1995, latin_2026)
    ("бульон", "bulyon", "bulyon"),
    ("Бульон", "Bulyon", "Bulyon"),
    ("БУЛЬОН", "BULYON", "BULYON"),
    ("павильон", "pavilyon", "pavilyon"),
    ("почтальонлар", "pochtalyonlar", "poçtalyonlar"),
    ("медальон", "medalyon", "medalyon"),
    ("альбом", "albom", "albom"),        # not before о: dropped, as before
]


@pytest.mark.parametrize("cyrillic,latin_1995,latin_2026", SOFT_SIGN_BEFORE_O)
def test_soft_sign_before_o_is_y(cyrillic, latin_1995, latin_2026):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin_1995
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_2026) == latin_2026


def test_soft_sign_before_o_normalize():
    assert normalize("бульон") == normalize("bulyon") == "bulyon"


# --- case per letter unit: MChJ, AQSh, ToshDU -------------------------------------
#
# Case was decided for the whole word: all caps, an initial capital, or
# lowercase. MChJ is not all caps -- its h is lowercase -- so it came out as
# Mçj, AQSh as Aqş and ToshDU as Toşdu. Now the h after a capital S or C is a
# capital when the word has another capital (MChJ, AQSh; not Shahar), a word is
# split where a lowercase letter is followed by a capital (Tosh|DU, Oʻz|MU),
# and a word with irregular case keeps it letter by letter when the output is
# as long as the input.

CASE_UNITS = [
    # (latin_1995, latin_2026, cyrillic)
    ("MChJ", "MÇJ", "МЧЖ"),
    ("AQSh", "AQŞ", "АҚШ"),
    ("ToshDU", "ToşDU", "ТошДУ"),
    ("OʻzMU", "ÖzMU", "ЎзМУ"),
    ("Shahar", "Şahar", "Шаҳар"),      # an initial capital, as before
    ("SHAHAR", "ŞAHAR", "ШАҲАР"),      # all caps, as before
    ("shahar", "şahar", "шаҳар"),      # lowercase, as before
    ("ShAHAR", "ŞAHAR", "ШАҲАР"),
    ("OʻzBEKISTON", "ÖzBEKISTON", "ЎзБЕКИСТОН"),
]


@pytest.mark.parametrize("latin_1995,latin_2026,cyrillic", CASE_UNITS)
def test_case_is_kept_per_letter_unit(latin_1995, latin_2026, cyrillic):
    # protect=False: this is the conversion itself. ToshDU is also a token
    # until Uzbek abbreviations are taken out of the token rule.
    def from_1995(target):
        return convert(latin_1995, source=LATIN_1995, target=target, protect=False)

    assert from_1995(LATIN_2026) == latin_2026
    assert from_1995(CYRILLIC) == cyrillic
    assert from_1995(LATIN_1995) == latin_1995


@pytest.mark.parametrize(
    "text,latin_2026,cyrillic",
    [
        ("MChJ", "MÇJ", "МЧЖ"),
        ("AQSh va BMT", "AQŞ va BMT", "АҚШ ва БМТ"),
        ("«AKADEMTECH» MChJ", "«AKADEMTEÇ» MÇJ", "«АКАДЕМТЕЧ» МЧЖ"),
        ("OʻzMU talabasi", "ÖzMU talabasi", "ЎзМУ талабаси"),
        ("QoʻqonDPI", "QöqonDPI", "ҚўқонДПИ"),  # the turned comma stays with its o
    ],
)
def test_to_latin_and_to_cyrillic_keep_the_case_units(text, latin_2026, cyrillic):
    assert to_latin(text) == latin_2026
    assert to_cyrillic(text) == cyrillic
    assert to_latin(text, variant=LATIN_1995) == text


@pytest.mark.parametrize(
    "cyrillic,latin_1995,latin_2026",
    [
        ("ТошДУ ва ЎзМУ", "ToshDU va OʻzMU", "ToşDU va ÖzMU"),
        ("ЎзБЕКИСТОН", "OʻzBEKISTON", "ÖzBEKISTON"),
        ("Тошкент", "Toshkent", "Toşkent"),
    ],
)
def test_cyrillic_case_units(cyrillic, latin_1995, latin_2026):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin_1995
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_2026) == latin_2026
    assert convert(cyrillic, source=CYRILLIC, target=CYRILLIC) == cyrillic


def test_the_h_of_sh_is_a_capital_only_beside_another_capital():
    # In latin_2026, Sh is s + h. With no other capital the word has an
    # initial capital, so the separator and the h stay lowercase.
    assert convert("Sh", source=LATIN_2026, target=LATIN_1995) == "Sʼh"
    assert convert("AQSh", source=LATIN_1995, target=LATIN_2026) == "AQŞ"


def test_a_caseless_mark_does_not_break_all_caps():
    assert convert("MAʼNO", source=LATIN_1995, target=CYRILLIC) == "МАЪНО"
    assert convert("SHEʼR", source=LATIN_2026, target=CYRILLIC) == "СҲЕЪР"


def test_irregular_case_is_copied_letter_by_letter_when_the_length_is_kept():
    assert convert("McDonald", source=LATIN_1995, target=LATIN_1995, protect=False) == "McDonald"
    # A mark without case takes the case of the letter before it: ʼ -> Ъ.
    assert convert("MAʼNo", source=LATIN_1995, target=CYRILLIC, protect=False) == "МАЪНо"


def test_known_limitation_cyrillic_and_2026_abbreviations_come_out_all_caps():
    """МЧЖ and MÇJ have one letter for Ch; 1995 writes MChJ, but nothing in the
    letters says so (see the README)."""
    assert convert("МЧЖ", source=CYRILLIC, target=LATIN_1995) == "MCHJ"
    assert convert("MÇJ", source=LATIN_2026, target=LATIN_1995) == "MCHJ"


# The golden inputs for case units, numbers with a suffix and Uzbek
# abbreviations: (text, second tag, to_cyrillic, to_latin_1995, to_latin_2026,
# to_ascii); None is the input itself. In Тошкент ŞAHAR the 2026 word is not
# converted: the text is read as Cyrillic as a whole.
CASE_UNIT_INPUTS = {
    "c1168": ("10ta kitob, 2026yil, 100mg", "mixed", "10та китоб, 2026йил, 100мг", None, None, None),
    "c1169": ("ToshDU va SamDU", "latin_1995", "ТошДУ ва СамДУ", None, "ToşDU va SamDU", None),
    "c1170": ("ТошДУ ва ЎзМУ", "cyrillic", None, "ToshDU va OʻzMU", "ToşDU va ÖzMU", "ToshDU va OzMU"),
    "c1171": ("OʻzMU talabasi", "latin_1995", "ЎзМУ талабаси", None, "ÖzMU talabasi", "OzMU talabasi"),
    "c1172": ("ChatGPT, PhD, AkademID", "mixed", None, None, None, None),
    "c1173": ("MÇJ va AQŞ", "latin_2026", "МЧЖ ва АҚШ", "MCHJ va AQSH", None, "MCHJ va AQSH"),
    "c1174": ("Тошкент ŞAHAR", "mixed", None, "Toshkent ŞAHAR", "Toşkent ŞAHAR", "Toshkent SHAHAR"),
    "c1175": ("ShAHAR", "latin_1995", "ШАҲАР", None, "ŞAHAR", None),
}


def test_the_case_unit_inputs_are_golden_inputs():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    cases = {case["id"]: case for case in doc["cases"]}
    assert {i: (cases[i]["text"], cases[i]["tags"]) for i in CASE_UNIT_INPUTS} == {
        i: (row[0], ["protect-0.3.0", row[1]]) for i, row in CASE_UNIT_INPUTS.items()
    }


@pytest.mark.parametrize("case_id", sorted(CASE_UNIT_INPUTS))
def test_the_case_unit_inputs(case_id):
    text, _tag, *expected = CASE_UNIT_INPUTS[case_id]
    got = [to_cyrillic(text), to_latin(text, variant=LATIN_1995), to_latin(text), to_ascii(text)]
    assert got == [text if value is None else value for value in expected]


# --- abbreviations with a suffix: AQShda, ToshDUga; TerSh -------------------------
#
# A word is also split where a capital is followed by a lowercase letter, when
# the capitals before it are two letters or more: AQSh|da, MChJ|ning, АҚШ|да,
# Tosh|DU|ga; not Shahar. Each unit is cased by its own letters, so the Sh of
# Ter|Sh has no other capital beside it: an initial capital, not SH. An Uzbek
# abbreviation with a suffix is not a token (ToshDUga, SamDUda); ChatGPTda and
# AkademIDning do not have its shape and stay tokens.

SUFFIXED_ABBREVIATIONS = [
    # (latin_1995, latin_2026, cyrillic)
    ("AQShda", "AQŞda", "АҚШда"),
    ("MChJning", "MÇJning", "МЧЖнинг"),
    ("ToshDUga", "ToşDUga", "ТошДУга"),
    ("SamDUda", "SamDUda", "СамДУда"),
    ("TerSh", "TerŞ", "ТерШ"),
    ("Shahar", "Şahar", "Шаҳар"),      # a capital alone is not split off
    ("SHAHAR", "ŞAHAR", "ШАҲАР"),
]


@pytest.mark.parametrize("latin_1995,latin_2026,cyrillic", SUFFIXED_ABBREVIATIONS)
def test_an_abbreviation_with_a_suffix_keeps_its_case(latin_1995, latin_2026, cyrillic):
    def from_1995(target, **kw):
        return convert(latin_1995, source=LATIN_1995, target=target, **kw)

    assert from_1995(LATIN_2026) == from_1995(LATIN_2026, protect=False) == latin_2026
    assert from_1995(CYRILLIC) == from_1995(CYRILLIC, protect=False) == cyrillic
    assert from_1995(LATIN_1995) == from_1995(LATIN_1995, protect=False) == latin_1995


@pytest.mark.parametrize(
    "cyrillic,latin_2026,latin_1995",
    [
        # AQSHda and MCHJning: the known limitation of МЧЖ and MÇJ, which have
        # one letter for Ch; the official 1995 spelling is AQShda, MChJning.
        ("АҚШда", "AQŞda", "AQSHda"),
        ("МЧЖнинг", "MÇJning", "MCHJning"),
    ],
)
def test_a_cyrillic_abbreviation_with_a_suffix(cyrillic, latin_2026, latin_1995):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_2026) == latin_2026
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin_1995
    assert convert(cyrillic, source=CYRILLIC, target=CYRILLIC) == cyrillic


def test_each_unit_is_cased_by_its_own_letters():
    # Ter|Sh: no capital in Sh besides the S, so its h is lowercase. Read as
    # 2026, Sh is s + h and takes the separator.
    assert convert("TerSh", source=LATIN_1995, target=LATIN_1995) == "TerSh"
    assert convert("TerSh", source=LATIN_2026, target=LATIN_1995) == "TerSʼh"


@pytest.mark.parametrize("word", ["ChatGPTda", "AkademIDning"])
def test_a_token_with_a_suffix_stays_as_it_is(word):
    assert to_latin(word) == to_latin(word, variant=LATIN_1995) == to_cyrillic(word) == word
