import { launch, session, shot, UI, sleep, lastApi } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/sbti"); await sleep(5000);
await shot(page, "w5_sbti", true);
let t = await page.locator("main, body").first().innerText();
console.log("SBTI TEXT:", t.slice(t.indexOf("SBTi"), t.indexOf("SBTi") + 2500).replace(/\n+/g, " | "));
console.log("APIs:", log.api.filter(a => /sbti|target|trajectory/i.test(a.url)).map(a => `${a.status} ${a.url} ${JSON.stringify(a.body).slice(0, 700)}`).join("\n"));
const btn = page.getByText("Scope 1+2 (Operational)", { exact: false }).first();
if (await btn.count()) { await btn.click(); await sleep(3000); await shot(page, "w5_sbti_s12", true);
  t = await page.locator("main, body").first().innerText();
  const k = t.search(/ON TRACK|OFF TRACK|AT RISK|Reduction/i); console.log("S12 TEXT:", t.slice(Math.max(0, k - 600), k + 600).replace(/\n+/g, " | ")); }
else console.log("no Scope 1+2 toggle");
await page.goto(UI + "/"); await sleep(5000);
t = await page.locator("main, body").first().innerText();
console.log("DASH %GOAL present:", /% ?GOAL/i.test(t), "| SBTi label:", (t.match(/SBTi[^\n|]*Linear Target[^\n]*/) || [""])[0]);
const m = t.match(/[^\n]*% ?GOAL[^\n]*/i); console.log("goal badge text:", m?.[0]);
await b.close();
