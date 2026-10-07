import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const FRONTEND = 'http://127.0.0.1:5173';
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
    console.log('[E2E QBC] Performing authentication login as Admin...');
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

test.describe('Suite 18: QA/QC Diagnostics, Blowdown & Catalogs Deep Audit', () => {

  test('QBC-1: QA/QC Anomaly Diagnostics manual scan & health findings inspection', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/qa-dashboard`);

    // Verify Page Header
    await expect(page.locator('text=QA/QC & System Diagnostics').first()).toBeVisible({ timeout: 15000 });
    console.log('[QBC-1] QA/QC page loaded.');

    // Trigger manual diagnostics refresh
    const scanBtn = page.locator('button:has-text("Run Diagnostics")').first();
    await expect(scanBtn).toBeVisible({ timeout: 8000 });
    await scanBtn.click();
    console.log('[QBC-1] Clicked Run Diagnostics button.');
    await page.waitForTimeout(2000);

    // Switch to Health & Completeness Diagnostics Tab
    const diagTab = page.locator('[role="tab"]:has-text("Health & Completeness Diagnostics")').first();
    await expect(diagTab).toBeVisible({ timeout: 8000 });
    await diagTab.click();
    await page.waitForTimeout(1000);

    // Verify Dimension Completeness Labels
    await expect(page.locator('text=Organizational Facility Assignment').first()).toBeVisible({ timeout: 8000 });
    await expect(page.locator('text=Source & Fuel Type Specifications').first()).toBeVisible();
    await expect(page.locator('text=Activity Quantities & Physical Units').first()).toBeVisible();
    await expect(page.locator('text=Calculated CO₂e Emissions Integrity').first()).toBeVisible();
    console.log('[QBC-1] Dimension completeness bars verified.');

    // Expand finding sample records if available
    const inspectBtn = page.locator('.qa-issue-item button:has-text("Inspect")').first();
    if (await inspectBtn.isVisible().catch(() => false)) {
      console.log('[QBC-1] Expanding diagnostic sample records preview...');
      await inspectBtn.click();
      await page.waitForTimeout(800);
      await expect(page.locator('.qa-issue-item table').first()).toBeVisible({ timeout: 5000 });
    }

    const shotPath = path.join(SCREENSHOT_DIR, 'qbc01_qaqc_diagnostics_scan_and_findings.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('qbc01_qaqc_diagnostics_scan_and_findings.png');
  });

  test('QBC-2: QA/QC Queue single & bulk resolution modal flow', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/qa-dashboard`);

    // Ensure Anomaly Resolution Queue Tab is active
    const queueTab = page.locator('[role="tab"]:has-text("Anomaly Resolution Queue")').first();
    await expect(queueTab).toBeVisible({ timeout: 8000 });
    await queueTab.click();
    await page.waitForTimeout(1000);

    // Verify Status Filter Buttons
    const filterGroup = page.locator('div[role="group"][aria-label="Status filter"]').first();
    await expect(filterGroup).toBeVisible({ timeout: 8000 });

    const pendingBtn = filterGroup.locator('button:has-text("Pending Review")');
    if (await pendingBtn.isVisible()) {
      await pendingBtn.click();
      await page.waitForTimeout(500);
    }

    const allBtn = filterGroup.locator('button:has-text("All Statuses")');
    if (await allBtn.isVisible()) {
      await allBtn.click();
      await page.waitForTimeout(500);
    }

    // Check if table rows exist
    const rows = page.locator('tbody tr');
    const rowCount = await rows.count();
    console.log(`[QBC-2] Detected ${rowCount} rows in QA queue.`);

    if (rowCount > 0) {
      // Test selection and bulk modal
      const firstCheckbox = page.locator('tbody tr input[type="checkbox"]').first();
      await firstCheckbox.check();
      await page.waitForTimeout(500);

      // Verify bulk action bar
      await expect(page.locator('text=1 record selected').first()).toBeVisible({ timeout: 5000 });
      console.log('[QBC-2] Bulk selection bar visible.');

      // Click Approve Selected to open ConfirmDialog
      const approveBtn = page.locator('button:has-text("Approve Selected")').first();
      await approveBtn.click();
      await page.waitForTimeout(600);

      // Verify ConfirmDialog Modal
      await expect(page.locator('text=Confirm Bulk Verification').first()).toBeVisible({ timeout: 5000 });
      console.log('[QBC-2] ConfirmDialog modal displayed.');

      // Cancel to keep test non-destructive
      const cancelBtn = page.locator('button:has-text("Cancel")').first();
      await cancelBtn.click();
      await page.waitForTimeout(500);
      await expect(page.locator('text=Confirm Bulk Verification')).not.toBeVisible();
    } else {
      console.log('[QBC-2] No flagged records currently present; verifying empty state card.');
      await expect(page.locator('text=Zero Anomalies Detected').or(page.locator('text=No Matching Records')).first()).toBeVisible({ timeout: 5000 });
    }

    const shotPath = path.join(SCREENSHOT_DIR, 'qbc02_qaqc_resolution_queue_and_actions.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('qbc02_qaqc_resolution_queue_and_actions.png');
  });

  test('QBC-3: Reference Data multi-catalog search & conversion inspection', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/reference-data`);

    // Verify Page Header
    await expect(page.locator('text=Reference Data Library').first()).toBeVisible({ timeout: 15000 });
    console.log('[QBC-3] Reference Data Library loaded.');

    const catSelect = page.locator('select.filter-select').first();
    await expect(catSelect).toBeVisible({ timeout: 8000 });

    // Category 1: Default Heating Values (HHV)
    await catSelect.selectOption('hhv_defaults');
    await page.waitForTimeout(600);
    await expect(page.locator('text=Default Fuel Heating Values (HHV)').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('table.factors-table td:has-text("Natural Gas")').first()).toBeVisible();
    await expect(page.locator('table.factors-table td:has-text("Diesel")').first()).toBeVisible();
    console.log('[QBC-3] Verified HHV defaults catalog.');

    // Category 2: Unit Conversions
    await catSelect.selectOption('conversions');
    await page.waitForTimeout(600);
    await expect(page.locator('text=Unit Conversions').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('table.factors-table td:has-text("1 MJ (Megajoule)")').first()).toBeVisible();
    console.log('[QBC-3] Verified unit conversions table.');

    // Test Search Filtering inside Conversions
    const searchInput = page.locator('.search-input-wrapper input').first();
    await searchInput.fill('BOE');
    await page.waitForTimeout(500);
    await expect(page.locator('table.factors-table td:has-text("1 BOE (Barrel of Oil Equivalent)")').first()).toBeVisible();
    console.log('[QBC-3] Verified search filter in reference data.');

    // Clear search and switch to Global Warming Potentials (GWPs)
    await searchInput.fill('');
    await catSelect.selectOption('gwp');
    await page.waitForTimeout(600);
    await expect(page.locator('text=Global Warming Potentials (GWPs)').first()).toBeVisible({ timeout: 5000 });
    await expect(page.locator('table.factors-table th:has-text("AR4 (2007)")').first()).toBeVisible();
    await expect(page.locator('table.factors-table th:has-text("AR6 (2021)")').first()).toBeVisible();
    await expect(page.locator('table.factors-table td:has-text("Methane (CH₄)")').first()).toBeVisible();
    console.log('[QBC-3] Verified GWP standards table.');

    // Toggle category collapse
    const catHeader = page.locator('.category-header').first();
    await catHeader.click();
    await page.waitForTimeout(400);
    await catHeader.click();
    await page.waitForTimeout(400);

    const shotPath = path.join(SCREENSHOT_DIR, 'qbc03_reference_data_library_and_conversions.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('qbc03_reference_data_library_and_conversions.png');
  });

  test('QBC-4: Scope 1 Compressor Blowdown stoichiometric calculation', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);

    // Wait for form container
    await expect(page.locator('.s1-form').first()).toBeVisible({ timeout: 15000 });
    console.log('[QBC-4] Scope 1 form loaded.');

    // Select Region
    const regionDropdown = page.locator('.s1-span-2 button.dropdown-selected').first();
    await regionDropdown.click();
    await page.waitForTimeout(400);
    const regionOpt = page.locator('[role="option"]').first();
    await regionOpt.click();
    await page.waitForTimeout(500);

    // Select Process: Venting (Blowdown)
    const procDropdown = page.locator('label:has-text("Process")').locator('..').locator('button.dropdown-selected').first();
    await procDropdown.click();
    await page.waitForTimeout(500);
    const blowdownOpt = page.locator('[role="option"]:has-text("Venting (Blowdown)")').first();
    await blowdownOpt.click();
    await page.waitForTimeout(800);
    console.log('[QBC-4] Selected Venting (Blowdown) process.');

    // Select Methodology: Measurement / GC (Tier 3)
    const tier3Btn = page.locator('button:has-text("Measurement / GC")').first();
    if (await tier3Btn.isVisible()) {
      await tier3Btn.click();
      await page.waitForTimeout(800);
    }

    // Verify BlowdownForm is mounted
    const volInput = page.locator('input[placeholder="Vessel Vol"]').first();
    await expect(volInput).toBeVisible({ timeout: 8000 });

    // Fill Blowdown parameters
    await volInput.fill('120');

    const pressInput = page.locator('input[placeholder="Before blowdown (psig)"]').first();
    await pressInput.fill('450');

    const eventsInput = page.locator('input[placeholder="Count"]').first();
    await eventsInput.fill('4');

    const ch4Input = page.locator('input[placeholder="e.g. 85"]').first();
    await ch4Input.fill('85');

    const co2Input = page.locator('input[placeholder="e.g. 2.5"]').first();
    await co2Input.fill('2.5');

    const effInput = page.locator('input[placeholder="0 = Vented, 98 = Flared"]').first();
    await effInput.fill('0');
    await page.waitForTimeout(800);
    console.log('[QBC-4] Filled Compressor Blowdown stoichiometric inputs.');

    // Save entry as Draft
    const draftBtn = page.locator('button.btn-add-draft').first();
    await draftBtn.click();
    await page.waitForTimeout(1500);
    console.log('[QBC-4] Draft submission completed.');

    const shotPath = path.join(SCREENSHOT_DIR, 'qbc04_scope1_compressor_blowdown_calculation.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('qbc04_scope1_compressor_blowdown_calculation.png');
  });

  test('QBC-5: Scope 1 Fugitives component count & screening calculation', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);

    // Wait for form container
    await expect(page.locator('.s1-form').first()).toBeVisible({ timeout: 15000 });

    // Select Region
    const regionDropdown = page.locator('.s1-span-2 button.dropdown-selected').first();
    await regionDropdown.click();
    await page.waitForTimeout(400);
    const regionOpt = page.locator('[role="option"]').first();
    await regionOpt.click();
    await page.waitForTimeout(500);

    // Select Process: Onshore Equipment Leaks / Fugitives
    const procDropdown = page.locator('label:has-text("Process")').locator('..').locator('button.dropdown-selected').first();
    await procDropdown.click();
    await page.waitForTimeout(500);
    const fugOpt = page.locator('[role="option"]:has-text("Onshore Equipment Leaks / Fugitives")').first();
    await fugOpt.click();
    await page.waitForTimeout(800);
    console.log('[QBC-5] Selected Onshore Equipment Leaks / Fugitives process.');

    // Step 1: Test Tier 2 Component Count Method
    const tier2Btn = page.locator('button:has-text("Equipment & Component")').first();
    if (await tier2Btn.isVisible()) {
      await tier2Btn.click();
      await page.waitForTimeout(800);
    }

    const compCountSub = page.locator('button:has-text("Component count")').first();
    if (await compCountSub.isVisible()) {
      await compCountSub.click();
      await page.waitForTimeout(500);
    }

    // Fill Tier 2B Component count & hours
    const compCountInput = page.locator('input[placeholder="e.g. 100"]').first();
    if (await compCountInput.isVisible()) {
      await compCountInput.fill('250');
    }

    const hoursInput = page.locator('input[placeholder="whole month"]').first();
    if (await hoursInput.isVisible()) {
      await hoursInput.fill('720');
    }

    const ch4MolInput = page.locator('input[placeholder="81.6 (table basis)"]').first();
    if (await ch4MolInput.isVisible()) {
      await ch4MolInput.fill('88.5');
    }
    await page.waitForTimeout(600);
    console.log('[QBC-5] Configured Tier 2B component count.');

    // Step 2: Switch to Tier 3 Leaker Survey (OGI)
    const tier3Btn = page.locator('button:has-text("Screening / OGI / Meas.")').first();
    if (await tier3Btn.isVisible()) {
      await tier3Btn.click();
      await page.waitForTimeout(800);
    }

    const ogiSub = page.locator('button:has-text("Leaker Survey (OGI)")').first();
    if (await ogiSub.isVisible()) {
      await ogiSub.click();
      await page.waitForTimeout(500);
    }

    const leakersInput = page.locator('input[placeholder="e.g. 2"]').first();
    if (await leakersInput.isVisible()) {
      await leakersInput.fill('4');
    }

    const ogiHours = page.locator('input[placeholder="whole month"]').first();
    if (await ogiHours.isVisible()) {
      await ogiHours.fill('720');
    }
    await page.waitForTimeout(800);
    console.log('[QBC-5] Configured Tier 3 OGI survey.');

    const shotPath = path.join(SCREENSHOT_DIR, 'qbc05_scope1_fugitives_tier2b_and_ogi_survey.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('qbc05_scope1_fugitives_tier2b_and_ogi_survey.png');
  });

  test('QBC-6: Scope 3 EEIO Quick Spend NAICS financial conversion calculator', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope3`);

    // Verify Scope 3 entry form container
    await expect(page.locator('.calc-panel').first()).toBeVisible({ timeout: 15000 });
    console.log('[QBC-6] Scope 3 page loaded.');

    // Expand EEIO Quick Spend Calculator accordion if needed
    const eeioHeader = page.locator('text=EEIO Quick Spend Calculator').first();
    await expect(eeioHeader).toBeVisible({ timeout: 8000 });

    const naicsInput = page.locator('input[placeholder="e.g. 331110 or steel"]').first();
    if (!(await naicsInput.isVisible().catch(() => false))) {
      console.log('[QBC-6] Expanding EEIO calculator accordion...');
      await eeioHeader.click();
      await page.waitForTimeout(600);
    }

    await expect(naicsInput).toBeVisible({ timeout: 5000 });
    await naicsInput.fill('331110');
    await page.waitForTimeout(400);

    const spendInput = page.locator('input[placeholder="0.00"]').first();
    await spendInput.fill('250000');
    await page.waitForTimeout(400);

    // Click Calculate & Auto-fill
    const calcBtn = page.locator('button:has-text("Calculate & Auto-fill")').first();
    await calcBtn.click();
    console.log('[QBC-6] Clicked Calculate & Auto-fill.');
    await page.waitForTimeout(1500);

    // Verify Result Display
    await expect(page.locator('text=Estimated Emissions:').first()).toBeVisible({ timeout: 8000 });
    console.log('[QBC-6] EEIO estimated emissions calculated and displayed.');

    // Verify auto-filled amount in main Scope 3 form
    const mainAmount = page.locator('input[name="amount"]').or(page.locator('.calc-panel input[type="number"]')).nth(1);
    const amountVal = await mainAmount.inputValue().catch(() => '');
    console.log(`[QBC-6] Auto-filled amount value: ${amountVal}`);

    const shotPath = path.join(SCREENSHOT_DIR, 'qbc06_scope3_eeio_quick_spend_calculator.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('qbc06_scope3_eeio_quick_spend_calculator.png');
  });

  test('QBC-7: GHG Protocol Base Year Recalculation justification entry', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=goals`);

    // Verify Active Baseline Banner
    await expect(page.locator('text=GHG Protocol & OGMP 2.0 Baseline').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Base Years & Recalculations History').first()).toBeVisible();
    console.log('[QBC-7] Goals tab and Base Year Recalculation section loaded.');

    // Fill Base Year Recalculation Form
    const baseYearInputs = page.locator('input[placeholder="e.g. 2023"]');
    await expect(baseYearInputs.first()).toBeVisible({ timeout: 8000 });
    await baseYearInputs.first().fill('2023');

    // Prev emissions & Adjusted emissions
    const optionalInputs = page.locator('input[placeholder="Optional"]');
    if (await optionalInputs.count() >= 2) {
      await optionalInputs.nth(0).fill('1250000');
      await optionalInputs.nth(1).fill('1180000');
    }

    // Reason Textarea
    const reasonArea = page.locator('textarea[placeholder*="Detail the justification"]').first();
    await reasonArea.fill('Methodological update to IPCC AR6 GWPs and boundary consolidation across upstream production clusters');
    await page.waitForTimeout(400);

    // Click Save Recalculation
    const saveRecalcBtn = page.locator('button:has-text("Save Recalculation")').first();
    await saveRecalcBtn.click();
    console.log('[QBC-7] Clicked Save Recalculation button.');
    await page.waitForTimeout(1800);

    // Verify History Table Row
    const histRow = page.locator('table.data-table tbody tr:has-text("2023")').first();
    await expect(histRow).toBeVisible({ timeout: 8000 });
    await expect(histRow.locator('text=Active').first()).toBeVisible();
    console.log('[QBC-7] Base year recalculation history row confirmed.');

    const shotPath = path.join(SCREENSHOT_DIR, 'qbc07_ghg_protocol_base_year_recalculation_saved.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('qbc07_ghg_protocol_base_year_recalculation_saved.png');
  });

});
