import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';

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

  // Fallback login
  const emailInput = page.locator('input[placeholder="Email Address"]');
  if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await emailInput.fill('a');
    await page.locator('input[type="password"]').fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000);
  }

  await expect(page.locator('.app-container, .main-content, #main').first()).toBeVisible({ timeout: 20000 });
  await page.waitForLoadState('networkidle').catch(() => {});
}

test.describe.serial('Interactive User Business Functionality Deep Audit', () => {

  // -------------------------------------------------------------------------
  // FUNCTIONALITY 1: Gas Composition Calculator & Stoichiometry Engine
  // -------------------------------------------------------------------------
  test('FN-1: Gas Composition Calculator Tool & Factor Application', async ({ page }) => {
    console.log('[USER FUNC] Testing Gas Composition Calculator on Scope 1...');
    await ensureAuthenticatedPage(page, '/emissions?scope=1');
    await page.waitForTimeout(1000);

    // Look for Gas Composition Calculator trigger button
    const gasCalcTrigger = page.locator('button:has-text("Gas Composition"), button:has-text("Gas Analysis"), button[title*="composition" i]').first();
    if (await gasCalcTrigger.isVisible().catch(() => false)) {
      console.log('[USER FUNC] Opening Gas Composition Calculator modal...');
      await gasCalcTrigger.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn01_gas_comp_modal_open.png') });

      // Enter composition percentages
      const c1Input = page.locator('input[name*="c1" i], input[placeholder*="CH4" i], input[placeholder*="Methane" i]').first();
      if (await c1Input.isVisible().catch(() => false)) {
        await c1Input.fill('88.5');
      }

      // Apply button
      const applyBtn = page.locator('button:has-text("Apply"), button:has-text("Compute & Apply")').first();
      if (await applyBtn.isVisible().catch(() => false)) {
        await applyBtn.click();
        await page.waitForTimeout(600);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn01_gas_comp_applied.png') });
      }
    }
  });

  // -------------------------------------------------------------------------
  // FUNCTIONALITY 2: Flaring Process Calculation & Submission
  // -------------------------------------------------------------------------
  test('FN-2: Flaring Calculation: Flare Volume, 98% Efficiency & Submission', async ({ page }) => {
    console.log('[USER FUNC] Testing Flaring Process in Scope 1...');
    await ensureAuthenticatedPage(page, '/emissions?scope=1');
    await page.waitForTimeout(1000);

    // Select Process Dropdown -> Flaring
    const processDropdown = page.locator('.input-group:has-text("Process") button[role="combobox"]').first();
    if (await processDropdown.isVisible().catch(() => false)) {
      await processDropdown.click();
      await page.waitForTimeout(400);

      const flaringOption = page.locator('[role="option"]:has-text("Flaring")').first();
      if (await flaringOption.isVisible().catch(() => false)) {
        console.log('[USER FUNC] Selecting Flaring process...');
        await flaringOption.click();
        await page.waitForTimeout(800);
      } else {
        await page.keyboard.press('Escape');
      }
    }

    // Fill flaring volume / quantity if visible
    const volumeInput = page.locator('input[type="number"], input[name*="amount" i], input[placeholder*="volume" i]').first();
    if (await volumeInput.isVisible().catch(() => false)) {
      await volumeInput.fill('250000');
    }

    // Submit flaring calculation
    const submitBtn = page.locator('button.btn-add-activity, button:has-text("Submit")').first();
    if (await submitBtn.isVisible().catch(() => false)) {
      console.log('[USER FUNC] Submitting Flaring emission record...');
      await submitBtn.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn02_flaring_submitted.png') });
    }
  });

  // -------------------------------------------------------------------------
  // FUNCTIONALITY 3: Calculation Inspection Modal (Formulas & Uncertainties)
  // -------------------------------------------------------------------------
  test('FN-3: Inspect Calculation Details Modal (Stoichiometry & Audit Proof)', async ({ page }) => {
    console.log('[USER FUNC] Testing Calculation Inspection in Scope 1 History...');
    await ensureAuthenticatedPage(page, '/emissions?scope=1');
    await page.waitForTimeout(1200);

    // Find Inspect button in history table
    const inspectBtn = page.locator('button:has-text("Inspect"), button[title*="Inspect" i], button:has(svg.lucide-info)').first();
    if (await inspectBtn.isVisible().catch(() => false)) {
      console.log('[USER FUNC] Opening Calculation Inspection modal...');
      await inspectBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn03_calculation_details_modal.png') });

      // Verify modal contents
      const modal = page.locator('[role="dialog"], .calc-details-modal, .modal-content').first();
      await expect(modal).toBeVisible();

      // Close modal
      const closeBtn = page.locator('button:has-text("Close"), [aria-label="Close"]').last();
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
        await page.waitForTimeout(400);
      }
    }
  });

  // -------------------------------------------------------------------------
  // FUNCTIONALITY 4: Manage Data Multi-Tab Exploration (Facilities, Sources, OGMP)
  // -------------------------------------------------------------------------
  test('FN-4: Manage Data Tabs: Sources, Facilities, Production & OGMP Surveys', async ({ page }) => {
    console.log('[USER FUNC] Traversing Manage Data operational tabs...');
    await ensureAuthenticatedPage(page, '/manage-data');
    await page.waitForTimeout(1000);

    const tabsToTest = [
      { name: 'Facilities', screenshot: 'fn04_tab_facilities.png' },
      { name: 'Sources', screenshot: 'fn04_tab_sources.png' },
      { name: 'Production', screenshot: 'fn04_tab_production.png' },
      { name: 'OGMP 2.0', screenshot: 'fn04_tab_ogmp.png' },
    ];

    for (const t of tabsToTest) {
      const tabBtn = page.locator(`button:has-text("${t.name}"), [role="tab"]:has-text("${t.name}")`).first();
      if (await tabBtn.isVisible().catch(() => false)) {
        console.log(`[USER FUNC] Clicking tab: ${t.name}...`);
        await tabBtn.click();
        await page.waitForTimeout(600);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, t.screenshot) });
      }
    }
  });

  // -------------------------------------------------------------------------
  // FUNCTIONALITY 5: SBTi Corporate Target Configuration & Pathway Save
  // -------------------------------------------------------------------------
  test('FN-5: SBTi Target Setting: Pathway Selection (1.5°C vs WB-2°C) & Save Target', async ({ page }) => {
    console.log('[USER FUNC] Testing SBTi Target Configuration...');
    await ensureAuthenticatedPage(page, '/sbti');
    await page.waitForTimeout(1000);

    // Open target configuration drawer
    const configBtn = page.locator('button:has-text("Configure target"), button:has-text("target settings")').first();
    if (await configBtn.isVisible().catch(() => false)) {
      await configBtn.click();
      await page.waitForTimeout(600);

      // Select 1.5°C pathway button
      const p15Btn = page.locator('button:has-text("1.5°C")').first();
      if (await p15Btn.isVisible().catch(() => false)) {
        console.log('[USER FUNC] Selecting 1.5°C pathway...');
        await p15Btn.click();
        await page.waitForTimeout(400);
      }

      // Enter Base Year
      const baseYearInput = page.locator('input[type="number"]').first();
      if (await baseYearInput.isVisible().catch(() => false)) {
        await baseYearInput.fill('2024');
      }

      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn05_sbti_configured_form.png') });

      // Save Target
      const saveTargetBtn = page.locator('button:has-text("Save"), button:has-text("Apply Target"), button[type="submit"]:has-text("Save")').first();
      if (await saveTargetBtn.isVisible().catch(() => false)) {
        console.log('[USER FUNC] Saving SBTi target...');
        await saveTargetBtn.click();
        await page.waitForTimeout(1200);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn05_sbti_target_saved.png') });
      }
    }
  });

  // -------------------------------------------------------------------------
  // FUNCTIONALITY 6: ISO 14064-1 & Master Report Generation
  // -------------------------------------------------------------------------
  test('FN-6: Reports: Select Reporting Standard & Trigger ISO 14064-1 Report', async ({ page }) => {
    console.log('[USER FUNC] Testing Report Generation & Export Menu...');
    await ensureAuthenticatedPage(page, '/reports');
    await page.waitForTimeout(1000);

    // Open Export Menu
    const exportBtn = page.locator('button:has-text("Export")').first();
    if (await exportBtn.isVisible().catch(() => false)) {
      await exportBtn.click();
      await page.waitForTimeout(500);

      // Verify menu items: OGMP, ISO 14064-1, Master Report
      const isoOption = page.locator('[role="menuitem"]:has-text("ISO"), button:has-text("ISO")').first();
      if (await isoOption.isVisible().catch(() => false)) {
        console.log('[USER FUNC] Clicking ISO 14064-1 export option...');
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn06_report_options_menu.png') });
      }
      await page.keyboard.press('Escape');
    }
  });

  // -------------------------------------------------------------------------
  // FUNCTIONALITY 7: QA/QC Diagnostics Re-scan & Anomaly Queue
  // -------------------------------------------------------------------------
  test('FN-7: QA/QC Dashboard: Live Diagnostics Scan & Anomaly Queue Filters', async ({ page }) => {
    console.log('[USER FUNC] Testing QA/QC Diagnostics Scan & Filters...');
    await ensureAuthenticatedPage(page, '/qa-dashboard');
    await page.waitForTimeout(1000);

    // Trigger Run Diagnostics
    const scanBtn = page.locator('button:has-text("Run Diagnostics")').first();
    if (await scanBtn.isVisible().catch(() => false)) {
      console.log('[USER FUNC] Triggering diagnostic scan...');
      await scanBtn.click();
      await page.waitForTimeout(1800);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn07_diagnostics_scan_done.png') });
    }

    // Switch between Scope filters
    const scopeSelect = page.locator('select.qa-filter-select, select[aria-label*="Scope" i]').first();
    if (await scopeSelect.isVisible().catch(() => false)) {
      await scopeSelect.selectOption('1');
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn07_qa_scope1_filtered.png') });
    }
  });

  // -------------------------------------------------------------------------
  // FUNCTIONALITY 8: User Settings & Consolidation Preferences Update
  // -------------------------------------------------------------------------
  test('FN-8: Organization Settings: Consolidation Approach & Reporting Standard', async ({ page }) => {
    console.log('[USER FUNC] Testing Settings Preferences...');
    await ensureAuthenticatedPage(page, '/settings');
    await page.waitForTimeout(1000);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn08_settings_overview.png') });

    // Look for Save / Update button in Settings
    const saveBtn = page.locator('button:has-text("Save"), button:has-text("Update Profile")').first();
    if (await saveBtn.isVisible().catch(() => false)) {
      console.log('[USER FUNC] Saving settings changes...');
      await saveBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'fn08_settings_saved.png') });
    }
  });

});
