// Converts fully static, simple inline style objects into Tailwind utility classes (with ! so they keep
// inline-style precedence over legacy CSS). Usage: node scripts/inline-to-tailwind.mjs [--write]
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const write = process.argv.includes("--write");

const len = (v) =>
  /^-?\d*\.?\d+(px|rem|em|%)$/.test(String(v)) ? String(v) : typeof v === "number" ? `${v}px` : null;
const spacing = (prefix) => (v) => {
  const l = len(v);
  return l ? [`${prefix}-[${l}]!`] : null;
};
const lookup = (table) => (v) => (table[v] ? [table[v]] : null);

const MAP = {
  display: lookup({ flex: "flex!", grid: "grid!", block: "block!", "inline-flex": "inline-flex!", "inline-block": "inline-block!", none: "hidden!" }),
  flexDirection: lookup({ column: "flex-col!", row: "flex-row!" }),
  alignItems: lookup({ center: "items-center!", "flex-start": "items-start!", "flex-end": "items-end!", baseline: "items-baseline!", stretch: "items-stretch!" }),
  justifyContent: lookup({ center: "justify-center!", "space-between": "justify-between!", "flex-end": "justify-end!", "flex-start": "justify-start!" }),
  flexWrap: lookup({ wrap: "flex-wrap!", nowrap: "flex-nowrap!" }),
  flex: (v) => (v === 1 || v === "1" ? ["flex-1!"] : null),
  flexShrink: (v) => (v === 0 ? ["shrink-0!"] : null),
  gap: spacing("gap"),
  marginTop: spacing("mt"),
  marginBottom: spacing("mb"),
  marginLeft: spacing("ml"),
  marginRight: spacing("mr"),
  paddingTop: spacing("pt"),
  paddingBottom: spacing("pb"),
  paddingLeft: spacing("pl"),
  paddingRight: spacing("pr"),
  width: (v) => (v === "100%" ? ["w-full!"] : len(v) ? [`w-[${len(v)}]!`] : null),
  height: (v) => (v === "100%" ? ["h-full!"] : len(v) ? [`h-[${len(v)}]!`] : null),
  minWidth: (v) => (v === 0 || v === "0" ? ["min-w-0!"] : len(v) ? [`min-w-[${len(v)}]!`] : null),
  textAlign: lookup({ center: "text-center!", right: "text-right!", left: "text-left!" }),
  fontWeight: lookup({ 400: "font-normal!", 500: "font-medium!", 600: "font-semibold!", 700: "font-bold!" }),
  cursor: (v) => (["pointer", "default", "not-allowed"].includes(v) ? [`cursor-${v}!`] : null),
  position: (v) => (v === "relative" ? ["relative!"] : null),
  whiteSpace: (v) => (v === "nowrap" ? ["whitespace-nowrap!"] : null),
  overflow: (v) => (["hidden", "auto"].includes(v) ? [`overflow-${v}!`] : null),
  textTransform: (v) => (v === "uppercase" ? ["uppercase!"] : null),
};


const safe = (v) => (typeof v === "string" && /^[A-Za-z0-9#%.,()\-\s/]+$/.test(v) ? v.trim().replace(/\s+/g, "_") : null);
const colorish = (v) => typeof v === "string" && /^(#[0-9a-fA-F]{3,8}|var\(--[\w-]+(,\s*[^)]+)?\)|rgba?\([^)]+\)|white|black|transparent|inherit|currentColor)$/.test(v.trim());
const multi = (prefix) => (v) => { const x = safe(typeof v === "number" ? `${v}px` : v); return x ? [`${prefix}-[${x}]!`] : null; };
Object.assign(MAP, {
  color: (v) => (colorish(v) ? [`text-[color:${safe(v)}]!`] : null),
  background: (v) => (colorish(v) ? [`bg-[color:${safe(v)}]!`] : null),
  fontSize: (v) => { const l = len(v); return l && /rem|px|em/.test(l) ? [`text-[length:${l}]!`] : null; },
  padding: multi("p"),
  margin: multi("m"),
  borderRadius: (v) => { const x = safe(typeof v === "number" ? `${v}px` : v); return x && !/%/.test(x) ? [`rounded-[${x}]!`] : null; },
  opacity: (v) => (typeof v === "number" || /^[01]?\.?\d+$/.test(String(v)) ? [`opacity-[${v}]!`] : null),
  lineHeight: (v) => (/^\d*\.?\d+(rem|px|em)?$/.test(String(v)) ? [`leading-[${v}]!`] : null),
  fontFamily: (v) => (v === "monospace" ? ["font-mono!"] : null),
  minHeight: (v) => { const l = len(v); return l ? [`min-h-[${l}]!`] : null; },
  maxWidth: (v) => { const l = len(v); return l ? [`max-w-[${l}]!`] : null; },
});

const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "__tests__" || n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};

let converted = 0;
let seen = 0;
const files = walk("src").filter((f) => f.endsWith(".jsx") && !/[\\/](ui|app|dev)[\\/]/.test(f));
for (const file of files) {
  const code = fs.readFileSync(file, "utf8");
  if (!code.includes("style={{")) continue;
  const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
  const edits = [];
  traverse(ast, {
    JSXOpeningElement(p) {
      const attrs = p.node.attributes;
      const style = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "style");
      if (!style) return;
      seen++;
      const ex = style.value?.expression;
      if (!ex || ex.type !== "ObjectExpression" || ex.properties.length === 0) return;
      const classes = [];
      for (const prop of ex.properties) {
        if (prop.type !== "ObjectProperty" || prop.computed) return;
        const key = prop.key.name || prop.key.value;
        if (prop.value.type !== "StringLiteral" && prop.value.type !== "NumericLiteral") return;
        const m = MAP[key];
        const cls = m && m(prop.value.value);
        if (!cls) return;
        classes.push(...cls);
      }
      const cn = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "className");
      if (cn && cn.value && cn.value.type !== "StringLiteral") return;
      if (attrs.some((a) => a.type === "JSXSpreadAttribute")) return;
      const add = classes.join(" ");
      if (cn) {
        edits.push({ start: cn.value.start, end: cn.value.end, text: `"${cn.value.value} ${add}"` });
        edits.push({ start: style.start - 1, end: style.end, text: "" });
      } else {
        edits.push({ start: style.start, end: style.end, text: `className="${add}"` });
      }
      converted++;
    },
  });
  if (write && edits.length) {
    let out = code;
    for (const e of edits.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
    fs.writeFileSync(file, out);
  }
}
console.log(`${write ? "converted" : "convertible"} ${converted} of ${seen} inline styles`);
