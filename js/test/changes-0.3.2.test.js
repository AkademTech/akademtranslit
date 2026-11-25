// Changes in 0.3.2: Roman numerals, month names, dates and a word-final ц, and
// toAscii writing U+2011 as a hyphen (as tests/test_changes_0_3_2.py for the
// Python library, with the same tables).
//
// Each rule has a section: the examples it was made for, its boundaries, the
// other direction, source "auto", and a protected span, which keeps its text
// whatever the rule says.

import assert from "node:assert/strict";
import { test } from "node:test";

import { CYRILLIC, LATIN_1995, LATIN_2026, convert, normalize, toAscii, toCyrillic, toLatin } from "../src/index.js";
import { cyrillicWordToLatin1995, dates, isRomanNumeral } from "../src/rules.js";

const LATIN = [LATIN_1995, LATIN_2026];

// --- TRANSLIT-24: a Roman numeral stays Latin in Cyrillic ------------------------------

const ROMAN_NUMERALS = [
  ["XIX asr", "XIX аср"],
  ["IV bob", "IV боб"],
  ["XXI asrning oxiri", "XXI асрнинг охири"],
  ["MMXXVI", "MMXXVI"],
  ["CD va DVD", "CD ва ДВД"], // DVD is not a well-formed numeral
  ["XIX.", "XIX."], // more than one letter: a full stop after it is a full stop
  ["II", "II"], // two letters: a numeral wherever they stand
  // One letter, in context: (a) the word after it ...
  ["V asr", "V аср"],
  ["X sinf", "X синф"],
  ["I jahon", "I жаҳон"],
  ["V ASR", "V АСР"],
  ["V Asrda", "V Асрда"],
  ["V\u{A0}asr", "V\u{A0}аср"],
  ["V-asr", "V-аср"],
  ["V\u{2011}asr", "V\u{2011}аср"],
  ["V bo'lim, V bo‘lim", "V бўлим, V бўлим"],
  // ... (b) the word before it.
  ["Pyotr I", "Пётр I"],
  ["Nikolay I", "Николай I"],
  ["Pyotr\u{A0}I", "Пётр\u{A0}I"],
  ["Pyotr I, Nikolay II", "Пётр I, Николай II"],
  ["Пётр I", "Пётр I"], // a Cyrillic word before it, with a Latin source
  // Known limit (README): a capitalised word before a letter makes it a numeral.
  ["Variant V", "Вариант V"],
];

// Boundaries: an initial, a letter, a known limit, and what is not a numeral.
const NOT_ROMAN_NUMERALS = [
  ["I. Boʻriyev", "И. Бўриев"],
  ["M. Asadullayev", "М. Асадуллаев"],
  ["V. I. Lenin", "В. И. Ленин"],
  ["Pyotr I.", "Пётр И."], // known limit: read as an initial at the end of a sentence
  ["IIII", "ИИИИ"],
  ["Xix", "Хих"],
  ["XIXda", "ХИХда"], // a numeral with a suffix in one word is not a numeral word
  // One letter out of context is a letter.
  ["I", "И"],
  ["V", "В"],
  ["X", "Х"],
  ["V harfi", "В ҳарфи"],
  ["V  asr", "В  аср"], // two spaces
  ["V–asr", "В–аср"], // a dash is not a hyphen
  ["V- asr", "В- аср"],
  ["V. asr", "В. аср"],
  ["V, asr", "В, аср"],
  ["Pyotr  I", "Пётр  И"], // two spaces
  ["Pyotr, I", "Пётр, И"],
  ["Pyotr-I", "Пётр-И"], // the word before counts after one space only
  ["pyotr I", "пётр И"], // no capital before it
  ["A I", "А И"], // one letter before it
  ["Oʻ I", "Ў И"], // oʻ is one letter
  ["I va V", "И ва В"],
  ["V basr", "В баср"], // asr inside a word does not count
  // One L, C, D or M is a letter wherever it stands (C is not in the alphabet and stays).
  ["D guruhida", "Д гуруҳида"],
  ["M harfi", "М ҳарфи"],
  ["A, B, C va D toifalar", "А, Б, C ва Д тоифалар"],
  ["L asr", "Л аср"],
  ["Karl D", "Карл Д"],
  // Before harf or tovush one I, V or X is a letter, after a name too.
  ["Lotin V harfi", "Лотин В ҳарфи"],
  ["V va X harflari", "В ва Х ҳарфлари"],
  ["V, X harflari", "В, Х ҳарфлари"],
  ["Pyotr I harfi", "Пётр И ҳарфи"],
  ["Lotin X HARFLARI", "Лотин Х ҲАРФЛАРИ"],
  ["V\u{A0}Harflari", "В\u{A0}Ҳарфлари"],
];

