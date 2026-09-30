import { start, OUT, UI } from "./lib.mjs";
const { browser, page } = await start("admin");
await page.goto(UI + "/emissions?scope=scope1"); await page.waitForTimeout(9000);
await page.locator(".tier-selector-btn").first().focus();
await page.locator('input[placeholder="e.g. West Facility"]').focus();
const seq = [];
for (let i = 0; i < 12; i++) {
  seq.push(await page.evaluate(() => { const e = document.activeElement; return e.tagName + (e.className ? "." + String(e.className).split(" ")[0] : "") + (e.placeholder ? "[" + e.placeholder + "]" : "") + (e.innerText ? "{" + e.innerText.slice(0, 20).replace(/\s+/g, " ") + "}" : ""); }));
  await page.keyboard.press("Tab");
}
console.log(seq.join("\n"));
const regionFocusable = await page.locator(".dropdown-selected", { hasText: "Select Region" }).evaluate(e => ({ tabIndex: e.tabIndex, role: e.getAttribute("role"), aria: e.getAttribute("aria-haspopup") }));
console.log("Region dropdown:", JSON.stringify(regionFocusable));
await browser.close();
