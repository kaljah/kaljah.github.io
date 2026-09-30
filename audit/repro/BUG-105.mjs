// BUG-105: Reference Data hides the whole factor catalog (and shows no error) when /api/custom-factors fails. Needs UI :5191 / API :5056.
import { start, UI } from "./k_uilib.mjs";
const { browser, page } = await start("admin");
const rows = async () => { await page.goto(UI + "/reference-data"); await page.waitForTimeout(6000); return page.locator("tr").count(); };
const normal = await rows();
await page.route("**/api/custom-factors**", r => r.fulfill({ status: 500, contentType: "application/json", body: '{"error":"boom"}' }));
const failed = await rows();
const err = await page.getByText(/fail|error|unable/i).count();
console.log(`rows normal=${normal}, with custom-factors 500=${failed}, visible error messages=${err}`);
await browser.close(); process.exit(err > 0 && failed > 40 ? 0 : 1);
