// BCP 47 language tags for the three orthographies. A port of
// src/akademtranslit/tags.py; the rules for reading a tag are in its docstring.
//
// Errors: Python's ValueError is RangeError here, TypeError is TypeError.
//
// Warnings: Python's script_for_tag() emits a FutureWarning for "uz" and
// "uz-Latn" (read as latin_1995 in 0.x, as latin_2026 from 1.0.0). JavaScript
// has no warnings module, so scriptForTag() returns the warning as data,
// { script, warning }, with warning "FutureWarning" or null -- the shape the
// golden file records -- and writes nothing to the console. The functions
// that take an orthography read those tags the same way, silently.

import { CYRILLIC, LATIN_1995, LATIN_2026, SCRIPTS } from "./tables.js";
import { repr, requireArgument, typeName } from "./unicode.js";

const TAG_FOR_SCRIPT = [
  [CYRILLIC, "uz-Cyrl"],
  [LATIN_1995, "uz-Latn-1995"],
  [LATIN_2026, "uz-Latn-2026"],
];

const VARIANTS = new Map([
  ["1995", LATIN_1995],
  ["2026", LATIN_2026],
]);
const SCRIPT_SUBTAGS = ["latn", "cyrl"];
const OTHER_CODES_FOR_UZBEK = ["uzb", "uzn", "uzs"];

// ASCII only, checked before anything is lowercased.
const TAG_CHARACTERS = /^[A-Za-z0-9_-]+$/u;
const ALPHA = /^[a-z]+$/u;
const DIGITS = /^[0-9]+$/u;

const FORMS =
  "'uz-Cyrl', 'uz-Latn-1995' or 'uz-Latn-2026' (or 'uz-1995', 'uz-2026'), " +
  "in any case, with '-' or '_'";

/** The warning scriptForTag() reports for a tag that names no orthography. */
export const FUTURE_WARNING = "FutureWarning";

const scriptsRepr = "(" + SCRIPTS.map(repr).join(", ") + ")";

/** Why a tag was not read; the callers put it in their own message. */
class NotRead extends Error {}

function isVariant(subtag) {
  // RFC 5646: 5 to 8 alphanumerics, or a digit and 3 alphanumerics.
  return (subtag.length >= 5 && subtag.length <= 8) || (subtag.length === 4 && DIGITS.test(subtag[0]));
}

/** [orthography, namesIt] for ``tag``. Throws TypeError or NotRead. */
function parse(tag) {
  if (typeof tag !== "string") {
    throw new TypeError(`a language tag must be a str, not ${typeName(tag)}`);
  }
  if (!tag) throw new NotRead("it is empty");
  if (!TAG_CHARACTERS.test(tag)) {
    throw new NotRead("only ASCII letters, digits, '-' and '_' may appear in a tag");
  }
  const subtags = tag.replaceAll("_", "-").toLowerCase().split("-");
  for (const subtag of subtags) {
    if (!subtag) throw new NotRead("it has an empty subtag");
    if (subtag.length > 8) throw new NotRead(`the subtag ${repr(subtag)} is longer than 8 characters`);
  }

  const language = subtags[0];
  const rest = subtags.slice(1);
  if (OTHER_CODES_FOR_UZBEK.includes(language)) throw new NotRead(`${repr(language)} is Uzbek too, but use 'uz'`);
  if (language !== "uz") throw new NotRead(`the language is ${repr(language)}, not 'uz'`);

  let i = 0;
  const n = rest.length;
  if (i < n && rest[i].length === 3 && ALPHA.test(rest[i])) {
    throw new NotRead(`an extended language subtag (${repr(rest[i])}) is not supported`);
  }

  let script = null;
  if (i < n && rest[i].length === 4 && ALPHA.test(rest[i])) {
    if (!SCRIPT_SUBTAGS.includes(rest[i])) {
      throw new NotRead(`the script ${repr(rest[i])} is not supported; use 'Latn' or 'Cyrl'`);
    }
    script = rest[i];
    i++;
  }

  if (i < n && ((rest[i].length === 2 && ALPHA.test(rest[i])) || (rest[i].length === 3 && DIGITS.test(rest[i])))) {
    i++; // a region: it does not change the orthography
  }

  let variant = null;
  while (i < n && isVariant(rest[i])) {
    if (!VARIANTS.has(rest[i])) {
      throw new NotRead(`the variant ${repr(rest[i])} is not supported; use '1995' or '2026'`);
    }
    if (variant !== null) throw new NotRead("it has more than one variant");
    variant = rest[i];
    i++;
  }

  const singletons = new Set();
  while (i < n && rest[i].length === 1 && rest[i] !== "x") {
    const singleton = rest[i];
    if (singletons.has(singleton)) throw new NotRead(`the extension ${repr(singleton)} appears twice`);
    singletons.add(singleton);
    i++;
    const first = i;
    while (i < n && rest[i].length >= 2) i++;
    if (i === first) throw new NotRead(`the extension ${repr(singleton)} has no subtags`);
  }

  if (i < n && rest[i] === "x") {
    if (i + 1 === n) throw new NotRead("the private-use part 'x' has no subtags");
    i = n; // private use runs to the end
  }

  if (i < n) throw new NotRead(`the subtag ${repr(rest[i])} is out of place`);

  if (script === "cyrl") {
    if (variant !== null) {
      throw new NotRead(`the variant ${repr(variant)} is a Latin orthography; 'uz-Cyrl' takes none`);
    }
    return [CYRILLIC, true];
  }
  if (variant === null) return [LATIN_1995, false];
  return [VARIANTS.get(variant), true];
}

/**
 * The orthography ``tag`` names, as { script, warning }: script is one of
 * SCRIPTS, and warning is "FutureWarning" for "uz" and "uz-Latn" (they name
 * no orthography: latin_1995 in 0.x, latin_2026 from 1.0.0), otherwise null.
 * A tag that breaks a rule throws RangeError; anything but a string, TypeError.
 */
export function scriptForTag(tag) {
  requireArgument(tag, "tag", "scriptForTag");
  let script;
  let namesIt;
  try {
    [script, namesIt] = parse(tag);
  } catch (error) {
    if (error instanceof NotRead) {
      throw new RangeError(
        `${repr(tag)} is not a language tag for an Uzbek orthography: ${error.message}; expected ${FORMS}`,
      );
    }
    throw error;
  }
  return { script, warning: namesIt ? null : FUTURE_WARNING };
}

/** The language tag for ``script``, one of SCRIPTS; anything else throws RangeError. */
export function tagForScript(script) {
  requireArgument(script, "script", "tagForScript");
  for (const [name, tag] of TAG_FOR_SCRIPT) if (script === name) return tag;
  throw new RangeError(`unknown orthography: ${repr(script)}; expected one of ${scriptsRepr}`);
}

/**
 * The orthography an argument names, for the functions that take one. Called
 * only when ``value`` is not in SCRIPTS. ``unknown`` is the caller's message.
 * RangeError for "auto", for anything but a string and for a tag not read.
 */
export function orthography(value, unknown) {
  if (typeof value !== "string") throw new RangeError(`${unknown}, or a language tag for one of them`);
  if (value === "auto") throw new RangeError(unknown);
  try {
    return parse(value)[0];
  } catch (error) {
    if (error instanceof NotRead) {
      throw new RangeError(`${unknown}, or a language tag for one of them; ${repr(value)} is not one: ${error.message}`);
    }
    throw error;
  }
}

/** SCRIPTS as Python prints the tuple, for messages. */
export { scriptsRepr as SCRIPTS_REPR };
