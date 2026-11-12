"""validate: what in a text does not belong to the orthography it is meant to be in;
migration_report: what converting a latin_1995 text to latin_2026 does to it."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, RULES_VERSION, convert, migration_report, validate
from akademtranslit.checks import CODES
from akademtranslit.tables import APOSTROPHE_VARIANTS

GOLDEN_INPUTS = Path(__file__).resolve().parent.parent / "golden" / "inputs.json"

# Characters that look like others or do not show, by code point.
O_MACRON = chr(0x014D)       # LATIN SMALL LETTER O WITH MACRON
S_COMMA = chr(0x0219)        # LATIN SMALL LETTER S WITH COMMA BELOW
CYRILLIC_IE = chr(0x0435)    # CYRILLIC SMALL LETTER IE
LATIN_O = chr(0x006F)        # LATIN SMALL LETTER O
SOFT_HYPHEN = chr(0x00AD)    # SOFT HYPHEN
COMBINING_DIAERESIS = chr(0x0308)
O_ACUTE = chr(0x00D3)        # LATIN CAPITAL LETTER O WITH ACUTE
G_ACUTE = chr(0x01F5)        # LATIN SMALL LETTER G WITH ACUTE


def _golden_cases():
    return json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))["cases"]


# --- the cases --------------------------------------------------------------------

CASES = [
    # (text, orthography, findings)
    ("Oʻzbekiston Respublikasi", LATIN_2026, [(0, 11, "latin-1995-word", "Özbekiston")]),
    ("Toshkent shahri", LATIN_2026, [(0, 8, "digraph", "Toşkent"), (9, 15, "digraph", "şahri")]),
    ("Isʼhoq va Ishoq", LATIN_2026, [(0, 6, "latin-1995-word", "Ishoq"), (10, 15, "digraph", "Işoq")]),
    (
        "Özbekiston va Toşkent",
        LATIN_1995,
        [(0, 10, "latin-2026-word", "Oʻzbekiston"), (14, 21, "latin-2026-word", "Toshkent")],
    ),
    (
        "o'zbek, ma'no, oʼzbek, maʻno",
        LATIN_1995,
        [
            (0, 6, "mark-form", "oʻzbek"),
            (8, 13, "mark-form", "maʼno"),
            (15, 21, "wrong-mark", "oʻzbek"),
            (23, 28, "wrong-mark", "maʼno"),
        ],
    ),
    (O_ACUTE + "zbekiston, " + G_ACUTE + "oza", LATIN_1995,
     [(0, 10, "look-alike", "Oʻzbekiston"), (12, 16, "look-alike", "gʻoza")]),
    (O_ACUTE + "zbekiston, " + G_ACUTE + "oza", LATIN_2026,
     [(0, 10, "look-alike", "Özbekiston"), (12, 16, "look-alike", "ğoza")]),
    ("T" + O_MACRON + "ky" + O_MACRON + ", To" + S_COMMA + "kent", LATIN_2026,
     [(0, 5, "letter-form", "Tökyö"), (7, 14, "letter-form", "Toşkent")]),
    ("T" + O_MACRON + "ky" + O_MACRON + ", To" + S_COMMA + "kent", LATIN_1995,
     [(0, 5, "letter-form", "Toʻkyoʻ"), (7, 14, "letter-form", "Toshkent")]),
    ("Тошкент ŞAHAR, Google", CYRILLIC, [(8, 13, "latin-2026-word", "ШАҲАР")]),
    ("Тошкент oʻrdak", CYRILLIC, [(8, 14, "latin-1995-word", "ўрдак")]),
    ("Toshk" + CYRILLIC_IE + "nt va Т" + LATIN_O + "шкент", LATIN_1995,
     [(0, 8, "mixed-script", "Toshkent"), (12, 19, "mixed-script", "Тошкент")]),
    ("Tosh" + SOFT_HYPHEN + "kent", LATIN_1995, [(4, 5, "invisible", "")]),
    ("O" + COMBINING_DIAERESIS + "zbekiston", LATIN_2026, [(0, 2, "decomposed", "Ö")]),
    ("Тошкент шаҳри", LATIN_1995, [(0, 7, "cyrillic-word", "Toshkent"), (8, 13, "cyrillic-word", "shahri")]),
    ("Manba: https://shahar.uz, ChatGPT", LATIN_2026, []),  # protected
    ("ʻ", LATIN_1995, []),  # only a mark: not a word
    ("AQSh, MChJ, TerSh", LATIN_1995, []),
    ("AQŞ, MÇJ, TerŞ, Ishoq", LATIN_2026, [(16, 21, "digraph", "Işoq")]),
    # An sh beside a 2026 letter in 1995 text stays sh (not sʼh).
    ("Qashqadaryö", LATIN_1995, [(0, 11, "latin-2026-word", "Qashqadaryoʻ")]),
    # s with comma below is a letter form, not a 2026 letter, in 1995 text.
    ("To" + S_COMMA + "kent", LATIN_1995, [(0, 7, "letter-form", "Toshkent")]),
    ("", LATIN_1995, []),
]


@pytest.mark.parametrize("text,orthography,findings", CASES)
def test_validate(text, orthography, findings):
    assert validate(text, orthography) == findings


def test_the_found_text_is_where_it_says():
    for text, orthography, findings in CASES:
        for start, end, code, _ in findings:
            assert 0 <= start < end <= len(text), (text, code)


def test_a_cyrillic_mixed_word_with_no_twin_has_no_suggestion():
    word = "Тош" + "k" + "ент"
    assert validate(word, CYRILLIC) == [(0, 7, "mixed-script", None)]


def test_other_latin_words_are_not_findings_in_cyrillic_text():
    assert validate("Google ва Telegram, Toshkent", CYRILLIC) == []


def test_a_cyrillic_accent_is_not_decomposed():
    # NFC leaves Cyrillic o and U+0301 COMBINING ACUTE ACCENT as they are.
    assert validate("То" + chr(0x0301) + "шкент", CYRILLIC) == []


# --- the arguments ----------------------------------------------------------------


@pytest.mark.parametrize("value", ["auto", "klingon", "uz-Latn-1990", None])
def test_an_unknown_orthography_is_an_error(value):
    with pytest.raises(ValueError, match="^unknown orthography: .*; expected one of "):
        validate("Toshkent", value)


def test_a_tag_is_read_as_its_orthography():
    text = "Oʻzbekiston va Toshkent shahri"
    assert validate(text, "uz-Latn-2026") == validate(text, LATIN_2026)
    assert validate(text, "uz-Cyrl") == validate(text, CYRILLIC)


def test_uz_warns_and_is_read_as_latin_1995():
    with pytest.warns(FutureWarning, match="'uz' names no orthography"):
        assert validate("Тошкент oʻrdak", "uz") == validate("Тошкент oʻrdak", LATIN_1995)


def test_the_warning_points_at_the_caller():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        validate("Toshkent", "uz")
    assert [Path(w.filename).name for w in caught] == [Path(__file__).name]


def test_protect_false_checks_the_words_of_a_url():
    text = "Manba: https://shahar.uz"
    assert validate(text, LATIN_2026) == []
    assert validate(text, LATIN_2026, protect=False) == [(15, 21, "digraph", "şahar")]


def test_protect_takes_only_true_false_or_a_protect():
    with pytest.raises(ValueError, match="protect must be"):
        validate("Toshkent", LATIN_1995, protect="yes")


def test_protect_is_keyword_only():
    with pytest.raises(TypeError):
        validate("Toshkent", LATIN_1995, False)


# --- on the golden inputs ---------------------------------------------------------


def test_the_codes():
    assert CODES == (
        "invisible", "decomposed", "mixed-script", "cyrillic-word", "latin-1995-word",
        "latin-2026-word", "look-alike", "letter-form", "digraph", "wrong-mark", "mark-form",
    )


@pytest.mark.parametrize("orthography", [CYRILLIC, LATIN_1995, LATIN_2026])
def test_the_findings_on_the_golden_inputs_are_well_formed(orthography):
    for case in _golden_cases():
        text = case["text"]
        findings = validate(text, orthography)
        assert findings == sorted(findings, key=lambda finding: finding[:3]), case["id"]
        for start, end, code, suggestion in findings:
            assert 0 <= start < end <= len(text), case["id"]
            assert code in CODES, case["id"]
            assert suggestion is None or isinstance(suggestion, str), case["id"]


@pytest.mark.parametrize("orthography", [LATIN_1995, LATIN_2026])
def test_a_golden_input_without_findings_is_its_own_conversion(orthography):
    # The one exception is a lone mark: convert writes it as the tutuq
    # belgisi, validate does not take it for a word.
    changed = [
        case["id"] for case in _golden_cases()
        if not validate(case["text"], orthography) and convert(case["text"], orthography, orthography) != case["text"]
    ]
    assert changed == ["c0339"]


@pytest.mark.parametrize("orthography", [LATIN_1995, LATIN_2026])
def test_on_the_golden_inputs_a_mark_finding_changes_only_marks(orthography):
    # The table of codes is complete: a word that its suggestion changes in
    # anything but a mark has an earlier code.
    marks = frozenset(APOSTROPHE_VARIANTS)
    wrong = []
    for case in _golden_cases():
        for start, end, code, suggestion in validate(case["text"], orthography):
            if code in ("wrong-mark", "mark-form"):
                word = case["text"][start:end]
                changed = [(a, b) for a, b in zip(word, suggestion) if a != b]
                if len(word) != len(suggestion) or not changed or any(a not in marks for a, _ in changed):
                    wrong.append((case["id"], word, suggestion))
    assert wrong == []


# --- migration_report -------------------------------------------------------------

REPORTS = [
    # (text, words, changed, protected, round_trip, check, result)
    (
        "Mirzo Ulugʻbek nomidagi Oʻzbekiston Milliy universiteti", 6, 2, 0, True, [],
        "Mirzo Uluğbek nomidagi Özbekiston Milliy universiteti",
    ),
    (
        "Isʼhoq va asʼhob", 3, 2, 0, True,
        [(0, 6, "separator", "Ishoq"), (10, 16, "separator", "ashob")],
        "Ishoq va ashob",
    ),
    ("Toşkent va Toshkent", 3, 1, 0, False, [(0, 7, "latin-2026-word", "Toshkent")], "Toşkent va Toşkent"),
    # A known limitation (README): MChJ and AQSh come back all capitals.
    (
        "MChJning va AQSh", 3, 2, 0, False,
        [(0, 8, "round-trip", "MCHJning"), (12, 16, "round-trip", "AQSH")],
        "MÇJning va AQŞ",
    ),
    ("ma'no https://shahar.uz", 1, 0, 1, True, [(0, 5, "mark-form", "maʼno")], "maʼno https://shahar.uz"),
    ("", 0, 0, 0, True, [], ""),
]


@pytest.mark.parametrize("text,words,changed,protected,round_trip,check,result", REPORTS)
def test_migration_report(text, words, changed, protected, round_trip, check, result):
    assert migration_report(text) == {
        "words": words,
        "changed": changed,
        "protected": protected,
        "round_trip": round_trip,
        "rules_version": RULES_VERSION,
        "check": check,
        "result": result,
    }


def test_the_keys_of_the_report_are_in_order():
    assert list(migration_report("Toshkent")) == [
        "words", "changed", "protected", "round_trip", "rules_version", "check", "result"
    ]


def test_the_result_is_the_conversion():
    text = "Oʻzbekiston Respublikasi, https://shahar.uz"
    assert migration_report(text)["result"] == convert(text, LATIN_1995, LATIN_2026)
    assert migration_report(text, protect=False)["result"] == convert(text, LATIN_1995, LATIN_2026, protect=False)


def test_protect_false_counts_and_checks_the_words_of_a_url():
    report = migration_report("ma'no https://shahar.uz", protect=False)
    assert (report["words"], report["changed"], report["protected"]) == (4, 1, 0)
    assert report["check"] == [(0, 5, "mark-form", "maʼno")]


def test_a_lone_mark_is_not_a_word():
    assert migration_report("ʻ")["words"] == 0


def test_a_word_with_a_finding_gets_no_other():
    # Toşkent is a latin-2026-word; it does not also come back as Toshkent.
    report = migration_report("Toşkent")
    assert report["check"] == [(0, 7, "latin-2026-word", "Toshkent")]


def test_the_check_of_the_golden_inputs_is_validate_and_two_codes():
    for case in _golden_cases():
        report = migration_report(case["text"])
        found = validate(case["text"], LATIN_1995)
        assert [f for f in report["check"] if f[2] in CODES] == found, case["id"]
        assert report["check"] == sorted(report["check"], key=lambda finding: finding[:3]), case["id"]
        assert {f[2] for f in report["check"]} - set(CODES) <= {"round-trip", "separator"}, case["id"]
