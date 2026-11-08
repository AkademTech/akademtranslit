# Contributing

Thank you for helping. This project follows a [code of conduct](CODE_OF_CONDUCT.md).

## Set up

With the standard library only:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[test]"
```

Or with [uv](https://docs.astral.sh/uv/), without installing anything into the
project:

```bash
uv run --no-project --with pytest -- python -m pytest
```

## Run the tests

```bash
.venv/bin/python -m pytest              # tests, docstring examples, README examples
.venv/bin/python tools/golden.py --check
```

Both must pass on every supported Python version, 3.9 and newer.

## The golden rule

`golden/` holds the library's output on a fixed set of inputs. Downstream code
relies on it byte for byte, so **every change to any output must be visible**:

1. Change the code, with a test that fails before the change and passes after.
2. Run `python tools/golden.py --write`. It rewrites
   `golden/golden-<version>.json` and `golden/SHA256SUMS`.
3. Run `python tools/golden.py --diff golden/golden-<previous>.json
   golden/golden-<version>.json` and put the result in the pull request.
   Every changed line needs a reason.
4. Commit the updated golden files in the same commit as the code.

`golden/inputs.json` is append-only. New inputs go at the end with new ids; an
existing `id` is never changed or reused. The output of `normalize()` never
changes in a patch release.

## Constraints

- **No runtime dependencies.** The library uses the Python standard library
  only. Test and build tools (pytest, setuptools, twine) are fine.
- **Python 3.9 syntax.** No `match`, no `X | Y` types evaluated at run time, no
  standard-library APIs newer than 3.9. Keep `from __future__ import
  annotations` at the top of each module.
- **Files** are read with `encoding="utf-8"` and written with `newline="\n"`,
  so the bytes are the same on every platform.
- **Test examples** use common words, widely known terms and common names
  (`Ali`, `Valiyev`). No personal data, no real people's records, no text from
  private sources.
- Keep commits small and focused; write commit messages in English.

## Reporting security issues

Not in a public issue: see [SECURITY.md](SECURITY.md).
