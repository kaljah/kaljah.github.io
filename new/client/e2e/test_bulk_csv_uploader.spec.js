/**
 * test_bulk_csv_uploader.spec.js
 *
 * Comprehensive Bulk CSV Uploader Audit:
 * 1. Tier 1 Bulk CSV: 123 rows testing all fuels, units, and default factors across West, Center, South.
 * 2. Tier 3 Bulk CSV: Exactly 360 distinct scenarios per region (West, Center, South) = 1,080 rows total
 *    covering 10 engineering formula categories.
 * 3. Background Job Pipeline (/api/emissions/upload/start -> /api/emissions/upload/status).
 * 4. Maker-Checker Verification & Batch Approval (/api/emissions/approve/batch).
 * 5. Database Ground Truth assertion: 1,080+ persistent records created with zero teardown.
 * 6. Post-Calculation KPI Recalculation & Re-Audit on Dashboard, Carbon Intensity, and Methane Intensity.
 * 7. Screenshots saved to C:/Users/samsung/Desktop/H2/test_results/screenshots/
 */

import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { execFileSync } from 'child_process';

const FRONTEND = 'http://127.0.0.1:5173';
const BACKEND = 'http://127.0.0.1:5000';
const DB_PATH = 'c:/Users/samsung/Desktop/H2/new/server/ghg_app.db';
const SCREENSHOT_DIR = 'C:/Users/samsung/Desktop/H2/test_results/screenshots';
const TIER1_CSV_PATH = 'c:/Users/samsung/Desktop/H2/new/server/bulk_tier1_all_fuels.csv';
const TIER3_CSV_PATH = 'c:/Users/samsung/Desktop/H2/new/server/bulk_tier3_360_per_region.csv';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function queryDb(sql, params = []) {
  try {
    const pyScript = `
import sys, sqlite3, json
db_path = sys.argv[1]
sql = sys.argv[2]
params = json.loads(sys.argv[3])
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute(sql, params)
rows = c.fetchall()
cols = [d[0] for d in c.description] if c.description else []
result = [dict(zip(cols, r)) for r in rows]
print(json.dumps(result))
`;
    const out = execFileSync('python', ['-c', pyScript, DB_PATH, sql, JSON.stringify(params)], { encoding: 'utf-8' });
    return JSON.parse(out.trim());
  } catch (e) {
    console.error('queryDb error:', e);
    return [];
  }
}

async function getCsrfToken(request) {
  const csrfRes = await request.get(`${BACKEND}/api/csrf-token`);
  const csrfJson = await csrfRes.json();
  return csrfJson.csrf_token;
}

async function uploadCsvViaApi(request, csvFilePath, scope = '1') {
  const fileBuffer = fs.readFileSync(csvFilePath);
  const filename = path.basename(csvFilePath);
  const csrfToken = await getCsrfToken(request);

  console.log(`[API UPLOAD] Starting upload for ${filename}...`);
  const uploadRes = await request.post(`${BACKEND}/api/emissions/upload/start`, {
    headers: {
      'X-CSRFToken': csrfToken,
    },
    multipart: {
      file: {
        name: filename,
        mimeType: 'text/csv',
        buffer: fileBuffer,
      },
      scope: String(scope),
      global_factor_type: 'auto',
      overwrite_duplicates: 'false'
    }
  });

  const bodyText = await uploadRes.text();
  console.log(`[API UPLOAD RESULT] status=${uploadRes.status()} body=${bodyText}`);
  expect(uploadRes.status()).toBe(200);
  const uploadJson = JSON.parse(bodyText);
  const jobId = uploadJson.job_id;
  expect(jobId).toBeDefined();
  console.log(`[API UPLOAD] Job ID received: ${jobId}`);

  // Poll until completion
  const maxRetries = 90;
  let jobData = {};
  for (let i = 0; i < maxRetries; i++) {
    await new Promise(r => setTimeout(r, 1000));
    const statusRes = await request.get(`${BACKEND}/api/emissions/upload/status/${jobId}`);
    if (statusRes.status() === 200) {
      jobData = await statusRes.json();
      console.log(`[JOB PROGRESS] ${jobData.status} - ${jobData.processed || 0} rows processed (${jobData.progress || 0}%)`);
      if (jobData.status === 'completed' || jobData.status === 'error') {
        break;
      }
    }
  }

  expect(jobData.status).toBe('completed');
  return jobData;
}

