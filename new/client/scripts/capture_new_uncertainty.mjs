import { chromium } from '@playwright/test';

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
  
  await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  
  const emailInput = page.locator('input[placeholder="Email Address"]').first();
  await emailInput.fill('a');
  const pwdInput = page.locator('input[type="password"]').first();
  await pwdInput.fill('a');
  await page.locator('button[type="submit"]:has-text("Sign In")').click();
  
  await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1500);
  
  await page.goto('http://127.0.0.1:5173/uncertainty', { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);
  
  // 1. Capture the Top Hero & Analytics view
  await page.screenshot({
    path: 'C:/Users/samsung/.gemini/antigravity/brain/1f18a3ee-4bdf-4a64-aa96-c514668d5c68/screenshots/19_uncertainty_new_hero.png',
    fullPage: false
  });
  
  // 2. Scroll to the new Table and expand the first row
  const firstRow = page.locator('.ua-table tbody tr.ua-row-clickable').first();
  if (await firstRow.isVisible()) {
    await firstRow.click();
    await page.waitForTimeout(800);
    await firstRow.scrollIntoViewIfNeeded();
    await page.waitForTimeout(800);
    await page.screenshot({
      path: 'C:/Users/samsung/.gemini/antigravity/brain/1f18a3ee-4bdf-4a64-aa96-c514668d5c68/screenshots/19_uncertainty_new_table.png',
      fullPage: false
    });
  }
  
  // 3. Overwrite the main 19_uncertainty.png
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  await page.screenshot({
    path: 'C:/Users/samsung/.gemini/antigravity/brain/1f18a3ee-4bdf-4a64-aa96-c514668d5c68/screenshots/19_uncertainty.png',
    fullPage: false
  });
  
  console.log('New layout screenshots captured successfully!');
  await browser.close();
}

main().catch(console.error);
