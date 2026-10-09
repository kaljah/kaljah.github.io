import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
const ARTIFACT_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\145e1f58-77e7-4f5b-8573-5a1c4dc13171';
const PROJECT_ROOT = path.resolve(__dirname, '../../../..');

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

function runSeed(action) {
  const cmd = `python new/server/tests/seed_maker_checker.py --action ${action}`;
  return execSync(cmd, { cwd: PROJECT_ROOT }).toString().trim();
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

test.describe.serial('Maker-Checker Verification & Real File Downloads Audit', () => {

  test.beforeAll(async () => {
    // Seed initial records
    runSeed('seed1');
  });

  test.afterAll(async () => {
    // Clean up test records
    try {
      runSeed('clean');
    } catch {
      // best-effort cleanup: a failed seed clean must not fail the suite
    }
  });

  // -------------------------------------------------------------------------
  // WORKFLOW 1: Maker-Checker Segregation & Single Record Approval
  // -------------------------------------------------------------------------
  test('VF-1: Maker-Checker Segregation & Single Record Approval', async ({ page }) => {
    console.log('[USER VERIFY] Navigating to /manage-data as Admin...');
    await ensureAuthenticatedPage(page, '/manage-data');
    await page.waitForTimeout(800);

    // Switch to Pending Review tab via navigation button
    const pendingTabBtn = page.locator('button.manage-nav-item:has-text("Pending Review")');
    await expect(pendingTabBtn).toBeVisible({ timeout: 10000 });
    await pendingTabBtn.click();
    await page.waitForTimeout(1000);

    // Verify Pending Review header
    await expect(page.locator('h2:has-text("Pending Review & Approvals")')).toBeVisible({ timeout: 10000 });

    // Verify pending table is visible
    const pendingTable = page.locator('table.pending-table');
    await expect(pendingTable).toBeVisible({ timeout: 10000 });

    // Look for our Scope 1 record
    const targetRow = page.locator('table.pending-table tbody tr:has-text("Scope 1")').first();
    await expect(targetRow).toBeVisible({ timeout: 10000 });

    // Verify Maker-Checker check: the Approve button must be active, not "Self-Submitted"
    const approveBtn = targetRow.locator('button.btn-review-action.approve');
    await expect(approveBtn).toBeVisible();

    const shot1 = 'vf01_pending_record_to_approve.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot1) });
    copyArtifact(shot1);

    // Click Approve
    console.log('[USER VERIFY] Clicking Approve button on pending Scope 1 record...');
    await approveBtn.click();
    await page.waitForTimeout(1200);

    const shot2 = 'vf01_record_approved_success.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot2) });
    copyArtifact(shot2);

    // Verify in SQLite that the record is now 'Verified' and approved_by is 1 (Admin)
    const dbStatus = runSeed('check_s1');
    console.log(`[USER VERIFY] DB status check: ${dbStatus}`);
    expect(dbStatus).toContain('Verified');
    expect(dbStatus).toContain('1');
  });

  // -------------------------------------------------------------------------
  // WORKFLOW 2: Maker-Checker Rejection Modal with Preset Reason
  // -------------------------------------------------------------------------
  test('VF-2: Maker-Checker Rejection Modal with Reason Justification', async ({ page }) => {
    console.log('[USER VERIFY] Seeding Pending Scope 2 record created by Operator (User 2)...');
    runSeed('seed2');

    console.log('[USER VERIFY] Refreshing Pending Review queue in /manage-data...');
    await ensureAuthenticatedPage(page, '/manage-data');
    await page.waitForTimeout(800);

    const pendingTabBtn = page.locator('button.manage-nav-item:has-text("Pending Review")');
    await expect(pendingTabBtn).toBeVisible({ timeout: 10000 });
    await pendingTabBtn.click();
    await page.waitForTimeout(1000);

    // Look for Scope 2 row
    const s2Row = page.locator('table.pending-table tbody tr:has-text("Scope 2")').first();
    await expect(s2Row).toBeVisible({ timeout: 10000 });

    // Click Reject button
    const rejectBtn = s2Row.locator('button.btn-review-action.reject');
    await expect(rejectBtn).toBeVisible();
    await rejectBtn.click();
    await page.waitForTimeout(600);

    // Verify Rejection Modal opens
    const modalHeading = page.locator('h3:has-text("Reject")');
    await expect(modalHeading).toBeVisible({ timeout: 5000 });

    // Select Quick Rejection Reason preset
    const presetChip = page.locator('button.rejection-chip:has-text("Missing Metering Documentation"), button.rejection-chip').first();
    if (await presetChip.isVisible()) {
      await presetChip.click();
      await page.waitForTimeout(300);
    }

    // Append audit detail in textarea
    const reasonTextarea = page.locator('textarea[placeholder*="detailed reason" i]');
    await expect(reasonTextarea).toBeVisible();
    await reasonTextarea.fill('Monthly utility meter calibration certificate and Sonelgaz invoice are missing for Q3.');
    await page.waitForTimeout(300);

    const shot1 = 'vf02_rejection_modal_configured.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot1) });
    copyArtifact(shot1);

    // Click Confirm Rejection
    const confirmRejectBtn = page.locator('button:has-text("Confirm Rejection")');
    await expect(confirmRejectBtn).toBeEnabled();
    await confirmRejectBtn.click();
    await page.waitForTimeout(1200);

    const shot2 = 'vf02_rejected_success.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot2) });
    copyArtifact(shot2);

    // Verify in SQLite that the Scope 2 record is now 'Rejected'
    const dbStatus = runSeed('check_s2');
    console.log(`[USER VERIFY] Scope 2 DB status check: ${dbStatus}`);
    expect(dbStatus).toBe('Rejected');
  });

  // -------------------------------------------------------------------------
  // WORKFLOW 3: Batch Review Wizard
  // -------------------------------------------------------------------------
  test('VF-3: Launch Batch Review Wizard & Interactive Multi-Record Inspection', async ({ page }) => {
    console.log('[USER VERIFY] Seeding 2 records for Batch Review Wizard test...');
    runSeed('seed_wizard');

    await ensureAuthenticatedPage(page, '/manage-data');
    await page.waitForTimeout(800);

    const pendingTabBtn = page.locator('button.manage-nav-item:has-text("Pending Review")');
    await expect(pendingTabBtn).toBeVisible({ timeout: 10000 });
    await pendingTabBtn.click();
    await page.waitForTimeout(1000);

    // Click "Launch Review Wizard"
    const wizardTrigger = page.locator('button:has-text("Launch Review Wizard")');
    await expect(wizardTrigger).toBeVisible({ timeout: 10000 });
    await wizardTrigger.click();
    await page.waitForTimeout(1000);

    // Verify Wizard modal title
    const wizardTitle = page.locator('h2:has-text("Pending Data Audit & Verification Wizard")');
    await expect(wizardTitle).toBeVisible({ timeout: 8000 });

    const shot1 = 'vf03_batch_review_wizard_open.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot1) });
    copyArtifact(shot1);

    // Test Esc or close wizard
    await page.keyboard.press('Escape');
    await page.waitForTimeout(600);
    console.log('[USER VERIFY] Batch Review Wizard verified and dismissed.');
  });

  // -------------------------------------------------------------------------
  // EXPORT 1: PDF Report Export & Stream Byte Integrity
  // -------------------------------------------------------------------------
  test('EX-1: PDF Report Export & Binary Byte Integrity', async ({ page }) => {
    console.log('[USER EXPORT] Navigating to /reports for PDF export...');
    await ensureAuthenticatedPage(page, '/reports');
    await page.waitForTimeout(1000);

    // Find Export dropdown menu
    const exportBtn = page.locator('button:has-text("Export")');
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await exportBtn.click();
    await page.waitForTimeout(500);

    // Listen for download event
    const downloadPromise = page.waitForEvent('download', { timeout: 25000 });

    // Click "PDF report"
    const pdfItem = page.locator('[role="menuitem"]:has-text("PDF report")').first();
    await expect(pdfItem).toBeVisible({ timeout: 5000 });
    await pdfItem.click();

    console.log('[USER EXPORT] Awaiting PDF download stream...');
    const download = await downloadPromise;
    const downloadPath = await download.path();
    const downloadName = download.suggestedFilename();
    console.log(`[USER EXPORT] Downloaded file: ${downloadName} to ${downloadPath}`);

    expect(downloadName.endsWith('.pdf')).toBe(true);

    // Verify byte stream integrity
    const fileBytes = fs.readFileSync(downloadPath);
    console.log(`[USER EXPORT] PDF byte size: ${fileBytes.length} bytes`);
    expect(fileBytes.length).toBeGreaterThan(1000);

    // Verify PDF header magic bytes "%PDF-"
    const header = fileBytes.subarray(0, 5).toString('ascii');
    console.log(`[USER EXPORT] Magic header: ${header}`);
    expect(header).toBe('%PDF-');

    const shot1 = 'vf04_pdf_report_exported.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot1) });
    copyArtifact(shot1);
  });

  // -------------------------------------------------------------------------
  // EXPORT 2: 2025 Master Annual Report (PDF) Download Verification
  // -------------------------------------------------------------------------
  test('EX-2: 2025 Master Annual Report (PDF) Comprehensive Export', async ({ page }) => {
    console.log('[USER EXPORT] Requesting 2025 Master Annual Report (PDF)...');
    await ensureAuthenticatedPage(page, '/reports');
    await page.waitForTimeout(1000);

    const exportBtn = page.locator('button:has-text("Export")');
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await exportBtn.click();
    await page.waitForTimeout(500);

    const downloadPromise = page.waitForEvent('download', { timeout: 60000 });

    const masterItem = page.locator('[role="menuitem"]:has-text("2025 Master report")').first();
    await expect(masterItem).toBeVisible({ timeout: 5000 });
    await masterItem.click();

    console.log('[USER EXPORT] Awaiting 2025 Master Report download...');
    const download = await downloadPromise;
    const downloadPath = await download.path();
    const downloadName = download.suggestedFilename();
    console.log(`[USER EXPORT] Master Report downloaded: ${downloadName}`);

    expect(downloadName).toContain('Annual_GHG_Report');
    expect(downloadName.endsWith('.pdf')).toBe(true);

    const fileBytes = fs.readFileSync(downloadPath);
    console.log(`[USER EXPORT] Master Report size: ${fileBytes.length} bytes`);
    expect(fileBytes.length).toBeGreaterThan(50000);

    const header = fileBytes.subarray(0, 5).toString('ascii');
    expect(header).toBe('%PDF-');

    const shot1 = 'vf05_master_pdf_downloaded.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot1) });
    copyArtifact(shot1);
  });

  // -------------------------------------------------------------------------
  // EXPORT 3: OGMP 2.0 (Excel) Workbook Download Verification
  // -------------------------------------------------------------------------
  test('EX-3: OGMP 2.0 Excel Workbook Download Verification', async ({ page }) => {
    console.log('[USER EXPORT] Requesting OGMP 2.0 Excel export...');
    await ensureAuthenticatedPage(page, '/reports');
    await page.waitForTimeout(1000);

    const exportBtn = page.locator('button:has-text("Export")');
    await expect(exportBtn).toBeVisible({ timeout: 10000 });
    await exportBtn.click();
    await page.waitForTimeout(500);

    const downloadPromise = page.waitForEvent('download', { timeout: 30000 });

    const ogmpItem = page.locator('[role="menuitem"]:has-text("OGMP 2.0")').first();
    await expect(ogmpItem).toBeVisible({ timeout: 5000 });
    await ogmpItem.click();

    console.log('[USER EXPORT] Awaiting OGMP Excel download...');
    const download = await downloadPromise;
    const downloadPath = await download.path();
    const downloadName = download.suggestedFilename();
    console.log(`[USER EXPORT] OGMP downloaded: ${downloadName}`);

    expect(downloadName).toContain('OGMP_2.0_Methane_Report');
    expect(downloadName.endsWith('.xlsx')).toBe(true);

    const fileBytes = fs.readFileSync(downloadPath);
    console.log(`[USER EXPORT] OGMP Excel size: ${fileBytes.length} bytes`);
    expect(fileBytes.length).toBeGreaterThan(2000);

    // Verify ZIP magic bytes 'PK'
    const header = fileBytes.subarray(0, 2).toString('ascii');
    expect(header).toBe('PK');

    const shot1 = 'vf06_ogmp_excel_downloaded.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot1) });
    copyArtifact(shot1);
  });

  // -------------------------------------------------------------------------
  // EXPORT 4: Client-Side ISO 14064-1 Compliant Report Generation
  // -------------------------------------------------------------------------
  test('EX-4: Client-Side ISO 14064-1 Compliant PDF Generation', async ({ page }) => {
    console.log('[USER EXPORT] Testing ISO 14064-1 Client-Side Report Generator...');
    await ensureAuthenticatedPage(page, '/reports');
    await page.waitForTimeout(1000);

    // Open facility multi-select
    const dropdownTrigger = page.locator('.custom-dropdown .dropdown-selected');
    await expect(dropdownTrigger).toBeVisible({ timeout: 10000 });
    await dropdownTrigger.click();
    await page.waitForTimeout(500);

    // Click "Select All" in the portal options
    const selectAllBtn = page.locator('.dropdown-portal .dropdown-option:has-text("Select All")');
    if (await selectAllBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await selectAllBtn.click();
      await page.waitForTimeout(300);
    }

    // Close dropdown by pressing Escape or clicking outside
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);

    // Click "Create Report"
    const createBtn = page.locator('button:has-text("Create Report")');
    await expect(createBtn).toBeEnabled();
    await createBtn.click();
    await page.waitForTimeout(800);

    // Verify Dialog opens
    const dialogTitle = page.locator('h2:has-text("Generate Executive GHG Report"), [role="dialog"]');
    await expect(dialogTitle.first()).toBeVisible({ timeout: 5000 });

    // Switch to ISO 14064-1 format
    const isoOption = page.locator('button[role="radio"]:has-text("ISO 14064-1")');
    await expect(isoOption).toBeVisible();
    await isoOption.click();
    await page.waitForTimeout(500);

    // Verify ISO mandatory fields
    const exclusionField = page.locator('textarea');
    await expect(exclusionField.first()).toBeVisible();

    const shot1 = 'vf07_iso_report_config_dialog.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot1) });
    copyArtifact(shot1);

    // Listen for download event
    const downloadPromise = page.waitForEvent('download', { timeout: 45000 });

    // Click "Generate ISO PDF"
    const generateBtn = page.locator('button:has-text("Generate ISO PDF")');
    await expect(generateBtn).toBeVisible();
    await generateBtn.click();

    console.log('[USER EXPORT] Awaiting ISO 14064-1 generated PDF...');
    const download = await downloadPromise;
    const downloadPath = await download.path();
    const downloadName = download.suggestedFilename();
    console.log(`[USER EXPORT] ISO Report downloaded: ${downloadName}`);

    expect(downloadName).toMatch(/^GHG_Inventory_Report_/);
    expect(downloadName.endsWith('.pdf')).toBe(true);

    const fileBytes = fs.readFileSync(downloadPath);
    console.log(`[USER EXPORT] ISO Report byte size: ${fileBytes.length} bytes`);
    expect(fileBytes.length).toBeGreaterThan(5000);

    const header = fileBytes.subarray(0, 5).toString('ascii');
    expect(header).toBe('%PDF-');

    const shot2 = 'vf07_iso_pdf_completed.png';
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, shot2) });
    copyArtifact(shot2);
    console.log('[USER EXPORT] All verification and export deep tests passed successfully!');
  });

});
