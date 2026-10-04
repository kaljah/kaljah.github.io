import { test } from "@playwright/test";
import fs from "node:fs";

// Scratch probe: dumps geometry and key computed styles for interactive states (tabs, menus, dialogs, forms).
// Run against two builds with the same PROBE_DIR layout and diff the output.
const dumpPage = async (page, name) => {
  await page.waitForTimeout(700);
  const rows = await page.evaluate(() => {
    const props = ["fontFamily", "fontSize", "fontWeight", "letterSpacing", "lineHeight", "color", "paddingTop", "paddingLeft", "marginTop", "display", "backgroundColor", "borderBottomWidth", "borderTopWidth", "boxShadow", "borderRadius"];
    const out = [];
    document.querySelectorAll("body *").forEach((el, i) => {
      const cs = getComputedStyle(el);
      const rect = el.getBoundingClientRect();
      const cls = (typeof el.className === "string" ? el.className : "").split(/\s+/)[0].slice(0, 40);
      out.push([i, el.tagName, cls, Math.round(rect.x), Math.round(rect.y), Math.round(rect.width), Math.round(rect.height), ...props.map((p) => cs[p])].join("|"));
    });
    return out;
  });
  fs.writeFileSync(`${process.env.PROBE_DIR}/${name}.txt`, rows.join("\n"));
};

const safe = async (fn) => {
  try {
    await fn();
  } catch {
    // state not reachable in this build: the missing dump is itself a difference
  }
};

const clickAndDump = async (page, role, name, file) =>
  safe(async () => {
    await page.getByRole(role, { name }).first().click();
    await dumpPage(page, file);
  });

const visit = async (page, route) => {
  await page.goto(`/${route}`);
  await page.waitForTimeout(1500);
};

test("probe states", async ({ page }) => {
  test.setTimeout(900000);
  page.setDefaultTimeout(5000);
  fs.mkdirSync(process.env.PROBE_DIR, { recursive: true });
  await page.setViewportSize({ width: 1440, height: 900 });

  await visit(page, "manage-data");
  const MD = ["Pending Review", "Emission Factors", "Regions", "Production Data", "Emission Sources", "Emission Goals & Base Years", "Mitigation Projects", "OGMP 2.0 Surveys", "CBAM Products"];
  for (const [i, n] of MD.entries()) await clickAndDump(page, "button", new RegExp(n.replace(/[&.]/g, ".")), `md-${i}`);

  await visit(page, "settings");
  for (const [i, n] of ["IPCC", "OGMP 2.0", "Facility Overrides", "Copernicus"].entries()) await clickAndDump(page, "tab", new RegExp(n), `settings-${i}`);

  await visit(page, "qa-dashboard");
  for (const [i, n] of ["Anomaly", "Health", "Uncertainty"].entries()) await clickAndDump(page, "tab", new RegExp(n), `qa-tab-${i}`);
  await visit(page, "qa-dashboard");
  for (const [i, n] of ["Pending Review", "Verified", "Rejected"].entries()) await clickAndDump(page, "button", new RegExp(n), `qa-filter-${i}`);

  await visit(page, "audit-trail");
  await clickAndDump(page, "radio", /Timeline/, "audit-timeline");
  await visit(page, "audit-trail");
  await clickAndDump(page, "button", /^Details/, "audit-details");

  for (const sc of ["scope2", "scope3"]) {
    await visit(page, `emissions?scope=${sc}`);
    await dumpPage(page, `emissions-${sc}`);
  }

  await visit(page, "emissions?scope=scope1");
  await safe(async () => {
    const trigger = page.locator(".input-group:has-text('Process') [data-testid=select-trigger]").first();
    await trigger.click();
    const count = await page.locator("[data-testid=select-option]").count();
    await page.keyboard.press("Escape");
    for (let i = 0; i < count; i++) {
      await trigger.click();
      await page.locator("[data-testid=select-option]").nth(i).click();
      await dumpPage(page, `scope1-${i}`);
    }
  });

  await visit(page, "reports");
  await clickAndDump(page, "button", /^Export/, "reports-export");
  await visit(page, "reports");
  await clickAndDump(page, "button", /Columns/, "reports-columns");

  await visit(page, "sbti");
  await clickAndDump(page, "radio", /operational/, "sbti-radio");
  await clickAndDump(page, "button", /Configure target/, "sbti-dialog");

  await visit(page, "");
  await clickAndDump(page, "button", /Set Target/, "dash-target");
  await visit(page, "");
  await clickAndDump(page, "radio", /GWP-20/, "dash-gwp20");
  await clickAndDump(page, "button", /Detailed Breakdown/, "dash-detailed");
  await clickAndDump(page, "button", /Compare Regions/, "dash-compare");

  await visit(page, "carbon-intensity");
  await clickAndDump(page, "radio", /AR5 20/, "carbon-gwp20");
  await clickAndDump(page, "button", /Heatmap/, "carbon-heatmap");

  await visit(page, "methane-intensity");
  await clickAndDump(page, "button", /Heatmap/, "methane-heatmap");
  await clickAndDump(page, "button", /2024/, "methane-2024");
  await clickAndDump(page, "button", /OGMP 2.0 Level 4/, "methane-level");

  await visit(page, "methane-explorer");
  for (const [i, n] of ["Total GHG", "Super-Emitters", "Moderate", "Baseline"].entries()) await clickAndDump(page, "button", new RegExp(n), `explorer-${i}`);

  await visit(page, "reference-data");
  for (let i = 0; i < 11; i++) {
    await safe(async () => {
      await page.locator("main button").nth(i).click();
      await dumpPage(page, `refdata-${i}`);
    });
  }

  await visit(page, "uncertainty");
  await dumpPage(page, "uncertainty");

  await visit(page, "user-management");
  await dumpPage(page, "usermgmt");

  await visit(page, "");
  await safe(async () => {
    await page.keyboard.press("Control+k");
    await dumpPage(page, "palette");
  });
  await safe(async () => {
    await page.getByRole("button", { name: /Account menu/ }).click();
    await dumpPage(page, "account-menu");
  });

  // login screen as a signed-out visitor
  const ctx = await page.context().browser().newContext({ viewport: { width: 1440, height: 900 }, baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:5173" });
  const anon = await ctx.newPage();
  await anon.goto("/login");
  await anon.waitForTimeout(1500);
  await dumpPage(anon, "login");
  await ctx.close();
});