test("Roman numerals: Latin to Cyrillic", () => {
  for (const [latin, cyrillic] of [...ROMAN_NUMERALS, ...NOT_ROMAN_NUMERALS]) {
    for (const source of [...LATIN, "auto"]) {
      assert.equal(convert(latin, source, CYRILLIC), cyrillic, `${latin} (${source})`);
    }
  }
});

// Section 6 of the 0.3.2c task: what one letter or a numeral gave at ba40a26 and still
// gives, and the known limits.
const ROMAN_AS_AT_BA40A26 = [
  ["V harfi", "В ҳарфи"],
  ["V asr", "V аср"],
  ["Nikolay I", "Николай I"],
  ["Pyotr, I", "Пётр, И"],
  ["X", "Х"],
  ["D I L M V X", "Д И Л М В Х"],
  ["XIX asr, IV bob", "XIX аср, IV боб"],
  ["MIX", "MIX"],
  ["CD va DVD", "CD ва ДВД"],
  ["Karl V", "Карл V"],
  ["Lyudovik XIV va Lyudovik XV", "Людовик XIV ва Людовик XV"],
  ["C toifa", "C тоифа"],
  ["B toifali", "Б тоифали"],
  ["C va D", "C ва Д"],
  // Known limits (README): an initial at the end of a sentence, and a capitalised
  // word at the start of one.
  ["Pyotr I.", "Пётр И."],
  ["Karl V.", "Карл В."],
  ["Variant V", "Вариант V"],
];

test("Roman numerals: as before", () => {
  for (const [latin, cyrillic] of ROMAN_AS_AT_BA40A26) {
    for (const source of [...LATIN, "auto"]) {
      assert.equal(convert(latin, source, CYRILLIC), cyrillic, `${latin} (${source})`);
    }
  }
});

// The words that make one letter before them a numeral (the last 14 since 0.3.2c), and
// their 2026 forms.
const COUNTED = [
  "asr", "ming", "bob", "qism", "jild", "tom", "sinf", "kurs", "boʻlim", "guruh", "chorak",
  "bosqich", "daraja", "toifa", "qurultoy", "syezd", "sessiya", "chaqiriq", "jahon",
  "kvartal", "semestr", "smena", "kitob", "kategoriya", "oʻrin", "yarim", "yarmi", "xalqaro",
  "respublika", "konferensiya", "kongress", "anjuman", "simpozium",
];
const COUNTED_2026 = ["bölim", "çorak", "bosqiç", "çaqiriq", "örin"];

test("Roman numerals: one letter before a counted word", () => {
  for (const word of [...COUNTED, ...COUNTED_2026]) {
    for (const source of [...LATIN, "auto"]) {
      for (const letter of "IVX") {
        for (const text of [`${letter} ${word}`, `${letter} ${word.toUpperCase()}`, `${letter} ${word}lar`]) {
          const rest = text.slice(2);
          assert.equal(convert(text, source, CYRILLIC), `${letter} ` + convert(rest, source, CYRILLIC), `${text} (${source})`);
        }
      }
    }
  }
});

test("Roman numerals: one L, C, D or M before a counted word is a letter", () => {
  for (const word of [...COUNTED, ...COUNTED_2026]) {
    for (const source of [...LATIN, "auto"]) {
      for (const letter of "LCDM") {
        for (const text of [`${letter} ${word}`, `Pyotr ${letter} ${word}`]) {
          const expected = text.split(" ").map((part) => convert(part, source, CYRILLIC)).join(" ");
          assert.equal(convert(text, source, CYRILLIC), expected, `${text} (${source})`);
        }
      }
      assert.ok(convert(`L ${word}`, source, CYRILLIC).startsWith("Л "), word);
      assert.ok(convert(`D ${word}`, source, CYRILLIC).startsWith("Д "), word);
      assert.ok(convert(`M ${word}`, source, CYRILLIC).startsWith("М "), word);
    }
  }
});

