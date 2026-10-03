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
const baseProp = (p) => (p === "box-sizing" || p === "outline-offset" ? p : p.split("-")[0]);
const elementPropsByTag = {};
// Element-only selectors (no class) are overridden by a plain class rule today; remember which tags they set what for.
const noteElementRules = (root) =>
  root.walkRules((r) => {
    if (r.parent?.type === "atrule" && /keyframes$/.test(r.parent.name)) return;
    for (const sel of r.selectors) {
      if (/[.]/.test(sel)) continue;
      const m = sel.trim().match(/([a-z][a-z0-9]*|[*])(?:[:[#][^ >+~]*)*$/);
      const tags = m ? [m[1]] : ["*"];
      r.walkDecls((d) => {
        if (d.important) return; // an important element rule already beats a plain class rule
        elementProps.add(baseProp(d.prop));
        for (const tg of tags) (elementPropsByTag[tg] ||= new Set()).add(baseProp(d.prop));
      });
    }
  });
const elementSets = (tag) => [elementPropsByTag["*"], typeof tag === "string" ? elementPropsByTag[tag] : null].filter(Boolean);
if (process.argv.includes("--dbg3")) process.on("exit", () => console.log(Object.fromEntries(Object.entries(elementPropsByTag).map(([k, v]) => [k, [...v]]))));
const elementSets2 = (tag) => (typeof tag === "string" && /^[A-Z]/.test(tag) ? [] : elementSets(tag));
const blocked = new Set();
const pinned = new Set();
const allSelectors = [];
const classesIn = (sel) => [...sel.matchAll(/\.(-?[_a-zA-Z][\w-]*)/g)].map((m) => m[1]);
// Specificity of a selector as [ids, classes/attrs/pseudo-classes, tags/pseudo-elements].
const specOf = (selector) => {
  let a = 0;
  let b = 0;
  let c = 0;
  let t = selector.replace(/:where\([^)]*\)/g, "").replace(/:(not|is|has)\(([^)]*)\)/g, " $2 ");
  t = t.replace(/::[\w-]+/g, () => (c++, ""));
  t = t.replace(/#[\w-]+/g, () => (a++, ""));
  t = t.replace(/\[[^\]]*\]/g, () => (b++, ""));
  t = t.replace(/\.[\w-]+/g, () => (b++, ""));
  t = t.replace(/:[\w-]+(\([^)]*\))?/g, () => (b++, ""));
  c += (t.match(/(?:^|[\s>+~])[a-zA-Z][\w-]*/g) || []).length;
  return [a, b, c];
};
const cmpSpec = (x, y) => x[0] - y[0] || x[1] - y[1] || x[2] - y[2];
const skippedMedia = (rule) => {
  for (let n = rule?.parent; n; n = n.parent) {
    if (n.type === "atrule" && n.name === "media" && /print|prefers-reduced-motion/.test(n.params)) return true;
  }
  return false;
};
const noteMentions = (sel, lead, rule, file) => {
  const imp = new Set();
  const props = new Set();
  rule?.walkDecls((d) => (d.important ? imp : props).add(baseProp(d.prop)));
  const cls = classesIn(sel);
  const first = sel.trim().match(/^\.(-?[_a-zA-Z][\w-]*)/)?.[1];
  const compound = sel.trim().match(/([^\s>+~]+)$/)?.[1] ?? "";
  const subj = { tag: compound.match(/^[a-z][a-z0-9]*/)?.[0] ?? null, classes: [...compound.matchAll(/[.](-?[_a-zA-Z][\w-]*)/g)].map((m) => m[1]) };
  allSelectors.push({
    lead: first ?? null,
    nonLead: cls.filter((c, i) => !(i === 0 && first === c)),
    imp,
    props,
    subj,
    selector: sel,
    spec: specOf(sel),
    simple: !/[\s>+~]/.test(sel.trim().replace(/\([^)]*\)/g, "")),
    file,
    line: rule?.source?.start?.line ?? 0,
    skip: skippedMedia(rule),
  });
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
      noteMentions(sel, (c) => blocked.add(c), r, f);
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
const BAD_REST = /[[\]{}'"\,;]/;
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
const importantPropsOf = {};
const noteProps = (sel, rule) => {
  const m = sel.trim().match(/^\.(-?[_a-zA-Z][\w-]*)(.*)$/s);
  if (!m || /^[\s>+~]/.test(m[2])) return;
  const set = (propsOf[m[1]] ||= new Set());
  const imp = (importantPropsOf[m[1]] ||= new Set());
  rule.walkDecls((d) => {
    if (d.important) imp.add(baseProp(d.prop));
    else set.add(baseProp(d.prop));
  });
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
      }, r, f);
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
        entries.push({ prefix: o.prefix, prop: d.prop, bp, base: u, important: Boolean(d.important), generic: o.generic, selector: o.selector, file: o.file, line: o.rule.source.start.line });
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
let coOccur = null; // class -> classes seen together on one element (filled once the JSX has been scanned)
const settle = () => {};
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

// CSS properties (kebab-case) set by the element's inline style (a Set), or "all" when they cannot be known statically.
const inlineStyleProps = (opening) => {
  const attr = opening?.attributes?.find((a) => a.type === "JSXAttribute" && a.name.name === "style");
  if (!attr) return new Set();
  const ex = attr.value?.expression;
  if (!ex || ex.type !== "ObjectExpression") return "all";
  const set = new Set();
  for (const prop of ex.properties) {
    if (prop.type !== "ObjectProperty" || prop.computed) return "all";
    const key = prop.key.name || prop.key.value;
    set.add(key.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()));
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
// Exact CSS properties a plain, variant-free Tailwind class (or `[prop:value]` class) sets; null when unknown.
const EXACT_RULES = [
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
  [/^gap-x-/, ["column-gap"]],
  [/^gap-y-/, ["row-gap"]],
  [/^gap-/, ["gap"]],
  [/^w-/, ["width"]],
  [/^min-w-/, ["min-width"]],
  [/^max-w-/, ["max-width"]],
  [/^h-/, ["height"]],
  [/^min-h-/, ["min-height"]],
  [/^max-h-/, ["max-height"]],
  [/^text-\[length:/, ["font-size"]],
  [/^text-(xs|sm|base|md|lg|xl|[2-9]xl)$/, ["font-size"]],
  [/^text-(left|center|right|justify|start|end)$/, ["text-align"]],
  [/^text-\[color:/, ["color"]],
  [/^font-(thin|light|normal|medium|semibold|bold|extrabold|black)$/, ["font-weight"]],
  [/^font-(mono|sans|serif)$/, ["font-family"]],
  [/^leading-/, ["line-height"]],
  [/^tracking-/, ["letter-spacing"]],
  [/^bg-\[color:/, ["background-color"]],
  [/^rounded/, ["border-radius"]],
  [/^(flex|inline-flex)$/, ["display"]],
  [/^(grid|inline-grid|block|inline-block|inline|hidden|contents|table)$/, ["display"]],
  [/^flex-(col|row)/, ["flex-direction"]],
  [/^flex-(wrap|nowrap)/, ["flex-wrap"]],
  [/^items-/, ["align-items"]],
  [/^justify-/, ["justify-content"]],
  [/^opacity-/, ["opacity"]],
  [/^(relative|absolute|fixed|sticky)$/, ["position"]],
  [/^cursor-/, ["cursor"]],
  [/^whitespace-/, ["white-space"]],
];
const exactProps = (token) => {
  const body = token.replace(/!$/, "");
  const arb = body.match(/^\[([a-z-]+):/);
  if (arb) return [arb[1]];
  for (const [re, props] of EXACT_RULES) if (re.test(body)) return props;
  return null;
};
// A declared property covers another when equal or when it is the shorthand ancestor (padding covers padding-left).
const covers = (declared, target) =>
  declared === target ||
  (target.startsWith(`${declared}-`) && !(declared === "border" && target === "border-radius") && !(declared === "flex" && /^flex-(direction|wrap|flow)$/.test(target)));
const hasVariant = (token) => /^(?:[a-z0-9-]+:|\[[^\]]*\]:)/.test(token.replace(/^!/, ""));

// Could the unlayered rule (selector info) reach an element living in `file` (or, for class-level checks, in any of `files`)?
// A rule scoped by a lead class only matches inside elements carrying that class, which come from the files that use it.
const usersCache = {};
const usersOf = (cls) =>
  (usersCache[cls] ||= Object.entries(sources)
    .filter(([f, t]) => jsxFiles.includes(f) && (tokenRe(cls).lastIndex = 0, tokenRe(cls).test(t)))
    .map(([f]) => f));
const nearbyCache = {};
const nearbyOf = (f) => (nearbyCache[f] ||= nearby(f));
const ruleReaches = (sel, files) => {
  if (!sel.lead) return true;
  // Children are composed by React, not by imports: an element can sit inside the lead's element whenever both files
  // are part of the same route chunk.
  const users = usersOf(sel.lead).map((u) => path.normalize(u));
  if (!users.length) return false;
  return files.some((f) => [...rootClosures.values()].some((cl) => cl.has(path.normalize(f)) && users.some((u) => cl.has(u))));
};
// CSS order inside a route chunk: the shell's CSS first, then the route's, each in import (depth-first) order.
const orderedCss = (root) => {
  const seen = new Set();
  const out = [];
  const visit = (f) => {
    if (seen.has(f)) return;
    seen.add(f);
    if (f.endsWith(".css")) return void out.push(f);
    for (const d of staticDeps[f] ?? []) visit(d);
  };
  visit(root);
  return out;
};
const combinedOrderCache = new Map();
const combinedOrder = (root) => {
  if (!combinedOrderCache.has(root)) {
    const shell = orderedCss(shellRoot);
    combinedOrderCache.set(root, [...shell, ...orderedCss(root).filter((f) => !shell.includes(f))]);
  }
  return combinedOrderCache.get(root);
};
// -1 when css file A comes before B in every chunk that contains one of the files, 1 when after, null when unknowable.
const cssOrderBetween = (A, B, files) => {
  const signs = new Set();
  for (const [root, cl] of rootClosures) {
    if (!files.some((f) => cl.has(path.normalize(f)))) continue;
    const order = combinedOrder(root);
    const ia = order.indexOf(path.normalize(A));
    const ib = order.indexOf(path.normalize(B));
    if (ia < 0 || ib < 0) continue;
    signs.add(Math.sign(ia - ib));
  }
  return signs.size === 1 ? [...signs][0] : null;
};
const inStyles = (f) => /styles[\/]/.test(f);
// Is the css file loaded in any route chunk that contains one of the JSX files?
const loadedFor = (cssFile, files) => {
  if (inStyles(cssFile)) return true;
  for (const [root, cl] of rootClosures) {
    if (!files.some((f) => cl.has(path.normalize(f)))) continue;
    if (combinedOrder(root).includes(path.normalize(cssFile))) return true;
  }
  return false;
};
// Does the unlayered rule R reach the element (or descendant target) described by ctx?
const pseudoElementOf = (selector) => selector.match(/::?(before|after)|::[a-z-]+/)?.[0]?.replace(/^:/, "").replace(/^:/, "") ?? null;
const ruleApplies = (R, ctx) => {
  // Pseudo-element rules style other boxes, and :root/html/body rules never target an element rendered by JSX.
  // A rule styles the pseudo-element it ends in (or the element itself); only rules for the same one compete.
  if ((pseudoElementOf(R.selector) ?? null) !== (ctx.pseudo ?? null)) return false;
  if (/:root|(^|[\s>+~])(html|body)/.test(R.selector)) return false;
  if (/#[\w-]/.test(R.selector.replace(/\[[^\]]*\]/g, ""))) return false;
  if (/\[style/.test(R.selector) && (ctx.mode === "generic" || ctx.hasInline === false)) return false;
  if (ctx.mode === "own") {
    const tagOk = R.subj.tag === null || ctx.unknownTag || R.subj.tag === ctx.tag;
    const classesOk =
      ctx.unknownClasses || R.subj.classes.every((c) => ctx.tokens.has(c) || [...ctx.prefixes].some((pre) => c.startsWith(pre)));
    const reach = R.simple || !R.lead ? true : ruleReaches(R, [ctx.file]);
    return tagOk && classesOk && reach;
  }
  const tagOk = R.subj.tag === null || (ctx.tTag === null ? ctx.possibleTagsUnknown || ctx.possibleTags.has(R.subj.tag) : R.subj.tag === ctx.tTag);
  const classesOk = ctx.possibleUnknown || R.subj.classes.every((c) => ctx.possible.has(c));
  const reach = R.simple || !R.lead ? true : ruleReaches(R, ctx.files);
  return tagOk && classesOk && reach;
};
// Should the unlayered rule R beat the entry (higher specificity, or equal and later in the same file)?
const ruleRelation = (R, en, enSpec, ctx) => {
  const c = cmpSpec(R.spec, enSpec);
  if (c > 0) return "win";
  if (c < 0) return "lose";
  if (R.file === en.file) return R.line > en.line ? "win" : "lose";
  if (inStyles(R.file) && !inStyles(en.file)) return "lose";
  const files = ctx.mode === "own" ? [ctx.file] : ctx.files;
  const ord = cssOrderBetween(R.file, en.file, files);
  if (ord === null) return "unknown";
  return ord < 0 ? "lose" : "win";
};
// Which remaining unlayered rules beat the entry (wins), lose to it (loses), or have an unknowable order (unknown).
const compete = (en, ctx) => {
  let wins = false;
  let loses = false;
  let unknown = false;
  const why = { w: [], l: [], u: [] };
  const enSpec = specOf(en.selector);
  for (const R of allSelectors) {
    if (R.skip) continue;
    const imp = R.imp.has(en.bp);
    if (!imp && !R.props.has(en.bp)) continue;
    if (R.subj.tag === "html" || R.subj.tag === "body") continue;
    const converted = R.lead && ctx.active[R.lead];
    if (converted && (R.simple || R.lead === ctx.self)) continue;
    if (!loadedFor(R.file, ctx.mode === "own" ? [ctx.file] : ctx.files)) continue;
    if (!ruleApplies(R, ctx)) continue;
    if (en.important) {
      if (!imp) continue;
      const rl = ruleRelation(R, en, enSpec, ctx);
      if (rl === "win") (wins = true, why.w.push(R.selector));
      else if (rl === "unknown") (unknown = true, why.u.push(R.selector));
      continue;
    }
    if (imp) {
      wins = true;
      why.w.push(R.selector + " !imp");
      continue;
    }
    const rl = ruleRelation(R, en, enSpec, ctx);
    if (rl === "win") (wins = true, why.w.push(R.selector));
    else if (rl === "lose") (loses = true, why.l.push(R.selector));
    else (unknown = true, why.u.push(R.selector + "@" + R.file.split(/[\/]/).pop() + " vs " + en.file.split(/[\/]/).pop()));
  }
  return { wins, loses, unknown, why };
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
      const nativeNormal = new Set();
      const nativeImportant = new Set();
      const shadowing = new Set(); // exact props set by important, variant-free natives: they beat any class rule
      for (const t of g.tokens) {
        if (active[t] || cssDefined.has(t)) continue;
        const imp = t.endsWith("!") || t.startsWith("!");
        twProps(t).forEach((pp) => (imp ? nativeImportant : nativeNormal).add(pp));
        if (imp && !hasVariant(t)) exactProps(t.replace(/^!/, ""))?.forEach((pp) => shadowing.add(pp));
      }
      const inlineSet = g.inline === "all" ? null : g.inline;
      const isShadowed = (prop) =>
        [...shadowing].some((pp) => covers(pp, prop)) || (inlineSet ? [...inlineSet].some((pp) => covers(pp, prop)) : false);
      const isComponent = typeof g.tag !== "string" || /^[A-Z]/.test(g.tag);
      // Order between converted classes that set the same property: the later rule won, so it gets more specificity.
      const owners = new Map();
      for (const t of g.tokens) {
        const e = active[t];
        if (!e) continue;
        for (const en of e.entries) {
          if (isShadowed(en.prop)) continue;
          const key = en.prefix + en.bp;
          const list = owners.get(key) ?? owners.set(key, []).get(key);
          if (!list.some((x) => x.t === t)) list.push({ t, file: en.file, line: en.line });
        }
      }
      const levelOf = new Map();
      for (const [key, list] of owners) {
        if (list.length < 2) continue;
        if (new Set(list.map((x) => x.file)).size > 1) {
          for (const x of list) addConflict(conflicts, x.t, "two-classes-same-prop-across-files");
          continue;
        }
        list.sort((a, b) => a.line - b.line).forEach((x, i) => levelOf.set(`${x.t}\u0000${key}`, i));
      }
      // One decision per property: when any rule of the class for it must be important, all of them are,
      // otherwise a state variant (`.active`) could not override its own base declaration.
      const decisions = new Map();
      for (const t of g.tokens) {
        const e = active[t];
        if (!e) continue;
        if (g.unknown) addConflict(conflicts, t, "unknown-dynamic-classes");
        const need = {};
        const forbid = {};
        const whyMap = {};
        const live = e.entries.filter((en) => en.generic || !isShadowed(en.prop));
        for (const en of live) {
          let n;
          if (en.generic) n = en.fixedBang;
          else {
            const res = compete(en, {
              mode: "own",
              active,
              self: t,
              tag: isComponent ? null : g.tag,
              unknownTag: isComponent,
              tokens: g.tokens,
              prefixes: g.prefixes,
              unknownClasses: g.unknown,
              hasInline: g.inline === "all" ? null : g.inline.size > 0,
              pseudo: pseudoElementOf(en.selector),
              file,
            });
            n = en.important || en.media || res.loses || nativeNormal.has(en.bp) || isComponent;
            if (process.env.DBG_CLASS === t) console.log("DBG", t, file, en.selector.trim(), en.bp, JSON.stringify({ n, imp: en.important, media: en.media, native: nativeNormal.has(en.bp), isComponent, wins: res.wins, loses: res.loses, unknown: res.unknown, why: res.why }));
            if (res.unknown) {
              addConflict(conflicts, t, "unknown-source-order");
              if (process.argv.includes("--dbg5")) console.log("UNKNOWN", t, en.selector.trim(), en.bp, JSON.stringify(res.why.u));
            }
            (whyMap[en.bp] ||= []).push(res.why);
            forbid[en.bp] =
              forbid[en.bp] ||
              res.wins ||
              nativeImportant.has(en.bp) ||
              g.inline === "all" ||
              Boolean(inlineSet && [...inlineSet].some((pp) => pp.split("-")[0] === en.bp));
          }
          need[en.bp] = need[en.bp] || n;
        }
        decisions.set(t, { live, need, forbid, why: whyMap });
      }
      const byProp = new Map();
      for (const [t, d] of decisions) for (const bp of Object.keys(d.need)) (byProp.get(bp) ?? byProp.set(bp, []).get(bp)).push(t);
      for (const [bp, ts] of byProp) {
        if (ts.length > 1 && ts.some((t) => decisions.get(t).need[bp])) for (const t of ts) decisions.get(t).need[bp] = true;
      }
      const rendered = new Map();
      for (const [t, d] of decisions) {
        const parts = [];
        for (const en of d.live) {
          if (d.need[en.bp] && d.forbid[en.bp]) {
            addConflict(conflicts, t, "needs-important-but-blocked");
            if (process.argv.includes("--dbg5")) console.log("BLOCKED", t, en.selector.trim(), en.bp, JSON.stringify(d.why?.[en.bp] ?? null));
          }
          const level = levelOf.get(`${t}\u0000${en.prefix + en.bp}`) ?? 0;
          parts.push("[&&]:".repeat(level) + en.pre + en.base + (d.need[en.bp] ? "!" : ""));
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
coOccur = {};
for (const file of jsxFiles) {
  let ast;
  try {
    ast = parse(sources[file], { sourceType: "module", plugins: ["jsx"] });
  } catch {
    continue;
  }
  const groups = new Map();
  for (const s of classStrings(ast)) {
    const g = groups.get(s.attr) ?? { tokens: new Set(), tag: s.tag, unknown: s.unknown };
    sources[file].slice(s.start, s.end).split(/\s+/).filter(Boolean).forEach((t) => g.tokens.add(t));
    groups.set(s.attr, g);
  }
  for (const { tokens } of groups.values()) {
    for (const a of tokens) for (const b of tokens) if (a !== b) (coOccur[a] ||= new Set()).add(b);
  }
  const rec = (impByFile[file] = { cls: {}, tag: {}, tagCls: {}, tagUnknown: {}, clsTags: {} });
  for (const { tokens, tag, unknown } of groups.values()) {
    if (typeof tag !== "string" || !/^[a-z]/.test(tag)) continue;
    const set = (rec.tagCls[tag] ||= new Set());
    tokens.forEach((t) => set.add(t));
    if (unknown) rec.tagUnknown[tag] = true;
  }
  for (const { tokens, tag, unknown } of groups.values()) {
    for (const t of tokens) {
      const ct = (rec.clsTags[t] ||= { tags: new Set(), unknown: false });
      if (typeof tag === "string" && /^[a-z]/.test(tag)) ct.tags.add(tag);
      else ct.unknown = true;
      if (unknown) ct.unknown = true;
    }
  }
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
  for (let depth = 0; depth < 4; depth++) {
    const next = [];
    for (const f of frontier) for (const d of staticDeps[f] ?? []) if (!out.has(d)) (out.add(d), next.push(d));
    frontier = next;
  }
  return out;
};
for (const [name, e] of Object.entries(eligible)) {
  const generic = e.entries.filter((en) => en.generic);
  if (!generic.length) continue;
  const users = usersOf(name);
  const scope = new Set(users.flatMap((f) => [...nearby(f)]));
  let dead = false;
  for (const en of generic) {
    const tail = en.selector.trim().replace(/^\.-?[_a-zA-Z][\w-]*/, "");
    const target = en.selector.trim().match(/([^\s>+~]+)$/)?.[1] ?? "";
    const tTag = target.match(/^[a-z][a-z0-9]*/)?.[0] ?? null;
    const tClasses = [...target.matchAll(/[.](-?[_a-zA-Z][\w-]*)/g)].map((m) => m[1]);
    const tags = [...tail.matchAll(/(?:^|[\s>+~])([a-z][a-z0-9]*)/g)].map((m) => m[1]);
    const classes = classesIn(en.selector).slice(1);
    // Classes that can sit on the target element: its own, those seen beside them, and those on same-tag elements in scope.
    const possible = new Set(tClasses);
    let possibleUnknown = false;
    for (const tc of tClasses) coOccur[tc]?.forEach((c) => possible.add(c));
    if (tTag) {
      let seenTag = false;
      for (const f of scope) {
        const rec = impByFile[f];
        if (!rec) continue;
        if (rec.tagCls[tTag]) seenTag = true;
        rec.tagCls[tTag]?.forEach((c) => possible.add(c));
        if (rec.tagUnknown[tTag]) possibleUnknown = true;
      }
      void seenTag;
    }
    const possibleTags = new Set();
    let possibleTagsUnknown = false;
    if (tTag === null) {
      for (const f of scope) {
        const rec = impByFile[f];
        for (const tc of tClasses) {
          const ct = rec?.clsTags[tc];
          if (!ct) continue;
          ct.tags.forEach((x) => possibleTags.add(x));
          if (ct.unknown) possibleTagsUnknown = true;
        }
      }
      if (!tClasses.length) possibleTagsUnknown = true;
    }
    const res = compete(en, { mode: "generic", active: eligible, self: name, pseudo: pseudoElementOf(en.selector), tTag, tClasses, possible, possibleUnknown, possibleTags, possibleTagsUnknown, files: [...scope] });
    const need = en.important || en.media || res.loses;
    // A child carrying its own important utility for the property would be beaten by an important descendant rule.
    let forbid = false;
    for (const f of scope) {
      const rec = impByFile[f];
      if (!rec) continue;
      if (classes.some((c) => rec.cls[c]?.has(en.bp) || rec.cls[c]?.has("*"))) forbid = true;
      if (tags.some((tg) => rec.tag[tg]?.has(en.bp) || rec.tag[tg]?.has("*"))) forbid = true;
    }
    if (need && (res.wins || res.unknown || forbid) || (!need && res.unknown)) {
      dead = true;
      if (process.argv.includes("--dbg2")) console.log("CLASHDETAIL", name, en.selector.trim(), en.bp, JSON.stringify({ need, ...res, forbid }));
    }
    en.fixedBang = need;
  }
  if (dead) {
    rej("descendant-competition", e.occurrences);
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
