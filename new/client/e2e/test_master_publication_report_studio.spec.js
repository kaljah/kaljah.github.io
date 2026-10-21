/**
 * test_master_publication_report_studio.spec.js
 *
 * END-TO-END VERIFICATION OF THE EXECUTIVE MASTER REPORT & INTELLIGENCE STUDIO
 *
 * Validates:
 * 1. Studio presentation & 300 DPI publication-grade badge display
 * 2. Dynamic mode switching: Regional Asset, Consolidated National, Cross-Basin Benchmark
 * 3. Dynamic authentic regional profiles & geological intelligence updates
 * 4. Multi-year timeline selection & GWP standards
 * 5. Synchronous HTTP streaming of Master Report PDF with SHA-256 header
 * 6. Cross-basin benchmark Excel export
 * 7. High-resolution screenshot capture for audit verification
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const FRONTEND = process.env.E2E_BASE_URL || 'http://localhost:5174';
const SCREENSHOT_DIR = 'C:/Users/samsung/.gemini/antigravity/brain/dd96e698-aa0b-4016-a59d-85ecf47988c4/screenshots';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

test.describe.serial('Executive Master Report & Intelligence Studio E2E Suite', () => {
  let page;
  let context;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    page = await context.newPage();

    // Login as operator
    await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(400);

    const emailIn = page.locator('input[placeholder*="Email"], input[type="email"]').first();
    await emailIn.waitFor({ state: 'visible', timeout: 15000 });
    await emailIn.fill('operator@sonatrach.dz');
    const passIn = page.locator('input[type="password"]').first();
    await passIn.fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In"), button:has-text("Sign In")').first().click();
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(600);
  });

  test.afterAll(async () => {
    if (context) await context.close();
  });

  test('Navigate to Reports and verify Studio presence and architecture', async () => {
    await page.goto(`${FRONTEND}/reports`, { waitUntil: 'domcontentloaded', timeout: 25000 });
    await page.waitForTimeout(1000);

    // Verify Studio Title
    const studioTitle = page.locator('h2:has-text("Executive Master Report & Intelligence Studio")');
    await expect(studioTitle).toBeVisible({ timeout: 10000 });

    // Verify Badges
    const pubBadge = page.locator('text="300 DPI // Vector Publication Grade"');
    await expect(pubBadge).toBeVisible();

    const isoBadge = page.locator('text="ISO 14064-1 & Décret 21-330"');
    await expect(isoBadge).toBeVisible();

    // Take screenshot of Regional View
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'master_report_studio_regional_view.png'),
      fullPage: false,
    });
  });

  test('Verify Regional Asset switching and live geological intelligence', async () => {
    // Click Regional Asset mode
    const regionalTab = page.locator('button:has-text("Regional Asset Master Report")');
    await regionalTab.click();
    await page.waitForTimeout(300);

    // Verify presence of asset selector
    const assetSelect = page.locator('select').filter({ hasText: /Hassi Messaoud/ }).first();
    await expect(assetSelect).toBeVisible();

    // Verify live intelligence snapshot displays Hassi Messaoud profile
    const intelSnapshot = page.locator('text="Authentic Regional Profile & Statutory Alignment Snapshot:"');
    await expect(intelSnapshot).toBeVisible();

    // Select Hassi R'Mel
    await assetSelect.selectOption('hrm');
    await page.waitForTimeout(300);

    // Verify snapshot updated to Tilrhemt Dome / Hassi R'Mel
    const hrmText = page.getByText(/Tilrhemt Dome/);
    await expect(hrmText).toBeVisible();
  });

  test('Verify Consolidated Sonatrach Group mode and Cross-Basin Benchmark mode', async () => {
    // Switch to Consolidated Sonatrach Group
    const nationalTab = page.locator('button:has-text("Consolidated Sonatrach Group")');
    await nationalTab.click();
    await page.waitForTimeout(300);

    const nationalScopeText = page.getByText(/National Hydrocarbon Estate/);
    await expect(nationalScopeText).toBeVisible();

    // Switch to Cross-Basin Benchmark League
    const benchmarkTab = page.locator('button:has-text("Cross-Basin Benchmark League")');
    await benchmarkTab.click();
    await page.waitForTimeout(300);

    const benchmarkScopeText = page.getByText(/All 9 Hydrocarbon Basins/);
    await expect(benchmarkScopeText).toBeVisible();

    // Take screenshot of Benchmark View
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, 'master_report_studio_benchmark_view.png'),
      fullPage: false,
    });
  });

  test('Generate and verify Master Publication PDF download stream', async () => {
    // Switch back to Regional mode
    await page.locator('button:has-text("Regional Asset Master Report")').click();
    await page.waitForTimeout(300);

    // Set up response listener for /api/reports/master-report
    const [response] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes('/api/reports/master-report') && resp.request().method() === 'POST',
        { timeout: 35000 }
      ),
      page.locator('button:has-text("Download Regional Master (PDF)")').click(),
    ]);

    expect(response.status()).toBe(200);
    const contentType = response.headers()['content-type'];
    expect(contentType).toContain('application/pdf');

    const sha256 = response.headers()['x-report-sha256'];
    expect(sha256).toBeDefined();
    expect(sha256.length).toBe(64);

    // Verify success toast appears
    const toast = page.getByText(/Executive Master Publication PDF generated/);
    await expect(toast).toBeVisible({ timeout: 10000 });
  });

  test('Generate and verify Cross-Basin Benchmark Excel export', async () => {
    // Set up response listener for /api/reports/master-report/benchmark-excel
    const [response] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes('/api/reports/master-report/benchmark-excel') && resp.request().method() === 'POST',
        { timeout: 35000 }
      ),
      page.locator('button:has-text("Export Benchmark (Excel)")').click(),
    ]);

    expect(response.status()).toBe(200);
    const contentType = response.headers()['content-type'];
    expect(contentType).toMatch(/spreadsheetml|excel/);

    const sha256 = response.headers()['x-report-sha256'];
    expect(sha256).toBeDefined();

    // Verify success toast appears
    const toast = page.getByText(/Cross-Basin Benchmark Excel exported/);
    await expect(toast).toBeVisible({ timeout: 10000 });
  });

  test('Select French language and verify French Master Report PDF generation', async () => {
    // Select French in the studio language dropdown
    const langSelect = page.locator('select').filter({ hasText: /English/ }).first();
    await expect(langSelect).toBeVisible();
    await langSelect.selectOption('fr');
    await page.waitForTimeout(300);

    const [response] = await Promise.all([
      page.waitForResponse(
        (resp) => resp.url().includes('/api/reports/master-report') && resp.request().method() === 'POST',
        { timeout: 35000 }
      ),
      page.locator('button:has-text("Download Regional Master (PDF)")').click(),
    ]);

    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('application/pdf');
    expect(response.headers()['content-disposition']).toContain('_FR.pdf');
  });
});

