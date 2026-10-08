// @ts-check
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
const BACKEND = 'http://127.0.0.1:5000';
const SCREENSHOT_DIR = path.resolve('e2e/deep_user_audit/screenshots');
const ARTIFACT_DIR = 'C:/Users/samsung/.gemini/antigravity/brain/145e1f58-77e7-4f5b-8573-5a1c4dc13171';

function copyArtifact(filename) {
  try {
    const src = path.join(SCREENSHOT_DIR, filename);
    const dest = path.join(ARTIFACT_DIR, filename);
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dest);
    }
  } catch (err) {
    console.error(`Failed to copy artifact ${filename}:`, err.message);
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
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1000);
  }

  await expect(page.locator('.app-container, .main-content, #main').first()).toBeVisible({ timeout: 20000 });
  await page.waitForLoadState('networkidle').catch(() => {});
}

async function selectScope1Region(page) {
  const regionDropdown = page.locator('.input-group:has-text("Region") button.dropdown-selected, button:has-text("Select Region")').first();
  if (await regionDropdown.isVisible({ timeout: 4000 }).catch(() => false)) {
    const text = await regionDropdown.textContent().catch(() => '');
    if (!text || text.includes('Select')) {
      await regionDropdown.click();
      await page.waitForTimeout(400);
      const option = page.locator('.dropdown-option:not(:has-text("Select")), [role="option"]:not(:has-text("Select"))').first();
      if (await option.isVisible({ timeout: 3000 }).catch(() => false)) {
        await option.click();
        await page.waitForTimeout(400);
      }
    }
  }
}

