import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import os from 'os';

const CHROMIUM_1208 = path.join(
  os.homedir(),
  'AppData', 'Local', 'ms-playwright',
  'chromium-1208', 'chrome-win64', 'chrome.exe'
);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 1,
  reporter: 'list',
  timeout: 60000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    headless: true,
    storageState: 'storageState.json',
    // Use the locally installed Chromium-1208 (avoids needing headless-shell-1243)
    launchOptions: {
      executablePath: CHROMIUM_1208,
    },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
