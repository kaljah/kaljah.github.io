import { chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const ARTIFACT_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\1f18a3ee-4bdf-4a64-aa96-c514668d5c68\\screenshots_v2';
const BASE_URL = 'http://127.0.0.1:5174';

if (!fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

const PAGES = [
  { name: '02_dashboard', url: '/', title: 'Dashboard Enhanced (Redesigned)' },
  { name: '03_carbon_intensity', url: '/carbon-intensity', title: 'Carbon Intensity (Segmented BOE / CBAM)' },
  { name: '04_methane_intensity', url: '/methane-intensity', title: 'Methane Intensity (Unified Multi-Metric Benchmark)' },
  { name: '05_sbti_netzero', url: '/sbti', title: 'SBTi Trajectory (Milestone Zoom 2030/2050)' },
  { name: '07_emissions_calculations', url: '/emissions', title: 'Emissions Intake Hub (Status Strip & Scope Cards)' },
  { name: '08_manage_data', url: '/manage-data?tab=facilities', title: 'Manage Data (Horizontal Sub-Nav Tab Bar)' },
  { name: '14_manage_data_ogmp', url: '/manage-data?tab=ogmp', title: 'Manage Data OGMP 2.0 Tab' },
  { name: '18_reports', url: '/reports', title: 'Reports (1-Click Compliance Presets & Workbench)' },
  { name: '19_uncertainty', url: '/uncertainty', title: 'Uncertainty Assessment (Redesigned)' },
  { name: '20_qa_dashboard', url: '/qa-dashboard', title: 'QA/QC & Diagnostics (Formatted IDs & Severity Badges)' },
  { name: '21_audit_trail', url: '/audit-trail', title: 'Audit Trail (Cryptographic SHA-256 Ledger Health)' },
  { name: '23_settings', url: '/settings', title: 'Settings (Live Regulatory Protocol Status Strip)' },
];

async function main() {
  console.log('Launching browser for V2 screenshots on port 5174...');
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();

  // Authenticate
  console.log('Authenticating at http://127.0.0.1:5174/login ...');
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

  // Iterate pages
  const results = [];
  for (const item of PAGES) {
    console.log(`Navigating to ${item.title} (${item.url})...`);
    try {
      await page.goto(`${BASE_URL}${item.url}`, { waitUntil: 'networkidle', timeout: 15000 }).catch(async () => {
        await page.goto(`${BASE_URL}${item.url}`, { waitUntil: 'domcontentloaded' });
      });
      await page.waitForTimeout(2000);

      const filePath = path.join(ARTIFACT_DIR, `${item.name}.png`);
      await page.screenshot({ path: filePath, fullPage: false });
      console.log(`Saved: ${filePath}`);

      results.push({
        name: item.name,
        title: item.title,
        url: item.url,
        file: filePath,
        status: 'OK',
      });
    } catch (err) {
      console.error(`Failed on ${item.url}:`, err);
      results.push({
        name: item.name,
        title: item.title,
        url: item.url,
        error: String(err),
        status: 'ERROR',
      });
    }
  }

  await browser.close();
  fs.writeFileSync(path.join(ARTIFACT_DIR, 'results_v2.json'), JSON.stringify(results, null, 2));
  console.log('All V2 screenshots captured successfully!');
}

main().catch(console.error);
