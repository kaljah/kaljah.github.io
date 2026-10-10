#!/usr/bin/env node
/**
 * French translation coverage: lists the interface strings passed to t() / tr() under src/ and
 * compares them with src/i18n/fr.json.
 *
 *   npm run i18n:check                 summary
 *   npm run i18n:check -- --missing    also print the strings without a French entry
 *   npm run i18n:check -- --strict     exit 1 if fr.json has entries no code uses
 *
 * Data values shown through t(variable) (process names, activity lists) are not counted in the
 * coverage, but their entries are not reported as unused while the text appears in the code.
 */
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const SRC = path.join(ROOT, "src");
const fr = JSON.parse(fs.readFileSync(path.join(SRC, "i18n", "fr.json"), "utf8"));
const args = process.argv.slice(2);

const CALL = /\b(?:t|tr)\(/g;
const STRING = /"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g;

/** Value of a "..." or '...' literal. */
function literal(src) {
  if (src[0] === '"') return JSON.parse(src);
  return JSON.parse(`"${src.slice(1, -1).replace(/\\'/g, "'").replace(/"/g, '\\"')}"`);
}

/** String literals of the first argument of t(...) (a plain string or a ternary between strings). */
function firstArgStrings(code, start) {
  let depth = 0;
  let i = start;
  let inStr = "";
  for (; i < code.length; i++) {
    const ch = code[i];
    if (inStr) { if (ch === "\\") i++; else if (ch === inStr) inStr = ""; continue; }
    if (ch === '"' || ch === "'") inStr = ch;
    else if (ch === "(" || ch === "{" || ch === "[") depth++;
    else if (ch === ")" || ch === "}" || ch === "]") { if (depth === 0) break; depth--; }
    else if (ch === "," && depth === 0) break;
  }
  return [...code.slice(start, i).matchAll(STRING)].map((m) => literal(m[0]));
}
const used = new Map();
const mentioned = new Set();
function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== "__tests__") walk(p); continue; }
    if (!/\.(tsx|ts)$/.test(e.name)) continue;
    const code = fs.readFileSync(p, "utf8");
    for (const m of code.matchAll(STRING)) { try { mentioned.add(literal(m[0])); } catch { /* not JSON-compatible */ } }
    for (const m of code.matchAll(CALL)) {
      for (const key of firstArgStrings(code, m.index + m[0].length)) {
        if (!used.has(key)) used.set(key, path.relative(ROOT, p));
      }
    }
  }
}
walk(SRC);

const missing = [...used.keys()].filter((k) => !(k in fr)).sort();
const unused = Object.keys(fr).filter((k) => !used.has(k) && !mentioned.has(k)).sort();
const translated = used.size - missing.length;
console.log(`French: ${translated} of ${used.size} interface strings translated (${((100 * translated) / Math.max(used.size, 1)).toFixed(1)}%), ${missing.length} still in English.`);
if (unused.length) console.log(`${unused.length} entries in fr.json are no longer used.`);
if (args.includes("--missing")) for (const k of missing) console.log(`  ${JSON.stringify(k)}   (${used.get(k)})`);
if (args.includes("--strict") && unused.length) {
  for (const k of unused) console.log(`  unused: ${JSON.stringify(k)}`);
  process.exit(1);
}