test("Roman numerals: one letter before another word is a letter", () => {
  for (const word of ["harfi", "va", "as", "asos", "boshqa", "minora", "to", "sin", "jahl", "bo"]) {
    assert.ok(toCyrillic(`V ${word}`).startsWith("В "), word);
  }
});

// The words that make one letter before them a letter, and the 2026 form.
const LETTER_WORDS = ["harf", "harfi", "harflari", "harfini", "tovush", "tovushi", "tovushlar"];
const LETTER_WORDS_2026 = ["tovuş", "tovuşi", "tovuşlar"];

test("Roman numerals: one letter before harf or tovush is a letter", () => {
  const capitalize = (word) => word[0].toUpperCase() + word.slice(1);
  for (const word of [...LETTER_WORDS, ...LETTER_WORDS_2026]) {
    for (const source of [...LATIN, "auto"]) {
      if (source === LATIN_1995 && LETTER_WORDS_2026.includes(word)) continue; // ş is not a latin_1995 letter
      for (const [letter, cyrillic] of [["I", "И"], ["V", "В"], ["X", "Х"]]) {
        for (const form of [word, word.toUpperCase(), capitalize(word)]) {
          for (const before of ["", "Lotin ", "Pyotr\u{A0}"]) {
            const text = `${before}${letter} ${form}`;
            const expected = convert(before, source, CYRILLIC) + `${cyrillic} ` + convert(form, source, CYRILLIC);
            assert.equal(convert(text, source, CYRILLIC), expected, `${text} (${source})`);
          }
        }
      }
    }
  }
  assert.equal(toCyrillic("Lotin V harfiy"), "Лотин В ҳарфий");
  assert.equal(toCyrillic("Lotin V harakat"), "Лотин V ҳаракат"); // not harf
});

test("Roman numerals: one letter in both Latin orthographies", () => {
  const cases = [
    ["I jahon urushi", "I jahon uruşi", "I жаҳон уруши"],
    ["V boʻlim", "V bölim", "V бўлим"],
    ["II chorak va I chorak", "II çorak va I çorak", "II чорак ва I чорак"],
    ["I bosqich", "I bosqiç", "I босқич"],
    ["V harfi", "V harfi", "В ҳарфи"],
    ["Nikolay I", "Nikolay I", "Николай I"],
    ["I tovushi", "I tovuşi", "И товуши"],
    ["Lotin X TOVUSHI", "Lotin X TOVUŞI", "Лотин Х ТОВУШИ"],
  ];
  for (const [latin1995, latin2026, cyrillic] of cases) {
    assert.equal(convert(latin1995, LATIN_1995, CYRILLIC), cyrillic, latin1995);
    assert.equal(convert(latin2026, LATIN_2026, CYRILLIC), cyrillic, latin2026);
    assert.equal(toCyrillic(latin1995), cyrillic, latin1995);
    assert.equal(toCyrillic(latin2026), cyrillic, latin2026);
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
    ["XIX", "", "", "", true],
    ["MMMCMXCIX", "", "", "", true],
    ["II", " ", "", "harfi", true],
    ["XIX", ".", "", "", true],
    ["I", "", "", "", false],
    ["I", " ", "", "", false],
    ["I", ".", "", "", false],
    ["I", " ", "", "asr", true],
    ["I", " ", "", "Asrlar", true],
    ["I", " ", "", "bo'lim", true],
    ["I", " ", "", "BOʼLIM", true],
    ["I", " ", "", "bōlim", true], // o with macron: ö in latin_2026
    ["I", " ", "", "çaqiriq", true],
    ["I", " ", "", "kvartal", true],
    ["I", " ", "", "Xalqaro", true],
    ["I", " ", "", "o'rinni", true],
    ["I", " ", "", "örin", true],
    ["I", " ", "", "yarmi", true],
    ["I", "-", "", "asr", true], // the caller passes the word after a hyphen
    ["I", " ", "", "harfi", false],
    ["I", " ", "", "as", false],
    ["I", "", "Pyotr", "", true],
    ["I", ",", "Pyotr", "", true],
    ["I", ".", "Pyotr", "", false],
    ["I", " ", "Pyotr", "harfi", false],
    ["V", " ", "Lotin", "Harflari", false],
    ["X", " ", "", "TOVUSHI", false],
    ["X", " ", "", "tovuşi", false],
    ["X", " ", "", "harakat", false],
    ["X", " ", "Pyotr", "harakat", true],
    ["L", " ", "", "asr", false],
    ["C", "", "Pyotr", "", false],
    ["D", " ", "", "guruhida", false],
    ["M", " ", "Karl", "toifa", false],
    ["I", "", "Пётр", "", true],
    ["I", "", "pyotr", "", false],
    ["I", "", "A", "", false],
    ["I", "", "Oʻ", "", false],
    ["I", "", "Ab", "", true],
    ["", "", "Pyotr", "asr", false],
    ["IIII", "", "Pyotr", "asr", false],
    ["MMMM", "", "", "", false],
    ["xix", "", "", "", false],
    ["XIx", "", "", "", false],
    ["IC", "", "", "", false],
    ["i", " ", "Pyotr", "asr", false],
  ];
  for (const [word, after, previous, following, expected] of cases) {
    assert.equal(isRomanNumeral(word, after, previous, following), expected, `${word} ${previous}|${following}`);
  }
  assert.equal(isRomanNumeral("XIX"), true);
  assert.equal(isRomanNumeral("XIX", "."), true);
  assert.equal(isRomanNumeral("I"), false);
  assert.equal(isRomanNumeral("I", "."), false);
});

