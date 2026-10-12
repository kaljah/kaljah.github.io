import { chromium } from '@playwright/test';
import path from 'path';

const ARTIFACT_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\1f18a3ee-4bdf-4a64-aa96-c514668d5c68\\screenshots_v2';
const BASE_URL = 'http://127.0.0.1:5174';

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 950 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.message || err));

  // Authenticate
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

  console.log('Navigating to /reports...');
  await page.goto(`${BASE_URL}/reports`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(2000);

  // 1. Initial view
  const pagePath = path.join(ARTIFACT_DIR, '18_reports.png');
  await page.screenshot({ path: pagePath, fullPage: false });
  console.log(`Saved screenshot: ${pagePath}`);

  // 2. Select a facility in Card 2 (Table filter)
  console.log('Filtering table by facility to test cross-card sync button...');
  // The Region / Facility select in Card 2
  const facilitySelects = page.locator('select');
  const count = await facilitySelects.count();
  console.log(`Found ${count} select elements`);
  
  // Find the select that contains facility options (like 170 or options with 'El Merk')
  let facilitySelect = null;
  for (let i = 0; i < count; i++) {
    const s = facilitySelects.nth(i);
    const text = await s.innerText().catch(() => '');
    if (text.includes('El Merk') || text.includes('All Regions & Facilities')) {
      facilitySelect = s;
      break;
    }
  }

  if (facilitySelect) {
    // Select El Merk (value 170 if present, or second option)
    const options = await facilitySelect.locator('option').all();
    if (options.length > 1) {
      const val = await options[1].getAttribute('value');
      console.log(`Selecting facility value: ${val}`);
      await facilitySelect.selectOption(val);
      await page.waitForTimeout(800);
    }
  }

  // 3. Screenshot with "Sync from Table Filters" button active in Card 1
  const syncReadyPath = path.join(ARTIFACT_DIR, '18_reports_sync_ready.png');
  await page.screenshot({ path: syncReadyPath, fullPage: false });
  console.log(`Saved sync ready screenshot: ${syncReadyPath}`);

  // 4. Click the "Sync from Table Filters" button
  const syncBtn = page.locator('button:has-text("Sync from Table Filters")').first();
  if (await syncBtn.isVisible().catch(() => false)) {
    console.log('Clicking Sync from Table Filters button...');
    await syncBtn.click();
    await page.waitForTimeout(1000);
    const syncedPath = path.join(ARTIFACT_DIR, '18_reports_synced.png');
    await page.screenshot({ path: syncedPath, fullPage: false });
    console.log(`Saved synced screenshot: ${syncedPath}`);
  }

  // 5. Click "Create Report" to capture modal with document thumbnail preview
  const createReportBtn = page.locator('button:has-text("Create Report")').first();
  if (await createReportBtn.isVisible()) {
    console.log('Opening Create Report modal...');
    await createReportBtn.click();
    await page.waitForTimeout(1000);
    const modalPath = path.join(ARTIFACT_DIR, '18_reports_modal.png');
    await page.screenshot({ path: modalPath, fullPage: false });
    console.log(`Saved modal screenshot: ${modalPath}`);

    // If Master Report option is present and enabled, click it
    const masterOpt = page.locator('button:has-text("Executive Master Report"), [role="radio"]:has-text("Executive Master Report"), label:has-text("Executive Master Report")').first();
    if (await masterOpt.isVisible().catch(() => false)) {
      console.log('Selecting Executive Master Report format...');
      await masterOpt.click();
      await page.waitForTimeout(500);
      const masterModalPath = path.join(ARTIFACT_DIR, '18_reports_modal_master.png');
      await page.screenshot({ path: masterModalPath, fullPage: false });
      console.log(`Saved master modal screenshot: ${masterModalPath}`);
    }
  }

  await browser.close();
  console.log('All screenshots captured successfully.');
}

main().catch(console.error);
