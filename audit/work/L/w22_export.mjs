import { launch, session, shot, UI, sleep } from "./lib.mjs";
const b = await launch(); const { page, log } = await session(b, "admin");
await page.goto(UI + "/reports"); await sleep(5000);
const selects = page.locator("select");
const info = await selects.evaluateAll(s => s.map((x, i) => [i, x.value, [...x.options].slice(0, 4).map(o => o.text)]));
console.log(JSON.stringify(info));
// filter selects: the ones after "Filter & Group Data" (scope, year, ..., region)
const yearSel = selects.filter({ has: page.locator('option[value="2025"]') }).last();
await yearSel.selectOption("2025"); await sleep(2500);
const regSel = selects.filter({ has: page.locator("option", { hasText: "AUDIT-L Plant" }) }).last();
const v = await regSel.locator("option", { hasText: "AUDIT-L Plant" }).first().getAttribute("value"); await regSel.selectOption(v); await sleep(3000);
const t = await page.locator("body").innerText(); console.log((t.match(/Total Records[^\n]*/) || [])[0]);
const list = [...log.api].reverse().find(a => a.url.includes("/api/emissions?"));
console.log("list api:", list?.url, "total:", list?.body?.total ?? list?.body?.total_count, "rows:", list?.body?.data?.length, "sum co2e:", (list?.body?.data || []).reduce((s, r) => s + (r.co2e_total ?? r.co2e ?? 0), 0));
for (const [btn, name] of [["Excel Export", "rep.xlsx"], ["PDF Report", "rep.pdf"]]) {
  const [dl] = await Promise.all([page.waitForEvent("download", { timeout: 20000 }).catch(() => null), page.getByRole("button", { name: btn }).first().click()]);
  if (dl) { await dl.saveAs("C:/Users/samsung/Desktop/H2/audit/work/L/" + name); console.log(btn, "saved", dl.suggestedFilename()); } else console.log(btn, "no download");
  const e = [...log.api].reverse().find(a => /export/.test(a.url)); console.log("  export call:", e?.status, e?.url);
}
await b.close();