// (a) after a hyphen: the word after one letter counts after one space, U+00A0, a
// hyphen or U+2011; the word before it, for (b), after one space or U+00A0 only.
const HYPHENATED = [
  ["V-asr", "V-аср"],
  ["I-jahon urushi", "I-жаҳон уруши"],
  ["X\u{2011}sinf", "X\u{2011}синф"],
  ["I-kvartal", "I-квартал"],
  ["V-harfi", "В-ҳарфи"], // harf counts after a hyphen too
  ["D-guruh", "Д-гуруҳ"],
  ["V\u{2010}asr", "В\u{2010}аср"], // U+2010 is not one of them
  ["V–asr", "В–аср"],
  ["V- asr", "В- аср"],
  ["V -asr", "В -аср"],
  ["Pyotr-I", "Пётр-И"],
  ["Pyotr\u{2011}I", "Пётр\u{2011}И"],
];

// A latin_1995 table text in the given source (urushi -> uruşi for latin_2026).
const inSource = (text, source) => (source === LATIN_2026 ? convert(text, LATIN_1995, LATIN_2026) : text);

test("Roman numerals: one letter and a hyphen", () => {
  for (const [latin, cyrillic] of HYPHENATED) {
    for (const source of [...LATIN, "auto"]) {
      assert.equal(convert(inSource(latin, source), source, CYRILLIC), cyrillic, `${latin} (${source})`);
    }
  }
});

