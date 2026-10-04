import { test, expect } from "@playwright/test";

// Guards the section extractions: clicks every tab, radio and view toggle on each page and fails on
// any uncaught runtime error (a missing prop shows up as a ReferenceError when the section mounts).
const ROUTES = ["/settings", "/qa-dashboard", "/audit-trail", "/methane-intensity", "/carbon-intensity", "/", "/reports", "/uncertainty", "/reference-data", "/sbti"];

for (const route of ROUTES) {
  test(`smoke ${route}`, async ({ page }) => {
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800);
    const targets = page.locator("[role=tab], [role=radio]:not([aria-disabled=true]), button.settings-tab-btn, button.qa-tab-btn");
    const n = await targets.count();
    for (let i = 0; i < n; i++) {
      await targets.nth(i).click({ timeout: 4000 }).catch(() => {});
      await page.waitForTimeout(400);
    }
    // collapsible headers and clickable cards
    const toggles = page.locator("[role=button][tabindex='0']");
    const m = Math.min(await toggles.count(), 12);
    for (let i = 0; i < m; i++) {
      await toggles.nth(i).click({ timeout: 2000 }).catch(() => {});
      await page.waitForTimeout(250);
    }
    expect(errors).toEqual([]);
  });
}
