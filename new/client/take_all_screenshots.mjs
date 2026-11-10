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

const SCRIPT_DIR = import.meta.dirname;
const BASE_URL = 'http://127.0.0.1:5173';
const OUTPUT_DIR = path.resolve(SCRIPT_DIR, '..', '..', 'screenshots');

if (!fs.existsSync(OUTPUT_DIR)) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

console.log(`Saving screenshots to: ${OUTPUT_DIR}`);

// List of all pages and views
const PAGES_CONFIG = [
  // 1. Unauthenticated Login
  {
    id: '01_login',
    title: 'Login Page',
    url: `${BASE_URL}/login`,
    auth: 'none',
  },

  // 2. Main Executive Dashboard
  {
    id: '02_dashboard',
    title: 'Executive GHG Dashboard',
    url: `${BASE_URL}/`,
    auth: 'admin',
  },

  // 3. Carbon Intensity
  {
    id: '03_carbon_intensity_operational',
    title: 'Carbon Intensity - Operational Emissions',
    url: `${BASE_URL}/carbon-intensity`,
    auth: 'admin',
    action: async (page) => {
      const btn = page.locator('button:has-text("Operational Emissions"), button:has-text("Émissions Opérationnelles")').first();
      if (await btn.isVisible()) await btn.click();
      await page.waitForTimeout(500);
    }
  },
  {
    id: '04_carbon_intensity_cbam',
    title: 'Carbon Intensity - CBAM Embedded Emissions',
    url: `${BASE_URL}/carbon-intensity`,
    auth: 'admin',
    action: async (page) => {
      const btn = page.locator('button:has-text("CBAM Embedded"), button:has-text("Émissions Intégrées CBAM")').first();
      if (await btn.isVisible()) await btn.click();
      await page.waitForTimeout(500);
    }
  },

  // 4. Methane Intensity
  {
    id: '05_methane_intensity_loss_rate',
    title: 'Methane Intensity - Loss Rate (%)',
    url: `${BASE_URL}/methane-intensity`,
    auth: 'admin',
    action: async (page) => {
      const btn = page.locator('button:has-text("Loss Rate"), button:has-text("Taux de Perte")').first();
      if (await btn.isVisible()) await btn.click();
      await page.waitForTimeout(500);
    }
  },
  {
    id: '06_methane_intensity_intensity',
    title: 'Methane Intensity - CH4/Hydrocarbon Intensity',
    url: `${BASE_URL}/methane-intensity`,
    auth: 'admin',
    action: async (page) => {
      const btn = page.locator('button:has-text("Intensity"), button:has-text("Intensité")').first();
      if (await btn.isVisible()) await btn.click();
      await page.waitForTimeout(500);
    }
  },
  {
    id: '07_methane_intensity_total_ch4',
    title: 'Methane Intensity - Total CH4 (t)',
    url: `${BASE_URL}/methane-intensity`,
    auth: 'admin',
    action: async (page) => {
      const btn = page.locator('button:has-text("Total CH4")').first();
      if (await btn.isVisible()) await btn.click();
      await page.waitForTimeout(500);
    }
  },
  {
    id: '08_methane_intensity_flaring',
    title: 'Methane Intensity - Flaring & Venting Efficiency',
    url: `${BASE_URL}/methane-intensity`,
    auth: 'admin',
    action: async (page) => {
      const btn = page.locator('button:has-text("Flaring"), button:has-text("Torche")').first();
      if (await btn.isVisible()) await btn.click();
      await page.waitForTimeout(500);
    }
  },

  // 5. SBTi & Net-Zero Dashboard
  {
    id: '09_sbti_dashboard',
    title: 'SBTi & Net-Zero Dashboard',
    url: `${BASE_URL}/sbti`,
    auth: 'admin',
  },

  // 6. Emissions Map / Methane Explorer
  {
    id: '10_methane_explorer_map',
    title: 'Methane Explorer GIS Emissions Map',
    url: `${BASE_URL}/methane-explorer`,
    auth: 'admin',
    action: async (page) => {
      await page.waitForTimeout(3000); // Give Leaflet tiles extra time to render
    }
  },

  // 7. Calculations & Emissions Forms
  {
    id: '11_emissions_scope_selection',
    title: 'Emissions Calculations - Scope Selection',
    url: `${BASE_URL}/emissions`,
    auth: 'admin',
  },
  {
    id: '12_emissions_scope1_form',
    title: 'Emissions Calculations - Scope 1 Direct Emissions',
    url: `${BASE_URL}/emissions?scope=1`,
    auth: 'admin',
  },
  {
    id: '13_emissions_scope2_form',
    title: 'Emissions Calculations - Scope 2 Indirect Energy',
    url: `${BASE_URL}/emissions?scope=2`,
    auth: 'admin',
  },
  {
    id: '14_emissions_scope3_form',
    title: 'Emissions Calculations - Scope 3 Value Chain',
    url: `${BASE_URL}/emissions?scope=3`,
    auth: 'admin',
  },

  // 8. Manage Data Tabs
  {
    id: '15_manage_data_pending_review',
    title: 'Manage Data - Pending Review',
    url: `${BASE_URL}/manage-data?tab=pending`,
    auth: 'admin',
  },
  {
    id: '16_manage_data_factors',
    title: 'Manage Data - Emission Factors',
    url: `${BASE_URL}/manage-data?tab=factors`,
    auth: 'admin',
  },
  {
    id: '17_manage_data_regions',
    title: 'Manage Data - Facilities & Regions',
    url: `${BASE_URL}/manage-data?tab=facilities`,
    auth: 'admin',
  },
  {
    id: '18_manage_data_production',
    title: 'Manage Data - Production Data',
    url: `${BASE_URL}/manage-data?tab=production`,
    auth: 'admin',
  },
  {
    id: '19_manage_data_sources',
    title: 'Manage Data - Emission Sources',
    url: `${BASE_URL}/manage-data?tab=sources`,
    auth: 'admin',
  },
  {
    id: '20_manage_data_goals',
    title: 'Manage Data - Emission Goals & Base Years',
    url: `${BASE_URL}/manage-data?tab=goals`,
    auth: 'admin',
  },
  {
    id: '21_manage_data_mitigation',
    title: 'Manage Data - Mitigation Projects',
    url: `${BASE_URL}/manage-data?tab=mitigation`,
    auth: 'admin',
  },
  {
    id: '22_manage_data_ogmp_surveys',
    title: 'Manage Data - OGMP 2.0 Surveys',
    url: `${BASE_URL}/manage-data?tab=ogmp`,
    auth: 'admin',
  },
  {
    id: '23_manage_data_ldar',
    title: 'Manage Data - LDAR & Fugitives',
    url: `${BASE_URL}/manage-data?tab=ldar`,
    auth: 'admin',
  },
  {
    id: '24_manage_data_cbam',
    title: 'Manage Data - CBAM Products',
    url: `${BASE_URL}/manage-data?tab=cbam`,
    auth: 'admin',
  },

  // 9. Reference Data
  {
    id: '25_reference_data',
    title: 'Reference Data - Factor Compendium',
    url: `${BASE_URL}/reference-data`,
    auth: 'admin',
  },

  // 10. Reports Studio
  {
    id: '26_reports_studio',
    title: 'Reports & Document Generation Studio',
    url: `${BASE_URL}/reports`,
    auth: 'admin',
  },

  // 11. Uncertainty Assessment
  {
    id: '27_uncertainty_assessment',
    title: 'Uncertainty Assessment & Sensitivity Analysis',
    url: `${BASE_URL}/uncertainty`,
    auth: 'admin',
  },

  // 12. QA/QC & Diagnostics
  {
    id: '28_qa_dashboard_queue',
    title: 'QA/QC & Diagnostics - Anomaly Queue',
    url: `${BASE_URL}/qa-dashboard`,
    auth: 'admin',
    action: async (page) => {
      const tab = page.locator('button[role="tab"]:has-text("Resolution Queue"), button[role="tab"]:has-text("File d\'Attente")').first();
      if (await tab.isVisible()) await tab.click();
      await page.waitForTimeout(500);
    }
  },
  {
    id: '29_qa_dashboard_diagnostics',
    title: 'QA/QC & Diagnostics - System Diagnostics',
    url: `${BASE_URL}/qa-dashboard`,
    auth: 'admin',
    action: async (page) => {
      const tab = page.locator('button[role="tab"]:has-text("Diagnostics"), button[role="tab"]:has-text("Diagnostics")').first();
      if (await tab.isVisible()) await tab.click();
      await page.waitForTimeout(500);
    }
  },
  {
    id: '30_qa_dashboard_uncertainty',
    title: 'QA/QC & Diagnostics - Uncertainty & Tolerances',
    url: `${BASE_URL}/qa-dashboard`,
    auth: 'admin',
    action: async (page) => {
      const tab = page.locator('button[role="tab"]:has-text("Uncertainty"), button[role="tab"]:has-text("Incertitude")').first();
      if (await tab.isVisible()) await tab.click();
      await page.waitForTimeout(500);
    }
  },

  // 13. Audit Trail
  {
    id: '31_audit_trail',
    title: 'Cryptographic Audit Trail',
    url: `${BASE_URL}/audit-trail`,
    auth: 'admin',
  },

  // 14. User Management (IT Admin)
  {
    id: '32_user_management_users',
    title: 'User Management - Directory',
    url: `${BASE_URL}/user-management?tab=users`,
    auth: 'it',
  },
  {
    id: '33_user_management_sessions',
    title: 'User Management - Active Sessions & Security',
    url: `${BASE_URL}/user-management?tab=sessions`,
    auth: 'it',
    action: async (page) => {
      const tab = page.locator('#um-tab-sessions, button:has-text("Active Sessions"), button:has-text("Sessions Actives")').first();
      if (await tab.isVisible()) await tab.click();
      await page.waitForTimeout(500);
    }
  },

  // 15. Settings & Protocols
  {
    id: '34_settings_gwp',
    title: 'Settings - IPCC GWP Standards',
    url: `${BASE_URL}/settings`,
    auth: 'admin',
    action: async (page) => {
      const tab = page.locator('button[role="tab"]:has-text("IPCC GWP"), button[role="tab"]:has-text("GWP")').first();
      if (await tab.isVisible()) await tab.click();
      await page.waitForTimeout(500);
    }
  },
  {
    id: '35_settings_ogmp',
    title: 'Settings - OGMP 2.0 Baseline & Thresholds',
    url: `${BASE_URL}/settings`,
    auth: 'admin',
    action: async (page) => {
      const tab = page.locator('button[role="tab"]:has-text("OGMP 2.0"), button[role="tab"]:has-text("Baseline")').first();
      if (await tab.isVisible()) await tab.click();
      await page.waitForTimeout(500);
    }
  },
  {
    id: '36_settings_facilities',
    title: 'Settings - Facility Overrides',
    url: `${BASE_URL}/settings`,
    auth: 'admin',
    action: async (page) => {
      const tab = page.locator('button[role="tab"]:has-text("Facility Overrides"), button[role="tab"]:has-text("Dérogations")').first();
      if (await tab.isVisible()) await tab.click();
      await page.waitForTimeout(500);
    }
  },

  // 16. UI Gallery (Dev)
  {
    id: '37_dev_ui_gallery',
    title: 'Design System & UI Component Gallery',
    url: `${BASE_URL}/__ui`,
    auth: 'admin',
  }
];

