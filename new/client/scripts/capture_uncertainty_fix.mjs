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
  
  // Capture view showing the newly formatted chart cards
  await page.screenshot({
    path: 'C:/Users/samsung/.gemini/antigravity/brain/1f18a3ee-4bdf-4a64-aa96-c514668d5c68/screenshots/19_uncertainty.png',
    fullPage: false
  });
  
  // Also capture scrolled view to see the full chart
  const chartEl = page.locator('.ua-chart-card').first();
  if (await chartEl.isVisible()) {
    await chartEl.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);
    await page.screenshot({
      path: 'C:/Users/samsung/.gemini/antigravity/brain/1f18a3ee-4bdf-4a64-aa96-c514668d5c68/screenshots/19_uncertainty_chart_detail.png',
      fullPage: false
    });
  }
  
  console.log('Uncertainty screenshots captured successfully!');
  await browser.close();
}

main().catch(console.error);
