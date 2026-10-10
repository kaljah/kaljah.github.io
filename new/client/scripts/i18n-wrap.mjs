#!/usr/bin/env node
/**
 * One-off codemod: wraps visible English interface text in t("...") (src/i18n).
 *
 *   node scripts/i18n-wrap.mjs [--dry] [files...]     (default: every .tsx/.ts under src/)
 *
 * Wraps: JSX text; display attributes (placeholder, title, aria-label, label, ...); toast / alert /
 * confirm messages; label-like properties of objects in pages, components, ui and app. Leaves data
 * modules (constants, utils, types), tests, code samples and unit-like tokens alone. Babel only
 * locates the text: edits are spliced into the original source, so formatting is unchanged.
 * Prints the wrapped strings as JSON on stdout (--list) for translation.
 */
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import traverseModule from "@babel/traverse";

const traverse = traverseModule.default || traverseModule;
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const SRC = path.join(ROOT, "src");
const args = process.argv.slice(2);
const DRY = args.includes("--dry");
const LIST = args.includes("--list");
const fileArgs = args.filter((a) => !a.startsWith("--"));

const SKIP_DIRS = ["__tests__", "i18n", "types", "constants", "dev"];
const SKIP_FILES = new Set(["test-setup.ts", "vite-env.d.ts", "ModernReportGenerator.ts", "main.tsx"]);
// Object properties are only wrapped in these folders (elsewhere a "label" may be data sent to the API).
const OBJECT_PROP_DIRS = ["pages", "components", "ui", "app", "filters", "context", "hooks"];

const ATTRS = new Set([
  "placeholder", "title", "aria-label", "alt", "label", "sublabel", "description", "helperText", "hint",
  "emptyMessage", "emptyText", "emptyTitle", "emptyDescription", "tooltip", "subtitle", "footnote",
  "confirmLabel", "cancelLabel", "caption", "heading", "loadingText", "valueText", "aria-description",
  "aria-roledescription", "message",
]);
const OBJECT_KEYS = new Set([
  "label", "title", "description", "sublabel", "subtitle", "placeholder", "tooltip", "hint", "helperText",
  "emptyMessage", "footnote", "heading", "caption", "message", "confirmLabel", "cancelLabel",
]);
// Helpers whose last string argument is a fallback message shown to the user.
const MESSAGE_HELPERS = new Set(["apiError", "errorMessage", "getErrorMessage", "describeError"]);
const TOAST_METHODS = new Set(["success", "error", "info", "warning", "warn", "loading"]);
const NO_TEXT_PARENTS = new Set(["code", "pre", "kbd", "samp", "style", "script", "var"]);

/** Visible prose worth translating (not a unit, code, number or single symbol). */
function isProse(text) {
  const s = text.trim();
  if (s.length < 2) return false;
  if (!/[A-Za-z]{2,}/.test(s)) return false;
  if (/^(https?:|\/|\.\/|#)/.test(s)) return false;
  // tokens like kg/BOE, tCO2e, m3/d, CH4, AR6, 1H, ISO-14064 (no space, digits or slashes or all caps)
  if (!/\s/.test(s) && (/[\d/_=]/.test(s) || /^[A-Z0-9.\-+]+$/.test(s))) return false;
  if (/^[a-z]+(_[a-z]+)+$/.test(s)) return false; // snake_case identifiers
  return true;
}

/** Rendered value of a JSX text node (React's whitespace rules). */
function renderedJsxText(raw) {
  const lines = raw.split(/\r\n|\n|\r/);
  let last = -1;
  lines.forEach((l, i) => { if (/[^ \t]/.test(l)) last = i; });
  let out = "";
  lines.forEach((line, i) => {
    const isFirst = i === 0;
    const isLast = i === lines.length - 1;
    let trimmed = line.replace(/\t/g, " ");
    if (!isFirst) trimmed = trimmed.replace(/^[ ]+/, "");
    if (!isLast) trimmed = trimmed.replace(/[ ]+$/, "");
    if (trimmed) {
      if (i !== last) trimmed += " ";
      out += trimmed;
    }
  });
  return out;
}

function listFiles(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (!SKIP_DIRS.includes(entry.name)) out.push(...listFiles(p));
    } else if (/\.(tsx|ts)$/.test(entry.name) && !entry.name.endsWith(".d.ts") && !SKIP_FILES.has(entry.name)
               && !/\.(test|spec)\.tsx?$/.test(entry.name)) {
      out.push(p);
    }
  }
  return out;
}

