// Character tables for the three Uzbek orthographies. A port of
// src/akademtranslit/tables.py; the comments there are the documentation.
//
// Everything context-free lives here as data; anything that needs to look at
// the surrounding characters lives in rules.js. test/fixtures/tables-0.3.0.json
// is a dump of the Python tables, and test/api.test.js compares the two.

const freeze = (value) => Object.freeze(value);
const pairs = (list) => freeze(list.map((pair) => freeze(pair)));

// --- orthography identifiers -------------------------------------------------

export const CYRILLIC = "cyrillic";
export const LATIN_1995 = "latin_1995";
export const LATIN_2026 = "latin_2026";

export const SCRIPTS = freeze([CYRILLIC, LATIN_1995, LATIN_2026]);

// --- the rules version -------------------------------------------------------

// Which rules convert(), toLatin() and toCyrillic() follow: the official basis
// (the 2026 alphabet of Law No. O'RQ-1184, without official spelling rules),
// then this project's rule set, by the year and month of the release that last
// changed their output. test/golden.test.js checks it against the golden file.
export const RULES_VERSION = "uz-2026-alphabet+project-2026.11";

// --- the two modifier marks --------------------------------------------------

/** U+02BB MODIFIER LETTER TURNED COMMA -- part of the letters oʻ and gʻ. */
export const TURNED_COMMA = "ʻ";

/** U+02BC MODIFIER LETTER APOSTROPHE -- the tutuq belgisi. */
export const TUTUQ = "ʼ";

/** Everything seen in the wild for either mark; output uses only the two above. */
export const APOSTROPHE_VARIANTS = freeze([
  "ʻ", // ʻ turned comma (canonical for oʻ/gʻ)
  "ʼ", // ʼ modifier apostrophe (canonical for tutuq belgisi)
  "’", // ’ right single quotation mark
  "‘", // ‘ left single quotation mark
  "´", // ´ acute accent
  "ʹ", // ʹ modifier letter prime
  "'", // ' ASCII apostrophe
  "`", // ` grave accent
]);

// --- invisible characters --------------------------------------------------------

/** Default_Ignorable_Code_Point of Unicode 15.1 (ICU 74.2), as (first, last) ranges. */
export const DEFAULT_IGNORABLE = pairs([
  [0x00ad, 0x00ad], // soft hyphen
  [0x034f, 0x034f], // combining grapheme joiner
  [0x061c, 0x061c], // Arabic letter mark
  [0x115f, 0x1160], // Hangul choseong and jungseong fillers
  [0x17b4, 0x17b5], // Khmer inherent vowels
  [0x180b, 0x180f], // Mongolian free variation selectors and vowel separator
  [0x200b, 0x200f], // zero-width space, non-joiner and joiner; LRM, RLM
  [0x202a, 0x202e], // bidirectional embeddings and overrides
  [0x2060, 0x206f], // word joiner, invisible operators, bidirectional isolates
  [0x3164, 0x3164], // Hangul filler
  [0xfe00, 0xfe0f], // variation selectors
  [0xfeff, 0xfeff], // byte order mark (zero-width no-break space)
  [0xffa0, 0xffa0], // halfwidth Hangul filler
  [0xfff0, 0xfff8], // unassigned specials
  [0x1bca0, 0x1bca3], // shorthand format controls
  [0x1d173, 0x1d17a], // musical symbol format controls
  [0xe0000, 0xe0fff], // tags, variation selectors supplement, unassigned
]);

// --- Cyrillic ----------------------------------------------------------------

/** The Cyrillic block and Cyrillic Supplement: what every function counts as Cyrillic. */
export const CYRILLIC_FIRST = 0x0400;
export const CYRILLIC_LAST = 0x052f;

/** Cyrillic vowels, for the е rule. */
export const CYRILLIC_VOWELS = freeze(new Set("аеёиоуўэюяы"));

/** Context-free Cyrillic to latin_1995; positional letters are in rules.js. */
export const CYRILLIC_TO_LATIN_1995 = freeze(
  new Map([
    ["а", "a"],
    ["б", "b"],
    ["в", "v"],
    ["г", "g"],
    ["д", "d"],
    ["ё", "yo"],
    ["ж", "j"],
    ["з", "z"],
    ["и", "i"],
    ["й", "y"],
    ["к", "k"],
    ["л", "l"],
    ["м", "m"],
    ["н", "n"],
    ["о", "o"],
    ["п", "p"],
    ["р", "r"],
    ["с", "s"],
    ["т", "t"],
    ["у", "u"],
    ["ф", "f"],
    ["х", "x"],
    ["ч", "ch"],
    ["ш", "sh"],
    ["ъ", TUTUQ],
    ["э", "e"],
    ["ю", "yu"],
    ["я", "ya"],
    // Uzbek-specific letters
    ["ў", "o" + TURNED_COMMA],
    ["қ", "q"],
    ["ғ", "g" + TURNED_COMMA],
    ["ҳ", "h"],
    // Letters only in Russian loanwords; these folds are lossy.
    ["щ", "sh"],
    ["ы", "i"],
    ["ь", ""],
  ]),
);

