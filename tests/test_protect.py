"""Protected spans: what segments() finds and what Protect turns on and off."""

from __future__ import annotations

import copy
import hashlib
import json
import pickle
from pathlib import Path

import pytest

from akademtranslit import Protect, segments

REPO = Path(__file__).resolve().parent.parent
GOLDEN_INPUTS = REPO / "golden" / "inputs.json"

# Invisible characters, built from their code points so the source shows them.
SOFT_HYPHEN = chr(0x00AD)
ZERO_WIDTH_SPACE = chr(0x200B)
CYRILLIC_O = chr(0x041E)  # looks like the Latin O

# The inputs added to the golden vectors for protected spans.
NEW_INPUTS = {
    "c1140": "Batafsil: https://gazeta.uz/oz/2026/11/05/shahar-chiroqlari/ manzilida.",
    "c1141": "www.shahar.uz saytida",
    "c1142": "gazeta.uz va kun.uz",
    "c1143": "info@shahar.uz ga yozing",
    "c1144": "doi:10.1234/chashma.2026.01 maqolasi",
    "c1145": "https://doi.org/10.5555/shox-2026",
    "c1146": "10.1007/s00415-026-12345-6 raqamli maqola",
    "c1147": "{count} ta kitob",
    "c1148": "{count, plural, one {# ta shahar} other {# ta shahar}}",
    "c1149": "Salom, {name}! Sizda {n, number} ta xabar bor",
    "c1150": "%s ta fayl, %(soni)d ta shahar",
    "c1151": '<b>Shahar</b> <a href="https://shahar.uz">havola</a>',
    "c1152": "&nbsp;choy &amp; shakar",
    "c1153": "SpO2 92%, pH 7,35, PaCO2 45 mmHg",
    "c1154": "McDonald's va iPhone, YouTube",
    "c1155": "AkademTech va AslMatn",
    "c1156": "«AKADEMTECH» MChJ",
    "c1157": "AQSh va BMT",
    "c1158": "B12 vitamini va eGFR",
    "c1159": "/home/user/shahar.txt fayli",
    "c1160": "hisobot_shahar.docx faylini oching",
    "c1161": "kirill/lotin yozuvi",
    "c1162": "Тошкент https://toshkent.uz/шаҳар",
    "c1163": "To'raqo'rg'on tumani",
    "c1164": "Tosh" + SOFT_HYPHEN + "kent",
    "c1165": "shahar" + ZERO_WIDTH_SPACE + " choy",
    "c1166": "a < b va c > d",
    "c1167": "{shahar_soni",
}


def test_the_new_inputs_are_golden_inputs():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    cases = {case["id"]: case for case in doc["cases"]}
    assert {i: cases[i]["text"] for i in NEW_INPUTS} == NEW_INPUTS
    assert all("protect-0.3.0" in cases[i]["tags"] for i in NEW_INPUTS)


def protected(text, protect=True):
    """The protected pieces of ``text``, in order, with their kinds."""
    return [(piece, kind) for piece, kind in segments(text, protect) if kind is not None]


def all_inputs():
    """Every golden input, then the new ones, without repeats."""
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    texts = [case["text"] for case in doc["cases"]]
    seen = set(texts)
    return texts + [text for text in NEW_INPUTS.values() if text not in seen]


# --- segments: the pieces put back together are the text ---------------------------


def test_the_pieces_join_to_the_text_on_every_input():
    broken = [text for text in all_inputs() if "".join(p for p, _ in segments(text)) != text]
    assert broken == []


def test_no_piece_is_empty_and_neighbours_differ_in_kind():
    bad = []
    for text in all_inputs():
        pieces = segments(text)
        if any(piece == "" for piece, _ in pieces):
            bad.append((text, "empty piece"))
        if any(a[1] == b[1] for a, b in zip(pieces, pieces[1:])):
            bad.append((text, "neighbours of one kind"))
    assert bad == []


def test_every_kind_is_a_known_one():
    kinds = {kind for text in all_inputs() for _, kind in segments(text)}
    assert kinds <= {None, "url", "email", "doi", "markup", "placeholder", "path", "term", "token"}


def test_empty_text():
    assert segments("") == []


def test_text_with_nothing_to_protect_is_one_piece():
    assert segments("Toshkent shahri, 2026-yil") == [("Toshkent shahri, 2026-yil", None)]


