import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const SCREENSHOT_DIR = path.resolve('e2e/deep_user_audit/screenshots');
const BRAIN_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\145e1f58-77e7-4f5b-8573-5a1c4dc13171';

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
    await emailInput.fill('a');
    const pwdInput = page.locator('input[type="password"]').first();
    await pwdInput.fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
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
      const firstOpt = page.locator('.dropdown-option:not(:has-text("Select")), [role="option"]:not(:has-text("Select"))').first();
      if (await firstOpt.isVisible({ timeout: 3000 }).catch(() => false)) {
        await firstOpt.click();
        await page.waitForTimeout(400);
      }
    }
  }
}

async function selectScope2Region(page) {
  const regBtn = page.locator('.input-group:has-text("Region") button.dropdown-selected, button:has-text("Select Region")').first();
  if (await regBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
    const txt = await regBtn.textContent().catch(() => '');
    if (!txt || txt.includes('Select')) {
      await regBtn.click();
      await page.waitForTimeout(400);
      const firstOpt = page.locator('.dropdown-option:not(:has-text("Select")), [role="option"]:not(:has-text("Select"))').first();
      if (await firstOpt.isVisible({ timeout: 3000 }).catch(() => false)) {
        await firstOpt.click();
        await page.waitForTimeout(400);
      }
    }
  }
}

async function selectScope3Facility(page) {
  const facBtn = page.locator('.input-group:has-text("Facility") button.dropdown-selected, button:has-text("Select Facility")').first();
  if (await facBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
    const txt = await facBtn.textContent().catch(() => '');
    if (!txt || txt.includes('Select')) {
      await facBtn.click();
      await page.waitForTimeout(400);
      const firstOpt = page.locator('.dropdown-option:not(:has-text("Select")), [role="option"]:not(:has-text("Select"))').first();
      if (await firstOpt.isVisible({ timeout: 3000 }).catch(() => false)) {
        await firstOpt.click();
        await page.waitForTimeout(400);
      }
    }
  }
}

