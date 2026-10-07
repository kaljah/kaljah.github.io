import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const FRONTEND = 'http://127.0.0.1:5173';
const SCREENSHOT_DIR = path.resolve('e2e/deep_user_audit/screenshots');
const BRAIN_DIR = 'C:\\Users\\samsung\\.gemini\\antigravity\\brain\\145e1f58-77e7-4f5b-8573-5a1c4dc13171';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function copyArtifact(filename) {
  try {
    const src = path.join(SCREENSHOT_DIR, filename);
    const dst = path.join(BRAIN_DIR, filename);
    if (fs.existsSync(src)) {
      fs.copyFileSync(src, dst);
    }
  } catch (err) {
    console.warn(`[WARN] Failed to copy artifact ${filename}:`, err);
  }
}

async function ensureAuthenticatedPage(page, targetUrl) {
  await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(800);

  const emailInput = page.locator('input[placeholder="Email Address"]').first();
  if (await emailInput.isVisible().catch(() => false)) {
    console.log('[E2E UP] Performing authentication login...');
    await emailInput.fill('a');
    const pwdInput = page.locator('input[type="password"]').first();
    await pwdInput.fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForTimeout(1000);
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000);
  }

  if (targetUrl) {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
  }
}

async function selectScope1Region(page) {
  const regBtn = page.locator('.input-group:has-text("Region") button.dropdown-selected, button:has-text("Select Region")').first();
  if (await regBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
    const txt = await regBtn.textContent().catch(() => '');
    if (!txt || txt.includes('Select')) {
      await regBtn.click();
      await page.waitForTimeout(400);
      const firstOpt = page.locator('.dropdown-option:not(:has-text("Select")), [role="option"]:not(:has-text("Select"))').first();
      if (await firstOpt.isVisible({ timeout: 3000 }).catch(() => false)) {
        await firstOpt.click();
        await page.waitForTimeout(400);
      }
    }
  }
}

async function selectScope1Process(page, processLabel) {
  const processGroup = page.locator('.input-group:has-text("Process")').first();
  const procDropdown = processGroup.locator('button.dropdown-selected').first();
  await procDropdown.click();
  await page.waitForTimeout(400);
  const opt = page.locator(`.dropdown-menu .dropdown-option:has-text("${processLabel}"), [role="option"]:has-text("${processLabel}")`).first();
  await expect(opt).toBeVisible({ timeout: 10000 });
  await opt.click();
  await page.waitForTimeout(800);
}