# --- url -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,url",
    [
        (NEW_INPUTS["c1140"], "https://gazeta.uz/oz/2026/11/05/shahar-chiroqlari/"),
        ("http://shahar.uz/a?b=1&c=2#d", "http://shahar.uz/a?b=1&c=2#d"),
        ("ftp://fayl.shahar.uz/hisobot.zip", "ftp://fayl.shahar.uz/hisobot.zip"),
        (NEW_INPUTS["c1141"], "www.shahar.uz"),
        ("kun.uz/oz/news/2026", "kun.uz/oz/news/2026"),
        ("HTTPS://SHAHAR.UZ/YANGILIK", "HTTPS://SHAHAR.UZ/YANGILIK"),
        ("Rasmiy sayt: gov.uz.", "gov.uz"),
        ("Тошкент https://toshkent.uz/шаҳар", "https://toshkent.uz/шаҳар"),
    ],
)
def test_url(text, url):
    assert protected(text) == [(url, "url")]


def test_bare_domains_from_the_list():
    assert protected(NEW_INPUTS["c1142"]) == [("gazeta.uz", "url"), ("kun.uz", "url")]
    for tld in ("uz", "com", "org", "net", "ru", "info", "edu", "gov", "io"):
        assert protected(f"sayt.{tld} manzili") == [(f"sayt.{tld}", "url")], tld


@pytest.mark.parametrize(
    "text,url",
    [
        ("Manba: https://shahar.uz.", "https://shahar.uz"),
        ("Manba: https://shahar.uz, keyin", "https://shahar.uz"),
        ("(https://shahar.uz/yangilik)", "https://shahar.uz/yangilik"),
        ("https://uz.wikipedia.org/wiki/Shahar_(film)", "https://uz.wikipedia.org/wiki/Shahar_(film)"),
        ("(https://uz.wikipedia.org/wiki/Shahar_(film))", "https://uz.wikipedia.org/wiki/Shahar_(film)"),
        ("«https://shahar.uz»", "https://shahar.uz"),
        ('"https://shahar.uz",', "https://shahar.uz"),
        ("Ochdingizmi https://shahar.uz?!", "https://shahar.uz"),
        ("https://shahar.uz/a;", "https://shahar.uz/a"),
        ("'gazeta.uz/oz/'", "gazeta.uz/oz/"),
    ],
)
def test_url_leaves_trailing_punctuation_out(text, url):
    assert protected(text) == [(url, "url")]


@pytest.mark.parametrize(
    "text",
    [
        "Toshkent.",
        "shahar.uzbek",
        "shahar.tj sayti",
        "5.5 foiz",
        "www. va https:// yolgʻiz",
        "Toshkent.Uzoq",
    ],
)
def test_not_a_url(text):
    assert [kind for _, kind in protected(text)] == []


def test_a_domain_starts_where_its_word_starts_and_never_after_an_at_sign():
    assert protected("2gazeta.uz") == [("2gazeta.uz", "url")]
    assert protected("xgazeta.uz") == [("xgazeta.uz", "url")]
    assert protected("info@shahar.uz") == [("info@shahar.uz", "email")]
    assert protected("info@shahar.uz", Protect(emails=False)) == []


# --- email -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,email",
    [
        (NEW_INPUTS["c1143"], "info@shahar.uz"),
        ("Yozing: ism.familiya+uz@pochta.example.org.", "ism.familiya+uz@pochta.example.org"),
        ("mailto:info@shahar.uz", "mailto:info@shahar.uz"),
        ("MAILTO:Info@Shahar.UZ", "MAILTO:Info@Shahar.UZ"),
        ("Ёзинг: info@example.org", "info@example.org"),
        ("a_b%c-d@x-y.travel", "a_b%c-d@x-y.travel"),
    ],
)
def test_email(text, email):
    assert protected(text) == [(email, "email")]


@pytest.mark.parametrize("text", ["@shahar", "info@shahar", "info@shahar.u", "info @shahar.uz"])
def test_not_an_email(text):
    assert [kind for _, kind in protected(text) if kind == "email"] == []


# --- doi -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,doi",
    [
        (NEW_INPUTS["c1144"], "doi:10.1234/chashma.2026.01"),
        (NEW_INPUTS["c1146"], "10.1007/s00415-026-12345-6"),
        ("DOI:10.1234/abcd.5678", "DOI:10.1234/abcd.5678"),
        ("(10.1234/abcd.5678).", "10.1234/abcd.5678"),
        ("10.123456789/x", "10.123456789/x"),
    ],
)
def test_doi(text, doi):
    assert protected(text) == [(doi, "doi")]


def test_doi_prefix_with_a_space_is_not_part_of_it():
    assert segments("DOI: 10.1234/abcd.5678") == [
        ("DOI: ", None),
        ("10.1234/abcd.5678", "doi"),
    ]


def test_a_doi_in_a_url_is_the_url():
    assert protected(NEW_INPUTS["c1145"]) == [("https://doi.org/10.5555/shox-2026", "url")]


@pytest.mark.parametrize("text", ["10.123/abc", "10.1234567890/abc", "110.1234/abc", "10.1234/", "10.1234 /abc"])
def test_not_a_doi(text):
    assert [kind for _, kind in protected(text) if kind == "doi"] == []


