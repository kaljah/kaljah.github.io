// BUG-091: dehydrator throughput labelled MMscf/yr is sent as MMscf/day. Needs UI :5191 / API :5056.
import { start, UI } from "./k_uilib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/emissions?scope=scope1"); await page.waitForTimeout(9000);
await page.locator(".dropdown-selected", { hasText: "Select Region" }).click(); await page.waitForTimeout(500);
await page.locator(".dropdown-option").nth(1).click(); await page.waitForTimeout(800);
await page.locator(".dropdown-selected", { hasText: "Stationary Combustion" }).click(); await page.waitForTimeout(500);
await page.locator(".dropdown-option", { hasText: "Dehydrator" }).first().click(); await page.waitForTimeout(1000);
const grp = (t) => page.locator(".input-group").filter({ has: page.locator("label", { hasText: t }) }).last();
for (const [t, v] of [["Gas Throughput", "1000"], ["Gas CH4 Content", "85"], ["Operating Hours", "8760"], ["Contactor Pressure", "800"], ["Contactor Temperature", "100"]]) await grp(t).locator("input").fill(v);
await grp("Pump").locator("input").first().fill("5");
const label = await grp("Gas Throughput").locator("label").innerText();
log.reqs.length = 0;
await page.getByText("Calculate & Submit", { exact: false }).click(); await page.waitForTimeout(3000);
const post = log.reqs.find(r => r.m === "POST" && r.u.startsWith("/api/emissions"));
const unit = post && JSON.parse(post.body).unit;
console.log("label:", label, "| sent unit:", unit);
await browser.close(); process.exit(unit && label.includes(unit.replace("MMscf", "MMscf")) ? 0 : 1);
