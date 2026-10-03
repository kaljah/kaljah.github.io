// Tailwind emits arbitrary-property utilities ordered by name, so `[border-bottom:..]` lands before `[border:..]`
// and the shorthand wins. When a className has a longhand utility after its shorthand (same variant prefix), the
// longhand gets a doubled selector (`[&&]:`), which wins on specificity whatever the emit order.
// Usage: node scripts/fix-longhand-order.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");

const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};

// Split a utility token into { prefix, prop, inner, bang } when it ends in an arbitrary-property bracket group.
const splitToken = (tok) => {
  const bang = tok.endsWith("!");
  const body = bang ? tok.slice(0, -1) : tok;
  if (!body.endsWith("]")) return null;
  let depth = 0;
  let start = -1;
  for (let i = body.length - 1; i >= 0; i--) {
    if (body[i] === "]") depth++;
    else if (body[i] === "[") {
      depth--;
      if (depth === 0) {
        start = i;
        break;
      }
    }
  }
  if (start < 0) return null;
  const inner = body.slice(start + 1, -1);
  const m = inner.match(/^([a-z-]+):/);
  if (!m) return null;
  return { prefix: body.slice(0, start), prop: m[1], inner, bang };
};

const classStrings = (ast) => {
  const nodes = [];
  const collect = (node) => {
    if (!node) return;
    switch (node.type) {
      case "StringLiteral":
        nodes.push({ start: node.start + 1, end: node.end - 1 });
        break;
      case "TemplateLiteral":
        node.quasis.forEach((q) => nodes.push({ start: q.start, end: q.end }));
        node.expressions.forEach(collect);
        break;
      case "JSXExpressionContainer":
        collect(node.expression);
        break;
      case "ConditionalExpression":
        collect(node.consequent);
        collect(node.alternate);
        break;
      case "LogicalExpression":
      case "BinaryExpression":
        collect(node.left);
        collect(node.right);
        break;
      case "CallExpression":
        if (["cn", "clsx", "classNames"].includes(node.callee.name)) node.arguments.forEach(collect);
        break;
      default:
    }
  };
  traverse(ast, {
    JSXAttribute(p) {
      if (p.node.name.name === "className") collect(p.node.value);
    },
  });
  return nodes;
};

let fixed = 0;
for (const file of walk("src").filter((f) => f.endsWith(".jsx") && !/__tests__/.test(f))) {
  const code = fs.readFileSync(file, "utf8");
  if (!code.includes("[")) continue;
  let ast;
  try {
    ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  } catch {
    continue;
  }
  const edits = [];
  for (const s of classStrings(ast)) {
    const text = code.slice(s.start, s.end);
    const tokens = text.split(/(\s+)/);
    const seen = [];
    let changed = false;
    const out = tokens.map((t) => {
      const sp = t.trim() ? splitToken(t) : null;
      if (!sp) return t;
      const doubled = sp.prefix.includes("[&&]:");
      const dependsOnShorthand = seen.some((o) => o.prefix === sp.prefix && sp.prop.startsWith(`${o.prop}-`));
      seen.push(sp);
      if (dependsOnShorthand && !doubled) {
        changed = true;
        fixed++;
        return `${sp.prefix}[&&]:[${sp.inner}]${sp.bang ? "!" : ""}`;
      }
      return t;
    });
    if (changed) edits.push({ start: s.start, end: s.end, text: out.join("") });
  }
  if (write && edits.length) {
    let res = code;
    for (const e of edits.sort((a, b) => b.start - a.start)) res = res.slice(0, e.start) + e.text + res.slice(e.end);
    fs.writeFileSync(file, res);
  }
}
console.log(`${write ? "fixed" : "would fix"} ${fixed} longhand utilities`);
