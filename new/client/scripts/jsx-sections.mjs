import fs from "node:fs";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;
const file = process.argv[2];
const min = Number(process.argv[3] || 120);
const code = fs.readFileSync(file, "utf8");
const ast = parse(code, { sourceType: "module", plugins: ["jsx"] });
const line = (pos) => code.slice(0, pos).split("\n").length;
traverse(ast, {
  ReturnStatement(path) {
    const fp = path.getFunctionParent(); if ((fp.node.id?.name || fp.parentPath.node.id?.name) !== process.argv[4]) return;
    path.get("argument").traverse({
      JSXElement(p) {
        const n = line(p.node.end) - line(p.node.start);
        if (n < min) return;
        let depth = 0, q = p; while ((q = q.parentPath)) if (q.isJSXElement()) depth++;
        const cls = p.node.openingElement.attributes.find((a) => a.name?.name === "className");
        const cn = cls?.value?.value || cls?.value?.expression?.quasis?.[0]?.value?.raw || "";
        const cond = p.parentPath.isLogicalExpression() ? code.slice(p.parentPath.node.start, p.parentPath.node.right.start).slice(0, 60).replace(/\s+/g, " ") : "";
        console.log(`${"  ".repeat(depth)}${line(p.node.start)}-${line(p.node.end)} (${n}) <${p.node.openingElement.name.name} ${cn.slice(0, 40)}> ${cond}`);
      },
    });
  },
});
