"""The golden vectors are current, and the inputs they were made from are intact."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO / "golden"
INPUTS = GOLDEN_DIR / "inputs.json"


def _inputs() -> dict:
    return json.loads(INPUTS.read_bytes().decode("utf-8"))


def test_golden_check_passes():
    """src/ reproduces the golden file for its version, and SHA256SUMS is current."""
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "golden.py"), "--check"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    assert result.returncode == 0, result.stdout.decode("utf-8", "replace")


def test_input_ids_are_unique_and_there_are_enough_of_them():
    ids = [case["id"] for case in _inputs()["cases"]]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 600


def test_input_ids_have_the_documented_shape():
    for case in _inputs()["cases"]:
        assert len(case["id"]) == 5 and case["id"][0] == "c" and case["id"][1:].isdigit()


def test_golden_files_name_the_inputs_they_were_made_from():
    digest = hashlib.sha256(INPUTS.read_bytes()).hexdigest()
    for path in sorted(GOLDEN_DIR.glob("golden-*.json")):
        doc = json.loads(path.read_bytes().decode("utf-8"))
        assert doc["inputs_sha256"] == digest, path.name
