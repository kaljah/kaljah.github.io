import { start, OUT } from "./lib.mjs";
const { browser, page, log } = await start("admin");
console.log(page.url());
await page.screenshot({ path: OUT + "t0.png" });
console.log(log.errors); console.log(log.resps.map(r => r.s + " " + r.u).join("\n"));
await browser.close();
