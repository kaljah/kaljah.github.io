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
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1.5,
  });

  const page = await context.newPage();

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

  console.log('Navigating to /emissions...');
  await page.goto(`${BASE_URL}/emissions`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(2000);

  const outPath = path.join(ARTIFACT_DIR, '07_emissions_calculations.png');
  await page.screenshot({ path: outPath, fullPage: true });
  console.log(`Saved screenshot: ${outPath}`);

  await browser.close();
}

main().catch(console.error);
