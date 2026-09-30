import { launch, session } from "./lib.mjs";
const b = await launch(); const { page } = await session(b, process.argv[2] || "user");
const call = (m, p, body) => page.evaluate(async ([m, p, body]) => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const r = await fetch("/api" + p, { method: m, credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t }, body: body ? JSON.stringify(body) : undefined });
  return [r.status, await r.text()];
}, [m, p, body]);
const base = { year: 2025, month: 9, facility_id: 173, source_type: "electricity" };
for (const extra of [
  { grid_region: "My Supplier (market-based)", electricity_kwh: 1000, emission_factor: 0, co2e: 0 },
  { grid_region: "My Supplier", electricity_kwh: 1000, emission_factor: 0.001, co2e: 999 },
  { grid_region: "My Supplier", electricity_kwh: 0, emission_factor: 0, co2e: -500 },
  { grid_region: "Algerian National Grid", electricity_kwh: 0, emission_factor: 0, co2e: 12345 },
]) { const r = await call("POST", "/scope2", { ...base, ...extra }); console.log(JSON.stringify(extra), "->", r[0], r[1].slice(0, 260)); }
await b.close();
