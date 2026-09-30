// BUG-108: Scope 1 form clips controls at 390px. Needs UI :5191 / API :5056.
import { start, UI, OUT } from "./k_uilib.mjs";
const { browser, page } = await start("admin", { viewport: { width: 390, height: 844 } });
await page.goto(UI + "/emissions?scope=scope1"); await page.waitForTimeout(9000);
const clipped = await page.evaluate(() => [...document.querySelectorAll("input, .dropdown-selected, .tier-selector-btn")]
  .filter(e => e.offsetParent).filter(e => e.getBoundingClientRect().right > window.innerWidth + 1).length);
await page.screenshot({ path: OUT + "bug108.png" });
console.log(`expected 0 controls beyond the 390px viewport; actual ${clipped}`);
await browser.close(); process.exit(clipped === 0 ? 0 : 1);
