import { chromium } from '@playwright/test';

async function run() {
  try {
    const browser = await chromium.launch({
      executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      headless: true,
    });
    console.log('Google Chrome launched successfully with Playwright!');
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:5173');
    const title = await page.title();
    console.log('Page title:', title);
    await browser.close();
  } catch (err) {
    console.error('Browser launch error:', err);
  }
}
run();
