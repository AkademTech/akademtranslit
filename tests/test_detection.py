"""script_class and cyrillic_language: closed answers for routing text."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from akademtranslit import cyrillic_language, detect_script, script_class

GOLDEN_INPUTS = Path(__file__).resolve().parent.parent / "golden" / "inputs.json"


def _golden_texts():
    doc = json.loads(GOLDEN_INPUTS.read_bytes().decode("utf-8"))
    return [case["text"] for case in doc["cases"]]


# --- script_class ------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Тошкент", "cyrillic"),
        ("Toshkent", "latin"),
        ("Toşkent", "latin"),
        ("Oʻzbekiston", "latin"),
        ("Аliyev", "mixed"),            # Cyrillic А
        ("Tоshkent", "mixed"),          # Cyrillic о
        ("Toshkent Тошкент", "mixed"),
        ("123", "latin"),
        ("", "latin"),
        ("   ", "latin"),
        ("«—»", "latin"),
        ("Нөкис", "cyrillic"),          # Karakalpak ө is Cyrillic
        ("ԁ", "cyrillic"),              # U+0501, Cyrillic Supplement
        ("Nókis", "latin"),
    ],
)
def test_script_class(text, expected):
    assert script_class(text) == expected


@pytest.mark.parametrize("marks", ["ʻ", "ʼ", "ʹ", "ʻʼʹ"])
def test_modifier_letters_are_not_counted(marks):
    assert script_class(marks) == "latin"
    assert script_class("Тошкент" + marks) == "cyrillic"


@pytest.mark.parametrize("text", ["αβγ", "東京", "שלום"])
def test_other_scripts_are_not_counted(text):
    assert script_class(text) == "latin"
    assert script_class("Тошкент " + text) == "cyrillic"
    assert script_class("Toshkent " + text) == "latin"


def test_script_class_is_always_one_of_three_on_every_golden_input():
    for text in _golden_texts():
        assert script_class(text) in ("latin", "cyrillic", "mixed"), text


def test_detect_script_is_unchanged_by_it():
    """detect_script still answers in orthographies, and still on first hit."""
    assert detect_script("Аliyev") == "cyrillic"
    assert detect_script("Toşkent") == "latin_2026"
    assert detect_script("") == "latin_1995"


# --- cyrillic_language -------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Ўзбекистон", "uz"),
        ("ЎЗБЕКИСТОН", "uz"),
        ("Қашқадарё", "uz"),
        ("тоғ", "uz"),
        ("ҳаёт", "uz"),
        ("Мы здесь", "ru"),
        ("ЩИ", "ru"),
        ("бир", "unknown"),
        ("Тошкент", "unknown"),
        ("Қўшиқ ва щи", "mixed"),
        ("", "unknown"),
        ("Toshkent", "unknown"),
        ("Нөкис", "unknown"),
    ],
)
def test_cyrillic_language(text, expected):
    assert cyrillic_language(text) == expected


def test_cyrillic_language_is_always_one_of_four_on_every_golden_input():
    for text in _golden_texts():
        assert cyrillic_language(text) in ("uz", "ru", "mixed", "unknown"), text
