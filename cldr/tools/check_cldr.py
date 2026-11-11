"""Check the proposed CLDR data for Uzbek against ICU and against AkademTranslit.

Usage:
    python tools/check_cldr.py GOLDEN_DIR [--write-tests]

GOLDEN_DIR holds ``inputs.json`` and ``golden-<version>.json`` from the
AkademTranslit release (the ``golden/`` folder of the repository, or the
release assets).

Needs PyICU (``pip install PyICU``; it needs the ICU library) and the
``akademtranslit`` package of the same version as the golden file. Neither is
a dependency of the library itself.

What it checks:

1. Every proposed transform compiles in ICU, in both directions.
2. ``uz_Latn_1995 -> uz_Latn_2026`` and back: equal to the library on every
   golden input written in that orthography.
3. ``uz_Cyrl -> uz_Latn_2026``: equal to the existing ``uz_Cyrl-uz_Latn`` (``reference/``)
   followed by ``uz_Latn_1995 -> uz_Latn_2026``, except where the existing
   transform is ambiguous (с + ҳ). Differences from the library are counted by
   cause.
4. Round trips: Cyrillic -> 2026 -> Cyrillic, and 2026 -> 1995 -> 2026.
5. The proposed collations order the alphabet words the same way as the
   library's ``sort_key``.

With ``--write-tests`` it writes the test files in ``tests/``.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path

import icu

import akademtranslit as at

HERE = Path(__file__).resolve().parent.parent
FWD = icu.UTransDirection.FORWARD
REV = icu.UTransDirection.REVERSE


def load_rules(path: Path, tag: str) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"<" + tag + r"><!\[CDATA\[(.*?)\]\]></" + tag + r">", text, re.S)
    if not m:
        raise SystemExit(f"no <{tag}> CDATA in {path}")
    return m.group(1)


def transliterator(path: Path, direction) -> icu.Transliterator:
    return icu.Transliterator.createFromRules(path.stem, load_rules(path, "tRule"), direction)


def collator(path: Path) -> icu.RuleBasedCollator:
    return icu.RuleBasedCollator(load_rules(path, "cr"))


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


UZBEK_LATIN = set("abcdefghijklmnopqrstuvwxyzğöşçʻʼ")


def explain_common(text: str, got: str, lib: str) -> str | None:
    """Reasons shared by every direction, or None."""
    if text.strip() in {"ʻ", "ʼ", "'", "‘", "’"}:
        return "a lone mark outside a word"
    if nfc(text) != text:
        return "decomposed input: the transform normalizes it, the library does not"
    if any(ch.isalpha() and ch not in UZBEK_LATIN and not ("а" <= ch <= "я" or ch in "ёўқғҳ")
           for ch in nfc(text).lower()):
        return "letters outside the Uzbek alphabet"
    return None


def explain_latin(text: str, got: str, lib: str) -> str:
    """Name the reason a Latin 1995/2026 result differs from the library."""
    common = explain_common(text, got, lib)
    if common:
        return common
    if nfc(got) == nfc(lib):
        return "normalization form only (the transform outputs NFC)"
    if got.lower() == lib.lower():
        return "case: the library re-cases mixed-case words, the transform keeps each letter's case"
    return "unexplained"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("golden_dir", type=Path)
    ap.add_argument("--write-tests", action="store_true")
    args = ap.parse_args()

    inputs = json.loads((args.golden_dir / "inputs.json").read_text(encoding="utf-8"))
    goldens = sorted(args.golden_dir.glob("golden-*.json"))
    golden = json.loads(goldens[-1].read_text(encoding="utf-8"))
    if golden["library_version"] != at.__version__:
        raise SystemExit(f"golden {golden['library_version']} != installed {at.__version__}")
    results = golden["results"]
    cases = [(c["id"], c["text"], results[c["id"]]) for c in inputs["cases"]]

    t = HERE / "transforms"
    l95_26 = transliterator(t / "uz_Latn_1995-uz_Latn_2026.xml", FWD)
    l26_95 = transliterator(t / "uz_Latn_1995-uz_Latn_2026.xml", REV)
    c_26 = transliterator(t / "uz_Cyrl-uz_Latn_2026.xml", FWD)
    l26_c = transliterator(t / "uz_Cyrl-uz_Latn_2026.xml", REV)
    # The existing CLDR transform, from reference/ (a copy of CLDR main), so the
    # baseline does not depend on the CLDR version inside the installed ICU.
    old_c_l = transliterator(HERE / "reference" / "uz_Cyrl-uz_Latn.xml", FWD)
    old_l_c = transliterator(HERE / "reference" / "uz_Cyrl-uz_Latn.xml", REV)

    # 2026 inputs: the golden ones, plus the library's 2026 output for every
    # Cyrillic and 1995 golden input (ids prefixed with "d"). Expected values
    # come from the library.
    cases26: list[tuple[str, str, str, str]] = []
    seen26: set[str] = set()
    for cid, text, r in cases:
        if r["detect_script"] == "latin_2026" and r["script_class"] != "mixed":
            cases26.append((cid, text, r["to_latin_1995"], r["to_cyrillic"]))
            seen26.add(text)
    for cid, text, r in cases:
        if r["detect_script"] in ("cyrillic", "latin_1995") and r["script_class"] == "latin" \
                or r["detect_script"] == "cyrillic" and r["script_class"] == "cyrillic":
            y = r["to_latin_2026"]
            if y in seen26 or at.script_class(y) != "latin" or not any(ch.isalpha() for ch in y):
                continue
            seen26.add(y)
            cases26.append(("d" + cid, y, at.convert(y, source="latin_2026", target="latin_1995"),
                            at.convert(y, source="latin_2026", target="cyrillic")))

    report: list[str] = [f"ICU {icu.ICU_VERSION}, Unicode {icu.UNICODE_VERSION}, "
                         f"akademtranslit {at.__version__}, {len(cases)} golden inputs, "
                         f"{len(cases26)} inputs in the 2026 orthography (golden and derived)", ""]
    failures = 0

    def section(title: str) -> None:
        report.append(f"## {title}")

    # 2. 1995 <-> 2026 against the library.
    section("1995 -> 2026 and 2026 -> 1995 against the library")
    tests_95_26, tests_26_95 = [], []
    rows_95 = [(cid, text, r["to_latin_2026"]) for cid, text, r in cases
               if r["detect_script"] == "latin_1995" and r["script_class"] != "mixed"]
    rows_26 = [(cid, text, exp95) for cid, text, exp95, _cyr in cases26]
    for direction, rows, trans, store in (
        ("1995->2026", rows_95, l95_26, tests_95_26),
        ("2026->1995", rows_26, l26_95, tests_26_95),
    ):
        n = 0
        kinds: collections.Counter[str] = collections.Counter()
        for cid, text, lib in rows:
            n += 1
            got = trans.transliterate(text)
            store.append((cid, text, got))
            if got == lib:
                continue
            kind = explain_latin(text, got, lib)
            kinds[kind] += 1
            report.append(f"- {direction} {cid} [{kind}]: {text!r} -> CLDR {got!r}, library {lib!r}")
        report.append(f"{direction}: {n} inputs, {sum(kinds.values())} differ — " +
                      (", ".join(f"{k}: {v}" for k, v in kinds.most_common()) or "none"))
        failures += kinds["unexplained"]
    report.append("")

    # 3. Cyrillic -> 2026: consistency with the existing transform, and the library.
    section("Cyrillic -> 2026")
    tests_c_26 = []
    chain_diff = []
    causes: collections.Counter[str] = collections.Counter()
    lib_diff = []
    for cid, text, r in cases:
        if r["detect_script"] != "cyrillic" or r["script_class"] == "mixed":
            continue
        got = c_26.transliterate(text)
        tests_c_26.append((cid, text, got))
        via_old = l95_26.transliterate(old_c_l.transliterate(text))
        if got != via_old:
            chain_diff.append((cid, text, got, via_old))
        lib = r["to_latin_2026"]
        if got != lib:
            low = text.lower()
            if "сҳ" in low:
                cause = "с+ҳ"
            elif "ц" in low:
                cause = "ц: library ts/s by position, CLDR ts"
            elif "ъ" in low:
                cause = "ъ: library drops it before е ё ю я after a consonant and after ў"
            elif any(ch.isupper() for ch in text) and got.lower() == lib.lower():
                cause = "case"
            elif set(low) & set("щыңәөүһ"):
                cause = "letters outside the Uzbek alphabet (щ ы and others): the library folds them, CLDR keeps them"
            else:
                cause = "other"
            causes[cause] += 1
            lib_diff.append((cid, text, got, lib, cause))
    report.append(f"inputs: {len(tests_c_26)}")
    report.append(f"differs from existing uz_Cyrl-uz_Latn + 1995->2026: {len(chain_diff)}")
    for cid, text, got, via in chain_diff:
        report.append(f"- {cid}: {text!r} -> new {got!r}, via existing {via!r}")
    report.append(f"differs from the library: {len(lib_diff)} — " +
                  ", ".join(f"{k}: {v}" for k, v in causes.most_common()))
    for cid, text, got, lib, cause in lib_diff:
        report.append(f"- {cid} [{cause}]: {text!r} -> CLDR {got!r}, library {lib!r}")
    unexplained = [d for d in chain_diff
                   if "сҳ" not in d[1].lower() and d[2].lower() != d[3].lower()]
    report.append("  (expected: с + ҳ, which the existing transform writes as the digraph sh; "
                  "and a single capital Е Ё Ю Я Ц, now Ye Yo Yu Ya Ts)")
    failures += len(unexplained) + causes["other"]
    report.append("")

    # 4. Round trips.
    section("Round trips")
    rt_bad = []
    old_ok = 0
    for cid, text, got in tests_c_26:
        back = l26_c.transliterate(got)
        old_back = old_l_c.transliterate(old_c_l.transliterate(text))
        old_ok += old_back == text
        if back != text:
            rt_bad.append((cid, text, got, back, old_back))
    report.append(f"Cyrillic -> 2026 -> Cyrillic: {len(tests_c_26) - len(rt_bad)} of {len(tests_c_26)} come back unchanged "
                  f"(the existing Cyrillic -> 1995 -> Cyrillic: {old_ok})")
    for cid, text, got, back, old_back in rt_bad:
        report.append(f"- {cid}: {text!r} -> {got!r} -> {back!r} (existing 1995 round trip: {old_back!r})")
    rt26 = alias = 0
    for cid, text, got in tests_26_95:
        if l95_26.transliterate(got) != nfc(text):
            if set(unicodedata.normalize("NFD", text)) & {"\u0304", "\u030c"}:
                alias += 1
                continue
            rt26 += 1
            report.append(f"- 2026 round trip {cid}: {text!r} -> {got!r} -> {l95_26.transliterate(got)!r}")
    report.append(f"2026 -> 1995 -> 2026: {len(tests_26_95) - rt26 - alias} of {len(tests_26_95)} come back unchanged; "
                  f"{alias} more are the draft spellings ō ǒ, which come back as ö")
    failures += rt26
    report.append("")

    # 2026 -> Cyrillic against the library and the existing 1995 -> Cyrillic.
    section("2026 -> Cyrillic")
    tests_26_c = []
    lc: collections.Counter[str] = collections.Counter()
    for cid, text, _exp95, lib in cases26:
        got = l26_c.transliterate(text)
        tests_26_c.append((cid, text, got))
        if got == lib:
            continue
        low = text.lower()
        common = explain_common(text, got, lib)
        if common:
            cause = common
        elif "ts" in low:
            cause = "ts: the library reads т + с before an Uzbek suffix, CLDR always ц"
        elif got.lower() == lib.lower():
            cause = "case"
        else:
            cause = "unexplained"
        lc[cause] += 1
        report.append(f"- {cid} [{cause}]: {text!r} -> CLDR {got!r}, library {lib!r}")
    report.append(f"2026 -> Cyrillic: {len(tests_26_c)} inputs, {sum(lc.values())} differ from the library — " +
                  (", ".join(f"{k}: {v}" for k, v in lc.most_common()) or "none"))
    failures += lc["unexplained"]
    report.append("")

    # 5. Collation.
    section("Collation against the library's sort_key")
    col = HERE / "collation"
    uz = collator(col / "uz.xml")
    uz_cyrl = collator(col / "uz_Cyrl.xml")
    for c in (uz, uz_cyrl):
        c.setStrength(icu.Collator.PRIMARY)
    uz_b = collator(col / "uz_Latn_2026-option-b.xml")
    uz_b.setStrength(icu.Collator.PRIMARY)
    singles_1995 = {x for x in at.LATIN_1995_ALPHABET if len(x) == 1}

    def only_alphabet(w: str, key: str) -> bool:
        if key == "latin_2026":
            return set(w) <= set(at.LATIN_2026_ALPHABET) | {at.TUTUQ}
        if key == "latin_1995":
            rest = w
            for unit in ("oʻ", "gʻ", "sʼh", "sh", "ch"):
                rest = rest.replace(unit, "")
            return set(rest) <= singles_1995 | {at.TUTUQ}
        return set(w) <= set(at.CYRILLIC_ALPHABET)

    words: dict[str, set[str]] = {k: set() for k in ("latin_2026", "latin_1995", "cyrillic")}
    for _cid, _text, r in cases:
        for key, field in (("latin_2026", "to_latin_2026"), ("latin_1995", "to_latin_1995"),
                           ("cyrillic", "to_cyrillic")):
            for w in re.findall(r"[^\W\d_]+(?:[ʻʼ][^\W\d_]+)*ʻ?", r[field].lower()):
                if only_alphabet(w, key):
                    words[key].add(w)
    sort_lists = {}
    for key, c, label in (("latin_2026", uz, "A"), ("latin_2026", uz_b, "B"),
                          ("latin_1995", uz, "A"), ("cyrillic", uz_cyrl, "")):
        ws = sorted(words[key])
        lib = sorted(ws, key=lambda w: at.sort_key(w, key))
        cl = sorted(ws, key=c.getSortKey)
        bad = 0
        for a, b in zip(lib, lib[1:]):
            lw = at.sort_key(a, key)[0] < at.sort_key(b, key)[0]
            if lw and c.compare(a, b) > 0:
                bad += 1
                report.append(f"- {key} {label}: library {a!r} < {b!r}, ICU the other way")
        sort_lists[(key, label)] = cl
        name = f"{key}" + (f" (option {label})" if label else "")
        report.append(f"{name}: {len(ws)} words, {bad} order differences")
        if label == "A" and key == "latin_2026":
            report.append("  (option A: a real s + h in 2026 text, as in Ishoq or ashob, meets the 1995 contraction sh)")
        else:
            failures += bad
    report.append("")

    # The test files: written with --write-tests, otherwise compared.
    files: dict[str, str] = {}

    def esc(x: str) -> str:
        return (x.replace("\\", "\\\\").replace("\t", "\\t")
                 .replace("\n", "\\n").replace("\r", "\\r"))

    def tsv(rows) -> str:
        head = "# id\tsource\texpected  (backslash escapes: \\\\ \\t \\n \\r)\n"
        return head + "".join(f"{cid}\t{esc(src)}\t{esc(exp)}\n" for cid, src, exp in rows)

    files["uz-Latn-2026-t-uz-latn-1995.tsv"] = tsv(tests_95_26)
    files["uz-Latn-1995-t-uz-latn-2026.tsv"] = tsv(tests_26_95)
    files["uz-Latn-2026-t-uz-cyrl.tsv"] = tsv(tests_c_26)
    files["uz-Cyrl-t-uz-latn-2026.tsv"] = tsv(tests_26_c)

    # The same cases in CLDR's common/testData/transforms format: source TAB
    # expected, no header; cases with a tab or a line break are left out.
    def cldr(rows) -> str:
        seen, lines = set(), []
        for _cid, src, exp in rows:
            if any(ch in src + exp for ch in "\t\n\r") or src in seen or not src.strip():
                continue
            seen.add(src)
            lines.append(f"{src}\t{exp}\n")
        return "".join(lines)

    files["cldr/uz-Latn-2026-t-uz-Latn-1995.txt"] = cldr(tests_95_26)
    files["cldr/uz-Latn-1995-t-uz-Latn-2026.txt"] = cldr(tests_26_95)
    files["cldr/uz-Latn-2026-t-uz-Cyrl.txt"] = cldr(tests_c_26)
    files["cldr/uz-Cyrl-t-uz-Latn-2026.txt"] = cldr(tests_26_c)
    for key, label, name in (("latin_2026", "A", "collation-uz-latn-2026-option-a.txt"),
                             ("latin_2026", "B", "collation-uz-latn-2026-option-b.txt"),
                             ("latin_1995", "A", "collation-uz-latn-1995.txt"),
                             ("cyrillic", "", "collation-uz-cyrl.txt")):
        files[name] = "\n".join(sort_lists[(key, label)]) + "\n"
    out = HERE / "tests"
    if args.write_tests:
        (out / "cldr").mkdir(parents=True, exist_ok=True)
        for name, body in files.items():
            with (out / name).open("w", encoding="utf-8", newline="\n") as f:
                f.write(body)
    else:
        def read(path: Path) -> str:
            with path.open(encoding="utf-8", newline="") as f:
                return f.read()

        stale = [n for n, body in files.items() if not (out / n).exists() or read(out / n) != body]
        report.append(f"test files in tests/: {len(files) - len(stale)} of {len(files)} match"
                      + (f"; differ: {', '.join(stale)}" if stale else ""))
        failures += len(stale)
        report.append("")

    report.append(f"RESULT: {'ok' if failures == 0 else f'{failures} unexplained difference(s)'}")
    print("\n".join(report))
    if args.write_tests:
        with (out / "check-report.txt").open("w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(report) + "\n")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