# --- markup ----------------------------------------------------------------------


def test_tags_are_protected_and_the_text_between_them_is_not():
    assert segments(NEW_INPUTS["c1151"]) == [
        ("<b>", "markup"),
        ("Shahar", None),
        ("</b>", "markup"),
        (" ", None),
        ('<a href="https://shahar.uz">', "markup"),
        ("havola", None),
        ("</a>", "markup"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        "<br>",
        "<br/>",
        "<br />",
        '<img src="shahar.png" alt="a > b">',
        "<p class='shahar'>",
        "<!-- izoh: a > b -->",
        "<!DOCTYPE html>",
        "&nbsp;",
        "&amp;",
        "&#123;",
        "&#x1F;",
    ],
)
def test_markup(text):
    assert segments(text) == [(text, "markup")]


def test_entities():
    assert segments(NEW_INPUTS["c1152"]) == [
        ("&nbsp;", "markup"),
        ("choy ", None),
        ("&amp;", "markup"),
        (" shakar", None),
    ]


@pytest.mark.parametrize("text", [NEW_INPUTS["c1166"], "x <3 y", "choy & shakar", "AT&T", "&;", "&#;"])
def test_not_markup(text):
    assert protected(text) == []


# --- placeholder -----------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        (NEW_INPUTS["c1147"], [("{count}", "placeholder")]),
        ("{0} ta", [("{0}", "placeholder")]),
        ("{ name }", [("{ name }", "placeholder")]),
        (NEW_INPUTS["c1149"], [("{name}", "placeholder"), ("{n, number}", "placeholder")]),
        ("{d, date, short}", [("{d, date, short}", "placeholder")]),
        ("{n, number, ::currency/UZS}", [("{n, number, ::currency/UZS}", "placeholder")]),
        (NEW_INPUTS["c1150"], [("%s", "placeholder"), ("%(soni)d", "placeholder")]),
        ("%1$s va %2$d", [("%1$s", "placeholder"), ("%2$d", "placeholder")]),
        ("%-5.2f soʻm", [("%-5.2f", "placeholder")]),
        ("%sga yuborildi", [("%s", "placeholder")]),
        ("{{ shahar }} va {{shahar.nomi}}", [("{{ shahar }}", "placeholder"), ("{{shahar.nomi}}", "placeholder")]),
    ],
)
def test_placeholder(text, expected):
    assert protected(text) == expected


def test_plural_message_text_is_not_protected():
    assert segments(NEW_INPUTS["c1148"]) == [
        ("{count, plural, one {#", "placeholder"),
        (" ta shahar", None),
        ("} other {#", "placeholder"),
        (" ta shahar", None),
        ("}}", "placeholder"),
    ]


def test_select_selectordinal_offset_and_explicit_values():
    assert segments("{jins, select, ayol {U shaharda} other {Ular shaharda}}") == [
        ("{jins, select, ayol {", "placeholder"),
        ("U shaharda", None),
        ("} other {", "placeholder"),
        ("Ular shaharda", None),
        ("}}", "placeholder"),
    ]
    assert segments("{n, selectordinal, one {#-shahar} other {#-shahar}}") == [
        ("{n, selectordinal, one {#", "placeholder"),
        ("-shahar", None),
        ("} other {#", "placeholder"),
        ("-shahar", None),
        ("}}", "placeholder"),
    ]
    assert segments("{n, plural, offset:1 =0 {hech kim} other {# kishi}}") == [
        ("{n, plural, offset:1 =0 {", "placeholder"),
        ("hech kim", None),
        ("} other {#", "placeholder"),
        (" kishi", None),
        ("}}", "placeholder"),
    ]


def test_hash_is_text_in_a_select_outside_a_plural():
    assert segments("{x, select, other {#1 shahar}}") == [
        ("{x, select, other {", "placeholder"),
        ("#1 shahar", None),
        ("}}", "placeholder"),
    ]


def test_nested_arguments():
    assert segments("{n, plural, one {{name} shaharda} other {{name}, {d, date} # kishi}}") == [
        ("{n, plural, one {{name}", "placeholder"),
        (" shaharda", None),
        ("} other {{name}", "placeholder"),
        (", ", None),
        ("{d, date}", "placeholder"),
        (" ", None),
        ("#", "placeholder"),
        (" kishi", None),
        ("}}", "placeholder"),
    ]
    assert segments("{a, select, x {{n, plural, one {# shahar} other {# shahar}}} other {yoʻq}}") == [
        ("{a, select, x {{n, plural, one {#", "placeholder"),
        (" shahar", None),
        ("} other {#", "placeholder"),
        (" shahar", None),
        ("}}} other {", "placeholder"),
        ("yoʻq", None),
        ("}}", "placeholder"),
    ]


