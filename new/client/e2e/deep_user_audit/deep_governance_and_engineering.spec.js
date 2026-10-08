// @ts-check
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const BACKEND = 'http://127.0.0.1:5000';
const SCREENSHOT_DIR = path.resolve('e2e/deep_user_audit/screenshots');
const ARTIFACT_DIR = 'C:/Users/samsung/.gemini/antigravity/brain/145e1f58-77e7-4f5b-8573-5a1c4dc13171';

function copyArtifact(filename) {
  try {
    const src = path.join(SCREENSHOT_DIR, filename);
    const dest = path.join(ARTIFACT_DIR, filename);
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dest);
    }
  } catch (err) {
    console.error(`Failed to copy artifact ${filename}:`, err.message);
  }
}

async function ensureAuthenticatedPage(page, targetUrl = '/') {
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(800);

  // Dismiss intro overlay if present
  const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
  if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipBtn.click();
    await page.waitForTimeout(400);
  }
  await page.locator('.login-intro-overlay').waitFor({ state: 'detached', timeout: 3000 }).catch(() => {});

  // Fallback login if unauthenticated
  const emailInput = page.locator('input[placeholder="Email Address"]');
  if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await emailInput.fill('a');
    await page.locator('input[type="password"]').fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000);
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1000);
  }

  await expect(page.locator('.app-container, .main-content, #main').first()).toBeVisible({ timeout: 20000 });
  await page.waitForLoadState('networkidle').catch(() => {});
}

