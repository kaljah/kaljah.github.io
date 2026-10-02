import fs from "node:fs";
import path from "node:path";
import { blocks, code, imports } from "./split-managedata.mjs";

const OUT = "src/pages/manage-data";
fs.mkdirSync(OUT, { recursive: true });

const nameFor = (cond) => {
  const tab = /activeTab === '(\w+)'/.exec(cond)[1];
  if (tab === "pending") return cond.includes("!isPrivileged") ? "PendingAccessNotice" : "PendingReviewTab";
  return tab[0].toUpperCase() + tab.slice(1) + "Tab";
};
const fixSource = (src) => (src.startsWith("./") ? "." + src : src.startsWith("../") ? "../" + src : src);

const buildImports = (names) => {
  const bySource = new Map();
  const local = [];
  for (const n of names) {
    if (n === "PaginationControls") { local.push(`import PaginationControls from './PaginationControls';`); continue; }
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
    return `import ${parts.join(", ")} from '${src}';`;
  });
  return [...lines, ...local].join("\n");
};

// 1) PaginationControls module
const pcStart = code.indexOf("const PaginationControls");
const pcEnd = code.indexOf("const ManageDataInner");
const pc = code.slice(pcStart, pcEnd).trimEnd();
fs.writeFileSync(path.join(OUT, "PaginationControls.jsx"), `import React, { useEffect } from 'react';\n\n${pc}\n\nexport default PaginationControls;\n`);

// 2) tab components + parent rewrite
let parent = code;
const used = [];
for (const b of [...blocks].reverse()) {
  const name = nameFor(b.cond);
  used.push(name);
  const jsx = code.slice(b.right.start, b.right.end);
  const left = code.slice(b.e.start, b.e.left.end);
  const props = b.needs;
  const header = `import React from 'react';\n${buildImports(b.modLevel)}\n\n`;
  const sig = props.length ? `{ ${props.join(", ")} }` : "";
  const body = `// Extracted from ManageData.jsx; markup and behavior are unchanged. State and handlers stay in the parent.\nconst ${name} = (${sig}) => (\n${jsx}\n);\n\nexport default ${name};\n`;
  fs.writeFileSync(path.join(OUT, name + ".jsx"), header + body);
  const call = props.length
    ? `<${name}\n${props.map((p) => `                            ${p}={${p}}`).join("\n")}\n                        />`
    : `<${name} />`;
  parent = parent.slice(0, b.start) + `{${left} && ${call}}` + parent.slice(b.end);
}
// remove PaginationControls from parent and import tabs
parent = parent.replace(code.slice(pcStart, pcEnd), "");
const tabImports = used.reverse().map((n) => `import ${n} from './manage-data/${n}';`).join("\n");
parent = parent.replace("import './ManageData.css';", `${tabImports}\nimport './ManageData.css';`);
fs.writeFileSync("src/pages/ManageData.jsx", parent);
console.log("written", used.length, "tabs; parent lines:", parent.split("\n").length);
