import { test, expect } from "@playwright/test";

// Guards the ManageData split: every tab must render without a runtime error (a missing prop shows up
// as a ReferenceError the moment the tab mounts).
const TABS = [
  "Pending Review",
  "Emission Factors",
  "Regions",
  "Production Data",
  "Emission Sources",
  "Emission Goals & Base Years",
  "Mitigation Projects",
  "OGMP 2.0 Surveys",
  "CBAM Products",
];

test("every Manage Data tab renders without page errors", async ({ page }) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => {
    if (m.type() === "error" && /is not defined|Cannot read|undefined is not/.test(m.text())) errors.push(m.text());
  });
  await page.goto("/manage-data");
  await page.waitForLoadState("networkidle");
  for (const name of TABS) {
    const tab = page.getByRole("button", { name: new RegExp(name.replace(/[&.]/g, ".")) }).first();
    await tab.click();
    await expect(tab).toHaveAttribute("aria-current", "page");
    await page.waitForTimeout(600);
  }
  expect(errors).toEqual([]);
});
