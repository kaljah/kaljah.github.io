import { start, OUT, UI } from "./lib.mjs";
const { browser, page, log } = await start("admin");
const count = async () => { await page.goto(UI + "/reference-data"); await page.waitForTimeout(6000); return { rows: await page.locator("tr").count(), toast: (await page.locator("[class*=toast]").allInnerTexts()).join("|"), txt: (await page.locator("body").innerText()).match(/(No [^.\n]*found[^.\n]*|Failed[^.\n]*)/g) }; };
console.log("normal:", JSON.stringify(await count()));
await page.route("**/api/custom-factors**", r => r.fulfill({ status: 500, contentType: "application/json", body: '{"error":"boom"}' }));
console.log("custom-factors 500:", JSON.stringify(await count()));
await browser.close();
