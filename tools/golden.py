#!/usr/bin/env python3
"""Golden vectors: the library's output on a fixed set of inputs, sealed.

Downstream code (and the ports to other languages) switches to this library
only when its output matches byte for byte. The golden files are how that is
checked, and how every change to the output is made visible.

    python tools/golden.py --write             # regenerate for the current version
    python tools/golden.py --check             # exit 1 if anything differs
    python tools/golden.py --diff OLD NEW      # Markdown report of the differences

``golden/inputs.json`` is append-only: an ``id`` never changes and is never
reused. ``golden/golden-<version>.json`` holds one result per input and field.
``golden/SHA256SUMS`` lists every ``.json`` in ``golden/`` and can be checked
with ``shasum -a 256 -c SHA256SUMS``.

``--check`` also checks the rules version: two consecutive golden files that
record one (0.3.0 on) and differ in the output of a conversion function must
differ in ``rules_version`` too. :func:`rules_version_problems` does that and
can be called on its own.

Not part of the installed package. The library is imported from ``src/``, and
only when a command needs it: loading this file imports nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO / "golden"
INPUTS = GOLDEN_DIR / "inputs.json"
SUMS = GOLDEN_DIR / "SHA256SUMS"

#: The library, once :func:`load_library` has imported it.
lib = None

# The fields that hold the output of convert, to_latin and to_cyrillic: the
# ones RULES_VERSION answers for.
CONVERSION_FIELDS = ("to_cyrillic", "to_latin_1995", "to_latin_2026")
CONVERSION_FIELD_PREFIX = "convert_"

SCHEMA = "akademtranslit-golden/1"
INPUTS_SCHEMA = "akademtranslit-golden-inputs/1"


def load_library(src: Path = REPO / "src") -> None:
    """Import ``akademtranslit`` from ``src`` as :data:`lib`."""
    global lib
    sys.path.insert(0, str(src))
    import akademtranslit

    lib = akademtranslit


def canonical(obj) -> bytes:
    """The one serialisation every golden file uses; hashes are taken from it."""
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fields() -> dict:
    """Field name -> function of the input text.

    A field is written only if the library has the function, so the generator
    runs unchanged against older versions.
    """
    out = {
        "detect_script": lib.detect_script,
        "normalize": lib.normalize,
        "to_cyrillic": lib.to_cyrillic,
        "to_latin_1995": lambda text: lib.to_latin(text, variant="latin_1995"),
        "to_latin_2026": lambda text: lib.to_latin(text, variant="latin_2026"),
    }
    if hasattr(lib, "sort_key"):
        for orthography in ("cyrillic", "latin_1995", "latin_2026"):
            out["sort_key_" + orthography] = (
                lambda text, o=orthography: list(lib.sort_key(text, o)[0])
            )
    if hasattr(lib, "normalize_apostrophes"):
        for style in ("unicode", "ascii"):
            out["normalize_apostrophes_" + style] = (
                lambda text, s=style: lib.normalize_apostrophes(text, s)
            )
    if hasattr(lib, "script_class"):
        out["script_class"] = lib.script_class
    if hasattr(lib, "cyrillic_language"):
        out["cyrillic_language"] = lib.cyrillic_language
    return out


def load_inputs() -> tuple:
    data = INPUTS.read_bytes()
    doc = json.loads(data.decode("utf-8"))
    if doc.get("schema") != INPUTS_SCHEMA:
        raise SystemExit(f"{INPUTS.name}: unexpected schema {doc.get('schema')!r}")
    return data, doc["cases"]


def compute() -> bytes:
    data, cases = load_inputs()
    funcs = fields()
    results = {}
    for case in cases:
        row = {}
        for name, func in funcs.items():
            try:
                row[name] = func(case["text"])
            except Exception as exc:  # recorded, not raised: an error is an output too
                row[name] = {"error": type(exc).__name__}
        results[case["id"]] = row
    return canonical({
        "schema": SCHEMA,
        "library_version": lib.__version__,
        "inputs_sha256": sha256(data),
        "results": results,
    })


def golden_path() -> Path:
    return GOLDEN_DIR / f"golden-{lib.__version__}.json"


def sums_text() -> bytes:
    lines = [
        f"{sha256(path.read_bytes())}  {path.name}\n"
        for path in sorted(GOLDEN_DIR.glob("*.json"), key=lambda p: p.name)
    ]
    return "".join(lines).encode("utf-8")


def write() -> int:
    path = golden_path()
    path.write_bytes(compute())
    SUMS.write_bytes(sums_text())
    print(f"wrote {path.relative_to(REPO).as_posix()} and {SUMS.relative_to(REPO).as_posix()}")
    return 0


def _is_conversion_field(name: str) -> bool:
    return name in CONVERSION_FIELDS or name.startswith(CONVERSION_FIELD_PREFIX)


def _version_key(version: str) -> tuple:
    return tuple(int(number) for number in re.findall(r"\d+", version))


def rules_version_problems(directory: Path) -> list:
    """The consecutive golden files in ``directory`` that break the rules version.

    Only files with a ``rules_version`` take part, in the order of their
    ``library_version``. For each pair of consecutive ones, if a conversion
    field (``to_cyrillic``, ``to_latin_1995``, ``to_latin_2026``,
    ``convert_*``) differs on an input both have, their ``rules_version`` must
    differ too. Returns one message per pair that breaks this; none is ``[]``.
    """
    docs = []
    for path in sorted(Path(directory).glob("golden-*.json")):
        doc = json.loads(path.read_bytes().decode("utf-8"))
        if "rules_version" in doc:
            docs.append((path.name, doc))
    docs.sort(key=lambda item: _version_key(item[1]["library_version"]))

    problems = []
    for (old_name, old), (new_name, new) in zip(docs, docs[1:]):
        if old["rules_version"] != new["rules_version"]:
            continue
        changed = set()
        for case_id in sorted(set(old["results"]) & set(new["results"])):
            a, b = old["results"][case_id], new["results"][case_id]
            changed.update(f for f in set(a) & set(b) if _is_conversion_field(f) and a[f] != b[f])
        if changed:
            problems.append(
                f"{old_name} -> {new_name}: {', '.join(sorted(changed))} changed, "
                f"but rules_version is {new['rules_version']!r} in both"
            )
    return problems


def check() -> int:
    path = golden_path()
    ok = True
    if not path.exists():
        print(f"missing: {path.relative_to(REPO).as_posix()}")
        return 1
    if path.read_bytes() != compute():
        print(f"differs: {path.name} does not match the output of src/ "
              f"(run --write, then --diff against the previous golden file)")
        ok = False
    if not SUMS.exists() or SUMS.read_bytes() != sums_text():
        print(f"differs: {SUMS.name} does not match the files in golden/")
        ok = False
    for problem in rules_version_problems(GOLDEN_DIR):
        print(f"rules version: {problem}")
        ok = False
    if ok:
        print(f"ok: {path.name} and {SUMS.name} match")
    return 0 if ok else 1


def _cell(value) -> str:
    text = json.dumps(value, ensure_ascii=False).replace("|", "\\|")
    fence = "``" if "`" in text else "`"
    pad = " " if fence == "``" else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def diff(old_path: str, new_path: str) -> int:
    old = json.loads(Path(old_path).read_bytes().decode("utf-8"))
    new = json.loads(Path(new_path).read_bytes().decode("utf-8"))
    _, cases = load_inputs()
    texts = {case["id"]: case["text"] for case in cases}

    ids = sorted(set(old["results"]) & set(new["results"]))
    old_fields = {f for row in old["results"].values() for f in row}
    new_fields = {f for row in new["results"].values() for f in row}
    shared = sorted(old_fields & new_fields)

    changes = {f: [] for f in shared}
    for case_id in ids:
        a, b = old["results"][case_id], new["results"][case_id]
        for f in shared:
            if f in a and f in b and a[f] != b[f]:
                changes[f].append((case_id, a[f], b[f]))

    out = [
        f"# Golden diff: {old['library_version']} -> {new['library_version']}",
        "",
        f"- old: `{Path(old_path).name}` (inputs sha256 `{old['inputs_sha256']}`)",
        f"- new: `{Path(new_path).name}` (inputs sha256 `{new['inputs_sha256']}`)",
        f"- inputs compared: {len(ids)}",
        f"- fields only in old: {', '.join(sorted(old_fields - new_fields)) or 'none'}",
        f"- fields only in new: {', '.join(sorted(new_fields - old_fields)) or 'none'}",
        "",
        "| field | changed |",
        "| --- | ---: |",
    ]
    out += [f"| {f} | {len(changes[f])} |" for f in shared]
    for f in shared:
        if not changes[f]:
            continue
        out += ["", f"## {f} ({len(changes[f])})", "", "| id | input | old | new |",
                "| --- | --- | --- | --- |"]
        out += [
            f"| {case_id} | {_cell(texts.get(case_id, '?'))} | {_cell(a)} | {_cell(b)} |"
            for case_id, a, b in changes[f]
        ]
    sys.stdout.buffer.write(("\n".join(out) + "\n").encode("utf-8"))
    sys.stdout.flush()
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true", help="write golden-<version>.json and SHA256SUMS")
    group.add_argument("--check", action="store_true", help="exit 1 unless both match src/")
    group.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"), help="Markdown diff of two golden files")
    args = parser.parse_args(argv)
    load_library()
    if args.write:
        return write()
    if args.check:
        return check()
    return diff(*args.diff)


if __name__ == "__main__":
    sys.exit(main())