/** latin_1995 to Cyrillic, longest match first: tried in this order at each position. */
export const LATIN_1995_TO_CYRILLIC = pairs([
  ["s" + TUTUQ + "h", "сҳ"],
  ["o" + TURNED_COMMA, "ў"],
  ["g" + TURNED_COMMA, "ғ"],
  ["sh", "ш"],
  ["ch", "ч"],
  ["ts", "ц"],
  ["y" + "o" + TURNED_COMMA, "йў"],
  ["yo", "ё"],
  ["yu", "ю"],
  ["ya", "я"],
  ["a", "а"],
  ["b", "б"],
  ["d", "д"],
  ["f", "ф"],
  ["g", "г"],
  ["h", "ҳ"],
  ["i", "и"],
  ["j", "ж"],
  ["k", "к"],
  ["l", "л"],
  ["m", "м"],
  ["n", "н"],
  ["o", "о"],
  ["p", "п"],
  ["q", "қ"],
  ["r", "р"],
  ["s", "с"],
  ["t", "т"],
  ["u", "у"],
  ["v", "в"],
  ["x", "х"],
  ["y", "й"],
  ["z", "з"],
  [TUTUQ, "ъ"],
]);

/** Latin vowels, for the reverse e/ye rule. */
export const LATIN_VOWELS = freeze(new Set("aeiouö"));

/** Loanword stems whose final ts is ц: the Russian -ица nouns. */
export const TS_LOANWORD_STEMS = freeze([
  "tablits", "teplits", "stolits", "ulits", "bolnits", "granits", "gostinits",
]);

// --- the 2026 reform ---------------------------------------------------------

/** The four letters the reform changes (Law No. O'RQ-1184). */
export const REFORM_PAIRS = pairs([
  ["sh", "ş"],
  ["ch", "ç"],
  ["g" + TURNED_COMMA, "ğ"],
  ["o" + TURNED_COMMA, "ö"],
]);

/** Ordered rewrite steps for latin_1995 -> latin_2026; the order is load-bearing. */
export const LATIN_1995_TO_2026_STEPS = pairs([
  ...REFORM_PAIRS,
  ["s" + TUTUQ + "h", "sh"],
]);

/** Ordered rewrite steps for latin_2026 -> latin_1995. */
export const LATIN_2026_TO_1995_STEPS = pairs([
  ["sh", "s" + TUTUQ + "h"],
  ...REFORM_PAIRS.map(([old, now]) => [now, old]),
]);

/** Other input forms of the reformed letters, read as them; never output. */
export const LATIN_2026_INPUT_ALIASES = pairs([
  [String.fromCodePoint(0x014d), "ö"], // o with macron
  [String.fromCodePoint(0x01d2), "ö"], // o with caron
  [String.fromCodePoint(0x0219), "ş"], // s with comma below (not s with cedilla)
]);

// --- ASCII for names and logins -------------------------------------------------

/** How toAscii() writes the letters conversion to latin_1995 leaves. Frozen. */
export const ASCII_SCHEME = pairs([
  ["o" + TURNED_COMMA, "o"],
  ["O" + TURNED_COMMA, "O"],
  ["g" + TURNED_COMMA, "g"],
  ["G" + TURNED_COMMA, "G"],
  ["ş", "sh"],
  ["ç", "ch"],
  ["ğ", "g"],
  ["Ğ", "G"],
  ["ö", "o"],
  ["Ö", "O"],
]);

/** Capital Ş and Ç for toAscii(): [letter, beside a capital, otherwise]. Frozen. */
export const ASCII_CAPITALS = pairs([
  ["Ş", "SH", "Sh"],
  ["Ç", "CH", "Ch"],
]);

// --- look-alike letters ----------------------------------------------------------

