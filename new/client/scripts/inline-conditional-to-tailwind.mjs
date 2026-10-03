// Moves inline style objects into Tailwind arbitrary-property utilities, including values that switch on a condition
// (`color: ok ? "#059669" : "inherit"` becomes a conditional class). A property is left inline when any legacy CSS rule
// sets it with !important (a layered important utility would then win over that rule, which an inline style never did).
// Usage: node scripts/inline-conditional-to-tailwind.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
import postcss from "postcss";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");

const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "__tests__" || n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};

// Legacy rules that use !important: { props, tag, classes } of the rule's subject compound selector.
const importantRules = [];
const globalProps = new Set(); // props set by a rule we cannot narrow to a tag or class
for (const f of walk("src").filter((x) => x.endsWith(".css"))) {
  const root = postcss.parse(fs.readFileSync(f, "utf8"));
  // selectors such as div[style*="grid-template-columns"] match on the inline style itself
  root.walkRules((r) => {
    for (const m of r.selector.matchAll(/\[style[*^$|~]?=["']?([a-z-]+)/g)) globalProps.add(m[1]);
    const props = new Set();
    r.walkDecls((d) => {
      if (!d.important) return;
      // print and reduced-motion resets only apply in those modes; display:none there still has to win
      let at = r.parent;
      while (at && at.type !== "atrule") at = at.parent;
      const modal = at && at.name === "media" && /print|reduced-motion/.test(at.params);
      if (!modal || d.prop === "display") props.add(d.prop);
    });
    if (!props.size) return;
    for (const sel of r.selectors) {
      const compound = sel.trim().match(/([^\s>+~]+)$/)?.[1] ?? "";
      const tag = compound.match(/^[a-z][a-z0-9]*/)?.[0] ?? null;
      const classes = [...compound.matchAll(/[.](-?[_a-zA-Z][\w-]*)/g)].map((m) => m[1]);
      if (!tag && !classes.length) props.forEach((x) => globalProps.add(x));
      else importantRules.push({ props, tag, classes });
    }
  });
}

const UNITLESS = new Set(["opacity", "flex", "flexGrow", "flexShrink", "fontWeight", "lineHeight", "zIndex", "order", "zoom"]);
const kebab = (k) => k.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
const skipProps = new Set(["animation", "transition", "transform", "willChange"]);

// One static value -> "[prop:value]!" or null when it cannot be written safely.
const why = {};
let ctx = { tag: null, classText: "", dynamic: false };
const blocked = (prop) => {
  if (globalProps.has(prop)) return true;
  return importantRules.some((r) => {
    if (!r.props.has(prop)) return false;
    if (r.tag && ctx.tag && r.tag !== ctx.tag) return false;
    if (!r.classes.length) return true;
    const have = new Set(ctx.classText.split(/\s+/));
    return ctx.dynamic || r.classes.every((c) => have.has(c));
  });
};
const toClass = (key, node) => {
  if (skipProps.has(key) || blocked(kebab(key))) { why[key] = (why[key] || 0) + 1; return null; }
  let v;
  if (node.type === "StringLiteral") v = node.value;
  else if (node.type === "NumericLiteral") v = UNITLESS.has(key) || node.value === 0 ? String(node.value) : `${node.value}px`;
  else { why["nonliteral:" + key] = (why["nonliteral:" + key] || 0) + 1; return null; }
  if (!/^[A-Za-z0-9#%.,()\-\s/+*:]+$/.test(v)) { why["chars"] = (why["chars"] || 0) + 1; return null; }
  return `[${kebab(key)}:${v.trim().replace(/\s+/g, "_")}]!`;
};

let converted = 0;
let total = 0;
const files = walk("src").filter((f) => f.endsWith(".jsx"));
for (const file of files) {
  const code = fs.readFileSync(file, "utf8");
  const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  const edits = [];
  traverse(ast, {
    JSXOpeningElement(p) {
      const attrs = p.node.attributes;
      const style = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "style");
      if (!style || style.value?.type !== "JSXExpressionContainer" || style.value.expression.type !== "ObjectExpression") return;
      total++;
      {
        const nm = p.node.name;
        const cnAttr = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "className");
        let classText = "";
        let dynamic = false;
        if (cnAttr?.value) {
          const v = cnAttr.value;
          if (v.type === "StringLiteral") classText = v.value;
          else if (v.type === "JSXExpressionContainer" && v.expression.type === "TemplateLiteral") {
            classText = v.expression.quasis.map((q) => q.value.raw).join(" ");
            dynamic = v.expression.expressions.length > 0;
          } else dynamic = true;
        }
        ctx = { tag: nm.type === "JSXIdentifier" && /^[a-z]/.test(nm.name) ? nm.name : null, classText, dynamic };
      }
      const statics = [];
      const conds = [];
      for (const prop of style.value.expression.properties) {
        if (prop.type !== "ObjectProperty" || prop.computed) return;
        const key = prop.key.type === "Identifier" ? prop.key.name : prop.key.value;
        const val = prop.value;
        if (val.type === "ConditionalExpression") {
          const a = toClass(key, val.consequent);
          const b = toClass(key, val.alternate);
          if (!a || !b) return;
          const test = code.slice(val.test.start, val.test.end);
          if (test.includes("`")) return;
          conds.push(`\${${test} ? "${a}" : "${b}"}`);
        } else {
          const c = toClass(key, val);
          if (!c) return;
          statics.push(c);
        }
      }
      const cls = [...statics, ...conds].join(" ");
      const cn = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "className");
      let classEdit;
      if (!cn) classEdit = { start: style.start, end: style.end, text: `className={\`${cls}\`}` };
      else if (cn.value.type === "StringLiteral") {
        if (cn.value.value.includes("`") || cn.value.value.includes("${")) return;
        classEdit = { start: cn.start, end: cn.end, text: `className={\`${cn.value.value} ${cls}\`}` };
      } else if (cn.value.type === "JSXExpressionContainer" && cn.value.expression.type === "TemplateLiteral") {
        const e = cn.value.expression;
        classEdit = { start: e.end - 1, end: e.end - 1, text: ` ${cls}` };
      } else return;
      converted++;
      edits.push(classEdit);
      if (cn) {
        // drop the style attribute together with its leading whitespace
        let s = style.start;
        while (/\s/.test(code[s - 1])) s--;
        edits.push({ start: s, end: style.end, text: "" });
      }
    },
  });
  if (!edits.length) continue;
  let out = code;
  for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
  if (write) fs.writeFileSync(file, out);
  else console.log(`${file}: ${edits.length} edits`);
}
console.log(`${write ? "converted" : "convertible"} ${converted} of ${total} inline styles`);

if (process.argv.includes("--why")) console.log(Object.entries(why).sort((a, b) => b[1] - a[1]).slice(0, 25));