function decodeEntities(s) {
  return s.replace(/ /g, " ");
}

function processFile(file, collected) {
  const code = fs.readFileSync(file, "utf8");
  let ast;
  try {
    ast = parse(code, { sourceType: "module", plugins: ["typescript", "jsx"], errorRecovery: false });
  } catch (e) {
    console.error(`skip (parse error) ${path.relative(ROOT, file)}: ${e.message}`);
    return 0;
  }
  const rel = path.relative(SRC, file);
  const topDir = rel.split(path.sep)[0];
  const objectProps = OBJECT_PROP_DIRS.includes(topDir) || !rel.includes(path.sep);

  // Name of the imported function: t, unless the file already binds "t" somewhere.
  let tName = "t";
  let alreadyImported = false;
  traverse(ast, {
    ImportDeclaration(p) {
      if (/(^|\/)i18n$/.test(p.node.source.value)) {
        for (const s of p.node.specifiers) if (s.imported && s.imported.name === "t") { alreadyImported = true; tName = s.local.name; }
      }
    },
  });
  if (!alreadyImported) {
    let tBound = false;
    traverse(ast, {
      Scope(p) { if (Object.prototype.hasOwnProperty.call(p.scope.bindings, "t")) tBound = true; },
      Identifier(p) { if (p.node.name === "t" && p.scope.hasBinding("t")) tBound = true; },
    });
    if (tBound) tName = "tr";
  }

  const edits = [];
  const call = (text) => `${tName}(${JSON.stringify(text)})`;
  const add = (start, end, replacement, key) => {
    edits.push({ start, end, replacement });
    collected.add(key);
  };

  traverse(ast, {
    JSXText(p) {
      const parentEl = p.parentPath.node;
      const tag = parentEl.type === "JSXElement" && parentEl.openingElement.name.type === "JSXIdentifier"
        ? parentEl.openingElement.name.name : "";
      if (NO_TEXT_PARENTS.has(tag)) return;
      const raw = p.node.extra?.raw ?? p.node.value;
      const rendered = decodeEntities(renderedJsxText(p.node.value));
      if (!isProse(rendered)) return;
      const core = rendered.trim();
      const lead = rendered.startsWith(" ") ? '{" "}' : "";
      const trail = rendered.endsWith(" ") ? '{" "}' : "";
      const leadWs = (raw.match(/^\s*/)[0].includes("\n") ? raw.match(/^\s*/)[0] : "");
      const trailWs = (raw.match(/\s*$/)[0].includes("\n") ? raw.match(/\s*$/)[0] : "");
      add(p.node.start, p.node.end, `${leadWs}${lead}{${call(core)}}${trail}${trailWs}`, core);
    },
    // {cond ? "Collapse" : "Pin open"}, {label || "Untitled"} as a child, or in a display attribute
    JSXExpressionContainer(p) {
      const parent = p.parentPath.node;
      const inChild = parent.type === "JSXElement" || parent.type === "JSXFragment";
      const inAttr = parent.type === "JSXAttribute" && parent.name.type === "JSXIdentifier" && ATTRS.has(parent.name.name);
      if (!inChild && !inAttr) return;
      const visit = (n) => {
        if (!n) return;
        if (n.type === "ConditionalExpression") { visit(n.consequent); visit(n.alternate); }
        else if (n.type === "LogicalExpression") { visit(n.left); visit(n.right); }
        else if (n.type === "StringLiteral" && isProse(n.value)) add(n.start, n.end, call(n.value), n.value);
      };
      const e = p.node.expression;
      if (e.type === "ConditionalExpression" || e.type === "LogicalExpression") visit(e);
      else if (inChild && e.type === "StringLiteral" && isProse(e.value) && e.value.trim() === e.value) add(e.start, e.end, call(e.value), e.value);
    },
    JSXAttribute(p) {
      const name = p.node.name.type === "JSXIdentifier" ? p.node.name.name : "";
      if (!ATTRS.has(name)) return;
      const v = p.node.value;
      if (v && v.type === "StringLiteral" && isProse(v.value)) {
        add(v.start, v.end, `{${call(v.value)}}`, v.value);
      } else if (v && v.type === "JSXExpressionContainer" && v.expression.type === "StringLiteral" && isProse(v.expression.value)) {
        add(v.expression.start, v.expression.end, call(v.expression.value), v.expression.value);
      }
    },
    CallExpression(p) {
      const c = p.node.callee;
      // apiError(err, "fallback")
      if (c.type === "Identifier" && MESSAGE_HELPERS.has(c.name)) {
        for (const a of p.node.arguments) {
          if (a.type === "StringLiteral" && isProse(a.value)) add(a.start, a.end, call(a.value), a.value);
        }
        return;
      }
      const isToast = c.type === "MemberExpression" && c.property.type === "Identifier" && TOAST_METHODS.has(c.property.name)
        && /toast/i.test(c.object.type === "Identifier" ? c.object.name : c.object.type === "MemberExpression" && c.object.property.type === "Identifier" ? c.object.property.name : "");
      // toast.error(err?.response?.data?.error || "fallback")  /  cond ? "a" : "b"
      if (isToast && p.node.arguments[0]) {
        const visit = (n) => {
          if (!n) return;
          if (n.type === "LogicalExpression") { visit(n.right); visit(n.left); }
          else if (n.type === "ConditionalExpression") { visit(n.consequent); visit(n.alternate); }
          else if (n.type === "StringLiteral" && n !== p.node.arguments[0] && isProse(n.value)) add(n.start, n.end, call(n.value), n.value);
        };
        visit(p.node.arguments[0]);
      }
      const arg = p.node.arguments[0];
      if (!arg || arg.type !== "StringLiteral" || !isProse(arg.value)) return;
      let match = false;
      if (c.type === "MemberExpression" && c.property.type === "Identifier" && TOAST_METHODS.has(c.property.name)) {
        const obj = c.object;
        const objName = obj.type === "Identifier" ? obj.name : obj.type === "MemberExpression" && obj.property.type === "Identifier" ? obj.property.name : "";
        match = /toast/i.test(objName);
      } else if (c.type === "Identifier" && ["alert", "confirm"].includes(c.name)) {
        match = true;
      } else if (c.type === "MemberExpression" && c.object.type === "Identifier" && c.object.name === "window"
                 && c.property.type === "Identifier" && ["alert", "confirm", "prompt"].includes(c.property.name)) {
        match = true;
      }
      if (match) add(arg.start, arg.end, call(arg.value), arg.value);
    },
    ObjectProperty(p) {
      if (!objectProps) return;
      const k = p.node.key;
      const key = k.type === "Identifier" ? k.name : k.type === "StringLiteral" ? k.value : "";
      if (!OBJECT_KEYS.has(key)) return;
      const v = p.node.value;
      if (v.type !== "StringLiteral" || !isProse(v.value)) return;
      // not inside a call to the API (payloads keep their English values)
      const inApiCall = p.findParent((q) => q.isCallExpression() && q.node.callee.type === "MemberExpression"
        && q.node.callee.object.type === "Identifier" && /^(api|axios)$/.test(q.node.callee.object.name));
      if (inApiCall) return;
      add(v.start, v.end, call(v.value), v.value);
    },
  });

  if (!edits.length) return 0;
  edits.sort((a, b) => b.start - a.start);
  let out = code;
  for (const e of edits) out = out.slice(0, e.start) + e.replacement + out.slice(e.end);

  if (!alreadyImported) {
    const relImport = path.relative(path.dirname(file), path.join(SRC, "i18n")).split(path.sep).join("/");
    const spec = relImport.startsWith(".") ? relImport : `./${relImport}`;
    const importLine = tName === "t" ? `import { t } from "${spec}";\n` : `import { t as ${tName} } from "${spec}";\n`;
    const imports = ast.program.body.filter((n) => n.type === "ImportDeclaration");
    if (imports.length) {
      // after the last import (edits above only touch code after the imports)
      const lastImport = imports[imports.length - 1];
      const lineEnd = out.indexOf("\n", out.indexOf(code.slice(lastImport.start, lastImport.end)) + (lastImport.end - lastImport.start));
      out = out.slice(0, lineEnd + 1) + importLine + out.slice(lineEnd + 1);
    } else {
      out = importLine + out;
    }
  }
  if (!DRY) fs.writeFileSync(file, out);
  return edits.length;
}

const files = fileArgs.length ? fileArgs.map((f) => path.resolve(f)) : listFiles(SRC);
const collected = new Set();
let total = 0;
for (const f of files) {
  const n = processFile(f, collected);
  if (n && !LIST) console.error(`${String(n).padStart(4)}  ${path.relative(ROOT, f)}`);
  total += n;
}
console.error(`${total} strings wrapped in ${files.length} files (${collected.size} distinct)${DRY ? " [dry run]" : ""}`);
if (LIST) process.stdout.write(JSON.stringify([...collected].sort(), null, 1));