/** Latin and Cyrillic letters that look alike, as [Latin, Cyrillic], by code point. */
export const HOMOGLYPHS = pairs([
  // Lowercase.
  ["a", String.fromCodePoint(0x0430)], // CYRILLIC SMALL LETTER A
  ["c", String.fromCodePoint(0x0441)], // CYRILLIC SMALL LETTER ES
  ["e", String.fromCodePoint(0x0435)], // CYRILLIC SMALL LETTER IE
  ["o", String.fromCodePoint(0x043e)], // CYRILLIC SMALL LETTER O
  ["p", String.fromCodePoint(0x0440)], // CYRILLIC SMALL LETTER ER
  ["x", String.fromCodePoint(0x0445)], // CYRILLIC SMALL LETTER HA
  ["y", String.fromCodePoint(0x0443)], // CYRILLIC SMALL LETTER U
  ["i", String.fromCodePoint(0x0456)], // CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
  ["j", String.fromCodePoint(0x0458)], // CYRILLIC SMALL LETTER JE
  ["s", String.fromCodePoint(0x0455)], // CYRILLIC SMALL LETTER DZE
  ["h", String.fromCodePoint(0x04bb)], // CYRILLIC SMALL LETTER SHHA
  ["q", String.fromCodePoint(0x051b)], // CYRILLIC SMALL LETTER QA
  ["w", String.fromCodePoint(0x051d)], // CYRILLIC SMALL LETTER WE
  ["ö", String.fromCodePoint(0x04e7)], // CYRILLIC SMALL LETTER O WITH DIAERESIS
  // Capitals.
  ["A", String.fromCodePoint(0x0410)], // CYRILLIC CAPITAL LETTER A
  ["B", String.fromCodePoint(0x0412)], // CYRILLIC CAPITAL LETTER VE
  ["C", String.fromCodePoint(0x0421)], // CYRILLIC CAPITAL LETTER ES
  ["E", String.fromCodePoint(0x0415)], // CYRILLIC CAPITAL LETTER IE
  ["H", String.fromCodePoint(0x041d)], // CYRILLIC CAPITAL LETTER EN
  ["I", String.fromCodePoint(0x0406)], // CYRILLIC CAPITAL LETTER BYELORUSSIAN-UKRAINIAN I
  ["J", String.fromCodePoint(0x0408)], // CYRILLIC CAPITAL LETTER JE
  ["K", String.fromCodePoint(0x041a)], // CYRILLIC CAPITAL LETTER KA
  ["M", String.fromCodePoint(0x041c)], // CYRILLIC CAPITAL LETTER EM
  ["O", String.fromCodePoint(0x041e)], // CYRILLIC CAPITAL LETTER O
  ["P", String.fromCodePoint(0x0420)], // CYRILLIC CAPITAL LETTER ER
  ["S", String.fromCodePoint(0x0405)], // CYRILLIC CAPITAL LETTER DZE
  ["T", String.fromCodePoint(0x0422)], // CYRILLIC CAPITAL LETTER TE
  ["X", String.fromCodePoint(0x0425)], // CYRILLIC CAPITAL LETTER HA
  ["Y", String.fromCodePoint(0x0423)], // CYRILLIC CAPITAL LETTER U
  ["Ö", String.fromCodePoint(0x04e6)], // CYRILLIC CAPITAL LETTER O WITH DIAERESIS
]);

// --- alphabets -----------------------------------------------------------------

/** The 28 letters of the 2026 alphabet, in the order of Law No. O'RQ-1184. */
export const LATIN_2026_ALPHABET = freeze([
  "a", "b", "d", "e", "f", "g", "ğ", "h", "i", "j", "k", "l", "m", "n",
  "o", "ö", "p", "q", "r", "s", "ş", "ç", "t", "u", "v", "x", "y", "z",
]);

/** The 1995 alphabet in sorting order: 24 letters, then oʻ gʻ sh ch. */
export const LATIN_1995_ALPHABET = freeze([
  "a", "b", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o",
  "p", "q", "r", "s", "t", "u", "v", "x", "y", "z",
  "o" + TURNED_COMMA, "g" + TURNED_COMMA, "sh", "ch",
]);

/** The 35 letters of the Uzbek Cyrillic alphabet; Ў Қ Ғ Ҳ follow Я. */
export const CYRILLIC_ALPHABET = freeze([
  "а", "б", "в", "г", "д", "е", "ё", "ж", "з", "и", "й", "к", "л", "м",
  "н", "о", "п", "р", "с", "т", "у", "ф", "х", "ц", "ч", "ш", "ъ", "ь",
  "э", "ю", "я", "ў", "қ", "ғ", "ҳ",
]);
