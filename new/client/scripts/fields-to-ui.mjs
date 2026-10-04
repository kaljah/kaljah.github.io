// Converts <div className="input-group"><label>..</label><Input|Textarea|NativeSelect .../></div> into <Field label=..>.
// Only that exact shape is converted. Usage: node scripts/fields-to-ui.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");
const CONTROLS = new Set(["Input", "Textarea", "NativeSelect"]);

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
  if (!code.includes("input-group")) continue;
  const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  const edits = [];
  traverse(ast, {
    JSXElement(p) {
      const open = p.node.openingElement;
      if (open.name.name !== "div" || !p.node.closingElement) return;
      const attrs = open.attributes;
      if (attrs.length !== 1 || attrs[0].type !== "JSXAttribute" || attrs[0].name.name !== "className" || attrs[0].value?.value !== "input-group") return;
      const kids = p.node.children.filter((c) => !(c.type === "JSXText" && !c.value.trim()));
      if (kids.length !== 2) return;
      const [label, control] = kids;
      if (label.type !== "JSXElement" || label.openingElement.name.name !== "label") return;
      if (label.openingElement.attributes.some((a) => a.type !== "JSXAttribute" || !["className"].includes(a.name.name))) return;
      if (control.type !== "JSXElement" || !CONTROLS.has(control.openingElement.name.name)) return;
      if (label.children.some((c) => c.type === "JSXElement" && /^(input|select|button|a)$/.test(c.openingElement.name.name))) return;
      const inner = code.slice(label.openingElement.end, label.closingElement.start).trim();
      if (!inner) return;
      const labelProp = /^[^<>{}]+$/.test(inner) ? `label="${inner.replace(/"/g, "&quot;")}"` : `label={<>${inner}</>}`;
      edits.push({ start: p.node.start, end: p.node.end, text: `<Field className="input-group" ${labelProp}>\n${code.slice(control.start, control.end)}\n</Field>` });
      total++;
    },
  });
  if (!edits.length) continue;
  // drop edits nested inside other edits (outermost wins; nesting cannot happen for this exact shape)
  console.log(`${file}: ${edits.length}`);
  if (!write) continue;
  let out = code;
  for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  const uiImports = [...out.matchAll(/import \{([^}]*)\} from ["']([^"']*\/ui)["'];/g)].filter((m) => path.resolve(path.dirname(file), m[2]) === path.resolve("src/ui"));
  const existing = uiImports[0];
  const rel = path.relative(path.dirname(file), "src/ui").split(path.sep).join("/");
  if (existing) out = out.replace(existing[0], `import { ${[...new Set([...existing[1].split(",").map((s) => s.trim()).filter(Boolean), "Field"])].join(", ")} } from "${existing[2]}";`);
  else {
    const first = out.indexOf("\n", out.indexOf("import ")) + 1;
    out = out.slice(0, first) + `import { Field } from "${rel}";\n` + out.slice(first);
  }
  fs.writeFileSync(file, out);
}
console.log(`${write ? "converted" : "convertible"} ${total} fields`);
