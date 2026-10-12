import { chromium } from '@playwright/test';
import path from 'path';
import os from 'os';
import fs from 'fs';

const CHROMIUM_1208 = path.join(
  os.homedir(),
  'AppData', 'Local', 'ms-playwright',
  'chromium-1208', 'chrome-win64', 'chrome.exe'
);

const chromeExe = fs.existsSync(CHROMIUM_1208)
  ? CHROMIUM_1208
  : 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

const BASE_URL = process.env.E2E_BASE_URL || 'http://127.0.0.1:5174';

async function main() {
  const browser = await chromium.launch({
    executablePath: chromeExe,
    headless: true,
  });

  const context = await browser.newContext();
  const page = await context.newPage();

  console.log(`Authenticating at ${BASE_URL}/login...`);
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);

  const emailInput = page.locator('input[placeholder="Email Address"]').first();
  if (await emailInput.isVisible()) {
    await emailInput.fill('a');
    const pwdInput = page.locator('input[type="password"]').first();
    await pwdInput.fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForTimeout(1500);
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
  }

  await context.storageState({ path: 'storageState.json' });
  console.log('Saved storageState.json successfully!');
  await browser.close();
}

main().catch(console.error);
