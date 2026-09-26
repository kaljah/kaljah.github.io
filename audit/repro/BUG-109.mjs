// Scope 1 form submitted without a Unit (browser stack :5190 -> :5055 -> audit/db/browser.db)
import { launch, session, openS1, fillS1, submitS1 } from "../work/L/lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await openS1(page);
await fillS1(page, { facility: "AUDIT-L Plant", year: 2025, month: 3, factor: "Diesel (No. 2 Fuel Oil)", qty: 10 });
const r1 = await submitS1(page, log, true);
await openS1(page);
await fillS1(page, { facility: "AUDIT-L Plant", year: 2025, month: 3, factor: "Diesel (No. 2 Fuel Oil)", qty: 2641.72, unit: "gal" });
const r2 = await submitS1(page, log, true);
const a = r1.body, c = r2.body;
console.log(`no unit: request ${JSON.parse(r1.req).quantity} ${JSON.parse(r1.req).unit} (calc_inputs ${JSON.stringify(JSON.parse(r1.req).calc_inputs)}) -> record ${a.record.amount} ${a.record.unit}, ${a.emissions.totalCo2e} t`);
console.log(`same stored activity entered explicitly: ${c.record.amount} ${c.record.unit} -> ${c.emissions.totalCo2e} t`);
const bad = r1.status < 300 && Math.abs(a.emissions.totalCo2e - c.emissions.totalCo2e) / c.emissions.totalCo2e > 0.01;
console.log(bad ? "BUG: request accepted without a unit and stored activity does not match its emissions" : "ok");
await b.close(); process.exit(bad ? 1 : 0);
