// BUG-107: CustomDropdown triggers are not keyboard-focusable. Needs UI :5191 / API :5056.
import { start, UI } from "./k_uilib.mjs";
const { browser, page } = await start("admin");
await page.goto(UI + "/emissions?scope=scope1"); await page.waitForTimeout(9000);
const r = await page.evaluate(() => {
  const dd = [...document.querySelectorAll(".dropdown-selected")];
  return { total: dd.length, focusable: dd.filter(e => e.tabIndex >= 0).length };
});
console.log(`expected all ${r.total} dropdown triggers focusable; actual focusable = ${r.focusable}`);
await browser.close(); process.exit(r.focusable === r.total ? 0 : 1);
