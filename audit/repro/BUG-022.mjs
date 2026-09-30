// BUG-022: Reports Group By is a no-op. Needs UI :5191 / API :5056.
import { start, UI } from "./k_uilib.mjs";
const { browser, page } = await start("admin");
await page.goto(UI + "/reports"); await page.waitForTimeout(4000);
await page.locator("select").nth(4).selectOption("all"); await page.waitForTimeout(2000);
const a = await page.locator(".grid-row").allInnerTexts();
await page.locator("select").filter({ has: page.locator("option", { hasText: "No Grouping" }) }).selectOption("facility"); await page.waitForTimeout(1000);
const b = await page.locator(".grid-row").allInnerTexts();
const changed = JSON.stringify(a) !== JSON.stringify(b);
console.log("expected: grouped rendering differs; actual changed =", changed);
await browser.close(); process.exit(changed ? 0 : 1);
