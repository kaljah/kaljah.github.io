// One-off codemod: extracts the tab blocks of pages/ManageData.jsx into pages/manage-data/*Tab.jsx.
// Behavior-neutral: each block moves verbatim; the identifiers it uses from the component scope become props.
import fs from "node:fs";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;

const SRC = "src/pages/ManageData.jsx";
const code = fs.readFileSync(SRC, "utf8");
const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });

let inner = null;
const blocks = [];
traverse(ast, {
  VariableDeclarator(path) {
    if (path.node.id.name === "ManageDataInner") inner = path;
  },
});
const innerScope = inner.get("init").scope;

traverse(ast, {
  JSXExpressionContainer(path) {
    const e = path.node.expression;
    if (e.type !== "LogicalExpression" || e.operator !== "&&") return;
    const src = code.slice(e.start, e.end);
    // only the top-level tab blocks: "activeTab === 'x' && ... && ( <JSX> )"
    if (!/^activeTab === '\w+'/.test(src)) return;
    if (path.findParent((p) => p.isJSXExpressionContainer())) return;
    let right = e.right;
    const cond = code.slice(e.start, right.start).trim();
    blocks.push({ path, e, right, cond, start: path.node.start, end: path.node.end });
  },
});

const imports = {};
traverse(ast, {
  ImportDeclaration(p) {
    for (const s of p.node.specifiers) imports[s.local.name] = { decl: p.node, spec: s };
  },
});

for (const b of blocks) {
  const needs = new Set();
  const modLevel = new Set();
  b.path.get("expression.right").traverse({
    Identifier(p) {
      if (!p.isReferencedIdentifier()) return;
      const bind = p.scope.getBinding(p.node.name);
      if (!bind) return;
      if (bind.scope === innerScope) needs.add(p.node.name);
      else if (bind.scope.path.isProgram()) modLevel.add(p.node.name);
    },
    JSXIdentifier(p) {
      const n = p.node.name;
      if (!/^[A-Z]/.test(n) || p.parent.type === "JSXAttribute") return;
      const bind = p.scope.getBinding(n);
      if (!bind) return;
      if (bind.scope === innerScope) needs.add(n);
      else if (bind.scope.path.isProgram()) modLevel.add(n);
    },
  });
  b.needs = [...needs].sort();
  b.modLevel = [...modLevel].sort();
  console.log(`${code.slice(0, b.start).split("\n").length}-${code.slice(0, b.end).split("\n").length} | ${b.cond.slice(0, 70).replace(/\n/g, " ")} | props=${b.needs.length} mod=${b.modLevel.join(",")}`);
}
export { blocks, code, imports, innerScope, inner };
