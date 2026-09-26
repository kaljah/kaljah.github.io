import { launch, session, sleep, openS1, fillS1, submitS1, pick } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await openS1(page);
await fillS1(page, { facility: "AUDIT-L Plant", year: 2025, month: 1, tier: "Tier 3", qty: 1000 });
{ const all = await page.locator(".custom-dropdown .dropdown-selected").allInnerTexts(); await pick(page, null, "m³", { idx: all.findIndex(t => t.trim() === "Select..."), exact: true }); }
const lab = l => page.locator("div").filter({ has: page.locator("label", { hasText: l }) }).last();
await lab("CO2 Factor").locator("input").first().fill("2.0");
await lab("CH4 Factor").locator("input").first().fill("0.001");
await lab("N2O Factor").locator("input").first().fill("0.0001");
await lab("HHV — Higher Heating Value").locator("input").first().fill("1000");
await lab("Combustion Efficiency").locator("input").first().fill("99.5");
console.log("inspector:", (await page.locator(".formula-inspector-card").innerText()).replace(/\n+/g, " "));
const r = await submitS1(page, log, true);
console.log(r?.status, "req:", r?.req?.slice(0, 900));
console.log("resp:", JSON.stringify(r?.body).slice(0, 600));
await b.close();