// Series: numerals linked by a dash with no space around it or with one space on each
// side, a comma and one space, or va or yoki in any case with one space on each side,
// go together.
const SERIES = [
  // The 0.3.2c task.
  ["V–VI asrlar", "V–VI асрлар"],
  ["X–XII asrlarda", "X–XII асрларда"],
  ["I-II kurs talabalari", "I-II курс талабалари"],
  ["I–V asrlar", "I–V асрлар"],
  ["I, II va III boblar", "I, II ва III боблар"],
  ["I va II jahon urushlari", "I ва II жаҳон урушлари"],
  ["I yoki II guruh", "I ёки II гуруҳ"],
  ["V, X va XV asrlar", "V, X ва XV асрлар"],
  ["I–II.", "I–II."],
  ["V–VI", "V–VI"],
  ["V va X", "В ва Х"], // no member is a numeral on its own
  ["I. Karimov va V. Ivanov", "И. Каримов ва В. Иванов"],
  ["Karimov I. va Ivanov V.", "Каримов И. ва Иванов В."],
  // One member a numeral on its own: two letters, (a) or (b).
  ["V va X asrlar", "V ва X асрлар"],
  ["Karl V va X", "Карл V ва X"],
  ["I, I, I va II", "I, I, I ва II"],
  ["Pyotr I, II", "Пётр I, II"],
  ["Тошкент I–II асрлар, V va VI", "Тошкент I–II асрлар, V ва VI"],
  // U+00A0 for the space.
  ["V,\u{A0}X va XV asrlar", "V,\u{A0}X ва XV асрлар"],
  ["I\u{A0}va\u{A0}II", "I\u{A0}ва\u{A0}II"],
  // What is not a member: one letter before a full stop, and one L, C, D or M.
  ["II va V.", "II ва В."],
  ["V.–VI", "В.–VI"],
  ["L–LI", "Л–LI"],
  ["C–CI", "C–CI"],
  ["D va DI", "Д ва DI"],
  ["M, MI", "М, MI"],
  // Section 2 of the 0.3.2d task: a dash with one space or U+00A0 on each side links,
  // and va or yoki in any case.
  ["V – VI asrlar", "V – VI асрлар"],
  ["V - VI asrlar", "V - VI асрлар"],
  ["V — VI asrlar", "V — VI асрлар"],
  ["I\u{A0}–\u{A0}II kurs", "I\u{A0}–\u{A0}II курс"],
  ["I VA II JAHON URUSHLARI", "I ВА II ЖАҲОН УРУШЛАРИ"],
  ["I Va II", "I Ва II"],
  ["I YOKI II GURUH", "I ЁКИ II ГУРУҲ"],
  ["X – nomaʼlum, V – tezlik", "Х – номаълум, В – тезлик"], // no numeral after the dash
  ["Pyotr I – rus podshosi", "Пётр I – рус подшоси"], // as before
  // A spaced dash links only a member, and like the other links.
  ["X – nomaʼlum, V – tezlik, XX asr", "Х – номаълум, В – тезлик, XX аср"],
  ["I – II asrlar", "I – II асрлар"],
  ["I – II va III boblar", "I – II ва III боблар"],
  ["V – X", "В – Х"], // no member is a numeral on its own
  ["V – VI harflari", "В – VI ҳарфлари"],
  ["I\u{A0}– II", "I\u{A0}– II"],
  ["I Yoki II", "I Ёки II"],
  // What does not link.
  ["I -II asrlar", "И -II асрлар"],
  ["I- II asrlar", "И- II асрлар"],
  ["I  – II asrlar", "И  – II асрлар"],
  ["I –  II asrlar", "И –  II асрлар"],
  ["I –– II asrlar", "И –– II асрлар"],
  ["I II asrlar", "И II асрлар"],
  ["I,II", "И,II"],
  ["I ,II", "И ,II"],
  ["I,  II", "И,  II"],
  ["I  va II", "И  ва II"],
  ["I va  II", "И ва  II"],
  ["I VA  II", "И ВА  II"],
  ["I va-II", "И ва-II"],
  ["I ham II", "И ҳам II"],
  ["I va asr II", "И ва аср II"],
  // harf or tovush after the series: every member of one letter is a letter, even
  // one that is a numeral on its own (0.3.2d); two letters or more stay numerals.
  ["V, X va XV harflari", "В, Х ва XV ҳарфлари"],
  ["V–VI harflari", "В–VI ҳарфлари"],
  ["V yoki X tovushi", "В ёки Х товуши"],
  ["Nikolay I, V harfi", "Николай И, В ҳарфи"], // known limit (README)
  ["Karl V, X harfi", "Карл В, Х ҳарфи"],
  ["Lotin V va X harflari", "Лотин В ва Х ҳарфлари"],
  ["V–VI-harflar", "В–VI-ҳарфлар"],
  ["V–VI asrlar harflari", "V–VI асрлар ҳарфлари"], // not the word after the series
];

test("Roman numerals: in a series", () => {
  for (const [latin, cyrillic] of SERIES) {
    for (const source of [...LATIN, "auto"]) {
      assert.equal(convert(inSource(latin, source), source, CYRILLIC), cyrillic, `${latin} (${source})`);
    }
  }
});

