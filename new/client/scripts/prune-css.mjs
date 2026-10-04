// Removes CSS rules whose class selectors are not referenced anywhere in the source.
// Conservative: keeps third-party class prefixes and any class that could be built dynamically
// (template-literal or concatenated prefixes/suffixes). Usage: node scripts/prune-css.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import postcss from "postcss";

const write = process.argv.includes("--write");
const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "__tests__" || n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};
const files = walk("src");
const css = files.filter((f) => f.endsWith(".css") && !/styles[\/](tokens|base)\.css$/.test(f));
const srcText = files.filter((f) => /\.(jsx?|html)$/.test(f)).map((f) => fs.readFileSync(f, "utf8")).join("\n") +
  fs.readFileSync("index.html", "utf8");

const prefixes = new Set();
const suffixes = new Set();
for (const m of srcText.matchAll(/([\w-]{2,})\$\{/g)) prefixes.add(m[1]);
for (const m of srcText.matchAll(/\}([\w-]{3,})/g)) suffixes.add(m[1]);
for (const m of srcText.matchAll(/["']([\w-]{2,}-)["']\s*\+/g)) prefixes.add(m[1]);
for (const m of srcText.matchAll(/\+\s*["'](-[\w-]{2,})["']/g)) suffixes.add(m[1]);

const THIRD_PARTY = /^(leaflet|recharts|cmdk|radix|jspdf|html2canvas)/;
// Whole-token match: `top-bar` must not count as used just because `top-bar-actions` exists.
const tokenInSource = (tok) =>
  new RegExp(`(?<![\\w-])${tok.replace(/-/g, "\\-")}(?![\\w-])`).test(srcText);
const used = new Map();
const isUsed = (tok) => {
  if (used.has(tok)) return used.get(tok);
  let r = THIRD_PARTY.test(tok) || tokenInSource(tok);
  if (!r) for (const p of prefixes) if (tok.startsWith(p)) { r = true; break; }
  if (!r) for (const s of suffixes) if (tok.endsWith(s)) { r = true; break; }
  used.set(tok, r);
  return r;
};

let totalRemoved = 0, totalLines = 0;
for (const f of css) {
  const before = fs.readFileSync(f, "utf8");
  const root = postcss.parse(before);
  let removed = 0;
  root.walkRules((rule) => {
    if (rule.parent?.type === "atrule" && /keyframes$/i.test(rule.parent.name)) return;
    const sels = rule.selectors;
    const dead = sels.every((sel) => {
      const toks = [...sel.matchAll(/\.(-?[A-Za-z_][\w-]*)/g)].map((m) => m[1]);
      return toks.some((t) => !isUsed(t));
    });
    if (dead) { rule.remove(); removed++; }
  });
  // keyframes never referenced by any CSS animation or JS
  const allCss = css.map((c) => fs.readFileSync(c, "utf8")).join("\n") + srcText;
  root.walkAtRules(/keyframes$/i, (at) => {
    const refs = allCss.split(at.params).length - 1;
    if (refs <= 1) { at.remove(); removed++; }
  });
  root.walkAtRules((at) => { if (at.nodes && at.nodes.length === 0) at.remove(); });
  const after = root.toString();
  if (removed) {
    const dl = before.split("\n").length - after.split("\n").length;
    totalRemoved += removed; totalLines += dl;
    console.log(`${f}: -${removed} rules (${dl} lines)`);
    if (write) fs.writeFileSync(f, after);
  }
}
console.log(`${write ? "removed" : "would remove"} ${totalRemoved} rules, ${totalLines} lines`);