def test_message_text_is_scanned_for_the_other_kinds():
    assert segments("{n, plural, one {# iPhone, https://shahar.uz} other {# ta}}") == [
        ("{n, plural, one {#", "placeholder"),
        (" ", None),
        ("iPhone", "token"),
        (", ", None),
        ("https://shahar.uz", "url"),
        ("} other {#", "placeholder"),
        (" ta", None),
        ("}}", "placeholder"),
    ]


@pytest.mark.parametrize(
    "text",
    [
        NEW_INPUTS["c1167"],
        "}shahar{",
        "{}",
        "{ }",
        "{shahar soni}",
        "{Toshkent, Samarqand}",
        "{n, plural, one {# ta}",
        "{n, plural, one {# ta} other}",
        "{n, plural}",
        "{n, number",
        "5,5%",
        "50%dan ortiq, 5%ga, 100%li",
        "{{ yopilmagan",
    ],
)
def test_not_a_placeholder(text):
    assert [kind for _, kind in protected(text) if kind == "placeholder"] == []


def test_an_unbalanced_brace_is_an_ordinary_character():
    assert segments("{shahar {name}") == [("{shahar ", None), ("{name}", "placeholder")]


def test_unbalanced_braces_stay_fast():
    text = "{n, plural, one {" * 2000 + "shahar"
    assert segments(text) == [(text, None)]


# --- path ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,path",
    [
        (NEW_INPUTS["c1159"], "/home/user/shahar.txt"),
        ("./skript.sh ni yurgizing", "./skript.sh"),
        ("../shahar/ papkasi", "../shahar/"),
        ("~/hujjatlar/shahar.md", "~/hujjatlar/shahar.md"),
        ("C:\\Users\\shahar\\hisobot.docx", "C:\\Users\\shahar\\hisobot.docx"),
        ("(/etc/hosts)", "/etc/hosts"),
        ("«/tmp/shahar»", "/tmp/shahar"),
        (NEW_INPUTS["c1160"], "hisobot_shahar.docx"),
        ("Shahar.PDF faylini", "Shahar.PDF"),
        ("jadval-2026.v2.xlsx.", "jadval-2026.v2.xlsx"),
    ],
)
def test_path(text, path):
    assert protected(text) == [(path, "path")]


@pytest.mark.parametrize(
    "text",
    [NEW_INPUTS["c1161"], "24/7", "va/yoki", "km/soat", "a / b", "hisobot.docs", "hisobot.pdfda", "/"],
)
def test_not_a_path(text):
    assert protected(text) == []


# --- term ------------------------------------------------------------------------


def test_term():
    protect = Protect(tokens=False, terms=("Toshkent",))
    assert segments("Toshkent va toshkent, Toshkentda", protect) == [
        ("Toshkent", "term"),
        (" va toshkent, Toshkentda", None),
    ]


def test_term_wins_over_token_on_the_same_span():
    assert segments("AslMatn va shahar", Protect(terms=("AslMatn",))) == [
        ("AslMatn", "term"),
        (" va shahar", None),
    ]


def test_the_longest_term_wins():
    protect = Protect(tokens=False, terms=("Akadem", "Akadem Tech"))
    assert protected("Akadem Tech va Akadem", protect) == [("Akadem Tech", "term"), ("Akadem", "term")]


def test_a_term_ends_at_an_apostrophe():
    assert protected("Toshkent'ning", Protect(terms=("Toshkent",))) == [("Toshkent", "term")]


# --- token -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "word",
    ["SpO2", "B12", "PaCO2", "H2O", "3D", "b12", "COVID19"]  # a letter and a digit
    + ["pH", "mmHg", "eGFR", "iPhone", "McDonald", "McDonald's", "AkademTech", "AslMatn", "YouTube"],
)
def test_token(word):
    assert segments(word) == [(word, "token")]


@pytest.mark.parametrize(
    "word",
    ["MChJ", "AQSh", "2026", "COVID", "Toshkent", "TOSHKENT", "toshkent", "ТошКент", "Sp" + CYRILLIC_O + "2"],
)
def test_not_a_token(word):
    assert segments(word) == [(word, None)]


@pytest.mark.parametrize("mark", ["ʻ", "ʼ", "’", "‘", "´", "ʹ", "'", "`"])
def test_a_word_with_o_or_g_and_an_apostrophe_is_uzbek(mark):
    for word in ("O{}zBEKISTON", "tO{}g{}", "To{}raQo{}rg{}on", "gO{}ZAL", "AG{}A"):
        word = word.replace("{}", mark)
        assert segments(word) == [(word, None)], word


def test_a_run_with_a_non_ascii_letter_is_not_a_token():
    assert segments("ÖzBEKISTON") == [("ÖzBEKISTON", None)]
    assert segments("iPhoneда") == [("iPhoneда", None)]  # да: Cyrillic U+0434 U+0430
    assert segments("SpO2ni") == [("SpO2ni", "token")]