// Section 1 of the 0.3.2d task: harf or tovush after a series makes every member of
// one letter a letter, one that (a) or (b) makes a numeral on its own too; members of
// two letters or more stay numerals.
const SERIES_BEFORE_HARF = [
  ["Ushbu V va X harflari", "Ушбу В ва Х ҳарфлари"], // (b): Ushbu, first word of a sentence
  ["Lotin V va X harflari", "Лотин В ва Х ҳарфлари"],
  ["Lotin V, X harflari", "Лотин В, Х ҳарфлари"],
  ["V, X va XV harflari", "В, Х ва XV ҳарфлари"], // as before
  ["Nikolay I, V harfi", "Николай И, В ҳарфи"], // known limit (README)
  ["Pyotr I yoki V TOVUSHLARI", "Пётр И ёки В ТОВУШЛАРИ"],
  ["Lotin V\u{A0}va X\u{A0}Harflari", "Лотин В\u{A0}ва Х\u{A0}Ҳарфлари"],
  ["XX, V va X harflari", "XX, В ва Х ҳарфлари"],
  ["Lotin V va X harflari, Karl V", "Лотин В ва Х ҳарфлари, Карл V"], // only the series before harf
];

// Section 3 of the 0.3.2d task: as at bfcbb9f.
const ROMAN_AS_AT_BFCBB9F = [
  ["Masalan, V va X harflari", "Масалан, В ва Х ҳарфлари"],
  ["Lotin V va X", "Лотин V ва X"],
  ["Karl V, X", "Карл V, X"],
  ["IV – V asrlar", "IV – V асрлар"],
];

test("Roman numerals: a series before harf, and as at bfcbb9f", () => {
  for (const [latin, cyrillic] of [...SERIES_BEFORE_HARF, ...ROMAN_AS_AT_BFCBB9F]) {
    for (const source of [...LATIN, "auto"]) {
      assert.equal(convert(inSource(latin, source), source, CYRILLIC), cyrillic, `${latin} (${source})`);
    }
  }
});

test("Roman numerals: every dash links a series", () => {
  for (const dash of ["-", "\u{2010}", "\u{2011}", "\u{2012}", "\u{2013}", "\u{2014}"]) {
    assert.equal(toCyrillic(`I${dash}II asrlar`), `I${dash}II асрлар`, dash);
    assert.equal(toCyrillic(`V${dash}VI`), `V${dash}VI`, dash);
    assert.equal(toCyrillic(`V${dash}X${dash}XV`), `V${dash}X${dash}XV`, dash);
    assert.equal(toCyrillic(`V${dash}X`), `В${dash}Х`, dash);
    assert.equal(toCyrillic(`V${dash}VI harflari`), `В${dash}VI ҳарфлари`, dash);
    // One space or U+00A0 on each side links too (0.3.2d), on one side only or two do not.
    for (const a of [" ", "\u{A0}"]) {
      for (const b of [" ", "\u{A0}"]) {
        assert.equal(toCyrillic(`V${a}${dash}${b}VI asrlar`), `V${a}${dash}${b}VI асрлар`, dash);
        assert.equal(toCyrillic(`V${a}${dash}${b}X`), `В${a}${dash}${b}Х`, dash);
        assert.equal(toCyrillic(`V${a}${dash}${b}tezlik, XV`), `В${a}${dash}${b}тезлик, XV`, dash);
      }
      assert.equal(toCyrillic(`V${a}${dash}VI`), `В${a}${dash}VI`, dash);
      assert.equal(toCyrillic(`V${dash}${a}VI`), `В${dash}${a}VI`, dash);
      assert.equal(toCyrillic(`V${a}${a}${dash} VI`), `В${a}${a}${dash} VI`, dash);
      assert.equal(toCyrillic(`V ${dash}${a}${a}VI`), `В ${dash}${a}${a}VI`, dash);
    }
  }
});

test("Roman numerals: a series in a 2026 text, the other directions and a protected span", () => {
  const text = "V–VI asrlar, I bölim, I çorak";
  assert.equal(convert(text, LATIN_2026, CYRILLIC), "V–VI асрлар, I бўлим, I чорак");
  assert.equal(toCyrillic(text), "V–VI асрлар, I бўлим, I чорак");
  assert.equal(convert("V–VI asrlar, I boʻlim, I chorak", LATIN_1995, CYRILLIC), "V–VI асрлар, I бўлим, I чорак");
  assert.equal(convert("V–VI asrlar", LATIN_1995, LATIN_2026), "V–VI asrlar");
  assert.equal(convert("V–VI асрлар", CYRILLIC, CYRILLIC), "V–VI асрлар");
  assert.equal(toLatin("V–VI асрлар, V va X"), "V–VI asrlar, V va X");
  assert.equal(toCyrillic("https://shahar.uz/V–VI va V–VI asrlar"), "https://shahar.uz/V–VI ва V–VI асрлар");
  assert.equal(toCyrillic("V–https://shahar.uz VI"), "В–https://shahar.uz VI");
});

