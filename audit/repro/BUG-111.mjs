// BUG-111 repro: Scope 1 bulk import via the UI wizard (browser stack :5190 -> :5055 -> audit/db/browser.db)
import { launch, session, sleep, openS1 } from "../work/L/lib.mjs";
import fs from "fs";
const tag = Date.now() % 100000;
const csv = `Date,Site,Process,Fuel,Qty,UOM,Year,Month\n2024-02-01,AUDIT-L Plant,combustion,Diesel (No. 2 Fuel Oil),${tag},,2024,2\n1800-03-01,AUDIT-L Plant,combustion,Motor Gasoline,${tag},gal,1800,3\n`;
const f = "C:/Users/samsung/Desktop/H2/audit/work/L/bug111.csv"; fs.writeFileSync(f, csv);
const b = await launch(); const { page, log } = await session(b, "admin");
await openS1(page);
await page.getByRole("button", { name: /Bulk Import \(Wizard\)/ }).click(); await sleep(1500);
for (let s = 0; s < 2; s++) { await page.locator(".s1w-modal").getByRole("button", { name: /Next/ }).last().click(); await sleep(800); }
await page.locator("input[type=file]").setInputFiles(f); await sleep(2000);
const rows = page.locator(".s1w-map-row"); const n = await rows.count();
for (const [l, c] of [["Region / Facility", "Site"], ["Quantity", "Qty"], ["Unit", "UOM"]]) for (let i = 0; i < n; i++) if ((await rows.nth(i).locator(".s1w-map-field-label").innerText()).trim() === l) await rows.nth(i).locator("select").selectOption(c);
await page.locator(".s1w-modal").getByRole("button", { name: /Start Import/ }).click();
let st;
for (let i = 0; i < 30; i++) { await sleep(1000); st = [...log.api].reverse().find(a => a.url.includes("upload/status")); if (st?.body?.status === "completed" || st?.body?.status === "error") break; }
const list = await page.evaluate(async () => (await (await fetch("/api/emissions?scope=1&limit=50&offset=0", { credentials: "include" })).json()));
const data = list.data || list;
const blank = data.find(r => r.amount == tag && /Diesel/.test(r.fuel_type || r.fuel || ""));
const y1800 = data.find(r => r.amount == tag && r.year === 1800);
console.log(`job ${st?.body?.status}, skipped ${st?.body?.skipped_count}; blank-unit row stored as unit=${blank?.unit} (expected: skipped); year-1800 row stored=${!!y1800} (expected: skipped)`);
await b.close(); process.exit(blank || y1800 ? 1 : 0);
