// `npm test` runs `node --test test/`. Node 20 expands a directory argument
// itself and runs every test file in it. Node 21 and later read the argument
// as a glob, so `test/` names this directory's index file, which imports every
// *.test.js file next to it, each once. On Node 20 it does nothing: the files
// are run directly there.

import { readdirSync } from "node:fs";

const major = Number(process.versions.node.split(".")[0]);
if (major >= 21) {
  const here = new URL("./", import.meta.url);
  const files = readdirSync(here)
    .filter((name) => name.endsWith(".test.js"))
    .sort();
  for (const name of files) await import(new URL(name, here));
}
