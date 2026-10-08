// Converts fully static inline style objects in .tsx files into Tailwind arbitrary-property classes
// ("[padding:20px]!"), keeping the "!" so they still win over legacy CSS like an inline style did.
// Usage: node scripts/inline-static-to-tailwind.mjs [--write]
// Skips: dynamic styles, anything under ui/ app/ dev/, the chart containers (their legacy !important
// rules treat inline styles and "!" utilities differently), and elements whose className is an expression.
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";

const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");
const SKIP_FILES = [/components[\\/]charts[\\/]/];
const UNITLESS = new Set(["opacity", "zIndex", "flex", "flexGrow", "flexShrink", "fontWeight", "lineHeight", "order", "zoom"]);

const walk = (d, out = []) => {
  for (const n of fs.readdirSync(d)) {
    const p = path.join(d, n);
    if (n === "__tests__") continue;
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};
const kebab = (k) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
const toClass = (key, value) => {
  let v = typeof value === "number" ? (UNITLESS.has(key) || value === 0 ? String(value) : `${value}px`) : String(value);
  if (/[_[\]'"`\\]/.test(v) || v.includes("{") || v.includes("}")) return null;
  v = v.trim().replace(/\s+/g, "_");
  return `[${kebab(key)}:${v}]!`;
};

const files = walk("src").filter((f) => f.endsWith(".tsx") && !/(^|[\\/])(ui|app|dev)[\\/]/.test(f) && !SKIP_FILES.some((r) => r.test(f)));
let converted = 0, skipped = 0;
const report = [];
for (const f of files) {
  const code = fs.readFileSync(f, "utf8");
  let ast;
  try { ast = parse(code, { sourceType: "module", plugins: ["typescript", "jsx"] }); } catch { continue; }
  const edits = [];
  let fileCount = 0;
  traverse(ast, {
    JSXOpeningElement(p) {
      const attrs = p.node.attributes;
      const style = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "style");
      if (!style || !style.value || style.value.type !== "JSXExpressionContainer" || style.value.expression.type !== "ObjectExpression") return;
      const props = style.value.expression.properties;
      if (!props.every((pr) => pr.type === "ObjectProperty" && !pr.computed && ["StringLiteral", "NumericLiteral"].includes(pr.value.type))) return;
      const cls = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "className");
      if (cls && !(cls.value && cls.value.type === "StringLiteral")) { skipped++; report.push(`skip (className expression) ${f}:${style.loc.start.line}`); return; }
      // animation/transition stay inline: the global prefers-reduced-motion rule and some hover rules are
      // !important in unlayered CSS, which beats an inline style but loses to a "!" utility.
      if (props.some((pr) => /^(animation|transition)/.test(pr.key.name || pr.key.value))) { skipped++; report.push(`skip (animation/transition) ${f}:${style.loc.start.line}`); return; }
      const classes = props.map((pr) => toClass(pr.key.name || pr.key.value, pr.value.value));
      if (classes.some((c) => c === null)) { skipped++; report.push(`skip (value needs escaping) ${f}:${style.loc.start.line}`); return; }
      const add = classes.join(" ");
      if (cls) {
        // append inside the existing string literal and drop the style attribute
        const q = code[cls.value.start];
        const inner = code.slice(cls.value.start + 1, cls.value.end - 1);
        edits.push({ start: cls.value.start, end: cls.value.end, text: `${q}${inner.trim()} ${add}${q}` });
        edits.push({ start: style.start - 1, end: style.end, text: "" }); // include the preceding space
      } else {
        edits.push({ start: style.start, end: style.end, text: `className="${add}"` });
      }
      converted++;
      fileCount++;
    },
  });
  if (!edits.length) continue;
  if (write) {
    let out = code;
    for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
    fs.writeFileSync(f, out);
  }
  report.push(`${write ? "converted" : "would convert"} ${fileCount} in ${f.split(path.sep).join("/")}`);
}
console.log(`${write ? "converted" : "would convert"} ${converted} static inline style objects; skipped ${skipped}`);
for (const r of report) console.log("  " + r);
