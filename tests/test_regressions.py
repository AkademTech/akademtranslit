"""Regressions found against 0.1.0, fixed in 0.1.1.

Each section pins one defect: the inputs that exposed it, the neighbouring
words the fix must leave alone, and the round trip the defect broke.
"""

from __future__ import annotations

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert

# The five spellings of the turned comma seen most in real input.
APOSTROPHES = ["ʻ", "'", "‘", "’", "ʼ"]
APOSTROPHE_IDS = ["U+02BB", "ASCII", "U+2018", "U+2019", "U+02BC"]

BOTH_LATINS = [LATIN_1995, LATIN_2026]


def _round_trip(text: str, via: str) -> str:
    latin = convert(text, source=CYRILLIC, target=via)
    return convert(latin, source=via, target=CYRILLIC)


# --- X1: y + oʻ is й + ў, not ё ----------------------------------------------
#
# The ``yo`` row matched before ``oʻ`` could, so yoʻq came out as ёʻқ: the o
# went into ё and the turned comma was stranded.

X1_CASES = [
    ("yoʻq", "йўқ"),
    ("yoʻl", "йўл"),
    ("Yoʻl", "Йўл"),
    ("Yoʻldosh", "Йўлдош"),
    ("yoʻtal", "йўтал"),
]


@pytest.mark.parametrize("mark", APOSTROPHES, ids=APOSTROPHE_IDS)
@pytest.mark.parametrize("latin,expected", X1_CASES)
def test_x1_y_before_o_turned_comma(latin, expected, mark):
    spelled = latin.replace("ʻ", mark)
    assert convert(spelled, source=LATIN_1995, target=CYRILLIC) == expected