test.describe.serial('Suite 11: Specialized Engineering Systems, EU CBAM & Enterprise Administration', () => {

  test.beforeAll(async () => {
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  // -------------------------------------------------------------------------
  // TEST 1: Upstream Pneumatic Controller Venting Accounting
  // -------------------------------------------------------------------------
  test('ENG-1: Upstream Pneumatic Controller Venting Accounting (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E ENG] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);
    await selectScope1Region(page);

    // Verify Scope 1 form container
    const formHeading = page.locator('button:has-text("01 Scope 1"), .input-group:has-text("Process")').first();
    await expect(formHeading).toBeVisible({ timeout: 10000 });

    // Open Process dropdown and select Pneumatic Device
    console.log('[E2E ENG] Selecting "Pneumatic Device" process...');
    const processDropdown = page.locator('.input-group:has-text("Process") button.dropdown-selected').first();
    await expect(processDropdown).toBeVisible();
    await processDropdown.click();
    await page.waitForTimeout(400);

    const pneuOption = page.locator('.dropdown-portal .dropdown-option:has-text("Pneumatic Device"), [role="option"]:has-text("Pneumatic Device")').first();
    await expect(pneuOption).toBeVisible();
    await pneuOption.click();
    await page.waitForTimeout(600);

    // Switch method to Tier 3 / Measurement / GC
    console.log('[E2E ENG] Selecting Tier 3 Engineering / Measurement method for Pneumatic Device...');
    const pneuTier3 = page.locator('.methodology-toggle button:has-text("Measurement / GC"), .methodology-toggle button:has-text("Tier 3")').first();
    if (await pneuTier3.isVisible().catch(() => false)) {
      await pneuTier3.click();
      await page.waitForTimeout(400);
    }

    // Populate Pneumatics engineering inputs
    console.log('[E2E ENG] Entering pneumatic engineering parameters...');
    const countInput = page.locator('.pneumatics-form input[placeholder="Count"], input[placeholder="Count"]').first();
    await expect(countInput).toBeVisible({ timeout: 8000 });
    await countInput.fill('16');

    const bleedInput = page.locator('.pneumatics-form input[placeholder="e.g. 15.4"]').first();
    if (await bleedInput.isVisible().catch(() => false)) {
      await bleedInput.fill('18.5');
    }

    const ch4Input = page.locator('.pneumatics-form input[placeholder="e.g. 85"]').first();
    if (await ch4Input.isVisible().catch(() => false)) {
      await ch4Input.fill('88');
    }

    const hoursInput = page.locator('.pneumatics-form input[placeholder="whole month if blank"]').first();
    if (await hoursInput.isVisible().catch(() => false)) {
      await hoursInput.fill('8760');
    }
    await page.waitForTimeout(300);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'eng01_pneumatic_devices_logged.png') });
    copyArtifact('eng01_pneumatic_devices_logged.png');
    console.log('[E2E ENG] Captured eng01_pneumatic_devices_logged.png.');

    // Submit form
    console.log('[E2E ENG] Submitting Pneumatic Scope 1 record...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit")').first();
    await submitBtn.click();

    // Verify confirmation toast
    const successToast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed "Scope 1 entry added successfully" notification toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 2: Crude Oil Storage Tank Flashing & Breathing Losses
  // -------------------------------------------------------------------------
  test('ENG-2: Crude Oil Storage Tank Flashing & Breathing Losses (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E ENG] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);
    await selectScope1Region(page);

    // Switch process to Storage Tank - Flashing/Events
    console.log('[E2E ENG] Selecting "Storage Tank - Flashing/Events" process...');
    const processDropdown = page.locator('.input-group:has-text("Process") button.dropdown-selected').first();
    await processDropdown.click();
    await page.waitForTimeout(400);

    const tankOption = page.locator('.dropdown-portal .dropdown-option:has-text("Storage Tank - Flashing/Events"), [role="option"]:has-text("Storage Tank - Flashing/Events")').first();
    await expect(tankOption).toBeVisible();
    await tankOption.click();
    await page.waitForTimeout(600);

    // Switch method to Tier 3 / Engineering
    console.log('[E2E ENG] Switching to Tier 3 Measured/Engineered method...');
    const tier3Btn = page.locator('.methodology-toggle button:has-text("Measured / Engineered"), .methodology-toggle button:has-text("Tier 3")').first();
    if (await tier3Btn.isVisible().catch(() => false)) {
      await tier3Btn.click();
      await page.waitForTimeout(400);
    }

    // Populate Tank throughput, GOR, CH4%
    const throughputInput = page.locator('input[placeholder="Enter throughput"]').first();
    await expect(throughputInput).toBeVisible();
    await throughputInput.fill('35000');

    const gorInput = page.locator('input[placeholder="e.g. 500"]').first();
    if (await gorInput.isVisible().catch(() => false)) {
      await gorInput.fill('480');
    }

    const ch4Input = page.locator('.tank-form input[placeholder="e.g. 85"]').first();
    if (await ch4Input.isVisible().catch(() => false)) {
      await ch4Input.fill('82');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'eng02_tank_flashing_loss_logged.png') });
    copyArtifact('eng02_tank_flashing_loss_logged.png');
    console.log('[E2E ENG] Captured eng02_tank_flashing_loss_logged.png.');

    // Submit form
    console.log('[E2E ENG] Submitting Tank Flashing calculation...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit")').first();
    await submitBtn.click();

    // Verify toast
    const successToast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed Tank Flashing submission toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 3: Glycol Dehydration Unit Gas Dehydration Accounting
  // -------------------------------------------------------------------------
  test('ENG-3: Glycol Dehydration Unit Gas Dehydration Accounting (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E ENG] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);
    await selectScope1Region(page);

    // Switch process to Dehydrator
    console.log('[E2E ENG] Selecting "Dehydrator" process...');
    const processDropdown = page.locator('.input-group:has-text("Process") button.dropdown-selected').first();
    await processDropdown.click();
    await page.waitForTimeout(400);

    const dehyOption = page.locator('.dropdown-portal .dropdown-option:has-text("Dehydrator"), [role="option"]:has-text("Dehydrator")').first();
    await expect(dehyOption).toBeVisible();
    await dehyOption.click();
    await page.waitForTimeout(600);

    // Switch method to Tier 3
    console.log('[E2E ENG] Selecting Tier 3 Simulation / Measured method...');
    const dehyTier3 = page.locator('.methodology-toggle button:has-text("Simulation / Measured"), .methodology-toggle button:has-text("Tier 3")').first();
    if (await dehyTier3.isVisible().catch(() => false)) {
      await dehyTier3.click();
      await page.waitForTimeout(400);
    }

    // Populate Measured Vent Volume parameters (API Compendium 2021 §6.3.8.1 standard)
    const gasVolInput = page.locator('.input-group:has-text("Gas volume") input[type="number"], input[placeholder="Gas volume"]').first();
    await expect(gasVolInput).toBeVisible({ timeout: 5000 });
    await gasVolInput.fill('150000');

    const ch4Input = page.locator('input[placeholder="e.g. 70"], .input-group:has-text("CH₄") input[type="number"]').first();
    if (await ch4Input.isVisible().catch(() => false)) {
      await ch4Input.fill('88.5');
    }

    const co2Input = page.locator('input[placeholder="e.g. 9"], .input-group:has-text("CO₂") input[type="number"]').first();
    if (await co2Input.isVisible().catch(() => false)) {
      await co2Input.fill('1.8');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'eng03_dehydrator_unit_logged.png') });
    copyArtifact('eng03_dehydrator_unit_logged.png');
    console.log('[E2E ENG] Captured eng03_dehydrator_unit_logged.png.');

    // Submit form
    console.log('[E2E ENG] Submitting Dehydrator Scope 1 record...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit")').first();
    await submitBtn.click();

    // Verify toast
    const successToast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed Dehydrator submission toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 4: Acid Gas Removal (AGR Amine Unit) CO2 Venting Stoichiometry
  // -------------------------------------------------------------------------
  test('ENG-4: Acid Gas Removal (AGR Amine Unit) CO2 Venting Stoichiometry (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E ENG] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);
    await selectScope1Region(page);

    // Switch process to Acid Gas Removal (AGR)
    console.log('[E2E ENG] Selecting "Acid Gas Removal (AGR)" process...');
    const processDropdown = page.locator('.input-group:has-text("Process") button.dropdown-selected').first();
    await processDropdown.click();
    await page.waitForTimeout(400);

    const agrOption = page.locator('.dropdown-portal .dropdown-option:has-text("Acid Gas Removal (AGR)"), [role="option"]:has-text("Acid Gas Removal (AGR)")').first();
    await expect(agrOption).toBeVisible();
    await agrOption.click();
    await page.waitForTimeout(600);

    // Switch method to Tier 3 Engineering
    console.log('[E2E ENG] Selecting Tier 3 Engineering method for AGR...');
    const agrTier3 = page.locator('.methodology-toggle button:has-text("Engineering"), .methodology-toggle button:has-text("Tier 3")').first();
    if (await agrTier3.isVisible().catch(() => false)) {
      await agrTier3.click();
      await page.waitForTimeout(400);
    }

    // Populate AGR parameters: throughput, inlet CO2, outlet CO2
    const agrThroughput = page.locator('.agr-form input[placeholder="Volume"]').first();
    if (await agrThroughput.isVisible().catch(() => false)) {
      await agrThroughput.fill('380');
    }

    const agrCo2In = page.locator('.agr-form input[placeholder="e.g. 5.0"]').first();
    if (await agrCo2In.isVisible().catch(() => false)) {
      await agrCo2In.fill('4.2');
    }

    const agrCo2Out = page.locator('.agr-form input[placeholder="e.g. 0.05"]').first();
    if (await agrCo2Out.isVisible().catch(() => false)) {
      await agrCo2Out.fill('0.3');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'eng04_agr_amine_logged.png') });
    copyArtifact('eng04_agr_amine_logged.png');
    console.log('[E2E ENG] Captured eng04_agr_amine_logged.png.');

    // Submit form
    console.log('[E2E ENG] Submitting AGR Amine Unit calculation...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit")').first();
    await submitBtn.click();

    // Verify toast
    const successToast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(successToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed AGR Amine Unit submission toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 5: EU CBAM Product Export & Embedded Carbon Intensity Registration
  // -------------------------------------------------------------------------
  test('ENG-5: EU CBAM Product Export & Embedded Carbon Intensity Registration (/manage-data?tab=cbam)', async ({ page }) => {
    console.log('[E2E ENG] Navigating to CBAM Products Tab (/manage-data?tab=cbam)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=cbam`);
    await page.waitForTimeout(1500);

    // Verify CBAM Header
    const cbamHeader = page.locator('text=EU CBAM Export & Embedded Emission Tracking').first();
    await expect(cbamHeader).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed EU CBAM Regulation (EU) 2023/956 heading.');

    // Select Activity
    const actSelect = page.locator('.form-grid-3 select').first();
    if (await actSelect.isVisible().catch(() => false)) {
      const actOpts = await actSelect.locator('option').all();
      if (actOpts.length > 1) {
        const actVal = await actOpts[1].getAttribute('value');
        if (actVal) await actSelect.selectOption(actVal);
      }
      await page.waitForTimeout(300);
    }

    // Select Division
    const divSelect = page.locator('.form-grid-3 select').nth(1);
    if (await divSelect.isEnabled().catch(() => false)) {
      const divOpts = await divSelect.locator('option').all();
      if (divOpts.length > 1) {
        const divVal = await divOpts[1].getAttribute('value');
        if (divVal) await divSelect.selectOption(divVal);
      }
      await page.waitForTimeout(300);
    }

    // Select Facility
    const facSelect = page.locator('.form-grid-3 select').nth(2);
    if (await facSelect.isVisible().catch(() => false)) {
      const options = await facSelect.locator('option').all();
      if (options.length > 1) {
        const val = await options[1].getAttribute('value');
        if (val) await facSelect.selectOption(val);
      }
      await page.waitForTimeout(300);
    }

    // Populate Product Name
    const productNameInput = page.locator('input[placeholder="e.g. Export Blend Crude Oil"]').first();
    await expect(productNameInput).toBeVisible();
    await productNameInput.fill('Saharan Blend Export Crude Oil');

    // Populate Export Quantity (Metric Tonnes)
    const quantityInput = page.locator('input[placeholder="0.00"]').first();
    await expect(quantityInput).toBeVisible();
    await quantityInput.fill('50000');

    // Populate Direct Specific Embedded (tCO2e / t)
    const directInput = page.locator('input[placeholder="0.000"]').first();
    if (await directInput.isVisible().catch(() => false)) {
      await directInput.fill('0.042');
    }

    // Populate Indirect Specific Embedded (tCO2e / t)
    const indirectInput = page.locator('input[placeholder="0.000"]').nth(1);
    if (await indirectInput.isVisible().catch(() => false)) {
      await indirectInput.fill('0.006');
    }

    // Populate Notes
    const notesInput = page.locator('input[placeholder="Accredited Verifier / Certificate ID"]').first();
    if (await notesInput.isVisible().catch(() => false)) {
      await notesInput.fill('Accredited verification under EU Regulation (EU) 2023/956');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'eng05_cbam_export_registered.png') });
    copyArtifact('eng05_cbam_export_registered.png');
    console.log('[E2E ENG] Captured eng05_cbam_export_registered.png.');

    // Submit Save CBAM Record
    console.log('[E2E ENG] Submitting Save CBAM Record...');
    const saveCbamBtn = page.locator('button.action-btn:has-text("Save CBAM Record")').first();
    await saveCbamBtn.click();

    // Verify toast
    const cbamToast = page.locator('text=CBAM export record saved!').first();
    await expect(cbamToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed "CBAM export record saved!" notification toast.');

    // Verify row appears in CBAM table
    const tableEntry = page.locator('text=Saharan Blend Export Crude Oil').first();
    await expect(tableEntry).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Verified Saharan Blend export entry rendered in CBAM records table.');
  });

  // -------------------------------------------------------------------------
  // TEST 6: Audit Trail Interactive Timeline Switcher & Event Payload Inspector
  // -------------------------------------------------------------------------
  test('ENG-6: Audit Trail Interactive Timeline Switcher & Event Payload Inspector (/audit-trail)', async ({ page }) => {
    console.log('[E2E ENG] Navigating to Audit Trail (/audit-trail)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/audit-trail`);
    await page.waitForTimeout(1500);

    // Verify Audit Header
    const auditHeader = page.locator('text=Audit Trail & System Activity').first();
    await expect(auditHeader).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Audit Trail & System Activity page confirmed.');

    // Switch to Timeline View via SegmentedControl
    console.log('[E2E ENG] Switching from Table View to Timeline View...');
    const timelineBtn = page.locator('[role="radio"]:has-text("Timeline"), label:has-text("Timeline"), button:has-text("Timeline")').first();
    await expect(timelineBtn).toBeVisible();
    await timelineBtn.click();
    await page.waitForTimeout(800);

    // Verify timeline view active
    const timelineContainer = page.locator('ol').first();
    await expect(timelineContainer).toBeVisible({ timeout: 8000 });
    console.log('[E2E ENG] Chronological event timeline feed successfully rendered.');

    // Expand Raw JSON on the first timeline card
    const rawJsonBtn = page.locator('ol li button:has-text("Raw JSON")').first();
    if (await rawJsonBtn.isVisible().catch(() => false)) {
      await rawJsonBtn.click();
      await page.waitForTimeout(400);
      console.log('[E2E ENG] Expanded raw JSON data block inside timeline card.');
    }

    // Switch back to Table View
    console.log('[E2E ENG] Switching back to Table View...');
    const tableBtn = page.locator('[role="radio"]:has-text("Table"), label:has-text("Table"), button:has-text("Table")').first();
    await tableBtn.click();
    await page.waitForTimeout(800);

    // Filter by Action: CREATE
    console.log('[E2E ENG] Filtering Audit Trail by Action "CREATE"...');
    const actionSelect = page.locator('select:has(option:has-text("All Actions"))').first();
    if (await actionSelect.isVisible().catch(() => false)) {
      await actionSelect.selectOption('CREATE');
      await page.waitForTimeout(800);
      console.log('[E2E ENG] Applied filter: Action = CREATE.');
    }

    // Inspect Details on first row
    console.log('[E2E ENG] Clicking "Details" button to inspect raw audit event payload...');
    const detailsBtn = page.locator('button:has-text("Details")').first();
    if (await detailsBtn.isVisible().catch(() => false)) {
      await detailsBtn.click();
      await page.waitForTimeout(600);

      // Verify Audit Event Dialog
      const dialogTitle = page.locator('text=Audit event').first();
      await expect(dialogTitle).toBeVisible();

      const preJson = page.locator('pre').first();
      await expect(preJson).toBeVisible();
      console.log('[E2E ENG] Audit event JSON details inspector verified.');

      await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'eng06_audit_trail_timeline_inspector.png') });
      copyArtifact('eng06_audit_trail_timeline_inspector.png');
      console.log('[E2E ENG] Captured eng06_audit_trail_timeline_inspector.png.');

      // Close Dialog with Escape
      await page.keyboard.press('Escape');
      await page.waitForTimeout(400);
    }
  });

  // -------------------------------------------------------------------------
  // TEST 7: IT Administration User Provisioning & Password Security Lifecycle
  // -------------------------------------------------------------------------
  test('ENG-7: IT Administration User Provisioning & Password Security Lifecycle (/user-management)', async ({ browser }) => {
    console.log('[E2E ENG] Opening isolated IT Admin browser context...');
    const itContext = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await itContext.newPage();

    // Authenticate specifically as IT Admin
    console.log('[E2E ENG] Authenticating as IT Administrator (itadmin@sonatrach.dz)...');
    await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);

    const emailInput = page.locator('input[placeholder="Email Address"]').first();
    await emailInput.fill('itadmin@sonatrach.dz');
    const pwdInput = page.locator('input[type="password"]').first();
    await pwdInput.fill('itadmin123');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000);

    // Navigate to User Management
    console.log('[E2E ENG] Navigating to User Management portal (/user-management)...');
    await page.goto(`${FRONTEND}/user-management`, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1500);

    // Verify Add User button is present
    const addUserBtn = page.locator('#um-add-user-btn');
    await expect(addUserBtn).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed IT Management interface access.');

    // Open User Provisioning Drawer
    await addUserBtn.click();
    await page.waitForTimeout(600);

    const drawerTitle = page.locator('text=Register New User').first();
    await expect(drawerTitle).toBeVisible();
    console.log('[E2E ENG] Provisioning drawer "Register New User" opened.');

    // Populate user credentials and organizational properties
    const timestamp = Date.now();
    const newUserEmail = `auditor_${timestamp}@sonatrach.dz`;

    await page.locator('#um-modal-fullname').fill('Farid Belhadj (Field Auditor)');
    await page.locator('#um-modal-email').fill(newUserEmail);
    await page.locator('#um-modal-department').fill('Field Operations');
    await page.locator('#um-modal-jobtitle').fill('Senior HSE Auditor');
    await page.locator('#um-modal-password').fill('SecurityPass2026!');
    await page.waitForTimeout(300);

    // Submit User Creation
    console.log('[E2E ENG] Submitting new user identity creation...');
    await page.locator('#um-modal-submit').click();

    // Verify creation toast
    const userToast = page.locator('text=User created successfully').first();
    await expect(userToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed "User created successfully" toast.');
    await page.waitForTimeout(1000);

    // Verify new user exists in the directory table and open Reset Password drawer
    console.log('[E2E ENG] Locating newly registered user and opening password reset drawer...');
    const userRow = page.locator(`tr:has-text("${newUserEmail}")`).first();
    await expect(userRow).toBeVisible({ timeout: 10000 });

    const resetPwdBtn = userRow.locator('button[id^="um-reset-pwd-btn-"]').first();
    await expect(resetPwdBtn).toBeVisible();
    await resetPwdBtn.click();
    await page.waitForTimeout(600);

    // Verify Reset Password Drawer
    const resetDrawerTitle = page.locator('text=Reset User Password').first();
    await expect(resetDrawerTitle).toBeVisible();

    // Fill new password and confirmation
    await page.locator('#um-reset-pwd-input').fill('NewPass2026Secure!');
    await page.locator('#um-reset-pwd-confirm').fill('NewPass2026Secure!');
    await page.waitForTimeout(300);

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'eng07_it_user_provisioning_and_reset.png') });
    copyArtifact('eng07_it_user_provisioning_and_reset.png');
    console.log('[E2E ENG] Captured eng07_it_user_provisioning_and_reset.png.');

    // Submit password reset
    console.log('[E2E ENG] Submitting administrative password reset...');
    await page.locator('#um-reset-pwd-submit').click();

    // Verify reset confirmation toast
    const resetToast = page.locator('text=has been reset successfully').first();
    await expect(resetToast).toBeVisible({ timeout: 10000 });
    console.log('[E2E ENG] Confirmed administrative password reset notification toast.');

    await itContext.close();
  });

});
