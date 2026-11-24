// Changes in 0.3.2: Roman numerals, month names, dates and a word-final ц (as
// tests/test_changes_0_3_2.py for the Python library, with the same tables).
//
// Each rule has a section: the examples it was made for, its boundaries, the
// other direction, source "auto", and a protected span, which keeps its text
// whatever the rule says.

import assert from "node:assert/strict";
import { test } from "node:test";

import { CYRILLIC, LATIN_1995, LATIN_2026, convert, normalize, toCyrillic, toLatin } from "../src/index.js";
import { cyrillicWordToLatin1995, dates, isRomanNumeral } from "../src/rules.js";

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
    ["sentabr, oktabrda", "сентябрь, октябрда"],
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

// --- TRANSLIT-20: dates: no hyphen after the number in Cyrillic --------------------------

// One date in latin_1995, latin_2026 and Cyrillic.
const DATES = [
  ["1991-yilning 1-sentabri", "1991-yilning 1-sentabri", "1991 йилнинг 1 сентябри"],
  ["1956-yil 22-sentabr", "1956-yil 22-sentabr", "1956 йил 22 сентябрь"],
  ["2026-yilda", "2026-yilda", "2026 йилда"],
  ["1941–1945-yillar", "1941–1945-yillar", "1941–1945 йиллар"], // an en dash before 1945
  ["1990-1991-yillarda", "1990-1991-yillarda", "1990-1991 йилларда"],
  ["1-may", "1-may", "1 май"],
  ["8-martda", "8-martda", "8 мартда"],
  ["9-mayi", "9-mayi", "9 майи"],
  ["31-dekabrgacha", "31-dekabrgaça", "31 декабргача"],
  ["15-iyundagi", "15-iyundagi", "15 июндаги"],
  ["2-oktabrning", "2-oktabrning", "2 октябрнинг"],
  ["21–22-noyabr", "21–22-noyabr", "21–22 ноябрь"],
  ["1-YANVAR, 2026-YIL", "1-YANVAR, 2026-YIL", "1 ЯНВАРЬ, 2026 ЙИЛ"],
  // U+2011 NON-BREAKING HYPHEN and U+00A0 NO-BREAK SPACE stay unbreakable.
  ["1991‑yil 1‑sentabr", "1991‑yil 1‑sentabr", "1991 йил 1 сентябрь"],
];

test("dates: Latin to Cyrillic", () => {
  for (const [latin1995, latin2026, cyrillic] of DATES) {
    assert.equal(convert(latin1995, LATIN_1995, CYRILLIC), cyrillic, latin1995);
    assert.equal(convert(latin2026, LATIN_2026, CYRILLIC), cyrillic, latin2026);
    assert.equal(toCyrillic(latin1995), cyrillic, latin1995);
  }
});

test("dates: Cyrillic to Latin", () => {
  for (const [latin1995, latin2026, cyrillic] of DATES) {
    assert.equal(convert(cyrillic, CYRILLIC, LATIN_1995), latin1995, cyrillic);
    assert.equal(convert(cyrillic, CYRILLIC, LATIN_2026), latin2026, cyrillic);
    assert.equal(toLatin(cyrillic, LATIN_1995), latin1995, cyrillic);
    assert.equal(toLatin(cyrillic), latin2026, cyrillic);
  }
});

test("dates: in their own orthography", () => {
  const cases = [
    ["1991-йилнинг 1-сентябри", CYRILLIC, "1991 йилнинг 1 сентябри"],
    ["1991‑йил 1‑сентябрь", CYRILLIC, "1991 йил 1 сентябрь"],
    ["1991 йилнинг 1 сентябри", CYRILLIC, "1991 йилнинг 1 сентябри"],
    ["1956 yil 22 sentabr", LATIN_1995, "1956-yil 22-sentabr"],
    ["1956 yil 22 sentabr", LATIN_1995, "1956‑yil 22‑sentabr"],
    ["2026 yil 1 iyun", LATIN_2026, "2026-yil 1-iyun"],
    ["2026-yil 1-iyun", LATIN_2026, "2026-yil 1-iyun"],
  ];
  for (const [text, orthography, expected] of cases) {
    assert.equal(convert(text, orthography, orthography), expected, text);
    assert.equal(convert(text, "auto", orthography), expected, text);
  }
});

test("dates: boundaries", () => {
  const cases = [
    ["60-yillar", CYRILLIC, "60-йиллар"],
    ["60-йиллар", LATIN_1995, "60-yillar"],
    ["5-sinf, 39-son", CYRILLIC, "5-синф, 39-сон"],
    ["5-синф, 39-сон", LATIN_1995, "5-sinf, 39-son"],
    ["5 yil ishladi", CYRILLIC, "5 йил ишлади"],
    ["5 йил ишлади", LATIN_1995, "5 yil ishladi"],
    ["476 йил", LATIN_1995, "476 yil"],
    ["2100 йил", LATIN_1995, "2100 yil"],
    ["476-yil", CYRILLIC, "476 йил"],
    ["2000 йил давомида", LATIN_1995, "2000-yil davomida"], // known limit
    ["32 sentabr", CYRILLIC, "32 сентябрь"],
    ["32 сентябрь", LATIN_1995, "32 sentabr"],
    ["32-sentabr", CYRILLIC, "32-сентябрь"],
    ["01-sentabr, 0991-yil, 12345-yil", CYRILLIC, "01-сентябрь, 0991-йил, 12345-йил"],
    ["1991  йил", LATIN_1995, "1991  yil"],
    ["1991 - yil", CYRILLIC, "1991 - йил"],
    ["№1991-yil", CYRILLIC, "№1991 йил"],
    ["1,5-yil", CYRILLIC, "1,5-йил"],
    ["3 марта", LATIN_1995, "3 marta"],
    ["5-martaba, 2-maydon", CYRILLIC, "5-мартаба, 2-майдон"],
    ["5-мартаба, 2-майдон", LATIN_1995, "5-martaba, 2-maydon"],
    ["5 майда", LATIN_1995, "5-mayda"], // read as May
  ];
  for (const [text, target, expected] of cases) assert.equal(convert(text, "auto", target), expected, text);
});

