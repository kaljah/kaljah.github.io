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
const elementProps = new Set();
const baseProp = (p) => p.split("-")[0];
const noteElementRules = (root) =>
  root.walkRules((r) => {
    if (r.parent?.type === "atrule" && /keyframes$/.test(r.parent.name)) return;
    if (r.selectors.some((s) => !/\./.test(s))) r.walkDecls((d) => elementProps.add(baseProp(d.prop)));
  });
const blocked = new Set();
const pinned = new Set();
const allSelectors = [];
const classesIn = (sel) => [...sel.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)].map((m) => m[1]);
const noteMentions = (sel, lead) => {
  const cls = classesIn(sel);
  const first = sel.trim().match(/^\.(-?[_a-zA-Z][\w-]*)/)?.[1];
  allSelectors.push({ lead: first ?? null, nonLead: cls.filter((c, i) => !(i === 0 && first === c)) });
  cls.forEach((c, i) => {
    if (i === 0 && first === c) lead(c);
    else pinned.add(c);
  });
};
for (const f of all.filter((x) => x.endsWith(".css") && !cssFiles.includes(x))) {
  const root0 = postcss.parse(fs.readFileSync(f, "utf8"));
  noteElementRules(root0);
  root0.walkRules((r) => {
    for (const sel of r.selectors) {
      noteMentions(sel, (c) => blocked.add(c));
      classesIn(sel).forEach((c) => blocked.add(c));
    }
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
  if (/[{}'"]/.test(t)) return null;
  return `[@media${t.startsWith("(") ? "" : "_"}${t.replace(/:\s+/g, ":").replace(/\s+/g, "_")}]:`;
};
const BAD_REST = /[[\]{}'"\,;]|::?(before|after|first-line|first-letter|selection|-webkit|-moz)/;
const simpleOccurrence = (sel, rule) => {
  const m = sel.trim().match(/^\.(-?[_a-zA-Z][\w-]*)(.*)$/s);
  if (!m) return null;
  const rest = m[2];
  const parent = rule.parent;
  let media = "";
  if (parent?.type === "atrule") {
    if (parent.name !== "media" || parent.parent?.type !== "root") return null;
    media = mediaPrefix(parent.params);
    if (!media) return null;
  } else if (parent?.type !== "root") return null;
  if (rest === "") return { name: m[1], prefix: media, generic: false };
  if (BAD_REST.test(rest) || /^[\w-]/.test(rest)) return null;
  const pseudos = rest.match(/^((?::{1,2}[a-z-]+)+)$/);
  if (pseudos) {
    const parts = pseudos[1].split(/:+/).filter(Boolean);
    if (parts.every((ps) => PSEUDO[ps])) return { name: m[1], prefix: media + parts.map((ps) => PSEUDO[ps]).join(""), generic: false };
  }
  const t = rest.trim().replace(/\s*([>+~])\s*/g, "$1").replace(/\s+/g, "_");
  const body = /^\s/.test(rest) && !/^[>+~]/.test(t) ? `&_${t}` : `&${t}`;
  return { name: m[1], prefix: `${media}[${body}]:`, generic: true };
};
const leadTotal = {};
for (const f of cssFiles) {
  const root = postcss.parse(fs.readFileSync(f, "utf8"));
  roots[f] = root;
  noteElementRules(root);
  root.walkRules((r) => {
    if (r.parent?.type === "atrule" && /keyframes$/.test(r.parent.name)) return;
    for (const sel of r.selectors) {
      noteMentions(sel, (c) => {
        leadTotal[c] = (leadTotal[c] || 0) + 1;
        const so = simpleOccurrence(sel, r);
        if (so && so.name === c) (occ[c] ||= []).push({ file: f, rule: r, selector: sel, prefix: so.prefix, generic: so.generic });
      });
    }
  });
}

const toUtility = (decl) => {
  const v = decl.value.trim().replace(/"/g, "'");
  if (!v || /[;]|url\(/i.test(v) || /[[\]{}`]|[$][{]/.test(v) || decl.prop === "content") return null;
  if (v.includes(String.fromCharCode(92))) return null;
  const bang = decl.important || elementProps.has(baseProp(decl.prop));
  return `[${decl.prop}:${v.replace(/\s+/g, "_")}]${bang ? "!" : ""}`;
};

let eligible = {};
for (const [name, list] of Object.entries(occ)) {
  if (leadTotal[name] !== list.length || blocked.has(name)) continue;
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
      else entries.push({ prefix: o.prefix, prop: d.prop, util: u, generic: o.generic });
    }
  }
  if (!ok || n > MAX) continue;
  // Media variants may sort before the base utility; make them important when they override another declaration.
  const isMedia = (pre) => /^(max-\[|min-\[|\[@media)/.test(pre);
  const utils = entries.map((e) => {
    const overrides = isMedia(e.prefix) && entries.some((x) => x !== e && baseProp(x.prop) === baseProp(e.prop));
    return e.prefix + ((overrides || e.generic) && !e.util.endsWith("!") ? `${e.util}!` : e.util);
  });
  if (tokenRe(name).test(testText) || tokenRe(name).test(indexHtml)) pinned.add(name);
  eligible[name] = { occurrences: list, utils, keys: new Set(entries.map((e) => e.prefix + baseProp(e.prop))) };
}

// A class that is a non-leading part of any selector that stays in the CSS keeps its rules there
// (a more specific legacy rule may still depend on the ordering), so drop it and repeat.
for (let changed = true; changed; ) {
  changed = false;
  const remainingNonLead = new Set();
  for (const sel of allSelectors) {
    if (sel.lead && eligible[sel.lead]) continue;
    sel.nonLead.forEach((c) => remainingNonLead.add(c));
  }
  for (const n of Object.keys(eligible)) {
    if (remainingNonLead.has(n)) {
      delete eligible[n];
      changed = true;
    }
  }
}

const sources = Object.fromEntries([...jsxFiles, ...otherJs].map((f) => [f, fs.readFileSync(f, "utf8")]));
const cssDefined = new Set([...Object.keys(leadTotal), ...pinned]);

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
        node.quasis.forEach((q, qi) => nodes.push({ start: q.start, end: q.end, dynamic: true, first: qi === 0, last: qi === node.quasis.length - 1 }));
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
  const conflicts = new Set();
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
      const seenKeys = new Map();
      let changed = false;
      const out = tokens.map((t, i) => {
        const e = active[t];
        if (!e) return t;
        // first/last token of a template quasi may continue into a ${...} placeholder
        if (s.dynamic && ((i === 0 && !s.first && !/^\s/.test(text)) || (i === tokens.length - 1 && !s.last && !/\s$/.test(text)))) return t;
        if (e.utils.some((u) => u.includes("'")) && code[s.start - 1] === "'") return t;
        for (const k of e.keys) {
          if (seenKeys.has(k) && seenKeys.get(k) !== t) {
            conflicts.add(t);
            conflicts.add(seenKeys.get(k));
          }
          seenKeys.set(k, t);
        }
        changed = true;
        replaced[t] = (replaced[t] || 0) + 1;
        const bang = stillLegacy || s.dynamic;
        const utils = e.utils.map((u) => (bang && !u.endsWith("!") ? `${u}!` : u)).join(" ");
        return pinned.has(t) ? `${t} ${utils}` : utils;
      });
      if (changed) (edits[file] ||= []).push({ start: s.start, end: s.end, text: out.join("") });
    }
  }
  return { edits, replaced, conflicts };
};

// 2. Keep only classes whose every JS occurrence was replaced (otherwise the CSS rule must stay).
const jsCount = {};
for (const name of Object.keys(eligible)) {
  jsCount[name] = Object.values(sources).reduce((n, t) => n + (t.match(tokenRe(name)) || []).length, 0);
}
for (let round = 0; round < 20; round++) {
  const { replaced, conflicts } = planEdits(eligible);
  const next = Object.fromEntries(
    Object.entries(eligible).filter(([n]) => replaced[n] && replaced[n] === jsCount[n] && !conflicts.has(n)),
  );
  if (process.argv.includes("--why")) {
    for (const n of Object.keys(eligible)) {
      if (next[n]) continue;
      const lines = eligible[n].occurrences.reduce((a, o) => a + o.rule.source.end.line - o.rule.source.start.line + 1, 0);
      const why = conflicts.has(n) ? "conflict" : replaced[n] ? `partial ${replaced[n]}/${jsCount[n]}` : `none ${jsCount[n]}`;
      console.log(`${lines}\t${n}\t${why}`);
    }
  }
  if (Object.keys(next).length === Object.keys(eligible).length) break;
  eligible = next;
}
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
        return !(so && eligible[so.name] && !blocked.has(so.name));
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
