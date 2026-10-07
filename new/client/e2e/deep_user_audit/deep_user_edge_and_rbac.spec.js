import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
const ARTIFACT_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\145e1f58-77e7-4f5b-8573-5a1c4dc13171';
const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';

function copyArtifact(filename) {
  try {
    const src = path.join(SCREENSHOT_DIR, filename);
    const dest = path.join(ARTIFACT_DIR, filename);
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dest);
    }
  } catch (err) {
    console.error(`Failed to copy artifact ${filename}:`, err);
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

test.describe.serial('Edge Workflows, RBAC Personas & Untested User Journeys', () => {

  // -------------------------------------------------------------------------
  // TEST 1: Standard Operator Persona & Route Guards
  // -------------------------------------------------------------------------
  test('EDGE-1: Operator Persona RBAC & Review Queue Restriction Notice', async ({ browser }) => {
    console.log('[USER RBAC] Launching unauthenticated session for Operator Persona...');
    const operatorContext = await browser.newContext({ storageState: undefined });
    const page = await operatorContext.newPage();

    await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    // Skip intro if present
    const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
    if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBtn.click();
      await page.waitForTimeout(400);
    }

    // Fill credentials for standard operator
    await page.locator('input[placeholder="Email Address"]').fill('operator@sonatrach.dz');
    await page.locator('input[placeholder="Password"]').fill('operator123');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();

    await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 15000 });
    await expect(page.locator('.app-container, .main-content').first()).toBeVisible();
    console.log('[USER RBAC] Operator successfully authenticated, landed on Dashboard.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge01_operator_dashboard.png') });
    copyArtifact('edge01_operator_dashboard.png');

    // 1. Operator attempts to access privileged pending review tab
    console.log('[USER RBAC] Operator navigating to /manage-data?tab=pending...');
    await page.goto(`${FRONTEND}/manage-data?tab=pending`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);

    // Verify PendingAccessNotice is rendered
    const accessNotice = page.locator('text=Review Permissions Required');
    await expect(accessNotice).toBeVisible({ timeout: 10000 });
    const noticeDesc = page.locator('text=corporate Maker-Checker governance rules');
    await expect(noticeDesc).toBeVisible();
    console.log('[USER RBAC] Verified PendingAccessNotice is displayed for unprivileged operator.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge01_operator_pending_restricted.png') });
    copyArtifact('edge01_operator_pending_restricted.png');

    // Click "Return to Emission Factors"
    const returnBtn = page.locator('button:has-text("Return to Emission Factors")');
    await expect(returnBtn).toBeVisible();
    await returnBtn.click();
    await page.waitForTimeout(800);

    // Verify view returned to Factors
    const factorsView = page.locator('h2:has-text("Custom Emission Factors")');
    await expect(factorsView).toBeVisible({ timeout: 10000 });

    // 2. Operator attempts to access IT route /user-management
    console.log('[USER RBAC] Operator attempting direct URL navigation to /user-management...');
    await page.goto(`${FRONTEND}/user-management`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);

    // Guard should redirect operator to '/'
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/user-management');
    console.log(`[USER RBAC] Operator properly quarantined: URL redirected to ${currentUrl}`);

    // 3. Operator attempts to access privileged Superuser route /qa-dashboard
    console.log('[USER RBAC] Operator attempting direct URL navigation to /qa-dashboard...');
    await page.goto(`${FRONTEND}/qa-dashboard`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);

    // Guard should redirect operator to '/'
    const qaUrl = page.url();
    expect(qaUrl).not.toContain('/qa-dashboard');
    console.log(`[USER RBAC] Operator properly blocked from QA: URL redirected to ${qaUrl}`);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge01_operator_redirect_home.png') });
    copyArtifact('edge01_operator_redirect_home.png');

    await operatorContext.close();
  });

  // -------------------------------------------------------------------------
  // TEST 2: IT Administrator Persona & Route Isolation Guard
  // -------------------------------------------------------------------------
  test('EDGE-2: IT Admin Persona Route Isolation & Quarantine Verification', async ({ browser }) => {
    console.log('[USER RBAC] Launching unauthenticated session for IT Admin Persona...');
    const itContext = await browser.newContext({ storageState: undefined });
    const page = await itContext.newPage();

    await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
    if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBtn.click();
      await page.waitForTimeout(400);
    }

    await page.locator('input[placeholder="Email Address"]').fill('itadmin@sonatrach.dz');
    await page.locator('input[placeholder="Password"]').fill('itadmin123');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();

    // IT admin logging in is denied access to '/' and automatically redirected to '/user-management'
    await page.waitForURL((url) => url.toString().includes('/user-management'), { timeout: 15000 });
    console.log('[USER RBAC] IT Admin successfully quarantined to /user-management.');
    await expect(page.locator('h1, h2').filter({ hasText: /User Management/i }).first()).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge02_itadmin_user_management.png') });
    copyArtifact('edge02_itadmin_user_management.png');

    // 1. IT admin attempts to visit operational route /emissions
    console.log('[USER RBAC] IT Admin attempting direct URL navigation to /emissions...');
    await page.goto(`${FRONTEND}/emissions`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
    expect(page.url()).toContain('/user-management');
    console.log('[USER RBAC] Verified IT Admin blocked from operational /emissions and redirected.');

    // 2. IT admin attempts to visit /reports
    console.log('[USER RBAC] IT Admin attempting direct URL navigation to /reports...');
    await page.goto(`${FRONTEND}/reports`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
    expect(page.url()).toContain('/user-management');
    console.log('[USER RBAC] Verified IT Admin blocked from /reports.');

    // 3. IT admin attempts to visit /audit-trail (audit rule allows it_admin)
    console.log('[USER RBAC] IT Admin navigating to /audit-trail...');
    await page.goto(`${FRONTEND}/audit-trail`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);
    expect(page.url()).toContain('/audit-trail');
    await expect(page.locator('h1').filter({ hasText: /Audit Trail/i }).first()).toBeVisible({ timeout: 10000 });
    console.log('[USER RBAC] Verified IT Admin is authorized to inspect compliance Audit Trail.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge02_itadmin_audit_trail_allowed.png') });
    copyArtifact('edge02_itadmin_audit_trail_allowed.png');

    await itContext.close();
  });

  // -------------------------------------------------------------------------
  // TEST 3: Scope 3 Value Chain Form & USEEIO Spend Calculator
  // -------------------------------------------------------------------------
  test('EDGE-3: Scope 3 Value Chain & USEEIO Spend-to-Emissions Calculator', async ({ page }) => {
    console.log('[USER SCOPE3] Navigating to Scope 3 Emissions calculator...');
    await ensureAuthenticatedPage(page, '/emissions?scope=3');
    await page.waitForTimeout(1500);

    // Ensure Scope 3 tab is active
    const s3Tab = page.locator('button:has-text("Scope 3")');
    if (await s3Tab.isVisible().catch(() => false)) {
      await s3Tab.click();
      await page.waitForTimeout(800);
    }

    // Locate EEIO Quick Spend Calculator toggle
    const eeioHeader = page.locator('text=EEIO Quick Spend Calculator');
    await expect(eeioHeader).toBeVisible({ timeout: 10000 });

    // Expand accordion if not already expanded
    const naicsInput = page.locator('input[placeholder*="331110"], input[list="eeio-naics-options"]');
    if (!(await naicsInput.isVisible().catch(() => false))) {
      await eeioHeader.click();
      await page.waitForTimeout(500);
    }
    await expect(naicsInput).toBeVisible({ timeout: 5000 });

    console.log('[USER SCOPE3] Entering NAICS 331110 and spend amount $50,000 USD...');
    await naicsInput.fill('331110');
    
    // Spend amount input in EEIO section
    const spendInput = page.locator('label:has-text("Spend Amount")').locator('..').locator('input[type="number"]');
    await spendInput.fill('50000');

    // Click Calculate & Auto-fill
    const calcBtn = page.locator('button:has-text("Calculate & Auto-fill")');
    await expect(calcBtn).toBeVisible();
    await calcBtn.click();
    await page.waitForTimeout(1500);

    // Verify calculation result box appears with calculated emissions
    const resultBox = page.locator('div:has-text("Estimated Emissions:")').filter({ hasText: 'tCO₂e' }).first();
    await expect(resultBox).toBeVisible({ timeout: 10000 });
    await expect(resultBox).toContainText('39.35');
    console.log('[USER SCOPE3] Verified USEEIO spend conversion: 39.35 tCO2e estimated.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge03_eeio_calculator_result.png') });
    copyArtifact('edge03_eeio_calculator_result.png');

    // Verify the entry form inputs were auto-filled
    const amountField = page.locator('div.input-group:has-text("Amount") input[type="number"]').first();
    await expect(amountField).toHaveValue('50000');

    // Select facility if not set
    const facDropdown = page.locator('div.input-group:has-text("Facility") .custom-dropdown-container').first();
    if (await facDropdown.isVisible().catch(() => false)) {
      await facDropdown.click().catch(() => {});
      await page.waitForTimeout(300);
      const firstOption = page.locator('.dropdown-item').filter({ hasNotText: /Select Facility/i }).first();
      if (await firstOption.isVisible().catch(() => false)) {
        await firstOption.click().catch(() => {});
      }
    }

    // Submit as Draft (Maker Mode)
    const draftBtn = page.locator('button:has-text("Save as Draft (Maker Mode)")');
    if (await draftBtn.isVisible().catch(() => false)) {
      console.log('[USER SCOPE3] Saving entry as Draft in Maker mode...');
      await draftBtn.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge03_scope3_submitted.png') });
      copyArtifact('edge03_scope3_submitted.png');
    }
  });

  // -------------------------------------------------------------------------
  // TEST 4: Production Data & Interactive Unit Converters (Gas & Oil)
  // -------------------------------------------------------------------------
  test('EDGE-4: Production Unit Converters (Gas m³ to mscf & Oil m³ to bbl)', async ({ page }) => {
    console.log('[USER PROD] Navigating to /manage-data and selecting Production tab...');
    await ensureAuthenticatedPage(page, '/manage-data');
    await page.waitForTimeout(1000);

    const prodTab = page.locator('button:has-text("Production"), [data-tab="production"]').first();
    await expect(prodTab).toBeVisible({ timeout: 10000 });
    await prodTab.click();
    await page.waitForTimeout(1000);

    await expect(page.locator('h2:has-text("Annual Production Records")')).toBeVisible({ timeout: 10000 });

    // 1. Test Oil Unit Converter (m³ to bbl)
    console.log('[USER PROD] Testing Oil Unit Converter modal (100 m³ -> bbl)...');
    const convertOilBtn = page.locator('label:has-text("Oil") button:has-text("Convert m³")');
    await expect(convertOilBtn).toBeVisible();
    await convertOilBtn.click();
    await page.waitForTimeout(600);

    // Verify modal is open
    const modalInput = page.locator('input[placeholder="e.g. 1000"]').first();
    await expect(modalInput).toBeVisible({ timeout: 5000 });
    await modalInput.fill('100');

    // Click Convert & Apply
    const applyBtn = page.locator('button:has-text("Convert & Apply")');
    await applyBtn.click();
    await page.waitForTimeout(800);

    // Verify oil amount was populated with 628.98
    const oilInput = page.locator('div.input-group:has-text("Oil") input[type="number"]').first();
    await expect(oilInput).toHaveValue('628.98');
    console.log('[USER PROD] Verified Oil converted to 628.98 bbl.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge04_oil_converter_applied.png') });
    copyArtifact('edge04_oil_converter_applied.png');

    // 2. Test Gas Unit Converter (m³ to mscf)
    console.log('[USER PROD] Testing Gas Unit Converter modal (1000 m³ -> mscf)...');
    const convertGasBtn = page.locator('label:has-text("Gas") button:has-text("Convert m³")');
    await expect(convertGasBtn).toBeVisible();
    await convertGasBtn.click();
    await page.waitForTimeout(600);

    const gasModalInput = page.locator('input[placeholder="e.g. 1000"]').first();
    await expect(gasModalInput).toBeVisible({ timeout: 5000 });
    await gasModalInput.fill('1000');

    await page.locator('button:has-text("Convert & Apply")').click();
    await page.waitForTimeout(800);

    // Verify gas amount was populated with 35.31
    const gasInput = page.locator('div.input-group:has-text("Gas") input[type="number"]').first();
    await expect(gasInput).toHaveValue('35.31');
    console.log('[USER PROD] Verified Gas converted to 35.31 mscf.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge04_gas_converter_applied.png') });
    copyArtifact('edge04_gas_converter_applied.png');

    // 3. Fill required fields and save record
    console.log('[USER PROD] Configuring production record metadata and saving...');
    const activitySelect = page.locator('div.input-group:has-text("Activity") select.component-select').first();
    if (await activitySelect.isVisible().catch(() => false)) {
      await activitySelect.selectOption({ index: 1 });
      await page.waitForTimeout(400);
    }

    const divisionSelect = page.locator('div.input-group:has-text("Division") select.component-select').first();
    if (await divisionSelect.isVisible().catch(() => false)) {
      await divisionSelect.selectOption({ index: 1 });
      await page.waitForTimeout(400);
    }

    // Region dropdown
    const regionDropdown = page.locator('div.input-group:has-text("Region") .custom-dropdown-container').first();
    if (await regionDropdown.isVisible().catch(() => false)) {
      await regionDropdown.click();
      await page.waitForTimeout(300);
      const option = page.locator('.dropdown-item').filter({ hasNotText: /Select Region/i }).first();
      if (await option.isVisible().catch(() => false)) {
        await option.click();
      }
    }

    // Set Year and Month
    const yearInput = page.locator('div.input-group:has-text("Year") input[type="number"]').first();
    await yearInput.fill('2025');

    const monthSelect = page.locator('div.input-group:has-text("Month") select.component-select').first();
    if (await monthSelect.isVisible().catch(() => false)) {
      await monthSelect.selectOption({ index: 5 });
    }

    // Click Save Production Record
    const saveProdBtn = page.locator('button.action-btn:has-text("Save Record")').first();
    await expect(saveProdBtn).toBeVisible({ timeout: 5000 });
    await saveProdBtn.click();
    await page.waitForTimeout(1500);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge04_production_record_saved.png') });
    copyArtifact('edge04_production_record_saved.png');
    console.log('[USER PROD] Production record submission completed.');
  });

  // -------------------------------------------------------------------------
  // TEST 5: EU CBAM Regulation Export Tracking
  // -------------------------------------------------------------------------
  test('EDGE-5: EU CBAM Regulation Export & Specific Embedded Emissions', async ({ page }) => {
    console.log('[USER CBAM] Navigating to /manage-data?tab=cbam and selecting CBAM Products tab...');
    await ensureAuthenticatedPage(page, '/manage-data?tab=cbam');
    await page.waitForTimeout(1000);

    const cbamTab = page.locator('button:has-text("CBAM Products"), button:has-text("CBAM"), [data-tab="cbam"]').first();
    if (await cbamTab.isVisible().catch(() => false)) {
      await cbamTab.click();
      await page.waitForTimeout(800);
    }

    // Verify CBAM Header
    await expect(page.locator('h2:has-text("EU CBAM Export & Embedded Emission Tracking")')).toBeVisible({ timeout: 10000 });

    // Select Activity & Division
    const actSelect = page.locator('div.input-group:has-text("Activity") select.component-select').first();
    await actSelect.selectOption({ index: 1 });
    await page.waitForTimeout(400);

    const divSelect = page.locator('div.input-group:has-text("Division") select.component-select').first();
    if (await divSelect.isVisible().catch(() => false)) {
      await divSelect.selectOption({ index: 1 });
      await page.waitForTimeout(400);
    }

    const facSelect = page.locator('div.input-group:has-text("Facility") select.component-select').first();
    await facSelect.selectOption({ index: 1 });
    await page.waitForTimeout(400);

    // Product Name
    const productNameInput = page.locator('input[placeholder*="Export Blend Crude Oil"]').first();
    await productNameInput.fill('Sahara Blend Export Crude');

    // EU CN Code
    const cnSelect = page.locator('div.input-group:has-text("EU CN Code") select.component-select').first();
    await cnSelect.selectOption('2709 00');

    // Year & Month
    const yearInput = page.locator('div.input-group:has-text("Reporting Year") input[type="number"]').first();
    await yearInput.fill('2025');

    const qtyInput = page.locator('input[placeholder="0.00"]').first();
    await qtyInput.fill('5000');

    // Embedded emissions
    const directInput = page.locator('div.input-group:has-text("Direct Specific Embedded") input').first();
    await directInput.fill('0.045');

    const indirectInput = page.locator('div.input-group:has-text("Indirect Specific Embedded") input').first();
    await indirectInput.fill('0.012');

    // Notes
    const notesInput = page.locator('input[placeholder*="Accredited Verifier"]').first();
    await notesInput.fill('TUV Rhineland Accredited CBAM Verification #DZ-2025-081');

    console.log('[USER CBAM] Saving new EU CBAM export record...');
    const saveCbamBtn = page.locator('button:has-text("Save CBAM Record")');
    await saveCbamBtn.click();
    await page.waitForTimeout(1500);

    // Assert that the record is rendered in the CBAM table
    const tableRecord = page.locator('text=Sahara Blend Export Crude').first();
    await expect(tableRecord).toBeVisible({ timeout: 10000 });
    console.log('[USER CBAM] Successfully verified new EU CBAM export entry in table.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge05_cbam_record_saved.png') });
    copyArtifact('edge05_cbam_record_saved.png');
  });

  // -------------------------------------------------------------------------
  // TEST 6: Interactive Audit Trail Search, Timeline & Raw JSON Modal
  // -------------------------------------------------------------------------
  test('EDGE-6: Audit Trail Search Filter, Timeline View & Raw JSON Inspector', async ({ page }) => {
    console.log('[USER AUDIT] Navigating to /audit-trail...');
    await ensureAuthenticatedPage(page, '/audit-trail');
    await page.waitForTimeout(1500);

    // Header assertion
    await expect(page.locator('h1:has-text("Audit Trail & System Activity")')).toBeVisible({ timeout: 10000 });

    // 1. Filter Search Test
    console.log('[USER AUDIT] Testing live search filter...');
    const searchInput = page.locator('input[aria-label="Search audit log"], input[placeholder*="Search by user"]').first();
    await expect(searchInput).toBeVisible();
    await searchInput.fill('LOGIN');
    await page.waitForTimeout(600); // Allow 350ms debounce

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge06_audit_search_filtered.png') });
    copyArtifact('edge06_audit_search_filtered.png');

    // Reset search
    await searchInput.fill('');
    await page.waitForTimeout(600);

    // 2. Open Raw JSON Details Modal
    console.log('[USER AUDIT] Opening Raw JSON Details modal on first audit row...');
    const detailsBtn = page.locator('button:has-text("Details")').first();
    await expect(detailsBtn).toBeVisible({ timeout: 10000 });
    await detailsBtn.click();
    await page.waitForTimeout(600);

    // Verify Dialog opened with JSON payload
    const dialogTitle = page.locator('text=Audit event').first();
    await expect(dialogTitle).toBeVisible({ timeout: 5000 });
    const preBlock = page.locator('pre').first();
    await expect(preBlock).toBeVisible();
    const jsonContent = await preBlock.textContent();
    expect(jsonContent).toContain('{');
    console.log('[USER AUDIT] Verified raw JSON inspection dialog with full audit payload.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge06_audit_details_modal.png') });
    copyArtifact('edge06_audit_details_modal.png');

    // Close Dialog
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);

    // 3. Switch to Timeline View
    console.log('[USER AUDIT] Switching view mode to Timeline...');
    const timelineOption = page.locator('button:has-text("Timeline"), [role="radio"]:has-text("Timeline")').first();
    await timelineOption.click();
    await page.waitForTimeout(800);

    // Assert timeline container
    const timelineNode = page.locator('ol li, .group.relative.flex').first();
    await expect(timelineNode).toBeVisible({ timeout: 10000 });
    console.log('[USER AUDIT] Verified chronological Timeline view rendered.');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge06_audit_timeline_view.png') });
    copyArtifact('edge06_audit_timeline_view.png');

    // 4. Test Refresh button
    const refreshBtn = page.locator('button:has-text("Refresh")').first();
    await refreshBtn.click();
    await page.waitForTimeout(600);
  });

  // -------------------------------------------------------------------------
  // TEST 7: Cross-Route Global Filter Persistence
  // -------------------------------------------------------------------------
  test('EDGE-7: Cross-Route Global Filter Persistence & Route Synchronization', async ({ page }) => {
    console.log('[USER FILTERS] Navigating to Dashboard / to verify filter synchronization...');
    await ensureAuthenticatedPage(page, '/');
    await page.waitForTimeout(1500);

    // Find Year dropdown in dashboard top bar
    const yearDropdown = page.locator('.dashboard-filters .filter-wrapper button, .dashboard-filters .filter-wrapper [role="combobox"]').first();
    await expect(yearDropdown).toBeVisible({ timeout: 10000 });
    await yearDropdown.click();
    await page.waitForTimeout(400);

    // Choose 2024 (or first year option after 'All Years')
    const yearOption = page.locator('[role="option"], .dropdown-option').filter({ hasText: /202[0-9]/ }).first();
    if (await yearOption.isVisible().catch(() => false)) {
      const yearText = await yearOption.textContent();
      console.log(`[USER FILTERS] Selecting year: ${yearText}`);
      await yearOption.click();
      await page.waitForTimeout(800);

      // Verify URL updated with query parameter
      expect(page.url()).toContain('year=');
      console.log(`[USER FILTERS] Dashboard URL synchronized: ${page.url()}`);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge07_dashboard_filtered.png') });
      copyArtifact('edge07_dashboard_filtered.png');

      // Navigate to Carbon Intensity
      console.log('[USER FILTERS] Navigating to /carbon-intensity...');
      await page.goto(`${FRONTEND}/carbon-intensity`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1500);

      // Verify URL retains year parameter
      expect(page.url()).toContain('year=');
      console.log(`[USER FILTERS] Carbon Intensity retained filter: ${page.url()}`);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge07_carbon_intensity_synced.png') });
      copyArtifact('edge07_carbon_intensity_synced.png');

      // Navigate to Methane Intensity
      console.log('[USER FILTERS] Navigating to /methane-intensity...');
      await page.goto(`${FRONTEND}/methane-intensity`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(1500);

      expect(page.url()).toContain('year=');
      console.log(`[USER FILTERS] Methane Intensity retained filter: ${page.url()}`);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'edge07_methane_intensity_synced.png') });
      copyArtifact('edge07_methane_intensity_synced.png');
    }
  });

});
