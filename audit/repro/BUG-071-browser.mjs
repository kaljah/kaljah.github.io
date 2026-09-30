// Stale dashboard repro (browser stack :5190 -> :5055 -> audit/db/browser.db)
import { launch, session, sleep, UI } from "../work/L/lib.mjs";
const b = await launch();
const { page } = await session(b, "admin");
const call = (m, p, body) => page.evaluate(async ([m, p, body]) => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const r = await fetch("/api" + p, { method: m, credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t }, body: body ? JSON.stringify(body) : undefined });
  return [r.status, await r.json().catch(() => null)];
}, [m, p, body]);
// fresh facility so numbers are isolated
const [, fac] = await call("POST", "/facilities", { name: "STALE-" + Date.now(), activity: "EP", division: "Production", location: "West", latitude: 1, longitude: 1 });
const q = async () => (await call("GET", `/dashboard/batch-all?facilityId=${fac.id}&activity=all&division=all&year=2025`))[1].summary?.[0]?.scope1_total ?? 0;
const before = await q();   // primes the cache
const [st, rec] = await call("POST", "/emissions", { facility_id: fac.id, year: 2025, month: 1, process_type: "combustion", quantity: 1000, amount: 1000, unit: "gal", factor_source: "default", fuel: "Diesel (No. 2 Fuel Oil)", fuel_type: "Diesel (No. 2 Fuel Oil)", calc_inputs: { combustion: { fuel: "Diesel (No. 2 Fuel Oil)", amount: 1000, unit: "gal" } } });
const stored = rec?.emissions?.totalCo2e;
await sleep(3000);
const after = await q();
// what the UI dashboard shows after a full page reload
await page.goto(UI + "/"); await sleep(3000);
console.log(`facility ${fac.id}: POST ${st} status Verified co2e=${stored}; dashboard scope1 before=${before} after=${after} (expected ${stored})`);
await b.close();
process.exit(Math.abs(after - stored) > 1e-6 ? 1 : 0);
