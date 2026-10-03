// Gives clickable non-semantic elements (div/span/tr/li/td with onClick and no role) an explicit role so keyboard and
// assistive tech users are not left with a mouse-only control:
//   modal backdrops and stopPropagation wrappers -> role="presentation"
//   table rows -> role="row" (they already have tabIndex and key handlers where interactive)
//   dropdown options and collapsible headers -> role="button", tabIndex, Enter/Space activation
// Usage: node scripts/add-roles.mjs [--write]
import fs from "node:fs";
import path from "node:path";

const write = process.argv.includes("--write");
const walk = (dir, out = []) => {
  for (const n of fs.readdirSync(dir)) {
    if (n === "node_modules" || n === "__tests__") continue;
    const p = path.join(dir, n);
    fs.statSync(p).isDirectory() ? walk(p, out) : out.push(p);
  }
  return out;
};

const tagRe = /<(div|span|tr|li|td)\b[^>]*onClick[^>]*>/g;
let count = 0;
for (const file of walk("src").filter((f) => f.endsWith(".jsx"))) {
  let text = fs.readFileSync(file, "utf8");
  const edits = [];
  let needImport = false;
  for (const m of text.matchAll(tagRe)) {
    const tag = m[0];
    if (tag.includes("role=")) continue;
    const name = m[1];
    let next;
    if (name === "tr") next = tag.replace("<tr", '<tr role="row"');
    else if (/stopPropagation|position:fixed|modal-overlay/.test(tag)) next = tag.replace(`<${name}`, `<${name} role="presentation"`);
    else if (/dropdown-option|setShowGuide|setRoadmapCollapsed/.test(tag)) {
      const attrs = ' role="button" tabIndex={0}' + (tag.includes("onKeyDown") ? "" : " onKeyDown={activateOnKey}");
      next = tag.replace(`<${name}`, `<${name}${attrs}`);
      if (next.includes("onKeyDown={activateOnKey}")) needImport = true;
    } else next = tag.replace(`<${name}`, `<${name} role="presentation"`);
    edits.push({ start: m.index, end: m.index + tag.length, next });
  }
  if (!edits.length) continue;
  count += edits.length;
  if (!write) continue;
  for (const e of edits.sort((a, b) => b.start - a.start)) text = text.slice(0, e.start) + e.next + text.slice(e.end);
  if (needImport && !text.includes("import { activateOnKey }")) {
    let rel = path.relative(path.dirname(file), path.join("src", "utils", "a11yKeys")).split(path.sep).join("/");
    if (!rel.startsWith(".")) rel = `./${rel}`;
    text = text.replace(/^import[^\n]*\n/m, (first) => `${first}import { activateOnKey } from "${rel}";\n`);
  }
  fs.writeFileSync(file, text);
}
console.log(`${write ? "updated" : "would update"} ${count} elements`);
