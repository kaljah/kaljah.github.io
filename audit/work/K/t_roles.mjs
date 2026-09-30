import { start, OUT, UI } from "./lib.mjs";
const routes = ["/", "/emissions", "/manage-data", "/qa-dashboard", "/reports", "/carbon-intensity", "/methane-intensity", "/methane-explorer", "/sbti", "/uncertainty", "/reference-data", "/diagnostics", "/audit-trail", "/user-management", "/settings"];
const role = process.argv[2];
const { browser, page, log } = await start(role);
const links = await page.$$eval("a[href]", as => [...new Set(as.map(a => a.getAttribute("href")))]);
console.log(role, "landing:", page.url().replace(UI, ""), "sidebar links:", links.join(" "));
for (const r of routes) {
  log.resps.length = 0; log.errors.length = 0;
  await page.goto(UI + r); await page.waitForTimeout(r === "/" ? 5000 : 3500);
  const bad = log.resps.filter(x => x.s >= 400).map(x => x.s + " " + x.u.split("?")[0]);
  const txt = (await page.locator("main, .main-content, body").first().innerText()).slice(0, 0);
  const crashed = await page.locator("text=/Something went wrong|Error boundary|Unexpected/i").count();
  console.log(`${r.padEnd(20)} -> ${page.url().replace(UI, "").padEnd(20)} api>=400: ${[...new Set(bad)].join(", ") || "-"} ${crashed ? "CRASH" : ""} pageerr: ${log.errors.filter(e=>e.startsWith("PAGEERROR")).length}`);
}
await browser.close();
