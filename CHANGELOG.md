# Changelog

## 0.1.1 — 2026-10-16

### Fixed

- Latin → Cyrillic: `y` before `oʻ` is `й` + `ў` (`yoʻq` → `йўқ`), not `ё` and a stray mark (`ёʻқ`).
- Latin → Cyrillic: `ts` is `т` + `с` before an Uzbek suffix (`ketsa` → `кетса`, `hayotsiz` → `ҳаётсиз`) and `т` + `ш` before `h` (`adabiyotshunos` → `адабиётшунос`); loanwords keep `ц`, with the misses listed in the README.
- Words in all caps that contain `ʻ` or `ʼ` stay in all caps (`OʻZBEKISTON` → `ЎЗБЕКИСТОН`, `ÖZBEKISTON`); they came out as `Ўзбекистон`.

## 0.1.0 — 2026-08-15

First release.
