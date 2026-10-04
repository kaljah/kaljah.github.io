import { test, expect } from "@playwright/test";

// Regression test for a page stylesheet redefining global design tokens (the accent once turned teal
// after visiting Carbon Intensity until a full reload).
test("brand accent survives visiting Carbon and Methane Intensity", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  const accent = () => page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue("--accent-color").trim());
  expect((await accent()).toLowerCase()).toMatch(/^(#ff6600|#f60)$/);
  await page.getByRole("link", { name: "Carbon Intensity" }).click();
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: "Methane Intensity" }).click();
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: "Dashboard" }).click();
  await page.waitForLoadState("networkidle");
  expect((await accent()).toLowerCase()).toMatch(/^(#ff6600|#f60)$/);
});

test("shared filters persist across analytics pages and deep links", async ({ page }) => {
  await page.goto("/?year=2026");
  await page.waitForLoadState("networkidle");
  await page.getByRole("link", { name: "Carbon Intensity" }).click();
  await page.waitForLoadState("networkidle");
  await expect(page).toHaveURL(/year=2026/);
  // regression: the URL sync once navigated back to the route it was created on
  await page.waitForTimeout(2500);
  expect(new URL(page.url()).pathname).toBe("/carbon-intensity");
});
