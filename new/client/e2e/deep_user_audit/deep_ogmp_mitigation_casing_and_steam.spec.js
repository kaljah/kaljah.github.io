import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const SCREENSHOT_DIR = path.resolve('e2e/deep_user_audit/screenshots');
const BRAIN_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\145e1f58-77e7-4f5b-8573-5a1c4dc13171';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function copyArtifact(filename) {
  try {
    const src = path.join(SCREENSHOT_DIR, filename);
    const dst = path.join(BRAIN_DIR, filename);
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dst);
      console.log(`[ARTIFACT] Copied ${filename} to brain dir.`);
    }
  } catch (err) {
    console.warn(`[WARN] Failed to copy artifact ${filename}:`, err);
  }
}

async function ensureAuthenticatedPage(page, targetUrl) {
  await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(800);

  const emailInput = page.locator('input[placeholder="Email Address"]').first();
  if (await emailInput.isVisible().catch(() => false)) {
    console.log('[E2E OMS] Performing authentication login as Admin...');
    await emailInput.fill('a');
    const pwdInput = page.locator('input[type="password"]').first();
    await pwdInput.fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForTimeout(1000);
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000);
  }

  if (targetUrl) {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
  }
}

test.describe('Suite 19: OGMP Surveys, Mitigation, Casing Gas & Steam Cogeneration Deep Audit', () => {

  test('OMS-1: OGMP 2.0 Level 4 & 5 Top-Down Survey Registration', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=ogmp`);

    // Verify Tab Header
    await expect(page.locator('text=OGMP 2.0 Level 4 & 5 Top-Down / Bottom-Up Surveys').first()).toBeVisible({ timeout: 15000 });
    console.log('[OMS-1] OGMP Survey tab loaded.');

    // Activity Select
    const actSelect = page.locator('select.component-select').nth(0);
    await actSelect.selectOption('EP');
    await page.waitForTimeout(400);

    // Division Select
    const divSelect = page.locator('select.component-select').nth(1);
    await divSelect.selectOption({ index: 1 });
    await page.waitForTimeout(400);

    // Facility Select
    const facSelect = page.locator('select.component-select').nth(2);
    await facSelect.selectOption({ index: 1 });
    await page.waitForTimeout(400);

    // Survey Date Input
    const dateInput = page.locator('.form-grid-3 input[type="date"]').first();
    await dateInput.fill('2024-05-15');

    // Measurement Technology Select
    const techSelect = page.locator('select.component-select').nth(3);
    await techSelect.selectOption('Drone / UAV LiDAR Scanning');
    await page.waitForTimeout(400);

    // Measured Emission Rate
    const rateInput = page.locator('.form-grid-3 input[placeholder="0.0"]').first();
    await rateInput.fill('18.5');

    // Reconciliation Status
    const reconSelect = page.locator('select.component-select').nth(4);
    await reconSelect.selectOption('Discrepancy Detected');

    // Operator Notes
    const notesInput = page.locator('.form-grid-3 input[placeholder*="Wind speed"]').first();
    await notesInput.fill('Aerial campaign pass #3 over North manifold headers; wind 4.2 m/s NW');
    await page.waitForTimeout(400);

    // Save OGMP Survey Record
    const saveBtn = page.locator('button.action-btn:has-text("Save OGMP Survey")').first();
    await saveBtn.click();
    console.log('[OMS-1] Clicked Save OGMP Survey button.');
    await page.waitForTimeout(1800);

    // Verify Row in Survey Table
    const surveyRow = page.locator('table.data-table tbody tr:has-text("18.5")').first();
    await expect(surveyRow).toBeVisible({ timeout: 8000 });
    console.log('[OMS-1] OGMP survey record confirmed in table.');

    const shotPath = path.join(SCREENSHOT_DIR, 'oms01_ogmp_survey_topdown_registered.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('oms01_ogmp_survey_topdown_registered.png');
  });

  test('OMS-2: Corporate Decarbonization Mitigation Project Registration', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=mitigation`);

    // Verify Tab Header
    await expect(page.locator('text=Mitigation Projects').first()).toBeVisible({ timeout: 15000 });
    console.log('[OMS-2] Mitigation tab loaded.');

    // Activity Select
    const actSelect = page.locator('select.component-select').nth(0);
    await actSelect.selectOption('EP');
    await page.waitForTimeout(400);

    // Division Select
    const divSelect = page.locator('select.component-select').nth(1);
    await divSelect.selectOption({ index: 1 });
    await page.waitForTimeout(400);

    // Region Dropdown
    const regDropdown = page.locator('.grid-forms button.dropdown-selected').first();
    await regDropdown.click();
    await page.waitForTimeout(400);
    const regOpt = page.locator('[role="option"]').nth(1);
    await regOpt.click();
    await page.waitForTimeout(400);

    // Project Name
    const nameInput = page.locator('input[placeholder*="Flare Reduction Unit"]').first();
    await nameInput.fill('In Salah Industrial Carbon Capture & Storage (CCUS Phase II)');

    // Year
    const yrInput = page.locator('.grid-forms input[type="number"]').first();
    await yrInput.fill('2024');

    // Type Select
    const typeSelect = page.locator('select.component-select').nth(2);
    await typeSelect.selectOption('CCUS');

    // Quantity (tCO2e)
    const qtyInput = page.locator('input[placeholder="0.0"]').first();
    await qtyInput.fill('85000');

    // Status Select
    const statusSelect = page.locator('select.component-select').nth(3);
    await statusSelect.selectOption('Active');
    await page.waitForTimeout(400);

    // Click Save Record
    const saveBtn = page.locator('button.action-btn:has-text("Save Record")').first();
    await saveBtn.click();
    console.log('[OMS-2] Clicked Save Record for Mitigation.');
    await page.waitForTimeout(1800);

    // Verify in table
    const mitRow = page.locator('table.data-table tbody tr:has-text("In Salah Industrial Carbon Capture")').first();
    await expect(mitRow).toBeVisible({ timeout: 8000 });
    console.log('[OMS-2] Mitigation project confirmed in table.');

    const shotPath = path.join(SCREENSHOT_DIR, 'oms02_mitigation_ccus_project_saved.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('oms02_mitigation_ccus_project_saved.png');
  });

  test('OMS-3: Scope 1 Upstream Casing Gas Venting Stoichiometric Calculation', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);

    // Verify Scope 1 form loaded
    await page.locator('.s1-form, .scope-form, h2:has-text("New entry")').first().waitFor({ state: 'visible', timeout: 20000 });

    // Select Region
    const regionDropdown = page.locator('.s1-span-2 button.dropdown-selected').first();
    await regionDropdown.click();
    await page.waitForTimeout(400);
    const regionOpt = page.locator('[role="option"]').first();
    await regionOpt.click();
    await page.waitForTimeout(500);

    // Select Process: Casing Gas Venting
    const procDropdown = page.locator('label:has-text("Process")').locator('..').locator('button.dropdown-selected').first();
    await procDropdown.click();
    await page.waitForTimeout(500);
    const casingOpt = page.locator('[role="option"]:has-text("Casing Gas Venting")').first();
    await casingOpt.click();
    await page.waitForTimeout(800);
    console.log('[OMS-3] Selected Casing Gas Venting process.');

    // Configure input parameters (Activity factor or gas throughput)
    const numInput = page.locator('.s1-form input[type="number"]').nth(2);
    if (await numInput.isVisible()) {
      await numInput.fill('45');
    }
    await page.waitForTimeout(800);

    // Save entry as Draft
    const draftBtn = page.locator('button.btn-add-draft').first();
    await draftBtn.click();
    await page.waitForTimeout(1500);
    console.log('[OMS-3] Saved Casing Gas Venting calculation as Draft.');

    const shotPath = path.join(SCREENSHOT_DIR, 'oms03_scope1_casing_gas_venting_calculation.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('oms03_scope1_casing_gas_venting_calculation.png');
  });

  test('OMS-4: Scope 1 Upstream Well Testing Flaring & Venting Calculation', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);

    // Verify Scope 1 form loaded
    await expect(page.locator('.s1-form').first()).toBeVisible({ timeout: 15000 });

    // Select Region
    const regionDropdown = page.locator('.s1-span-2 button.dropdown-selected').first();
    await regionDropdown.click();
    await page.waitForTimeout(400);
    const regionOpt = page.locator('[role="option"]').first();
    await regionOpt.click();
    await page.waitForTimeout(500);

    // Select Process: Well Testing
    const procDropdown = page.locator('label:has-text("Process")').locator('..').locator('button.dropdown-selected').first();
    await procDropdown.click();
    await page.waitForTimeout(500);
    const testOpt = page.locator('[role="option"]:has-text("Well Testing")').first();
    await testOpt.click();
    await page.waitForTimeout(800);
    console.log('[OMS-4] Selected Well Testing process.');

    // Fill throughput or number of tests
    const numInput = page.locator('.s1-form input[type="number"]').nth(2);
    if (await numInput.isVisible()) {
      await numInput.fill('12');
    }
    await page.waitForTimeout(800);

    // Save entry as Draft
    const draftBtn = page.locator('button.btn-add-draft').first();
    await draftBtn.click();
    await page.waitForTimeout(1500);
    console.log('[OMS-4] Saved Well Testing entry as Draft.');

    const shotPath = path.join(SCREENSHOT_DIR, 'oms04_scope1_well_testing_calculation.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('oms04_scope1_well_testing_calculation.png');
  });

  test('OMS-5: Scope 2 Purchased Indirect Steam / Heat with Transmission Losses', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope2`);

    // Verify Scope 2 form
    await expect(page.locator('text=New Electricity Entry').first()).toBeVisible({ timeout: 15000 });
    console.log('[OMS-5] Scope 2 form loaded.');

    // Select Region
    const regDropdown = page.locator('.calc-panel button.dropdown-selected').first();
    await regDropdown.click();
    await page.waitForTimeout(400);
    const regOpt = page.locator('[role="option"]').first();
    await regOpt.click();
    await page.waitForTimeout(400);

    // Select Source Type: Indirect Steam / Heat
    const srcDropdown = page.locator('label:has-text("Source Type")').locator('..').locator('button.dropdown-selected').first();
    await srcDropdown.click();
    await page.waitForTimeout(400);
    const steamOpt = page.locator('[role="option"]:has-text("Indirect Steam / Heat")').first();
    await steamOpt.click();
    await page.waitForTimeout(600);
    console.log('[OMS-5] Selected Indirect Steam / Heat.');

    // Verify Boiler Efficiency & Transmission Loss fields
    const boilerInput = page.locator('input[type="number"]').nth(2);
    if (await boilerInput.isVisible()) {
      await boilerInput.fill('0.82');
    }

    const transInput = page.locator('input[type="number"]').nth(3);
    if (await transInput.isVisible()) {
      await transInput.fill('0.05');
    }

    // Set Steam Consumption Amount
    const amtInput = page.locator('input[placeholder*="Amount"]').or(page.locator('.calc-panel input[type="number"]').last());
    if (await amtInput.isVisible()) {
      await amtInput.fill('15000');
    }
    await page.waitForTimeout(600);

    // Save as Draft
    const draftBtn = page.locator('button:has-text("Save as Draft")').first();
    if (await draftBtn.isVisible()) {
      await draftBtn.click();
      await page.waitForTimeout(1500);
    }
    console.log('[OMS-5] Indirect Steam draft saved.');

    const shotPath = path.join(SCREENSHOT_DIR, 'oms05_scope2_indirect_steam_transmission_losses.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('oms05_scope2_indirect_steam_transmission_losses.png');
  });

  test('OMS-6: Scope 2 Combined Heat & Power (CHP) Dual-Output Allocation', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope2`);

    // Verify Scope 2 form
    await expect(page.locator('text=New Electricity Entry').first()).toBeVisible({ timeout: 15000 });

    // Select Region
    const regDropdown = page.locator('.calc-panel button.dropdown-selected').first();
    await regDropdown.click();
    await page.waitForTimeout(400);
    const regOpt = page.locator('[role="option"]').first();
    await regOpt.click();
    await page.waitForTimeout(400);

    // Select Source Type: CHP / Cogeneration Allocation
    const srcDropdown = page.locator('label:has-text("Source Type")').locator('..').locator('button.dropdown-selected').first();
    await srcDropdown.click();
    await page.waitForTimeout(400);
    const chpOpt = page.locator('[role="option"]:has-text("CHP / Cogeneration Allocation")').first();
    await chpOpt.click();
    await page.waitForTimeout(600);
    console.log('[OMS-6] Selected CHP / Cogeneration Allocation.');

    // Fill Heat Output & Power Output
    const heatOutInput = page.locator('input[type="number"]').nth(2);
    if (await heatOutInput.isVisible()) {
      await heatOutInput.fill('25000');
    }

    const pwrOutInput = page.locator('input[type="number"]').nth(3);
    if (await pwrOutInput.isVisible()) {
      await pwrOutInput.fill('1200');
    }

    // Set Allocation Method: WRI Efficiency
    const methodSelect = page.locator('.calc-panel select.component-select').last();
    if (await methodSelect.isVisible()) {
      await methodSelect.selectOption('wri_efficiency');
    }

    // Fill Fuel Amount
    const amtInput = page.locator('input[placeholder*="Amount"]').or(page.locator('.calc-panel input[type="number"]').last());
    if (await amtInput.isVisible()) {
      await amtInput.fill('45000');
    }
    await page.waitForTimeout(600);

    // Save as Draft
    const draftBtn = page.locator('button:has-text("Save as Draft")').first();
    if (await draftBtn.isVisible()) {
      await draftBtn.click();
      await page.waitForTimeout(1500);
    }
    console.log('[OMS-6] CHP Cogeneration entry draft saved.');

    const shotPath = path.join(SCREENSHOT_DIR, 'oms06_scope2_chp_cogen_efficiency_allocation.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('oms06_scope2_chp_cogen_efficiency_allocation.png');
  });

  test('OMS-7: Methane Intensity Multi-Metric & Target Trajectory Explorer', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/methane-intensity`);

    // Verify Page Header / KPIs
    await expect(page.locator('text=Methane Intensity & Loss Rate Analytics').first()).toBeVisible({ timeout: 15000 });
    console.log('[OMS-7] Methane Intensity dashboard loaded.');

    // Verify KPI indicators (Methane Intensity (Avg), Methane Loss Rate, OGMP Targets)
    await expect(page.locator('text=Methane Intensity (Avg)').first()).toBeVisible({ timeout: 8000 });
    await expect(page.locator('text=Methane Loss Rate').first()).toBeVisible({ timeout: 8000 });
    await expect(page.locator('text=OGMP 2.0 Targets:').first()).toBeVisible({ timeout: 8000 });
    console.log('[OMS-7] Methane KPI cards confirmed.');

    // Switch Year Filter if available
    const yrSelect = page.locator('select').first();
    if (await yrSelect.isVisible().catch(() => false)) {
      const opts = await yrSelect.locator('option').allInnerTexts();
      if (opts.length > 1) {
        await yrSelect.selectOption({ index: 1 });
        await page.waitForTimeout(800);
        console.log('[OMS-7] Toggled reporting year.');
      }
    }

    const shotPath = path.join(SCREENSHOT_DIR, 'oms07_methane_intensity_kpis_and_ogmp_pathway.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('oms07_methane_intensity_kpis_and_ogmp_pathway.png');
  });

});
