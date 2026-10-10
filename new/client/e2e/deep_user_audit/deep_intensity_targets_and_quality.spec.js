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

test.describe.serial('Suite 10: Quantitative Intensity Analytics, Target Modeling & Quality Assurance Operations', () => {

  test.beforeAll(async () => {
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  // -------------------------------------------------------------------------
  // TEST 1: Carbon Intensity 5-Year Performance Track & Heatmap Matrix
  // -------------------------------------------------------------------------
  test('INT-1: Carbon Intensity 5-Year Performance Track & Heatmap Matrix Switcher (/carbon-intensity)', async ({ page }) => {
    console.log('[E2E INT] Navigating to Carbon Intensity (/carbon-intensity)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/carbon-intensity`);
    await page.waitForTimeout(1500);

    // Verify Carbon Intensity KPI cards
    const intensityTitle = page.locator('text=Carbon Intensity & Product Embodiment').first();
    await expect(intensityTitle).toBeVisible({ timeout: 15000 });
    console.log('[E2E INT] Carbon Intensity & Product Embodiment KPI header verified.');

    // Switch between Chart and Heatmap in TrendSection
    console.log('[E2E INT] Switching from Line Chart to Facility Heatmap view...');
    const heatmapBtn = page.locator('button:has-text("Heatmap")').first();
    await expect(heatmapBtn).toBeVisible({ timeout: 10000 });
    await heatmapBtn.click();
    await page.waitForTimeout(800);

    // Verify Heatmap is active
    const heatmapView = page.locator('.heatmap-container, table, [role="grid"]').first();
    await expect(heatmapView).toBeVisible();
    console.log('[E2E INT] Facility x Year Intensity Heatmap matrix successfully rendered.');

    // Verify EU CBAM Product Specific Embedded Emissions section
    const cbamHeader = page.locator('text=EU CBAM Product Specific Embedded Emissions').first();
    await expect(cbamHeader).toBeVisible();
    console.log('[E2E INT] EU CBAM Product Specific Embedded Emissions verified.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'int01_carbon_intensity_heatmap.png') });
    copyArtifact('int01_carbon_intensity_heatmap.png');
    console.log('[E2E INT] Captured int01_carbon_intensity_heatmap.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 2: Methane Intensity OGMP 2.0 Gold Standard Roadmap & Level 4/5 Reconciliation
  // -------------------------------------------------------------------------
  test('INT-2: Methane Intensity OGMP 2.0 Gold Standard Pathway & Level 4/5 Reconciliation (/methane-intensity)', async ({ page }) => {
    console.log('[E2E INT] Navigating to Methane Intensity (/methane-intensity)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/methane-intensity`);
    await page.waitForTimeout(1500);

    // Verify Methane Loss Rate KPI Header
    const methaneLossTitle = page.locator('text=Methane Intensity & Loss Rate Analytics').first();
    await expect(methaneLossTitle).toBeVisible({ timeout: 15000 });
    console.log('[E2E INT] Methane Intensity & Loss Rate Analytics KPI verified.');

    // Locate and Expand OGMP 2.0 Gold Standard Pathway & Milestone Roadmap
    console.log('[E2E INT] Expanding OGMP 2.0 Gold Standard Pathway & Milestone Roadmap...');
    const roadmapCardHeader = page.locator('h3:has-text("OGMP 2.0 Gold Standard Pathway & Milestone Roadmap")').first();
    await expect(roadmapCardHeader).toBeVisible({ timeout: 10000 });
    await roadmapCardHeader.click();
    await page.waitForTimeout(800);

    // Verify roadmap content is visible
    const milestoneProgress = page.locator('text=Level 4/5 site-level measurement reconciliation').first();
    await expect(milestoneProgress).toBeVisible();
    console.log('[E2E INT] OGMP 2.0 Gold Standard multi-year milestone roadmap expanded.');

    // Locate and Expand Level 4/5 Top-Down Survey & Bottom-Up Reconciliation Section
    console.log('[E2E INT] Expanding OGMP 2.0 Level 4/5 Top-Down Survey & Bottom-Up Reconciliation section...');
    const reconCardHeader = page.locator('h3:has-text("OGMP 2.0 Level 4/5 Top-Down Survey & Bottom-Up Reconciliation")').first();
    await expect(reconCardHeader).toBeVisible();
    await reconCardHeader.click();
    await page.waitForTimeout(800);

    // Verify Gold Standard Pathway badge
    const reconBadge = page.locator('text=Gold Standard Pathway: Level 5 Reconciled').first();
    await expect(reconBadge).toBeVisible();
    console.log('[E2E INT] Level 4/5 Top-Down Site Measurement Reconciliation matrix active.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'int02_methane_intensity_ogmp_roadmap.png') });
    copyArtifact('int02_methane_intensity_ogmp_roadmap.png');
    console.log('[E2E INT] Captured int02_methane_intensity_ogmp_roadmap.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 3: Decarbonization Target Modeling & Trajectory Simulator
  // -------------------------------------------------------------------------
  test('INT-3: Decarbonization Target Modeling & Trajectory Simulator (/sbti)', async ({ page }) => {
    console.log('[E2E INT] Navigating to SBTi & Net-Zero (/sbti)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/sbti`);
    await page.waitForTimeout(1500);

    // Verify SBTi Trajectory Dashboard
    const sbtiHeader = page.locator('text=SBTi & Net-Zero Trajectory').first();
    await expect(sbtiHeader).toBeVisible({ timeout: 15000 });
    console.log('[E2E INT] SBTi & Net-Zero Trajectory Dashboard verified.');

    // Open Target Configuration Drawer
    console.log('[E2E INT] Opening SBTi Corporate Target Setup drawer...');
    const configBtn = page.locator('button:has-text("Configure target")').first();
    await expect(configBtn).toBeVisible({ timeout: 10000 });
    await configBtn.click();
    await page.waitForTimeout(800);

    // Select 1.5°C pathway button
    const pathwayBtn = page.locator('button:has-text("1.5°C")').first();
    await expect(pathwayBtn).toBeVisible();
    await pathwayBtn.click();
    await page.waitForTimeout(400);

    // Update target fields
    const baseYearInput = page.locator('input[type="number"][min="2015"]').first();
    await baseYearInput.fill('2024');

    const emissionsInput = page.locator('input[type="number"][step="0.01"]').first();
    await emissionsInput.fill('485000');

    const targetYearInput = page.locator('input[type="number"][min="2030"]').first();
    await targetYearInput.fill('2050');

    const reductionInput = page.locator('input[type="number"][step="0.1"]').first();
    await reductionInput.fill('4.2');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'int03_sbti_target_modeling.png') });
    copyArtifact('int03_sbti_target_modeling.png');
    console.log('[E2E INT] Captured int03_sbti_target_modeling.png.');

    // Save Target
    console.log('[E2E INT] Submitting Save SBTi Target...');
    const saveTargetBtn = page.locator('button[type="submit"]:has-text("Save SBTi Target")').first();
    await saveTargetBtn.click();

    // Verify Success Toast
    const successToast = page.locator('text=SBTi Net-Zero Target saved successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E INT] Confirmed SBTi Target persistence notification.');
  });

  // -------------------------------------------------------------------------
  // TEST 4: QA/QC System Diagnostics Run & Anomaly Resolution Workflow
  // -------------------------------------------------------------------------
  test('INT-4: QA/QC System Diagnostics Run & Anomaly Resolution Workflow (/qa-dashboard)', async ({ page }) => {
    console.log('[E2E INT] Navigating to QA/QC Diagnostics (/qa-dashboard)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/qa-dashboard`);
    await page.waitForTimeout(1500);

    // Verify QA/QC Header and KPIs
    const qaTitle = page.locator('text=QA/QC & System Diagnostics').first();
    await expect(qaTitle).toBeVisible({ timeout: 15000 });
    console.log('[E2E INT] QA/QC & System Diagnostics dashboard loaded.');

    // Trigger Run Diagnostics Scan
    console.log('[E2E INT] Triggering live "Run Diagnostics" scan...');
    const runDiagBtn = page.locator('button:has-text("Run Diagnostics")').first();
    await expect(runDiagBtn).toBeVisible({ timeout: 10000 });
    await runDiagBtn.click();

    // Verify Diagnostics Scan notification
    const diagToast = page.locator('text=Diagnostics and anomaly scans refreshed successfully').first();
    await expect(diagToast).toBeVisible({ timeout: 12000 });
    console.log('[E2E INT] Live inventory diagnostic scan completed with confirmation toast.');

    // Switch to Health & Completeness Diagnostics tab
    console.log('[E2E INT] Switching to "Health & Completeness Diagnostics" tab...');
    const diagTab = page.locator('button:has-text("Health & Completeness Diagnostics")').first();
    await diagTab.click();
    await page.waitForTimeout(800);

    // Verify Diagnostics panel is rendered
    const compHeader = page.locator('text=Completeness').first();
    await expect(compHeader).toBeVisible();
    console.log('[E2E INT] Health & Completeness Diagnostics panel active.');

    // Switch to Uncertainty & Rigor Analysis tab
    console.log('[E2E INT] Switching to "Uncertainty & Rigor Analysis" tab...');
    const uncertTab = page.locator('button:has-text("Uncertainty & Rigor Analysis")').first();
    await uncertTab.click();
    await page.waitForTimeout(800);

    // Switch back to Queue tab
    const queueTab = page.locator('button:has-text("Anomaly Resolution Queue")').first();
    await queueTab.click();
    await page.waitForTimeout(800);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'int04_qa_diagnostics_scan.png') });
    copyArtifact('int04_qa_diagnostics_scan.png');
    console.log('[E2E INT] Captured int04_qa_diagnostics_scan.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 5: Scope 3 Supply Chain EEIO Spend-Based Factor Estimator
  // -------------------------------------------------------------------------
  test('INT-5: Scope 3 Supply Chain EEIO Spend-Based Factor Estimator (/emissions?scope=scope3)', async ({ page }) => {
    console.log('[E2E INT] Navigating to Emissions Scope 3 (/emissions?scope=scope3)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope3`);
    await page.waitForTimeout(1500);

    // Expand EEIO Quick Spend Calculator
    console.log('[E2E INT] Expanding EEIO Quick Spend Calculator drawer...');
    const eeioToggle = page.locator('strong:has-text("EEIO Quick Spend Calculator")').first();
    await expect(eeioToggle).toBeVisible({ timeout: 15000 });
    await eeioToggle.click();
    await page.waitForTimeout(600);

    // Input NAICS and Spend Amount
    console.log('[E2E INT] Populating NAICS code and financial expenditure ($125,000)...');
    const naicsInput = page.locator('input[placeholder="e.g. 331110 or steel"]').first();
    await expect(naicsInput).toBeVisible();
    await naicsInput.fill('211120');

    const spendInput = page.locator('.calc-panel input[type="number"][placeholder="0.00"]').first();
    await expect(spendInput).toBeVisible();
    await spendInput.fill('125000');

    // Trigger Calculation
    console.log('[E2E INT] Clicking "Calculate & Auto-fill"...');
    const calcEeioBtn = page.locator('button:has-text("Calculate & Auto-fill")').first();
    await calcEeioBtn.click();
    await page.waitForTimeout(800);

    // Verify EEIO Result Card
    const resultCard = page.locator('strong:has-text("Estimated Emissions:")').first();
    await expect(resultCard).toBeVisible({ timeout: 10000 });
    console.log('[E2E INT] EEIO factor calculation evaluated and verified.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'int05_scope3_eeio_calculator.png') });
    copyArtifact('int05_scope3_eeio_calculator.png');
    console.log('[E2E INT] Captured int05_scope3_eeio_calculator.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 6: Annual Production & Throughput Accounting Entry
  // -------------------------------------------------------------------------
  test('INT-6: Annual Production & Throughput Accounting Entry (/manage-data?tab=production)', async ({ page }) => {
    console.log('[E2E INT] Navigating to Production Tab (/manage-data?tab=production)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=production`);
    await page.waitForTimeout(1500);

    // Verify Production Tab header
    const prodHeader = page.locator('h2:has-text("Annual Production Records")').first();
    await expect(prodHeader).toBeVisible({ timeout: 15000 });
    console.log('[E2E INT] Annual Production Records form loaded.');

    // Select Activity
    const activitySelect = page.locator('.grid-forms select').nth(0);
    if (await activitySelect.isEnabled().catch(() => false)) {
      await activitySelect.selectOption('EP');
      await page.waitForTimeout(300);
    }

    // Select Division
    const divisionSelect = page.locator('.grid-forms select').nth(1);
    if (await divisionSelect.isEnabled().catch(() => false)) {
      await divisionSelect.selectOption('Production');
      await page.waitForTimeout(300);
    }

    // Select Facility/Region via CustomDropdown
    const regionDropdown = page.locator('.input-group:has-text("Region") button.dropdown-selected, .input-group:has-text("Region") button').first();
    if (await regionDropdown.isVisible().catch(() => false)) {
      await regionDropdown.click();
      await page.waitForTimeout(300);
      const firstOption = page.locator('.dropdown-option:not(:has-text("Select Region")), [role="option"]:not(:has-text("Select Region"))').first();
      if (await firstOption.isVisible().catch(() => false)) {
        await firstOption.click();
        await page.waitForTimeout(300);
      }
    }

    // Fill Year & Month
    const yearInput = page.locator('.input-group:has-text("Year") input[type="number"]').first();
    await yearInput.fill('2025');

    // Fill Oil Amount
    const oilInput = page.locator('input.mole-input[placeholder="0.0"]').first();
    await oilInput.fill('45000');

    // Fill Gas Amount
    const gasInput = page.locator('input.mole-input[placeholder="0.0"]').nth(1);
    if (await gasInput.isVisible().catch(() => false)) {
      await gasInput.fill('12500000');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'int06_production_data_registered.png') });
    copyArtifact('int06_production_data_registered.png');
    console.log('[E2E INT] Captured int06_production_data_registered.png.');

    // Submit Production Form
    console.log('[E2E INT] Submitting Save Record...');
    const saveProdBtn = page.locator('button.action-btn:has-text("Save Record")').first();
    await saveProdBtn.click();

    // Verify Save Notification
    const saveToast = page.locator('text=Production record saved!').first();
    await expect(saveToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E INT] Confirmed "Production record saved!" notification toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 7: Enterprise Report Configuration & ISO 14064-1 Compliance Builder
  // -------------------------------------------------------------------------
  test('INT-7: Enterprise Report Configuration & ISO 14064-1 Compliance Builder (/reports)', async ({ page }) => {
    console.log('[E2E INT] Navigating to Reports (/reports)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/reports`);
    await page.waitForTimeout(1500);

    // Select at least one region if not selected
    const multiSelectTrigger = page.locator('.dropdown-selected[aria-label="Select Regions..."], .custom-dropdown .dropdown-selected').first();
    if (await multiSelectTrigger.isVisible().catch(() => false)) {
      await multiSelectTrigger.click();
      await page.waitForTimeout(400);
      const selectAllBtn = page.locator('.dropdown-portal .dropdown-option:has-text("Select All")').first();
      if (await selectAllBtn.isVisible().catch(() => false)) {
        await selectAllBtn.click();
        await page.waitForTimeout(300);
      }
      // Click trigger or press Escape to close dropdown
      await page.keyboard.press('Escape');
      await page.waitForTimeout(300);
    }

    // Open "Create Report" Dialog
    console.log('[E2E INT] Opening Create Report dialog via "Create Report" button...');
    const createReportBtn = page.locator('button:has-text("Create Report")').first();
    await expect(createReportBtn).toBeVisible({ timeout: 10000 });
    await createReportBtn.click();
    await page.waitForTimeout(800);

    // Verify Dialog opened
    const dialogTitle = page.locator('text=Generate Executive GHG Report').first();
    await expect(dialogTitle).toBeVisible();
    console.log('[E2E INT] Generate Executive GHG Report configuration dialog opened.');

    // Switch format to ISO 14064-1
    console.log('[E2E INT] Selecting "ISO 14064-1 Report" format...');
    const isoOption = page.locator('button:has-text("ISO 14064-1 Report")').first();
    await expect(isoOption).toBeVisible();
    await isoOption.click();
    await page.waitForTimeout(500);

    // Verify ISO specific fields
    const exclusionTextarea = page.locator('textarea').first();
    await expect(exclusionTextarea).toBeVisible();
    await exclusionTextarea.fill('Minor fugitive leaks < 0.5% screened out per ISO 14064-1:2018 §5.2 criteria.');

    const verificationInput = page.locator('input[value="Not externally verified"], input:near(label:has-text("Verification Status"))').first();
    if (await verificationInput.isVisible().catch(() => false)) {
      await verificationInput.fill('Reasonable Assurance by Bureau Veritas 2026');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'int07_report_iso_config_builder.png') });
    copyArtifact('int07_report_iso_config_builder.png');
    console.log('[E2E INT] Captured int07_report_iso_config_builder.png.');

    // Close Dialog with Cancel button
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    await cancelBtn.click();
    await page.waitForTimeout(500);
    console.log('[E2E INT] Report configuration modal closed.');

    // Test Group By dropdown in Filter & Group Data
    console.log('[E2E INT] Testing Group By filter (By Category/Process)...');
    const groupBySelect = page.locator('select:has(option[value="process"])').first();
    if (await groupBySelect.isVisible().catch(() => false)) {
      await groupBySelect.selectOption('process');
      await page.waitForTimeout(600);
      console.log('[E2E INT] Group By "By Category/Process" activated and table re-rendered.');
    }
  });

});
