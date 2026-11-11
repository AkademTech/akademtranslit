"""The package does no I/O of its own: no network, no files, no subprocesses.

PRIVACY.md promises this. The tests below read the package source with
``ast`` and fail if a module imports anything but ``re`` and
``unicodedata``, or calls one of the built-ins that open files or run code.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "akademtranslit"

ALLOWED_IMPORTS = frozenset({"re", "unicodedata"})

FORBIDDEN_CALLS = frozenset(
    {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
)


def _package_files() -> list[Path]:
    return sorted(PACKAGE.glob("*.py"))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(tree: ast.Module) -> list[str]:
    """Top-level names of the absolute imports in ``tree``, except __future__."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0 or node.module == "__future__":
                continue
            names.append(node.module.split(".")[0])
    return names


def test_package_imports_only_re_and_unicodedata():
    offenders = [
        (path.name, module)
        for path in _package_files()
        for module in _imported_modules(_parse(path))
        if module not in ALLOWED_IMPORTS
    ]
    assert offenders == []


def test_package_calls_no_file_or_code_builtins():
    offenders = [
        (path.name, node.lineno, node.func.id)
        for path in _package_files()
        for node in ast.walk(_parse(path))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in FORBIDDEN_CALLS
    ]
    assert offenders == []


def test_package_files_are_found():
    assert _package_files(), f"no .py files under {PACKAGE}"
