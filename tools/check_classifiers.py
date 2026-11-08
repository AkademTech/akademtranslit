#!/usr/bin/env python3
"""Check the trove classifiers in pyproject.toml against the PyPI list.

PyPI rejects an upload that carries a classifier it does not know, and
``twine check --strict`` does not look at classifiers. This script does:

    python tools/check_classifiers.py                    # ./pyproject.toml
    python tools/check_classifiers.py path/to/pyproject.toml

Exit codes: 0 when every classifier is valid; 1 when one is invalid or
deprecated; 2 when the check cannot run (Python older than 3.11, no
``trove-classifiers``, or an unreadable file).

Needs Python 3.11+ (``tomllib``) and the ``trove-classifiers`` package; CI
installs it for this step only. Not part of the installed package.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pyproject", nargs="?", default="pyproject.toml",
                        help="path to pyproject.toml (default: %(default)s)")
    args = parser.parse_args(argv)

    try:
        import tomllib
    except ImportError:
        print(f"error: Python 3.11 or newer is needed (tomllib); this is "
              f"{sys.version.split()[0]}", file=sys.stderr)
        return 2
    try:
        import trove_classifiers
    except ImportError:
        print("error: the trove_classifiers module is missing; "
              "install trove-classifiers", file=sys.stderr)
        return 2

    path = Path(args.pyproject)
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return 2
    classifiers = data.get("project", {}).get("classifiers", [])
    if not isinstance(classifiers, list) or not all(isinstance(c, str) for c in classifiers):
        print(f"error: project.classifiers in {path} is not a list of strings",
              file=sys.stderr)
        return 2

    bad = 0
    for name in classifiers:
        if name in trove_classifiers.deprecated_classifiers:
            # Deprecated names are not in `classifiers`; say so, not "invalid".
            use = trove_classifiers.deprecated_classifiers[name]
            hint = f" (use: {', '.join(use)})" if use else ""
            print(f"deprecated: {name}{hint}")
            bad += 1
        elif name not in trove_classifiers.classifiers:
            print(f"invalid: {name}")
            bad += 1
    if bad:
        return 1
    print(f"ok: {len(classifiers)} classifiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
