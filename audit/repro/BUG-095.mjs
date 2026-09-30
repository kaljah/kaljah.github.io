// BUG-095: Scope 1 Recent Activity CSV export = current page only; year options from current page. Needs UI :5191 / API :5056.
import { start, UI, OUT } from "./k_uilib.mjs";
import fs from "fs";
const { browser, page } = await start("admin");
await page.goto(UI + "/emissions?scope=scope1"); await page.waitForTimeout(9000);
const pager = await page.getByText(/Page \d+ of/).innerText();
const dl = page.waitForEvent("download"); await page.getByText("Export CSV").click();
const p = OUT + "bug095.csv"; await (await dl).saveAs(p);
const rows = fs.readFileSync(p, "utf8").trim().split("\n").length - 1;
const years = await page.locator("select").filter({ has: page.locator("option", { hasText: "All Years" }) }).locator("option").allInnerTexts();
console.log(`pager: ${pager}; expected CSV rows > 10, actual ${rows}; year options: ${years.join(",")}`);
await browser.close(); process.exit(rows > 10 ? 0 : 1);
