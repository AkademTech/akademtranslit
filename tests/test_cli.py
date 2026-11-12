"""The command-line tool, run in this process with main(argv); one test runs
python -m akademtranslit in a subprocess."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import akademtranslit
from akademtranslit import RULES_VERSION, __version__
from akademtranslit.cli import main

SAMPLE = "Oʻzbekiston Respublikasi\nToshkent shahri, Isʼhoq va MChJning\nma'no https://shahar.uz\n"

COMBINING_DIAERESIS = chr(0x0308)
SOFT_HYPHEN = chr(0x00AD)


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_bytes(SAMPLE.encode("utf-8"))
    return str(path)


@pytest.fixture
def run(monkeypatch, capsysbinary):
    """main(argv) with ``stdin`` (bytes) as standard input: (exit code, stdout, stderr)."""

    def _run(argv, stdin=b""):
        monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(stdin), encoding="utf-8"))
        try:
            code = main(argv)
        except SystemExit as exc:
            code = exc.code
        out, err = capsysbinary.readouterr()
        return code, out.decode("utf-8"), err.decode("utf-8")

    return _run


# --- convert ----------------------------------------------------------------------


def test_convert(run, sample):
    assert run(["convert", "--from", "latin_1995", "--to", "uz-Latn-2026", sample]) == (
        0,
        "Özbekiston Respublikasi\nToşkent şahri, Ishoq va MÇJning\nmaʼno https://shahar.uz\n",
        "",
    )


def test_convert_reads_standard_input_and_adds_nothing(run):
    assert run(["convert"], "Тошкент".encode("utf-8")) == (0, "Toşkent", "")
    assert run(["convert", "-", "--to", "cyrillic"], "Toshkent".encode("utf-8")) == (0, "Тошкент", "")


def test_convert_keeps_crlf(run, tmp_path):
    path = tmp_path / "crlf.txt"
    path.write_bytes("Toshkent\r\nshahri\r\n".encode("utf-8"))
    code, out, _ = run(["convert", "--from", "latin_1995", str(path)])
    assert code == 0 and out == "Toşkent\r\nşahri\r\n"


def test_convert_no_protect(run):
    text = "https://shahar.uz".encode("utf-8")
    assert run(["convert", "--to", "cyrillic"], text)[1] == "https://shahar.uz"
    assert run(["convert", "--to", "cyrillic", "--no-protect"], text)[1] == "ҳттпс://шаҳар.уз"


def test_a_library_warning_goes_to_standard_error(run):
    code, out, err = run(["convert", "--to", "uz"], "Тошкент".encode("utf-8"))
    assert (code, out) == (0, "Toshkent")
    assert err.startswith("akademtranslit: warning: 'uz' names no orthography")
    assert err.endswith("\n") and err.count("\n") == 1


# --- validate ---------------------------------------------------------------------


def test_validate(run, sample):
    assert run(["validate", "--orthography", "latin_1995", sample]) == (
        1,
        f"{sample}:3:1: mark-form: ma'no -> maʼno\n",
        "",
    )


def test_validate_ignore(run, sample):
    assert run(["validate", "--orthography", "latin_1995", "--ignore", "mark-form", sample]) == (0, "", "")
    assert run(["validate", "--orthography", "latin_1995", "--ignore", "digraph,mark-form", sample])[0] == 0


def test_validate_shows_invisible_and_decomposed_by_code_point(run):
    text = "O" + COMBINING_DIAERESIS + "zbekiston va Tosh" + SOFT_HYPHEN + "kent"
    assert run(["validate", "--orthography", "latin_2026"], text.encode("utf-8")) == (
        1,
        "<stdin>:1:1: decomposed: U+004F U+0308 -> U+00D6\n"
        "<stdin>:1:16: digraph: Tosh -> Toş\n"
        "<stdin>:1:20: invisible: U+00AD\n",
        "",
    )


def test_validate_counts_lines_and_columns_from_one(run):
    text = "Тошкент\r\nva\n  shahar"
    assert run(["validate", "--orthography", "latin_2026"], text.encode("utf-8"))[1] == (
        "<stdin>:1:1: cyrillic-word: Тошкент -> Toşkent\n"
        "<stdin>:3:3: digraph: shahar -> şahar\n"
    )


def test_validate_json(run, sample):
    code, out, _ = run(["validate", "--orthography", "latin_1995", "--json", sample])
    assert code == 1 and out.endswith("]\n")
    assert json.loads(out) == [
        {"line": 3, "column": 1, "start": 61, "end": 66, "code": "mark-form", "text": "ma'no", "suggestion": "maʼno"}
    ]
    assert out == json.dumps(json.loads(out), ensure_ascii=False, indent=2) + "\n"


def test_validate_json_with_nothing_found(run):
    assert run(["validate", "--orthography", "latin_1995", "--json"], b"Toshkent") == (0, "[]\n", "")


def test_validate_no_protect(run):
    text = "https://shahar.uz".encode("utf-8")
    assert run(["validate", "--orthography", "latin_2026"], text)[0] == 0
    assert run(["validate", "--orthography", "latin_2026", "--no-protect"], text)[1] == (
        "<stdin>:1:9: digraph: shahar -> şahar\n"
    )


# --- report -----------------------------------------------------------------------


def test_report(run, sample):
    assert run(["report", sample]) == (
        1,
        "words: 8\n"
        "changed: 5\n"
        "protected: 1\n"
        "round trip: no\n"
        f"rules: {RULES_VERSION}\n"
        "to check: 3\n"
        f"{sample}:2:18: separator: Isʼhoq -> Ishoq\n"
        f"{sample}:2:28: round-trip: MChJning -> MCHJning\n"
        f"{sample}:3:1: mark-form: ma'no -> maʼno\n",
        "",
    )


def test_report_with_only_separators_to_check_is_fine(run):
    code, out, _ = run(["report"], "Isʼhoq va asʼhob".encode("utf-8"))
    assert code == 0
    assert "round trip: yes\n" in out and "to check: 2\n" in out


def test_report_with_another_finding_to_check_is_not_fine(run):
    # The text comes back, but ma'no is a mark-form.
    code, out, _ = run(["report"], "ma'no https://shahar.uz".encode("utf-8"))
    assert code == 1
    assert "round trip: yes\n" in out and out.endswith("<stdin>:1:1: mark-form: ma'no -> maʼno\n")


def test_report_json(run, sample):
    code, out, _ = run(["report", "--json", sample])
    report = json.loads(out)
    assert code == 1
    assert list(report) == ["words", "changed", "protected", "round_trip", "rules_version", "check", "result"]
    assert [(f["line"], f["column"], f["code"]) for f in report["check"]] == [
        (2, 18, "separator"), (2, 28, "round-trip"), (3, 1, "mark-form")
    ]
    assert report["result"] == "Özbekiston Respublikasi\nToşkent şahri, Ishoq va MÇJning\nmaʼno https://shahar.uz\n"


# --- normalize --------------------------------------------------------------------


def test_normalize(run):
    text = "Şoşimova N.\nShoshimova N.\r\nШошимова Н."
    assert run(["normalize"], text.encode("utf-8")) == (0, "shoshimova n\n" * 3, "")


# --- errors -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "argv,stdin,message",
    [
        (["convert", "no-such-file.txt"], b"", "cannot read no-such-file.txt: "),
        (["convert"], b"Tosh\xffkent", "<stdin> is not UTF-8 (byte 4)"),
        (["convert", "--to", "klingon"], b"x", "argument --to: unknown orthography: 'klingon'"),
        (["convert", "--from", "klingon"], b"x", "argument --from: unknown orthography: 'klingon'"),
        (["validate", "--orthography", "auto"], b"x", "argument --orthography: unknown orthography: 'auto'"),
        (["validate", "--orthography", "latin_1995", "--ignore", "foo"], b"x", "unknown code: 'foo'"),
        (["validate", "--orthography", "latin_1995", "--ignore", "round-trip"], b"x", "unknown code: 'round-trip'"),
        ([], b"", None),
        (["validate"], b"x", None),
    ],
)
def test_errors_exit_with_code_2(run, argv, stdin, message):
    code, out, err = run(argv, stdin)
    assert (code, out) == (2, "")
    if message is not None:
        assert message in err


def test_a_file_that_is_not_utf_8_is_named(run, tmp_path):
    path = tmp_path / "latin1.txt"
    path.write_bytes("Gödel".encode("latin-1"))
    code, _, err = run(["convert", str(path)])
    assert code == 2 and f"{path} is not UTF-8 (byte 1)" in err


def test_version(run):
    assert run(["--version"]) == (0, f"akademtranslit {__version__} (rules {RULES_VERSION})\n", "")


def test_python_m_akademtranslit():
    # The package this test imported, wherever it is: src/ or an installed wheel.
    env = dict(os.environ, PYTHONPATH=str(Path(akademtranslit.__file__).resolve().parent.parent))
    done = subprocess.run(
        [sys.executable, "-m", "akademtranslit", "--version"], capture_output=True, env=env, timeout=60
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.decode("utf-8").strip() == "akademtranslit 0.3.0 (rules uz-2026-alphabet+project-2026.11)"
