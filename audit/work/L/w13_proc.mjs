import { launch, session, sleep, openS1, fillS1, submitS1, pick, shot } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
const cases = JSON.parse(process.argv[2]);
for (const c of cases) {
  await openS1(page);
  try {
    await fillS1(page, { facility: "AUDIT-L Plant", year: 2025, month: c.month || 4, process: c.process, tier: c.tier });
    if (c.factor) { const all = await page.locator(".custom-dropdown .dropdown-selected").allInnerTexts(); const i = all.findIndex(t => /Select Standard Emission Factor|Select Custom|Select/.test(t) && !/Region|Source|Unit/.test(t)); await pick(page, null, c.factor, { idx: i, exact: true }); }
    if (c.qty !== undefined) await page.locator("div").filter({ has: page.locator("label", { hasText: c.qtyLabel || "Fuel / Activity Quantity" }) }).last().locator("input").first().fill(String(c.qty));
    if (c.unit) await pick(page, "Unit", c.unit, { exact: true });
    for (const [l, v] of Object.entries(c.fill || {})) { const inp = page.locator("div").filter({ has: page.locator("label", { hasText: l }) }).last().locator("input, select").first(); if ((await inp.evaluate(e => e.tagName)) === "SELECT") await inp.selectOption(String(v)); else await inp.fill(String(v)); }
    if (c.dump) console.log("FORM:", (await page.locator(".calc-panel").innerText()).replace(/\n+/g, " | ").slice(0, 2500));
    const r = await submitS1(page, log, false);
    if (!r) { console.log(c.tag, "NO REQUEST", (await page.locator("body").innerText()).match(/[^\n]*(Please|required|valid)[^\n]*/g)?.slice(0, 3)); await shot(page, "w13_" + c.tag, true); continue; }
    const e = r.body?.emissions || {};
    console.log(c.tag, r.status, "id", r.body?.id, "tot", e.totalCo2e, "co2", e.co2, "ch4", e.ch4, "| req", r.req.slice(0, 500), r.status >= 400 ? JSON.stringify(r.body) : "");
    await sleep(1500);
    const row = await page.locator("tr", { hasText: "AUDIT-L" }).first().innerText().catch(() => "");
    console.log("   first list row:", row.replace(/\s+/g, " ").slice(0, 200));
  } catch (err) { console.log(c.tag, "ERR", err.message.slice(0, 400)); }
}
await b.close();
