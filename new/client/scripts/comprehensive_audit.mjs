import { chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const ARTIFACT_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\1f18a3ee-4bdf-4a64-aa96-c514668d5c68\\audit_v2';
const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';

if (!fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

const TEST_PAGES = [
  { id: 'dashboard', path: '/', name: 'Dashboard' },
  { id: 'carbon_intensity', path: '/carbon-intensity', name: 'Carbon Intensity' },
  { id: 'methane_intensity', path: '/methane-intensity', name: 'Methane Intensity' },
  { id: 'sbti', path: '/sbti', name: 'SBTi & Net-Zero' },
  { id: 'methane_explorer', path: '/methane-explorer', name: 'Emissions Map' },
  { id: 'emissions_hub', path: '/emissions', name: 'Emissions Records Hub' },
  { id: 'calc_scope1', path: '/emissions?tab=calculate&scope=1', name: 'Scope 1 Emissions Calculation' },
  { id: 'calc_scope2', path: '/emissions?tab=calculate&scope=2', name: 'Scope 2 Emissions Calculation' },
  { id: 'calc_scope3', path: '/emissions?tab=calculate&scope=3', name: 'Scope 3 Emissions Calculation' },
  { id: 'manage_facilities', path: '/manage-data?tab=facilities', name: 'Manage Data: Facilities' },
  { id: 'manage_equipment', path: '/manage-data?tab=equipment', name: 'Manage Data: Equipment' },
  { id: 'manage_production', path: '/manage-data?tab=production', name: 'Manage Data: Production' },
  { id: 'manage_factors', path: '/manage-data?tab=factors', name: 'Manage Data: Emission Factors' },
  { id: 'manage_targets', path: '/manage-data?tab=targets', name: 'Manage Data: Reduction Targets' },
  { id: 'manage_ogmp', path: '/manage-data?tab=ogmp', name: 'Manage Data: OGMP 2.0' },
  { id: 'manage_import', path: '/manage-data?tab=import', name: 'Manage Data: Import' },
  { id: 'reference_data', path: '/reference-data', name: 'Reference Data' },
  { id: 'reports', path: '/reports', name: 'Reports Page' },
  { id: 'uncertainty', path: '/uncertainty', name: 'Uncertainty Assessment' },
  { id: 'qa_dashboard', path: '/qa-dashboard', name: 'QA/QC & Diagnostics' },
  { id: 'audit_trail', path: '/audit-trail', name: 'Audit Trail' },
  { id: 'user_management', path: '/user-management', name: 'User Management' },
  { id: 'settings', path: '/settings', name: 'Settings' },
];

async function main() {
  console.log('--- STARTING COMPREHENSIVE V2 AUDIT ---');
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();

  const pageErrors = [];
  const consoleErrors = [];

  page.on('pageerror', (err) => {
    console.error('PAGE ERROR DETECTED:', err.message);
    pageErrors.push({ message: err.message, stack: err.stack });
  });

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Ignore routine favicon or harmless dev warnings if any
      if (!text.includes('favicon') && !text.includes('Failed to load resource: the server responded with a status of 401')) {
        console.warn('CONSOLE ERROR:', text);
        consoleErrors.push(text);
      }
    }
  });

  // 1. Authenticate
  console.log('Authenticating at /login...');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(1000);

  const emailInput = page.locator('input[placeholder="Email Address"]').first();
  if (await emailInput.isVisible().catch(() => false)) {
    await emailInput.fill('a');
    const pwdInput = page.locator('input[type="password"]').first();
    await pwdInput.fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForTimeout(1500);
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1000);
  }

  const results = [];

  for (const item of TEST_PAGES) {
    console.log(`\nTesting [${item.name}] at ${item.path}...`);
    const pageErrorsBefore = pageErrors.length;
    const consoleErrorsBefore = consoleErrors.length;

    try {
      await page.goto(`${BASE_URL}${item.path}`, { waitUntil: 'networkidle', timeout: 15000 }).catch(async () => {
        await page.goto(`${BASE_URL}${item.path}`, { waitUntil: 'domcontentloaded' });
      });
      await page.waitForTimeout(1500);

      // Check for React error boundary or fatal crashing text
      const bodyText = await page.locator('body').innerText().catch(() => '');
      const hasBoundaryCrash = bodyText.includes('Something went wrong') || bodyText.includes('Minified React error');

      // Check main content presence
      const hasMainOrCard = (await page.locator('main, [role="main"], h1, h2, table, form').count()) > 0;

      const pageErrorsThisPage = pageErrors.slice(pageErrorsBefore);
      const consoleErrorsThisPage = consoleErrors.slice(consoleErrorsBefore);

      const screenshotFile = path.join(ARTIFACT_DIR, `${item.id}.png`);
      await page.screenshot({ path: screenshotFile, fullPage: false });

      const passed = !hasBoundaryCrash && pageErrorsThisPage.length === 0 && hasMainOrCard;

      results.push({
        id: item.id,
        name: item.name,
        path: item.path,
        status: passed ? 'PASS' : 'FAIL',
        hasBoundaryCrash,
        pageErrors: pageErrorsThisPage,
        consoleErrors: consoleErrorsThisPage,
        screenshot: screenshotFile,
      });

      console.log(`Result for ${item.name}: ${passed ? '✓ PASS' : '✗ FAIL'}`);
      if (!passed) {
        if (hasBoundaryCrash) console.error('  -> Triggered ErrorBoundary crash text');
        if (pageErrorsThisPage.length > 0) console.error('  -> Uncaught page errors:', pageErrorsThisPage);
      }
    } catch (err) {
      console.error(`Exception while testing ${item.name}:`, err);
      results.push({
        id: item.id,
        name: item.name,
        path: item.path,
        status: 'FAIL',
        error: String(err),
      });
    }
  }

  // Also test interactive flow: Sidebar navigation click
  console.log('\nTesting Sidebar Navigation clicks...');
  try {
    const navReports = page.locator('a[href="/reports"], button:has-text("Reports")').first();
    if (await navReports.isVisible()) {
      await navReports.click();
      await page.waitForTimeout(1000);
      console.log('  Sidebar link /reports clicked successfully.');
    }
  } catch (err) {
    console.error('Sidebar navigation test error:', err);
  }

  await browser.close();

  const reportPath = path.join(ARTIFACT_DIR, 'audit_report.json');
  fs.writeFileSync(reportPath, JSON.stringify({ results, total: results.length, passed: results.filter(r => r.status === 'PASS').length }, null, 2));

  console.log(`\n========================================`);
  console.log(`COMPREHENSIVE AUDIT COMPLETE:`);
  console.log(`Total Pages/Views Tested: ${results.length}`);
  console.log(`Passed: ${results.filter(r => r.status === 'PASS').length}`);
  console.log(`Failed: ${results.filter(r => r.status === 'FAIL').length}`);
  console.log(`Full report saved at: ${reportPath}`);
  console.log(`========================================\n`);
}

main().catch(console.error);
