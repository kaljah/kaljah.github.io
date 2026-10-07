import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import os from 'os';
import fs from 'fs';

const CHROMIUM_1208 = path.join(
  os.homedir(),
  'AppData', 'Local', 'ms-playwright',
  'chromium-1208', 'chrome-win64', 'chrome.exe'
);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }], ['json', { outputFile: 'playwright-report/test-results.json' }]]
    : 'list',
  timeout: 60000,
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: true,
    storageState: 'storageState.json',
    // Use the locally installed Chromium-1208 when present, else Playwright managed browser
    launchOptions: fs.existsSync(CHROMIUM_1208) ? { executablePath: CHROMIUM_1208 } : {},
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