def test_x1_from_latin_2026():
    assert convert("yöl", source=LATIN_2026, target=CYRILLIC) == "йўл"


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("boʻyoq", "бўёқ"),   # yo with no mark after it is still ё
        ("qoʻyosh", "қўёш"),
        ("yoz", "ёз"),
    ],
)
def test_x1_yo_without_a_following_mark_is_still_yo(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize("via", BOTH_LATINS)
@pytest.mark.parametrize("text", ["йўқ", "йўл", "Йўлдош", "йўтал"])
def test_x1_round_trip(text, via):
    assert _round_trip(text, via) == text


# --- X2: ts at an Uzbek suffix boundary is т + с, not ц ----------------------
#
# The ``ts`` row read every t + s as ц, so ketsa came out as кеца and hayotsiz
# as ҳаёциз. ts is now decided per word, by the ordered checks in
# rules._ts_splits; each check has its own test below.

X2_SUFFIX_CASES = [
    ("ketsa", "кетса"),
    ("aytsa", "айтса"),
    ("tutsa", "тутса"),
    ("yetsa", "етса"),
    ("oʻtsa", "ўтса"),
    ("kutsangiz", "кутсангиз"),
    ("aytsangizchi", "айтсангизчи"),
    ("ketsin", "кетсин"),
    ("bitsin", "битсин"),
    ("oʻqitsin", "ўқитсин"),
    ("eshitsin", "эшитсин"),
    ("ketsinmi", "кетсинми"),
    ("hayotsiz", "ҳаётсиз"),
    ("mehnatsiz", "меҳнатсиз"),
    ("otsiz", "отсиз"),
    ("hayotsizlik", "ҳаётсизлик"),
    ("hayotsizman", "ҳаётсизман"),
    ("mehnatsevar", "меҳнатсевар"),
]

# Correct in 0.1.0 and must stay so.
X2_LOANWORDS = [
    ("militsiya", "милиция"),
    ("reanimatsiya", "реанимация"),
    ("natsional", "национал"),
    ("intubatsiyasiz", "интубациясиз"),
    ("sotsiologiya", "социология"),
    ("leykotsit", "лейкоцит"),
    ("eritrotsit", "эритроцит"),
    ("trombotsit", "тромбоцит"),
    ("limfotsit", "лимфоцит"),
    ("protsent", "процент"),
    ("platsenta", "плацента"),
    ("litsey", "лицей"),
    ("atseton", "ацетон"),
    ("farmatsevt", "фармацевт"),
    ("detsibel", "децибел"),
    ("spetsifik", "специфик"),
    ("meditsina", "медицина"),
    ("vaktsina", "вакцина"),
    ("natsizm", "нацизм"),
    ("azitromitsin", "азитромицин"),
    ("glitsin", "глицин"),
]


@pytest.mark.parametrize("latin,expected", X2_SUFFIX_CASES)
def test_x2_suffix_after_t_is_t_plus_s(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize("latin,expected", X2_LOANWORDS)
def test_x2_loanwords_keep_tse(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


def test_x2_case_is_kept():
    assert convert("KETSA", source=LATIN_1995, target=CYRILLIC) == "КЕТСА"
    assert convert("Hayotsiz", source=LATIN_1995, target=CYRILLIC) == "Ҳаётсиз"


# Check 0: the s is the first half of sh, so there is no ts at all.


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("adabiyotshunos", "адабиётшунос"),
        ("adabiyotshunoslik", "адабиётшунослик"),
        ("sanʼatshunos", "санъатшунос"),
    ],
)
def test_x2_check0_s_opening_sh(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


def test_x2_check0_from_latin_2026():
    assert convert("adabiyotşunos", source=LATIN_2026, target=CYRILLIC) == "адабиётшунос"


# Check 1: word-initial ts is ц. tsinga is the case that needs it -- its tail
# reads as sin + ga, which check 4 would otherwise split.


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("tsement", "цемент"),
        ("tsar", "цар"),
        ("tsitokin", "цитокин"),
        ("tsinga", "цинга"),
    ],
)
def test_x2_check1_word_initial(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


# Check 2: ts + i + vowel or y, the -tsiya / -tsion / -tsiy family.


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("operatsiya", "операция"),
        ("informatsiya", "информация"),
        ("ratsion", "рацион"),
        ("patsiyent", "пациент"),
        ("sotsial", "социал"),
    ],
)
def test_x2_check2_before_i_and_a_vowel(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


# Check 3: loans whose tail looks like the -sin suffix. Matched where the ts
# is, not at the end of the word, so the inflected forms hold too.


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("azitromitsin", "азитромицин"),
        ("streptomitsin", "стрептомицин"),
        ("gentamitsin", "гентамицин"),
        ("glitsin", "глицин"),
        ("azitromitsinni", "азитромицинни"),
        ("glitsinning", "глициннинг"),
    ],
)
def test_x2_check3_known_loans(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


# Check 4: the whole tail has to be suffixes.


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("mehnatsizligi", "меҳнатсизлиги"),   # siz + ligi
        ("hayotsizlikni", "ҳаётсизликни"),    # sizlik + ni
        ("ketsangizlar", "кетсангизлар"),     # sangiz + lar
        ("mehnatsizroq", "меҳнатсизроқ"),     # siz + roq
        ("hayotsizsan", "ҳаётсизсан"),        # siz + san
        ("patsiyentsiz", "пациентсиз"),       # check 2, then check 4
        ("meditsina", "медицина"),            # sin + a: a is not a suffix here
        ("vaktsina", "вакцина"),
        ("natsizm", "нацизм"),                # siz + m
    ],
)
def test_x2_check4_needs_the_whole_tail(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize("via", BOTH_LATINS)
@pytest.mark.parametrize(
    "text",
    [
        "кетса",
        "айтса",
        "тутса",
        "ўтса",
        "кетсин",
        "ҳаётсиз",
        "КЕТСА",
        "ҲАЁТСИЗ",
        "милиция",
        "лейкоцит",
        "адабиётшунос",
        "санъатшунос",
    ],
)
def test_x2_round_trip(text, via):
    assert _round_trip(text, via) == text


# --- X2, continued: loanwords the suffix check misread -----------------------
#
# Check 4 reads any tail that looks like suffixes as т + с, and some loanwords
# have such a tail: tablitsa looks like tablit + -sa, leytsin like leyt + -sin.
# These were ц in 0.1.0 and are again, through checks 3b-3d.


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("levofloksatsin", "левофлоксацин"),
        ("ofloksatsin", "офлоксацин"),
        ("moksifloksatsin", "моксифлоксацин"),
        ("siprofloksatsin", "сипрофлоксацин"),   # only the ts; the s- is not restored
        ("levofloksatsinni", "левофлоксацинни"),
        ("amikatsin", "амикацин"),
        ("leytsin", "лейцин"),
        ("izoleytsin", "изолейцин"),
    ],
)
def test_x2_check3b_tsin_names(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("aktsiz", "акциз"),
        ("aktsizlar", "акцизлар"),
        ("aktsizni", "акцизни"),
    ],
)
def test_x2_check3c_aktsiz(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize(
    "latin,expected",
    [
        # A noun ending in -kt takes -siz like any other: a rule keyed on the
        # k alone would turn these into ц.
        ("kontaktsiz", "контактсиз"),
        ("kontaktsizlik", "контактсизлик"),
        ("effektsiz", "эффектсиз"),
        ("effektsizligi", "эффектсизлиги"),
        ("faktsiz", "фактсиз"),
        ("proyektsiz", "проектсиз"),
        ("intellektsiz", "интеллектсиз"),
    ],
)
def test_x2_check3c_is_not_a_rule_about_k(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("tablitsa", "таблица"),
        ("tablitsada", "таблицада"),
        ("teplitsa", "теплица"),
        ("teplitsalar", "теплицалар"),
        ("stolitsa", "столица"),
        ("ulitsa", "улица"),
        ("bolnitsa", "болница"),   # ь is never restored
        ("granitsa", "граница"),
        ("gostinitsa", "гостиница"),
    ],
)
def test_x2_check3d_loanword_stems(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize(
    "latin,expected",
    [
        # The same endings on Uzbek verbs, which is why 3b-3d name exact stems
        # rather than -itsa or -atsin.
        ("bitsa", "битса"),
        ("oʻqitsa", "ўқитса"),
        ("eshitsa", "эшитса"),
        ("quritsa", "қуритса"),
        ("ilitsa", "илитса"),
        ("tanitsa", "танитса"),
        ("koʻrsatsin", "кўрсатсин"),
        ("yaratsin", "яратсин"),
        ("oʻrgatsin", "ўргатсин"),
        ("uzatsin", "узатсин"),
        ("qaytsa", "қайтса"),
        ("tortsa", "тортса"),
        ("yurtsiz", "юртсиз"),
    ],
)
def test_x2_uzbek_words_beside_the_loanwords_keep_t_plus_s(latin, expected):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize("via", BOTH_LATINS)
@pytest.mark.parametrize("text", ["таблица", "теплица", "улица", "левофлоксацин", "амикацин"])
def test_x2_loanword_round_trip(text, via):
    assert _round_trip(text, via) == text


# --- X3: ʻ and ʼ do not count when deciding case ------------------------------
#
# apply_case counted letters with str.isalpha(). ʻ (U+02BB) and ʼ (U+02BC) are
# letters to Unicode but have no case, so an all-caps word containing one never
# looked all-caps: OʻZBEKISTON came out as Ўзбекистон.

X3_TO_CYRILLIC = [
    ("OʻZBEKISTON", "ЎЗБЕКИСТОН"),
    ("GʻOYA", "ҒОЯ"),
    ("GʻALLA", "ҒАЛЛА"),
    ("SOʻM", "СЎМ"),
    ("YOʻL", "ЙЎЛ"),   # needs X1 too
    ("YOʻQ", "ЙЎҚ"),
]


@pytest.mark.parametrize("mark", APOSTROPHES, ids=APOSTROPHE_IDS)
@pytest.mark.parametrize("latin,expected", X3_TO_CYRILLIC)
def test_x3_all_caps_with_turned_comma_to_cyrillic(latin, expected, mark):
    spelled = latin.replace("ʻ", mark)
    assert convert(spelled, source=LATIN_1995, target=CYRILLIC) == expected


@pytest.mark.parametrize(
    "latin,expected",
    [
        ("OʻZBEKISTON", "ÖZBEKISTON"),
        ("GʻALLA", "ĞALLA"),
    ],
)
def test_x3_all_caps_with_turned_comma_to_latin_2026(latin, expected):
    assert convert(latin, source=LATIN_1995, target=LATIN_2026) == expected


def test_x3_all_caps_with_tutuq_belgisi():
    assert convert("MAʼNO", source=LATIN_1995, target=CYRILLIC) == "МАЪНО"
    assert convert("SHEʼR", source=LATIN_1995, target=CYRILLIC) == "ШЕЪР"


@pytest.mark.parametrize(
    "source,target,text,expected",
    [
        (LATIN_1995, CYRILLIC, "SHAHAR", "ШАҲАР"),
        (LATIN_1995, CYRILLIC, "Shahar", "Шаҳар"),
        (LATIN_1995, CYRILLIC, "Choy", "Чой"),
        (LATIN_1995, CYRILLIC, "CHOY", "ЧОЙ"),
        (LATIN_1995, CYRILLIC, "Oʻzbekiston", "Ўзбекистон"),
        (LATIN_1995, CYRILLIC, "Gʻalla", "Ғалла"),
        (CYRILLIC, LATIN_1995, "ШАҲАР", "SHAHAR"),
        (CYRILLIC, LATIN_1995, "Шаҳар", "Shahar"),
    ],
)
def test_x3_other_casing_is_unchanged(source, target, text, expected):
    """A digraph takes its case from its first letter; one capital stays one."""
    assert convert(text, source=source, target=target) == expected


@pytest.mark.parametrize("via", BOTH_LATINS)
@pytest.mark.parametrize(
    "text",
    ["ЎЗБЕКИСТОН", "ЙЎЛ", "СЎМ", "ҒОЯ", "ҒАЛЛА", "ШАҲАР", "МАЪНО"],
)
def test_x3_round_trip(text, via):
    assert _round_trip(text, via) == text


# --- Cyrillic -> Latin: е, ц and ь -------------------------------------------
#
# Unchanged in 0.1.1, and passing on 0.1.0 as well. Pinned here because the
# ts rule above is the return half of the ц rule below.


@pytest.mark.parametrize(
    "cyrillic,latin",
    [
        ("Ер", "Yer"),          # word-initial: ye
        ("поезд", "poyezd"),    # after a vowel: ye
        ("пьеса", "pyesa"),     # after ь: ye
        ("тезда", "tezda"),     # elsewhere: e
        ("кеча", "kecha"),
    ],
)
def test_reverse_e_rule(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin


@pytest.mark.parametrize(
    "cyrillic,latin",
    [
        ("милиция", "militsiya"),   # after a vowel: ts
        ("цирк", "sirk"),           # word-initial: s
        ("концерт", "konsert"),     # after a consonant: s
    ],
)
def test_reverse_tse_rule(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin


@pytest.mark.parametrize(
    "cyrillic,latin",
    [
        ("компьютер", "kompyuter"),
        ("июнь", "iyun"),
    ],
)
def test_reverse_soft_sign_is_dropped(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin
