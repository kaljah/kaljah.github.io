import { chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const ARTIFACT_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\1f18a3ee-4bdf-4a64-aa96-c514668d5c68\\screenshots_v2';
const BASE_URL = 'http://127.0.0.1:5174';

if (!fs.existsSync(ARTIFACT_DIR)) {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
}

const SCOPES = [
  { name: 'scope1_calculation', url: '/emissions?scope=scope1', title: 'Scope 1 Direct Emissions Form' },
  { name: 'scope2_calculation', url: '/emissions?scope=scope2', title: 'Scope 2 Indirect Electricity Form' },
  { name: 'scope3_calculation', url: '/emissions?scope=scope3', title: 'Scope 3 Value Chain Form' },
];

async function main() {
  console.log('Launching browser for Scope 1, 2, 3 calculations on port 5174...');
  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
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

  for (const item of SCOPES) {
    console.log(`Navigating to ${item.title} (${item.url})...`);
    await page.goto(`${BASE_URL}${item.url}`, { waitUntil: 'networkidle' }).catch(() => {});
    await page.waitForTimeout(2000);

    const outPath = path.join(ARTIFACT_DIR, `${item.name}.png`);
    await page.screenshot({ path: outPath, fullPage: true });
    console.log(`Saved screenshot: ${outPath}`);
  }

  await browser.close();
  console.log('Done capturing scope calculation screenshots!');
}

main().catch(console.error);
