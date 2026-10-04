// Moves text colors to AA-safe shades and darkens fills that carry white text. Usage: node scripts/aa-colors.mjs [--write]
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
const TEXT = {
  "var(--color-ink-400)": "var(--color-ink-600)",
  "var(--color-green-500)": "var(--color-green-700)",
  "var(--color-green-600)": "var(--color-green-700)",
  "var(--color-amber-500)": "var(--color-amber-700)",
  "var(--color-amber-600)": "var(--color-amber-700)",
  "var(--color-red-500)": "var(--color-red-700)",
  "var(--color-red-600)": "var(--color-red-700)",
  "var(--color-blue-500)": "var(--color-blue-700)",
  "var(--color-violet-500)": "var(--color-violet-700)",
  "var(--color-brand-500)": "var(--color-brand-700)",
  "var(--color-brand-600)": "var(--color-brand-700)",
  "var(--color-sky-600)": "var(--color-blue-700)",
};
const FILL = {
  "var(--color-green-500)": "var(--color-green-700)",
  "var(--color-green-600)": "var(--color-green-700)",
  "var(--color-red-500)": "var(--color-red-700)",
  "var(--color-red-600)": "var(--color-red-700)",
  "var(--color-blue-500)": "var(--color-blue-700)",
  "var(--color-amber-500)": "var(--color-amber-700)",
  "var(--color-amber-600)": "var(--color-amber-700)",
  "var(--color-violet-500)": "var(--color-violet-700)",
};
const WHITE = new Set(["white", "#fff", "#ffffff", "var(--color-white)"]);
let n = 0;
for (const f of walk("src").filter((x) => x.endsWith(".css") && !/tokens\.css$/.test(x))) {
  const root = postcss.parse(fs.readFileSync(f, "utf8"));
  root.walkRules((rule) => {
    if (/disabled|placeholder|::?before|::?after/.test(rule.selector)) return;
    const color = rule.nodes?.find((d) => d.type === "decl" && d.prop === "color");
    const whiteText = color && WHITE.has(color.value.trim());
    if (color && TEXT[color.value.trim()] && !/\bth\b/.test("") ) { color.value = TEXT[color.value.trim()]; n++; }
    if (/(^|[\s,>+~])th\b/.test(rule.selector) && color && color.value.trim() === "var(--color-ink-500)") { color.value = "var(--color-ink-600)"; n++; }
    if (whiteText) {
      rule.walkDecls(/^background(-color)?$/, (d) => {
        let v = d.value;
        for (const [a, b] of Object.entries(FILL)) v = v.split(a).join(b);
        if (v !== d.value) { d.value = v; n++; }
      });
    }
  });
  if (write) fs.writeFileSync(f, root.toString());
}
console.log(`${write ? "changed" : "would change"} ${n} declarations`);
