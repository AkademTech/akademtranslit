// Changes in 0.3.2: Roman numerals, month names, dates and a word-final ц (as
// tests/test_changes_0_3_2.py for the Python library, with the same tables).
//
// Each rule has a section: the examples it was made for, its boundaries, the
// other direction, source "auto", and a protected span, which keeps its text
// whatever the rule says.

import assert from "node:assert/strict";
import { test } from "node:test";

import { CYRILLIC, LATIN_1995, LATIN_2026, convert, toCyrillic } from "../src/index.js";
import { isRomanNumeral } from "../src/rules.js";

const LATIN = [LATIN_1995, LATIN_2026];

// --- TRANSLIT-24: a Roman numeral stays Latin in Cyrillic ------------------------------

const ROMAN_NUMERALS = [
  ["XIX asr", "XIX аср"],
  ["IV bob", "IV боб"],
  ["Pyotr I", "Пётр I"],
  ["XXI asrning oxiri", "XXI асрнинг охири"],
  ["MMXXVI", "MMXXVI"],
  ["CD va DVD", "CD ва ДВД"], // DVD is not a well-formed numeral
  ["XIX.", "XIX."], // more than one letter: a full stop after it is a full stop
  ["I", "I"],
];

// Boundaries: an initial, a known limit, and what is not a numeral.
const NOT_ROMAN_NUMERALS = [
  ["I. Boʻriyev", "И. Бўриев"],
  ["M. Asadullayev", "М. Асадуллаев"],
  ["V. I. Lenin", "В. И. Ленин"],
  ["Pyotr I.", "Пётр И."], // known limit: read as an initial at the end of a sentence
  ["IIII", "ИИИИ"],
  ["Xix", "Хих"],
  ["XIXda", "ХИХда"], // a numeral with a suffix in one word is not a numeral word
];

test("Roman numerals: Latin to Cyrillic", () => {
  for (const [latin, cyrillic] of [...ROMAN_NUMERALS, ...NOT_ROMAN_NUMERALS]) {
    for (const source of [...LATIN, "auto"]) {
      assert.equal(convert(latin, source, CYRILLIC), cyrillic, `${latin} (${source})`);
    }
  }
});

test("Roman numerals: a word in capitals that is a numeral stays Latin (known limit)", () => {
  assert.equal(toCyrillic("MIX"), "MIX");
});

test("Roman numerals: Cyrillic to Latin, already Latin", () => {
  for (const [cyrillic, latin] of [["XIX аср", "XIX asr"], ["Пётр I", "Pyotr I"], ["IV боб", "IV bob"]]) {
    for (const target of LATIN) {
      assert.equal(convert(cyrillic, CYRILLIC, target), latin);
      assert.equal(convert(cyrillic, "auto", target), latin);
    }
  }
});

test("Roman numerals: in Cyrillic text they stay", () => {
  for (const source of [CYRILLIC, "auto"]) {
    assert.equal(convert("XIX аср ва Пётр I", source, CYRILLIC), "XIX аср ва Пётр I");
  }
});

test("Roman numerals: Latin to Latin, and in a 2026 text", () => {
  assert.equal(convert("XIX asr, I. Boʻriyev", LATIN_1995, LATIN_2026), "XIX asr, I. Böriyev");
  assert.equal(convert("XIX asr, I. Böriyev", LATIN_2026, LATIN_1995), "XIX asr, I. Boʻriyev");
  assert.equal(toCyrillic("XIX asr Toşkentda"), "XIX аср Тошкентда");
});

test("Roman numerals: in a protected span", () => {
  assert.equal(toCyrillic("https://shahar.uz/XIX-asr va XIX asr"), "https://shahar.uz/XIX-asr ва XIX аср");
  assert.equal(convert("IV", LATIN_1995, CYRILLIC, { protect: false }), "IV");
});

test("Roman numerals: isRomanNumeral", () => {
  const cases = [
    ["XIX", "", true],
    ["MMMCMXCIX", "", true],
    ["I", "", true],
    ["I", " ", true],
    ["I", ".", false],
    ["XIX", ".", true],
    ["", "", false],
    ["IIII", "", false],
    ["MMMM", "", false],
    ["xix", "", false],
    ["XIx", "", false],
    ["IC", "", false],
  ];
  for (const [word, after, expected] of cases) assert.equal(isRomanNumeral(word, after), expected, word);
});
