import { start, OUT, UI } from "./k_uilib.mjs";
const HHV = process.argv[2] || "38", HU = process.argv[3] || "MJ/m3";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/emissions?scope=scope1"); await page.waitForTimeout(9000);
await page.locator(".dropdown-selected", { hasText: "Select Region" }).click(); await page.waitForTimeout(500);
await page.locator(".dropdown-option").nth(1).click(); await page.waitForTimeout(800);
await page.locator(".tier-selector-btn", { hasText: "Tier 3" }).click(); await page.waitForTimeout(800);
const grp = (t) => page.locator(".input-group").filter({ has: page.locator("label", { hasText: t }) }).last();
await grp("Fuel / Activity Quantity").locator("input").fill("1000");
await page.locator(".input-group").filter({ has: page.locator("label", { hasText: /^Unit$/ }) }).first().locator(".dropdown-selected").click(); await page.waitForTimeout(300);
await page.locator(".dropdown-option", { hasText: "m³" }).first().click();
for (const [t, v] of [["CO2 Factor", "53.06"], ["CH4 Factor", "0.001"], ["N2O Factor", "0.0001"]]) { const i = grp(t).locator("input").first(); if (await i.count()) { await i.fill(v); await grp(t).locator("select").selectOption("kg/MMBtu"); } }
await page.fill("#hhv-input", HHV);
await grp("HHV Unit").locator("select").selectOption(HU);
await grp("Combustion Efficiency").locator("input").first().fill("99.5");
log.reqs.length = 0;
await page.getByText("Calculate & Submit", { exact: false }).click(); await page.waitForTimeout(3000);
console.log("toasts:", (await page.locator(".toast, [class*=toast-message]").allInnerTexts()).join(" / "));
const post = log.reqs.find(r => r.m === "POST" && r.u.startsWith("/api/emissions"));
const resp = log.resps.find(r => r.u.startsWith("/api/emissions") && r.body && r.body.includes("totalCo2e"));
if (post) { const b = JSON.parse(post.body); console.log("top hhv:", b.hhv, b.hhv_unit, "| calc_inputs:", JSON.stringify(b.calc_inputs)); }
console.log("RESP:", resp && resp.body.slice(0, 300));
const rp = page.locator(".result-panel"); console.log("RESULT PANEL:", (await rp.count()) ? (await rp.innerText()).replace(/\s+/g," ").slice(0,600) : "none");
await page.screenshot({ path: OUT + "hhv.png", fullPage: true });
await browser.close();
