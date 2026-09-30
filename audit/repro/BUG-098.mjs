// BUG-098: EmissionResult shows non-zero CH4 as "0.00 tonnes". Needs UI :5191 / API :5056.
import { execFileSync } from "child_process";
const out = execFileSync("node", ["k_hhvflow.mjs", "38", "MJ/m3"], { cwd: new URL(".", import.meta.url).pathname.replace(/^\//, ""), encoding: "utf8" });
const ch4 = +(out.match(/"ch4":([0-9.e+-]+)/) || [])[1];
const shown = (out.match(/METHANE ([0-9.,]+) tonnes/) || [])[1];
console.log(`API ch4 = ${ch4} t; panel shows "${shown} tonnes"`);
process.exit(ch4 > 0 && parseFloat(shown) === 0 ? 1 : 0);
