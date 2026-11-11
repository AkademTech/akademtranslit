"""The golden vectors are current, and the inputs they were made from are intact."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _tag_tables() -> tuple:
    """TAG_CASES and SCRIPT_CASES, the expected tag results, from the one place
    they are written. Loaded by path: the tests also run against the installed
    wheel, where tests/ is not a package and may not be on sys.path."""
    path = REPO / "tests" / "test_changes_0_3_0.py"
    spec = importlib.util.spec_from_file_location("_tag_tables", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TAG_CASES, module.SCRIPT_CASES


TAG_CASES, SCRIPT_CASES = _tag_tables()
GOLDEN_DIR = REPO / "golden"
INPUTS = GOLDEN_DIR / "inputs.json"
TAG_INPUTS = GOLDEN_DIR / "tag-inputs.json"


def _inputs() -> dict:
    return json.loads(INPUTS.read_bytes().decode("utf-8"))


def _tag_inputs() -> dict:
    return json.loads(TAG_INPUTS.read_bytes().decode("utf-8"))


def _schema_2_files() -> list:
    docs = []
    for path in sorted(GOLDEN_DIR.glob("golden-*.json")):
        doc = json.loads(path.read_bytes().decode("utf-8"))
        if doc["schema"] == "akademtranslit-golden/2":
            docs.append((path.name, doc))
    return docs


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


# --- language tags (schema 2, 0.3.0 on) ------------------------------------------


def test_tag_input_ids_are_unique_and_have_the_documented_shape():
    doc = _tag_inputs()
    assert doc["schema"] == "akademtranslit-golden-tag-inputs/1"
    tag_ids = [case["id"] for case in doc["tags"]]
    script_ids = [case["id"] for case in doc["scripts"]]
    assert len(tag_ids) == len(set(tag_ids)) and len(script_ids) == len(set(script_ids))
    for case_id in tag_ids:
        assert len(case_id) == 4 and case_id[0] == "t" and case_id[1:].isdigit(), case_id
    for case_id in script_ids:
        assert len(case_id) == 3 and case_id[0] == "s" and case_id[1:].isdigit(), case_id


def test_the_tag_inputs_are_the_ones_the_tests_expect():
    doc = _tag_inputs()
    assert [(case["id"], case["tag"]) for case in doc["tags"]] == [c[:2] for c in TAG_CASES]
    assert [(case["id"], case["script"]) for case in doc["scripts"]] == [c[:2] for c in SCRIPT_CASES]


def test_there_is_a_schema_2_golden_file():
    assert [name for name, _ in _schema_2_files()], "no golden file with schema 2"


def test_schema_2_files_name_the_tag_inputs_they_were_made_from():
    digest = hashlib.sha256(TAG_INPUTS.read_bytes()).hexdigest()
    for name, doc in _schema_2_files():
        assert doc["tag_inputs_sha256"] == digest, name


def test_segments_in_schema_2_files_join_to_their_input():
    texts = {case["id"]: case["text"] for case in _inputs()["cases"]}
    for name, doc in _schema_2_files():
        for case_id, row in doc["results"].items():
            if "segments" in row:
                assert "".join(piece for piece, _ in row["segments"]) == texts[case_id], (name, case_id)


def test_schema_2_files_give_the_expected_tag_results():
    tags = {}
    for case_id, _, expected, warning in TAG_CASES:
        if expected == "ValueError":
            tags[case_id] = {"error": "ValueError"}
        else:
            tags[case_id] = {"script": expected, "warning": warning}
    scripts = {
        case_id: {"error": "ValueError"} if expected == "ValueError" else expected
        for case_id, _, expected in SCRIPT_CASES
    }
    for name, doc in _schema_2_files():
        assert doc["tags"] == tags, name
        assert doc["scripts"] == scripts, name
