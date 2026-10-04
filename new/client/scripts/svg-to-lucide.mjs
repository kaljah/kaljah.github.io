// Replaces inline <svg> icons with lucide-react components when the path data matches a lucide icon exactly.
// Usage: node scripts/svg-to-lucide.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");

// 1) index lucide icons by normalized geometry
const iconsDir = "node_modules/lucide-react/dist/esm/icons";
const norm = (tag, attrs) => tag + ":" + Object.entries(attrs).filter(([k]) => k !== "key").sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => `${k}=${String(v).replace(/\s+/g, " ").trim()}`).join(";");
const index = new Map();
for (const f of fs.readdirSync(iconsDir).filter((x) => x.endsWith(".js"))) {
  const src = fs.readFileSync(path.join(iconsDir, f), "utf8");
  const m = /__iconNode\s*=\s*(\[[\s\S]*?\]);\s*\nconst/.exec(src);
  const name = /createLucideIcon\("([^"]+)"/.exec(src)?.[1];
  if (!m || !name) continue;
  let node;
  try { node = Function(`return ${m[1]}`)(); } catch { continue; }
  const key = node.map(([t, a]) => norm(t, a)).sort().join("|");
  const pascal = name.split("-").map((s) => s[0].toUpperCase() + s.slice(1)).join("");
  if (!index.has(key)) index.set(key, pascal);
}

const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "__tests__" || n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};
const staticAttrs = (el) => {
  const o = {};
  for (const a of el.openingElement.attributes) {
    if (a.type !== "JSXAttribute") return null;
    const n = a.name.name.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
    if (!a.value) o[n] = true;
    else if (a.value.type === "StringLiteral") o[n] = a.value.value;
    else return null;
  }
  return o;
};

let total = 0, matched = 0;
for (const file of walk("src").filter((f) => f.endsWith(".jsx") && !/[\/]ui[\/]/.test(f))) {
  const code = fs.readFileSync(file, "utf8");
  if (!code.includes("<svg")) continue;
  const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  const edits = [];
  const used = new Set();
  traverse(ast, {
    JSXElement(p) {
      if (p.node.openingElement.name.name !== "svg") return;
      total++;
      const kids = p.node.children.filter((c) => c.type === "JSXElement");
      if (p.node.children.some((c) => c.type === "JSXExpressionContainer" && c.expression.type !== "JSXEmptyExpression")) return;
      const parts = [];
      for (const k of kids) {
        const a = staticAttrs(k); if (!a) return;
        parts.push(norm(k.openingElement.name.name, a));
      }
      const name = index.get(parts.sort().join("|"));
      if (!name) return;
      const props = {};
      for (const a of p.node.openingElement.attributes) {
        if (a.type !== "JSXAttribute") return;
        const n = a.name.name;
        if (["xmlns", "viewBox", "fill", "stroke", "strokeLinecap", "strokeLinejoin"].includes(n)) continue;
        props[n] = a.value ? code.slice(a.value.start, a.value.end) : "{true}";
      }
      const size = props.width ?? props.height;
      delete props.width; delete props.height;
      const attrs = [];
      if (size) attrs.push(`size=${size.startsWith("{") ? size : size}`);
      for (const [k, v] of Object.entries(props)) attrs.push(`${k}=${v}`);
      if (!("aria-hidden" in props) && !("aria-label" in props) && !("role" in props)) attrs.push(`aria-hidden="true"`);
      edits.push({ start: p.node.start, end: p.node.end, text: `<${name} ${attrs.join(" ")} />`, name });
      used.add(name); matched++;
    },
  });
  if (!edits.length) continue;
  console.log(`${file}: ${edits.length} svg -> ${[...new Set(edits.map((e) => e.name))].join(",")}`);
  if (!write) continue;
  let out = code;
  for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  const existing = /import \{([^}]*)\} from ["']lucide-react["'];/.exec(out);
  if (existing) {
    const names = new Set(existing[1].split(",").map((s) => s.trim()).filter(Boolean));
    for (const u of used) names.add(u);
    out = out.replace(existing[0], `import { ${[...names].join(", ")} } from "lucide-react";`);
  } else {
    const first = out.indexOf("\n", out.indexOf("import ")) + 1;
    out = out.slice(0, first) + `import { ${[...used].join(", ")} } from "lucide-react";\n` + out.slice(first);
  }
  fs.writeFileSync(file, out);
}
console.log(`${matched}/${total} inline svgs ${write ? "replaced" : "replaceable"}`);
