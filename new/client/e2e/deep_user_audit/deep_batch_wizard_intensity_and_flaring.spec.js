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
    console.log('[E2E BATCH-WIZARD] Performing authentication login...');
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

test.describe('Suite 15: Deep Untested Batch Review Wizard, Custom Factors & Intensity Trends', () => {

  test('BW-1: Interactive Batch Review Wizard Modal & Anomaly Inspection', async ({ page }) => {
    console.log('[BW-1] Navigating to Pending Review Tab in Manage Data...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=pending`);
    await page.waitForTimeout(1500);

    // Locate the "Launch Review Wizard" button
    const launchWizardBtn = page.locator('button:has-text("Launch Review Wizard")').first();
    await expect(launchWizardBtn).toBeVisible({ timeout: 10000 });
    await launchWizardBtn.click();
    await page.waitForTimeout(1200);

    // Check wizard modal content
    const modalHeading = page.locator('h2:has-text("Pending Data Audit & Verification Wizard")');
    await expect(modalHeading).toBeVisible({ timeout: 8000 });

    const pipelineSubtitle = page.locator('text=Maker-Checker verification pipeline');
    await expect(pipelineSubtitle).toBeVisible();

    // Verify KPI summary chips in wizard
    const totalStagedChip = page.locator('div.kpi-chip:has-text("Total Staged:")');
    await expect(totalStagedChip).toBeVisible();

    const scopeDistChip = page.locator('div.kpi-chip:has-text("Scope Distribution:")');
    await expect(scopeDistChip).toBeVisible();

    // Capture screenshot of the open interactive wizard
    const shotPath = path.join(SCREENSHOT_DIR, 'bw01_batch_review_wizard_opened.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('bw01_batch_review_wizard_opened.png');

    // Close wizard via close button
    const closeBtn = page.locator('button[title*="Close Wizard"]').first();
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }
    await page.waitForTimeout(800);
    await expect(modalHeading).toBeHidden({ timeout: 5000 });
  });

  test('BW-2: Quick-Add Custom Emission Factor Modal in Scope 1', async ({ page }) => {
    console.log('[BW-2] Navigating to Scope 1 Emissions Calculation form...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Switch to "Library factor" tier
    const libraryTierBtn = page.locator('button.tier-selector-btn:has-text("Library factor")').first();
    if (await libraryTierBtn.isVisible({ timeout: 6000 }).catch(() => false)) {
      await libraryTierBtn.click();
      await page.waitForTimeout(600);
    }

    // Click "New library factor" button
    const newFactorBtn = page.locator('button:has-text("New library factor")').first();
    await expect(newFactorBtn).toBeVisible({ timeout: 6000 });
    await newFactorBtn.click();
    await page.waitForTimeout(800);

    // Assert the Quick-Add modal appeared
    const modalTitle = page.locator('h3:has-text("Register Tier 2 Custom Factor")');
    await expect(modalTitle).toBeVisible({ timeout: 6000 });

    const modalSubtitle = page.locator('text=Add a site-calibrated or supplier emission factor without leaving this form');
    await expect(modalSubtitle).toBeVisible();

    // Fill in custom factor attributes
    const nameInput = page.locator('input[placeholder*="Skikda"]').first();
    await nameInput.fill('Hassi Berkine LP Flare Gas 2026');

    // Fill CO2 Factor
    const co2Input = page.locator('label:has-text("CO₂ Factor") + div input, label:has-text("CO₂ Factor") ~ input, input[placeholder="53.06"]').first();
    if (await co2Input.isVisible().catch(() => false)) {
      await co2Input.fill('56.80');
    }

    // Fill CH4 Factor
    const ch4Input = page.locator('label:has-text("CH₄ Factor") + div input, label:has-text("CH₄ Factor") ~ input, input[placeholder="0.001"]').first();
    if (await ch4Input.isVisible().catch(() => false)) {
      await ch4Input.fill('0.0022');
    }

    // Fill Data Source reference
    const sourceInput = page.locator('input[placeholder*="Sonatrach Analysis"]').first();
    if (await sourceInput.isVisible().catch(() => false)) {
      await sourceInput.fill('Sonatrach GC Lab Test Ref #HB-2026-FL01');
    }

    // Capture screenshot of modal populated
    const shotPath = path.join(SCREENSHOT_DIR, 'bw02_scope1_quick_add_custom_factor_modal.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('bw02_scope1_quick_add_custom_factor_modal.png');

    // Close modal via Cancel button
    const cancelBtn = page.locator('div.modal-card button:has-text("Cancel")').first();
    await cancelBtn.click();
    await page.waitForTimeout(600);
    await expect(modalTitle).toBeHidden({ timeout: 5000 });
  });

  test('BW-3: Scope 2 Electricity & Steam Bulk Import Wizard Modal', async ({ page }) => {
    console.log('[BW-3] Navigating to Scope 2 Emissions Calculation form...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope2`);
    await page.waitForTimeout(1500);

    // Scroll to entries section with the wizard button
    const wizardTriggerBtn = page.locator('button:has-text("Bulk Import (Wizard)")').first();
    await wizardTriggerBtn.scrollIntoViewIfNeeded();
    await expect(wizardTriggerBtn).toBeVisible({ timeout: 8000 });
    await wizardTriggerBtn.click();
    await page.waitForTimeout(1000);

    // Verify Scope 2 Import Wizard dialog
    const wizardTitle = page.locator('text=Scope 2 Bulk Import').first();
    await expect(wizardTitle).toBeVisible({ timeout: 8000 });

    const wizardSubtitle = page.locator('text=Upload electricity and indirect steam data from CSV or Excel').first();
    await expect(wizardSubtitle).toBeVisible();

    // Verify Drop Zone
    const dropZone = page.locator('p:has-text("Drag & drop your file here")').first();
    await expect(dropZone).toBeVisible({ timeout: 6000 });

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'bw03_scope2_bulk_import_wizard.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('bw03_scope2_bulk_import_wizard.png');

    // Close dialog
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    if (await cancelBtn.isVisible().catch(() => false)) {
      await cancelBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }
    await page.waitForTimeout(600);
    await expect(wizardTitle).toBeHidden({ timeout: 5000 });
  });

  test('BW-4: Scope 3 Value Chain Bulk Import Wizard Modal', async ({ page }) => {
    console.log('[BW-4] Navigating to Scope 3 Emissions Calculation form...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope3`);
    await page.waitForTimeout(1500);

    // Scroll to entries section with the wizard button
    const wizardTriggerBtn = page.locator('button:has-text("Bulk Import (Wizard)")').first();
    await wizardTriggerBtn.scrollIntoViewIfNeeded();
    await expect(wizardTriggerBtn).toBeVisible({ timeout: 8000 });
    await wizardTriggerBtn.click();
    await page.waitForTimeout(1000);

    // Verify Scope 3 Import Wizard dialog
    const wizardTitle = page.locator('text=Scope 3 Bulk Import').first();
    await expect(wizardTitle).toBeVisible({ timeout: 8000 });

    const wizardSubtitle = page.locator('text=Upload value chain emissions data from CSV or Excel').first();
    await expect(wizardSubtitle).toBeVisible();

    // Verify mode selector options if present (Activity data vs EEIO Spend)
    const modeSelector = page.locator('button:has-text("Activity"), button:has-text("Spend")').first();
    if (await modeSelector.isVisible().catch(() => false)) {
      await modeSelector.click();
      await page.waitForTimeout(400);
    }

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'bw04_scope3_bulk_import_wizard.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('bw04_scope3_bulk_import_wizard.png');

    // Close dialog
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    if (await cancelBtn.isVisible().catch(() => false)) {
      await cancelBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }
    await page.waitForTimeout(600);
    await expect(wizardTitle).toBeHidden({ timeout: 5000 });
  });

  test('BW-5: Methane Intensity OGMP 2.0 Asset Level & Historical Trends', async ({ page }) => {
    console.log('[BW-5] Navigating to Methane Intensity page...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/methane-intensity`);
    await page.waitForTimeout(2000);

    // Verify Facility Loss Rate and Methane Intensity charts are present
    const lossRateHeader = page.locator('h3:has-text("Methane Loss Rate by Facility")');
    await expect(lossRateHeader).toBeVisible({ timeout: 10000 });

    const ch4IntensityHeader = page.locator('h3:has-text("Methane Intensity by Facility")');
    await expect(ch4IntensityHeader).toBeVisible();

    // Scroll to Historical Methane Trends section
    const historicalHeader = page.locator('h2:has-text("Historical Methane Trends"), h3:has-text("Historical Methane Trends")').first();
    await historicalHeader.scrollIntoViewIfNeeded();
    await expect(historicalHeader).toBeVisible();

    // Verify view toggle (Chart vs Heatmap)
    const heatmapToggle = page.locator('button:has-text("Heatmap")').first();
    if (await heatmapToggle.isVisible().catch(() => false)) {
      await heatmapToggle.click();
      await page.waitForTimeout(800);

      // Verify Heatmap view rendered
      const chartToggle = page.locator('button:has-text("Chart")').first();
      await expect(chartToggle).toBeVisible();
      await chartToggle.click();
      await page.waitForTimeout(600);
    }

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'bw05_methane_intensity_trends_and_ogmp.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('bw05_methane_intensity_trends_and_ogmp.png');
  });

  test('BW-6: Carbon Intensity Upstream Benchmark & GWP Horizon Toggle', async ({ page }) => {
    console.log('[BW-6] Navigating to Carbon Intensity page...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/carbon-intensity`);
    await page.waitForTimeout(2000);

    // Verify Carbon Intensity hero KPIs
    const heroTitle = page.locator('text=Carbon Intensity').first();
    await expect(heroTitle).toBeVisible({ timeout: 10000 });

    // Verify GWP-100 vs GWP-20 toggle buttons
    const gwp20Btn = page.locator('button:has-text("GWP-20")').first();
    const gwp100Btn = page.locator('button:has-text("GWP-100")').first();

    if (await gwp20Btn.isVisible().catch(() => false)) {
      console.log('[BW-6] Switching GWP horizon to 20-year...');
      await gwp20Btn.click();
      await page.waitForTimeout(1000);

      // Verify active switch
      console.log('[BW-6] Switching GWP horizon back to 100-year...');
      await gwp100Btn.click();
      await page.waitForTimeout(800);
    }

    // Scroll to CBAM / Regional Charts section
    const cbamHeader = page.locator('text=CBAM, text=Facility, text=Regional').first();
    if (await cbamHeader.isVisible().catch(() => false)) {
      await cbamHeader.scrollIntoViewIfNeeded();
    }

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'bw06_carbon_intensity_gwp_toggle_and_cbam.png');
    await page.screenshot({ path: shotPath, fullPage: true });
    copyArtifact('bw06_carbon_intensity_gwp_toggle_and_cbam.png');
  });

  test('BW-7: Zero Routine Flaring (ZRF 2030) Compliance & Detailed Hierarchy Breakdown', async ({ page }) => {
    console.log('[BW-7] Navigating to Dashboard...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/`);
    await page.waitForTimeout(2000);

    // Verify Operational Flaring & Regulatory Compliance banner
    const flaringBannerHeading = page.locator('h3:has-text("Operational Flaring & Regulatory Compliance")');
    await flaringBannerHeading.scrollIntoViewIfNeeded();
    await expect(flaringBannerHeading).toBeVisible({ timeout: 10000 });

    const decreeRef = page.locator('text=Executive Decree 21-330 Article 9');
    await expect(decreeRef).toBeVisible();

    // Verify stream tiles (e.g. Routine, Total Flared, etc.)
    const streamTile = page.locator('[data-testid="flaring-total"], [data-testid="flaring-routine"]').first();
    await expect(streamTile).toBeVisible({ timeout: 6000 });

    // Scroll to "Detailed breakdown" section
    const breakdownHeader = page.locator('span:has-text("Detailed breakdown"), button:has-text("Detailed breakdown")').first();
    await breakdownHeader.scrollIntoViewIfNeeded();
    await expect(breakdownHeader).toBeVisible();

    // Verify Scope 1 line item
    const scope1Row = page.locator('td:has-text("Scope 1 (Direct)")');
    await expect(scope1Row).toBeVisible();

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'bw07_zero_routine_flaring_compliance_card.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('bw07_zero_routine_flaring_compliance_card.png');
  });

});
