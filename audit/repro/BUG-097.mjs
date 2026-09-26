// BUG-097: CHP power output labelled MWh used as MMBtu. Needs UI :5191 / API :5056.
import { execFileSync } from "child_process";
const out = execFileSync("node", ["k_s2flow.mjs", "cogen"], { cwd: new URL(".", import.meta.url).pathname.replace(/^\//, ""), encoding: "utf8" });
const m = out.match(/"co2e":([0-9.]+)/); const act = m ? +m[1] : NaN;
const exp = 1000 * (100 / 0.8) / (100 / 0.8 + 100 * 3.412142 / 0.33);
console.log(`expected ${exp.toFixed(2)} tCO2e, actual ${act}`);
process.exit(Math.abs(act - exp) < 1 ? 0 : 1);
