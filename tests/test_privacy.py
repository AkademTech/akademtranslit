"""The package does no I/O of its own: no network, no files, no subprocesses.

PRIVACY.md promises this. The tests below read the package source with
``ast``. The library -- every module but the command-line tool -- must import
nothing but ``re``, ``unicodedata`` and ``warnings`` and call none of the
built-ins that open files or run code. The command-line tool (``cli.py`` and
``__main__.py``) may import ``argparse``, ``json``, ``sys`` and ``warnings``
besides the package, and may open a file only to read it (mode ``"rb"``); no
library module imports it.
"""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent.parent / "src" / "akademtranslit"

# The modules of the command-line tool, which the library does not import.
TOOL_FILES = ("cli.py", "__main__.py")

ALLOWED_IMPORTS = frozenset({"re", "unicodedata", "warnings"})
TOOL_IMPORTS = frozenset({"argparse", "json", "sys", "warnings"})

FORBIDDEN_CALLS = frozenset(
    {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
)


def _package_files() -> list[Path]:
    """The library's modules: every module but the command-line tool's."""
    return sorted(path for path in PACKAGE.glob("*.py") if path.name not in TOOL_FILES)


def _tool_file(name: str) -> Path:
    return PACKAGE / name


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


def _package_imports(tree: ast.Module) -> list[str]:
    """The package modules that the relative imports in ``tree`` name:
    ``from .cli import main`` gives ``cli``, ``from . import cli`` gives ``cli``
    (and any other name it imports)."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            if node.module:
                names.append(node.module.split(".")[0])
            else:
                names.extend(alias.name for alias in node.names)
    return names


def _calls(tree: ast.Module, names) -> list:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in names
    ]


# --- the library ------------------------------------------------------------------


def test_package_imports_only_re_unicodedata_and_warnings():
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
        for node in _calls(_parse(path), FORBIDDEN_CALLS)
    ]
    assert offenders == []


def test_package_files_are_found():
    assert _package_files(), f"no .py files under {PACKAGE}"
    assert "__init__.py" in [path.name for path in _package_files()]


def test_no_library_module_imports_the_command_line_tool():
    offenders = [
        (path.name, module)
        for path in _package_files()
        for module in _package_imports(_parse(path))
        if module in ("cli", "__main__")
    ]
    assert offenders == []


# --- the command-line tool ------------------------------------------------------------


def test_the_tool_files_are_found():
    assert [name for name in TOOL_FILES if not _tool_file(name).is_file()] == []


def test_the_tool_imports_only_argparse_json_sys_and_warnings():
    imported = set(_imported_modules(_parse(_tool_file("cli.py"))))
    assert imported and imported <= TOOL_IMPORTS, sorted(imported - TOOL_IMPORTS)


def test_main_imports_only_from_the_package():
    tree = _parse(_tool_file("__main__.py"))
    assert _imported_modules(tree) == []
    assert _package_imports(tree) == ["cli"]


def test_the_tool_opens_files_only_to_read_them():
    calls = _calls(_parse(_tool_file("cli.py")), {"open"})
    assert calls, "cli.py reads FILE with open(name, 'rb')"
    for call in calls:
        assert len(call.args) == 2 and not call.keywords, call.lineno
        mode = call.args[1]
        assert isinstance(mode, ast.Constant) and mode.value == "rb", call.lineno


def test_the_tool_calls_no_code_builtins():
    offenders = [
        (name, node.lineno, node.func.id)
        for name in TOOL_FILES
        for node in _calls(_parse(_tool_file(name)), FORBIDDEN_CALLS - {"open"})
    ]
    assert offenders == []
