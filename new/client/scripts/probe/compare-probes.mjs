// Compares two probe output folders (see playwright.probe.config.js). Class names are ignored (they change when
// styles move), chart SVG nodes are ignored (animation), and files are matched by name.
// Usage: node scripts/probe/compare-probes.mjs <folderA> <folderB> [--ignore audit]
import fs from "node:fs";
import path from "node:path";

const [dirA, dirB, ...rest] = process.argv.slice(2);
const ignore = rest.includes("--ignore") ? rest[rest.indexOf("--ignore") + 1] : null;
const SVG = new Set(["g", "path", "line", "defs", "clipPath", "rect", "circle", "text", "tspan", "svg", "polyline", "polygon"]);

const load = (file) =>
  fs
    .readFileSync(file, "utf8")
    .split("\n")
    .map((row) => row.split("|"))
    .filter((f) => f.length >= 5 && !SVG.has(f[1]))
    .map((f) => [f[1], ...f.slice(3)].join("|"));

// Number of differing blocks between two row lists (longest common subsequence).
const diffBlocks = (a, b) => {
  const n = a.length;
  const m = b.length;
  const lcs = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
  let i = 0;
  let j = 0;
  let blocks = 0;
  let inBlock = false;
  while (i < n || j < m) {
    if (i < n && j < m && a[i] === b[j]) {
      i++;
      j++;
      inBlock = false;
    } else {
      if (!inBlock) blocks++;
      inBlock = true;
      if (j >= m || (i < n && lcs[i + 1][j] >= lcs[i][j + 1])) i++;
      else j++;
    }
  }
  return blocks;
};

let bad = 0;
for (const name of fs.readdirSync(dirA).filter((f) => f.endsWith(".txt")).sort()) {
  if (ignore && name.includes(ignore)) continue;
  const other = path.join(dirB, name);
  if (!fs.existsSync(other)) {
    console.log(name, "MISSING");
    bad++;
    continue;
  }
  const blocks = diffBlocks(load(path.join(dirA, name)), load(other));
  if (blocks) {
    console.log(name, "differing blocks:", blocks);
    bad++;
  }
}
console.log(bad ? `${bad} file(s) differ` : "no differences");
process.exitCode = bad ? 1 : 0;
