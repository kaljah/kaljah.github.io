import { chromium } from '@playwright/test';

async function check() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });
  const page = await browser.newPage();
  page.on('console', (msg) => console.log('CONSOLE:', msg.type(), msg.text()));
  page.on('pageerror', (err) => console.log('PAGEERROR:', err.message, '\n', err.stack));

  await page.goto('http://127.0.0.1:5174/login');
  await page.waitForTimeout(1000);
  const emailInput = page.locator('input[placeholder="Email Address"]').first();
  await emailInput.fill('a');
  const pwdInput = page.locator('input[type="password"]').first();
  await pwdInput.fill('a');
  await page.locator('button[type="submit"]:has-text("Sign In")').click();
  await page.waitForTimeout(2000);

  console.log('Navigating to /sbti...');
  await page.goto('http://127.0.0.1:5174/sbti');
  await page.waitForTimeout(3000);

  await browser.close();
}

check().catch(console.error);