def test_tokens_in_text():
    assert protected(NEW_INPUTS["c1153"]) == [
        ("SpO2", "token"),
        ("pH", "token"),
        ("PaCO2", "token"),
        ("mmHg", "token"),
    ]
    assert protected(NEW_INPUTS["c1154"]) == [
        ("McDonald's", "token"),
        ("iPhone", "token"),
        ("YouTube", "token"),
    ]
    assert protected(NEW_INPUTS["c1158"]) == [("B12", "token"), ("eGFR", "token")]
    assert protected("pH-metr va SpO2-ni") == [("pH", "token"), ("SpO2", "token")]


def test_sh_and_ch_after_a_capital_are_one_capital():
    """MChJ and AQSh are Uzbek abbreviations: the h is part of Ch and Sh."""
    assert protected(NEW_INPUTS["c1156"]) == []
    assert protected(NEW_INPUTS["c1157"]) == []
    assert segments("iCh") == [("iCh", "token")]
    assert segments("ShahAr") == [("ShahAr", "token")]


def test_known_limitation_mixed_case_uzbek_words_are_tokens():
    """A misspelled Uzbek word with mixed case, and an Uzbek abbreviation with
    five or more lowercase letters, are protected (see the README)."""
    assert segments("ToshKent") == [("ToshKent", "token")]
    assert segments("tOSHKENT") == [("tOSHKENT", "token")]
    assert segments("TermizDU") == [("TermizDU", "token")]


# --- numbers with a suffix and Uzbek abbreviations are not tokens -----------------
#
# Two shapes are taken out of the token rule: digits followed by lowercase
# letters only (10ta, 2026yil, 100mg -- a number with a suffix or a unit), and
# a capital, one to four lowercase letters and two or more capitals, Sh and Ch
# counted as one capital (ToshDU, SamDU, ToshPTI -- an Uzbek abbreviation),
# with lowercase letters after it if it has a suffix (ToshDUga, SamDUda).


@pytest.mark.parametrize(
    "word",
    ["10ta", "2026yil", "100mg", "5ga"]  # digits, then lowercase letters
    + ["ToshDU", "SamDU", "TerDU", "ToshPTI"]  # an Uzbek abbreviation
    + ["ToshDUga", "SamDUda"],  # an Uzbek abbreviation with a suffix
)
def test_a_number_with_a_suffix_or_an_uzbek_abbreviation_is_not_a_token(word):
    assert segments(word) == [(word, None)]


@pytest.mark.parametrize(
    "word",
    ["4G", "B12", "mp3", "SpO2"]  # letters and digits in another order
    + ["ChatGPT", "PhD", "AkademID", "McDonald", "iPhone", "YouTube", "eGFR", "mmHg"]
    + ["ChatGPTda", "AkademIDning"],  # with a suffix
)
def test_other_mixed_words_are_still_tokens(word):
    assert segments(word) == [(word, "token")]


@pytest.mark.parametrize(
    "text,cyrillic,latin_2026",
    [
        ("10ta kitob, 2026yil, 100mg", "10та китоб, 2026йил, 100мг", "10ta kitob, 2026yil, 100mg"),
        ("ToshDU va SamDU", "ТошДУ ва СамДУ", "ToşDU va SamDU"),
        ("TerDU, ToshPTI", "ТерДУ, ТошПТИ", "TerDU, ToşPTI"),
        ("ChatGPT, PhD, AkademID", "ChatGPT, PhD, AkademID", "ChatGPT, PhD, AkademID"),
    ],
)
def test_numbers_with_a_suffix_and_uzbek_abbreviations_are_converted(text, cyrillic, latin_2026):
    assert to_cyrillic(text) == cyrillic
    assert to_latin(text) == latin_2026
    assert to_latin(text, variant=LATIN_1995) == text


# --- which span wins -------------------------------------------------------------


def test_at_one_start_the_longest_wins():
    assert segments("iPhone.uz") == [("iPhone.uz", "url")]
    assert segments("McDonald@shahar.uz") == [("McDonald@shahar.uz", "email")]
    assert segments("iPhone.pdf") == [("iPhone.pdf", "path")]


def test_the_leftmost_wins():
    assert segments("<a href='/x'>") == [("<a href='/x'>", "markup")]
    assert segments("https://shahar.uz/{id}") == [("https://shahar.uz/{id}", "url")]
    assert segments("https://shahar.uz/hisobot.pdf") == [("https://shahar.uz/hisobot.pdf", "url")]


def test_the_input_is_not_normalised():
    decomposed = "https://o" + chr(0x0308) + "rdak.uz"
    assert segments(decomposed) == [(decomposed, "url")]


