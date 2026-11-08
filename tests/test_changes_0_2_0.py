"""Rule changes in 0.2.0.

Each section pins one change: the words it fixes, the neighbouring words it
must leave alone, and what it does to the round trip.
"""

from __future__ import annotations

import pytest

from akademtranslit import CYRILLIC, LATIN_1995, LATIN_2026, convert, normalize

# --- ъ: dropped where the 1995 spelling drops it ------------------------------
#
# ъ was always the tutuq belgisi, so объект came out as obʼyekt and мўъжиза as
# moʻʼjiza. The 1995 spelling writes no mark in two places: after a consonant
# before е ё ю я, where ъ only separates the consonant from the y sound, and
# after ў.

HARD_SIGN_DROPPED = [
    ("объект", "obyekt"),
    ("подъезд", "podyezd"),
    ("инъекция", "inyeksiya"),
    ("съёмка", "syomka"),
    ("адъютант", "adyutant"),
    ("мўъжиза", "moʻjiza"),
    ("мўътабар", "moʻtabar"),
]

HARD_SIGN_KEPT = [
    ("маъюс", "maʼyus"),     # after a vowel
    ("санъат", "sanʼat"),    # after a consonant, before а
    ("таъсир", "taʼsir"),
    ("маъно", "maʼno"),
    ("шеър", "sheʼr"),
    ("аъзо", "aʼzo"),
    ("қатъий", "qatʼiy"),    # after a consonant, before и
]


@pytest.mark.parametrize("cyrillic,latin", HARD_SIGN_DROPPED)
def test_hard_sign_is_dropped_after_a_consonant_before_ye_or_after_u_breve(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin


@pytest.mark.parametrize("cyrillic,latin", HARD_SIGN_KEPT)
def test_hard_sign_is_the_tutuq_belgisi_everywhere_else(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_1995) == latin


@pytest.mark.parametrize(
    "cyrillic,latin",
    [("объект", "obyekt"), ("мўъжиза", "möjiza"), ("съёмка", "syomka"), ("санъат", "sanʼat")],
)
def test_hard_sign_in_latin_2026(cyrillic, latin):
    assert convert(cyrillic, source=CYRILLIC, target=LATIN_2026) == latin


def test_hard_sign_case():
    assert convert("ОБЪЕКТ", source=CYRILLIC, target=LATIN_1995) == "OBYEKT"
    assert convert("Мўъжиза", source=CYRILLIC, target=LATIN_1995) == "Moʻjiza"
    assert convert("МЎЪЖИЗА", source=CYRILLIC, target=LATIN_2026) == "MÖJIZA"


def test_hard_sign_the_reverse_direction_is_unchanged():
    """Latin has nothing to restore ъ from: these come back without it."""
    assert convert("obyekt", source=LATIN_1995, target=CYRILLIC) == "обект"
    assert convert("moʻjiza", source=LATIN_1995, target=CYRILLIC) == "мўжиза"
    assert convert("maʼno", source=LATIN_1995, target=CYRILLIC) == "маъно"


def test_hard_sign_normalize_is_unchanged():
    """normalize() strips the tutuq belgisi anyway, so its keys do not move."""
    assert normalize("объект") == normalize("obyekt") == "obyekt"
    assert normalize("мўъжиза") == normalize("moʻjiza") == "mojiza"


# --- ts before particles that follow a suffix ---------------------------------
#
# The ts rule reads ts as т + с when the rest of the word is suffixes, but the
# particles that can close a verb form were missing from the list of what may
# follow, so aytsangizgina came out as айцангизгина.

TS_PARTICLES = [
    ("aytsangizgina", "айтсангизгина"),   # -gina
    ("aytsakkina", "айтсаккина"),         # -kina
    ("ketsayu", "кетсаю"),                # -yu
    ("ketsinu", "кетсину"),               # -u
    ("ketsaku", "кетсаку"),               # -ku
    ("ketsayoq", "кетсаёқ"),              # -yoq
    ("tutsinmikan", "тутсинмикан"),       # -mikan
]

# Loanwords whose ц must not move.
TS_PARTICLES_UNCHANGED = [
    ("meditsina", "медицина"),
    ("natsizm", "нацизм"),
    ("protsent", "процент"),
    ("litsey", "лицей"),
    ("tsement", "цемент"),
    ("vaktsina", "вакцина"),
]


@pytest.mark.parametrize("latin,cyrillic", TS_PARTICLES)
def test_ts_before_a_particle_is_t_plus_s(latin, cyrillic):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == cyrillic


@pytest.mark.parametrize("latin,cyrillic", TS_PARTICLES_UNCHANGED)
def test_ts_particles_leave_loanwords_alone(latin, cyrillic):
    assert convert(latin, source=LATIN_1995, target=CYRILLIC) == cyrillic


def test_ts_particles_from_latin_2026_and_in_caps():
    assert convert("aytsangizgina", source=LATIN_2026, target=CYRILLIC) == "айтсангизгина"
    assert convert("KETSAYU", source=LATIN_1995, target=CYRILLIC) == "КЕТСАЮ"


@pytest.mark.parametrize("via", [LATIN_1995, LATIN_2026])
@pytest.mark.parametrize("cyrillic", [c for _, c in TS_PARTICLES])
def test_ts_particles_round_trip(cyrillic, via):
    latin = convert(cyrillic, source=CYRILLIC, target=via)
    assert convert(latin, source=via, target=CYRILLIC) == cyrillic
