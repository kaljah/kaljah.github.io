// Replaces <button className="btn-primary|btn-secondary|btn-ghost"> with the shared <Button variant>.
// Native buttons default to type=submit, so a missing type is made explicit to keep behavior.
// Usage: node scripts/buttons-to-ui.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");
const VARIANT = { "btn-primary": null, "btn-secondary": "secondary", "btn-secondary-unified": "secondary", "btn-ghost": "ghost" };

const SKIP = new Set(["Login.jsx"]);
const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "__tests__" || n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};
let total = 0;
for (const file of walk("src").filter((f) => f.endsWith(".jsx") && !f.split(path.sep).includes("ui") && !SKIP.has(path.basename(f)))) {
  const code = fs.readFileSync(file, "utf8");
  if (!/btn-(primary|secondary|ghost)/.test(code)) continue;
  const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  const edits = [];
  traverse(ast, {
    JSXElement(p) {
      const open = p.node.openingElement;
      if (open.name.name !== "button" || !p.node.closingElement) return;
      const cn = open.attributes.find((a) => a.type === "JSXAttribute" && a.name.name === "className");
      if (!cn || cn.value?.type !== "StringLiteral" || !(cn.value.value in VARIANT)) return;
      if (open.attributes.some((a) => a.type === "JSXSpreadAttribute")) return;
      const variant = VARIANT[cn.value.value];
      const hasType = open.attributes.some((a) => a.type === "JSXAttribute" && a.name.name === "type");
      const extra = [variant ? `variant="${variant}"` : null, hasType ? null : `type="submit"`].filter(Boolean).join(" ");
      edits.push({ start: p.node.closingElement.start, end: p.node.closingElement.end, text: "</Button>" });
      edits.push({ start: cn.start, end: cn.end, text: extra });
      edits.push({ start: open.name.start, end: open.name.end, text: "Button" });
      total++;
    },
  });
  if (!edits.length) continue;
  console.log(`${file}: ${edits.length / 3}`);
  if (!write) continue;
  let out = code;
  for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  const rel = path.relative(path.dirname(file), "src/ui").split(path.sep).join("/");
  const existing = /import \{([^}]*)\} from ["']([^"']*\/ui)["'];/.exec(out);
  if (existing) out = out.replace(existing[0], `import { ${[...new Set([...existing[1].split(",").map((s) => s.trim()).filter(Boolean), "Button"])].join(", ")} } from "${existing[2]}";`);
  else {
    const first = out.indexOf("\n", out.indexOf("import ")) + 1;
    out = out.slice(0, first) + `import { Button } from "${rel}";\n` + out.slice(first);
  }
  fs.writeFileSync(file, out);
}
console.log(`${write ? "converted" : "convertible"} ${total} buttons`);
