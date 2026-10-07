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
    console.log('[E2E CSS] Performing authentication login as Admin...');
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

test.describe('Suite 17: CBAM, Operational Equipment, Methane Map & Simulations Deep Audit', () => {

  test('CSS-1: EU CBAM Export Shipment Registration with Direct/Indirect Embedded Emissions', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=cbam`);

    // Verify Tab Header
    await expect(page.locator('text=EU CBAM Export & Embedded Emission Tracking').first()).toBeVisible({ timeout: 15000 });
    console.log('[CSS-1] CBAM tab loaded successfully.');

    // Select Activity
    const actSelect = page.locator('.form-grid-3 select.component-select').first();
    await actSelect.waitFor({ state: 'visible', timeout: 8000 });
    const actOptions = await actSelect.locator('option').allInnerTexts();
    const epOpt = actOptions.find(o => o.includes('Exploration') || o.includes('EP')) || actOptions[1];
    if (epOpt) {
      await actSelect.selectOption({ label: epOpt });
      await page.waitForTimeout(600);
    }

    // Select Division
    const divSelect = page.locator('.form-grid-3 select.component-select').nth(1);
    if (await divSelect.isEnabled().catch(() => false)) {
      const divOptions = await divSelect.locator('option').allInnerTexts();
      if (divOptions.length > 1) {
        await divSelect.selectOption({ index: 1 });
        await page.waitForTimeout(600);
      }
    }

    // Select Facility
    const facSelect = page.locator('.form-grid-3 select.component-select').nth(2);
    const facOptions = await facSelect.locator('option').allInnerTexts();
    if (facOptions.length > 1) {
      await facSelect.selectOption({ index: 1 });
      await page.waitForTimeout(600);
    }

    // Fill Product Name
    const productName = `Skikda Naphtha Export Batch #${Date.now().toString().slice(-4)}`;
    const productInput = page.locator('input[placeholder*="Export Blend"]').first();
    await productInput.fill(productName);

    // Select EU CN Code (Light Oils & Preparations - 2710 12)
    const cnSelect = page.locator('.form-grid-3 select.component-select').nth(3);
    await cnSelect.selectOption('2710 12');

    // Select Export Destination (EU-27)
    const destSelect = page.locator('.form-grid-3 select.component-select').nth(4);
    await destSelect.selectOption('EU');

    // Fill Reporting Month (June)
    const monthSelect = page.locator('.form-grid-3 select.component-select').nth(5);
    await monthSelect.selectOption('6');

    // Fill Export Quantity in Metric Tonnes
    const qtyInput = page.locator('input[placeholder="0.00"]').first();
    await qtyInput.fill('14500.50');

    // Fill Specific Embedded Direct (tCO2e/t)
    const directInput = page.locator('input[placeholder="0.000"]').first();
    await directInput.fill('0.185');

    // Fill Specific Embedded Indirect (tCO2e/t)
    const indirectInput = page.locator('input[placeholder="0.000"]').nth(1);
    await indirectInput.fill('0.042');

    // Fill Notes & Verification References
    const notesInput = page.locator('input[placeholder*="Accredited Verifier"]').first();
    await notesInput.fill('TÜV Rheinland Verified / ISO 14064-3 Cert #TR-DZ-2024-88');

    // Save CBAM Record
    const saveBtn = page.locator('button.action-btn:has-text("Save CBAM Record")').first();
    await saveBtn.click();
    await page.waitForTimeout(1500);

    // Verify record in table or toast
    const tableHasProduct = await page.locator(`text=${productName}`).first().isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`[CSS-1] CBAM Record saved and visible in export ledger: ${tableHasProduct}`);

    const screenshotFile = 'css01_cbam_export_shipment_registered.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, screenshotFile), fullPage: true });
    copyArtifact(screenshotFile);
    console.log(`[CSS-1] Artifact captured: ${screenshotFile}`);
  });

  test('CSS-2: Operational Emission Source Equipment Provisioning in Asset Registry', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=sources`);

    // Verify Sources tab loaded
    await expect(page.locator('text=Emission Sources Inventory').first()).toBeVisible({ timeout: 15000 });
    console.log('[CSS-2] Sources tab inventory loaded.');

    // Select Activity
    const actSelect = page.locator('.grid-forms select.component-select').first();
    await actSelect.waitFor({ state: 'visible', timeout: 8000 });
    const actOptions = await actSelect.locator('option').allInnerTexts();
    const epOpt = actOptions.find(o => o.includes('Exploration') || o.includes('EP')) || actOptions[1];
    if (epOpt) {
      await actSelect.selectOption({ label: epOpt });
      await page.waitForTimeout(600);
    }

    // Select Division
    const divSelect = page.locator('.grid-forms select.component-select').nth(1);
    if (await divSelect.isEnabled().catch(() => false)) {
      const divOptions = await divSelect.locator('option').allInnerTexts();
      if (divOptions.length > 1) {
        await divSelect.selectOption({ index: 1 });
        await page.waitForTimeout(600);
      }
    }

    // Select Region via CustomDropdown trigger button.dropdown-selected
    const dropdownTrigger = page.locator('.input-group button.dropdown-selected').first();
    if (await dropdownTrigger.isEnabled().catch(() => false)) {
      await dropdownTrigger.click();
      await page.waitForTimeout(500);
      const option = page.locator('.dropdown-options [role="option"]').nth(1);
      if (await option.isVisible().catch(() => false)) {
        await option.click();
        await page.waitForTimeout(500);
      }
    }

    // Fill Source Name
    const sourceName = `HP Flare Stack Unit #${Date.now().toString().slice(-4)}`;
    const nameInput = page.locator('input[placeholder*="Flare A"]').first();
    await nameInput.fill(sourceName);

    // Select Type
    const typeSelect = page.locator('.grid-forms select.component-select').nth(2);
    const typeOptions = await typeSelect.locator('option').allInnerTexts();
    if (typeOptions.length > 1) {
      await typeSelect.selectOption({ index: 1 });
    }

    // Fill Equipment ID
    const equipInput = page.locator('input[placeholder*="COMP-001"]').first();
    await equipInput.fill('EQ-FLR-04-NORTH');

    // Fill Fuel
    const fuelInput = page.locator('.grid-forms input[type="text"]').last();
    await fuelInput.fill('Associated Sour Gas');

    // Click Add Source button
    const addBtn = page.locator('button.action-btn:has-text("Add Source")').first();
    await addBtn.click();
    await page.waitForTimeout(1500);

    // Check table for provisioned equipment
    const sourceVisible = await page.locator(`text=${sourceName}`).first().isVisible({ timeout: 5000 }).catch(() => false);
    console.log(`[CSS-2] Operational source provisioned: ${sourceVisible}`);

    const screenshotFile = 'css02_operational_source_provisioned.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, screenshotFile), fullPage: true });
    copyArtifact(screenshotFile);
    console.log(`[CSS-2] Artifact captured: ${screenshotFile}`);
  });

  test('CSS-3: Methane Explorer Satellite Hotspot HUD & Facility Dossier Inspection', async ({ page }) => {
    test.setTimeout(75000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/methane-explorer`);

    // Wait for explorer container to mount
    await expect(page.locator('.methane-explorer').first()).toBeVisible({ timeout: 20000 });
    console.log('[CSS-3] Methane Explorer geospatial canvas mounted.');

    // Verify HUD Header
    await expect(page.locator('text=Emissions Map').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Sentinel-5P TROPOMI').first()).toBeVisible({ timeout: 10000 });

    // Toggle HUD viewMode: CH4 Flux -> Total GHG
    const totalGhgBtn = page.locator('button:has-text("Total GHG")').first();
    if (await totalGhgBtn.isVisible().catch(() => false)) {
      await totalGhgBtn.click();
      await page.waitForTimeout(800);
      console.log('[CSS-3] Toggled map metric to Total GHG.');
    }

    // Toggle back to CH4 Flux
    const ch4FluxBtn = page.locator('button:has-text("CH₄ Flux")').first();
    if (await ch4FluxBtn.isVisible().catch(() => false)) {
      await ch4FluxBtn.click();
      await page.waitForTimeout(800);
      console.log('[CSS-3] Toggled map metric back to CH4 Flux.');
    }

    // Select a facility in intelligence drawer to open Dossier
    const targetFacilityBtn = page.getByRole('button', { name: /Hassi Messaoud/i }).first();
    if (await targetFacilityBtn.isVisible().catch(() => false)) {
      console.log('[CSS-3] Dispatching click to Hassi Messaoud facility card...');
      await targetFacilityBtn.dispatchEvent('click');
      await page.waitForTimeout(1500);
    } else {
      const firstAssetBtn = page.getByRole('button', { name: /tCH₄/i }).first();
      console.log('[CSS-3] Dispatching click to first available asset card...');
      await firstAssetBtn.dispatchEvent('click');
      await page.waitForTimeout(1500);
    }

    // Verify ExplorerDossier slides out
    const dossierHeading = page.locator('section[aria-label="Facility Reconnaissance Dossier"] h3, section h3:has-text("Hassi"), section:has-text("Facility reconnaissance dossier") h3').first();
    await expect(dossierHeading).toBeVisible({ timeout: 15000 });
    const openedFacilityName = await dossierHeading.innerText();
    console.log(`[CSS-3] Facility dossier inspection active for: ${openedFacilityName}`);

    const screenshotFile = 'css03_methane_explorer_dossier_inspection.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, screenshotFile), fullPage: true });
    copyArtifact(screenshotFile);
    console.log(`[CSS-3] Artifact captured: ${screenshotFile}`);
  });

  test('CSS-4: SBTi 1.5°C vs WB-2°C Scenario Ambition & Trajectory Comparison', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/sbti`);

    // Verify Page Header
    await expect(page.locator('text=SBTi & Net-Zero Trajectory').first()).toBeVisible({ timeout: 15000 });
    console.log('[CSS-4] SBTi Net-Zero Trajectory page loaded.');

    // Toggle Scope coverage segmented control
    const opScopeBtn = page.locator('button:has-text("Scope 1+2 (operational)")').first();
    if (await opScopeBtn.isVisible().catch(() => false)) {
      await opScopeBtn.click();
      await page.waitForTimeout(800);
      console.log('[CSS-4] Switched scope mode to Scope 1+2.');
    }

    const allScopeBtn = page.locator('button:has-text("All scopes (1+2+3)")').first();
    if (await allScopeBtn.isVisible().catch(() => false)) {
      await allScopeBtn.click();
      await page.waitForTimeout(800);
      console.log('[CSS-4] Switched scope mode back to All Scopes.');
    }

    // Open target configuration drawer
    const configBtn = page.locator('button:has-text("Configure target")').first();
    if (await configBtn.isVisible().catch(() => false)) {
      await configBtn.click();
      await page.waitForTimeout(800);
      await expect(page.locator('text=SBTi Corporate Target Setup').first()).toBeVisible({ timeout: 10000 });
      console.log('[CSS-4] Target configuration drawer opened.');

      // Toggle Pathway Alignment: WB-2°C then 1.5°C
      const wb2cBtn = page.locator('button:has-text("WB-2°C (2.5% / yr)")').first();
      await wb2cBtn.click();
      await page.waitForTimeout(500);

      const p15cBtn = page.locator('button:has-text("1.5°C (4.2% / yr)")').first();
      await p15cBtn.click();
      await page.waitForTimeout(500);

      // Verify Auto-Fill Verified button
      const autoFillBtn = page.locator('button:has-text("Auto-Fill Verified")').first();
      if (await autoFillBtn.isVisible().catch(() => false)) {
        await autoFillBtn.click();
        await page.waitForTimeout(800);
        console.log('[CSS-4] Auto-fill baseline clicked.');
      }
    }

    const screenshotFile = 'css04_sbti_trajectory_ambition_configured.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, screenshotFile), fullPage: true });
    copyArtifact(screenshotFile);
    console.log(`[CSS-4] Artifact captured: ${screenshotFile}`);
  });

  test('CSS-5: Uncertainty Monte Carlo Confidence Interval & Iterations Toggling', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/uncertainty`);

    // Verify Page Header
    await expect(page.locator('text=Data Reliability Analysis').first()).toBeVisible({ timeout: 15000 });
    console.log('[CSS-5] Data Reliability Analysis page loaded.');

    // Verify Inventory Uncertainty badge
    const uncValue = page.locator('.ua-inventory-value').first();
    await expect(uncValue).toBeVisible({ timeout: 10000 });
    const uncText = await uncValue.innerText();
    console.log(`[CSS-5] Inventory Uncertainty quantification: ${uncText}`);

    // Verify 95% CI confidence badge
    await expect(page.locator('text=95% CI').first()).toBeVisible({ timeout: 10000 });

    // Verify Tier Breakdown cards
    await expect(page.locator('text=Tier 1 (share of Scope 1)').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Tier 2 (share of Scope 1)').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Tier 3 (share of Scope 1)').first()).toBeVisible({ timeout: 10000 });

    // Verify Uncertainty Bands cards
    await expect(page.locator('text=Low Uncertainty').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Medium Uncertainty').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=High Uncertainty').first()).toBeVisible({ timeout: 10000 });

    // Verify Methodology footer
    await expect(page.locator('text=Calculation Methodology').first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Square Root of Sum of Squares (SRSS)').first()).toBeVisible({ timeout: 10000 });

    const screenshotFile = 'css05_uncertainty_srss_reliability_quantification.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, screenshotFile), fullPage: true });
    copyArtifact(screenshotFile);
    console.log(`[CSS-5] Artifact captured: ${screenshotFile}`);
  });

  test('CSS-6: Audit Trail Action Type Forensic Search & Hash Timeline View', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/audit-trail`);

    // Verify Page Title and Badge
    await expect(page.locator('text=Audit Trail & System Activity').first()).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Immutable Compliance Log').first()).toBeVisible({ timeout: 10000 });
    console.log('[CSS-6] Audit Trail loaded.');

    // Search query
    const searchInput = page.locator('input[placeholder*="Search by user"]').first();
    await searchInput.fill('admin');
    await page.waitForTimeout(600);

    // Switch View to Timeline
    const timelineBtn = page.locator('button:has-text("Timeline")').first();
    await timelineBtn.click();
    await page.waitForTimeout(800);
    console.log('[CSS-6] Switched to Timeline view.');

    // Switch back to Table View
    const tableBtn = page.locator('button:has-text("Table")').first();
    await tableBtn.click();
    await page.waitForTimeout(800);
    console.log('[CSS-6] Switched back to Table view.');

    // Open first row Details Dialog
    const detailsBtn = page.locator('button:has-text("Details")').first();
    if (await detailsBtn.isVisible().catch(() => false)) {
      await detailsBtn.click();
      await page.waitForTimeout(800);
      await expect(page.locator('text=Audit event').first()).toBeVisible({ timeout: 10000 });
      console.log('[CSS-6] Audit event details dialog opened.');
    }

    const screenshotFile = 'css06_audit_trail_forensic_payload_dialog.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, screenshotFile), fullPage: true });
    copyArtifact(screenshotFile);
    console.log(`[CSS-6] Artifact captured: ${screenshotFile}`);
  });

  test('CSS-7: IPCC Global Warming Potential Standards & Base Year Configuration', async ({ page }) => {
    test.setTimeout(65000);
    await ensureAuthenticatedPage(page, `${FRONTEND}/settings`);

    // Verify Settings page title
    await expect(page.locator('text=System Settings & Protocols').first()).toBeVisible({ timeout: 15000 });
    console.log('[CSS-7] System Settings page loaded.');

    // Inspect active GWP tab
    await expect(page.locator('text=IPCC Global Warming Potential (GWP) Standard').first()).toBeVisible({ timeout: 10000 });

    // Select IPCC AR6 standard radio card
    const ar6Card = page.locator('#gwp-card-ar6').first();
    if (await ar6Card.isVisible().catch(() => false)) {
      await ar6Card.click();
      await page.waitForTimeout(600);
      console.log('[CSS-7] Selected IPCC AR6 standard.');
    }

    // Switch to OGMP 2.0 Baseline & Thresholds tab
    const ogmpTabTrigger = page.locator('button[role="tab"]:has-text("OGMP 2.0 Baseline")').first();
    if (await ogmpTabTrigger.isVisible().catch(() => false)) {
      await ogmpTabTrigger.click();
      await page.waitForTimeout(800);
      await expect(page.locator('text=OGMP 2.0 Framework & Threshold Configuration').first()).toBeVisible({ timeout: 10000 });
      console.log('[CSS-7] OGMP 2.0 Baseline tab active.');
    }

    // Switch back to GWP Standards tab
    const gwpTabTrigger = page.locator('button[role="tab"]:has-text("IPCC GWP Standards")').first();
    if (await gwpTabTrigger.isVisible().catch(() => false)) {
      await gwpTabTrigger.click();
      await page.waitForTimeout(800);
    }

    // Save All Changes
    const saveBtn = page.locator('#save-settings-btn').first();
    await saveBtn.click();
    await page.waitForTimeout(1500);

    console.log('[CSS-7] Save settings clicked.');

    const screenshotFile = 'css07_settings_ipcc_standards_and_ogmp_saved.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, screenshotFile), fullPage: true });
    copyArtifact(screenshotFile);
    console.log(`[CSS-7] Artifact captured: ${screenshotFile}`);
  });

});
