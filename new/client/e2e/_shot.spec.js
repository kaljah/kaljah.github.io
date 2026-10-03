import { test } from "@playwright/test";
test("shot", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/" + (process.env.ROUTE || ""));
  await page.waitForTimeout(4000);
  if (process.env.SCROLL) await page.evaluate((y) => { document.querySelectorAll("*").forEach((el) => { if (el.scrollHeight > el.clientHeight + 200 && getComputedStyle(el).overflowY !== "visible") el.scrollTop = y; }); }, Number(process.env.SCROLL));
  await page.waitForTimeout(600);
  await page.screenshot({ path: process.env.SHOT, fullPage: process.env.FULL === "1" });
});
