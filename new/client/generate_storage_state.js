import { chromium } from '@playwright/test';
import path from 'path';
import os from 'os';

const CHROMIUM_1208 = path.join(
  os.homedir(),
  'AppData', 'Local', 'ms-playwright',
  'chromium-1208', 'chrome-win64', 'chrome.exe'
);

async function globalAuth() {
  const browser = await chromium.launch({
    executablePath: CHROMIUM_1208,
    headless: true,
  });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('Navigating to login page...');
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
  if (await skipBtn.isVisible().catch(() => false)) {
    await skipBtn.click();
    await page.waitForTimeout(500);
  }

  const emailInput = page.locator('input[placeholder="Email Address"]');
  if (await emailInput.isVisible().catch(() => false)) {
    await emailInput.fill('a');
    await page.locator('input[type="password"]').fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
    console.log('Successfully logged in!');
  }

  await page.waitForTimeout(1500);
  await context.storageState({ path: 'storageState.json' });
  console.log('storageState.json saved successfully!');
  await browser.close();
}

globalAuth().catch(err => {
  console.error('Auth error:', err);
  process.exit(1);
});
