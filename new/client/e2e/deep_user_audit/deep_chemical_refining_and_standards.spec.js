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
    console.log('[E2E CHEM] Performing authentication login...');
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

async function selectScope1Region(page) {
  const regBtn = page.locator('.input-group:has-text("Region") button.dropdown-selected, button:has-text("Select Region")').first();
  if (await regBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
    const txt = await regBtn.textContent().catch(() => '');
    if (!txt || txt.includes('Select')) {
      await regBtn.click();
      await page.waitForTimeout(400);
      const firstOpt = page.locator('.dropdown-portal .dropdown-option:not(:has-text("Select")), .dropdown-option:not(:has-text("Select"))').first();
      if (await firstOpt.isVisible({ timeout: 3000 }).catch(() => false)) {
        await firstOpt.click();
        await page.waitForTimeout(400);
      }
    }
  }
}

async function selectScope1Process(page, processLabel) {
  const processGroup = page.locator('.input-group:has-text("Process")').first();
  await expect(processGroup).toBeVisible({ timeout: 15000 });
  const procDropdown = processGroup.locator('button.dropdown-selected').first();
  await expect(procDropdown).toBeVisible({ timeout: 15000 });
  await procDropdown.click();
  await page.waitForTimeout(500);
  const opt = page.locator(`.dropdown-portal .dropdown-option:has-text("${processLabel}"), [role="option"]:has-text("${processLabel}")`).first();
  await expect(opt).toBeVisible({ timeout: 10000 });
  await opt.click();
  await page.waitForTimeout(800);
}

