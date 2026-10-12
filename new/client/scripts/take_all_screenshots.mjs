import { chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const ARTIFACT_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\1f18a3ee-4bdf-4a64-aa96-c514668d5c68\\screenshots';
const BASE_URL = 'http://127.0.0.1:5173';

if (!fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

const PAGES = [
  { name: '01_login', url: '/login', requiresAuth: false, title: 'Login Page' },
  { name: '02_dashboard', url: '/', requiresAuth: true, title: 'Dashboard Enhanced' },
  { name: '03_carbon_intensity', url: '/carbon-intensity', requiresAuth: true, title: 'Carbon Intensity' },
  { name: '04_methane_intensity', url: '/methane-intensity', requiresAuth: true, title: 'Methane Intensity' },
  { name: '05_sbti_netzero', url: '/sbti', requiresAuth: true, title: 'SBTi & Net-Zero' },
  { name: '06_methane_explorer_map', url: '/methane-explorer', requiresAuth: true, title: 'Emissions Map / Methane Explorer', waitExtra: 3000 },
  { name: '07_emissions_calculations', url: '/emissions', requiresAuth: true, title: 'Emissions Calculations' },
  { name: '08_manage_data_facilities', url: '/manage-data?tab=facilities', requiresAuth: true, title: 'Manage Data: Active Regions' },
  { name: '09_manage_data_production', url: '/manage-data?tab=production', requiresAuth: true, title: 'Manage Data: Annual Production' },
  { name: '10_manage_data_sources', url: '/manage-data?tab=sources', requiresAuth: true, title: 'Manage Data: Emission Sources' },
  { name: '11_manage_data_goals', url: '/manage-data?tab=goals', requiresAuth: true, title: 'Manage Data: Emission Goals' },
  { name: '12_manage_data_mitigation', url: '/manage-data?tab=mitigation', requiresAuth: true, title: 'Manage Data: Mitigation Projects' },
  { name: '13_manage_data_cbam', url: '/manage-data?tab=cbam', requiresAuth: true, title: 'Manage Data: EU CBAM' },
  { name: '14_manage_data_ogmp', url: '/manage-data?tab=ogmp', requiresAuth: true, title: 'Manage Data: OGMP 2.0' },
  { name: '15_manage_data_factors', url: '/manage-data?tab=factors', requiresAuth: true, title: 'Manage Data: Custom Factors' },
  { name: '16_manage_data_pending_review', url: '/manage-data?tab=pending', requiresAuth: true, title: 'Manage Data: Pending Review' },
  { name: '17_reference_data', url: '/reference-data', requiresAuth: true, title: 'Reference Data' },
  { name: '18_reports', url: '/reports', requiresAuth: true, title: 'Reports' },
  { name: '19_uncertainty', url: '/uncertainty', requiresAuth: true, title: 'Uncertainty Assessment' },
  { name: '20_qa_dashboard', url: '/qa-dashboard', requiresAuth: true, title: 'QA/QC & Diagnostics' },
  { name: '21_audit_trail', url: '/audit-trail', requiresAuth: true, title: 'Audit Trail' },
  { name: '22_user_management', url: '/user-management', requiresAuth: true, title: 'User Management' },
  { name: '23_settings', url: '/settings', requiresAuth: true, title: 'Settings' },
];

async function main() {
  console.log('Launching browser...');
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();
  const consoleErrors = {};

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const url = page.url();
      consoleErrors[url] = consoleErrors[url] || [];
      consoleErrors[url].push(msg.text());
    }
  });

  // Capture Login Page first
  console.log('Capturing Login Page...');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(1000);
  const loginPath = path.join(ARTIFACT_DIR, '01_login.png');
  await page.screenshot({ path: loginPath, fullPage: true });
  console.log(`Saved: ${loginPath}`);

  // Authenticate
  console.log('Authenticating as admin...');
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

  // Iterate pages
  const results = [];
  for (const item of PAGES) {
    if (item.name === '01_login') continue; // already captured

    console.log(`Navigating to ${item.title} (${item.url})...`);
    try {
      await page.goto(`${BASE_URL}${item.url}`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(item.waitExtra || 1800);

      // Special handling for Leaflet map on /methane-explorer
      if (item.url === '/methane-explorer') {
        await page.waitForTimeout(3000);
      }

      const filePath = path.join(ARTIFACT_DIR, `${item.name}.png`);
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`Saved: ${filePath}`);

      results.push({
        name: item.name,
        title: item.title,
        url: item.url,
        status: 'OK',
        file: filePath,
      });
    } catch (err) {
      console.error(`Error capturing ${item.title}:`, err.message);
      results.push({
        name: item.name,
        title: item.title,
        url: item.url,
        status: `ERROR: ${err.message}`,
      });
    }
  }

  await browser.close();
  console.log('\n--- Screenshot Summary ---');
  console.log(JSON.stringify(results, null, 2));

  fs.writeFileSync(
    path.join(ARTIFACT_DIR, 'screenshot_results.json'),
    JSON.stringify({ results, consoleErrors }, null, 2)
  );
}

main().catch(console.error);
