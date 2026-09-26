// BUG-006: Reports exports drop division filter. Needs UI :5191 / API :5056.
import { start, UI } from "./k_uilib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/reports"); await page.waitForTimeout(4000);
await page.locator("select").filter({ has: page.locator("option", { hasText: "All Divisions" }) }).selectOption("Upstream");
await page.waitForTimeout(2000); log.reqs.length = 0;
await page.getByText("Excel Export").click(); await page.waitForTimeout(2500);
const req = log.reqs.find(r => r.u.includes("/emissions/export"));
console.log("expected: request contains division=Upstream");
console.log("actual:  ", req && req.u);
await browser.close();
process.exit(req && req.u.includes("division=Upstream") ? 0 : 1);
