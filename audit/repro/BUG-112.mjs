// BUG-112 repro (browser stack :5190 -> :5055 -> audit/db/browser.db)
import { launch, session } from "../work/L/lib.mjs";
const b = await launch(); const { page } = await session(b, "admin");
const call = (m, p, body) => page.evaluate(async ([m, p, body]) => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const r = await fetch("/api" + p, { method: m, credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t }, body: body ? JSON.stringify(body) : undefined });
  return [r.status, await r.json().catch(() => null)];
}, [m, p, body]);
const [s1, cf] = await call("POST", "/custom-factors", { factor_name: "BUG112 empty " + Date.now(), unit: "gal", co2_factor: "", ch4_factor: "", n2o_factor: "" });
let rec = null;
if (s1 < 300) [, rec] = await call("POST", "/emissions", { facility_id: 173, year: 2025, month: 2, process_type: "combustion", quantity: 100, amount: 100, unit: "gal", factor_source: "custom", custom_factor_id: cf.id, fuel: String(cf.id), fuel_type: String(cf.id), status: "Draft", calc_inputs: { combustion: { fuel: String(cf.id), amount: 100, unit: "gal" } } });
console.log(`blank custom factor: expected 400, actual ${s1}; record using it: totalCo2e=${rec?.emissions?.totalCo2e}`);
await b.close(); process.exit(s1 < 300 ? 1 : 0);
