// Generic behavior-neutral JSX extraction. Usage:
//   node scripts/extract-jsx.mjs <file> <outDir> <Component> <Name@startLine>... [--shared a,b]
// The element starting at that line moves verbatim into <outDir>/<Name>.jsx; identifiers it uses from the
// component scope become props; module-level imports are re-created; --shared names come from ./shared.
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;

const args = process.argv.slice(2);
const autoArg = args.findIndex((a) => a === "--auto");
const autoMin = autoArg >= 0 ? Number(args[autoArg + 1]) : 0;
if (autoArg >= 0) args.splice(autoArg, 2);
const maxArg = args.findIndex((a) => a === "--max");
const autoMax = maxArg >= 0 ? Number(args[maxArg + 1]) : Infinity;
if (maxArg >= 0) args.splice(maxArg, 2);
const sharedArg = args.findIndex((a) => a === "--shared");
const shared = new Set(sharedArg >= 0 ? args[sharedArg + 1].split(",") : []);
if (sharedArg >= 0) args.splice(sharedArg, 2);
const [file, outDir, comp, ...targets] = args;
const code = fs.readFileSync(file, "utf8");
const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
const lineOf = (pos) => code.slice(0, pos).split("\n").length;
fs.mkdirSync(outDir, { recursive: true });

const imports = {};
let innerScope = null;
traverse(ast, {
  ImportDeclaration(p) { for (const s of p.node.specifiers) imports[s.local.name] = { decl: p.node, spec: s }; },
  VariableDeclarator(p) { if (p.node.id.name === comp) innerScope = p.get("init").scope; },
  FunctionDeclaration(p) { if (p.node.id?.name === comp) innerScope = p.scope; },
});

const rel = path.relative(outDir, path.dirname(file)).split(path.sep).join("/") || ".";
const fixSource = (src) => {
  if (!src.startsWith(".")) return src;
  const joined = path.posix.normalize(path.posix.join(rel, src));
  return joined.startsWith(".") ? joined : "./" + joined;
};
const buildImports = (names) => {
  const bySource = new Map();
  const extra = [];
  for (const n of names) {
    if (n === "React") continue;
    if (shared.has(n)) { extra.push(n); continue; }
    const imp = imports[n];
    if (!imp) throw new Error("unresolved module-level name " + n);
    const src = fixSource(imp.decl.source.value);
    const e = bySource.get(src) || { def: null, named: [], ns: null };
    if (imp.spec.type === "ImportDefaultSpecifier") e.def = n;
    else if (imp.spec.type === "ImportNamespaceSpecifier") e.ns = n;
    else e.named.push(imp.spec.imported.name === n ? n : `${imp.spec.imported.name} as ${n}`);
    bySource.set(src, e);
  }
  const lines = [...bySource].map(([src, e]) => {
    const parts = [];
    if (e.def) parts.push(e.def);
    if (e.ns) parts.push(`* as ${e.ns}`);
    if (e.named.length) parts.push(`{ ${e.named.join(", ")} }`);
    return `import ${parts.join(", ")} from "${src}";`;
  });
  if (extra.length) lines.push(`import { ${extra.join(", ")} } from "./shared";`);
  return lines.join("\n");
};