async function run() {
  const browser = await chromium.launch({
    executablePath: chromeExe,
    headless: true,
  });

  const adminContext = await browser.newContext({
    storageState: path.join(SCRIPT_DIR, 'storageState.json'),
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });

  const itContext = await browser.newContext({
    storageState: path.join(SCRIPT_DIR, 'storageState_it.json'),
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });

  const anonContext = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });

  const results = [];

  for (let i = 0; i < PAGES_CONFIG.length; i++) {
    const item = PAGES_CONFIG[i];
    console.log(`[${i + 1}/${PAGES_CONFIG.length}] Capturing: ${item.title}...`);

    let context = adminContext;
    if (item.auth === 'it') context = itContext;
    else if (item.auth === 'none') context = anonContext;

    const page = await context.newPage();

    try {
      await page.goto(item.url, { waitUntil: 'load', timeout: 30000 });
      await page.waitForTimeout(1500);

      if (item.action) {
        await item.action(page);
      }

      // Wait a moment for dynamic data/charts to finish painting
      await page.waitForTimeout(1000);

      const filePath = path.join(OUTPUT_DIR, `${item.id}.png`);
      await page.screenshot({
        path: filePath,
        fullPage: true,
      });

      console.log(`  -> Saved: ${item.id}.png`);
      results.push({ ...item, filePath, success: true });
    } catch (err) {
      console.error(`  -> Failed: ${item.id}:`, err.message);
      results.push({ ...item, success: false, error: err.message });
    } finally {
      await page.close();
    }
  }

  await browser.close();

  // Save index json
  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'manifest.json'),
    JSON.stringify(results, null, 2),
    'utf-8'
  );
  console.log(`\nAll done! Manifest written to ${path.join(OUTPUT_DIR, 'manifest.json')}`);
}

run().catch(console.error);
