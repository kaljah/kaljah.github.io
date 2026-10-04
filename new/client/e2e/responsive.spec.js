import { test, expect } from "@playwright/test";

// No page may scroll horizontally at phone width, and the top bar must not overlap its own controls.
const ROUTES = [
  "/", "/carbon-intensity", "/methane-intensity", "/sbti", "/methane-explorer", "/emissions",
  "/emissions?scope=scope1", "/manage-data", "/reference-data", "/reports", "/uncertainty",
  "/qa-dashboard", "/audit-trail", "/settings",
];

test.use({ viewport: { width: 390, height: 844 } });

for (const route of ROUTES) {
  test(`no horizontal overflow ${route}`, async ({ page }) => {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800);
    const m = await page.evaluate(() => {
      const crumb = document.querySelector("nav[aria-label=Breadcrumb]")?.getBoundingClientRect();
      const search = document.querySelector("header button[aria-label=Search]")?.getBoundingClientRect();
      return {
        doc: document.documentElement.scrollWidth,
        win: window.innerWidth,
        crumbRight: crumb ? Math.round(crumb.right) : 0,
        searchLeft: search ? Math.round(search.left) : 9999,
      };
    });
    expect(m.doc).toBeLessThanOrEqual(m.win);
    expect(m.crumbRight).toBeLessThanOrEqual(m.searchLeft);
  });
}
