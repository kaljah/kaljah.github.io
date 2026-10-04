import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Accessibility scan of the import wizards while they are open.
const scan = async (page) => {
  await page.waitForTimeout(800);
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
  expect(blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
};

test("a11y Manage Data bulk import wizard", async ({ page }) => {
  await page.goto("/manage-data");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: /Bulk Import/ }).first().click();
  await scan(page);
});

test("a11y Scope 1 bulk import wizard", async ({ page }) => {
  await page.goto("/emissions?scope=scope1");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: /Bulk Import \(Wizard\)/ }).click();
  await scan(page);
});

test("a11y custom factor create form (Manage Data) and Scope 2 / Scope 3 forms", async ({ page }) => {
  for (const url of ["/emissions?scope=scope2", "/emissions?scope=scope3"]) {
    await page.goto(url);
    await page.waitForLoadState("networkidle");
    await scan(page);
  }
});
