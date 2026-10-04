import { test } from "@playwright/test";
import fs from "node:fs";

// Before/after screenshots for UI work. Run with: npx playwright test --grep @baseline
// Output goes to e2e/artifacts/baseline/<label>/ (git-ignored). Set BASELINE_LABEL=before|after.
const LABEL = process.env.BASELINE_LABEL || "current";
const SIZES = [
  { name: "1440", width: 1440, height: 900 },
  { name: "1024", width: 1024, height: 768 },
  { name: "390", width: 390, height: 844 },
];
const ROUTES = [
  ["dashboard", "/"],
  ["carbon-intensity", "/carbon-intensity"],
  ["methane-intensity", "/methane-intensity"],
  ["sbti", "/sbti"],
  ["emissions-map", "/methane-explorer"],
  ["calculations", "/emissions"],
  ["calculations-scope1", "/emissions?scope=scope1"],
  ["manage-data", "/manage-data"],
  ["reference-data", "/reference-data"],
  ["reports", "/reports"],
  ["uncertainty", "/uncertainty"],
  ["qa", "/qa-dashboard"],
  ["audit-trail", "/audit-trail"],
  ["settings", "/settings"],
];

test.describe("@baseline", () => {
  for (const size of SIZES) {
    for (const [name, route] of ROUTES) {
      test(`${name} @${size.name}`, async ({ page }) => {
        await page.setViewportSize({ width: size.width, height: size.height });
        await page.goto(route);
        await page.waitForLoadState("networkidle");
        await page.waitForTimeout(2000); // chart animations
        const dir = `e2e/artifacts/baseline/${LABEL}`;
        fs.mkdirSync(dir, { recursive: true });
        await page.screenshot({
          path: `${dir}/${name}-${size.name}.png`,
          fullPage: true,
          animations: "disabled",
          // time-dependent text
          mask: [page.getByText(/Updated \d|ago$/)],
        });
      });
    }
  }
});