test.describe('Suite 14: Downstream Chemical Synthesis, Refining Asphalt Oxidation, OGMP Framework Governance & Reference Standards Audit', () => {

  test.beforeEach(async () => {
    test.setTimeout(60000);
  });

  // -------------------------------------------------------------------------
  // TEST 1: Petrochemical Ethylene & Chemical Synthesis
  // -------------------------------------------------------------------------
  test('CHEM-1: Petrochemical Ethylene & Chemical Synthesis (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E CHEM] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Select Region
    await selectScope1Region(page);

    // Select Chemical Production
    console.log('[E2E CHEM] Selecting "Chemical Production" process...');
    await selectScope1Process(page, 'Chemical Production');

    // Select Chemical Product from dropdown if available
    const productDropdown = page.locator('.chemical-production-form button.dropdown-selected').first();
    if (await productDropdown.isVisible().catch(() => false)) {
      await productDropdown.click();
      await page.waitForTimeout(400);
      const firstProduct = page.locator('.dropdown-portal .dropdown-option:has-text("Ethylene"), .dropdown-portal .dropdown-option').first();
      if (await firstProduct.isVisible().catch(() => false)) {
        await firstProduct.click();
        await page.waitForTimeout(400);
      }
    }

    // Populate Production Quantity
    const qtyInput = page.locator('.chemical-production-form input[type="number"]').first();
    await expect(qtyInput).toBeVisible({ timeout: 10000 });
    await qtyInput.fill('1500');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chem01_chemical_production_ethylene.png') });
    copyArtifact('chem01_chemical_production_ethylene.png');
    console.log('[E2E CHEM] Captured chem01_chemical_production_ethylene.png.');

    // Submit entry
    console.log('[E2E CHEM] Submitting Chemical Production entry...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify confirmation toast
    const toast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed Chemical Production entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 2: Nitric Acid Production with Catalytic NSCR Abatement
  // -------------------------------------------------------------------------
  test('CHEM-2: Nitric Acid Production with Catalytic NSCR Abatement (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E CHEM] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Select Region
    await selectScope1Region(page);

    // Select Nitric Acid Production
    console.log('[E2E CHEM] Selecting "Nitric Acid Production" process...');
    await selectScope1Process(page, 'Nitric Acid Production');

    // Populate Production Quantity
    const qtyInput = page.locator('.nitric-acid-form input[type="number"]').first();
    await expect(qtyInput).toBeVisible({ timeout: 10000 });
    await qtyInput.fill('850');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chem02_nitric_acid_nscr_abatement.png') });
    copyArtifact('chem02_nitric_acid_nscr_abatement.png');
    console.log('[E2E CHEM] Captured chem02_nitric_acid_nscr_abatement.png.');

    // Submit entry
    console.log('[E2E CHEM] Submitting Nitric Acid Production entry...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify confirmation toast
    const toast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed Nitric Acid Production entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 3: Adipic Acid Industrial Synthesis with Thermal Abatement
  // -------------------------------------------------------------------------
  test('CHEM-3: Adipic Acid Industrial Synthesis with Thermal Abatement (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E CHEM] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Select Region
    await selectScope1Region(page);

    // Select Adipic Acid Production
    console.log('[E2E CHEM] Selecting "Adipic Acid Production" process...');
    await selectScope1Process(page, 'Adipic Acid Production');

    // Populate Production Quantity
    const qtyInput = page.locator('.adipic-acid-form input[type="number"]').first();
    await expect(qtyInput).toBeVisible({ timeout: 10000 });
    await qtyInput.fill('420');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chem03_adipic_acid_thermal_abatement.png') });
    copyArtifact('chem03_adipic_acid_thermal_abatement.png');
    console.log('[E2E CHEM] Captured chem03_adipic_acid_thermal_abatement.png.');

    // Submit entry
    console.log('[E2E CHEM] Submitting Adipic Acid Production entry...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify confirmation toast
    const toast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed Adipic Acid Production entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 4: Petroleum Refinery Bitumen & Asphalt Oxidation Blowing
  // -------------------------------------------------------------------------
  test('CHEM-4: Petroleum Refinery Bitumen & Asphalt Oxidation Blowing (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E CHEM] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Select Region
    await selectScope1Region(page);

    // Select Asphalt Blowing
    console.log('[E2E CHEM] Selecting "Asphalt Blowing" process...');
    await selectScope1Process(page, 'Asphalt Blowing');

    // Populate Asphalt Blown Throughput
    const qtyInput = page.locator('.asphalt-blowing-form input[type="number"]').first();
    await expect(qtyInput).toBeVisible({ timeout: 10000 });
    await qtyInput.fill('3200');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chem04_asphalt_blowing_refining.png') });
    copyArtifact('chem04_asphalt_blowing_refining.png');
    console.log('[E2E CHEM] Captured chem04_asphalt_blowing_refining.png.');

    // Submit entry
    console.log('[E2E CHEM] Submitting Asphalt Blowing entry...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify confirmation toast
    const toast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed Asphalt Blowing entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 5: Facility-Level OGMP 2.0 Overrides & Reconciliation Thresholds
  // -------------------------------------------------------------------------
  test('CHEM-5: Facility-Level OGMP 2.0 Overrides & Reconciliation Thresholds (/settings)', async ({ page }) => {
    console.log('[E2E CHEM] Navigating to Settings Facility Overrides (/settings)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/settings`);
    await page.waitForTimeout(1500);

    // Switch to Facility Overrides Tab
    const facTab = page.locator('button[role="tab"]:has-text("Facility Overrides"), button:has-text("Facility Overrides")').first();
    await expect(facTab).toBeVisible({ timeout: 10000 });
    await facTab.click();
    await page.waitForTimeout(800);

    // Verify Facility Overrides heading
    const title = page.locator('text=Facility-Level OGMP Overrides').first();
    await expect(title).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed Facility-Level OGMP Overrides section.');

    // Find first facility Save button
    const firstSaveBtn = page.locator('tbody tr button:has-text("Save")').first();
    await expect(firstSaveBtn).toBeVisible({ timeout: 10000 });

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chem05_settings_facility_ogmp_overrides.png') });
    copyArtifact('chem05_settings_facility_ogmp_overrides.png');
    console.log('[E2E CHEM] Captured chem05_settings_facility_ogmp_overrides.png.');

    // Click Save on first facility
    console.log('[E2E CHEM] Clicking Save on first facility override row...');
    await firstSaveBtn.click();

    // Verify confirmation toast
    const toast = page.locator('text=Facility OGMP settings updated!').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed Facility OGMP settings updated! toast notification.');
  });

  // -------------------------------------------------------------------------
  // TEST 6: Global OGMP 2.0 Framework Baselines & Decarbonization Thresholds
  // -------------------------------------------------------------------------
  test('CHEM-6: Global OGMP 2.0 Framework Baselines & Decarbonization Thresholds (/settings)', async ({ page }) => {
    console.log('[E2E CHEM] Navigating to Settings OGMP 2.0 Framework (/settings)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/settings`);
    await page.waitForTimeout(1500);

    // Switch to OGMP 2.0 Baseline & Thresholds Tab
    const ogmpTab = page.locator('button[role="tab"]:has-text("OGMP 2.0 Baseline"), button:has-text("OGMP 2.0 Baseline")').first();
    await expect(ogmpTab).toBeVisible({ timeout: 10000 });
    await ogmpTab.click();
    await page.waitForTimeout(800);

    // Verify OGMP Framework heading
    const title = page.locator('text=OGMP 2.0 Framework & Threshold Configuration').first();
    await expect(title).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed OGMP 2.0 Framework & Threshold Configuration section.');

    // Adjust upstream target input if present
    const upstreamInput = page.locator('input[type="number"][min="0.01"]').first();
    if (await upstreamInput.isVisible().catch(() => false)) {
      await upstreamInput.fill('0.18');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chem06_settings_ogmp_framework_targets.png') });
    copyArtifact('chem06_settings_ogmp_framework_targets.png');
    console.log('[E2E CHEM] Captured chem06_settings_ogmp_framework_targets.png.');

    // Click Save OGMP & Target Settings
    console.log('[E2E CHEM] Saving OGMP framework settings...');
    const saveBtn = page.locator('#save-ogmp-settings-btn, button:has-text("Save OGMP & Target Settings"), #save-settings-btn').first();
    await expect(saveBtn).toBeVisible({ timeout: 10000 });
    await saveBtn.click();

    // Verify success toast
    const toast = page.locator('text=System settings saved successfully!').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed System settings saved successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 7: Multi-Catalog Reference Data, HHV Heating Values & Conversions Explorer
  // -------------------------------------------------------------------------
  test('CHEM-7: Multi-Catalog Reference Data, HHV Heating Values & Conversions Explorer (/reference-data)', async ({ page }) => {
    console.log('[E2E CHEM] Navigating to Reference Data (/reference-data)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/reference-data`);
    await page.waitForTimeout(1500);

    // Verify Page Header
    const heading = page.locator('h1:has-text("Reference Data Library"), h1:has-text("Reference Data")').first();
    await expect(heading).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed Reference Data Library heading.');

    // Search for "Natural Gas"
    const searchInput = page.locator('input[placeholder*="Search by name"]').first();
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    await searchInput.fill('Natural Gas');
    await page.waitForTimeout(600);

    // Switch Category Filter to "Default Heating Values" (hhv_defaults)
    const categorySelect = page.locator('select[aria-label="Filter by category"]').first();
    await expect(categorySelect).toBeVisible({ timeout: 10000 });
    await categorySelect.selectOption('hhv_defaults');
    await page.waitForTimeout(600);

    // Clear search to view complete HHV table
    await searchInput.fill('');
    await page.waitForTimeout(600);

    // Verify HHV table header / item
    const hhvRow = page.locator('tr:has-text("Natural Gas"), tr:has-text("1,020")').first();
    await expect(hhvRow).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed Natural Gas 1,020 BTU/scf in Default Heating Values table.');

    // Switch Category Filter to "Unit Conversions" (conversions)
    await categorySelect.selectOption('conversions');
    await page.waitForTimeout(600);

    const convRow = page.locator('tr:has-text("1 MJ (Megajoule)"), tr:has-text("0.000947817")').first();
    await expect(convRow).toBeVisible({ timeout: 10000 });
    console.log('[E2E CHEM] Confirmed 1 MJ -> 0.000947817 MMBtu in Unit Conversions table.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chem07_reference_data_catalog_explorer.png') });
    copyArtifact('chem07_reference_data_catalog_explorer.png');
    console.log('[E2E CHEM] Captured chem07_reference_data_catalog_explorer.png.');
  });

});
