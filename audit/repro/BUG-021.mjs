// BUG-021: Reports search keeps page number. Needs UI :5191 / API :5056.
import { start, UI } from "./k_uilib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/reports"); await page.waitForTimeout(4000);
await page.locator("select").nth(4).selectOption("all"); await page.waitForTimeout(2000);
await page.locator(".btn-page").nth(1).click(); await page.waitForTimeout(2000);
log.reqs.length = 0;
await page.fill(".search-input", "Flaring"); await page.waitForTimeout(3000);
const req = log.reqs.filter(r => r.u.startsWith("/api/emissions?")).pop();
console.log("expected: page=1 in search request"); console.log("actual:  ", req && req.u);
await browser.close(); process.exit(req && req.u.includes("page=1&") ? 0 : 1);
