// Moves simple, single-use class rules from the legacy CSS into Tailwind arbitrary-property utilities.
// A class qualifies when its only appearance in all CSS is a root-level `.name { ... }` rule, every use in
// JS is a plain token inside a className attribute (or cn/clsx call), and it is not referenced by tests.
// Usage: node scripts/css-to-utilities.mjs [--write] [--max-decls 12] [--only file-substring]
import fs from "node:fs";
import path from "node:path";
import postcss from "postcss";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;

const write = process.argv.includes("--write");
const argVal = (k, d) => {
  const i = process.argv.indexOf(k);
  return i > -1 ? process.argv[i + 1] : d;
};
const MAX = Number(argVal("--max-decls", 12));
const ONLY = argVal("--only", "");

const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "node_modules") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};
const all = walk("src");
const cssFiles = all.filter((f) => f.endsWith(".css") && !/styles[\\/]/.test(f));
const isTest = (f) => /__tests__|\.test\./.test(f);
const jsxFiles = all.filter((f) => /\.jsx$/.test(f) && !isTest(f));
const otherJs = all.filter((f) => /\.(js|jsx)$/.test(f) && !jsxFiles.includes(f) && !isTest(f));
const testText = [...walk("e2e"), ...all.filter(isTest)]
  .filter((f) => /\.(js|jsx|mjs)$/.test(f))
  .map((f) => fs.readFileSync(f, "utf8"))
  .join("\n");
const indexHtml = fs.readFileSync("index.html", "utf8");
const tokenRe = (name) => new RegExp(`(?<![\\w-])${name.replace(/-/g, "\\-")}(?![\\w-])`, "g");

// 1. Count every class mention across all CSS (any selector form).
const mentions = {};
const elementProps = new Set();
const baseProp = (p) => p.split("-")[0];
const noteElementRules = (root) =>
  root.walkRules((r) => {
    if (r.parent?.type === "atrule" && /keyframes$/.test(r.parent.name)) return;
    if (r.selectors.some((s) => !/\./.test(s))) r.walkDecls((d) => elementProps.add(baseProp(d.prop)));
  });
