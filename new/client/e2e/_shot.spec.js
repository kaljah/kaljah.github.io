import { test } from "@playwright/test";
test("shot", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/methane-explorer");
  await page.waitForTimeout(3000);
  await page.getByLabel("Region / basin").selectOption("all").catch(() => {});
  await page.getByLabel("Activity type").selectOption("all").catch(() => {});
  await page.waitForTimeout(800);
  const card = page.locator("[aria-pressed]").first();
  if (await card.count()) { await card.click(); await page.waitForTimeout(2500); }
  await page.screenshot({ path: process.env.SHOT });
});
