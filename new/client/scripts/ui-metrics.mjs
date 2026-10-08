// Counts the design-fragmentation metrics from docs/ui-modernization-plan.md section 2.2.
// Usage: node scripts/ui-metrics.mjs [--check] [--write]
import { readFileSync, readdirSync, statSync, writeFileSync, existsSync } from "node:fs";
import { join, extname } from "node:path";
import postcss from "postcss";

const SRC = new URL("../src", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const BASELINE = new URL("../ui-metrics.baseline.json", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");

const walk = (dir, out = []) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (name === "__tests__" || name === "node_modules") continue;
    statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};

// Forward slashes on every platform: the exclusion regexes below (tokens.css, base.css) assume them.
const files = walk(SRC).map((f) => f.replace(/\\/g, "/"));
const css = files.filter((f) => extname(f) === ".css" && !/[\/]styles[\/]tokens\.css$/.test(f));
// The client is TypeScript; .jsx/.js are kept so any leftover legacy file is still counted.
const code = files.filter((f) => [".jsx", ".js", ".tsx", ".ts"].includes(extname(f)));
const jsx = code.filter((f) => [".jsx", ".tsx"].includes(extname(f)));
const read = (f) => readFileSync(f, "utf8");
const count = (files_, re) => files_.reduce((n, f) => n + (read(f).match(re) || []).length, 0);

// !important is allowed in base.css and inside print / reduced-motion media blocks (plan section 2.2); count the rest.
function importantOutsideAllowed() {
  let n = 0;
  for (const f of css.filter((x) => !/[\/]styles[\/]base\.css$/.test(x))) {
    postcss.parse(read(f)).walkDecls((d) => {
      if (!d.important) return;
      let at = d.parent;
      while (at && at.type !== "atrule") at = at.parent;
      if (!(at && at.name === "media" && /print|reduced-motion/.test(at.params))) n++;
    });
  }
  return n;
}

// style={{ key: "literal", other: 12 }} with nothing dynamic inside (no identifiers, calls, ternaries, templates).
const STATIC_ENTRY = /^\s*(?:[A-Za-z_$][\w$]*|"[^"]+")\s*:\s*(?:"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|-?\d+(?:\.\d+)?)\s*(?:,|$)/;
function countStaticInlineStyles(src) {
  let n = 0;
  for (const m of src.matchAll(/style=\{\{([^{}]*)\}\}/g)) {
    let body = m[1].trim();
    if (!body) continue;
    while (body) {
      const hit = STATIC_ENTRY.exec(body);
      if (!hit) break;
      body = body.slice(hit[0].length).trim();
    }
    if (!body) n++;
  }
  return n;
}

const metrics = {
  // Only fully static style objects (every value a string or number literal) count: those can be classes.
  // Data-driven ones (widths from props, computed positions) are the right use of an inline style.
  inlineStyleObjects: jsx.reduce((n, f) => n + countStaticInlineStyles(read(f)), 0),
  hexColorsInCss: count(css, /#[0-9a-fA-F]{3,8}\b/g),
  hexColorsInJs: count(code, /["'`]#[0-9a-fA-F]{3,8}\b/g),
  importantDeclarations: importantOutsideAllowed(),
  inlineSvgs: count(jsx, /<svg\b/g),
  nativeSelects: count(jsx, /<select\b/g),
  clickableDivsWithoutRole: jsx
    .reduce((n, f) => n + (read(f).match(/<(div|span|tr|li|td)\b[^>]*onClick[^>]*>/g) || []).filter((t) => !/role=/.test(t)).length, 0),
  cssFiles: css.length,
  cssLines: css.reduce((n, f) => n + read(f).split("\n").length, 0),
  distinctFontSizes: new Set(css.flatMap((f) => read(f).match(/font-size:\s*[^;]+/g) || [])).size,
  distinctBorderRadii: new Set(css.flatMap((f) => read(f).match(/border-radius:\s*[^;]+/g) || [])).size,
  distinctBoxShadows: new Set(css.flatMap((f) => read(f).match(/box-shadow:\s*[^;]+/g) || [])).size,
};

// Top-level class selectors defined in more than one stylesheet (cascade collisions)
const owners = new Map();
for (const f of css) {
  for (const m of read(f).matchAll(/^\.([a-zA-Z][\w-]*)\s*[{,]/gm)) {
    owners.set(m[1], (owners.get(m[1]) || new Set()).add(f));
  }
}
metrics.duplicateClassDefinitions = [...owners.values()].filter((s) => s.size > 1).length;

console.log(JSON.stringify(metrics, null, 2));

if (process.argv.includes("--write")) {
  writeFileSync(BASELINE, JSON.stringify(metrics, null, 2) + "\n");
  console.log("baseline written");
}

if (process.argv.includes("--check")) {
  if (!existsSync(BASELINE)) {
    console.error("No baseline. Run: npm run ui:metrics -- --write");
    process.exit(1);
  }
  const base = JSON.parse(read(BASELINE));
  const worse = Object.keys(metrics).filter((k) => k in base && metrics[k] > base[k]);
  if (worse.length) {
    console.error("UI metrics got worse: " + worse.map((k) => `${k} ${base[k]} -> ${metrics[k]}`).join(", "));
    process.exit(1);
  }
  console.log("UI metrics ok (no metric above baseline)");
}
