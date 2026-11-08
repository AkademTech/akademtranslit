"""The examples in README.md run, and give what the README says they give."""

from __future__ import annotations

import doctest
from pathlib import Path

README = Path(__file__).resolve().parent.parent / "README.md"


def test_readme_examples():
    result = doctest.testfile(str(README), module_relative=False, encoding="utf-8")
    assert result.attempted > 0
    assert result.failed == 0
