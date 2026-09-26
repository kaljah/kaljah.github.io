import { launch, session } from "./lib.mjs";
const b = await launch(); const { page } = await session(b, "user");
const call = (m, p, body) => page.evaluate(async ([m, p, body]) => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const r = await fetch("/api" + p, { method: m, credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t }, body: body ? JSON.stringify(body) : undefined });
  return [r.status, await r.text()];
}, [m, p, body]);
const base = { year: 2025, month: 9, facility_id: 173, category: 1, sub_category: "Steel", unit: "kg" };
for (const x of [{ activity_data: 1000, emission_factor: 1.85, co2e: 999 }, { activity_data: 0, emission_factor: 0, co2e: 777 }, { activity_data: -1000, emission_factor: 1.85 }, { activity_data: 1000, emission_factor: -2 }])
  { const r = await call("POST", "/scope3", { ...base, ...x }); console.log(JSON.stringify(x), "->", r[0], (r[1].match(/"co2e":[-0-9.e]+/) || [r[1].slice(0, 150)])[0]); }
await b.close();
