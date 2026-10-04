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
    // let the runtime label linker (utils/a11yLabels.js) finish before scanning
    await page.waitForTimeout(800);
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

// The IT-role page needs an IT account: set E2E_IT_EMAIL and E2E_IT_PASSWORD (for example by seeding the
// backend with IT_ADMIN_EMAIL / IT_ADMIN_PASSWORD against a throwaway database). Skipped otherwise.
test.describe("IT role", () => {
  test.use({ storageState: { cookies: [], origins: [] } });
  test.skip(!process.env.E2E_IT_EMAIL || !process.env.E2E_IT_PASSWORD, "set E2E_IT_EMAIL and E2E_IT_PASSWORD");

  test("a11y /user-management", async ({ page }) => {
    await page.goto("/login");
    await page.locator('input[placeholder="Email Address"]').fill(process.env.E2E_IT_EMAIL);
    await page.locator('input[type="password"]').fill(process.env.E2E_IT_PASSWORD);
    await page.locator('button[type="submit"]').click();
    await page.waitForURL((u) => !u.toString().includes("/login"));
    await page.goto("/user-management");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1200);
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    const blocking = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(blocking.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(" | ")}`)).toEqual([]);
  });
});