test("dates: a letter or digit before the number", () => {
  assert.equal(dates("ҳ1991-йил", CYRILLIC), "ҳ1991-йил");
  assert.equal(dates("21991-йил", CYRILLIC), "21991-йил");
  assert.equal(dates("x1991 yil", LATIN_1995), "x1991 yil");
  assert.equal(dates("_1991 yil", LATIN_1995), "_1991-yil");
});

test("dates: source auto", () => {
  assert.equal(toCyrillic("Toşkentda 2026-yil 1-sentabr"), "Тошкентда 2026 йил 1 сентябрь");
  assert.equal(toLatin("1991 йил 1 сентябрда", LATIN_1995), "1991-yil 1-sentabrda");
  assert.equal(toCyrillic("Тошкентда 2026-йил ва 2026-yil"), "Тошкентда 2026 йил ва 2026-yil");
});

test("dates: in a protected span", () => {
  assert.equal(toCyrillic("https://shahar.uz/1991-yil va 1991-yil"), "https://shahar.uz/1991-yil ва 1991 йил");
  assert.equal(toLatin('<a title="1991 йил">1991 йил</a>', LATIN_1995), '<a title="1991 йил">1991-yil</a>');
  assert.equal(toCyrillic("<b>1991</b>-yil"), "<b>1991</b>-йил");
  assert.equal(convert("https://x.uz/1991-yil", LATIN_1995, CYRILLIC, { protect: false }), "ҳттпс://х.уз/1991 йил");
});

test("dates: a Cyrillic date with a hyphen comes back without it", () => {
  const text = "Тошкент давлат университети, 2026-йил";
  for (const latin of LATIN) {
    assert.equal(convert(convert(text, CYRILLIC, latin), latin, CYRILLIC), "Тошкент давлат университети, 2026 йил");
  }
});

test("dates: linear time", () => {
  const text = "1".repeat(200_000) + "-йил " + "1-".repeat(100_000) + "1 ".repeat(100_000);
  const start = performance.now();
  for (const target of [CYRILLIC, LATIN_1995]) dates(text, target);
  assert.ok(performance.now() - start < 1000);
});

// --- TRANSLIT-25: a word-final ц is s -------------------------------------------------

const FINAL_TS = [
  ["марганец", "marganes"],
  ["ненец", "nenes"],
  ["шприц", "shpris"],
  ["кварц", "kvars"], // s before, s now
  ["ненецлар", "neneslar"],
  ["шприцни", "shprisni"],
  ["ненецларнинг", "neneslarning"],
  ["ненецларимизга", "neneslarimizga"],
  ["шприцдаги", "shprisdagi"],
  ["шприцгача", "shprisgacha"],
  ["МАРГАНЕЦ", "MARGANES"],
  ["Марганец", "Marganes"],
];

const TS_AS_BEFORE = [
  ["лицей", "litsey"],
  ["боцман", "botsman"], // ман is not one of the suffixes
  ["плацдарм", "platsdarm"],
  ["пицца", "pitssa"],
  ["милиция", "militsiya"],
  ["цирк", "sirk"],
  ["функция", "funksiya"],
  ["шприци", "shpritsi"], // the possessive -i alone is not one of the suffixes
];

test("ц: Cyrillic to latin_1995", () => {
  for (const [cyrillic, latin] of [...FINAL_TS, ...TS_AS_BEFORE]) {
    for (const source of [CYRILLIC, "auto"]) assert.equal(convert(cyrillic, source, LATIN_1995), latin, cyrillic);
  }
});

test("ц: Cyrillic to latin_2026", () => {
  for (const [cyrillic, latin] of [["шприц", "şpris"], ["шприцни", "şprisni"], ["марганец", "marganes"]]) {
    assert.equal(convert(cyrillic, CYRILLIC, LATIN_2026), latin);
    assert.equal(toLatin(cyrillic), latin);
  }
});

test("ц: Latin to Cyrillic does not change (known loss: marganes -> марганес)", () => {
  assert.equal(toCyrillic("marganes"), "марганес");
  assert.equal(toCyrillic("neneslar va shpris"), "ненеслар ва шприс");
  assert.equal(toCyrillic("litsey, botsman"), "лицей, боцман");
});

test("ц: in Cyrillic text and in a protected span", () => {
  assert.equal(toCyrillic("марганец"), "марганец");
  assert.equal(toLatin("https://shahar.uz/марганец ва марганец", LATIN_1995), "https://shahar.uz/марганец va marganes");
});

test("ц: normalize keeps its key", () => {
  assert.equal(normalize("Марганец"), "marganets");
  assert.equal(normalize("шприцни"), "shpritsni");
  assert.equal(cyrillicWordToLatin1995("марганец"), "marganets");
});

test("ц: linear time", () => {
  const start = performance.now();
  convert("ц".repeat(200_000), CYRILLIC, LATIN_1995);
  convert("а" + "цлар".repeat(50_000), CYRILLIC, LATIN_1995);
  assert.ok(performance.now() - start < 1000);
});
