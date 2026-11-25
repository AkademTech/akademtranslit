// The main criterion of the port: golden/golden-<version>.json, the Python
// library's output on golden/inputs.json and golden/tag-inputs.json, is
// reproduced exactly -- every input, every field, every tag.
//
// Values are compared as JSON: a Python tuple is a JSON array, None is null,
// and order counts (JSON.stringify of the two values must be equal). A Python
// exception is recorded in the golden file as {"error": name}: ValueError is
// RangeError here, TypeError is TypeError.

import assert from "node:assert/strict";
import { test } from "node:test";

import * as lib from "../src/index.js";
import { FIELDS, outcome, readGolden, sameJson, sha256 } from "./support.js";

const goldenName = `golden-${lib.VERSION}.json`;
const bytes = {
  golden: readGolden(goldenName),
  inputs: readGolden("inputs.json"),
  tagInputs: readGolden("tag-inputs.json"),
  sums: readGolden("SHA256SUMS").toString("utf8"),
};
const golden = JSON.parse(bytes.golden.toString("utf8"));
const cases = JSON.parse(bytes.inputs.toString("utf8")).cases;
const tagInputs = JSON.parse(bytes.tagInputs.toString("utf8"));

test("golden files match golden/SHA256SUMS", () => {
  const sums = new Map(
    bytes.sums
      .split("\n")
      .filter(Boolean)
      .map((line) => line.split(/ {2}/u).reverse()),
  );
  assert.equal(sha256(bytes.golden), sums.get(goldenName), goldenName);
  assert.equal(sha256(bytes.inputs), sums.get("inputs.json"), "inputs.json");
  assert.equal(sha256(bytes.tagInputs), sums.get("tag-inputs.json"), "tag-inputs.json");
});

test("golden header: schema, versions and input hashes", () => {
  assert.equal(golden.schema, "akademtranslit-golden/2");
  assert.equal(golden.library_version, lib.VERSION);
  assert.equal(golden.rules_version, lib.RULES_VERSION);
  assert.equal(golden.inputs_sha256, sha256(bytes.inputs));
  assert.equal(golden.tag_inputs_sha256, sha256(bytes.tagInputs));
  assert.equal(cases.length, 1233);
  assert.equal(Object.keys(golden.results).length, cases.length);
  assert.equal(tagInputs.tags.length, 57);
  assert.equal(tagInputs.scripts.length, 6);
});

test("every golden field is ported, and only those", () => {
  const goldenFields = new Set(Object.values(golden.results).flatMap((row) => Object.keys(row)));
  assert.equal(goldenFields.size, 30);
  assert.deepEqual([...goldenFields].sort(), Object.keys(FIELDS).sort());
});

const table = [];

for (const [field, func] of Object.entries(FIELDS)) {
  test(`golden field ${field}`, () => {
    const misses = [];
    for (const { id, text } of cases) {
      const expected = golden.results[id][field];
      const actual = outcome(() => func(text));
      if (!sameJson(actual, expected)) misses.push({ id, text, expected, actual });
    }
    table.push([field, cases.length - misses.length, cases.length]);
    assert.deepEqual(misses.slice(0, 5), [], `${field}: ${misses.length} of ${cases.length} differ`);
  });
}

test("golden tags: scriptForTag", () => {
  const misses = [];
  for (const { id, tag } of tagInputs.tags) {
    const actual = outcome(() => lib.scriptForTag(tag));
    if (!sameJson(actual, golden.tags[id])) misses.push({ id, tag, expected: golden.tags[id], actual });
  }
  table.push(["tags", tagInputs.tags.length - misses.length, tagInputs.tags.length]);
  assert.deepEqual(misses, []);
});

test("golden scripts: tagForScript", () => {
  const misses = [];
  for (const { id, script } of tagInputs.scripts) {
    const actual = outcome(() => lib.tagForScript(script));
    if (!sameJson(actual, golden.scripts[id])) misses.push({ id, script, expected: golden.scripts[id], actual });
  }
  table.push(["scripts", tagInputs.scripts.length - misses.length, tagInputs.scripts.length]);
  assert.deepEqual(misses, []);
});

test("golden summary: field — matched / total", (t) => {
  for (const [field, matched, total] of table) t.diagnostic(`${field} — ${matched} / ${total}`);
  const matched = table.reduce((sum, [, n]) => sum + n, 0);
  const total = table.reduce((sum, [, , n]) => sum + n, 0);
  t.diagnostic(`all — ${matched} / ${total}`);
  assert.equal(matched, total);
});
