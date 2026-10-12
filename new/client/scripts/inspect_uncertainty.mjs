import { chromium } from '@playwright/test';

async function main() {
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  
  await page.goto('http://127.0.0.1:5173/login');
  await page.fill('input[placeholder="Email Address"]', 'a');
  await page.fill('input[type="password"]', 'a');
  await page.locator('button[type="submit"]:has-text("Sign In")').click();
  await page.waitForTimeout(2000);
  
  await page.goto('http://127.0.0.1:5173/uncertainty');
  await page.waitForTimeout(3000);
  
  const info = await page.evaluate(() => {
    const sections = Array.from(document.querySelectorAll('.category-section'));
    const charts = Array.from(document.querySelectorAll('.recharts-wrapper'));
    const ticks = Array.from(document.querySelectorAll('.recharts-cartesian-axis-tick text')).map(t => ({
      text: t.textContent,
      y: t.getAttribute('y'),
      transform: t.getAttribute('transform')
    }));
    return {
      sectionCount: sections.length,
      chartCount: charts.length,
      ticks
    };
  });
  
  console.log('Inspection info:', JSON.stringify(info, null, 2));
  await browser.close();
}

main().catch(console.error);