// The words added to (a) in 0.3.2c: the task's table.
const COUNTED_0_3_2C = [
  ["I kvartal", "I квартал"],
  ["I semestr", "I семестр"],
  ["I smenada", "I сменада"],
  ["I kitob", "I китоб"],
  ["I kategoriya", "I категория"],
  ["I oʻrinni egalladi", "I ўринни эгаллади"],
  ["I o'rin", "I ўрин"],
  ["XX asrning I yarmi", "XX асрнинг I ярми"],
  ["I yarim yillik", "I ярим йиллик"],
  ["I Xalqaro ilmiy-amaliy konferensiya", "I Халқаро илмий-амалий конференсия"],
  ["I Respublika anjumani", "I Республика анжумани"],
  ["I kongress", "I конгресс"],
  ["I simpozium", "I симпозиум"],
];

test("Roman numerals: the new counted words", () => {
  for (const [latin, cyrillic] of COUNTED_0_3_2C) {
    for (const source of [LATIN_1995, "auto"]) assert.equal(convert(latin, source, CYRILLIC), cyrillic, latin);
    assert.equal(convert(convert(latin, LATIN_1995, LATIN_2026), LATIN_2026, CYRILLIC), cyrillic, latin);
  }
});

test("Roman numerals: series take linear time", () => {
  const start = performance.now();
  for (const text of [
    "I, ".repeat(10_000) + "II", "I va ".repeat(10_000) + "II", "V–".repeat(10_000) + "VI", "I, ".repeat(10_000) + "V",
    "V – ".repeat(10_000) + "VI", "I VA ".repeat(10_000) + "II",
  ]) {
    convert(text, LATIN_1995, CYRILLIC);
  }
  assert.ok(performance.now() - start < 1000);
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
  ["1991\u{2011}yil 1\u{2011}sentabr", "1991\u{2011}yil 1\u{2011}sentabr", "1991\u{A0}йил 1\u{A0}сентябрь"],
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

test("dates: in their own orthography the separator stays", () => {
  const cases = [
    ["1991-йилнинг 1-сентябри", CYRILLIC],
    ["1991-йил", CYRILLIC],
    ["1991\u{2011}йил 1\u{2011}сентябрь", CYRILLIC],
    ["1991 йилнинг 1 сентябри", CYRILLIC],
    ["1956 yil 22 sentabr", LATIN_1995],
    ["ilmiy jurnal 2026 yil 12 son", LATIN_1995],
    ["1956\u{A0}yil 22\u{A0}sentabr", LATIN_1995],
    ["2026 yil 1 iyun", LATIN_2026],
    ["2026-yil 1-iyun", LATIN_2026],
  ];
  for (const [text, orthography] of cases) {
    assert.equal(convert(text, orthography, orthography), text, text);
    assert.equal(convert(text, "auto", orthography), text, text);
  }
});

test("dates: latin_1995 <-> latin_2026 is one script, the separator stays", () => {
  const cases = [
    ["2026 yil", "2026 yil"],
    ["1956 yil 22 sentabr", "1956 yil 22 sentabr"],
    ["ilmiy jurnal 2026 yil 12 son", "ilmiy jurnal 2026 yil 12 son"],
    ["1991-yilning 1-sentabri", "1991-yilning 1-sentabri"],
    ["1956\u{A0}yil 22\u{A0}sentabr", "1956\u{A0}yil 22\u{A0}sentabr"],
    ["1991\u{2011}yil 1\u{2011}sentabr", "1991\u{2011}yil 1\u{2011}sentabr"],
    ["31 dekabrgacha, 2026 yil", "31 dekabrgaça, 2026 yil"],
  ];
  for (const [latin1995, latin2026] of cases) {
    assert.equal(convert(latin1995, LATIN_1995, LATIN_2026), latin2026, latin1995);
    assert.equal(convert(latin2026, LATIN_2026, LATIN_1995), latin1995, latin2026);
    assert.equal(toLatin(latin1995), latin2026, latin1995);
    assert.equal(toLatin(latin2026, LATIN_1995), latin1995, latin2026);
  }
});

test("dates: read in the named source", () => {
  assert.equal(convert("ilmiy jurnal 2026 yil 12 son", CYRILLIC, LATIN_1995), "ilmiy jurnal 2026-yil 12 son");
  assert.equal(convert("1956 yil 22 sentabr", CYRILLIC, LATIN_2026), "1956-yil 22-sentabr");
  assert.equal(convert("1991-йил", LATIN_1995, CYRILLIC), "1991 йил");
  assert.equal(convert("1991-йил", LATIN_2026, CYRILLIC), "1991 йил");
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
    ["2000 йиллик тарих", LATIN_1995, "2000-yillik tarix"], // the same limit
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

test("dates: only before a word from the other script", () => {
  // crossed: where a word read in the other script starts (UTF-16 offsets).
  assert.equal(dates("1991-йил", CYRILLIC, new Set()), "1991-йил");
  assert.equal(dates("1991-йил", CYRILLIC, new Set([5])), "1991 йил");
  assert.equal(dates("1991-йил 1991-йил", CYRILLIC, new Set([14])), "1991-йил 1991 йил");
  assert.equal(dates("1991 yil 1 sentabr", LATIN_1995, new Set([5])), "1991-yil 1 sentabr");
  assert.equal(dates("1991 yil 1 sentabr", LATIN_1995, new Set([11])), "1991 yil 1-sentabr");
});

test("dates: source auto", () => {
  assert.equal(toCyrillic("Toşkentda 2026-yil 1-sentabr"), "Тошкентда 2026 йил 1 сентябрь");
  assert.equal(toLatin("1991 йил 1 сентябрда", LATIN_1995), "1991-yil 1-sentabrda");
  // Mostly Cyrillic: both dates are in their own script and keep the hyphen.
  assert.equal(toCyrillic("Тошкентда 2026-йил ва 2026-yil"), "Тошкентда 2026-йил ва 2026-yil");
  // Each date by the script its word is read in.
  assert.equal(toLatin("1956 йил va 1956 yil", LATIN_1995), "1956-yil va 1956 yil");
  assert.equal(toLatin("1956 йил va 1956 yil"), "1956-yil va 1956 yil");
  assert.equal(toCyrillic("1956-yil va 1956-йил"), "1956 йил ва 1956-йил");
  assert.equal(toCyrillic("1 sentabr, 1-сентябрь, 1-sentabr"), "1 сентябрь, 1-сентябрь, 1 сентябрь");
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
  ["Кац, Швец", "Kas, Shves"], // surnames too (README)
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

// --- toAscii: U+2011 is a hyphen ------------------------------------------------------

test("toAscii writes the non-breaking hyphen as a hyphen", () => {
  const cases = [
    // c1211: the date converted to Latin has U+2011, which toAscii writes as -.
    ["1956\u{A0}йил 22\u{A0}сентябрь", "1956-yil 22-sentabr"],
    ["1991\u{2011}yil 1\u{2011}sentabr", "1991-yil 1-sentabr"], // c1210
    ["1991\u{2011}йил", "1991-yil"],
    ["a\u{2011}b", "a-b"],
    // U+00A0 is a space, as in 0.3.1 (NFKD).
    ["1991\u{A0}yil", "1991 yil"],
    ["a\u{A0}b", "a b"],
    ["1956 йил 22 сентябрь", "1956-yil 22-sentabr"],
  ];
  for (const [text, expected] of cases) assert.equal(toAscii(text), expected, text);
});

test("toAscii after toLatin", () => {
  const latin = toLatin("1956\u{A0}йил 22\u{A0}сентябрь", LATIN_1995);
  assert.equal(latin, "1956\u{2011}yil 22\u{2011}sentabr");
  assert.equal(toAscii(latin), "1956-yil 22-sentabr");
  assert.equal(toAscii(toLatin("1956 йил 22 сентябрь", LATIN_1995)), "1956-yil 22-sentabr");
});
