import { launch, session, shot, UI, sleep, toasts } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/manage-data"); await sleep(3000);
await page.getByText("Emission Factors", { exact: true }).first().click(); await sleep(2000);
const f = n => page.locator(`[name="${n}"]`).first();
const save = async tag => { const n0 = log.api.length; await page.getByRole("button", { name: "Save Factor" }).click(); await sleep(2000);
  console.log(tag, log.api.slice(n0).filter(a => a.method !== "GET").map(a => `${a.status} ${a.method} ${a.url} req=${a.req} resp=${JSON.stringify(a.body).slice(0, 200)}`), "|", (await toasts(page)).replace(/\s+/g, " ").slice(0, 100)); };
// invalid: negative factor
await f("factor_name").fill("AUDIT-L NEG"); await f("unit").selectOption("gal"); await f("co2_factor").fill("-5"); await save("negative");
await f("factor_name").fill("AUDIT-L EMPTY"); await f("co2_factor").fill(""); await f("ch4_factor").fill(""); await f("n2o_factor").fill(""); await save("allEmpty");
await f("factor_name").fill("AUDIT-L Diesel Lab"); await f("unit").selectOption("gal"); await f("co2_factor").fill("10.5"); await f("ch4_factor").fill("0.0005"); await f("n2o_factor").fill("0.0001"); await f("co2_uncertainty").fill("3"); await save("valid");
await page.reload(); await sleep(3000); await page.getByText("Emission Factors", { exact: true }).first().click(); await sleep(2000);
console.log("listed after reload:", (await page.locator("tr", { hasText: "AUDIT-L" }).allInnerTexts()).map(s => s.replace(/\s+/g, " ")));
await b.close();