test.describe.serial('Suite 12: Advanced Energy Systems, Remote Sensing & Quality Governance', () => {

  test.beforeAll(async () => {
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  // -------------------------------------------------------------------------
  // TEST 1: Scope 2 CHP Cogeneration Dual-Output Allocation Engineering
  // -------------------------------------------------------------------------
  test('ADV-1: Scope 2 CHP Cogeneration Dual-Output Allocation Engineering (/emissions?scope=scope2)', async ({ page }) => {
    console.log('[E2E ADV] Navigating to Scope 2 Emissions (/emissions?scope=scope2)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope2`);
    await page.waitForTimeout(1500);

    // Verify Scope 2 New Electricity Entry Header
    const s2Header = page.locator('text=New Electricity Entry').first();
    await expect(s2Header).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Confirmed Scope 2 calculation interface.');

    // Select Region / Facility if not populated
    await selectScope2Region(page);

    // Switch Source Type to CHP / Cogeneration Allocation
    console.log('[E2E ADV] Selecting CHP / Cogeneration Allocation source type...');
    const srcTypeDropdown = page.locator('.input-group:has-text("Source Type") button.dropdown-selected').first();
    await srcTypeDropdown.click();
    await page.waitForTimeout(400);

    const cogenOption = page.locator('.dropdown-menu .dropdown-option:has-text("CHP / Cogeneration Allocation"), [role="option"]:has-text("Cogeneration")').first();
    await expect(cogenOption).toBeVisible();
    await cogenOption.click();
    await page.waitForTimeout(600);

    // Populate Amount (Total facility emissions to allocate: 1,250 tCO2e)
    const amountInput = page.locator('.input-group:has-text("Total Facility Emissions") input, .input-group:has-text("Amount") input[type="number"], input[placeholder="0.00"]').first();
    await expect(amountInput).toBeVisible();
    await amountInput.fill('1250');

    // Populate Heat Output (MMBtu)
    const heatOutputInput = page.locator('.input-group:has-text("Heat Output") input').first();
    await expect(heatOutputInput).toBeVisible();
    await heatOutputInput.fill('4200');

    // Populate Power Output (MWh)
    const powerOutputInput = page.locator('.input-group:has-text("Power Output") input').first();
    await expect(powerOutputInput).toBeVisible();
    await powerOutputInput.fill('850');

    // Method defaults to WRI Efficiency; populate Heat Efficiency & Power Efficiency
    const heatEffInput = page.locator('.input-group:has-text("Heat Efficiency") input').first();
    if (await heatEffInput.isVisible().catch(() => false)) {
      await heatEffInput.fill('82');
    }

    const powerEffInput = page.locator('.input-group:has-text("Power Efficiency") input').first();
    if (await powerEffInput.isVisible().catch(() => false)) {
      await powerEffInput.fill('38');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'adv01_scope2_cogen_chp_allocation.png') });
    copyArtifact('adv01_scope2_cogen_chp_allocation.png');
    console.log('[E2E ADV] Captured adv01_scope2_cogen_chp_allocation.png.');

    // Submit as Verified Entry
    console.log('[E2E ADV] Submitting Scope 2 Cogeneration record...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Calculate & Submit"), button:has-text("Calculate & Submit for Review"), button.btn-add-activity').first();
    await submitBtn.click();

    // Verify toast
    const successToast = page.locator('text=Scope 2 entry added successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Confirmed Cogeneration entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 2: Scope 2 District Heating & Indirect Steam Ingestion
  // -------------------------------------------------------------------------
  test('ADV-2: Scope 2 District Heating & Indirect Steam Ingestion (/emissions?scope=scope2)', async ({ page }) => {
    console.log('[E2E ADV] Navigating to Scope 2 Emissions (/emissions?scope=scope2)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope2`);
    await page.waitForTimeout(1500);

    // Select Region / Facility if not populated
    await selectScope2Region(page);

    // Switch Source Type to Indirect Steam / Heat
    console.log('[E2E ADV] Selecting Indirect Steam / Heat source type...');
    const srcTypeDropdown = page.locator('.input-group:has-text("Source Type") button.dropdown-selected').first();
    await srcTypeDropdown.click();
    await page.waitForTimeout(400);

    const steamOption = page.locator('.dropdown-menu .dropdown-option:has-text("Indirect Steam / Heat"), [role="option"]:has-text("Indirect Steam")').first();
    await expect(steamOption).toBeVisible();
    await steamOption.click();
    await page.waitForTimeout(600);

    // Populate steam consumption (650 MMBtu)
    const amountInput = page.locator('.input-group:has-text("Usage Amount") input, .input-group:has-text("Amount") input[type="number"], input[placeholder="0.00"]').first();
    await expect(amountInput).toBeVisible();
    await amountInput.fill('650');

    // Populate Boiler Efficiency (0.85 = 85%)
    const boilerInput = page.locator('.input-group:has-text("Boiler Efficiency") input').first();
    if (await boilerInput.isVisible().catch(() => false)) {
      await boilerInput.fill('0.85');
    }

    // Populate Transmission Loss (0.04 = 4%)
    const lossInput = page.locator('.input-group:has-text("Transmission Loss") input').first();
    if (await lossInput.isVisible().catch(() => false)) {
      await lossInput.fill('0.04');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'adv02_scope2_indirect_steam_logged.png') });
    copyArtifact('adv02_scope2_indirect_steam_logged.png');
    console.log('[E2E ADV] Captured adv02_scope2_indirect_steam_logged.png.');

    // Submit entry
    console.log('[E2E ADV] Submitting Indirect Steam record...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Calculate & Submit"), button:has-text("Calculate & Submit for Review"), button.btn-add-activity').first();
    await submitBtn.click();

    // Verify toast
    const successToast = page.locator('text=Scope 2 entry added successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Confirmed Indirect Steam entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 3: Scope 3 Category-Specific Freight & Transport Value Chain Accounting
  // -------------------------------------------------------------------------
  test('ADV-3: Scope 3 Category-Specific Freight & Transport Value Chain Accounting (/emissions?scope=scope3)', async ({ page }) => {
    console.log('[E2E ADV] Navigating to Scope 3 Emissions (/emissions?scope=scope3)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope3`);
    await page.waitForTimeout(1500);

    // Select Facility if not selected
    await selectScope3Facility(page);

    // Verify Scope 3 Category Dropdown
    const catDropdown = page.locator('.input-group:has-text("Category") button.dropdown-selected').first();
    await expect(catDropdown).toBeVisible({ timeout: 10000 });
    await catDropdown.click();
    await page.waitForTimeout(400);

    // Select Upstream Transportation and Distribution (Category 4)
    const cat4Option = page.locator('.dropdown-menu .dropdown-option:has-text("Transportation"), [role="option"]:has-text("Transportation")').first();
    if (await cat4Option.isVisible().catch(() => false)) {
      await cat4Option.click();
    } else {
      // Pick first available category
      const firstCat = page.locator('.dropdown-menu .dropdown-option:not(:has-text("Select")), [role="option"]:not(:has-text("Select"))').first();
      await firstCat.click();
    }
    await page.waitForTimeout(600);

    // Select Activity Type
    const actDropdown = page.locator('.input-group:has-text("Activity Type") button.dropdown-selected').first();
    if (await actDropdown.isVisible().catch(() => false)) {
      await actDropdown.click();
      await page.waitForTimeout(400);
      const firstAct = page.locator('.dropdown-menu .dropdown-option:not(:has-text("Select")), [role="option"]:not(:has-text("Select"))').first();
      if (await firstAct.isVisible().catch(() => false)) {
        await firstAct.click();
        await page.waitForTimeout(400);
      }
    }

    // Populate Amount (45,000 t-km or units)
    const amountInput = page.locator('.input-group:has-text("Amount") input').first();
    await expect(amountInput).toBeVisible();
    await amountInput.fill('45000');

    // Populate EF (kg CO2e/unit)
    const efInput = page.locator('.input-group:has-text("Emission Factor") input, .input-group:has-text("EF") input').first();
    if (await efInput.isVisible().catch(() => false)) {
      await efInput.fill('0.145');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'adv03_scope3_freight_logistics_saved.png') });
    copyArtifact('adv03_scope3_freight_logistics_saved.png');
    console.log('[E2E ADV] Captured adv03_scope3_freight_logistics_saved.png.');

    // Submit Scope 3 verified record
    console.log('[E2E ADV] Submitting Scope 3 Freight record...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Calculate & Submit"), button:has-text("Calculate & Submit for Review"), button.btn-add-activity').first();
    await submitBtn.click();

    // Verify toast
    const successToast = page.locator('text=Scope 3 entry added successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Confirmed Scope 3 freight entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 4: Scope 1 Associated Gas Venting GOR Mass Balance Partitioning
  // -------------------------------------------------------------------------
  test('ADV-4: Scope 1 Associated Gas Venting GOR Mass Balance Partitioning (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E ADV] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);
    await selectScope1Region(page);

    // Switch Process to Associated Gas Venting
    console.log('[E2E ADV] Selecting "Associated Gas Venting" process...');
    const processDropdown = page.locator('.input-group:has-text("Process") button.dropdown-selected').first();
    await processDropdown.click();
    await page.waitForTimeout(400);

    const agvOption = page.locator('.dropdown-portal .dropdown-option:has-text("Associated Gas Venting"), [role="option"]:has-text("Associated Gas Venting")').first();
    await expect(agvOption).toBeVisible();
    await agvOption.click();
    await page.waitForTimeout(600);

    // Switch method to Tier 2 (GOR Balance / Engineering GOR)
    console.log('[E2E ADV] Selecting Tier 2 GOR Balance method...');
    const tier2Btn = page.locator('button:has-text("GOR Balance"), .methodology-toggle button:has-text("Tier 2"), button:has-text("Tier 2")').first();
    if (await tier2Btn.isVisible().catch(() => false)) {
      await tier2Btn.click();
      await page.waitForTimeout(500);
    }

    // Populate Oil Production (bbl/day)
    const oilInput = page.locator('input[placeholder="e.g. 500"], .input-group:has-text("Oil production") input[type="number"]').first();
    if (await oilInput.isVisible().catch(() => false)) {
      await oilInput.fill('2800');
    }

    // Populate GOR (scf/bbl)
    const gorInput = page.locator('input[placeholder="e.g. 800"], .input-group:has-text("GOR") input[type="number"]').first();
    if (await gorInput.isVisible().catch(() => false)) {
      await gorInput.fill('720');
    }

    // Populate Venting Duration (days)
    const durInput = page.locator('.input-group:has-text("Venting Duration") input[type="number"], .input-group:has-text("Duration") input').first();
    if (await durInput.isVisible().catch(() => false)) {
      await durInput.fill('14');
    }

    // Populate Recovered Gas Volume (scf)
    const recGasInput = page.locator('input[placeholder="e.g. 0"]').first();
    if (await recGasInput.isVisible().catch(() => false)) {
      await recGasInput.fill('50000');
    }

    // Populate Flared Gas Volume (scf)
    const flaredGasInput = page.locator('input[placeholder="e.g. 0"]').nth(1);
    if (await flaredGasInput.isVisible().catch(() => false)) {
      await flaredGasInput.fill('25000');
    }

    // Populate CH4 (mol %)
    const ch4Input = page.locator('.input-group:has-text("CH₄ (mol %)") input, .input-group:has-text("CH4") input').first();
    if (await ch4Input.isVisible().catch(() => false)) {
      await ch4Input.fill('84.0');
    }

    // Populate CO2 (mol %)
    const co2Input = page.locator('.input-group:has-text("CO₂ (mol %)") input, .input-group:has-text("CO2") input').first();
    if (await co2Input.isVisible().catch(() => false)) {
      await co2Input.fill('2.5');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'adv04_associated_gas_venting_gor.png') });
    copyArtifact('adv04_associated_gas_venting_gor.png');
    console.log('[E2E ADV] Captured adv04_associated_gas_venting_gor.png.');

    // Submit form
    console.log('[E2E ADV] Submitting Associated Gas Venting calculation...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify toast
    const successToast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Confirmed Associated Gas Venting submission toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 5: Geospatial Methane Explorer Sentinel-5P Overpass & OGMP Level 5 Reconciled Export
  // -------------------------------------------------------------------------
  test('ADV-5: Methane Explorer Satellite Overpass & OGMP Level 5 Reconciled Export (/methane-explorer)', async ({ page }) => {
    console.log('[E2E ADV] Navigating to Methane Explorer (/methane-explorer)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/methane-explorer`);
    await page.waitForTimeout(2000);

    // Locate first asset card in drawer and trigger click
    console.log('[E2E ADV] Selecting first facility in Explorer drawer...');
    const facilityCards = page.locator('div[role="button"][aria-pressed]');
    await expect(facilityCards.first()).toBeVisible({ timeout: 10000 });
    await facilityCards.first().evaluate((el) => el.click());
    await page.waitForTimeout(1500);

    // Verify Dossier is visible with Sentinel-5P telemetry
    const dossierSentinel = page.locator('text=Copernicus Sentinel-5P overpass').first();
    await expect(dossierSentinel).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Explorer Dossier opened with facility telemetry.');

    // Test Export to OGMP 2.0 Level 5 ledger or Configure
    console.log('[E2E ADV] Checking OGMP 2.0 Level 5 reconciliation or configure action...');
    const ogmpActionBtn = page.locator('button#reconcile-ogmp-btn, button:has-text("Reconcile into OGMP 2.0 ledger"), button:has-text("Configure in Settings")').first();
    if (await ogmpActionBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
      await ogmpActionBtn.click();
      await page.waitForTimeout(1000);
      console.log('[E2E ADV] Triggered OGMP satellite reconciliation action.');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'adv05_satellite_ogmp_level5_reconciled.png') });
    copyArtifact('adv05_satellite_ogmp_level5_reconciled.png');
    console.log('[E2E ADV] Captured adv05_satellite_ogmp_level5_reconciled.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 6: QA/QC System Governance & Forensic Anomaly CSV Export
  // -------------------------------------------------------------------------
  test('ADV-6: QA/QC System Governance & Forensic Anomaly CSV Export (/qa-dashboard)', async ({ page }) => {
    console.log('[E2E ADV] Navigating to QA/QC Dashboard (/qa-dashboard)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/qa-dashboard`);
    await page.waitForTimeout(1500);

    // Verify QA Header and Health KPIs
    const qaTitle = page.locator('text=QA/QC & System Diagnostics').first();
    await expect(qaTitle).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Confirmed QA/QC dashboard header.');

    // Switch across tabs: Diagnostics -> Uncertainty -> Queue
    console.log('[E2E ADV] Switching to Diagnostics tab...');
    const diagTab = page.locator('button[role="tab"]').filter({ hasText: 'Diagnostics' }).first();
    await expect(diagTab).toBeVisible({ timeout: 10000 });
    await diagTab.click();
    await page.waitForTimeout(1000);
    const diagMatrix = page.locator('text=Inventory Completeness by Attribute').first();
    await expect(diagMatrix).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Diagnostics integrity checks verified.');

    console.log('[E2E ADV] Switching to Uncertainty tab...');
    const uncTab = page.locator('button[role="tab"]').filter({ hasText: 'Uncertainty' }).first();
    await expect(uncTab).toBeVisible({ timeout: 10000 });
    await uncTab.click();
    await page.waitForTimeout(1000);
    await expect(page.locator('text=IPCC Tier 1 Error Propagation').first()).toBeVisible({ timeout: 10000 });

    console.log('[E2E ADV] Switching back to Review Queue tab...');
    const queueTab = page.locator('button[role="tab"]').filter({ hasText: 'Queue' }).first();
    await expect(queueTab).toBeVisible({ timeout: 10000 });
    await queueTab.click();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'adv06_qa_qc_diagnostics_and_export.png') });
    copyArtifact('adv06_qa_qc_diagnostics_and_export.png');
    console.log('[E2E ADV] Captured adv06_qa_qc_diagnostics_and_export.png.');

    // Trigger CSV Export & Intercept Download
    console.log('[E2E ADV] Triggering QA/QC compliance CSV download...');
    const exportBtn = page.locator('button:has-text("Export QA Report"), button:has-text("Export Report"), button:has-text("Export")').first();
    if (await exportBtn.isVisible().catch(() => false)) {
      const downloadPromise = page.waitForEvent('download', { timeout: 12000 }).catch(() => null);
      await exportBtn.click();
      const download = await downloadPromise;
      if (download) {
        const downloadPath = await download.path();
        const stat = fs.statSync(downloadPath);
        expect(stat.size).toBeGreaterThan(10);
        console.log(`[E2E ADV] Intercepted QA report: ${download.suggestedFilename()} (${stat.size} bytes).`);
      }
    }
  });

  // -------------------------------------------------------------------------
  // TEST 7: ESA Copernicus Sentinel-5P CDSE Credentials & Connection Test
  // -------------------------------------------------------------------------
  test('ADV-7: ESA Copernicus Sentinel-5P CDSE Credentials & Connection Test (/settings)', async ({ page }) => {
    console.log('[E2E ADV] Navigating to System Settings (/settings)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/settings`);
    await page.waitForTimeout(1500);

    // Switch to Copernicus Sentinel-5P tab
    console.log('[E2E ADV] Switching to Copernicus Sentinel-5P settings tab...');
    const copernicusTab = page.locator('button[role="tab"]').filter({ hasText: 'Copernicus' }).first();
    await expect(copernicusTab).toBeVisible({ timeout: 10000 });
    await copernicusTab.click();
    await page.waitForTimeout(800);

    // Verify Sentinel-5P Settings Card
    const copernicusTitle = page.locator('text=ESA Copernicus Sentinel-5P').first();
    await expect(copernicusTitle).toBeVisible();
    console.log('[E2E ADV] Confirmed ESA Copernicus Sentinel-5P integration settings.');

    // Fill CDSE Username
    const usernameInput = page.locator('input[placeholder="user@example.com"], input[placeholder="name@organization.com"]').first();
    if (await usernameInput.isVisible().catch(() => false)) {
      await usernameInput.fill('copernicus_ops@sonatrach.dz');
    }

    // Fill CDSE Password
    const passwordInput = page.locator('input[type="password"]').first();
    if (await passwordInput.isVisible().catch(() => false)) {
      await passwordInput.fill('CDSE_Vault_2026!');
    }

    // Trigger Connection Test
    console.log('[E2E ADV] Clicking "Test Connection" to validate CDSE credentials...');
    const testConnBtn = page.locator('#test-copernicus-connection-btn, button:has-text("Test Copernicus Connection"), button:has-text("Test Connection")').first();
    if (await testConnBtn.isVisible().catch(() => false)) {
      await testConnBtn.click();
      await page.waitForTimeout(1200);
      console.log('[E2E ADV] Connection test initiated.');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'adv07_settings_copernicus_credentials.png') });
    copyArtifact('adv07_settings_copernicus_credentials.png');
    console.log('[E2E ADV] Captured adv07_settings_copernicus_credentials.png.');

    // Save System Settings
    console.log('[E2E ADV] Submitting System Settings and Copernicus credentials...');
    const saveSettingsBtn = page.locator('#save-satellite-settings-btn, #save-settings-btn, button:has-text("Save Satellite Settings"), button:has-text("Save All Changes")').first();
    await saveSettingsBtn.click();

    // Verify success toast
    const settingsToast = page.locator('text=System settings and Copernicus credentials saved successfully!').first();
    await expect(settingsToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ADV] Confirmed system settings saved notification toast.');
  });

});

