import { launch, session, sleep, openS1, fillS1, shot } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await openS1(page);
await fillS1(page, { facility: "AUDIT-L Plant", year: 2025, month: 3, factor: "Diesel (No. 2 Fuel Oil)", qty: -100, unit: "gal" });
const n0 = log.api.length;
await page.getByRole("button", { name: /Save as Draft/ }).click(); await sleep(700);
await shot(page, "w12_neg");
const body = await page.locator("body").innerText();
console.log("msgs:", body.match(/[^\n]*(valid|must|required|greater|positive)[^\n]*/gi)?.slice(0, 5));
console.log("validity:", await page.locator("div").filter({ has: page.locator("label", { hasText: "Fuel / Activity Quantity" }) }).last().locator("input").evaluate(e => [e.type, e.min, e.checkValidity(), e.validationMessage]));
console.log("new api", log.api.slice(n0).map(a => a.method + " " + a.url));
// no unit
await openS1(page);
await fillS1(page, { facility: "AUDIT-L Plant", year: 2025, month: 3, factor: "Diesel (No. 2 Fuel Oil)", qty: 10 });
console.log("unit shown:", await page.locator("div").filter({ has: page.locator("label", { hasText: /^Unit$/ }) }).last().innerText());
await b.close();