for (const f of all.filter((x) => x.endsWith(".css") && /styles/.test(x))) {
  const root0 = postcss.parse(fs.readFileSync(f, "utf8"));
  noteElementRules(root0);
  root0.walkRules((r) => {
    for (const s of r.selectors) for (const m of s.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)) mentions[m[1]] = (mentions[m[1]] || 0) + 9;
  });
}
for (const f of all.filter((x) => x.endsWith(".css") && !cssFiles.includes(x))) {
  postcss.parse(fs.readFileSync(f, "utf8")).walkRules((r) => {
    for (const s of r.selectors) for (const m of s.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)) mentions[m[1]] = (mentions[m[1]] || 0) + 9;
  });
}
const roots = {};
const occ = {};
const PSEUDO = {
  hover: "hover:",
  focus: "focus:",
  "focus-visible": "focus-visible:",
  "focus-within": "focus-within:",
  active: "active:",
  disabled: "disabled:",
  checked: "checked:",
  "first-child": "first:",
  "last-child": "last:",
  placeholder: "placeholder:",
};
const mediaPrefix = (params) => {
  const t = params.trim();
  let m = t.match(/^\(\s*max-width\s*:\s*(\d+px)\s*\)$/);
  if (m) return `max-[${m[1]}]:`;
  m = t.match(/^\(\s*min-width\s*:\s*(\d+px)\s*\)$/);
  if (m) return `min-[${m[1]}]:`;
  if (/[[\]{}'"\\]/.test(t)) return null;
  return `[@media${t.replace(/\s+/g, "_")}]:`;
};
const simpleOccurrence = (sel, rule) => {
  const m = sel.trim().match(/^\.(-?[_a-zA-Z][\w-]*)((?::{1,2}[a-z-]+)*)$/);
  if (!m) return null;
  let prefix = "";
  for (const ps of m[2].split(/:+/).filter(Boolean)) {
    if (!PSEUDO[ps]) return null;
    prefix += PSEUDO[ps];
  }
  const parent = rule.parent;
  if (parent?.type === "atrule") {
    if (parent.name !== "media" || parent.parent?.type !== "root") return null;
    const mp = mediaPrefix(parent.params);
    if (!mp) return null;
    prefix = mp + prefix;
  } else if (parent?.type !== "root") return null;
  return { name: m[1], prefix };
};
for (const f of cssFiles) {
  const root = postcss.parse(fs.readFileSync(f, "utf8"));
  roots[f] = root;
  noteElementRules(root);
  root.walkRules((r) => {
    if (r.parent?.type === "atrule" && /keyframes$/.test(r.parent.name)) return;
    for (const s of r.selectors) {
      for (const m of s.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)) mentions[m[1]] = (mentions[m[1]] || 0) + 1;
      const so = simpleOccurrence(s, r);
      if (so) (occ[so.name] ||= []).push({ file: f, rule: r, selector: s, prefix: so.prefix });
    }
  });
}

const toUtility = (decl) => {
  if (decl.prop.startsWith("--")) return null;
  const v = decl.value.trim();
  if (!v || /["'\\;]|url\(/i.test(v) || /[[\]{}]/.test(v) || decl.prop === "content") return null;
  const bang = decl.important || elementProps.has(baseProp(decl.prop));
  return `[${decl.prop}:${v.replace(/\s+/g, "_")}]${bang ? "!" : ""}`;
};

let eligible = {};
for (const [name, list] of Object.entries(occ)) {
  if (mentions[name] !== list.length) continue;
  if (ONLY && !list.every((o) => o.file.includes(ONLY))) continue;
  const prefixes = list.map((o) => o.prefix);
  if (new Set(prefixes).size !== prefixes.length) continue;
  const entries = [];
  let ok = true;
  let n = 0;
  for (const o of list) {
    const decls = o.rule.nodes.filter((x) => x.type === "decl");
    if (decls.length !== o.rule.nodes.length || decls.length === 0) ok = false;
    n += decls.length;
    for (const d of decls) {
      const u = toUtility(d);
      if (!u) ok = false;
      else entries.push({ prefix: o.prefix, prop: d.prop, util: u });
    }
  }
  if (!ok || n > MAX) continue;
  // Media variants may sort before the base utility; make them important when they override another declaration.
  const isMedia = (pre) => /^(max-\[|min-\[|\[@media)/.test(pre);
  const utils = entries.map((e) => {
    const overrides = isMedia(e.prefix) && entries.some((x) => x !== e && baseProp(x.prop) === baseProp(e.prop));
    return e.prefix + (overrides && !e.util.endsWith("!") ? `${e.util}!` : e.util);
  });
  if (tokenRe(name).test(testText) || tokenRe(name).test(indexHtml)) continue;
  eligible[name] = { occurrences: list, utils };
}

const sources = Object.fromEntries([...jsxFiles, ...otherJs].map((f) => [f, fs.readFileSync(f, "utf8")]));
const cssDefined = new Set(Object.keys(mentions));

// String pieces inside className attributes (literals, template quasis, ternaries, cn/clsx calls).
const classStrings = (ast) => {
  const nodes = [];
  const collect = (node) => {
    if (!node) return;
    switch (node.type) {
      case "StringLiteral":
        nodes.push({ start: node.start + 1, end: node.end - 1, dynamic: false });
        break;
      case "TemplateLiteral":
        node.quasis.forEach((q) => nodes.push({ start: q.start, end: q.end, dynamic: true }));
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

const planEdits = (active) => {
  const edits = {};
  const replaced = {};
  for (const file of jsxFiles) {
    const code = sources[file];
    let ast;
    try {
      ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
    } catch {
      continue;
    }
    for (const s of classStrings(ast)) {
      const text = code.slice(s.start, s.end);
      const tokens = text.split(/(\s+)/);
      const stillLegacy = tokens.some((t) => t.trim() && cssDefined.has(t) && !active[t]);
      let changed = false;
      const out = tokens.map((t, i) => {
        const e = active[t];
        if (!e) return t;
        // first/last token of a template quasi may continue into a ${...} placeholder
        if (s.dynamic && ((i === 0 && !/^\s/.test(text)) || (i === tokens.length - 1 && !/\s$/.test(text)))) return t;
        changed = true;
        replaced[t] = (replaced[t] || 0) + 1;
        const bang = stillLegacy || s.dynamic;
        return e.utils.map((u) => (bang && !u.endsWith("!") ? `${u}!` : u)).join(" ");
      });
      if (changed) (edits[file] ||= []).push({ start: s.start, end: s.end, text: out.join("") });
    }
  }
  return { edits, replaced };
};

// 2. Keep only classes whose every JS occurrence was replaced (otherwise the CSS rule must stay).
const jsCount = {};
for (const name of Object.keys(eligible)) {
  jsCount[name] = Object.values(sources).reduce((n, t) => n + (t.match(tokenRe(name)) || []).length, 0);
}
let { replaced } = planEdits(eligible);
const keep = Object.fromEntries(Object.entries(eligible).filter(([n]) => replaced[n] && replaced[n] === jsCount[n]));
eligible = keep;
const { edits } = planEdits(eligible);

const seenRules = new Set();
let removedLines = 0;
for (const e of Object.values(eligible)) {
  for (const o of e.occurrences) {
    if (seenRules.has(o.rule)) continue;
    seenRules.add(o.rule);
    removedLines += o.rule.source.end.line - o.rule.source.start.line + 1;
  }
}
console.log(`${Object.keys(eligible).length} classes, ~${removedLines} CSS lines, ${Object.keys(edits).length} files`);

if (write) {
  for (const [file, list] of Object.entries(edits)) {
    let out = sources[file];
    for (const e of list.sort((a, b) => b.start - a.start)) out = out.slice(0, e.start) + e.text + out.slice(e.end);
    fs.writeFileSync(file, out);
  }
  for (const f of cssFiles) {
    let touched = false;
    roots[f].walkRules((r) => {
      if (!r.parent) return;
      const keep = r.selectors.filter((sel) => {
        const so = simpleOccurrence(sel, r);
        return !(so && eligible[so.name]);
      });
      if (keep.length === r.selectors.length) return;
      touched = true;
      const parent = r.parent;
      if (keep.length === 0) {
        r.remove();
        if (parent.type === "atrule" && parent.nodes.length === 0) parent.remove();
      } else r.selectors = keep;
    });
    if (touched) fs.writeFileSync(f, roots[f].toString());
  }
}
