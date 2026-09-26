import { start, OUT, UI } from "./lib.mjs";
const { browser, page, log } = await start("admin");
await page.goto(UI + "/emissions"); await page.waitForTimeout(8000);
await page.getByText("Scope 1", { exact: true }).click(); await page.waitForTimeout(8000);
await page.screenshot({ path: OUT + "s1.png", fullPage: true });
console.log(page.url());
console.log((await page.$$eval("label", ls => ls.map(l => l.innerText.trim()))).join(" | "));
console.log(await page.$$eval("select,input,button", es => es.slice(0,60).map(e => e.tagName+":"+(e.name||e.placeholder||e.innerText||"").slice(0,30)).join(" ; ")));
await browser.close();
