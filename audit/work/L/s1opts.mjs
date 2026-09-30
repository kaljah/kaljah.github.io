import { launch, session, shot, UI, sleep, pick, ddOptions } from "./lib.mjs";
const b = await launch();
const { page, log } = await session(b, "admin");
await page.goto(UI + "/emissions"); await sleep(2500);
await page.getByText("Scope 1", { exact: true }).first().click(); await sleep(2500);
console.log("PROCESS:", (await ddOptions(page, "Process Type")).join(" ; "));
const proc = process.argv[2];
if (proc) { console.log("picked", await pick(page, "Process Type", proc, { exact: true })); }
const tier = process.argv[3];
if (tier) { await page.locator(".tier-selector-btn", { hasText: tier }).click(); await sleep(800); }
const dds = page.locator(".custom-dropdown .dropdown-selected");
const n = await dds.count();
for (let i = 0; i < n; i++) {
  const d = dds.nth(i); const txt = await d.innerText();
  await d.scrollIntoViewIfNeeded(); await d.click(); await sleep(300);
  const o = await page.locator(".dropdown-portal .dropdown-option").allInnerTexts();
  console.log(`DD${i} [${txt}] (${o.length}):`, o.slice(0, 80).map(s => s.replace(/\n/g, " ")).join(" ; "));
  await page.mouse.click(5, 500); await sleep(200);
}
const sec = await page.locator(".calc-panel").innerText();
console.log(sec.slice(0, 2500));
await shot(page, "s1opts", true);
await b.close();
