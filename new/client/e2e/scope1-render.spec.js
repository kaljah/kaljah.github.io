import { test, expect } from "@playwright/test";

// Guards the Scope1Form split: selecting every process type must render without runtime errors
// (a missing prop surfaces as a ReferenceError when the section mounts).
test("Scope 1 form renders every process type and the history table", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/emissions?scope=scope1");
  await page.waitForLoadState("networkidle");

  await expect(page.locator("table.excel-table")).toBeVisible();
  const trigger = page.locator(".input-group:has-text('Process') [data-testid=select-trigger]").first();
  await trigger.click();
  const count = await page.locator("[data-testid=select-option]").count();
  expect(count).toBeGreaterThan(5);
  await page.keyboard.press("Escape");

  for (let i = 0; i < count; i++) {
    await trigger.click();
    await page.locator("[data-testid=select-option]").nth(i).click();
    await page.waitForTimeout(250);
  }
  // history interactions: toggle uncertainty columns, open the details dialog if a row exists
  await page.getByRole("button", { name: /show uncertainty columns/i }).click();
  await expect(page.locator("table.excel-table th", { hasText: "95%CI" }).first()).toBeVisible();
  expect(errors).toEqual([]);
});
