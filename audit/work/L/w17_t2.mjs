import { launch, session, sleep, openS1, fillS1, submitS1, pick } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
for (const [tag, fac, qty] of [["t2_lab", "AUDIT-L Diesel Lab", 100], ["t2_empty", "AUDIT-L EMPTY", 100]]) {
  await openS1(page);
  await fillS1(page, { facility: "AUDIT-L Plant", year: 2025, month: 2, tier: "Tier 2" });
  await page.getByText("Saved Custom Factors Library").click(); await sleep(800);
  const all = await page.locator(".custom-dropdown .dropdown-selected").allInnerTexts();
  const i = all.findIndex(t => t.includes("Select Saved Custom Factor"));
  console.log(tag, "picked:", await pick(page, null, fac, { idx: i }).catch(e => e.message.slice(0, 200)));
  await page.locator("div").filter({ has: page.locator("label", { hasText: "Fuel / Activity Quantity" }) }).last().locator("input").fill(String(qty));
  await pick(page, "Unit", "gal", { exact: true });
  const r = await submitS1(page, log, true);
  console.log(tag, r?.status, "req factor:", JSON.parse(r?.req || "{}").custom_factor_id, JSON.parse(r?.req || "{}").fuel, "resp:", JSON.stringify(r?.body?.emissions), r?.body?.calculation_method);
}
await b.close();
