// BUG-002: Reports master-report button sends facility_id=[object Object]. Needs UI :5191 / API :5056 running.
import { start, UI } from "./k_uilib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/reports"); await page.waitForTimeout(4000);
await page.locator("select").filter({ has: page.locator("option", { hasText: "All Regions" }) }).selectOption("170");
await page.waitForTimeout(1500); log.reqs.length = 0;
await page.getByText("2025 Master Report (PDF)").click(); await page.waitForTimeout(3000);
const req = log.reqs.find(r => r.u.includes("master-annual-report"));
console.log("expected: /api/reports/master-annual-report?facility_id=170");
console.log("actual:  ", req && req.u);
await browser.close();
process.exit(req && req.u.endsWith("facility_id=170") ? 0 : 1);
