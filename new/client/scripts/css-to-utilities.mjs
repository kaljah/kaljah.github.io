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
  const pe = rest.match(/^::?(before|after)$/);
  if (pe) return { name: m[1], prefix: `${media}${pe[1]}:`, generic: false };
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
const propsOf = {};
const noteProps = (sel, rule) => {
  const m = sel.trim().match(/^\.(-?[_a-zA-Z][\w-]*)(.*)$/s);
  if (!m || /^[\s>+~]/.test(m[2])) return;
  const set = (propsOf[m[1]] ||= new Set());
  rule.walkDecls((d) => set.add(baseProp(d.prop)));
};
for (const f of all.filter((x) => x.endsWith(".css") && !cssFiles.includes(x))) {
  postcss.parse(fs.readFileSync(f, "utf8")).walkRules((r) => r.selectors.forEach((sel) => noteProps(sel, r)));
}
const leadTotal = {};
for (const f of cssFiles) {
  const root = postcss.parse(fs.readFileSync(f, "utf8"));
  roots[f] = root;
  noteElementRules(root);
  root.walkRules((r) => {
    if (r.parent?.type === "atrule" && /keyframes$/.test(r.parent.name)) return;
    for (const sel of r.selectors) {
      noteProps(sel, r);
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
  const quotedContent = decl.prop === "content" && v.length >= 2 && v.startsWith("'") && v.endsWith("'") && !v.slice(1, -1).includes("'");
  if (!v || /[;]|url\(/i.test(v) || /[[\]{}`]|[$][{]/.test(v) || (decl.prop === "content" && !quotedContent)) return null;
  if (v.includes(String.fromCharCode(92))) return null;
  return `[${decl.prop}:${v.replace(/\s+/g, "_")}]`;
};

let eligible = {};
const WHY = {};
const rej = (reason, list) => {
  if (!process.argv.includes("--why2")) return;
  const L = list.reduce((a, o) => a + o.rule.source.end.line - o.rule.source.start.line + 1, 0);
  WHY[reason] = (WHY[reason] || 0) + L;
};
for (const [name, list] of Object.entries(occ)) {
  if (blocked.has(name)) {
    rej("blocked-by-styles-css", list);
    continue;
  }
  if (leadTotal[name] !== list.length) {
    rej("complex-lead-selector", list);
    continue;
  }
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
      else {
        const bp = baseProp(d.prop);
        entries.push({ prefix: o.prefix, prop: d.prop, bp, base: u, important: Boolean(d.important), elementBang: elementProps.has(bp), generic: o.generic, selector: o.selector });
      }
    }
  }
  if (!ok || n > MAX) {
    rej(ok ? "too-many-decls" : "bad-decl", list);
    continue;
  }
  // Media variants may sort before the base utility; they need to be important when they override another declaration.
  const isMedia = (pre) => /^(max-\[|min-\[|\[@media)/.test(pre);
  entries.forEach((e, i) => {
    e.media = isMedia(e.prefix) && entries.some((x) => x !== e && x.bp === e.bp);
    // Two state variants (`.a.x .t` and `.a.y .t`) can match together; the later rule won by source order, so it
    // gets one extra class of specificity per earlier overlapping variant.
    const rank = e.generic ? entries.slice(0, i).filter((x) => x.generic && x.prefix !== e.prefix && x.bp === e.bp).length : 0;
    e.pre = "[&&]:".repeat(rank) + e.prefix;
  });
  if (tokenRe(name).test(testText) || tokenRe(name).test(indexHtml)) pinned.add(name);
  eligible[name] = { occurrences: list, entries, keys: new Set(entries.map((e) => e.prefix + e.bp)), props: new Set(entries.map((e) => e.bp)) };
}

// A class that is a non-leading part of any selector that stays in the CSS keeps its rules there
// (a more specific legacy rule may still depend on the ordering), so drop it and repeat.
const settle = () => {
  for (let changed = true; changed; ) {
    changed = false;
    const remainingNonLead = new Set();
    for (const sel of allSelectors) {
      if (sel.lead && eligible[sel.lead]) continue;
      sel.nonLead.forEach((c) => remainingNonLead.add(c));
    }
    for (const n of Object.keys(eligible)) {
      if (remainingNonLead.has(n)) {
        rej("nonlead-in-remaining-rule", eligible[n].occurrences);
        delete eligible[n];
        changed = true;
      }
    }
  }
};
settle();

const sources = Object.fromEntries([...jsxFiles, ...otherJs].map((f) => [f, fs.readFileSync(f, "utf8")]));

// Route chunks only load the CSS their modules import. Moving a rule into a utility makes it global, so a class is
// converted only when its CSS file is already loaded wherever the class is used.
const resolveImport = (from, spec) => {
  if (!spec.startsWith(".")) return null;
  const base = path.join(path.dirname(from), spec);
  for (const c of [base, `${base}.jsx`, `${base}.js`, `${base}.css`, path.join(base, "index.jsx"), path.join(base, "index.js")]) {
    if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
  }
  return null;
};
const staticDeps = {};
const dynamicRoots = new Set();
for (const f of all.filter((x) => /\.(jsx?|mjs)$/.test(x))) {
  const code = fs.readFileSync(f, "utf8");
  const deps = new Set();
  for (const m of code.matchAll(/(?:from|import)\s*["']([^"']+)["']/g)) {
    const r = resolveImport(f, m[1]);
    if (r) deps.add(r);
  }
  for (const m of code.matchAll(/import\(\s*["']([^"']+)["']\s*\)/g)) {
    const r = resolveImport(f, m[1]);
    if (r) dynamicRoots.add(r);
  }
  staticDeps[f] = deps;
}
const closure = (root) => {
  const seen = new Set();
  const stack = [root];
  while (stack.length) {
    const f = stack.pop();
    if (seen.has(f)) continue;
    seen.add(f);
    for (const d of staticDeps[f] ?? []) stack.push(d);
  }
  return seen;
};
const shellRoot = path.join("src", "main.jsx");
const shellClosure = closure(shellRoot);
const rootClosures = new Map([[shellRoot, shellClosure]]);
for (const r of dynamicRoots) if (!rootClosures.has(r)) rootClosures.set(r, closure(r));
const cssAvailable = (cssFile, jsxFile) => {
  for (const [root, cl] of rootClosures) {
    if (!cl.has(jsxFile)) continue;
    if (cl.has(cssFile) || shellClosure.has(cssFile)) continue;
    return false;
  }
  return true;
};
for (const [name, e] of Object.entries(eligible)) {
  const cssFilesOf = new Set(e.occurrences.map((o) => path.normalize(o.file)));
  const re = tokenRe(name);
  for (const [jf, text] of Object.entries(sources)) {
    if (!re.test(text)) continue;
    re.lastIndex = 0;
    for (const cf of cssFilesOf) {
      if (!cssAvailable(path.normalize(cf), path.normalize(jf))) {
        rej("css-not-loaded-where-used", eligible[name].occurrences);
        delete eligible[name];
        break;
      }
    }
    if (!eligible[name]) break;
  }
}
const cssDefined = new Set([...Object.keys(leadTotal), ...pinned]);

// Base CSS properties set by the element's inline style (a Set), or "all" when they cannot be known statically.
const inlineStyleProps = (opening) => {
  const attr = opening?.attributes?.find((a) => a.type === "JSXAttribute" && a.name.name === "style");
  if (!attr) return new Set();
  const ex = attr.value?.expression;
  if (!ex || ex.type !== "ObjectExpression") return "all";
  const set = new Set();
  for (const prop of ex.properties) {
    if (prop.type !== "ObjectProperty" || prop.computed) return "all";
    const key = prop.key.name || prop.key.value;
    set.add(baseProp(key.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase())));
  }
  return set;
};

// String pieces inside className attributes (literals, template quasis, ternaries, cn/clsx calls).
const classStrings = (ast) => {
  const nodes = [];
  const unknown = new Set();
  let attrId = 0;
  const collect = (node) => {
    if (!node) return;
    switch (node.type) {
      case "StringLiteral":
        nodes.push({ start: node.start + 1, end: node.end - 1, dynamic: false, attr: attrId });
        break;
      case "TemplateLiteral":
        node.quasis.forEach((q, qi) => nodes.push({ start: q.start, end: q.end, dynamic: true, attr: attrId, first: qi === 0, last: qi === node.quasis.length - 1 }));
        // `prefix-${x}` only produces classes under that prefix (collected separately); a standalone `${x}` is unknown
        node.expressions.forEach((ex, i) => {
          if (!/\S$/.test(node.quasis[i].value.raw)) collect(ex);
        });
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
        else unknown.add(attrId);
        break;
      case "NullLiteral":
      case "BooleanLiteral":
      case "NumericLiteral":
        break;
      default:
        unknown.add(attrId);
    }
  };
  traverse(ast, {
    JSXAttribute(p) {
      if (p.node.name.name === "className") {
        attrId++;
        const before = nodes.length;
        collect(p.node.value);
        const inline = inlineStyleProps(p.parent);
        for (let i = before; i < nodes.length; i++) {
          nodes[i].inline = inline;
          nodes[i].tag = p.parent.name?.name;
        }
      }
    },
  });
  for (const n of nodes) n.unknown = unknown.has(n.attr);
  return nodes;
};


// Base CSS properties a plain Tailwind class (or an existing arbitrary-property class) sets, to catch ordering clashes.
const twProps = (token) => {
  let t = token.replace(/!$/, "");
  t = t.replace(/^(?:[a-z-]+:|\[[^\]]*\]:)+/, "").replace(/^!/, "");
  const arb = t.match(/^\[([a-z-]+):/);
  if (arb) return new Set([baseProp(arb[1])]);
  if (/^text-\[length:/.test(t)) return new Set(["font"]);
  const out = new Set();
  const rules = [
    [/^-?m[trblxyse]?-/, "margin"],
    [/^p[trblxyse]?-/, "padding"],
    [/^gap(-[xy])?-/, "gap"],
    [/^(w|min-w|max-w)-/, "width"],
    [/^(min-w|max-w)-/, "min"],
    [/^(min-w|max-w)-/, "max"],
    [/^(h|min-h|max-h)-/, "height"],
    [/^size-/, "width"],
    [/^size-/, "height"],
    [/^text-(xs|sm|base|md|lg|xl|[2-9]xl)$/, "font"],
    [/^text-(left|center|right|justify|start|end)$/, "text"],
    [/^font-/, "font"],
    [/^leading-/, "line"],
    [/^tracking-/, "letter"],
    [/^bg-/, "background"],
    [/^border/, "border"],
    [/^rounded/, "border"],
    [/^(flex|inline-flex)$/, "display"],
    [/^(grid|inline-grid|block|inline-block|inline|hidden|contents|table)$/, "display"],
    [/^flex-/, "flex"],
    [/^grid-/, "grid"],
    [/^(grow|shrink)/, "flex"],
    [/^items-/, "align"],
    [/^self-/, "align"],
    [/^justify-/, "justify"],
    [/^shadow/, "box"],
    [/^opacity-/, "opacity"],
    [/^overflow-/, "overflow"],
    [/^truncate$/, "overflow"],
    [/^(relative|absolute|fixed|sticky)$/, "position"],
    [/^(top|left|right|bottom|inset)-/, "top"],
    [/^z-/, "z"],
    [/^cursor-/, "cursor"],
    [/^(transition|duration|ease)/, "transition"],
    [/^whitespace-/, "white"],
    [/^(uppercase|lowercase|capitalize|underline|no-underline)$/, "text"],
  ];
  for (const [re, prop] of rules) if (re.test(t)) out.add(prop);
  if (/^text-/.test(t) && !out.size) out.add("color");
  return out;
};
const cssClassList = Object.keys(propsOf);
const conflictWhy = {};
const addConflict = (conflicts, t, why) => {
  conflicts.add(t);
  (conflictWhy[t] ||= new Set()).add(why);
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
    const strings = classStrings(ast);
    // Group the pieces of one className attribute: classes in any piece can meet on the same element.
    const groups = new Map();
    for (const s of strings) {
      const g = groups.get(s.attr) ?? { tokens: new Set(), prefixes: new Set(), pieces: [], inline: s.inline, unknown: s.unknown, tag: s.tag };
      const text = code.slice(s.start, s.end);
      text.split(/\s+/).filter(Boolean).forEach((t) => g.tokens.add(t));
      for (const m of text.matchAll(/([\w-]+-)[$][{]/g)) g.prefixes.add(m[1]);
      g.pieces.push(s);
      groups.set(s.attr, g);
    }
    for (const g of groups.values()) {
      // Classes that stay in the CSS may still override a converted class by source order (same specificity).
      const others = new Set([...g.tokens].filter((t) => cssDefined.has(t) && !active[t]));
      for (const pre of g.prefixes) for (const c of cssClassList) if (c.startsWith(pre) && !active[c]) others.add(c);
      const cssOtherProps = new Set();
      for (const o of others) propsOf[o]?.forEach((pp) => cssOtherProps.add(pp));
      const nativeNormal = new Set();
      const nativeImportant = new Set();
      for (const t of g.tokens) {
        if (active[t] || cssDefined.has(t)) continue;
        const imp = t.endsWith("!") || t.startsWith("!");
        twProps(t).forEach((pp) => (imp ? nativeImportant : nativeNormal).add(pp));
      }
      const seenKeys = new Map();
      const rendered = new Map();
      for (const t of g.tokens) {
        const e = active[t];
        if (!e) continue;
        if (g.unknown) addConflict(conflicts, t, "unknown-dynamic-classes");
        if (typeof g.tag === "string" && /^[A-Z]/.test(g.tag)) addConflict(conflicts, t, "component-tag");
        // One decision per property: when any rule of the class for it must be important, all of them are,
        // otherwise a state variant (`.active`) could not override its own base declaration.
        const need = {};
        const forbid = {};
        for (const en of e.entries) {
          const n = en.generic
            ? en.fixedBang
            : en.important || en.elementBang || en.media || cssOtherProps.has(en.bp) || nativeNormal.has(en.bp);
          need[en.bp] = need[en.bp] || n;
          if (!en.generic) forbid[en.bp] = nativeImportant.has(en.bp) || g.inline === "all" || Boolean(g.inline?.has(en.bp));
        }
        const parts = [];
        for (const en of e.entries) {
          if (need[en.bp] && forbid[en.bp]) addConflict(conflicts, t, "needs-important-but-blocked");
          parts.push(en.pre + en.base + (need[en.bp] ? "!" : ""));
        }
        rendered.set(t, parts.join(" "));
      }
      for (const s of g.pieces) {
        const text = code.slice(s.start, s.end);
        const tokens = text.split(/(\s+)/);
        let changed = false;
        const out = tokens.map((t, i) => {
          const e = active[t];
          if (!e) return t;
          // first/last token of a template quasi may continue into a ${...} placeholder
          if (s.dynamic && ((i === 0 && !s.first && !/^\s/.test(text)) || (i === tokens.length - 1 && !s.last && !/\s$/.test(text)))) return t;
          if (rendered.get(t).includes("'") && code[s.start - 1] === "'") return t;
          for (const k of e.keys) {
            if (seenKeys.has(k) && seenKeys.get(k) !== t) {
              addConflict(conflicts, t, "two-classes-same-prop");
              addConflict(conflicts, seenKeys.get(k), "two-classes-same-prop");
            }
            seenKeys.set(k, t);
          }
          changed = true;
          replaced[t] = (replaced[t] || 0) + 1;
          return pinned.has(t) ? `${t} ${rendered.get(t)}` : rendered.get(t);
        });
        if (changed) (edits[file] ||= []).push({ start: s.start, end: s.end, text: out.join("") });
      }
    }
  }
  return { edits, replaced, conflicts };
};

// 2. Keep only classes whose every JS occurrence was replaced (otherwise the CSS rule must stay).
// A descendant variant (`[&_.child]:`) has higher specificity than the child's own utilities, so it would beat an
// `!important` utility the child carries for the same property (e.g. from a converted inline style). Skip those.
// Base props of an inline style expression (object, or conditionals of objects); "*" when unknown.
const styleKeys = (ex) => {
  const out = new Set();
  const visit = (n) => {
    if (!n) return;
    if (n.type === "ObjectExpression") {
      for (const prop of n.properties) {
        if (prop.type !== "ObjectProperty" || prop.computed) out.add("*");
        else out.add(baseProp((prop.key.name || prop.key.value).replace(/[A-Z]/g, (c) => "-" + c.toLowerCase())));
      }
    } else if (n.type === "ConditionalExpression") {
      visit(n.consequent);
      visit(n.alternate);
    } else if (n.type === "LogicalExpression") {
      visit(n.right);
    } else out.add("*");
  };
  visit(ex);
  return out;
};
const impByFile = {};
for (const file of jsxFiles) {
  let ast;
  try {
    ast = parse(sources[file], { sourceType: "module", plugins: ["jsx"] });
  } catch {
    continue;
  }
  const groups = new Map();
  for (const s of classStrings(ast)) {
    const g = groups.get(s.attr) ?? { tokens: new Set(), tag: s.tag };
    sources[file].slice(s.start, s.end).split(/\s+/).filter(Boolean).forEach((t) => g.tokens.add(t));
    groups.set(s.attr, g);
  }
  const rec = (impByFile[file] = { cls: {}, tag: {} });
  traverse(ast, {
    JSXOpeningElement(p) {
      const attrs = p.node.attributes;
      const st = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "style");
      if (!st) return;
      const keys = st.value?.expression ? styleKeys(st.value.expression) : new Set();
      const tag = p.node.name.name;
      if (typeof tag === "string" && /^[a-z]/.test(tag)) (rec.tag[tag] ||= new Set()), keys.forEach((k) => rec.tag[tag].add(k));
      const cn = attrs.find((a) => a.type === "JSXAttribute" && a.name.name === "className");
      if (cn?.value?.type === "StringLiteral") {
        for (const t of cn.value.value.split(/\s+/).filter(Boolean)) (rec.cls[t] ||= new Set()), keys.forEach((k) => rec.cls[t].add(k));
      }
    },
  });
  for (const { tokens, tag } of groups.values()) {
    const imp = new Set();
    for (const t of tokens) if (t.endsWith("!") || t.startsWith("!")) twProps(t).forEach((pp) => imp.add(pp));
    if (!imp.size) continue;
    if (typeof tag === "string" && /^[a-z]/.test(tag)) {
      (rec.tag[tag] ||= new Set()), imp.forEach((pp) => rec.tag[tag].add(pp));
    }
    for (const t of tokens) (rec.cls[t] ||= new Set()), imp.forEach((pp) => rec.cls[t].add(pp));
  }
}
// JSX files whose elements can sit below a file that uses the class: the file and what it imports (two levels).
const nearby = (file) => {
  const out = new Set([file]);
  let frontier = [file];
  for (let depth = 0; depth < 2; depth++) {
    const next = [];
    for (const f of frontier) for (const d of staticDeps[f] ?? []) if (!out.has(d)) (out.add(d), next.push(d));
    frontier = next;
  }
  return out;
};
for (const [name, e] of Object.entries(eligible)) {
  const generic = e.entries.filter((en) => en.generic);
  if (!generic.length) continue;
  const re = tokenRe(name);
  const users = Object.entries(sources)
    .filter(([f, t]) => jsxFiles.includes(f) && (re.lastIndex = 0, re.test(t)))
    .map(([f]) => f);
  const scope = new Set(users.flatMap((f) => [...nearby(f)]));
  let dead = false;
  for (const en of generic) {
    const tail = en.selector.trim().replace(/^\.-?[_a-zA-Z][\w-]*/, "");
    const tags = [...tail.matchAll(/(?:^|[\s>+~])([a-z][a-z0-9]*)/g)].map((m) => m[1]);
    const classes = classesIn(en.selector).slice(1);
    // A descendant rule must be important only when a legacy rule (or a child utility) could otherwise override it;
    // it must not be important when the child carries its own important utility for the property.
    const legacy =
      classes.some((c) => propsOf[c]?.has(en.bp)) || (tags.length > 0 && elementProps.has(en.bp));
    const need = en.important || en.media || legacy;
    let forbid = false;
    for (const f of scope) {
      const rec = impByFile[f];
      if (!rec) continue;
      if (classes.some((c) => rec.cls[c]?.has(en.bp) || rec.cls[c]?.has("*"))) forbid = true;
      if (tags.some((tg) => rec.tag[tg]?.has(en.bp) || rec.tag[tg]?.has("*"))) forbid = true;
    }
    if (need && forbid) dead = true;
    en.fixedBang = need;
  }
  if (dead) {
    rej("descendant-important-clash", e.occurrences);
    delete eligible[name];
  }
}
settle();
const jsCount = {};
for (const name of Object.keys(eligible)) {
  jsCount[name] = Object.values(sources).reduce((n, t) => n + (t.match(tokenRe(name)) || []).length, 0);
}
for (let round = 0; round < 20; round++) {
  const { replaced, conflicts } = planEdits(eligible);
  const next = Object.fromEntries(
    Object.entries(eligible).filter(([n]) => replaced[n] && replaced[n] === jsCount[n] && !conflicts.has(n)),
  );
  if (process.argv.includes("--why") || process.argv.includes("--why2")) {
    for (const n of Object.keys(eligible)) {
      if (next[n]) continue;
      rej(conflicts.has(n) ? "conflict" : replaced[n] ? "partial-js-use" : "no-js-token", eligible[n].occurrences);
      const lines = eligible[n].occurrences.reduce((a, o) => a + o.rule.source.end.line - o.rule.source.start.line + 1, 0);
      const why = conflicts.has(n) ? "conflict" : replaced[n] ? `partial ${replaced[n]}/${jsCount[n]}` : `none ${jsCount[n]}`;
      console.log(`${lines}\t${n}\t${why}`);
    }
  }
  if (Object.keys(next).length === Object.keys(eligible).length) break;
  eligible = next;
  settle();
}
const { edits } = planEdits(eligible);

if (process.argv.includes("--why2")) {
  console.log(WHY);
  const byReason = {};
  for (const [n, set] of Object.entries(conflictWhy)) for (const w of set) byReason[w] = (byReason[w] || 0) + 1;
  console.log(byReason);
}
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
