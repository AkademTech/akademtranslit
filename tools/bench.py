#!/usr/bin/env python3
"""Rough timings for the main functions. Not part of the installed package.

    python tools/bench.py

- ``to_latin`` and ``to_cyrillic`` on one text of 10,000 words, built from the
  words in ``golden/inputs.json``;
- ``normalize`` and ``sort_key`` on 100,000 short name-shaped strings.

Each is run three times; the median is reported, with the Python version. The
numbers depend on the machine and are for comparing changes, not for quoting.
"""

from __future__ import annotations

import itertools
import json
import platform
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

import akademtranslit as lib  # noqa: E402

RUNS = 3
TEXT_WORDS = 10_000
SHORT_STRINGS = 100_000

GIVEN = ["Ali", "Vali", "Gʻani", "Aziza", "Jasur", "Oʻktam", "Shahnoza", "Али", "Ғани", "Азиза"]
FAMILY = ["Valiyev", "Aliyev", "Karimova", "Toshmatov", "Valiev", "Шошимова", "Алиев", "Каримов"]


def text_of_words(n: int) -> str:
    doc = json.loads((REPO / "golden" / "inputs.json").read_bytes().decode("utf-8"))
    words = [w for case in doc["cases"] for w in case["text"].split()]
    return " ".join(itertools.islice(itertools.cycle(words), n))


def short_strings(n: int) -> list:
    shapes = [f"{f} {g}" for g in GIVEN for f in FAMILY] + [f"{f} {g[0]}." for g in GIVEN for f in FAMILY]
    return list(itertools.islice(itertools.cycle(shapes), n))


def median_seconds(func) -> float:
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def main() -> int:
    text = text_of_words(TEXT_WORDS)
    names = short_strings(SHORT_STRINGS)
    cases = [
        (f"to_latin, {TEXT_WORDS:,} words", lambda: lib.to_latin(text)),
        (f"to_cyrillic, {TEXT_WORDS:,} words", lambda: lib.to_cyrillic(text)),
        (f"normalize, {SHORT_STRINGS:,} strings", lambda: [lib.normalize(s) for s in names]),
        (
            f"sort_key latin_1995, {SHORT_STRINGS:,} strings",
            lambda: [lib.sort_key(s, "latin_1995") for s in names],
        ),
    ]
    print(f"akademtranslit {lib.__version__}, Python {platform.python_version()} "
          f"({platform.python_implementation()}), {platform.machine()}; median of {RUNS} runs")
    print()
    print("| case | median, s |")
    print("| --- | ---: |")
    for label, func in cases:
        print(f"| {label} | {median_seconds(func):.3f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
