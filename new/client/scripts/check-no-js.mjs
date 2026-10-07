// Fails when a .js/.jsx source file exists under src/. The client is TypeScript (.ts/.tsx).
// Usage: node scripts/check-no-js.mjs   (npm run check:ts)
import { readdirSync, statSync } from "node:fs";
import { join, extname, relative } from "node:path";
import { fileURLToPath } from "node:url";

const SRC = fileURLToPath(new URL("../src", import.meta.url));
const ROOT = fileURLToPath(new URL("..", import.meta.url));

const found = [];
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules") continue;
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if ([".js", ".jsx"].includes(extname(p))) found.push(relative(ROOT, p));
  }
};
walk(SRC);

if (found.length) {
  console.error(`Found ${found.length} .js/.jsx file(s) under src/. Use .ts/.tsx instead:`);
  for (const f of found) console.error(`  ${f.replace(/\\/g, "/")}`);
  process.exit(1);
}
console.log("No .js/.jsx files under src/");
