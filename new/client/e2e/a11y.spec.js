import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// WCAG 2.0/2.1 A and AA scan of every page. Needs the dev server, the backend and storageState.json
// (see generate_storage_state.js). Zero serious or critical violations are allowed.
const ROUTES = [
  "/",
  "/carbon-intensity",
  "/methane-intensity",
  "/sbti",
  "/methane-explorer",
  "/emissions",
  "/emissions?scope=scope1",
  "/manage-data",
  "/reference-data",
  "/reports",
  "/uncertainty",
  "/qa-dashboard",
  "/audit-trail",
  "/settings",
];

for (const route of ROUTES) {
  test(`a11y ${route}`, async ({ page }) => {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
  });
}

test.describe("signed out", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("a11y /login", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
  });
});
