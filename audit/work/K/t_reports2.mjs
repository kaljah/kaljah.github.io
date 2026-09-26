import { start, OUT, UI } from "./lib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/reports"); await page.waitForTimeout(4000);
// table region filter is the select whose first option is "all" with text All Regions
const regionSel = page.locator("select").filter({ has: page.locator('option', { hasText: "All Regions" }) });
await regionSel.selectOption("170"); await page.waitForTimeout(1500);
log.reqs.length = 0;
const dl = page.waitForEvent("download", { timeout: 8000 }).catch(() => null);
await page.getByText("2025 Master Report (PDF)").click();
const d = await dl;
console.log("download filename:", d && d.suggestedFilename());
console.log(log.reqs.filter(r => r.u.includes("master")).map(r => r.m + " " + r.u));
await browser.close();
