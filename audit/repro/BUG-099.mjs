// BUG-099 repro (browser stack :5190 -> :5055 -> audit/db/browser.db)
import { launch, session } from "../work/L/lib.mjs";
const b = await launch(); const { page } = await session(b, "user");
const r = await page.evaluate(async () => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const res = await fetch("/api/scope2", { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t },
    body: JSON.stringify({ year: 2025, month: 9, facility_id: 173, source_type: "electricity", grid_region: "Algerian National Grid", electricity_kwh: 0, emission_factor: 0, co2e: 12345 }) });
  return [res.status, await res.json().catch(() => null)];
});
console.log(`0 kWh with client co2e=12345: expected 400 (or co2e 0), actual HTTP ${r[0]} co2e=${r[1]?.co2e}`);
await b.close(); process.exit(r[0] < 300 && r[1]?.co2e ? 1 : 0);
