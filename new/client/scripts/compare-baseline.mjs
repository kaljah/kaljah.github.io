// Pixel-diff two screenshot sets from e2e/visual-baseline.spec.js.
// Usage: node scripts/compare-baseline.mjs before after [maxDiffRatio]
import fs from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";

const [a, b, thr = "0.002"] = process.argv.slice(2);
const dirA = path.join("e2e/artifacts/baseline", a);
const dirB = path.join("e2e/artifacts/baseline", b);
const diffDir = path.join("e2e/artifacts/baseline", `diff-${a}-${b}`);
fs.mkdirSync(diffDir, { recursive: true });
let bad = 0;
for (const f of fs.readdirSync(dirA).filter((x) => x.endsWith(".png"))) {
  const pb = path.join(dirB, f);
  if (!fs.existsSync(pb)) { console.log("MISSING", f); bad++; continue; }
  const A = PNG.sync.read(fs.readFileSync(path.join(dirA, f)));
  const B = PNG.sync.read(fs.readFileSync(pb));
  if (A.width !== B.width || A.height !== B.height) {
    console.log(`SIZE   ${f}: ${A.width}x${A.height} -> ${B.width}x${B.height}`); bad++; continue;
  }
  const out = new PNG({ width: A.width, height: A.height });
  const n = pixelmatch(A.data, B.data, out.data, A.width, A.height, { threshold: 0.1 });
  const ratio = n / (A.width * A.height);
  if (ratio > Number(thr)) { fs.writeFileSync(path.join(diffDir, f), PNG.sync.write(out)); console.log(`DIFF   ${f}: ${(ratio * 100).toFixed(2)}%`); bad++; }
}
console.log(bad ? `${bad} file(s) differ` : "no visual differences above threshold");
process.exit(bad ? 1 : 0);
