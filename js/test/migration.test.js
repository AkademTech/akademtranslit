// migrationReport, against test/fixtures/migration-<version>.json: the
// Python library's migration_report(text) and migration_report(text,
// protect=False) on every golden input (the golden file has no such field).
// The fixture is made by tools/make-fixtures.py, never by hand.

import assert from "node:assert/strict";
import { test } from "node:test";

import * as lib from "../src/index.js";
import { outcome, readFixture, readGolden, sameJson, sha256 } from "./support.js";

const fixture = readFixture(new RegExp(`^migration-${lib.VERSION.replaceAll(".", "\\.")}\\.json$`, "u"));
const inputs = readGolden("inputs.json");
const cases = JSON.parse(inputs.toString("utf8")).cases;

test("migration fixture header", () => {
  assert.equal(fixture.schema, "akademtranslit-js-fixture-migration/1");
  assert.equal(fixture.library_version, lib.VERSION);
  assert.equal(fixture.rules_version, lib.RULES_VERSION);
  assert.equal(fixture.inputs_sha256, sha256(inputs));
  assert.equal(Object.keys(fixture.results).length, cases.length);
});

for (const [variant, call] of [
  ["protect", (text) => lib.migrationReport(text)],
  ["no_protect", (text) => lib.migrationReport(text, { protect: false })],
]) {
  test(`migrationReport matches Python on every golden input (${variant})`, (t) => {
    const misses = [];
    for (const { id, text } of cases) {
      const expected = fixture.results[id][variant];
      const actual = outcome(() => call(text));
      // As JSON, so the order of the keys counts too.
      if (!sameJson(actual, expected)) misses.push({ id, text, expected, actual });
    }
    t.diagnostic(`migration_report (${variant}) — ${cases.length - misses.length} / ${cases.length}`);
    assert.deepEqual(misses.slice(0, 3), [], `${misses.length} of ${cases.length} differ`);
  });
}

test("migrationReport keys are Python's, in Python's order", () => {
  const report = lib.migrationReport("Isʼhoq va asʼhob");
  assert.deepEqual(Object.keys(report), [
    "words",
    "changed",
    "protected",
    "round_trip",
    "rules_version",
    "check",
    "result",
  ]);
  assert.equal(report.result, "Ishoq va ashob");
  assert.equal(report.round_trip, true);
  assert.deepEqual(report.check, [
    [0, 6, "separator", "Ishoq"],
    [10, 16, "separator", "ashob"],
  ]);
});
