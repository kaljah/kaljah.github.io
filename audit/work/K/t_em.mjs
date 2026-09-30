import { start, OUT, UI } from "./lib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/emissions"); await page.waitForTimeout(15000);
await page.screenshot({ path: OUT + "em1.png", fullPage: true });
const labels = await page.$$eval("label", ls => ls.map(l => l.innerText.trim()).filter(Boolean));
console.log(labels.join(" | "));
console.log(log.errors);
await browser.close();
