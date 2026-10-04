// AA-safe text colors for inline styles and text-[color:...] utility classes.
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const MAP = { "#10b981": "#2e7d32", "#ef4444": "#b91c1c", "#ff6600": "#c2410c", "#ff6b00": "#c2410c", "#f59e0b": "#b45309", "#8b5cf6": "#6d28d9", "#3b82f6": "#1d4ed8", "#0284c7": "#0369a1", "#94a3b8": "#475569", "#e65c00": "#c2410c" };
const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "__tests__" || n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};
let total = 0;
for (const f of walk("src").filter((x) => x.endsWith(".jsx") && !x.split(path.sep).includes("ui") && !x.split(path.sep).includes("dev"))) {
  let code = fs.readFileSync(f, "utf8");
  const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  const edits = [];
  traverse(ast, {
    JSXAttribute(p) {
      if (p.node.name.name !== "style") return;
      const ex = p.node.value?.expression;
      if (!ex || ex.type !== "ObjectExpression") return;
      for (const prop of ex.properties) {
        if (prop.type !== "ObjectProperty" || (prop.key.name || prop.key.value) !== "color") continue;
        const v = prop.value;
        if (v.type === "StringLiteral" && MAP[v.value.toLowerCase()]) edits.push({ start: v.start, end: v.end, text: `"${MAP[v.value.toLowerCase()]}"` });
        // ternaries: color: cond ? "#10b981" : "..."
        if (v.type === "ConditionalExpression") for (const b of [v.consequent, v.alternate]) if (b.type === "StringLiteral" && MAP[b.value.toLowerCase()]) edits.push({ start: b.start, end: b.end, text: `"${MAP[b.value.toLowerCase()]}"` });
      }
    },
  });
  if (edits.length) { for (const e of edits.sort((a, b) => b.start - a.start)) code = code.slice(0, e.start) + e.text + code.slice(e.end); }
  const before = code;
  code = code.replace(/text-\[color:(#[0-9a-fA-F]{6})\]/g, (m, h) => (MAP[h.toLowerCase()] ? `text-[color:${MAP[h.toLowerCase()]}]` : m));
  const n = edits.length + (before === code ? 0 : 1);
  if (n) { fs.writeFileSync(f, code); total += n; }
}
console.log("files/edits touched:", total);