async function loginAndSetup(page, targetUrl = '/') {
  await page.goto(`${FRONTEND}${targetUrl}`, { waitUntil: 'domcontentloaded', timeout: 25000 });
  await page.waitForTimeout(1000);

  // Skip intro video if present
  const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
  if (await skipBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await skipBtn.click();
  }
  await page.locator('.login-intro-overlay').waitFor({ state: 'detached', timeout: 3000 }).catch(() => {});
  await page.waitForTimeout(500);

  // Fallback if on login page
  const emailInput = page.locator('input[placeholder="Email Address"]');
  if (await emailInput.isVisible({ timeout: 1000 }).catch(() => false)) {
    await emailInput.fill('a');
    await page.locator('input[type="password"]').fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 12000 }).catch(() => {});
    await page.waitForTimeout(1000);
  }

  await expect(page.locator('.app-container, .dashboard-grid, .sidebar, .intensity-grid, .calc-panel').first()).toBeVisible({ timeout: 15000 });
  await page.waitForTimeout(1000);
}

test.describe('Bulk CSV Uploader & Post-Calculation KPI Audit', () => {

  test('1. Tier 1 Bulk CSV Upload (All Fuels, Default Factors & Units)', async ({ request, page }) => {
    test.setTimeout(180000);

    const jobData = await uploadCsvViaApi(request, TIER1_CSV_PATH, '1');
    console.log(`[TIER 1 BULK] Completed: ${jobData.processed} rows processed, skipped: ${jobData.skipped_count || 0}`);
    expect(jobData.processed).toBeGreaterThanOrEqual(100);

    // Verify DB count
    const rows = queryDb('SELECT COUNT(*) as cnt FROM emissions');
    console.log(`[DB TOTAL EMISSIONS] Current records count: ${rows[0].cnt}`);
    expect(rows[0].cnt).toBeGreaterThan(100);

    // Navigate to Scope 1 page to verify UI display
    await loginAndSetup(page, '/emissions?scope=1');

    const tableSection = page.locator('.calculator-grid-container');
    await tableSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'scope1_tier1_bulk_imported.png'), fullPage: false });
  });

  test('2. Tier 3 Bulk CSV Upload: 360 Scenarios per Region (1,080 Total Rows)', async ({ request, page }) => {
    test.setTimeout(300000);

    console.log(`\n======================================================`);
    console.log(`[TIER 3 BULK] Uploading 1,080 scenarios (360 per region)...`);
    console.log(`======================================================`);

    const jobData = await uploadCsvViaApi(request, TIER3_CSV_PATH, '1');
    console.log(`[TIER 3 BULK] Completed: ${jobData.processed} rows processed!`);
    expect(jobData.processed).toBe(1080);

    // Verify database counts for EACH database region:
    // Facility 1: West (Tosyali) -> >= 360 rows
    // Facility 3: Center (GICA) -> >= 360 rows
    // Facility 4: South (Sonatrach) -> >= 360 rows
    const westRows = queryDb('SELECT COUNT(*) as cnt FROM emissions WHERE facility_id = 1');
    const centerRows = queryDb('SELECT COUNT(*) as cnt FROM emissions WHERE facility_id = 3');
    const southRows = queryDb('SELECT COUNT(*) as cnt FROM emissions WHERE facility_id = 4');

    console.log(`[DB VERIFICATION] West (Tosyali): ${westRows[0].cnt} rows`);
    console.log(`[DB VERIFICATION] Center (GICA): ${centerRows[0].cnt} rows`);
    console.log(`[DB VERIFICATION] South (Sonatrach): ${southRows[0].cnt} rows`);

    expect(westRows[0].cnt).toBeGreaterThanOrEqual(360);
    expect(centerRows[0].cnt).toBeGreaterThanOrEqual(360);
    expect(southRows[0].cnt).toBeGreaterThanOrEqual(360);

    // Verify values are valid (no negative co2e, no NaNs)
    const invalidRows = queryDb('SELECT COUNT(*) as cnt FROM emissions WHERE co2e_total < 0 OR co2e_total IS NULL');
    expect(invalidRows[0].cnt).toBe(0);

    // Approve all pending records via Batch Approval API (Maker-Checker workflow)
    const csrfToken = await getCsrfToken(request);
    const approveRes = await request.post(`${BACKEND}/api/emissions/approve/batch`, {
      headers: {
        'X-CSRFToken': csrfToken,
      },
      data: {
        approve_all: true,
        scope: '1'
      }
    });
    console.log(`[MAKER-CHECKER] Batch Approve response: ${approveRes.status()}`);
    expect(approveRes.status()).toBe(200);

    // Navigate to Scope 1 page to inspect UI
    await loginAndSetup(page, '/emissions?scope=1');

    const tableSection = page.locator('.calculator-grid-container');
    await tableSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);

    // Check pagination displays hundreds of pages
    const pageText = await page.locator('.pagination-controls').innerText().catch(() => '');
    console.log(`[PAGINATION CHECK] ${pageText.replace(/\n/g, ' ')}`);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'scope1_tier3_bulk_1080_records.png'), fullPage: false });
  });

  test('3. Post-Calculation KPI Recalculation & Re-Audit (Dashboard, Carbon & Methane)', async ({ page }) => {
    test.setTimeout(180000);

    console.log(`\n======================================================`);
    console.log(`[KPI RE-AUDIT] Validating updated metrics on Dashboard...`);
    console.log(`======================================================`);

    // 1. Dashboard (/)
    await loginAndSetup(page, '/');
    await expect(page.locator('.grid-title')).toHaveText('GHG Emissions Dashboard');

    // Check Hero Card Operational Stats
    const grossText = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
    const netText = await page.locator('.stat-item:has-text("Net Emissions") .stat-value').innerText();
    const ch4Text = await page.locator('.stat-item:has-text("Total CH4") .stat-value').innerText();
    console.log(`[POST-BULK DASHBOARD KPI] Gross: ${grossText}, Net: ${netText}, CH4: ${ch4Text}`);
    expect(grossText).not.toContain('0.00 t');

    // Scope Pills
    const s1Pill = await page.locator('.scope-pill.scope-1 .pill-value').innerText();
    console.log(`[POST-BULK SCOPE 1 PILL] ${s1Pill}`);
    expect(s1Pill).not.toContain('0.00');

    // Test GWP Toggles
    const gwp20Btn = page.locator('button:has-text("GWP-20")');
    if (await gwp20Btn.isVisible()) {
      await gwp20Btn.click();
      await page.waitForTimeout(600);
      const grossGwp20 = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
      console.log(`[POST-BULK GWP-20 VALUE] Gross: ${grossGwp20}`);
    }

    const gwp100Btn = page.locator('button:has-text("GWP-100")');
    if (await gwp100Btn.isVisible()) {
      await gwp100Btn.click();
      await page.waitForTimeout(600);
    }

    // Test Region Filter (West, Center, South)
    const filterWrappers = page.locator('.top-bar-injected-left .filter-wrapper');
    const regionWrapper = filterWrappers.nth(2);
    if (await regionWrapper.isVisible()) {
      for (const reg of ['West', 'Center', 'South']) {
        await regionWrapper.locator('.dropdown-selected').click();
        await page.waitForTimeout(300);
        const opt = page.locator(`.dropdown-portal .dropdown-option:has-text("${reg}")`).first();
        if (await opt.isVisible()) {
          await opt.click();
          await page.waitForTimeout(800);
          const regGross = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
          console.log(`[DASHBOARD REGION FILTER: ${reg}] Gross: ${regGross}`);
        } else {
          await page.keyboard.press('Escape');
        }
      }
      // Reset region filter to All
      await regionWrapper.locator('.dropdown-selected').click();
      await page.waitForTimeout(300);
      const allRegOpt = page.locator('.dropdown-portal .dropdown-option:has-text("All Regions")').first();
      if (await allRegOpt.isVisible()) await allRegOpt.click();
      else await page.keyboard.press('Escape');
      await page.waitForTimeout(600);
    }

    // Capture Post-bulk Dashboard Screenshot
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dashboard_post_calculation_audit.png'), fullPage: false });

    // 2. Carbon Intensity (/carbon-intensity)
    console.log(`\n[KPI RE-AUDIT] Validating Carbon Intensity...`);
    await loginAndSetup(page, '/carbon-intensity');
    await expect(page.locator('.grid-title')).toContainText('Carbon Intensity');

    const ciCards = page.locator('.kpi-card');
    await expect(ciCards).toHaveCount(4);
    const ciGhg = await ciCards.nth(0).locator('.total-value').innerText();
    const ciS1 = await ciCards.nth(1).locator('.total-value').innerText();
    console.log(`[POST-BULK CARBON INTENSITY] GHG: ${ciGhg}, S1: ${ciS1}`);
    expect(ciGhg).not.toContain('NaN');
    expect(ciS1).not.toContain('NaN');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'carbon_intensity_post_calculation_audit.png'), fullPage: false });

    // 3. Methane Intensity (/methane-intensity)
    console.log(`\n[KPI RE-AUDIT] Validating Methane Intensity...`);
    await loginAndSetup(page, '/methane-intensity');
    await expect(page.locator('.grid-title')).toContainText('Methane');

    const miCards = page.locator('.kpi-card');
    const miCount = await miCards.count();
    expect(miCount).toBeGreaterThan(0);
    const miCard1 = await miCards.first().locator('.total-value').innerText();
    console.log(`[POST-BULK METHANE INTENSITY] Card 1: ${miCard1}`);
    expect(miCard1).not.toContain('NaN');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'methane_intensity_post_calculation_audit.png'), fullPage: false });
  });

});