# --- turning kinds off -----------------------------------------------------------

EVERY_KIND = "https://shahar.uz info@shahar.uz 10.1234/abcd <b> {n} /tmp/x AslMatn pH"


def test_protect_false_and_protect_none_protect_nothing():
    assert segments(EVERY_KIND, False) == [(EVERY_KIND, None)]
    assert segments(EVERY_KIND, Protect.NONE) == [(EVERY_KIND, None)]


@pytest.mark.parametrize(
    "flag,kind",
    [
        ("urls", "url"),
        ("emails", "email"),
        ("dois", "doi"),
        ("markup", "markup"),
        ("placeholders", "placeholder"),
        ("paths", "path"),
        ("tokens", "token"),
    ],
)
def test_one_kind_off(flag, kind):
    every = [k for _, k in protected(EVERY_KIND)]
    assert [k for _, k in protected(EVERY_KIND, Protect(**{flag: False}))] == [
        k for k in every if k != kind
    ]


def test_every_kind_on_by_default():
    assert [k for _, k in protected(EVERY_KIND)] == [
        "url", "email", "doi", "markup", "placeholder", "path", "token", "token",
    ]
    assert [k for _, k in protected(EVERY_KIND, Protect(terms=("AslMatn",)))][-2] == "term"


@pytest.mark.parametrize("value", [1, 0, None, "yes", "True", Protect])
def test_protect_takes_only_true_false_or_a_protect(value):
    with pytest.raises(ValueError, match="protect"):
        segments("shahar", value)


# --- Protect ---------------------------------------------------------------------


def test_protect_defaults():
    p = Protect()
    assert (p.urls, p.emails, p.dois, p.placeholders, p.markup, p.paths, p.tokens) == (True,) * 7
    assert p.terms == ()


def test_protect_none():
    assert Protect.NONE == Protect(
        urls=False, emails=False, dois=False, placeholders=False, markup=False, paths=False, tokens=False
    )
    assert Protect.NONE.terms == ()


def test_protect_takes_keywords_only():
    with pytest.raises(TypeError):
        Protect(False)


def test_protect_is_immutable():
    p = Protect()
    with pytest.raises(AttributeError):
        p.urls = False
    with pytest.raises(AttributeError):
        p.colour = "red"
    with pytest.raises(AttributeError):
        del p.terms


def test_protect_equality_and_hash():
    assert Protect() == Protect()
    assert Protect(terms=["AslMatn"]) == Protect(terms=("AslMatn",))
    assert Protect(tokens=False) != Protect()
    assert Protect() != "Protect()"
    assert len({Protect(), Protect(), Protect(tokens=False)}) == 2


def test_protect_repr():
    assert repr(Protect()) == "Protect()"
    assert repr(Protect(tokens=False, terms=("AslMatn",))) == "Protect(tokens=False, terms=('AslMatn',))"
    for p in (Protect(), Protect.NONE, Protect(urls=False, terms=("a", "b"))):
        assert eval(repr(p), {"Protect": Protect}) == p


def test_protect_copy_and_pickle():
    p = Protect(dois=False, terms=("AslMatn",))
    assert copy.copy(p) == p
    assert copy.deepcopy(p) == p
    assert pickle.loads(pickle.dumps(p)) == p


@pytest.mark.parametrize(
    "terms,error",
    [("AslMatn", TypeError), (("",), ValueError), ((1,), TypeError), ((None,), TypeError)],
)
def test_protect_checks_the_terms(terms, error):
    with pytest.raises(error):
        Protect(terms=terms)


# --- convert, to_latin and to_cyrillic ---------------------------------------------

from akademtranslit import (  # noqa: E402
    CYRILLIC,
    LATIN_1995,
    LATIN_2026,
    SCRIPTS,
    convert,
    detect_script,
    normalize,
    sort_key,
    to_cyrillic,
    to_latin,
)

PAIRS = [(source, target) for source in SCRIPTS for target in SCRIPTS]

# The golden fields that hold conversion output, as functions of the input.
CONVERSION_FIELDS = {
    "to_cyrillic": lambda text, **kw: to_cyrillic(text, **kw),
    "to_latin_1995": lambda text, **kw: to_latin(text, variant=LATIN_1995, **kw),
    "to_latin_2026": lambda text, **kw: to_latin(text, variant=LATIN_2026, **kw),
}
for _source, _target in PAIRS:
    CONVERSION_FIELDS[f"convert_from_{_source}_to_{_target}"] = (
        lambda text, s=_source, t=_target, **kw: convert(text, source=s, target=t, **kw)
    )