test.describe.serial('Suite 9: Advanced Engineering, Governance & Enterprise Operations', () => {

  test.beforeAll(async () => {
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  // -------------------------------------------------------------------------
  // TEST 1: Tier 2 Custom Emission Factor Registration via QuickAdd Modal
  // -------------------------------------------------------------------------
  test('GOV-1: Tier 2 Custom Emission Factor Registration via QuickAdd Modal', async ({ page }) => {
    console.log('[E2E GOV] Navigating to Emissions Hub Scope 1 (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Switch to Library factor mode
    console.log('[E2E GOV] Switching to Library factor tier...');
    const libraryBtn = page.locator('button.tier-selector-btn:has-text("Library factor")');
    await expect(libraryBtn).toBeVisible({ timeout: 15000 });
    await libraryBtn.click();
    await page.waitForTimeout(800);

    // Open Quick Add Modal
    console.log('[E2E GOV] Triggering QuickAdd modal via "New library factor"...');
    const newFactorBtn = page.locator('button:has-text("New library factor")');
    await expect(newFactorBtn).toBeVisible();
    await newFactorBtn.click();
    await page.waitForTimeout(800);

    // Verify modal header
    const modalHeader = page.locator('h3:has-text("Register Tier 2 Custom Factor")');
    await expect(modalHeader).toBeVisible();

    // Fill Custom Factor Form
    const uniqueTs = Date.now();
    const testFactorName = `Skikda Light Refinery Gas 2026-${uniqueTs}`;

    console.log(`[E2E GOV] Filling custom factor form for ${testFactorName}...`);
    await page.locator('input[placeholder*="Hassi R\'Mel Fuel Gas"]').fill(testFactorName);
    
    // Units
    const unitSelect = page.locator('.modal-card select.mole-input, .modal-card select').first();
    await unitSelect.selectOption('kg/MMBtu');

    // CO2 Factor
    await page.locator('input[placeholder="e.g. 53.06"]').fill('54.85');

    // CH4 Factor
    await page.locator('input[placeholder="e.g. 0.001"]').fill('0.0018');

    // N2O Factor
    await page.locator('input[placeholder="e.g. 0.0001"]').fill('0.0001');

    // Uncertainty
    await page.locator('input[placeholder="7.0"]').fill('4.8');

    // Source
    await page.locator('input[placeholder*="Sonatrach Analysis Certificate"]').fill('ISO 17025 Certified GC-2026-SKIKDA');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'gov01_quickadd_factor_created.png') });
    copyArtifact('gov01_quickadd_factor_created.png');
    console.log('[E2E GOV] Captured gov01_quickadd_factor_created.png.');

    // Submit Modal
    console.log('[E2E GOV] Submitting QuickAdd modal...');
    await page.locator('button[type="submit"]:has-text("Save & Apply Factor")').click();

    // Verify toast
    const successToast = page.locator('text=Tier 2 custom factor registered successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E GOV] Verified "Tier 2 custom factor registered successfully" notification.');

    await page.waitForTimeout(1000);
  });

  // -------------------------------------------------------------------------
  // TEST 2: Custom Emission Factors Management & ISO 14064-1 Uncertainty Workbench
  // -------------------------------------------------------------------------
  test('GOV-2: Custom Emission Factors Management & ISO 14064-1 Uncertainty Workbench (/manage-data?tab=factors)', async ({ page }) => {
    console.log('[E2E GOV] Navigating to Custom Factors Registry (/manage-data?tab=factors)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=factors`);
    await page.waitForTimeout(1500);

    // Verify Tab Header
    const factorsHeader = page.locator('h2:has-text("Custom Emission Factors")');
    await expect(factorsHeader).toBeVisible({ timeout: 15000 });

    // Verify EF Uncertainty Workbench section
    console.log('[E2E GOV] Verifying EF Uncertainty Workbench (ISO 14064-1 compliant)...');
    const workbenchHeader = page.locator('h4:has-text("EF Uncertainty Workbench")');
    await expect(workbenchHeader).toBeVisible();

    // Interact with workbench inputs
    const meterInput = page.locator('.input-group:has-text("Meter Precision") input');
    await meterInput.fill('1.8');

    const labInput = page.locator('.input-group:has-text("Lab Analysis") input');
    await labInput.fill('2.4');

    // Click Calculate Combined Uncertainty (SRSS)
    const calcSrssBtn = page.locator('button:has-text("Calculate Combined Uncertainty")');
    await calcSrssBtn.click();
    await page.waitForTimeout(500);
    console.log('[E2E GOV] Computed SRSS Combined Uncertainty.');

    // Fill Custom Factor Form on page
    const uniqueTs = Date.now();
    const factorName = `Laghouat Field Gas Blend-${uniqueTs}`;

    console.log(`[E2E GOV] Adding new custom factor via main form: ${factorName}...`);
    await page.locator('input[name="factor_name"]').fill(factorName);
    await page.locator('select[name="parent_fuel"]').selectOption('Natural Gas');
    await page.locator('select[name="unit"]').selectOption('m³');
    await page.locator('input[name="co2_factor"]').fill('1.985');
    await page.locator('input[name="ch4_factor"]').fill('0.00035');
    await page.locator('input[name="n2o_factor"]').fill('0.00002');
    await page.locator('input[name="source"]').fill('Sonatrach Central Gas Lab Report #2026-LGH-09');
    await page.locator('textarea[name="description"]').fill('Field gas blend for upstream separation and booster compression.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'gov02_factors_registry_workbench.png') });
    copyArtifact('gov02_factors_registry_workbench.png');
    console.log('[E2E GOV] Captured gov02_factors_registry_workbench.png.');

    // Save Factor
    console.log('[E2E GOV] Saving custom factor via Save Factor button...');
    await page.locator('button.action-btn:has-text("Save Factor")').click();

    // Verify toast
    const successToast = page.locator('text=Factor added!').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E GOV] Verified "Factor added!" notification.');

    // Verify row in custom factors table
    await page.waitForTimeout(1000);
    const factorRow = page.locator(`table.data-table tbody tr:has-text("${factorName}")`).first();
    await expect(factorRow).toBeVisible({ timeout: 10000 });
    console.log('[E2E GOV] Verified factor rendered in custom factors table.');
  });

  // -------------------------------------------------------------------------
  // TEST 3: GHG Protocol Base Year Recalculation & Corporate Targets
  // -------------------------------------------------------------------------
  test('GOV-3: GHG Protocol Base Year Recalculation & Corporate Targets (/manage-data?tab=goals)', async ({ page }) => {
    console.log('[E2E GOV] Navigating to Goals & Base Years (/manage-data?tab=goals)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=goals`);
    await page.waitForTimeout(1500);

    // 1. Verify Active Baseline Banner
    const baselineBanner = page.locator('text=Current Base Year:').first();
    await expect(baselineBanner).toBeVisible({ timeout: 15000 });
    console.log('[E2E GOV] Active Baseline Banner verified.');

    // 2. Set Yearly Emission Goal
    console.log('[E2E GOV] Creating new Yearly Corporate Emission Goal...');
    const goalYearInput = page.locator('.grid-forms:has-text("Target Year") input[type="number"]').first();
    await goalYearInput.fill('2034');

    const goalAmountInput = page.locator('.grid-forms:has-text("Target Emission Amount") input').nth(1);
    await goalAmountInput.fill('315000');

    await page.locator('button.action-btn:has-text("Save Goal")').click();

    const goalToast = page.locator('text=Emission goal saved!').first();
    await expect(goalToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E GOV] Verified "Emission goal saved!" notification.');

    // Verify goal in table
    await page.waitForTimeout(800);
    const goalRow = page.locator('table.data-table tbody tr:has-text("2034")').first();
    await expect(goalRow).toBeVisible();
    await expect(goalRow).toContainText('315,000');
    console.log('[E2E GOV] Verified 2034 goal (315,000 tCO2e) in goals table.');

    // 3. Document Base Year Recalculation
    console.log('[E2E GOV] Logging GHG Protocol §5 Base Year Recalculation...');
    const baseYearForm = page.locator('.grid-forms:has-text("Prev. Emissions")');
    await baseYearForm.locator('input[placeholder*="2023"]').fill('2024');
    await baseYearForm.locator('input[placeholder="Optional"]').first().fill('520000');
    await baseYearForm.locator('input[placeholder="Optional"]').nth(1).fill('485000');
    await baseYearForm.locator('textarea').fill('Methodology update: Re-baselined upstream flaring with Tier 3 combustion formulas and updated IPCC AR6 GWP horizon.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'gov03_base_year_recalculation_goals.png') });
    copyArtifact('gov03_base_year_recalculation_goals.png');
    console.log('[E2E GOV] Captured gov03_base_year_recalculation_goals.png.');

    await page.locator('button.action-btn:has-text("Save Recalculation")').click();

    const recalcToast = page.locator('text=Base year recalculation recorded successfully!').first();
    await expect(recalcToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E GOV] Verified "Base year recalculation recorded successfully!" notification.');

    // Verify row in recalculation history table
    await page.waitForTimeout(800);
    const recalcRow = page.locator('table.data-table tbody tr:has-text("2024")').first();
    await expect(recalcRow).toBeVisible();
    await expect(recalcRow).toContainText('Active');
    await expect(recalcRow).toContainText('-35,000');
    console.log('[E2E GOV] Verified base year recalculation entry with Active badge and -35,000 tCO2e delta.');
  });

  // -------------------------------------------------------------------------
  // TEST 4: Operational Region & Geospatial Facility Boundary Management
  // -------------------------------------------------------------------------
  test('GOV-4: Operational Region & Geospatial Facility Boundary Management (/manage-data?tab=facilities)', async ({ page }) => {
    console.log('[E2E GOV] Navigating to Facilities & Regions (/manage-data?tab=facilities)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=facilities`);
    await page.waitForTimeout(1500);

    // Verify Tab Title
    const facHeader = page.locator('text=Active Regions').first();
    await expect(facHeader).toBeVisible({ timeout: 15000 });

    const uniqueTs = Date.now();
    const facilityName = `Gassi Touil Gas Complex-${uniqueTs}`;

    console.log(`[E2E GOV] Registering new operational facility: ${facilityName}...`);
    await page.locator('input[name="name"]').fill(facilityName);
    await page.locator('select[name="activity"]').selectOption('EP');
    await page.waitForTimeout(400);

    await page.locator('select[name="division"]').selectOption('Production');
    await page.locator('input[name="field"]').fill('Gassi Touil Central');
    await page.locator('input[name="location"]').fill('Ouargla');
    await page.locator('select[name="boundary_type"]').selectOption('Operational Control');
    await page.waitForTimeout(400);
    await page.locator('select[name="boundary_detail"]').selectOption('Wholly Owned');
    await page.locator('select[name="segment"]').selectOption('Upstream');
    await page.locator('input[name="latitude"]').fill('31.425');
    await page.locator('input[name="longitude"]').fill('6.852');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'gov04_facility_boundary_provisioned.png') });
    copyArtifact('gov04_facility_boundary_provisioned.png');
    console.log('[E2E GOV] Captured gov04_facility_boundary_provisioned.png.');

    // Submit Add Region
    console.log('[E2E GOV] Submitting Add Region form...');
    await page.locator('button:has-text("Add Region")').click();

    // Verify toast
    const successToast = page.locator('text=Region added!').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E GOV] Verified "Region added!" notification.');

    // Verify row in Active Regions table
    await page.waitForTimeout(1000);
    const regionRow = page.locator(`table tbody tr:has-text("${facilityName}")`).first();
    await expect(regionRow).toBeVisible({ timeout: 10000 });
    await expect(regionRow).toContainText('Exploration & Production');
    await expect(regionRow).toContainText('Operational Control');
    console.log('[E2E GOV] Verified new operational region registered with coordinates and control boundaries.');
  });

  // -------------------------------------------------------------------------
  // TEST 5: Enterprise GWP Standard & Regulatory Compliance Settings
  // -------------------------------------------------------------------------
  test('GOV-5: Enterprise GWP Standard & Regulatory Compliance Settings (/settings)', async ({ page }) => {
    console.log('[E2E GOV] Navigating to Settings & Protocols (/settings)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/settings`);
    await page.waitForTimeout(1500);

    // Verify Header
    const settingsHeader = page.locator('h1:has-text("System Settings & Protocols")');
    await expect(settingsHeader).toBeVisible({ timeout: 15000 });

    // Verify Tabs
    const gwpTab = page.locator('[role="tab"]:has-text("GWP Standards"), [role="tab"]:has-text("Standards")').first();
    await expect(gwpTab).toBeVisible();

    // Switch to OGMP 2.0 Tab
    console.log('[E2E GOV] Navigating to OGMP 2.0 Framework tab...');
    const ogmpTab = page.locator('[role="tab"]:has-text("OGMP 2.0"), button:has-text("OGMP 2.0")').first();
    await ogmpTab.click();
    await page.waitForTimeout(600);

    // Select baseline year
    const yrBtn = page.locator('button:has-text("2024")').first();
    if (await yrBtn.isVisible()) {
      await yrBtn.click();
      await page.waitForTimeout(400);
      console.log('[E2E GOV] Selected 2024 baseline year.');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'gov05_settings_global_configuration.png') });
    copyArtifact('gov05_settings_global_configuration.png');
    console.log('[E2E GOV] Captured gov05_settings_global_configuration.png.');

    // Save All Changes
    console.log('[E2E GOV] Triggering Save All Changes...');
    const saveBtn = page.locator('#save-settings-btn, button:has-text("Save All Changes")');
    await expect(saveBtn).toBeVisible();
    await saveBtn.click();

    // Verify toast
    const successToast = page.locator('text=System settings and Copernicus credentials saved successfully!').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E GOV] Verified "System settings and Copernicus credentials saved successfully!" notification.');
  });

  // -------------------------------------------------------------------------
  // TEST 6: Inline Emission Record Modification & Maker-Checker Quarantine
  // -------------------------------------------------------------------------
  test('GOV-6: Inline Emission Record Modification & Maker-Checker Quarantine (/reports -> EditEmissionModal)', async ({ page }) => {
    console.log('[E2E GOV] Navigating to Reports (/reports)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/reports`);
    await page.waitForTimeout(1500);

    // Locate first Edit button in audit table
    const editBtn = page.locator('table button:has-text("Edit")').first();
    await expect(editBtn).toBeVisible({ timeout: 15000 });
    console.log('[E2E GOV] Clicking Edit button on emission record...');
    await editBtn.click();
    await page.waitForTimeout(800);

    // Verify Edit Emission Modal
    const modalTitle = page.locator('text=Edit Emission Record #').first();
    await expect(modalTitle).toBeVisible();
    console.log('[E2E GOV] Edit Emission Record modal successfully opened.');

    // Update Activity Quantity
    const amountInput = page.locator('input[placeholder="0.00"]').first();
    await expect(amountInput).toBeVisible();
    const currentAmount = await amountInput.inputValue();
    const newAmount = (parseFloat(currentAmount || '100') + 25.5).toFixed(2);
    await amountInput.fill(newAmount);
    console.log(`[E2E GOV] Modified activity quantity from ${currentAmount} to ${newAmount}.`);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'gov06_edit_emission_modal.png') });
    copyArtifact('gov06_edit_emission_modal.png');
    console.log('[E2E GOV] Captured gov06_edit_emission_modal.png.');

    // Submit Changes
    console.log('[E2E GOV] Submitting edited emission record...');
    await page.locator('button:has-text("Save Changes")').click();

    // Verify notification of return to Pending Review
    const successToast = page.locator('text=Record returned to Pending review for verification').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E GOV] Verified record quarantine notice to Pending Review.');

    // Verify record in Pending Review queue
    console.log('[E2E GOV] Navigating to /manage-data?tab=pending to verify quarantine queue...');
    await page.goto(`${FRONTEND}/manage-data?tab=pending`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);

    const pendingRow = page.locator(`table tbody tr:has-text("${newAmount}")`).first();
    if (await pendingRow.isVisible().catch(() => false)) {
      console.log('[E2E GOV] Confirmed edited record present in Pending Review table!');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'gov06_record_returned_to_pending.png') });
    copyArtifact('gov06_record_returned_to_pending.png');
    console.log('[E2E GOV] Captured gov06_record_returned_to_pending.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 7: Real-Time TopBar Notification Center & Alert Management
  // -------------------------------------------------------------------------
  test('GOV-7: Real-Time TopBar Notification Center & Alert Inbox', async ({ page }) => {
    console.log('[E2E GOV] Navigating to Dashboard to test TopBar Notification Center...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/`);
    await page.waitForTimeout(1200);

    // Locate Notification Bell
    console.log('[E2E GOV] Locating Notification Center Bell button in sticky TopBar...');
    const bellBtn = page.locator('button[title="Notifications"]').first();
    await expect(bellBtn).toBeVisible({ timeout: 10000 });

    // Open Notification Tray
    console.log('[E2E GOV] Opening Notification Tray...');
    await bellBtn.click();
    await page.waitForTimeout(600);

    // Verify Notification Panel is rendered
    const notifHeader = page.locator('text=Notifications').first();
    await expect(notifHeader).toBeVisible();
    console.log('[E2E GOV] Notification Tray panel confirmed open.');

    // Check for "Mark read" or "Clear all" buttons if notifications exist
    const markReadBtn = page.locator('button:has-text("Mark read")');
    if (await markReadBtn.isVisible().catch(() => false)) {
      console.log('[E2E GOV] Triggering "Mark read"...');
      await markReadBtn.click();
      await page.waitForTimeout(500);
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'gov07_notification_center_tray.png') });
    copyArtifact('gov07_notification_center_tray.png');
    console.log('[E2E GOV] Captured gov07_notification_center_tray.png.');

    // Close panel with Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    console.log('[E2E GOV] Notification panel closed successfully.');
  });

});
