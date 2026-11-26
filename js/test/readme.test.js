// The JavaScript examples in README.md run, and give what the README says they
// give, as tests/test_readme.py runs the Python ones with doctest.
//
// An example is one line of a ```js block: `name(arguments); // result`, where
// the arguments and the result are JSON. Any other line of such a block, other
// than an import, a comment or a blank line, fails the test, so an example
// cannot be skipped by mistake.

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import * as lib from "../src/index.js";

const README = readFileSync(new URL("../../README.md", import.meta.url), "utf8");
const BLOCKS = [...README.matchAll(/^```js\n([\s\S]*?)^```$/gmu)].map((match) => match[1]);
const EXAMPLE = /^(\w+)\((.*)\); \/\/ (.+)$/u;

test("README.md: the JavaScript examples", () => {
  let checked = 0;
  for (const block of BLOCKS) {
    for (const line of block.split("\n")) {
      if (line === "" || line.startsWith("import ") || line.startsWith("//")) continue;
      const match = EXAMPLE.exec(line);
      assert.ok(match, `not an example: ${line}`);
      const [, name, args, result] = match;
      assert.equal(typeof lib[name], "function", name);
      assert.deepEqual(lib[name](...JSON.parse(`[${args}]`)), JSON.parse(result), line);
      checked += 1;
    }
  }
  assert.ok(BLOCKS.length >= 1 && checked >= 6, `${BLOCKS.length} blocks, ${checked} examples`);
});