const pascal = (str) => str.replace(/(^|[^A-Za-z0-9])([A-Za-z0-9])/g, (_, __, c) => c.toUpperCase()).replace(/[^A-Za-z0-9]/g, "");
const autoJobs = [];
if (autoMin) {
  const chosen = [];
  traverse(ast, {
    ReturnStatement(rp) {
      const fp = rp.getFunctionParent();
      if ((fp.node.id?.name || fp.parentPath.node.id?.name) !== comp) return;
      if (fp.scope !== innerScope) return;
      rp.get("argument").traverse({
        JSXElement(p) {
          const n = lineOf(p.node.end) - lineOf(p.node.start);
          if (n < autoMin || n > autoMax) return;
          if (!p.findParent((q) => q.isJSXElement())) return; // skip the root
          if (chosen.some((c) => p.findParent((q) => q.node === c.node))) return;
          // all identifiers must come from the component scope or the module (not from .map callbacks etc.)
          let ok = true;
          p.traverse({
            Identifier(q) {
              if (!q.isReferencedIdentifier()) return;
              const b = q.scope.getBinding(q.node.name);
              if (!b) return;
              let sc = b.scope;
              const inside = sc === p.scope || p.scope.path.isDescendant?.(sc.path) || sc.path.isDescendant?.(p.node ? p.scope.path : p.scope.path);
              const bpath = b.path;
              if (bpath.isDescendant && bpath.isDescendant(p)) return; // declared inside the element
              if (b.scope !== innerScope && !b.scope.path.isProgram()) ok = false;
            },
          });
          let hasThisOrHook = false;
          p.traverse({ ThisExpression() { hasThisOrHook = true; }, CallExpression(q) { if (/^use[A-Z]/.test(q.node.callee.name || "")) hasThisOrHook = true; } });
          if (!ok || hasThisOrHook) return;
          chosen.push(p);
        },
      });
    },
  });
  const taken = new Set();
  chosen.forEach((p) => {
    let heading = null;
    p.traverse({
      JSXElement(q) {
        if (heading || !/^h[1-4]$/.test(q.node.openingElement.name.name || "")) return;
        const t = q.node.children.find((c) => c.type === "JSXText" && c.value.trim().length > 2);
        if (t) heading = t.value.trim().split(/\s+/).slice(0, 3).join(" ");
      },
    });
    const cls = p.node.openingElement.attributes.find((a) => a.name?.name === "className");
    const cn = cls?.value?.value || cls?.value?.expression?.quasis?.[0]?.value?.raw || "";
    let base = pascal(heading || String(cn).split(/\s+/)[0] || "Block") || "Block";
    if (!/^[A-Z]/.test(base)) base = "S" + base;
    let name = `${comp}${base}`;
    if (taken.has(name)) name += lineOf(p.node.start);
    taken.add(name);
    autoJobs.push({ name, ln: lineOf(p.node.start), path: p });
  });
}
const jobs = [...autoJobs, ...targets.map((t) => { const [name, ln] = t.split("@"); return { name, ln: Number(ln) }; })];
const found = [];
traverse(ast, {
  JSXElement(p) {
    const ln = lineOf(p.node.start);
    const job = jobs.find((j) => j.ln === ln && !j.path);
    if (!job) return;
    // outermost element starting on that line wins
    if (p.findParent((q) => q.isJSXElement() && lineOf(q.node.start) === ln)) return;
    job.path = p;
  },
});

for (const job of jobs) {
  if (!job.path) throw new Error("no JSX element starts at line " + job.ln);
  const needs = new Set(), mod = new Set();
  const visit = (id, n) => {
    const b = id.scope.getBinding(n);
    if (!b) return;
    if (b.scope === innerScope) needs.add(n);
    else if (b.scope.path.isProgram()) (imports[n] ? mod : needs).add(n); // module-level locals are passed as props
  };
  job.path.traverse({
    Identifier(p) { if (p.isReferencedIdentifier()) visit(p, p.node.name); },
    JSXIdentifier(p) {
      const n = p.node.name;
      if (/^[A-Z]/.test(n) && p.parent.type !== "JSXAttribute" && p.parent.type !== "JSXNamespacedName") visit(p, n);
    },
  });
  job.needs = [...needs].sort();
  job.mod = [...mod].sort();
}

let out = code;
for (const job of [...jobs].sort((a, b) => b.path.node.start - a.path.node.start)) {
  const { start, end } = job.path.node;
  const jsx = code.slice(start, end);
  const sig = job.needs.length ? `{ ${job.needs.join(", ")} }` : "";
  const header = `import React from "react";\n${buildImports(job.mod)}\n\n`;
  fs.writeFileSync(path.join(outDir, job.name + ".jsx"), `${header}// Extracted from ${path.basename(file)}; markup and behavior are unchanged. State and handlers stay in the parent.\nconst ${job.name} = (${sig}) => (\n${jsx}\n);\n\nexport default ${job.name};\n`);
  const call = job.needs.length ? `<${job.name}\n${job.needs.map((p) => `        ${p}={${p}}`).join("\n")}\n      />` : `<${job.name} />`;
  out = out.slice(0, start) + call + out.slice(end);
  console.log(`${job.name}: ${job.needs.length} props, ${lineOf(end) - lineOf(start)} lines`);
}
const importLines = jobs.map((j) => `import ${j.name} from "./${path.basename(outDir)}/${j.name}";`).join("\n");
const first = out.indexOf('import "./ScopeTables.css"');
out = first >= 0 ? out.slice(0, first) + importLines + "\n" + out.slice(first) : importLines + "\n" + out;
fs.writeFileSync(file, out);
