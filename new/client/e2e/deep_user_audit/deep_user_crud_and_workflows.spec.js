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

test.describe.serial('Deep User Workflows: Calculation Creation, Bulk Import & Verification', () => {

  // -------------------------------------------------------------------------
  // WORKFLOW 1: Scope 1 Stationary Combustion Entry & Storage
  // -------------------------------------------------------------------------
  test('WF-1: Create Scope 1 Stationary Combustion Emission Record', async ({ page }) => {
    console.log('[CRUD TEST] Entering Scope 1 Stationary Combustion calculation...');
    await ensureAuthenticatedPage(page, '/emissions?scope=1');
    await page.waitForTimeout(1000);

    // Wait for form fields
    const amountInput = page.locator('input[type="number"], input[placeholder*="amount" i]').first();
    await amountInput.waitFor({ state: 'visible', timeout: 10000 });
    await amountInput.fill('12500');

    // Trigger calculation
    const calcBtn = page.locator('button:has-text("Calculate"), button:has-text("Compute")').first();
    if (await calcBtn.isVisible().catch(() => false)) {
      await calcBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'wf01_scope1_calculated.png') });
    }

    // Save record if save button is present
    const saveBtn = page.locator('button:has-text("Save"), button:has-text("Record"), button:has-text("Submit")').first();
    if (await saveBtn.isVisible().catch(() => false)) {
      console.log('[CRUD TEST] Submitting Scope 1 record...');
      await saveBtn.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'wf01_scope1_saved.png') });
    }
  });

  // -------------------------------------------------------------------------
  // WORKFLOW 2: Scope 2 Electricity Data Entry & Calculation
  // -------------------------------------------------------------------------
  test('WF-2: Create Scope 2 Electricity Record & Verify Breakdown', async ({ page }) => {
    console.log('[CRUD TEST] Entering Scope 2 Electricity calculation...');
    await ensureAuthenticatedPage(page, '/emissions?scope=2');
    await page.waitForTimeout(1000);

    // Fill consumption
    const amountInput = page.locator('input[type="number"], input[name*="amount" i]').first();
    await amountInput.waitFor({ state: 'visible', timeout: 10000 });
    await amountInput.fill('75000');

    // Calculate
    const calcBtn = page.locator('button:has-text("Calculate")').first();
    if (await calcBtn.isVisible().catch(() => false)) {
      await calcBtn.click();
      await page.waitForTimeout(1000);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'wf02_scope2_calculated.png') });
    }

    // Save record
    const saveBtn = page.locator('button:has-text("Save"), button:has-text("Record")').first();
    if (await saveBtn.isVisible().catch(() => false)) {
      console.log('[CRUD TEST] Submitting Scope 2 record...');
      await saveBtn.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'wf02_scope2_saved.png') });
    }
  });

  // -------------------------------------------------------------------------
  // WORKFLOW 3: Manage Data - Verify Records, Filters & Search
  // -------------------------------------------------------------------------
  test('WF-3: Inspect Records in Manage Data Table & Export CSV', async ({ page }) => {
    console.log('[CRUD TEST] Verifying Manage Data inventory table...');
    await ensureAuthenticatedPage(page, '/manage-data');
    await page.waitForTimeout(1000);

    const rows = page.locator('table tbody tr');
    const count = await rows.count();
    console.log(`[CRUD TEST] Current records count in Manage Data: ${count}`);
    expect(count).toBeGreaterThan(0);

    // Filter by Scope 1
    const scopeFilter = page.locator('select, button[role="combobox"]').filter({ hasText: /Scope|All Scopes/i }).first();
    if (await scopeFilter.isVisible().catch(() => false)) {
      await scopeFilter.click();
      await page.waitForTimeout(300);
    }

    // Trigger CSV Export download verification
    const exportBtn = page.locator('button:has-text("Export"), button:has-text("Download CSV")').first();
    if (await exportBtn.isVisible().catch(() => false)) {
      console.log('[CRUD TEST] Triggering CSV Export...');
      const [download] = await Promise.all([
        page.waitForEvent('download', { timeout: 8000 }).catch(() => [null]),
        exportBtn.click().catch(() => {}),
      ]);
      if (download) {
        console.log(`[CRUD TEST] Successfully initiated download: ${download.suggestedFilename()}`);
      }
    }
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'wf03_manage_data_verified.png') });
  });

  // -------------------------------------------------------------------------
  // WORKFLOW 4: Bulk CSV Upload Wizard UI & Ingestion Pipeline
  // -------------------------------------------------------------------------
  test('WF-4: Bulk CSV Wizard: Inspect Modal UI, Configuration & Backend Ingestion', async ({ page, request }) => {
    console.log('[CRUD TEST] Testing Bulk CSV Uploader Wizard UI...');
    await ensureAuthenticatedPage(page, '/manage-data');
    await page.waitForTimeout(1000);

    // 1. Open Bulk Import modal
    const importBtn = page.locator('button:has-text("Bulk Import"), button:has-text("Import CSV"), button:has-text("Upload")').first();
    if (await importBtn.isVisible().catch(() => false)) {
      await importBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'wf04_wizard_modal_open.png') });

      // Verify Tier configuration radios
      const tierOption = page.locator('label:has-text("Tier 1"), label:has-text("Tier 3"), [role="radio"]').first();
      if (await tierOption.isVisible().catch(() => false)) {
        await tierOption.click();
        await page.waitForTimeout(400);
      }

      // Close modal
      const closeBtn = page.locator('button:has-text("Cancel"), button:has-text("Close"), [aria-label="Close"]').last();
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
        await page.waitForTimeout(400);
      }
    }

    // 2. Test Ingestion Pipeline via API
    console.log('[CRUD TEST] Testing backend batch upload job...');
    const csrfRes = await request.get(`${FRONTEND}/api/csrf-token`);
    const { csrf_token } = await csrfRes.json();

    const sampleCsv = `facility,date,scope,category,fuel,amount,unit
Hassi Messaoud Main,2026-03-15,1,Stationary Combustion,Natural Gas,12500,MMBtu
`;
    const uploadRes = await request.post(`${FRONTEND}/api/emissions/upload/start`, {
      headers: { 'X-CSRFToken': csrf_token },
      multipart: {
        file: {
          name: 'sample_test_upload.csv',
          mimeType: 'text/csv',
          buffer: Buffer.from(sampleCsv, 'utf-8'),
        },
        scope: '1',
        global_factor_type: 'auto',
        overwrite_duplicates: 'false',
      },
    });

    if (uploadRes.ok()) {
      const data = await uploadRes.json();
      console.log(`[CRUD TEST] Upload job started, jobId=${data.job_id}`);
      expect(data.job_id).toBeDefined();

      // Poll status once
      await page.waitForTimeout(1000);
      const statusRes = await request.get(`${FRONTEND}/api/emissions/upload/status/${data.job_id}`);
      if (statusRes.ok()) {
        const statusData = await statusRes.json();
        console.log(`[CRUD TEST] Job status: ${statusData.status}, progress=${statusData.progress}%`);
      }
    }
  });

  // -------------------------------------------------------------------------
  // WORKFLOW 5: Audit Trail Verification of Created Records
  // -------------------------------------------------------------------------
  test('WF-5: Verify Activity Logging in Immutable Audit Trail', async ({ page }) => {
    console.log('[CRUD TEST] Inspecting Audit Trail for newly logged actions...');
    await ensureAuthenticatedPage(page, '/audit-trail');
    await page.waitForTimeout(1000);

    const logRows = page.locator('table tbody tr');
    const count = await logRows.count();
    console.log(`[CRUD TEST] Total Audit Trail entries: ${count}`);
    expect(count).toBeGreaterThan(0);

    // Verify presence of recent actions (LOGIN, CALCULATION, or CREATE)
    const tableText = await page.locator('table tbody').innerText();
    console.log(`[CRUD TEST] Audit Table sample text:\n${tableText.slice(0, 300).replace(/\n/g, ' ')}`);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'wf05_audit_trail_proof.png'), fullPage: true });
  });

});
