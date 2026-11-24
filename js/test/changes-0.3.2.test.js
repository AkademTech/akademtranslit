// Changes in 0.3.2: Roman numerals, month names, dates and a word-final ц (as
// tests/test_changes_0_3_2.py for the Python library, with the same tables).
//
// Each rule has a section: the examples it was made for, its boundaries, the
// other direction, source "auto", and a protected span, which keeps its text
// whatever the rule says.

import assert from "node:assert/strict";
import { test } from "node:test";

import { CYRILLIC, LATIN_1995, LATIN_2026, convert, normalize, toCyrillic, toLatin } from "../src/index.js";
import { cyrillicWordToLatin1995, isRomanNumeral } from "../src/rules.js";

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

// --- TRANSLIT-26: month names: sentabr, oktabr; the Cyrillic ь restored -----------------

const CYRILLIC_MONTHS = [
  ["Сентябрь", "Sentabr"],
  ["сентябрда", "sentabrda"],
  ["сентябри", "sentabri"],
  ["октябрнинг", "oktabrning"],
  ["Октябрь", "Oktabr"],
  ["СЕНТЯБРЬ", "SENTABR"],
  ["СЕНТЯБРда", "SENTABRda"],
  ["ноябрь", "noyabr"],
  [
    "январь, февраль, март, апрель, май, июнь, июль, август, декабрь",
    "yanvar, fevral, mart, aprel, may, iyun, iyul, avgust, dekabr",
  ],
];

const LATIN_MONTHS = [
  ["yanvar", "январь", "yanvarda", "январда"],
  ["fevral", "февраль", "fevralda", "февралда"],
  ["aprel", "апрель", "aprelda", "апрелда"],
  ["iyun", "июнь", "iyunda", "июнда"],
  ["iyul", "июль", "iyulda", "июлда"],
  ["sentabr", "сентябрь", "sentabrda", "сентябрда"],
  ["sentyabr", "сентябрь", "sentyabrda", "сентябрда"],
  ["oktabr", "октябрь", "oktabrdagi", "октябрдаги"],
  ["oktyabr", "октябрь", "oktyabrdagi", "октябрдаги"],
  ["noyabr", "ноябрь", "noyabrda", "ноябрда"],
  ["dekabr", "декабрь", "dekabrda", "декабрда"],
  ["mart", "март", "martda", "мартда"],
  ["may", "май", "mayda", "майда"],
  ["avgust", "август", "avgustda", "августда"],
];

test("month names: Cyrillic to Latin", () => {
  for (const [cyrillic, latin] of CYRILLIC_MONTHS) {
    for (const source of [CYRILLIC, "auto"]) {
      for (const target of LATIN) assert.equal(convert(cyrillic, source, target), latin, `${cyrillic} (${source}, ${target})`);
    }
  }
});

test("month names: Latin to Cyrillic, alone and with a suffix", () => {
  for (const [alone, aloneCyrillic, suffixed, suffixedCyrillic] of LATIN_MONTHS) {
    for (const source of [...LATIN, "auto"]) {
      assert.equal(convert(alone, source, CYRILLIC), aloneCyrillic, `${alone} (${source})`);
      assert.equal(convert(suffixed, source, CYRILLIC), suffixedCyrillic, `${suffixed} (${source})`);
    }
  }
});

test("month names: Latin to Cyrillic, case and boundaries", () => {
  const cases = [
    ["SENTABR", "СЕНТЯБРЬ"],
    ["Sentabr", "Сентябрь"],
    ["Iyun", "Июнь"],
    ["SENTABRda", "СЕНТЯБРда"], // two letter units: the suffix still drops ь
    ["sentabri", "сентябри"],
    ["1-sentabr, 2-oktabrda", "1-сентябрь, 2-октябрда"],
    ["Martaba, mayda, iyuncha", "Мартаба, майда, июнча"], // no ь: not month names alone
  ];
  for (const [latin, cyrillic] of cases) assert.equal(toCyrillic(latin), cyrillic, latin);
});

test("month names: Cyrillic -> Latin -> Cyrillic gives them back, ь included", () => {
  for (const word of ["январь", "февраль", "апрель", "июнь", "июль", "сентябрь", "октябрь", "ноябрь", "декабрь"]) {
    for (const latin of LATIN) assert.equal(convert(convert(word, CYRILLIC, latin), latin, CYRILLIC), word);
  }
});

test("month names: Latin to Latin does not change them", () => {
  for (const word of ["sentabr", "sentyabr", "oktabrda", "oktyabrda", "yanvar"]) {
    assert.equal(convert(word, LATIN_1995, LATIN_2026), word);
    assert.equal(convert(word, LATIN_2026, LATIN_1995), word);
  }
});

test("month names: in Cyrillic text, and in a protected span", () => {
  assert.equal(toCyrillic("Сентябрь ва октябрь"), "Сентябрь ва октябрь");
  assert.equal(toLatin("Тошкентда сентябрь ойи"), "Toşkentda sentabr oyi");
  assert.equal(toCyrillic("https://shahar.uz/sentabr va sentabr"), "https://shahar.uz/sentabr ва сентябрь");
  assert.equal(toLatin("https://shahar.uz/сентябрь ва сентябрь"), "https://shahar.uz/сентябрь va sentabr");
});

test("month names: normalize keeps its key (no change in a patch release)", () => {
  assert.equal(normalize("Сентябрь"), "sentyabr");
  assert.equal(normalize("октябрнинг"), "oktyabrning");
  assert.equal(cyrillicWordToLatin1995("сентябрь"), "sentyabr");
});
