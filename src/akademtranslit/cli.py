"""The command-line tool: ``akademtranslit`` and ``python -m akademtranslit``.

::

    akademtranslit [--version] COMMAND ...
    akademtranslit convert   [FILE] [--from SCRIPT] [--to SCRIPT] [--no-protect]
    akademtranslit validate  [FILE] --orthography SCRIPT [--ignore CODES] [--no-protect] [--json]
    akademtranslit report    [FILE] [--no-protect] [--json]
    akademtranslit normalize [FILE]

Each command reads ``FILE``, or standard input when it is ``-`` or not given,
as UTF-8, and writes UTF-8 to standard output; line ends come out as they
went in. Nothing else is read or written. ``SCRIPT`` is one of
:data:`~akademtranslit.tables.SCRIPTS` or a language tag for one of them.

* ``convert`` writes :func:`~akademtranslit.convert` of the text (``--from``
  is ``auto`` and ``--to`` is ``latin_2026`` unless given).
* ``validate`` writes one line per finding of
  :func:`~akademtranslit.validate`, ``NAME:LINE:COLUMN: CODE: FOUND``, with
  ``-> SUGGESTION`` when there is one; lines and columns count from 1,
  columns in code points. ``invisible`` and ``decomposed`` show code points.
  ``--ignore`` leaves out the codes it lists, separated by commas.
* ``report`` writes :func:`~akademtranslit.migration_report` of the text.
* ``normalize`` writes :func:`~akademtranslit.normalize` of each line.

``--json`` writes a JSON document instead. Exit codes: 0; 1 when
``validate`` finds something, or when ``report`` finds a text that does not
come back from ``latin_2026`` or anything but ``separator`` to check; 2 for
an error (a file that cannot be read, input that is not UTF-8, an unknown
orthography or code). The library's warnings go to standard error as
``akademtranslit: warning: ...``.

Not imported by the package: ``import akademtranslit`` does not load it.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings

from . import SCRIPTS, __version__, convert, migration_report, normalize, validate
from .checks import CODES, SEPARATOR
from .tables import RULES_VERSION
from .tags import _orthography

PROG = "akademtranslit"
STDIN = "-"
STDIN_NAME = "<stdin>"

# The codes whose found text and suggestion are written as code points.
_BY_CODE_POINT = ("invisible", "decomposed")


def main(argv=None) -> int:
    """Run the tool with ``argv`` (default: ``sys.argv[1:]``); return the
    exit code. An error raises :class:`SystemExit` with code 2."""
    parser = _parser()
    args = parser.parse_args(argv)
    caught = []
    try:
        return args.run(args.parser, args, caught)
    finally:
        for warning in caught:
            sys.stderr.write(f"{PROG}: warning: {warning.message}\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Uzbek transliteration across three orthographies.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"{PROG} {__version__} (rules {RULES_VERSION})"
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    def command(name, run, summary):
        sub = commands.add_parser(name, help=summary, description=summary)
        sub.add_argument(
            "file", nargs="?", default=STDIN, metavar="FILE", help="a file, or - for standard input (the default)"
        )
        sub.set_defaults(run=run, parser=sub)
        return sub

    sub = command("convert", _convert, "convert a text to another orthography")
    sub.add_argument(
        "--from", dest="source", default="auto", metavar="SCRIPT", help="the orthography of the text (default: auto)"
    )
    sub.add_argument(
        "--to", dest="target", default="latin_2026", metavar="SCRIPT",
        help="the orthography to write (default: latin_2026)",
    )
    sub.add_argument("--no-protect", action="store_true", help="convert URLs, e-mail addresses and the like too")

    sub = command("validate", _validate, "check a text against one orthography")
    sub.add_argument(
        "--orthography", required=True, metavar="SCRIPT", help="the orthography the text is meant to be in"
    )
    sub.add_argument(
        "--ignore", type=_codes, default=(), metavar="CODES", help="codes to leave out, separated by commas"
    )
    sub.add_argument("--no-protect", action="store_true", help="check URLs, e-mail addresses and the like too")
    sub.add_argument("--json", action="store_true", help="write JSON")

    sub = command("report", _report, "report on converting a latin_1995 text to latin_2026")
    sub.add_argument(
        "--no-protect", action="store_true", help="convert and check URLs, e-mail addresses and the like too"
    )
    sub.add_argument("--json", action="store_true", help="write JSON")

    command("normalize", _normalize, "write the search key of each line")
    return parser


def _codes(value: str) -> tuple:
    codes = tuple(code for code in value.split(",") if code)
    for code in codes:
        if code not in CODES:
            raise argparse.ArgumentTypeError(f"unknown code: {code!r}; expected one of {', '.join(CODES)}")
    return codes


# --- the commands -----------------------------------------------------------------


def _convert(parser, args, caught) -> int:
    with _Calls(parser, caught):
        source = _script(args.source, "--from", auto=True)
        target = _script(args.target, "--to")
    name, text = _read(parser, args.file)
    with _Calls(parser, caught):
        result = convert(text, source, target, protect=not args.no_protect)
    _write(result)
    return 0


def _validate(parser, args, caught) -> int:
    with _Calls(parser, caught):
        orthography = _script(args.orthography, "--orthography")
    name, text = _read(parser, args.file)
    with _Calls(parser, caught):
        found = validate(text, orthography, protect=not args.no_protect)
    found = [finding for finding in found if finding[2] not in args.ignore]
    if args.json:
        _write_json(_objects(text, found))
    else:
        _write("".join(line + "\n" for line in _lines(name, text, found)))
    return 1 if found else 0


def _report(parser, args, caught) -> int:
    name, text = _read(parser, args.file)
    with _Calls(parser, caught):
        report = migration_report(text, protect=not args.no_protect)
    if args.json:
        _write_json(dict(report, check=_objects(text, report["check"])))
    else:
        summary = [
            f"words: {report['words']}",
            f"changed: {report['changed']}",
            f"protected: {report['protected']}",
            f"round trip: {'yes' if report['round_trip'] else 'no'}",
            f"rules: {report['rules_version']}",
            f"to check: {len(report['check'])}",
        ]
        _write("".join(line + "\n" for line in summary + _lines(name, text, report["check"])))
    fine = report["round_trip"] and all(finding[2] == SEPARATOR for finding in report["check"])
    return 0 if fine else 1


def _normalize(parser, args, caught) -> int:
    name, text = _read(parser, args.file)
    with _Calls(parser, caught):
        _write("".join(normalize(line) + "\n" for line in text.splitlines()))
    return 0


# --- input, output and the library -------------------------------------------------


class _Calls:
    """Around calls to the library: keep its warnings in ``caught``, and make
    a :class:`ValueError` an error of ``parser`` (exit code 2)."""

    def __init__(self, parser, caught):
        self.parser = parser
        self.caught = caught
        self.warnings = warnings.catch_warnings(record=True)

    def __enter__(self):
        self.record = self.warnings.__enter__()
        warnings.simplefilter("always")

    def __exit__(self, kind, exc, traceback):
        self.warnings.__exit__(kind, exc, traceback)
        self.caught.extend(self.record)
        if isinstance(exc, ValueError):
            self.parser.error(str(exc))
        return False


def _script(value: str, option: str, auto: bool = False) -> str:
    """The orthography ``value`` of ``option`` names, read before the input."""
    if value in SCRIPTS or (auto and value == "auto"):
        return value
    expected = f"{SCRIPTS} or 'auto'" if auto else f"{SCRIPTS}"
    return _orthography(
        value, f"argument {option}: unknown orthography: {value!r}; expected one of {expected}", stacklevel=2
    )


def _read(parser, name: str) -> tuple:
    """``(the name to show, the text)`` of ``name``, a path or ``-``."""
    shown = STDIN_NAME if name == STDIN else name
    try:
        if name == STDIN:
            data = sys.stdin.buffer.read()
        else:
            with open(name, "rb") as f:
                data = f.read()
    except OSError as exc:
        parser.error(f"cannot read {shown}: {exc.strerror or exc}")
    try:
        return shown, data.decode("utf-8")
    except UnicodeDecodeError as exc:
        parser.error(f"{shown} is not UTF-8 (byte {exc.start})")


def _write(text: str) -> None:
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.buffer.flush()


def _write_json(obj) -> None:
    _write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def _where(text: str, starts: list) -> list:
    """``(line, column)`` of each of ``starts``, in order, counting from 1;
    columns count code points."""
    out = []
    line, line_start, pos = 1, 0, 0
    for start in starts:
        newlines = text.count("\n", pos, start)
        if newlines:
            line += newlines
            line_start = text.rfind("\n", pos, start) + 1
        pos = start
        out.append((line, start - line_start + 1))
    return out


def _code_points(text: str) -> str:
    return " ".join(f"U+{ord(ch):04X}" for ch in text)


def _lines(name: str, text: str, found: list) -> list:
    out = []
    for (line, column), (start, end, code, suggestion) in zip(_where(text, [f[0] for f in found]), found):
        shown = text[start:end]
        if code in _BY_CODE_POINT:
            shown = _code_points(shown)
            suggestion = _code_points(suggestion) if suggestion else None
        tail = "" if suggestion is None else f" -> {suggestion}"
        out.append(f"{name}:{line}:{column}: {code}: {shown}{tail}")
    return out


def _objects(text: str, found: list) -> list:
    return [
        {
            "line": line,
            "column": column,
            "start": start,
            "end": end,
            "code": code,
            "text": text[start:end],
            "suggestion": suggestion,
        }
        for (line, column), (start, end, code, suggestion) in zip(_where(text, [f[0] for f in found]), found)
    ]
