import { launch, session, shot, UI, sleep, pick } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/carbon-intensity"); await sleep(4000);
const all = await page.locator(".custom-dropdown .dropdown-selected").allInnerTexts(); console.log("dds", all);
const ri = all.findIndex(t => t.includes("All Regions")); await pick(page, null, "AUDIT-L Plant", { idx: ri }); await sleep(3000);
const yi = (await page.locator(".custom-dropdown .dropdown-selected").allInnerTexts()).findIndex(t => /All Years|All-Time|^\d{4}$/.test(t.trim()));
console.log("year dd idx", yi);
if (yi >= 0) { await pick(page, null, "2025", { idx: yi, exact: true }).catch(e => console.log(e.message.slice(0, 200))); await sleep(3000); }
const t = await page.locator("main, body").first().innerText();
const i = t.indexOf("GHG INTENSITY"); console.log(t.slice(i - 150, i + 900).replace(/\n+/g, " | "));
console.log(log.api.filter(a => /intensity|production/.test(a.url)).slice(-4).map(a => `${a.status} ${a.url} ${JSON.stringify(a.body).slice(0, 900)}`).join("\n"));
await shot(page, "w11_ci", true);
await b.close();
