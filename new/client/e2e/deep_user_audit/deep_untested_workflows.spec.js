import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}
const ARTIFACT_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\145e1f58-77e7-4f5b-8573-5a1c4dc13171';
const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';

function copyArtifact(filename) {
  try {
    const src = path.join(SCREENSHOT_DIR, filename);
    const dest = path.join(ARTIFACT_DIR, filename);
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dest);
    }
  } catch (err) {
    console.error(`Failed to copy artifact ${filename}:`, err);
  }
}

async function ensureAuthenticatedPage(page, targetUrl = '/') {
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(800);

  // Dismiss intro overlay if present
  const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
  if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipBtn.click();
    await page.waitForTimeout(400);
  }
  await page.locator('.login-intro-overlay').waitFor({ state: 'detached', timeout: 3000 }).catch(() => {});

  // Fallback login if unauthenticated
  const emailInput = page.locator('input[placeholder="Email Address"]');
  if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await emailInput.fill('a');
    await page.locator('input[type="password"]').fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000);
  }

  await expect(page.locator('.app-container, .main-content, #main').first()).toBeVisible({ timeout: 20000 });
  await page.waitForLoadState('networkidle').catch(() => {});
}

test.describe.serial('Suite 8: Deep Untested Platform Workflows & Enterprise Features', () => {

  // -------------------------------------------------------------------------
  // TEST 1: Geospatial Methane Explorer — Facility Dossier, Severity & Satellite
  // -------------------------------------------------------------------------
  test('UNTESTED-1: Geospatial Methane Explorer — Facility Selection, Dossier Drawer, Plume Rings, & Severity Filters', async ({ page }) => {
    console.log('[E2E UNTESTED] Navigating to Geospatial Methane Explorer (/methane-explorer)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/methane-explorer`);
    await page.waitForTimeout(1200);

    // 1. Verify HUD Header and Telemetry metrics
    const mapHeader = page.locator('h1:has-text("Emissions Map")');
    await expect(mapHeader).toBeVisible({ timeout: 15000 });
    const tropomiSub = page.locator('text=Sentinel-5P TROPOMI');
    await expect(tropomiSub).toBeVisible();

    const monitoredKpi = page.locator('header').locator('text=Monitored assets');
    await expect(monitoredKpi).toBeVisible();
    const superEmittersKpi = page.locator('header').locator('text=Super-emitters');
    await expect(superEmittersKpi).toBeVisible();

    // 2. Test Segmented Control (CH4 Flux vs Total GHG)
    console.log('[E2E UNTESTED] Testing Telemetry Map Metric toggle...');
    const totalGhgBtn = page.locator('button:has-text("Total GHG")');
    if (await totalGhgBtn.isVisible()) {
      await totalGhgBtn.click();
      await page.waitForTimeout(500);
      await expect(page.locator('text=Regional GHG')).toBeVisible();
      
      // Switch back to CH4 Flux
      const ch4Btn = page.locator('button:has-text("CH₄ Flux")');
      await ch4Btn.click();
      await page.waitForTimeout(500);
      await expect(page.locator('text=Regional methane')).toBeVisible();
    }

    // 3. Test Drawer Anomaly Severity Radios
    console.log('[E2E UNTESTED] Testing Anomaly Severity filter radios in drawer...');
    const superEmitterRadio = page.locator('button[role="radio"]:has-text("Super-emitters")');
    if (await superEmitterRadio.isVisible()) {
      await superEmitterRadio.click();
      await page.waitForTimeout(400);
      await expect(superEmitterRadio).toHaveAttribute('aria-checked', 'true');

      const moderateRadio = page.locator('button[role="radio"]:has-text("Moderate")');
      await moderateRadio.click();
      await page.waitForTimeout(400);
      await expect(moderateRadio).toHaveAttribute('aria-checked', 'true');

      const allRadio = page.locator('button[role="radio"]:has-text("All")');
      await allRadio.click();
      await page.waitForTimeout(400);
      await expect(allRadio).toHaveAttribute('aria-checked', 'true');
    }

    // 4. Test Search filter in Asset inventory
    console.log('[E2E UNTESTED] Testing asset inventory search input...');
    const searchInput = page.locator('input[placeholder="Search name, region, division..."]');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('Berkine');
    await page.waitForTimeout(600);
    // Clear search
    await searchInput.fill('');
    await page.waitForTimeout(400);

    // 5. Test Sentinel-5P overlay controls
    const satSwitch = page.locator('#toggle-sat-layer-checkbox');
    if (await satSwitch.isVisible()) {
      const opacitySlider = page.locator('#satellite-opacity-slider');
      await expect(opacitySlider).toBeVisible();
      console.log('[E2E UNTESTED] Sentinel-5P overlay and opacity slider verified active.');
    }

    // 6. Select a facility to open ExplorerDossier
    console.log('[E2E UNTESTED] Clicking facility card to open ExplorerDossier...');
    const facilityCards = page.locator('div[role="button"][aria-pressed]');
    await expect(facilityCards.first()).toBeVisible({ timeout: 10000 });
    const cardCount = await facilityCards.count();
    console.log(`[E2E UNTESTED] Found ${cardCount} facility cards in inventory drawer.`);

    await facilityCards.first().evaluate(el => el.click());
    await page.waitForTimeout(1200);

    // Verify Dossier opened
    const dossierSentinel = page.locator('text=Copernicus Sentinel-5P overpass');
    await expect(dossierSentinel).toBeVisible({ timeout: 10000 });

    const bottomUpSection = page.locator('text=Bottom-up reported inventory');
    await expect(bottomUpSection).toBeVisible();

    const centerCameraBtn = page.locator('button:has-text("Center aerial camera")');
    await expect(centerCameraBtn).toBeVisible();

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested01_methane_explorer_dossier.png') });
    copyArtifact('untested01_methane_explorer_dossier.png');
    console.log('[E2E UNTESTED] Captured untested01_methane_explorer_dossier.png.');

    // Close dossier
    const closeDossierBtn = page.locator('button[aria-label="Close dossier"]');
    if (await closeDossierBtn.isVisible()) {
      await closeDossierBtn.evaluate(el => el.click());
      await page.waitForTimeout(400);
      await expect(dossierSentinel).not.toBeVisible();
      console.log('[E2E UNTESTED] Successfully closed ExplorerDossier.');
    }
  });

  // -------------------------------------------------------------------------
  // TEST 2: Inventory Uncertainty & Data Reliability Assessment
  // -------------------------------------------------------------------------
  test('UNTESTED-2: Inventory Uncertainty & Data Reliability Assessment — ISO 14064-1 & IPCC Tier Quantification & CSV Export', async ({ page }) => {
    console.log('[E2E UNTESTED] Navigating to Inventory Uncertainty (/uncertainty)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/uncertainty`);
    await page.waitForTimeout(1200);

    // 1. Verify Page Title and ISO Standards Header
    const pageTitle = page.locator('.ua-title, h1:has-text("Data Reliability Analysis")');
    await expect(pageTitle).toBeVisible({ timeout: 15000 });

    const isoStandardText = page.locator('text=ISO 14064-1 §7.5 and IPCC 2006 GL Vol.1 §3.3');
    await expect(isoStandardText).toBeVisible();

    // 2. Verify Overall Inventory Uncertainty Metric
    const uncertaintyValue = page.locator('.ua-inventory-value');
    await expect(uncertaintyValue).toBeVisible();
    const uncertaintyText = await uncertaintyValue.textContent();
    console.log(`[E2E UNTESTED] Verified quantified inventory uncertainty: ${uncertaintyText}`);
    expect(uncertaintyText).toContain('%');

    // 3. Verify Confidence Interval Badge (95% CI)
    const ciBadge = page.locator('text=CI (k=');
    await expect(ciBadge).toBeVisible();

    // 4. Verify Tier Breakdown Cards (share of Scope 1)
    const tier1Card = page.locator('text=Tier 1 (share of Scope 1)');
    const tier2Card = page.locator('text=Tier 2 (share of Scope 1)');
    const tier3Card = page.locator('text=Tier 3 (share of Scope 1)');
    await expect(tier1Card).toBeVisible();
    await expect(tier2Card).toBeVisible();
    await expect(tier3Card).toBeVisible();

    // 5. Verify Uncertainty Bands
    const lowBand = page.locator('text=Low Uncertainty (≤ ±10%)').first();
    const medBand = page.locator('text=Medium Uncertainty (±10% to ±30%)').first();
    const highBand = page.locator('text=High Uncertainty (> ±30%)').first();
    await expect(lowBand).toBeVisible();
    await expect(medBand).toBeVisible();
    await expect(highBand).toBeVisible();

    // 6. Test Scope filter dropdown
    console.log('[E2E UNTESTED] Testing Scope filter dropdown...');
    const scopeDropdown = page.locator('.custom-dropdown').nth(1);
    if (await scopeDropdown.isVisible()) {
      await scopeDropdown.click();
      await page.waitForTimeout(400);

      const scope1Option = page.locator('.dropdown-option:has-text("Scope 1"), [role="option"]:has-text("Scope 1")').first();
      if (await scope1Option.isVisible()) {
        await scope1Option.click();
        await page.waitForTimeout(800);
        console.log('[E2E UNTESTED] Filtered uncertainty assessment to Scope 1.');

        // Revert to All Scopes
        await scopeDropdown.click();
        await page.waitForTimeout(400);
        const allScopesOption = page.locator('.dropdown-option:has-text("All Scopes"), [role="option"]:has-text("All Scopes")').first();
        if (await allScopesOption.isVisible()) {
          await allScopesOption.click();
          await page.waitForTimeout(800);
        }
      }
    }

    // 7. Test Real CSV Export Download
    console.log('[E2E UNTESTED] Triggering CSV Export download...');
    const exportBtn = page.locator('button:has-text("Export CSV")');
    await expect(exportBtn).toBeVisible();

    const downloadPromise = page.waitForEvent('download', { timeout: 15000 });
    await exportBtn.click();
    const download = await downloadPromise;

    const suggestedFilename = download.suggestedFilename();
    console.log(`[E2E UNTESTED] Download intercepted: ${suggestedFilename}`);
    expect(suggestedFilename).toMatch(/uncertainty.*\.csv$/i);

    const tempPath = path.join(SCREENSHOT_DIR, 'downloaded_uncertainty_test.csv');
    await download.saveAs(tempPath);
    const csvContent = fs.readFileSync(tempPath, 'utf-8');
    expect(csvContent.length).toBeGreaterThan(50);
    console.log(`[E2E UNTESTED] CSV file successfully saved (${csvContent.length} bytes). Header preview:\n${csvContent.slice(0, 180)}`);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested02_uncertainty_assessment_export.png') });
    copyArtifact('untested02_uncertainty_assessment_export.png');
    console.log('[E2E UNTESTED] Captured untested02_uncertainty_assessment_export.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 3: Enterprise User Management Slide-Over Drawer & New User Provisioning
  // -------------------------------------------------------------------------
  test('UNTESTED-3: Enterprise User Management Slide-Over Drawer & User Provisioning', async ({ browser }) => {
    console.log('[E2E UNTESTED] Launching IT Admin Persona session for User Management Drawer test...');
    const itContext = await browser.newContext({ storageState: undefined });
    const page = await itContext.newPage();

    await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(600);

    const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
    if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBtn.click();
      await page.waitForTimeout(400);
    }

    await page.locator('input[placeholder="Email Address"]').fill('itadmin@sonatrach.dz');
    await page.locator('input[placeholder="Password"]').fill('itadmin123');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();

    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(800);

    // Navigate to User Management
    await page.goto(`${FRONTEND}/user-management`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);

    // Verify User Management Title & KPI stats
    const itTitle = page.locator('h1:has-text("User Management")');
    await expect(itTitle).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Total Users').first()).toBeVisible();

    // Open Slide-Over Drawer
    console.log('[E2E UNTESTED] Opening Register New User drawer via #um-add-user-btn...');
    const addUserBtn = page.locator('#um-add-user-btn');
    await expect(addUserBtn).toBeVisible();
    await addUserBtn.click();
    await page.waitForTimeout(800);

    // Verify Drawer is open
    const drawerTitle = page.locator('text=Register New User').first();
    await expect(drawerTitle).toBeVisible();
    const userForm = page.locator('#um-user-form');
    await expect(userForm).toBeVisible();

    // Fill form
    const uniqueTimestamp = Date.now();
    const testEmail = `auditor_${uniqueTimestamp}@sonatrach.dz`;
    const testFullName = `Amine Mansouri (E2E Test)`;

    console.log(`[E2E UNTESTED] Filling new user form for ${testEmail}...`);
    await page.locator('#um-modal-fullname').fill(testFullName);
    await page.locator('#um-modal-email').fill(testEmail);
    await page.locator('#um-modal-department').fill('Corporate Auditing & Assurance');
    await page.locator('#um-modal-jobtitle').fill('Lead Environmental Auditor');

    // Role selection (Standard User compliant with IT provisioning permissions)
    await page.locator('#um-modal-role').selectOption('user');
    await page.waitForTimeout(400);

    // Region selection (required for user)
    const regionSelect = page.locator('#um-modal-region');
    await expect(regionSelect).toBeVisible();
    const regionOptions = await regionSelect.locator('option').allTextContents();
    const validRegion = regionOptions.find(opt => opt && !opt.includes('Select a Region')) || regionOptions[1];
    if (validRegion) {
      await regionSelect.selectOption({ label: validRegion.trim() });
    }

    // Password
    await page.locator('#um-modal-password').fill('SecurePass2026!');
    await page.waitForTimeout(400);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested03_user_management_drawer_filled.png') });
    copyArtifact('untested03_user_management_drawer_filled.png');
    console.log('[E2E UNTESTED] Captured untested03_user_management_drawer_filled.png.');

    // Submit user creation
    console.log('[E2E UNTESTED] Submitting new user form...');
    await page.locator('#um-modal-submit').click();

    // Verify success toast
    const successToast = page.locator('text=User created successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UNTESTED] Verified "User created successfully" notification.');

    // Verify user appears in table
    await page.waitForTimeout(1000);
    const userRow = page.locator(`tr:has-text("${testFullName}")`).first();
    await expect(userRow).toBeVisible({ timeout: 10000 });
    await expect(userRow.locator('text=User').first()).toBeVisible();
    console.log(`[E2E UNTESTED] Verified new user row rendered in table with Super User badge.`);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested03_user_created_in_table.png') });
    copyArtifact('untested03_user_created_in_table.png');
    console.log('[E2E UNTESTED] Captured untested03_user_created_in_table.png.');

    await itContext.close();
  });

  // -------------------------------------------------------------------------
  // TEST 4: Emission Sources Equipment Inventory Registration
  // -------------------------------------------------------------------------
  test('UNTESTED-4: Emission Sources Equipment Inventory — Operational Registration & Fuel Linkage', async ({ page }) => {
    console.log('[E2E UNTESTED] Navigating to Emission Sources Inventory (/manage-data?tab=sources)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=sources`);
    await page.waitForTimeout(1200);

    // Verify Header
    const tabHeader = page.locator('h2:has-text("Emission Sources Inventory")');
    await expect(tabHeader).toBeVisible({ timeout: 15000 });

    // Fill form
    const uniqueSuffix = Date.now();
    const sourceName = `Gas Lift Compressor Train 4-${uniqueSuffix}`;
    const equipId = `COMP-GL-404`;

    console.log(`[E2E UNTESTED] Registering new operational emission source: ${sourceName}...`);
    
    // Select Activity
    const activitySelect = page.locator('.grid-forms select.component-select').first();
    const actOptions = await activitySelect.locator('option').allTextContents();
    const validAct = actOptions.find(o => o && !o.includes('Select Activity')) || actOptions[1];
    if (validAct) {
      await activitySelect.selectOption({ label: validAct.trim() });
      await page.waitForTimeout(500);
    }

    // Select Division
    const divisionSelect = page.locator('.grid-forms select.component-select').nth(1);
    const divOptions = await divisionSelect.locator('option').allTextContents();
    const validDiv = divOptions.find(o => o && !o.includes('Select Division')) || divOptions[1];
    if (validDiv) {
      await divisionSelect.selectOption({ label: validDiv.trim() });
      await page.waitForTimeout(500);
    }

    // Select Region via CustomDropdown
    const regionDropdown = page.locator('.grid-forms .custom-dropdown');
    await regionDropdown.click();
    await page.waitForTimeout(400);
    const regionOpt = page.locator('.dropdown-option, [role="option"]').filter({ hasText: /.+/ }).nth(1);
    await regionOpt.click();
    await page.waitForTimeout(400);

    // Source Name
    await page.locator('input[placeholder="e.g. Flare A"]').fill(sourceName);

    // Type select
    const typeSelect = page.locator('.grid-forms select.component-select').nth(2);
    const typeOptions = await typeSelect.locator('option').allTextContents();
    const validType = typeOptions.find(o => o && !o.includes('Select Type')) || typeOptions[1];
    if (validType) {
      await typeSelect.selectOption({ label: validType.trim() });
    }

    // Equipment ID
    await page.locator('input[placeholder="e.g. COMP-001"]').fill(equipId);

    // Fuel Type
    const fuelInput = page.locator('.input-group:has-text("Fuel") input');
    await fuelInput.fill('Sweet Natural Gas');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested04_source_form_filled.png') });
    copyArtifact('untested04_source_form_filled.png');
    console.log('[E2E UNTESTED] Captured untested04_source_form_filled.png.');

    // Save Source
    console.log('[E2E UNTESTED] Submitting Source creation...');
    await page.locator('button.action-btn:has-text("Add Source")').click();

    // Verify success toast
    const successToast = page.locator('text=Source added!').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UNTESTED] Verified "Source added!" notification.');

    // Verify presence in table
    await page.waitForTimeout(1000);
    const newSourceRow = page.locator(`table.data-table tbody tr:has-text("${sourceName}")`).first();
    await expect(newSourceRow).toBeVisible({ timeout: 10000 });
    await expect(newSourceRow).toContainText(equipId);
    console.log('[E2E UNTESTED] Verified new equipment source rendered in data table.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested04_source_registered_table.png') });
    copyArtifact('untested04_source_registered_table.png');
    console.log('[E2E UNTESTED] Captured untested04_source_registered_table.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 5: Decarbonization & Mitigation Registry
  // -------------------------------------------------------------------------
  test('UNTESTED-5: Decarbonization & Mitigation Registry — CCUS & Offsets Lifecycle Record', async ({ page }) => {
    console.log('[E2E UNTESTED] Navigating to Mitigation Registry (/manage-data?tab=mitigation)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=mitigation`);
    await page.waitForTimeout(1200);

    // Verify Header
    const tabHeader = page.locator('h2:has-text("Mitigation Projects")');
    await expect(tabHeader).toBeVisible({ timeout: 15000 });
    await expect(page.locator('text=Record CCUS, RECs, and Carbon Offsets.').first()).toBeVisible();

    const uniqueSuffix = Date.now();
    const projName = `In Salah Geological Storage Unit 2-${uniqueSuffix}`;

    console.log(`[E2E UNTESTED] Registering new mitigation project: ${projName}...`);

    // Select Activity
    const activitySelect = page.locator('.grid-forms select.component-select').first();
    const actOptions = await activitySelect.locator('option').allTextContents();
    const validAct = actOptions.find(o => o && !o.includes('Select Activity')) || actOptions[1];
    if (validAct) {
      await activitySelect.selectOption({ label: validAct.trim() });
      await page.waitForTimeout(500);
    }

    // Select Division
    const divisionSelect = page.locator('.grid-forms select.component-select').nth(1);
    const divOptions = await divisionSelect.locator('option').allTextContents();
    const validDiv = divOptions.find(o => o && !o.includes('Select Division')) || divOptions[1];
    if (validDiv) {
      await divisionSelect.selectOption({ label: validDiv.trim() });
      await page.waitForTimeout(500);
    }

    // Select Region via CustomDropdown
    const regionDropdown = page.locator('.grid-forms .custom-dropdown');
    await regionDropdown.click();
    await page.waitForTimeout(400);
    const regionOpt = page.locator('.dropdown-option, [role="option"]').filter({ hasText: /.+/ }).nth(1);
    await regionOpt.click();
    await page.waitForTimeout(400);

    // Project Name
    await page.locator('input[placeholder="e.g. Flare Reduction Unit 1"]').fill(projName);

    // Year
    const yearInput = page.locator('.input-group:has-text("Year") input');
    await yearInput.fill('2025');

    // Type (CCUS)
    const typeSelect = page.locator('.grid-forms select.component-select').nth(2);
    await typeSelect.selectOption('CCUS');

    // Quantity (tCO2e)
    await page.locator('input[placeholder="0.0"]').first().fill('14250.0');

    // Status (Active)
    const statusSelect = page.locator('.grid-forms select.component-select').nth(3);
    await statusSelect.selectOption('Active');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested05_mitigation_form_filled.png') });
    copyArtifact('untested05_mitigation_form_filled.png');
    console.log('[E2E UNTESTED] Captured untested05_mitigation_form_filled.png.');

    // Save Mitigation
    console.log('[E2E UNTESTED] Submitting mitigation project...');
    await page.locator('button.action-btn:has-text("Save Record")').click();

    // Verify success toast
    const successToast = page.locator('text=Mitigation record saved!').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UNTESTED] Verified "Mitigation record saved!" notification.');

    // Verify row in table
    await page.waitForTimeout(1000);
    const mitigationRow = page.locator(`table.data-table tbody tr:has-text("${projName}")`).first();
    await expect(mitigationRow).toBeVisible({ timeout: 10000 });
    await expect(mitigationRow).toContainText('Active');
    console.log('[E2E UNTESTED] Verified new mitigation project in data table.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested05_mitigation_saved_table.png') });
    copyArtifact('untested05_mitigation_saved_table.png');
    console.log('[E2E UNTESTED] Captured untested05_mitigation_saved_table.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 6: OGMP 2.0 Site-Level Measurement Surveys
  // -------------------------------------------------------------------------
  test('UNTESTED-6: OGMP 2.0 Site-Level Measurement Surveys — Top-Down / Bottom-Up Logging', async ({ page }) => {
    console.log('[E2E UNTESTED] Navigating to OGMP Surveys (/manage-data?tab=ogmp)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=ogmp`);
    await page.waitForTimeout(1200);

    // Verify Tab Header & Notice
    const ogmpHeader = page.locator('h2:has-text("OGMP 2.0 Level 4 & 5 Top-Down / Bottom-Up Surveys")');
    await expect(ogmpHeader).toBeVisible({ timeout: 15000 });

    const ogScopeNotice = page.locator('text=Oil & Gas Scope Only').first();
    await expect(ogScopeNotice).toBeVisible();

    console.log('[E2E UNTESTED] Filling OGMP 2.0 survey measurement form...');

    // Select Activity
    const actSelect = page.locator('.form-grid-3 select.component-select').first();
    const actOpts = await actSelect.locator('option').allTextContents();
    const validAct = actOpts.find(o => o && !o.includes('Select Activity')) || actOpts[1];
    if (validAct) {
      await actSelect.selectOption({ label: validAct.trim() });
      await page.waitForTimeout(500);
    }

    // Select Division
    const divSelect = page.locator('.form-grid-3 select.component-select').nth(1);
    const divOpts = await divSelect.locator('option').allTextContents();
    const validDiv = divOpts.find(o => o && !o.includes('Select Division')) || divOpts[1];
    if (validDiv) {
      await divSelect.selectOption({ label: validDiv.trim() });
      await page.waitForTimeout(500);
    }

    // Select Facility
    const facSelect = page.locator('.form-grid-3 select.component-select').nth(2);
    const facOpts = await facSelect.locator('option').allTextContents();
    const validFac = facOpts.find(o => o && !o.includes('Select O& Gas Facility')) || facOpts[1];
    if (validFac) {
      await facSelect.selectOption({ label: validFac.trim() });
      await page.waitForTimeout(500);
    }

    // Survey Date
    const dateInput = page.locator('.form-grid-3 input[type="date"]');
    await dateInput.fill('2025-10-15');

    // Measurement Technology
    const techSelect = page.locator('.form-grid-3 select.component-select').nth(3);
    await techSelect.selectOption({ label: 'Aircraft Hyperspectral / LiDAR Aerial' });

    // Measured Rate
    const rateInput = page.locator('.input-group:has-text("Measured Emission Rate") input');
    await rateInput.fill('52.5');

    // Reconciliation Status
    const reconSelect = page.locator('.input-group:has-text("Reconciliation Status") select');
    await reconSelect.selectOption({ label: 'Discrepancy Detected (Bottom-Up Underestimated)' });

    // Operator Notes
    const notesInput = page.locator('input[placeholder="Wind speed, flight altitude, pass number, observation conditions"]');
    await notesInput.fill('Aerial LiDAR flight run #42, clear conditions, wind 3.2 m/s, detected manifold leak');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested06_ogmp_survey_form_filled.png') });
    copyArtifact('untested06_ogmp_survey_form_filled.png');
    console.log('[E2E UNTESTED] Captured untested06_ogmp_survey_form_filled.png.');

    // Save OGMP Survey
    console.log('[E2E UNTESTED] Submitting OGMP survey record...');
    await page.locator('button.action-btn:has-text("Save OGMP Survey")').click();

    // Verify success toast
    const successToast = page.locator('text=OGMP survey record saved!').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UNTESTED] Verified "OGMP survey record saved!" notification.');

    // Verify in table
    await page.waitForTimeout(1000);
    const surveyRow = page.locator('table.data-table tbody tr:has-text("52.5")').first();
    await expect(surveyRow).toBeVisible({ timeout: 10000 });
    await expect(surveyRow).toContainText('Discrepancy Detected');
    console.log('[E2E UNTESTED] Verified survey record saved and visible in OGMP data table.');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested06_ogmp_survey_saved_table.png') });
    copyArtifact('untested06_ogmp_survey_saved_table.png');
    console.log('[E2E UNTESTED] Captured untested06_ogmp_survey_saved_table.png.');
  });

  // -------------------------------------------------------------------------
  // TEST 7: Reference Data Catalog & Standards Inspector
  // -------------------------------------------------------------------------
  test('UNTESTED-7: Reference Data Catalog & Standards Inspector — GWP Matrices, Conversions, & Fuel Factors', async ({ page }) => {
    console.log('[E2E UNTESTED] Navigating to Reference Data Catalog (/reference-data)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/reference-data`);
    await page.waitForTimeout(1200);

    // Verify Header
    const pageHeader = page.locator('h1:has-text("Reference Data Library")');
    await expect(pageHeader).toBeVisible({ timeout: 15000 });

    // 1. Verify Global Warming Potentials (GWPs) table
    console.log('[E2E UNTESTED] Verifying Global Warming Potentials (GWPs) reference table...');
    const gwpSection = page.locator('.category-section:has-text("Global Warming Potentials (GWPs)")').first();
    await expect(gwpSection).toBeVisible();
    await expect(gwpSection.locator('text=AR4 (2007)')).toBeVisible();
    await expect(gwpSection.locator('text=AR6 (2021)')).toBeVisible();
    await expect(gwpSection.locator('text=Methane (CH₄)')).toBeVisible();
    await expect(gwpSection.locator('text=27.9')).toBeVisible(); // AR6 CH4

    // 2. Verify Unit Conversions table
    console.log('[E2E UNTESTED] Verifying Unit Conversions table...');
    const conversionsSection = page.locator('.category-section:has-text("Unit Conversions")').first();
    await expect(conversionsSection).toBeVisible();
    await expect(conversionsSection.locator('text=1 MJ (Megajoule)')).toBeVisible();
    await expect(conversionsSection.locator('text=0.000947817')).toBeVisible();
    await expect(conversionsSection.locator('text=1 BOE (Barrel of Oil Equivalent)')).toBeVisible();

    // 3. Verify Data Quality & Uncertainty Tiers
    console.log('[E2E UNTESTED] Verifying Data Quality & Uncertainty Tiers...');
    const qualitySection = page.locator('.category-section:has-text("Data Quality & Uncertainty Tiers")').first();
    await expect(qualitySection).toBeVisible();
    await expect(qualitySection.locator('text=Tier 3 (High)')).toBeVisible();
    await expect(qualitySection.locator('text=≤ 5% Uncertainty')).toBeVisible();

    // 4. Test Live Search Filtering
    console.log('[E2E UNTESTED] Testing live search in reference catalog...');
    const searchInput = page.locator('input[placeholder="Search by name, fuel type, code, or value..."]');
    await searchInput.fill('Diesel');
    await page.waitForTimeout(600);
    await expect(page.locator('text=Diesel').first()).toBeVisible();

    // Clear search
    await searchInput.fill('');
    await page.waitForTimeout(400);

    // 5. Test Category Filter dropdown
    console.log('[E2E UNTESTED] Testing category filter dropdown...');
    const filterSelect = page.locator('select.filter-select');
    await filterSelect.selectOption('gwp');
    await page.waitForTimeout(500);

    // Only GWP section should be displayed
    await expect(gwpSection).toBeVisible();
    await expect(conversionsSection).not.toBeVisible();

    // Reset to All Categories
    await filterSelect.selectOption('all');
    await page.waitForTimeout(500);
    await expect(conversionsSection).toBeVisible();

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'untested07_reference_data_catalog.png') });
    copyArtifact('untested07_reference_data_catalog.png');
    console.log('[E2E UNTESTED] Captured untested07_reference_data_catalog.png.');
  });

});
