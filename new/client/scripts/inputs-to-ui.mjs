// Replaces <input|textarea className="mole-input"> with the shared <Input|Textarea>.
// Only text-like input types are converted. Usage: node scripts/inputs-to-ui.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");
const TEXTLIKE = new Set(["text", "number", "email", "password", "date", "search", "tel", "url", "month", "time"]);

const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "__tests__" || n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};
let total = 0;
for (const file of walk("src").filter((f) => f.endsWith(".jsx") && !f.split(path.sep).includes("ui"))) {
  const code = fs.readFileSync(file, "utf8");
  if (!code.includes("mole-input")) continue;
  const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  const edits = [];
  const used = new Set();
  traverse(ast, {
    JSXOpeningElement(p) {
      const open = p.node;
      const tag = open.name.name;
      if (tag !== "input" && tag !== "textarea") return;
      const cn = open.attributes.find((a) => a.type === "JSXAttribute" && a.name.name === "className");
      if (!cn || cn.value?.type !== "StringLiteral" || cn.value.value !== "mole-input") return;
      if (open.attributes.some((a) => a.type === "JSXSpreadAttribute")) return;
      if (tag === "input") {
        const t = open.attributes.find((a) => a.type === "JSXAttribute" && a.name.name === "type");
        const tv = t ? (t.value?.type === "StringLiteral" ? t.value.value : null) : "text";
        if (!tv || !TEXTLIKE.has(tv)) return;
      }
      const comp = tag === "input" ? "Input" : "Textarea";
      // closing tag for textarea
      if (tag === "textarea" && p.parent.closingElement) edits.push({ start: p.parent.closingElement.name.start, end: p.parent.closingElement.name.end, text: comp });
      edits.push({ start: cn.start - 1, end: cn.end, text: "" }); // drop className and the space before it
      edits.push({ start: open.name.start, end: open.name.end, text: comp });
      used.add(comp);
      total++;
    },
  });
  if (!edits.length) continue;
  console.log(`${file}: ${edits.filter((e) => e.text === "Input" || e.text === "Textarea").length}`);
  if (!write) continue;
  let out = code;
  for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  const rel = path.relative(path.dirname(file), "src/ui").split(path.sep).join("/");
  const uiImports = [...out.matchAll(/import \{([^}]*)\} from ["']([^"']*\/ui)["'];/g)].filter((m) => path.resolve(path.dirname(file), m[2]) === path.resolve("src/ui"));
  const existing = uiImports[0];
  const names = [...used];
  if (existing) out = out.replace(existing[0], `import { ${[...new Set([...existing[1].split(",").map((s) => s.trim()).filter(Boolean), ...names])].join(", ")} } from "${existing[2]}";`);
  else {
    const first = out.indexOf("\n", out.indexOf("import ")) + 1;
    out = out.slice(0, first) + `import { ${names.join(", ")} } from "${rel}";\n` + out.slice(first);
  }
  fs.writeFileSync(file, out);
}
console.log(`${write ? "converted" : "convertible"} ${total} fields`);
