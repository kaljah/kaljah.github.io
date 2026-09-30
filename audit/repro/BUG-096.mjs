// BUG-096: Scope 2 steam entry sends hidden unit "kWh" while the dropdown shows "Select...". Needs UI :5191 / API :5056.
import { execFileSync } from "child_process";
const out = execFileSync("node", ["k_s2flow.mjs", "steam"], { cwd: new URL(".", import.meta.url).pathname.replace(/^\//, ""), encoding: "utf8" });
console.log(out);
const bad = out.includes('"Select..."') && out.includes('"unit":"kWh"');
console.log("expected: displayed unit == sent unit; actual mismatch =", bad);
process.exit(bad ? 1 : 0);
