import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';

// Helper to ensure authenticated state and clear overlays
async function ensureAuthenticatedPage(page, targetUrl = '/') {
  const errors = [];
  page.on('pageerror', (err) => errors.push(err.message));

  await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(1000);

  // 1. Skip intro video if present
  const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
  if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipBtn.click();
    await page.waitForTimeout(500);
  }
  await page.locator('.login-intro-overlay').waitFor({ state: 'detached', timeout: 3000 }).catch(() => {});

  // 2. Fallback login if session cookie expired
  const emailInput = page.locator('input[placeholder="Email Address"]');
  if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('[DEEP TEST] Performing fallback login...');
    await emailInput.fill('a');
    await page.locator('input[type="password"]').fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1500);
    if (targetUrl && targetUrl !== '/') {
      await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(1000);
    }
  }

  // 3. Ensure page shell is ready
  await expect(page.locator('.app-container, .main-content, #main').first()).toBeVisible({ timeout: 20000 });
  await page.waitForLoadState('networkidle').catch(() => {});
  return errors;
}

test.describe.serial('Deep User Journey & End-to-End Exploration', () => {

  // -------------------------------------------------------------------------
  // 1. AUTHENTICATION & LOGIN FLOWS
  // -------------------------------------------------------------------------
  test('1. Authentication Flow: Login Page, Credentials & Profile Header', async ({ browser }) => {
    // Test in an unauthenticated context
    const context = await browser.newContext({ storageState: undefined });
    const page = await context.newPage();

    console.log('[DEEP TEST] Testing unauthenticated access to /login...');
    await page.goto(`${FRONTEND}/login`, { waitUntil: 'networkidle' });
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_login_page_initial.png') });

    // Verify elements
    await expect(page.locator('input[placeholder="Email Address"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]:has-text("Sign In")')).toBeVisible();

    // Verify Password Toggle
    const togglePassBtn = page.locator('button:has(svg.lucide-eye), button:has(svg.lucide-eye-off), button[aria-label*="password" i]');
    if (await togglePassBtn.isVisible().catch(() => false)) {
      await page.locator('input[type="password"]').fill('secret123');
      await togglePassBtn.click();
      await page.waitForTimeout(300);
      await expect(page.locator('input[type="text"][placeholder*="password" i], input[type="text"]').last()).toBeVisible();
    }

    // Verify Invalid Login handling
    console.log('[DEEP TEST] Testing invalid credentials response...');
    await page.locator('input[placeholder="Email Address"]').fill('nonexistent@user.com');
    await page.locator('input[type="password"], input[type="text"]').last().fill('wrong_pwd');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForTimeout(1000);
    const hasError = await page.locator('[class*="error"], .banner, [role="alert"]').first().isVisible().catch(() => false);
    expect(hasError).toBeTruthy();
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_login_invalid_error.png') });

    // Verify Forgot Password modal
    const forgotBtn = page.locator('button:has-text("Forgot password"), a:has-text("Forgot password")');
    if (await forgotBtn.isVisible().catch(() => false)) {
      await forgotBtn.click();
      await page.waitForTimeout(500);
      await expect(page.locator('input[placeholder*="email" i], input[type="email"]').last()).toBeVisible();
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_forgot_password_modal.png') });
      const cancelModalBtn = page.locator('button:has-text("Cancel"), button:has-text("Close"), [aria-label="Close"]').last();
      if (await cancelModalBtn.isVisible().catch(() => false)) {
        await cancelModalBtn.click();
      }
    }

    // Valid Login
    console.log('[DEEP TEST] Submitting valid admin credentials...');
    await page.locator('input[placeholder="Email Address"]').fill('a');
    await page.locator('input[type="password"], input[type="text"]').last().fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000);

    // Verify redirect to dashboard
    expect(page.url()).not.toContain('/login');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_logged_in_dashboard.png') });
    console.log('[DEEP TEST] Authenticated successfully, on:', page.url());

    await context.close();
  });

  // -------------------------------------------------------------------------
  // 2. DASHBOARD EXPERIENCE & INTERACTIVE CONTROLS
  // -------------------------------------------------------------------------
  test('2. Dashboard: KPIs, Filters, Year Switching & GWP Horizon Toggles', async ({ page }) => {
    console.log('[DEEP TEST] Inspecting Dashboard metrics & filters...');
    await ensureAuthenticatedPage(page, '/');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_dashboard_overview.png'), fullPage: true });

    // Verify KPI cards
    const heroCard = page.locator('.hero-card, [data-testid="kpi-gross"], .dashboard-grid').first();
    await expect(heroCard).toBeVisible();

    // Verify GWP-100 and GWP-20 switches
    const gwp20Btn = page.locator('button:has-text("GWP-20")');
    const gwp100Btn = page.locator('button:has-text("GWP-100")');
    if (await gwp20Btn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Toggling GWP Horizon to GWP-20...');
      await gwp20Btn.click();
      await page.waitForTimeout(1200);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_dashboard_gwp20.png') });

      console.log('[DEEP TEST] Reverting GWP Horizon to GWP-100...');
      await gwp100Btn.click();
      await page.waitForTimeout(1200);
    }

    // Year Dropdown / Filter
    const yearTrigger = page.locator('button[role="combobox"], .dropdown-trigger').filter({ hasText: /202\d|All Years/i }).first();
    if (await yearTrigger.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Testing Year Filter...');
      await yearTrigger.click();
      await page.waitForTimeout(400);
      const year2025 = page.locator('[role="option"]:has-text("2025"), .dropdown-option:has-text("2025")').first();
      if (await year2025.isVisible().catch(() => false)) {
        await year2025.click();
        await page.waitForTimeout(1200);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_dashboard_year_2025.png') });
      }
    }

    // Organizational Hierarchy Breakdown Accordion
    const accordionBtn = page.locator('button:has-text("Breakdown"), .act-row, [role="button"]:has-text("Upstream")').first();
    if (await accordionBtn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Expanding Breakdown accordion...');
      await accordionBtn.click();
      await page.waitForTimeout(500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_dashboard_breakdown_expanded.png') });
    }

    // TopBar Notification Drawer
    const bellBtn = page.locator('button:has(svg.lucide-bell), button[aria-label*="notification" i]').first();
    if (await bellBtn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Opening notifications panel...');
      await bellBtn.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_notifications_drawer.png') });
      // Close panel
      await page.keyboard.press('Escape');
      await page.waitForTimeout(400);
    }

    // Command Palette (Ctrl+K)
    console.log('[DEEP TEST] Testing Command Palette shortcut...');
    await page.keyboard.press('Control+KeyK');
    await page.waitForTimeout(600);
    const commandDialog = page.locator('[role="dialog"], cmdk-root, .command-palette').first();
    if (await commandDialog.isVisible().catch(() => false)) {
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_command_palette.png') });
      await page.keyboard.press('Escape');
      await page.waitForTimeout(400);
    }
  });

  // -------------------------------------------------------------------------
  // 3. EMISSIONS CALCULATIONS (SCOPE 1, 2, 3)
  // -------------------------------------------------------------------------
  test('3. Calculations Hub: Scope 1, Scope 2, Scope 3 Execution', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to Calculations Hub (/emissions)...');
    await ensureAuthenticatedPage(page, '/emissions');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_emissions_landing.png') });

    // Step 3.1: Scope 1 Stationary Combustion
    console.log('[DEEP TEST] Testing Scope 1 Stationary Combustion form...');
    const s1Card = page.locator('text=Scope 1').first();
    if (await s1Card.isVisible().catch(() => false)) {
      await s1Card.click();
      await page.waitForTimeout(1000);
    }

    // Verify Scope 1 form rendered
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_scope1_form_initial.png') });

    // Fill Stationary Combustion Form
    const combustionTab = page.locator('button:has-text("Stationary Combustion"), button:has-text("Combustion")').first();
    if (await combustionTab.isVisible().catch(() => false)) {
      await combustionTab.click();
      await page.waitForTimeout(500);
    }

    // Fill consumption amount
    const amountInput = page.locator('input[type="number"], input[name*="amount" i], input[placeholder*="amount" i]').first();
    if (await amountInput.isVisible().catch(() => false)) {
      await amountInput.fill('15000');
      await page.waitForTimeout(300);
    }

    // Click Calculate button
    const calcBtn = page.locator('button:has-text("Calculate"), button:has-text("Compute")').first();
    if (await calcBtn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Clicking Calculate button in Scope 1...');
      await calcBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_scope1_calculated_result.png') });
    }

    // Step 3.2: Scope 2 Electricity Form
    console.log('[DEEP TEST] Navigating to Scope 2 Form...');
    await page.goto(`${FRONTEND}/emissions?scope=2`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_scope2_form.png') });

    const s2Amount = page.locator('input[type="number"], input[name*="amount" i]').first();
    if (await s2Amount.isVisible().catch(() => false)) {
      await s2Amount.fill('45000');
    }
    const s2CalcBtn = page.locator('button:has-text("Calculate"), button:has-text("Compute")').first();
    if (await s2CalcBtn.isVisible().catch(() => false)) {
      await s2CalcBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_scope2_calculated.png') });
    }

    // Step 3.3: Scope 3 Value Chain Form
    console.log('[DEEP TEST] Navigating to Scope 3 Form...');
    await page.goto(`${FRONTEND}/emissions?scope=3`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_scope3_form.png') });
  });

  // -------------------------------------------------------------------------
  // 4. DATA MANAGEMENT & BULK UPLOADER
  // -------------------------------------------------------------------------
  test('4. Manage Data: Table Inspection, Filters, Search & Bulk Wizard Modal', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to Manage Data (/manage-data)...');
    await ensureAuthenticatedPage(page, '/manage-data');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_manage_data_table.png'), fullPage: true });

    // Verify table records exist
    const rows = page.locator('table tbody tr');
    const rowCount = await rows.count();
    console.log(`[DEEP TEST] Found ${rowCount} emission records in table.`);
    expect(rowCount).toBeGreaterThanOrEqual(1);

    // Search filter
    const searchInput = page.locator('input[placeholder*="Search" i]').first();
    if (await searchInput.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Testing table search filter...');
      await searchInput.fill('Combustion');
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_manage_data_search.png') });
      await searchInput.fill('');
      await page.waitForTimeout(400);
    }

    // Bulk Import Modal
    const importBtn = page.locator('button:has-text("Bulk Import"), button:has-text("Import CSV"), button:has-text("Upload")').first();
    if (await importBtn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Opening Bulk Import wizard...');
      await importBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_bulk_import_wizard_modal.png') });

      // Close modal
      const closeBtn = page.locator('button:has-text("Cancel"), button:has-text("Close"), [aria-label="Close"]').last();
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
        await page.waitForTimeout(400);
      }
    }

    // Export Button
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download CSV")').first();
    if (await exportBtn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Verifying Export action is present...');
      await expect(exportBtn).toBeEnabled();
    }
  });

  // -------------------------------------------------------------------------
  // 5. CARBON & METHANE INTENSITY ANALYTICS
  // -------------------------------------------------------------------------
  test('5. Intensity Analytics: Carbon Intensity & Methane OGMP 2.0', async ({ page }) => {
    // 5.1 Carbon Intensity
    console.log('[DEEP TEST] Navigating to Carbon Intensity (/carbon-intensity)...');
    await ensureAuthenticatedPage(page, '/carbon-intensity');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_carbon_intensity_overview.png'), fullPage: true });

    // Check KPI cards (Total BOE, Corporate Intensity kg CO2e/boe)
    const kpiCards = page.locator('.kpi-card, .metric-card, [class*="intensity"]');
    await expect(kpiCards.first()).toBeVisible({ timeout: 10000 });

    // 5.2 Methane Intensity & OGMP 2.0
    console.log('[DEEP TEST] Navigating to Methane Intensity (/methane-intensity)...');
    await ensureAuthenticatedPage(page, '/methane-intensity');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_methane_intensity_ogmp.png'), fullPage: true });

    // OGMP 2.0 Gold Standard levels
    const ogmpLevelCard = page.locator('text=OGMP, text=Gold Standard, text=Level 4, text=Level 5').first();
    if (await ogmpLevelCard.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] OGMP 2.0 framework section verified.');
    }
  });

  // -------------------------------------------------------------------------
  // 6. SBTI & NET-ZERO TARGETS
  // -------------------------------------------------------------------------
  test('6. SBTi & Net-Zero: 1.5°C Reduction Pathways & Ambition Gap', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to SBTi Dashboard (/sbti)...');
    await ensureAuthenticatedPage(page, '/sbti');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_sbti_dashboard.png'), fullPage: true });

    // Verify SBTi title
    await expect(page.locator('text=SBTi & Net-Zero Trajectory').first()).toBeVisible({ timeout: 10000 });

    // Open target configuration drawer if present
    const configBtn = page.locator('button:has-text("Configure target"), button:has-text("target settings")').first();
    if (await configBtn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Toggling SBTi configuration drawer...');
      await configBtn.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_sbti_config_drawer.png') });
    }
  });

  // -------------------------------------------------------------------------
  // 7. GEOSPATIAL EMISSIONS MAP (METHANE EXPLORER)
  // -------------------------------------------------------------------------
  test('7. Emissions Map: Interactive Leaflet Geospatial View', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to Methane Explorer (/methane-explorer)...');
    await ensureAuthenticatedPage(page, '/methane-explorer');
    await page.waitForTimeout(2000); // Wait for Leaflet map tiles to render

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_methane_map.png'), fullPage: true });

    // Check leaflet map container
    const leafletMap = page.locator('.leaflet-container, #map, [class*="map"]').first();
    await expect(leafletMap).toBeVisible({ timeout: 15000 });

    // Click marker if available
    const marker = page.locator('.leaflet-marker-icon').first();
    if (await marker.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Clicking map marker...');
      await marker.click({ force: true }).catch(() => {});
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_map_marker_popup.png') });
    }
  });

  // -------------------------------------------------------------------------
  // 8. REFERENCE DATA & FACTOR CATALOG
  // -------------------------------------------------------------------------
  test('8. Reference Data: API Compendium, IPCC GWPs & Fuel Catalogs', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to Reference Data (/reference-data)...');
    await ensureAuthenticatedPage(page, '/reference-data');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_reference_data_catalog.png'), fullPage: true });

    // Check factors tabs or content cards
    const content = page.locator('table, [role="tablist"], .card, [class*="factor"]').first();
    await expect(content).toBeVisible({ timeout: 10000 });
  });

  // -------------------------------------------------------------------------
  // 9. ASSURANCE & REPORTS GENERATOR
  // -------------------------------------------------------------------------
  test('9. Reports Generator: Framework Selection, Preview & PDF Export', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to Reports (/reports)...');
    await ensureAuthenticatedPage(page, '/reports');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09_reports_generator_wizard.png'), fullPage: true });

    // Check PageHeader title
    await expect(page.locator('text=Reports').first()).toBeVisible({ timeout: 10000 });

    // Check Export dropdown menu button
    const exportBtn = page.locator('button:has-text("Export")').first();
    if (await exportBtn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Opening Export menu...');
      await exportBtn.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '09_reports_export_menu.png') });
      await page.keyboard.press('Escape');
    }
  });

  // -------------------------------------------------------------------------
  // 10. UNCERTAINTY ASSESSMENT (MONTE CARLO & ANALYTICAL)
  // -------------------------------------------------------------------------
  test('10. Uncertainty: Analytical Error Propagation & Monte Carlo Simulation', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to Uncertainty (/uncertainty)...');
    await ensureAuthenticatedPage(page, '/uncertainty');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '10_uncertainty_assessment.png'), fullPage: true });

    // Verify Page title
    await expect(page.locator('.ua-title').first()).toBeVisible({ timeout: 10000 });

    // Check Export button if present
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download")').first();
    if (await exportBtn.isVisible().catch(() => false)) {
      await expect(exportBtn).toBeEnabled();
    }
  });

  // -------------------------------------------------------------------------
  // 11. QA/QC DIAGNOSTICS & DATA HEALTH
  // -------------------------------------------------------------------------
  test('11. QA/QC Dashboard: Diagnostics, Completeness & Anomaly Checks', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to QA Dashboard (/qa-dashboard)...');
    await ensureAuthenticatedPage(page, '/qa-dashboard');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_qa_qc_dashboard.png'), fullPage: true });

    // Check QA title
    await expect(page.locator('.qa-title').first()).toBeVisible({ timeout: 10000 });

    // Check Diagnostics run button
    const runDiagBtn = page.locator('button:has-text("Run Diagnostics"), button:has-text("Diagnostics")').first();
    if (await runDiagBtn.isVisible().catch(() => false)) {
      console.log('[DEEP TEST] Triggering QA Diagnostics check...');
      await runDiagBtn.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '11_qa_qc_diagnostics_refreshed.png') });
    }
  });

  // -------------------------------------------------------------------------
  // 12. AUDIT TRAIL
  // -------------------------------------------------------------------------
  test('12. Audit Trail: Immutable Logs, Action Filters & Payload Inspector', async ({ page }) => {
    console.log('[DEEP TEST] Navigating to Audit Trail (/audit-trail)...');
    await ensureAuthenticatedPage(page, '/audit-trail');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '12_audit_trail_table.png'), fullPage: true });

    // Table rows
    const logRows = page.locator('table tbody tr');
    const count = await logRows.count();
    console.log(`[DEEP TEST] Found ${count} audit trail log records.`);
    expect(count).toBeGreaterThanOrEqual(1);

    // Expand first log entry for details if expand toggle exists
    const expandBtn = logRows.first().locator('button, [role="button"]').first();
    if (await expandBtn.isVisible().catch(() => false)) {
      await expandBtn.click();
      await page.waitForTimeout(400);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '12_audit_trail_expanded_entry.png') });
    }
  });

  // -------------------------------------------------------------------------
  // 13. SETTINGS & USER MANAGEMENT
  // -------------------------------------------------------------------------
  test('13. Settings & Administration: Org Profile, Facilities & User Roster', async ({ page }) => {
    // 13.1 Settings
    console.log('[DEEP TEST] Navigating to Settings (/settings)...');
    await ensureAuthenticatedPage(page, '/settings');
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_settings_profile.png'), fullPage: true });

    // Click facilities tab if present
    const facilitiesTab = page.locator('button:has-text("Facilities"), [role="tab"]:has-text("Facilities")').first();
    if (await facilitiesTab.isVisible().catch(() => false)) {
      await facilitiesTab.click();
      await page.waitForTimeout(600);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_settings_facilities.png') });
    }

    // 13.2 User Management (for IT / Admin)
    console.log('[DEEP TEST] Navigating to User Management (/user-management)...');
    await page.goto(`${FRONTEND}/user-management`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '13_user_management.png') });
  });

});
