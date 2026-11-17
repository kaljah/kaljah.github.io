/**
 * test_master_publication_report_studio.spec.js
 *
 * END-TO-END VERIFICATION OF THE REGIONAL ASSET MASTER REPORT WIZARD
 *
 * Validates against playwright.config.js baseURL & storageState:
 * 1. Wizard heading & DB-driven /api/reports/master-report/regions hydration (including national)
 * 2. Unsupported 20yr GWP omitted from Master Report GWP selector
 * 3. Async 202 Accepted job enqueue -> GET job status polling -> PDF download with SHA-256 headers
 * 4. Cross-Basin Benchmark Excel export with SHA-256 header
 * 5. French language Master Report generation yielding *_FR.pdf Content-Disposition
 */

import { test, expect } from '@playwright/test';

async function openReportsStudio(page) {
  await page.goto('/reports', { waitUntil: 'domcontentloaded', timeout: 30000 });
  if (page.url().includes('/login')) {
    const email = process.env.E2E_USER_EMAIL;
    const password = process.env.E2E_USER_PASSWORD;
    if (!email || !password) {
      throw new Error('Redirected to /login without authenticated storageState or E2E_USER_EMAIL/E2E_USER_PASSWORD.');
    }
    await page.locator('input[type="email"], input[placeholder*="Email"]').first().fill(email);
    await page.locator('input[type="password"]').first().fill(password);
    await page.locator('button[type="submit"]').first().click();
    await page.waitForURL((url) => !url.toString().includes('/login'), { timeout: 15000 });
    await page.goto('/reports', { waitUntil: 'domcontentloaded', timeout: 30000 });
  }
}

test.describe.serial('Regional Asset Master Report Wizard E2E Suite', () => {
  test('Renders Wizard with DB-driven regions and excludes unsupported 20yr GWP option', async ({ page }) => {
    await openReportsStudio(page);

    const wizardHeading = page.locator('h2:has-text("Regional Asset Master Report Wizard")');
    await expect(wizardHeading).toBeVisible({ timeout: 15000 });

    const regionSelect = page.locator('#master-region-select');
    await expect(regionSelect).toBeVisible();
    await expect(regionSelect).toBeEnabled({ timeout: 15000 });

    const optionCount = await regionSelect.locator('option').count();
    expect(optionCount).toBeGreaterThan(0);

    const gwpSelect = page.locator('#master-gwp-select');
    const gwpValues = await gwpSelect.locator('option').evaluateAll((opts) => opts.map((o) => o.value));
    expect(gwpValues).toEqual(['AR5', 'AR6', 'AR4']);
  });

  test('Enqueues async 202 job, polls status, and downloads Master Publication PDF with SHA-256 headers', async ({ page }) => {
    await openReportsStudio(page);

    const downloadBtn = page.getByRole('button', { name: /Download (Regional|National) Master Report/i });
    await expect(downloadBtn).toBeEnabled({ timeout: 15000 });

    const enqueuePromise = page.waitForResponse(
      (resp) => resp.url().endsWith('/api/reports/master-report') && resp.request().method() === 'POST',
      { timeout: 30000 }
    );
    const pollPromise = page.waitForResponse(
      (resp) => /\/api\/reports\/master-report\/jobs\/[A-Za-z0-9_-]+$/.test(resp.url()) && resp.request().method() === 'GET',
      { timeout: 45000 }
    );
    const filePromise = page.waitForResponse(
      (resp) => /\/api\/reports\/master-report\/jobs\/[A-Za-z0-9_-]+\/download$/.test(resp.url()) && resp.request().method() === 'GET',
      { timeout: 45000 }
    );

    await downloadBtn.click();

    const enqueueResp = await enqueuePromise;
    expect(enqueueResp.status()).toBe(202);
    const jobPayload = await enqueueResp.json();
    expect(jobPayload.job_id).toBeTruthy();

    const pollResp = await pollPromise;
    expect(pollResp.status()).toBe(200);

    const fileResp = await filePromise;
    expect(fileResp.status()).toBe(200);
    expect(fileResp.headers()['content-type']).toContain('application/pdf');
    expect(fileResp.headers()['x-report-sha256']).toHaveLength(64);
    expect(fileResp.headers()['x-dataset-sha256']).toHaveLength(64);

    await expect(page.getByRole('link', { name: /Download ready PDF/i })).toBeVisible({ timeout: 15000 });
  });

  test('Exports Cross-Basin Benchmark Excel workbook with SHA-256 header', async ({ page }) => {
    await openReportsStudio(page);

    const excelBtn = page.getByRole('button', { name: /Export Regional Inventory \(Excel\)/i });
    await expect(excelBtn).toBeEnabled({ timeout: 15000 });

    const [excelResp] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().endsWith('/api/reports/master-report/benchmark-excel') && resp.request().method() === 'POST',
        { timeout: 45000 }
      ),
      excelBtn.click(),
    ]);

    expect(excelResp.status()).toBe(200);
    expect(excelResp.headers()['content-type']).toMatch(/spreadsheetml|excel/);
    expect(excelResp.headers()['x-report-sha256']).toHaveLength(64);
  });

  test('Generates French Master Report PDF yielding _FR.pdf download header', async ({ page }) => {
    await openReportsStudio(page);

    const langSelect = page.locator('#master-language-select');
    await expect(langSelect).toBeVisible();
    await langSelect.selectOption('fr');

    const downloadBtn = page.getByRole('button', { name: /Download (Regional|National) Master Report/i });
    await expect(downloadBtn).toBeEnabled({ timeout: 15000 });

    const enqueuePromise = page.waitForResponse(
      (resp) => resp.url().endsWith('/api/reports/master-report') && resp.request().method() === 'POST',
      { timeout: 30000 }
    );
    const filePromise = page.waitForResponse(
      (resp) => /\/api\/reports\/master-report\/jobs\/[A-Za-z0-9_-]+\/download$/.test(resp.url()) && resp.request().method() === 'GET',
      { timeout: 45000 }
    );

    await downloadBtn.click();

    const enqueueResp = await enqueuePromise;
    expect(enqueueResp.status()).toBe(202);
    expect(enqueueResp.request().postDataJSON()).toMatchObject({ language: 'fr' });

    const fileResp = await filePromise;
    expect(fileResp.status()).toBe(200);
    expect(fileResp.headers()['content-type']).toContain('application/pdf');
    expect(fileResp.headers()['content-disposition']).toContain('_FR.pdf');
  });
});
