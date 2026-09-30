import { launch, session, UI, sleep } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/manage-data"); await sleep(3000);
await page.getByText("Emission Factors", { exact: true }).first().click(); await sleep(2500);
const cf = [...log.api].reverse().find(a => a.url.includes("custom-factors") && a.method === "GET");
console.log("api", cf?.url, Array.isArray(cf?.body) ? cf.body.length : JSON.stringify(cf?.body).slice(0, 200), Array.isArray(cf?.body) ? cf.body.filter(x => /AUDIT-L/.test(x.name || x.factor_name)).length : "");
console.log("rows in table:", await page.locator("tr").count(), "AUDIT-L rows:", await page.locator("tr", { hasText: "AUDIT-L" }).count());
const t = await page.locator("body").innerText(); console.log((t.match(/Page \d+ of \d+|Showing[^\n]*/g) || []).slice(0, 3));
await b.close();