# The golden inputs that have a protected span and whose output protection
# changes: the tokens McDonald, ToshKent, tOSHKENT, SpO2, pH, B12 and PaCO2,
# two DOIs, two URLs and three e-mail addresses.
CHANGED_BY_PROTECTION = [
    "c0872", "c0873", "c0874", "c0984", "c0985", "c0990", "c0991",
    "c1031", "c1032", "c1033", "c1034", "c1035", "c1036", "c1037",
]

# The golden inputs among c0001-c1139 whose case protect=False now keeps per
# letter unit: OʻzBEKISTON and the tokens McDonald, ToshKent, tOSHKENT, SpO2,
# pH and PaCO2. Only the case of their output changed (Mcdonald -> McDonald).
CHANGED_BY_CASE_UNITS = ["c0870", "c0872", "c0873", "c0874", "c0984", "c0985", "c0991"]

# The golden inputs among c0001-c1139 that protect=False now converts
# differently because source="auto" reads each word on its own: Toshkent
# viloyati Тошкент, Тошкент and a Latin word with o with macron, and Ёзинг:
# info@example.org, whose e-mail address is converted when nothing is
# protected.
CHANGED_BY_WORD_LEVEL_AUTO = ["c0338", "c1037", "c1139"]

# SHA-256 of the conversion output of 0.3.0 before protected spans: the 12
# fields above on c0001-c1139 except CHANGED_BY_CASE_UNITS and
# CHANGED_BY_WORD_LEVEL_AUTO, from golden-0.3.0.json at that commit, as
# {id: {field: output}} in the golden files' canonical JSON.
BEFORE_PROTECTION_SHA256 = "b0a16ee467a97d1c0563a9216c8823097184455b0601025f882a175bcbb8bee2"

# The same with protect=False on CHANGED_BY_CASE_UNITS, after case units.
CASE_UNITS_SHA256 = "f8a91be6d8cb4556e2312a4794d3c2091fafb57f8218069b0589f127476970b3"

# The same on CHANGED_BY_WORD_LEVEL_AUTO, after word-level auto.
WORD_LEVEL_AUTO_SHA256 = "4fff68422384a9821c039e91ccb5c6c98aa32cdec7f6855545d2ba50f073ddce"


def _golden_cases_before_protection():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    return [case for case in doc["cases"] if int(case["id"][1:]) <= 1139]


