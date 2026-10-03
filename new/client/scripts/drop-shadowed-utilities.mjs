// Legacy CSS was unlayered, so a legacy class always beat a Tailwind utility on the same element. After the
// css-to-utilities codemod both are utilities, and the emit order is arbitrary. Where an element carries an
// arbitrary-property utility (from a converted class or inline style) and a plain Tailwind utility that sets the
// same property under the same variants, the plain one never took effect before: drop it.
// Usage: node scripts/drop-shadowed-utilities.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");

const baseProp = (p) => p.split("-")[0];
const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};

const RULES = [
  [/^-?m-/, ["margin"]],
  [/^-?m[xe]-/, ["margin-left", "margin-right"]],
  [/^-?my-/, ["margin-top", "margin-bottom"]],
  [/^-?mt-/, ["margin-top"]],
  [/^-?mb-/, ["margin-bottom"]],
  [/^-?ml-/, ["margin-left"]],
  [/^-?mr-/, ["margin-right"]],
  [/^p-/, ["padding"]],
  [/^px-/, ["padding-left", "padding-right"]],
  [/^py-/, ["padding-top", "padding-bottom"]],
  [/^pt-/, ["padding-top"]],
  [/^pb-/, ["padding-bottom"]],
  [/^pl-/, ["padding-left"]],
  [/^pr-/, ["padding-right"]],
  [/^gap-/, ["gap"]],
  [/^gap-x-/, ["column-gap"]],
  [/^gap-y-/, ["row-gap"]],
  [/^w-/, ["width"]],
  [/^min-w-/, ["min-width"]],
  [/^max-w-/, ["max-width"]],
  [/^h-/, ["height"]],
  [/^min-h-/, ["min-height"]],
  [/^max-h-/, ["max-height"]],
  [/^size-/, ["width", "height"]],
  [/^text-(xs|sm|base|md|lg|xl|[2-9]xl)$/, ["font-size", "line-height"]],
  [/^text-(left|center|right|justify|start|end)$/, ["text-align"]],
  [/^font-(thin|light|normal|medium|semibold|bold|extrabold|black)$/, ["font-weight"]],
  [/^font-(mono|sans|serif)$/, ["font-family"]],
  [/^leading-/, ["line-height"]],
  [/^tracking-/, ["letter-spacing"]],
  [/^bg-/, ["background-color"]],
  [/^border$/, ["border-width"]],
  [/^border-(t|b|l|r|x|y)(-\d+)?$/, ["border-width"]],
  [/^rounded/, ["border-radius"]],
  [/^(flex|inline-flex)$/, ["display"]],
  [/^(grid|inline-grid|block|inline-block|inline|hidden|contents|table)$/, ["display"]],
  [/^flex-(col|row)/, ["flex-direction"]],
  [/^flex-(wrap|nowrap)/, ["flex-wrap"]],
  [/^items-/, ["align-items"]],
  [/^justify-/, ["justify-content"]],
  [/^shadow/, ["box-shadow"]],
  [/^opacity-/, ["opacity"]],
  [/^overflow-/, ["overflow"]],
  [/^(relative|absolute|fixed|sticky)$/, ["position"]],
  [/^z-/, ["z-index"]],
  [/^cursor-/, ["cursor"]],
  [/^whitespace-/, ["white-space"]],
];

// { variants, props } for a plain Tailwind class; null for anything else (arbitrary, unknown).
const plainTailwind = (token) => {
  if (token.includes("[") || token.endsWith("!") || token.startsWith("!")) return null;
  const m = token.match(/^((?:[a-z0-9-]+:)*)(.+)$/);
  if (!m) return null;
  for (const [re, props] of RULES) if (re.test(m[2])) return { variants: m[1], props };
  if (/^text-/.test(m[2])) return { variants: m[1], props: ["color"] };
  return null;
};

// A declared property covers another when equal or when it is the shorthand ancestor (padding covers padding-left).
const covers = (declared, target) =>
  declared === target ||
  (target.startsWith(`${declared}-`) && !(declared === "border" && target === "border-radius") && !(declared === "flex" && /^flex-(direction|wrap|flow)$/.test(target)));

// { variants, prop } for an arbitrary-property utility `variants[prop:value]`.
const arbitrary = (token) => {
  const body = token.replace(/!$/, "");
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
  const m = body.slice(start + 1, -1).match(/^([a-z-]+):/);
  if (!m) return null;
  return { variants: body.slice(0, start).replace(/\[&&\]:/g, ""), prop: m[1] };
};

const classStrings = (ast) => {
  const nodes = [];
  let attrId = 0;
  const collect = (node) => {
    if (!node) return;
    switch (node.type) {
      case "StringLiteral":
        nodes.push({ start: node.start + 1, end: node.end - 1, attr: attrId });
        break;
      case "TemplateLiteral":
        node.quasis.forEach((q) => nodes.push({ start: q.start, end: q.end, attr: attrId }));
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
      if (p.node.name.name === "className") {
        attrId++;
        collect(p.node.value);
      }
    },
  });
  return nodes;
};

let dropped = 0;
for (const file of walk("src").filter((f) => f.endsWith(".jsx") && !/__tests__|[\\/]ui[\\/]/.test(f))) {
  const code = fs.readFileSync(file, "utf8");
  if (!code.includes("[")) continue;
  let ast;
  try {
    ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  } catch {
    continue;
  }
  const pieces = classStrings(ast);
  const byAttr = new Map();
  for (const s of pieces) (byAttr.get(s.attr) ?? byAttr.set(s.attr, []).get(s.attr)).push(s);
  const edits = [];
  for (const group of byAttr.values()) {
    const arb = [];
    for (const s of group) {
      for (const t of code.slice(s.start, s.end).split(/\s+/).filter(Boolean)) {
        const a = arbitrary(t);
        if (a) arb.push(a);
      }
    }
    if (!arb.length) continue;
    for (const s of group) {
      const tokens = code.slice(s.start, s.end).split(/(\s+)/);
      let changed = false;
      const out = tokens.map((t) => {
        const p = t.trim() ? plainTailwind(t) : null;
        if (!p) return t;
        const shadowed = arb.some((a) => a.variants === p.variants && p.props.every((pp) => covers(a.prop, pp)));
        if (!shadowed) return t;
        changed = true;
        dropped++;
        return "";
      });
      if (changed) {
        const text = out.join("").replace(/ {2,}/g, " ");
        edits.push({ start: s.start, end: s.end, text });
      }
    }
  }
  if (write && edits.length) {
    let res = code;
    for (const e of edits.sort((a, b) => b.start - a.start)) res = res.slice(0, e.start) + e.text + res.slice(e.end);
    fs.writeFileSync(file, res);
  }
}
console.log(`${write ? "dropped" : "would drop"} ${dropped} shadowed utilities`);
