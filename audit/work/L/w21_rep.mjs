import { launch, session, shot, UI, sleep } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/reports"); await sleep(6000);
const t = await page.locator("body").innerText();
console.log((t.match(/Total Records[^\n]*/) || [])[0]);
for (const a of log.api.filter(a => !/notif|csrf|auth|settings/.test(a.url))) console.log(a.status, a.url, Array.isArray(a.body) ? `array(${a.body.length})` : JSON.stringify(a.body).slice(0, 300));
await shot(page, "w21_rep", true);
await b.close();
