import { start, OUT, UI } from "./lib.mjs";
const { browser, page } = await start("admin", { viewport: { width: 390, height: 844 } });
for (const r of ["/", "/emissions?scope=scope1", "/emissions?scope=scope2", "/manage-data", "/reports", "/settings", "/audit-trail", "/reference-data"]) {
  await page.goto(UI + r); await page.waitForTimeout(r.startsWith("/emissions") ? 8000 : 5000);
  const m = await page.evaluate(() => {
    const sw = document.documentElement.scrollWidth;
    const inputs = [...document.querySelectorAll("input:not([type=hidden]), select, textarea")].filter(e => e.offsetParent);
    const unlabeled = inputs.filter(e => !(e.labels && e.labels.length) && !e.getAttribute("aria-label") && !e.getAttribute("aria-labelledby") && !e.title).length;
    const dd = document.querySelectorAll(".dropdown-selected").length;
    const ddFocusable = [...document.querySelectorAll(".dropdown-selected")].filter(e => e.tabIndex >= 0 || e.getAttribute("role")).length;
    return { sw, inputs: inputs.length, unlabeled, dd, ddFocusable };
  });
  console.log(r.padEnd(26), JSON.stringify(m));
  if (r === "/emissions?scope=scope1" || r === "/reports") await page.screenshot({ path: OUT + "m390_" + r.replace(/\W/g, "_") + ".png" });
}
await browser.close();
