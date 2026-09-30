import { launch, session, sleep, openS1, fillS1, submitS1, toasts, grpOf } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
const cases = [["year1800", { year: 1800, qty: 10 }], ["year2099", { year: 2099, qty: 10 }], ["qty0", { year: 2025, qty: 0 }], ["qtyNeg", { year: 2025, qty: -100 }], ["qtyEmpty", { year: 2025, qty: "" }], ["qtyHuge", { year: 2025, qty: "1e15" }], ["noUnit", { year: 2025, qty: 10, nounit: true }], ["noFacility", { year: 2025, qty: 10, nofac: true }]];
for (const [tag, c] of cases) {
  await openS1(page);
  await fillS1(page, { facility: c.nofac ? undefined : "AUDIT-L Plant", year: c.year, month: 3, factor: "Diesel (No. 2 Fuel Oil)", qty: c.qty, unit: c.nounit ? undefined : "gal" });
  const r = await submitS1(page, log, true);
  console.log(tag, r ? `${r.status} ${JSON.stringify(r.body).slice(0, 160)}` : "NO REQUEST", "| toast:", (await toasts(page)).replace(/\s+/g, " ").slice(0, 120));
}
await b.close();