test.describe('Suite 13: Upstream Drilling, Well Completions, Mitigation Projects & Decarbonization Governance', () => {

  test.beforeEach(async () => {
    test.setTimeout(60000);
  });

  // -------------------------------------------------------------------------
  // TEST 1: Drilling Operations Wellbore Mud Degassing
  // -------------------------------------------------------------------------
  test('UP-1: Drilling Operations Wellbore Mud Degassing (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E UP] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Select Region
    await selectScope1Region(page);

    // Select Drilling Operations
    console.log('[E2E UP] Selecting "Drilling Operations" process...');
    await selectScope1Process(page, 'Drilling Operations');

    // Select emission factor from dropdown
    console.log('[E2E UP] Selecting Drilling emission factor...');
    const factorDropdown = page.locator('button.dropdown-selected:has-text("Select factor"), button:has-text("Select factor")').first();
    await expect(factorDropdown).toBeVisible({ timeout: 10000 });
    await factorDropdown.click();
    await page.waitForTimeout(500);

    const firstOpt = page.locator('.dropdown-portal .dropdown-option, .dropdown-portal [role="option"]').first();
    await expect(firstOpt).toBeVisible({ timeout: 10000 });
    await firstOpt.click();
    await page.waitForTimeout(500);

    // Populate Drilling Wells or Days
    const drillingInput = page.locator('.drilling-form input[type="number"], input[placeholder="Number of wells"]').first();
    await expect(drillingInput).toBeVisible({ timeout: 10000 });
    await drillingInput.fill('5');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'up01_drilling_operations_logged.png') });
    copyArtifact('up01_drilling_operations_logged.png');
    console.log('[E2E UP] Captured up01_drilling_operations_logged.png.');

    // Submit calculation
    console.log('[E2E UP] Submitting Drilling Operations entry...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify confirmation toast
    const toast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Drilling Operations entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 2: Well Completions & Workovers Flowback Venting
  // -------------------------------------------------------------------------
  test('UP-2: Well Completions & Workovers Flowback Venting (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E UP] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Select Region
    await selectScope1Region(page);

    // Select Well Completions & Workovers
    console.log('[E2E UP] Selecting "Well Completions & Workovers" process...');
    await selectScope1Process(page, 'Well Completions & Workovers');

    // Populate Completion Wells / Event Count
    const completionsInput = page.locator('.completions-form input[type="number"], .input-group:has-text("Wells") input, .input-group:has-text("Count") input, input[placeholder="e.g. 5"]').first();
    if (await completionsInput.isVisible({ timeout: 4000 }).catch(() => false)) {
      await completionsInput.fill('3');
    }

    // Populate CH4 content if present
    const ch4Input = page.locator('.completions-form .input-group:has-text("CH₄") input, input[placeholder="e.g. 85"]').first();
    if (await ch4Input.isVisible().catch(() => false)) {
      await ch4Input.fill('86.5');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'up02_well_completions_flowback_logged.png') });
    copyArtifact('up02_well_completions_flowback_logged.png');
    console.log('[E2E UP] Captured up02_well_completions_flowback_logged.png.');

    // Submit calculation
    console.log('[E2E UP] Submitting Well Completions record...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify toast
    const toast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Well Completions entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 3: Well Liquids Unloading Plunger Lift Venting Stoichiometry
  // -------------------------------------------------------------------------
  test('UP-3: Well Liquids Unloading Plunger Lift Venting Stoichiometry (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E UP] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Select Region
    await selectScope1Region(page);

    // Select Liquids Unloading
    console.log('[E2E UP] Selecting "Liquids Unloading" process...');
    await selectScope1Process(page, 'Liquids Unloading');

    // Switch to Tier 1 Per-Well Factor
    const tier1Btn = page.locator('button:has-text("Tier 1"), button:has-text("Per-Well")').first();
    if (await tier1Btn.isVisible().catch(() => false)) {
      await tier1Btn.click();
      await page.waitForTimeout(600);
    }

    // Populate Wells Count (target .unloading-form specifically)
    const unloadWells = page.locator('.unloading-form input[placeholder="e.g. 5"]').first();
    await expect(unloadWells).toBeVisible({ timeout: 10000 });
    await unloadWells.fill('6');

    // Populate CH4 content if present
    const ch4Input = page.locator('.unloading-form input[placeholder="e.g. 81.6"]').first();
    if (await ch4Input.isVisible().catch(() => false)) {
      await ch4Input.fill('82.5');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'up03_liquids_unloading_plunger_logged.png') });
    copyArtifact('up03_liquids_unloading_plunger_logged.png');
    console.log('[E2E UP] Captured up03_liquids_unloading_plunger_logged.png.');

    // Submit calculation
    console.log('[E2E UP] Submitting Liquids Unloading entry...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify toast
    const toast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Liquids Unloading entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 4: Compressor Depressurization & Blowdown Venting
  // -------------------------------------------------------------------------
  test('UP-4: Compressor Depressurization & Blowdown Venting (/emissions?scope=scope1)', async ({ page }) => {
    console.log('[E2E UP] Navigating to Scope 1 Emissions (/emissions?scope=scope1)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/emissions?scope=scope1`);
    await page.waitForTimeout(1500);

    // Select Region
    await selectScope1Region(page);

    // Select Venting (Blowdown)
    console.log('[E2E UP] Selecting "Venting (Blowdown)" process...');
    await selectScope1Process(page, 'Venting (Blowdown)');

    // Switch to Tier 3 Measurement to render Blowdown engineering model
    const tier3Btn = page.locator('button:has-text("Tier 3"), button:has-text("Measurement")').first();
    await expect(tier3Btn).toBeVisible({ timeout: 10000 });
    await tier3Btn.click();
    await page.waitForTimeout(600);

    // Populate Vessel Volume
    const volInput = page.locator('input[placeholder="Vessel Vol"]').first();
    await expect(volInput).toBeVisible({ timeout: 10000 });
    await volInput.fill('85');

    // Populate Pressure (psig)
    const pressInput = page.locator('input[placeholder="Before blowdown (psig)"]').first();
    await pressInput.fill('450');

    // Populate Number of Events
    const eventsInput = page.locator('input[placeholder="Count"]').first();
    await eventsInput.fill('2');

    // Populate CH4 (%)
    const ch4Input = page.locator('input[placeholder="e.g. 85"]').first();
    await ch4Input.fill('87.5');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'up04_compressor_blowdown_venting_logged.png') });
    copyArtifact('up04_compressor_blowdown_venting_logged.png');
    console.log('[E2E UP] Captured up04_compressor_blowdown_venting_logged.png.');

    // Submit calculation
    console.log('[E2E UP] Submitting Compressor Blowdown calculation...');
    const submitBtn = page.locator('button.btn-add-activity:has-text("Submit"), button:has-text("Submit")').first();
    await submitBtn.click();

    // Verify toast
    const toast = page.locator('text=Scope 1 entry added successfully').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Compressor Blowdown entry added successfully toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 5: Corporate Decarbonization Mitigation & Abatement Project Registration
  // -------------------------------------------------------------------------
  test('UP-5: Corporate Decarbonization Mitigation & Abatement Project Registration (/manage-data?tab=mitigation)', async ({ page }) => {
    console.log('[E2E UP] Navigating to Manage Data Mitigation (/manage-data?tab=mitigation)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=mitigation`);
    await page.waitForTimeout(1500);

    // Verify Mitigation Header
    const heading = page.locator('h2:has-text("Mitigation Projects")').first();
    await expect(heading).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Mitigation Projects heading.');

    // Select Activity if available
    const actSelect = page.locator('.input-group:has-text("Activity") select').first();
    if (await actSelect.isVisible().catch(() => false)) {
      const options = await actSelect.locator('option').all();
      if (options.length > 1) {
        await actSelect.selectOption({ index: 1 });
        await page.waitForTimeout(400);
      }
    }

    // Select Division if available
    const divSelect = page.locator('.input-group:has-text("Division") select').first();
    if (await divSelect.isVisible().catch(() => false)) {
      const options = await divSelect.locator('option').all();
      if (options.length > 1) {
        await divSelect.selectOption({ index: 1 });
        await page.waitForTimeout(400);
      }
    }

    // Select Region if available
    const regDropdown = page.locator('.input-group:has-text("Region") button.dropdown-selected').first();
    if (await regDropdown.isVisible().catch(() => false)) {
      await regDropdown.click();
      await page.waitForTimeout(400);
      const regOption = page.locator('.dropdown-menu .dropdown-option:not(:has-text("Select")), [role="option"]:not(:has-text("Select"))').first();
      if (await regOption.isVisible().catch(() => false)) {
        await regOption.click();
        await page.waitForTimeout(400);
      }
    }

    // Populate Project Name
    const projName = `Hassi Messaoud CCUS Phase ${Date.now().toString().slice(-4)}`;
    const nameInput = page.locator('input[placeholder="e.g. Flare Reduction Unit 1"]').first();
    await expect(nameInput).toBeVisible({ timeout: 10000 });
    await nameInput.fill(projName);

    // Populate Year
    const yearInput = page.locator('.input-group:has-text("Year") input').first();
    if (await yearInput.isVisible().catch(() => false)) {
      await yearInput.fill('2026');
    }

    // Select Type CCUS
    const typeSelect = page.locator('.input-group:has-text("Type") select').first();
    if (await typeSelect.isVisible().catch(() => false)) {
      await typeSelect.selectOption('CCUS');
    }

    // Populate Quantity (tCO2e)
    const qtyInput = page.locator('input[placeholder="0.0"]').first();
    await expect(qtyInput).toBeVisible();
    await qtyInput.fill('52000');

    // Populate Status
    const statusSelect = page.locator('.input-group:has-text("Status") select').first();
    if (await statusSelect.isVisible().catch(() => false)) {
      await statusSelect.selectOption('Active');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'up05_mitigation_project_registered.png') });
    copyArtifact('up05_mitigation_project_registered.png');
    console.log('[E2E UP] Captured up05_mitigation_project_registered.png.');

    // Click Save Record
    console.log('[E2E UP] Submitting Mitigation Record...');
    const saveBtn = page.locator('button:has-text("Save Record")').first();
    await saveBtn.click();

    // Verify confirmation toast
    const toast = page.locator('text=Mitigation record saved!').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Mitigation record saved notification toast.');
  });

  // -------------------------------------------------------------------------
  // TEST 6: Strategic Decarbonization Targets & Annual Pathway Goals
  // -------------------------------------------------------------------------
  test('UP-6: Strategic Decarbonization Targets & Annual Pathway Goals (/manage-data?tab=goals)', async ({ page }) => {
    console.log('[E2E UP] Navigating to Manage Data Goals (/manage-data?tab=goals)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=goals`);
    await page.waitForTimeout(1500);

    // Verify Goals Header
    const heading = page.locator('h2:has-text("Yearly Emission Goals")').first();
    await expect(heading).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Yearly Emission Goals heading.');

    // Fill Target Year
    const targetYear = 2035;
    const yearInput = page.locator('input[placeholder="e.g. 2030"]').first();
    await expect(yearInput).toBeVisible({ timeout: 10000 });
    await yearInput.fill(String(targetYear));

    // Fill Target Emission Amount
    const amountInput = page.locator('input[placeholder="e.g. 150000"]').first();
    await expect(amountInput).toBeVisible();
    await amountInput.fill('390000');

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'up06_decarbonization_goal_saved.png') });
    copyArtifact('up06_decarbonization_goal_saved.png');
    console.log('[E2E UP] Captured up06_decarbonization_goal_saved.png.');

    // Save Goal
    console.log('[E2E UP] Clicking Save Goal...');
    const saveBtn = page.locator('button:has-text("Save Goal"), button:has-text("Update Goal")').first();
    await saveBtn.click();

    // Verify entry in table
    const goalRow = page.locator(`tr:has-text("${targetYear}")`).first();
    await expect(goalRow).toBeVisible({ timeout: 10000 });
    console.log(`[E2E UP] Confirmed Emission goal row for ${targetYear} in Yearly Emission Goals table.`);
  });

  // -------------------------------------------------------------------------
  // TEST 7: Operational Region & Industrial Production Asset Provisioning
  // -------------------------------------------------------------------------
  test('UP-7: Operational Region & Industrial Production Asset Provisioning (/manage-data?tab=facilities)', async ({ page }) => {
    console.log('[E2E UP] Navigating to Manage Data Facilities (/manage-data?tab=facilities)...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=facilities`);
    await page.waitForTimeout(1500);

    // Verify Active Regions Card
    const regionTitle = page.locator('text=Active Regions').first();
    await expect(regionTitle).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Active Regions administration panel.');

    // Fill Region Name
    const uniqueRegionName = `Rhourde CPF Phase ${Date.now().toString().slice(-4)}`;
    const nameInput = page.locator('input[name="name"], input[placeholder="e.g. Hassi R\'Mel"]').first();
    await expect(nameInput).toBeVisible({ timeout: 10000 });
    await nameInput.fill(uniqueRegionName);

    // Select Activity (EP key from HIERARCHY)
    const actSelect = page.locator('select[name="activity"]').first();
    await actSelect.selectOption('EP');
    await page.waitForTimeout(400);

    // Select Division
    const divSelect = page.locator('select[name="division"]').first();
    await divSelect.selectOption({ index: 1 });
    await page.waitForTimeout(400);

    // Fill Location (Wilaya)
    const locInput = page.locator('input[name="location"], input[placeholder="e.g. Laghouat"]').first();
    if (await locInput.isVisible().catch(() => false)) {
      await locInput.fill('Illizi Basin');
    }

    // Select Consolidation Approach
    const boundarySelect = page.locator('select[name="boundary_type"]').first();
    if (await boundarySelect.isVisible().catch(() => false)) {
      await boundarySelect.selectOption({ index: 1 });
      await page.waitForTimeout(300);
    }

    // Select Segment
    const segSelect = page.locator('select[name="segment"]').first();
    if (await segSelect.isVisible().catch(() => false)) {
      await segSelect.selectOption('Upstream');
    }

    // Fill Coordinates
    const latInput = page.locator('input[name="latitude"]').first();
    if (await latInput.isVisible().catch(() => false)) {
      await latInput.fill('31.35');
    }
    const longInput = page.locator('input[name="longitude"]').first();
    if (await longInput.isVisible().catch(() => false)) {
      await longInput.fill('6.78');
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'up07_operational_region_provisioned.png') });
    copyArtifact('up07_operational_region_provisioned.png');
    console.log('[E2E UP] Captured up07_operational_region_provisioned.png.');

    // Click Add Region
    console.log('[E2E UP] Submitting new Operational Region...');
    const addBtn = page.locator('button:has-text("Add Region")').first();
    await addBtn.click();

    // Verify confirmation toast
    const toast = page.locator('text=Region added!').first();
    await expect(toast).toBeVisible({ timeout: 10000 });
    console.log('[E2E UP] Confirmed Region added! toast notification.');

    // Use search box to locate the newly added region in paginated table
    const searchBox = page.locator('input[placeholder*="Search facilities"]').first();
    if (await searchBox.isVisible().catch(() => false)) {
      await searchBox.fill(uniqueRegionName);
      await page.waitForTimeout(600);
    }

    // Verify entry in table
    const facilityRow = page.locator(`tr:has-text("${uniqueRegionName}")`).first();
    await expect(facilityRow).toBeVisible({ timeout: 10000 });
    console.log(`[E2E UP] Confirmed Region ${uniqueRegionName} in Active Regions table.`);
  });

});