def _protect_false_sha256(cases):
    results = {
        case["id"]: {name: func(case["text"], protect=False) for name, func in CONVERSION_FIELDS.items()}
        for case in cases
    }
    data = (json.dumps(results, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def test_protect_false_gives_the_output_from_before_protection():
    changed = CHANGED_BY_CASE_UNITS + CHANGED_BY_WORD_LEVEL_AUTO
    cases = [case for case in _golden_cases_before_protection() if case["id"] not in changed]
    assert _protect_false_sha256(cases) == BEFORE_PROTECTION_SHA256


def test_protect_false_on_the_inputs_whose_case_units_changed():
    cases = [case for case in _golden_cases_before_protection() if case["id"] in CHANGED_BY_CASE_UNITS]
    assert [case["id"] for case in cases] == CHANGED_BY_CASE_UNITS
    assert _protect_false_sha256(cases) == CASE_UNITS_SHA256


def test_protect_false_on_the_inputs_that_word_level_auto_changed():
    cases = [case for case in _golden_cases_before_protection() if case["id"] in CHANGED_BY_WORD_LEVEL_AUTO]
    assert [case["id"] for case in cases] == CHANGED_BY_WORD_LEVEL_AUTO
    assert _protect_false_sha256(cases) == WORD_LEVEL_AUTO_SHA256


def test_protection_changes_only_the_inputs_with_a_protected_span():
    changed = []
    for case in _golden_cases_before_protection():
        text = case["text"]
        if any(func(text) != func(text, protect=False) for func in CONVERSION_FIELDS.values()):
            changed.append(case["id"])
            assert protected(text), case["id"]
    assert changed == CHANGED_BY_PROTECTION


@pytest.mark.parametrize("source,target", PAIRS)
def test_protected_pieces_come_out_byte_for_byte(source, target):
    """Each protected piece is kept; each other piece is converted as on its own."""
    wrong = []
    for text in all_inputs():
        expected = "".join(
            piece if kind else convert(piece, source=source, target=target, protect=False)
            for piece, kind in segments(text)
        )
        if convert(text, source=source, target=target) != expected:
            wrong.append(text)
    assert wrong == []


# Not a letter, a digit or a mark: no word runs across it.
SEPARATOR = chr(0)


def test_auto_reads_the_orthography_from_the_unprotected_text_only():
    """With source="auto", the text between the protected spans is converted
    as if the spans were not there: the pieces, joined with a separator and
    converted with protect=False, come out the same."""
    wrong = []
    for text in all_inputs():
        pieces = segments(text)
        plain = [piece for piece, kind in pieces if kind is None]
        assert not any(SEPARATOR in piece for piece in plain)
        for target in SCRIPTS:
            converted = iter(convert(SEPARATOR.join(plain), target=target, protect=False).split(SEPARATOR))
            expected = "".join(piece if kind else next(converted) for piece, kind in pieces)
            if convert(text, target=target) != expected:
                wrong.append((text, target))
    assert wrong == []


def test_auto_ignores_a_2026_letter_inside_a_url():
    text = "shahar https://" + "ş" + "ahar.uz"
    assert detect_script(text) == LATIN_2026  # unchanged: it reads the whole text
    assert to_cyrillic(text) == "шаҳар https://şahar.uz"
    assert to_cyrillic(text, protect=False) == "сҳаҳар ҳттпс://шаҳар.уз"


def test_terms():
    assert (
        convert("AslMatn va shahar", source="latin_1995", target="latin_2026", protect=Protect(terms=("AslMatn",)))
        == "AslMatn va şahar"
    )
    protect = Protect(tokens=False, terms=("Toshkent",))
    assert to_latin("Toshkent shahri", protect=protect) == "Toshkent şahri"
    assert to_cyrillic("Toshkent shahri", protect=protect) == "Toshkent шаҳри"


@pytest.mark.parametrize(
    "text,latin_2026,cyrillic",
    [
        ("McDonald", "McDonald", "McDonald"),
        ("pH 7,4 va SpO2 92%", "pH 7,4 va SpO2 92%", "pH 7,4 ва SpO2 92%"),
        (NEW_INPUTS["c1155"], "AkademTech va AslMatn", "AkademTech ва AslMatn"),
        (NEW_INPUTS["c1159"], "/home/user/shahar.txt fayli", "/home/user/shahar.txt файли"),
        (NEW_INPUTS["c1143"], "info@shahar.uz ga yozing", "info@shahar.uz га ёзинг"),
        (
            NEW_INPUTS["c1148"],
            "{count, plural, one {# ta şahar} other {# ta şahar}}",
            "{count, plural, one {# та шаҳар} other {# та шаҳар}}",
        ),
        (
            NEW_INPUTS["c1151"],
            '<b>Şahar</b> <a href="https://shahar.uz">havola</a>',
            '<b>Шаҳар</b> <a href="https://shahar.uz">ҳавола</a>',
        ),
        (NEW_INPUTS["c1150"], "%s ta fayl, %(soni)d ta şahar", "%s та файл, %(soni)d та шаҳар"),
        ("%sga yuborildi", "%sga yuborildi", "%sга юборилди"),  # %s, then Cyrillic га
        ("50%dan ortiq", "50%dan ortiq", "50%дан ортиқ"),
        (NEW_INPUTS["c1162"], "Toşkent https://toshkent.uz/шаҳар", "Тошкент https://toshkent.uz/шаҳар"),
    ],
)
def test_conversion_keeps_the_protected_spans(text, latin_2026, cyrillic):
    assert to_latin(text) == latin_2026
    assert to_cyrillic(text) == cyrillic


def test_uzbek_abbreviations_with_sh_and_ch_are_converted():
    for text in (NEW_INPUTS["c1156"], NEW_INPUTS["c1157"]):
        assert to_latin(text) == to_latin(text, protect=False) != text


def test_protect_false_converts_everything():
    assert to_latin("https://shahar.uz", protect=False) == "https://şahar.uz"
    assert to_cyrillic("https://shahar.uz", protect=False) == "ҳттпс://шаҳар.уз"
    assert convert("pH", source=LATIN_1995, target=CYRILLIC, protect=Protect.NONE) == "пҲ"
    # Converted, and cased per letter unit: Mc + Donald.
    assert to_latin("McDonald", protect=False) == "McDonald"


@pytest.mark.parametrize("value", [1, 0, None, "yes", Protect])
def test_the_conversion_functions_take_only_true_false_or_a_protect(value):
    for call in (
        lambda: convert("shahar", protect=value),
        lambda: convert("", protect=value),
        lambda: to_latin("shahar", protect=value),
        lambda: to_cyrillic("shahar", protect=value),
    ):
        with pytest.raises(ValueError, match="protect"):
            call()


def test_protect_is_a_keyword_argument_only():
    with pytest.raises(TypeError):
        convert("shahar", "auto", LATIN_2026, False)
    with pytest.raises(TypeError):
        to_latin("shahar", LATIN_2026, False)
    with pytest.raises(TypeError):
        to_cyrillic("shahar", False)


def test_normalize_and_sort_key_do_not_use_protection():
    assert normalize("McDonald") == "mcdonald"
    assert normalize("https://shahar.uz") == "https shahar uz"
    assert sort_key("pH", LATIN_1995) == sort_key("ph", LATIN_1995)[:1] + ("pH",)
