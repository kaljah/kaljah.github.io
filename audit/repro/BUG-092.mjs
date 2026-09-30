// BUG-092 repro (browser stack :5190 -> :5055 -> audit/db/browser.db)
import { launch, session, sleep, openS1, UI } from "../work/L/lib.mjs";
const b = await launch();
const call = (page, m, p, body) => page.evaluate(async ([m, p, body]) => {
  const t = (await (await fetch("/api/csrf-token", { credentials: "include" })).json()).csrf_token;
  const r = await fetch("/api" + p, { method: m, credentials: "include", headers: { "Content-Type": "application/json", "X-CSRFToken": t }, body: body ? JSON.stringify(body) : undefined });
  return [r.status, await r.json().catch(() => null)];
}, [m, p, body]);
const u = await session(b, "user"), a = await session(b, "admin");
const fac = (await call(u.page, "GET", "/facilities"))[1].find(f => f.name === "AUDIT-L Plant") ;
const qty = 777 + Math.floor(Math.random() * 1000);
const [, rec] = await call(u.page, "POST", "/emissions", { facility_id: fac.id, year: 2025, month: 2, process_type: "combustion", quantity: qty, amount: qty, unit: "gal", factor_source: "default", fuel: "Diesel (No. 2 Fuel Oil)", fuel_type: "Diesel (No. 2 Fuel Oil)", calc_inputs: { combustion: { fuel: "Diesel (No. 2 Fuel Oil)", amount: qty, unit: "gal" } } });
const n0 = (await call(u.page, "GET", "/notifications"))[1];
await call(a.page, "POST", `/emissions/reject/${rec.id}`, { scope: "1", reason: "BUG-092 repro" });
const n1 = (await call(u.page, "GET", "/notifications"))[1];
const cnt = x => Array.isArray(x) ? x.length : (x?.notifications?.length ?? x?.data?.length ?? 0);
await openS1(u.page); await sleep(1500);
const row = (await u.page.locator("tr", { hasText: `${qty.toLocaleString("en-US")}.00 gal` }).first().innerText().catch(() => "")).replace(/\s+/g, " ");
const shows = /Rejected/i.test(row);
console.log(`record ${rec.id} rejected; maker notifications before=${cnt(n0)} after=${cnt(n1)} (expected +1); list row shows status: ${shows} (expected true) row="${row.slice(0, 120)}"`);
await b.close(); process.exit(!shows || cnt(n1) <= cnt(n0) ? 1 : 0);
