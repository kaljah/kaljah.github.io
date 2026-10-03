// Replaces the hand-drawn inline <svg> icons in `const Icon = { Name: () => (<svg>…</svg>) }` lookup objects with
// lucide-react components chosen by icon name (the shapes are redrawn, which the plan accepts). The lookup keeps
// its shape, so call sites are untouched; the stroke width and any `style` on the old svg are carried over, and the
// size still comes from the CSS rule that targeted the svg.
// Usage: node scripts/icons-to-lucide.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");

const NAMES = {
  Close: "X", X: "X", Check: "Check", ChevronRight: "ChevronRight", ChevronDown: "ChevronDown", ArrowLeft: "ArrowLeft",
  Upload: "CloudUpload", File: "File", FileExcel: "FileSpreadsheet", FileXlsx: "FileSpreadsheet", FileCsv: "FileText",
  Wand: "Wand2", Search: "Search", Warning: "TriangleAlert", Info: "Info", Flame: "Flame", Wind: "Wind",
  Container: "Container", Cpu: "Cpu", Layers: "Layers", Zap: "Zap", Activity: "Activity", Processing: "Activity",
  Settings: "Settings", Columns: "Columns3", Download: "Download", Globe: "Globe",
};

const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "node_modules" || n === "__tests__") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};

let total = 0;
for (const file of walk("src").filter((f) => f.endsWith(".jsx"))) {
  const code = fs.readFileSync(file, "utf8");
  if (!/const Icons? = \{/.test(code)) continue;
  const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  const edits = [];
  const used = new Set();
  traverse(ast, {
    VariableDeclarator(p) {
      if (!["Icon", "Icons"].includes(p.node.id.name) || p.node.init?.type !== "ObjectExpression") return;
      for (const prop of p.node.init.properties) {
        if (prop.type !== "ObjectProperty") continue;
        const name = prop.key.name;
        const lucide = NAMES[name];
        const fn = prop.value;
        if (!lucide || fn.type !== "ArrowFunctionExpression") continue;
        const body = fn.body.type === "ParenthesizedExpression" ? fn.body.expression : fn.body;
        if (body.type !== "JSXElement" || body.openingElement.name.name !== "svg") continue;
        const attr = (n) => body.openingElement.attributes.find((a) => a.type === "JSXAttribute" && a.name.name === n);
        const sw = attr("strokeWidth")?.value;
        const style = attr("style");
        const swText = sw ? (sw.type === "StringLiteral" ? `{${sw.value}}` : code.slice(sw.start, sw.end)) : "{2}";
        const styleText = style ? ` ${code.slice(style.start, style.end)}` : "";
        const params = fn.params.length ? code.slice(fn.params[0].start, fn.params[0].end) : "";
        used.add(lucide);
        edits.push({
          start: prop.value.start,
          end: prop.value.end,
          text: `(${params}) => <${lucide}Icon strokeWidth=${swText} aria-hidden="true"${styleText} />`,
          lucide,
        });
      }
    },
  });
  if (!edits.length) continue;
  total += edits.length;
  if (!write) continue;
  let out = code;
  for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  const imports = [...used].sort().map((n) => `${n} as ${n}Icon`).join(", ");
  out = out.replace(/^(import[^\n]*\n)/m, `$1import { ${imports} } from "lucide-react";\n`);
  fs.writeFileSync(file, out);
}
console.log(`${write ? "replaced" : "would replace"} ${total} icons`);
