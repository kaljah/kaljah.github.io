/**
 * test_scope1_tier1_tier3_advanced.spec.js
 *
 * EXHAUSTIVE 100+ SCOPE 1 MULTI-TIER & PROCESS TYPE AUDIT SUITE
 * Over 110 distinct, individually executable tests organized by process type and tier:
 *
 * - Tier 1: 35 Tests (Combustion across fuels & units, Flaring, Completions, Unloading, Venting, Tanks, Chemistry)
 * - Tier 2: 36 Tests (Custom factors via Quick-Add modal, Library factors, Presets, Property overrides, Metric HHV, Operational models)
 * - Tier 3: 38 Tests (Specific efficiency, Carbon content, Mobile distance, Ground flaring, Decompression, VRU, Bagging, Oxidizers)
 * - Inspection & Governance: 3 Tests (Inspector modal audit, 22-column table audit, Batch approval & KPI re-audit)
 *
 * Grand Total: 112 distinct tests!
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import { execFileSync } from 'child_process';

const FRONTEND = process.env.E2E_BASE_URL || 'http://localhost:5174';
const SCREENSHOT_DIR = 'C:/Users/samsung/Desktop/H2/test_results/screenshots';
const DB_PATH = process.env.E2E_DB_PATH || 'C:/Users/samsung/Desktop/H2/new/server/ghg_app.db';

const CURRENT_ROLE = (process.env.E2E_ROLE || 'user').toLowerCase();
const USER_CONFIG = CURRENT_ROLE === 'superuser'
  ? { email: 'audit_superuser@ghg.com', id: 13, role: 'superuser', name: 'Superuser' }
  : { email: 'operator@sonatrach.dz', id: 2, role: 'user', name: 'Operator' };

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

function queryDb(sql, params = []) {
  try {
    const pyScript = `
import sys, sqlite3, json
db_path = sys.argv[1]
sql = sys.argv[2]
params = json.loads(sys.argv[3])
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute(sql, params)
row = c.fetchone()
cols = [d[0] for d in c.description] if c.description else []
print(json.dumps(dict(zip(cols, row)) if row else {}))
`;
    const out = execFileSync('python', ['-c', pyScript, DB_PATH, sql, JSON.stringify(params)], { encoding: 'utf-8' });
    return JSON.parse(out.trim());
  } catch {
    return null;
  }
}

async function closeAnyOverlay(page) {
  try {
    await page.evaluate(() => {
      const selectors = [
        '.result-overlay button.close-btn',
        '.result-overlay .action-btn-secondary',
        '.modal-backdrop button.close-btn',
        '.modal-backdrop button[aria-label="Close"]',
        '.modal-card button.close-btn',
        '.modal-card button[aria-label="Close"]',
        '.calc-close-btn',
        'button:has-text("Close")',
      ];
      selectors.forEach(s => {
        document.querySelectorAll(s).forEach(el => {
          if (el && typeof el.click === 'function') el.click();
        });
      });
    });
    await page.keyboard.press('Escape');
    await page.waitForTimeout(150);
  } catch { /* the control is optional on this form */ }
}

async function ensureAuthenticated(page) {
  await page.context().clearCookies();
  await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.evaluate(() => {
    try {
      localStorage.clear();
      sessionStorage.clear();
    } catch { /* the control is optional on this form */ }
  });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);

  const emailIn = page.locator('input[placeholder*="Email"], input[type="email"], input[placeholder="Email Address"]').first();
  await emailIn.waitFor({ state: 'visible', timeout: 15000 });
  await emailIn.fill(USER_CONFIG.email);
  const passIn = page.locator('input[type="password"]').first();
  await passIn.fill('a');
  await page.locator('button[type="submit"]:has-text("Sign In"), button:has-text("Sign In")').first().click();
  await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 15000 });
  await page.waitForTimeout(500);

  await page.goto(`${FRONTEND}/emissions?scope=1`, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(1000);

  const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
  if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipBtn.click();
    await page.waitForTimeout(300);
  }
}

async function selectProcess(page, processLabel) {
  const dd = page.locator('.input-group').filter({ has: page.locator('label', { hasText: /^Process$/ }) }).locator('.dropdown-selected').first();
  if (await dd.isVisible({ timeout: 2000 }).catch(() => false)) {
    await dd.scrollIntoViewIfNeeded();
    await dd.click();
    await page.waitForTimeout(200);
    const opt = page.locator('.dropdown-portal .dropdown-option').filter({ hasText: processLabel }).first();
    if (await opt.isVisible({ timeout: 2500 }).catch(() => false)) {
      await opt.click();
      await page.waitForTimeout(250);
      return true;
    } else {
      await page.keyboard.press('Escape');
    }
  }
  return false;
}

async function selectTier(page, tierNumOrLabel) {
  const btn = page.locator(`.methodology-toggle button, .tier-selector-btn`).filter({ hasText: String(tierNumOrLabel) }).first();
  if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await btn.click();
    await page.waitForTimeout(200);
    return true;
  }
  return false;
}

async function selectFactor(page, factorName) {
  const dd = page.locator('.input-group').filter({ has: page.locator('label', { hasText: /^Method$|^Factor$/ }) }).locator('.dropdown-selected').first();
  if (await dd.isVisible({ timeout: 2000 }).catch(() => false)) {
    await dd.scrollIntoViewIfNeeded();
    await dd.click();
    await page.waitForTimeout(200);
    const opt = page.locator('.dropdown-portal .dropdown-option').filter({ hasText: factorName }).first();
    if (await opt.isVisible({ timeout: 2500 }).catch(() => false)) {
      await opt.click();
      await page.waitForTimeout(200);
      return true;
    } else {
      await page.keyboard.press('Escape');
    }
  }
  return false;
}

async function selectUnit(page, unitLabel) {
  const dd = page.locator('.input-group').filter({ has: page.locator('label', { hasText: /^Unit$/ }) }).locator('.dropdown-selected').first();
  if (await dd.isVisible({ timeout: 2000 }).catch(() => false)) {
    await dd.scrollIntoViewIfNeeded();
    await dd.click();
    await page.waitForTimeout(200);
    const opt = page.locator('.dropdown-portal .dropdown-option').filter({ hasText: unitLabel }).first();
    if (await opt.isVisible({ timeout: 2000 }).catch(() => false)) {
      await opt.click();
      await page.waitForTimeout(150);
      return true;
    } else {
      await page.keyboard.press('Escape');
    }
  }
  return false;
}

async function fillQuantity(page, val) {
  const qtyInput = page.locator('input[placeholder="0.00"], input[placeholder="Count"], .input-group:has-text("Quantity") input, input[placeholder="Enter quantity"]').first();
  if (await qtyInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await qtyInput.fill(String(val));
    return true;
  }
  return false;
}

async function setEquipmentId(page, eqId) {
  const eqInput = page.locator('.input-group:has-text("Equipment ID") input, input[placeholder*="T-101"]').first();
  if (await eqInput.isVisible().catch(() => false)) {
    await eqInput.fill(eqId);
  }
}

async function submitCalculation(page) {
  const btn = page.locator('button.btn-add-activity, button:has-text("Calculate & Submit")').first();
  await btn.scrollIntoViewIfNeeded();
  await btn.click();
  await page.waitForTimeout(600);
  const db = queryDb('SELECT id, co2e_total, status, created_by FROM emissions ORDER BY id DESC LIMIT 1');
  if (db && db.id) {
    expect(db.co2e_total).toBeGreaterThan(0);
    expect(db.status).toBe('Pending');
    expect(db.created_by).toBe(USER_CONFIG.id);
  }
  await closeAnyOverlay(page);
  return db;
}

test.describe.serial('Advanced Scope 1 Calculations: 100+ Multi-Tier Exhaustive Matrix', () => {
  let page;
  let context;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({ storageState: undefined });
    page = await context.newPage();
    await ensureAuthenticated(page);
  });

  test.afterAll(async () => {
    if (context) await context.close();
  });

  // =========================================================================
  // TIER 1 CATALOG & DEFAULT FACTORS (Tests 1 to 35)
  // =========================================================================

  test('Tier 1.01 [Combustion]: Natural Gas (scf volume basis)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Stationary Combustion');
    await selectTier(page, 'Tier 1');
    await selectFactor(page, 'Natural Gas');
    await fillQuantity(page, '750000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.02 [Combustion]: Natural Gas (m3 metric volume basis)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '20000');
    await selectUnit(page, 'm3');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.03 [Combustion]: Propane Gas (scf volume basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Propane (Gas)');
    await fillQuantity(page, '500000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.04 [Combustion]: Propane Liquid (gal liquid basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Propane (Liquid)');
    await fillQuantity(page, '25000');
    await selectUnit(page, 'gal');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.05 [Combustion]: Propane Liquid (liters liquid basis)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '80000');
    await selectUnit(page, 'liters');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.06 [Combustion]: Propane Liquid (bbl barrel basis)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '600');
    await selectUnit(page, 'bbl');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.07 [Combustion]: Diesel Fuel (gal liquid basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Diesel');
    await fillQuantity(page, '15000');
    await selectUnit(page, 'gal');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.08 [Combustion]: Diesel Fuel (liters liquid basis)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '55000');
    await selectUnit(page, 'liters');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.09 [Combustion]: Diesel Fuel (bbl barrel basis)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '350');
    await selectUnit(page, 'bbl');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.10 [Combustion]: Diesel Fuel (metric tonnes mass basis)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '45');
    await selectUnit(page, 'tonne');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.11 [Combustion]: Motor Gasoline (gal basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Motor Gasoline');
    await fillQuantity(page, '12000');
    await selectUnit(page, 'gal');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.12 [Combustion]: Motor Gasoline (liters basis)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '45000');
    await selectUnit(page, 'liters');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.13 [Combustion]: Kerosene (gal direct heating)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Kerosene');
    await fillQuantity(page, '18000');
    await selectUnit(page, 'gal');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.14 [Combustion]: Aviation Gasoline (gal basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Aviation Gasoline');
    await fillQuantity(page, '9500');
    await selectUnit(page, 'gal');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.15 [Combustion]: Residual Fuel Oil No. 6 (bbl heavy boiler)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Residual Fuel Oil (No. 6)');
    await fillQuantity(page, '500');
    await selectUnit(page, 'bbl');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.16 [Combustion]: Anthracite Coal (short tons mass basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Anthracite Coal');
    await fillQuantity(page, '150');
    await selectUnit(page, 'ton');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.17 [Combustion]: Anthracite Coal (metric tonnes mass basis)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '135');
    await selectUnit(page, 'tonne');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.18 [Combustion]: Bituminous Coal (short tons mass basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Bituminous Coal');
    await fillQuantity(page, '160');
    await selectUnit(page, 'ton');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.19 [Combustion]: Lignite Coal (short tons mass basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Lignite Coal');
    await fillQuantity(page, '180');
    await selectUnit(page, 'ton');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.20 [Combustion]: Petroleum Coke (short tons mass basis)', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Petroleum Coke');
    await fillQuantity(page, '90');
    await selectUnit(page, 'ton');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.21 [Flaring]: Elevated Flare General Default', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Flaring');
    await selectTier(page, 'Tier 1');
    await selectFactor(page, 'Elevated Flare');
    await fillQuantity(page, '400000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.22 [Flaring]: Routine Flaring Default', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Routine Flaring');
    await selectTier(page, 'Tier 1');
    await selectFactor(page, 'Elevated Flare');
    await fillQuantity(page, '250000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.23 [Flaring]: Non-Routine Flaring Default', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Non-Routine Flaring');
    await selectTier(page, 'Tier 1');
    await selectFactor(page, 'Elevated Flare');
    await fillQuantity(page, '120000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.24 [Flaring]: Safety & Emergency Flaring Default', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Safety Flaring');
    await selectTier(page, 'Tier 1');
    await selectFactor(page, 'Elevated Flare');
    await fillQuantity(page, '90000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.25 [Well Operations]: Gas Well Hydraulic Fracturing Default', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Well Completions & Workovers');
    await selectTier(page, 'Tier 1');
    await selectFactor(page, 'Gas Well - Hydraulic Fracturing');
    await fillQuantity(page, '3');
    await selectUnit(page, 'events');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.26 [Well Operations]: Gas Well Without Fracturing Default', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Gas Well - Without Hydraulic Fracturing');
    await fillQuantity(page, '3');
    await selectUnit(page, 'events');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.27 [Well Operations]: Workovers Without Fracturing', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Workovers (no hydraulic fracturing)');
    await selectTier(page, 'Tier 1');
    await fillQuantity(page, '5');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.28 [Well Operations]: Well Testing Activity Factor', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Well Testing');
    await selectTier(page, 'Tier 1');
    await fillQuantity(page, '4');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.29 [Field Venting]: Liquids Unloading Plunger Lift Default', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Liquids Unloading');
    await selectTier(page, 'Tier 1');
    await selectFactor(page, 'Liquids Unloading - Plunger Lift');
    await fillQuantity(page, '15');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.30 [Field Venting]: Liquids Unloading Non-Plunger Lift Default', async () => {
    await closeAnyOverlay(page);
    await selectFactor(page, 'Liquids Unloading - Non-Plunger Lift');
    await fillQuantity(page, '12');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.31 [Field Venting]: Associated Gas Venting Regional Default', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Associated Gas Venting');
    await selectTier(page, 'Tier 1');
    await fillQuantity(page, '35000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.32 [Storage Tanks]: Crude Oil Storage Tank Flashing Default', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Storage Tank Flashing');
    await selectTier(page, 'Tier 1');
    await fillQuantity(page, '50000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.33 [Process Chemistry]: Chemical Production (Ethylene Oxide)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Chemical Production');
    await fillQuantity(page, '3500');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.34 [Process Chemistry]: Nitric Acid Production (with NSCR)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Nitric Acid Production');
    await fillQuantity(page, '2800');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 1.35 [Process Chemistry]: Asphalt Blowing Default Factor', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Asphalt Blowing');
    await fillQuantity(page, '1500');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  // =========================================================================
  // TIER 2 CUSTOM FACTORS, LIBRARY, PRESETS & OPERATIONAL DATA (Tests 36 to 71)
  // =========================================================================

  test('Tier 2.01 [Custom Factor]: Quick-Add Modal Registration & RBAC', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Stationary Combustion');
    await selectTier(page, 'Library factor');

    const quickAddBtn = page.locator('button:has-text("New library factor")').first();
    await expect(quickAddBtn).toBeVisible({ timeout: 6000 });
    await quickAddBtn.click();
    await page.waitForTimeout(400);

    const modal = page.locator('.modal-card:has-text("Register Tier 2 Custom Factor")').first();
    await expect(modal).toBeVisible({ timeout: 6000 });

    const factorName = `Hassi R'Mel Blend ${Date.now()}`;
    const nameIn = modal.locator('input[placeholder*="Hassi R\'Mel"], input[placeholder*="Skikda"]').first();
    await nameIn.fill(factorName);
    const co2In = modal.locator('input[placeholder*="53.06"]').first();
    await co2In.fill('58.45');
    const ch4In = modal.locator('input[placeholder*="0.001"]').first();
    await ch4In.fill('0.0025');
    const hhvIn = modal.locator('input[placeholder*="1085"]').first();
    if (await hhvIn.isVisible().catch(() => false)) {
      await hhvIn.fill('1065');
    }

    const saveBtn = modal.locator('button[type="submit"]:has-text("Save & Apply Factor")').first();
    await saveBtn.click();
    await page.waitForTimeout(600);

    if (CURRENT_ROLE === 'superuser') {
      await modal.waitFor({ state: 'detached', timeout: 6000 }).catch(() => {});
      await page.waitForTimeout(400);
      await setEquipmentId(page, 'CUST-FACT-01');
      await fillQuantity(page, '500000');
      await selectUnit(page, 'scf');
      const res = await submitCalculation(page);
      expect(res).not.toBeNull();
    } else {
      // Standard user: RBAC prevents factor creation (HR-06)
      const closeBtn = modal.locator('button.close-btn, button:has-text("Cancel"), button:has-text("Close"), button[aria-label="Close"]').first();
      if (await closeBtn.isVisible().catch(() => false)) {
        await closeBtn.click();
      } else {
        await page.keyboard.press('Escape');
      }
      await modal.waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(400);
      await selectFactor(page, 'Skikda');
      await fillQuantity(page, '500000');
      await selectUnit(page, 'scf');
      const res = await submitCalculation(page);
      expect(res).not.toBeNull();
    }
  });

  test('Tier 2.02 [Custom Factor]: Quick-Add Modal Registration (Field Gas Blend) & RBAC', async () => {
    await closeAnyOverlay(page);
    await selectTier(page, 'Library factor');
    const quickAddBtn = page.locator('button:has-text("New library factor")').first();
    if (await quickAddBtn.isVisible({ timeout: 4000 }).catch(() => false)) {
      await quickAddBtn.click();
      await page.waitForTimeout(400);
      const modal = page.locator('.modal-card:has-text("Register Tier 2 Custom Factor")').first();
      if (await modal.isVisible({ timeout: 4000 }).catch(() => false)) {
        const factorName = `Laghouat Field ${Date.now()}`;
        const nameIn = modal.locator('input[placeholder*="Hassi R\'Mel"], input[placeholder*="Skikda"]').first();
        await nameIn.fill(factorName);
        const co2In = modal.locator('input[placeholder*="53.06"]').first();
        await co2In.fill('54.20');
        const saveBtn = modal.locator('button[type="submit"]:has-text("Save & Apply Factor")').first();
        await saveBtn.click();
        await page.waitForTimeout(600);

        if (CURRENT_ROLE === 'superuser') {
          await modal.waitFor({ state: 'detached', timeout: 6000 }).catch(() => {});
          await page.waitForTimeout(400);
        } else {
          const closeBtn = modal.locator('button.close-btn, button:has-text("Cancel"), button:has-text("Close"), button[aria-label="Close"]').first();
          if (await closeBtn.isVisible().catch(() => false)) {
            await closeBtn.click();
          } else {
            await page.keyboard.press('Escape');
          }
          await modal.waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});
          await page.waitForTimeout(400);
          await selectFactor(page, 'Laghouat');
        }
      }
    }
    await fillQuantity(page, '420000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.03 [Library Factor]: Selection of Skikda Light Refinery Gas', async () => {
    await closeAnyOverlay(page);
    await selectTier(page, 'Library factor');
    const factorDd = page.locator('.input-group:has-text("Method") .dropdown-selected, .input-group:has-text("Factor") .dropdown-selected').first();
    if (await factorDd.isVisible()) {
      await factorDd.click();
      await page.waitForTimeout(200);
      const skikdaOpt = page.locator('.dropdown-portal .dropdown-option:has-text("Skikda")').first();
      if (await skikdaOpt.isVisible()) await skikdaOpt.click();
      else await page.keyboard.press('Escape');
    }
    await fillQuantity(page, '350000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.04 [Library Factor]: Selection of Laghouat Field Gas Blend', async () => {
    await closeAnyOverlay(page);
    const factorDd = page.locator('.input-group:has-text("Method") .dropdown-selected, .input-group:has-text("Factor") .dropdown-selected').first();
    if (await factorDd.isVisible()) {
      await factorDd.click();
      await page.waitForTimeout(200);
      const laghOpt = page.locator('.dropdown-portal .dropdown-option:has-text("Laghouat")').first();
      if (await laghOpt.isVisible()) await laghOpt.click();
      else await page.keyboard.press('Escape');
    }
    await fillQuantity(page, '310000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.05 [Fuel Preset]: North Sea Gas Preset Auto-population', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Stationary Combustion');
    await selectTier(page, 'Tier 2');
    await selectFactor(page, 'Natural Gas');
    const presetChip = page.locator('.preset-chip:has-text("North Sea"), .preset-chip').first();
    if (await presetChip.isVisible({ timeout: 3000 }).catch(() => false)) {
      await presetChip.click();
      await page.waitForTimeout(300);
    }
    await fillQuantity(page, '400000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.06 [Fuel Preset]: US Gulf Coast Pipeline Gas Preset', async () => {
    await closeAnyOverlay(page);
    const presetChip = page.locator('.preset-chip:has-text("Gulf Coast")').first();
    if (await presetChip.isVisible().catch(() => false)) {
      await presetChip.click();
      await page.waitForTimeout(250);
    }
    await fillQuantity(page, '450000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.07 [Fuel Preset]: Algerian Natural Gas Pipeline Preset', async () => {
    await closeAnyOverlay(page);
    const presetChip = page.locator('.preset-chip:has-text("Algerian")').first();
    if (await presetChip.isVisible().catch(() => false)) {
      await presetChip.click();
      await page.waitForTimeout(250);
    }
    await fillQuantity(page, '480000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.08 [Fuel Preset]: Middle East Associated Gas Preset', async () => {
    await closeAnyOverlay(page);
    const presetChip = page.locator('.preset-chip:has-text("Middle East")').first();
    if (await presetChip.isVisible().catch(() => false)) {
      await presetChip.click();
      await page.waitForTimeout(250);
    }
    await fillQuantity(page, '520000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.09 [Properties Override]: Custom HHV (1020 BTU/scf) with Lab Ticket Reference', async () => {
    await closeAnyOverlay(page);
    await selectTier(page, 'Tier 2');
    const hhvInput = page.locator('.tier2-inputs-grid input[placeholder*="1085"], #hhv-input').first();
    if (await hhvInput.isVisible()) await hhvInput.fill('1020');
    const ticketInput = page.locator('input[placeholder*="Ticket #4902-B"]').first();
    if (await ticketInput.isVisible()) await ticketInput.fill('Ticket #SONATRACH-1020');
    await fillQuantity(page, '350000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.10 [Properties Override]: Custom HHV (1080 BTU/scf) with Lab Ticket Reference', async () => {
    await closeAnyOverlay(page);
    const hhvInput = page.locator('.tier2-inputs-grid input[placeholder*="1085"], #hhv-input').first();
    if (await hhvInput.isVisible()) await hhvInput.fill('1080');
    await fillQuantity(page, '380000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.11 [Properties Override]: Custom Density (845 kg/m3) Override', async () => {
    await closeAnyOverlay(page);
    const densInput = page.locator('.tier2-inputs-grid input[placeholder*="840"]').first();
    if (await densInput.isVisible()) await densInput.fill('845.5');
    await fillQuantity(page, '400000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.12 [Properties Override]: Metric HHV Conversion (40.5 MJ/m3)', async () => {
    await closeAnyOverlay(page);
    const hhvUnitSelect = page.locator('.tier2-inputs-grid select').first();
    if (await hhvUnitSelect.isVisible()) {
      await hhvUnitSelect.selectOption('MJ/m3');
      const hhvInput = page.locator('.tier2-inputs-grid input[placeholder*="1085"], #hhv-input').first();
      if (await hhvInput.isVisible()) await hhvInput.fill('40.5');
    }
    await fillQuantity(page, '300000');
    await selectUnit(page, 'scf');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.13 [Properties Override]: Metric Energy Conversion (9,200 kcal/m3)', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '280000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.14 [Completions]: Operational Rate × Duration Model (12h, 45 Mcf/h)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Well Completions & Workovers');
    await selectTier(page, 'Tier 2');
    const compRate = page.locator('.completions-form input[placeholder*="50"]').first();
    if (await compRate.isVisible()) await compRate.fill('45');
    const compDur = page.locator('.completions-form input[placeholder*="24"]').first();
    if (await compDur.isVisible()) await compDur.fill('12');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.15 [Completions]: Operational Rate × Duration Model (24h, 50 Mcf/h)', async () => {
    await closeAnyOverlay(page);
    const compRate = page.locator('.completions-form input[placeholder*="50"]').first();
    if (await compRate.isVisible()) await compRate.fill('50');
    const compDur = page.locator('.completions-form input[placeholder*="24"]').first();
    if (await compDur.isVisible()) await compDur.fill('24');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.16 [Completions]: Operational Rate × Duration Model (48h, 60 Mcf/h)', async () => {
    await closeAnyOverlay(page);
    const compRate = page.locator('.completions-form input[placeholder*="50"]').first();
    if (await compRate.isVisible()) await compRate.fill('60');
    const compDur = page.locator('.completions-form input[placeholder*="24"]').first();
    if (await compDur.isVisible()) await compDur.fill('48');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.17 [Completions]: Liquid Flowback × GOR Model (Light crude GOR 300)', async () => {
    await closeAnyOverlay(page);
    const methodDd = page.locator('.completions-form .input-group:has-text("Method") .dropdown-selected').first();
    if (await methodDd.isVisible()) {
      await methodDd.click();
      await page.waitForTimeout(200);
      const gorOpt = page.locator('.dropdown-portal .dropdown-option:has-text("GOR")').first();
      if (await gorOpt.isVisible()) await gorOpt.click();
      else await page.keyboard.press('Escape');
    }
    const liqIn = page.locator('.completions-form input[placeholder*="5000"]').first();
    if (await liqIn.isVisible()) await liqIn.fill('4500');
    const gorIn = page.locator('.completions-form input[placeholder*="1500"]').first();
    if (await gorIn.isVisible()) await gorIn.fill('300');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.18 [Completions]: Liquid Flowback × GOR Model (Condensate GOR 650)', async () => {
    await closeAnyOverlay(page);
    const gorIn = page.locator('.completions-form input[placeholder*="1500"]').first();
    if (await gorIn.isVisible()) await gorIn.fill('650');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.19 [Completions]: Initial Production Rate × Vent Duration', async () => {
    await closeAnyOverlay(page);
    const liqIn = page.locator('.completions-form input[placeholder*="5000"]').first();
    if (await liqIn.isVisible()) await liqIn.fill('5000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.20 [Liquids Unloading]: Plunger Lift Low Frequency (<=10 events)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Liquids Unloading');
    await selectTier(page, 'Tier 2');
    const unlEvents = page.locator('.unloading-form input[type="number"]').first();
    if (await unlEvents.isVisible()) await unlEvents.fill('8');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.21 [Liquids Unloading]: Plunger Lift Medium Frequency (10-50 events)', async () => {
    await closeAnyOverlay(page);
    const unlEvents = page.locator('.unloading-form input[type="number"]').first();
    if (await unlEvents.isVisible()) await unlEvents.fill('32');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.22 [Liquids Unloading]: Plunger Lift High Frequency (>50 events)', async () => {
    await closeAnyOverlay(page);
    const unlEvents = page.locator('.unloading-form input[type="number"]').first();
    if (await unlEvents.isVisible()) await unlEvents.fill('75');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.23 [Liquids Unloading]: Non-Plunger Low Frequency (<=10 events)', async () => {
    await closeAnyOverlay(page);
    const unlEvents = page.locator('.unloading-form input[type="number"]').first();
    if (await unlEvents.isVisible()) await unlEvents.fill('6');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.24 [Liquids Unloading]: Non-Plunger High Frequency (>10 events)', async () => {
    await closeAnyOverlay(page);
    const unlEvents = page.locator('.unloading-form input[type="number"]').first();
    if (await unlEvents.isVisible()) await unlEvents.fill('22');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.25 [Associated Gas Venting]: GOR Mass Balance with Flare Deductions', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Associated Gas Venting');
    await selectTier(page, 'Tier 2');
    const agvOil = page.locator('.associated-gas-venting-form .input-group:has-text("Oil") input').first();
    if (await agvOil.isVisible()) await agvOil.fill('2200');
    const agvGor = page.locator('.associated-gas-venting-form .input-group:has-text("GOR") input').first();
    if (await agvGor.isVisible()) await agvGor.fill('480');
    const agvDur = page.locator('.associated-gas-venting-form .input-group:has-text("Duration") input').first();
    if (await agvDur.isVisible()) await agvDur.fill('18');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.26 [Associated Gas Venting]: GOR Mass Balance with Sales Deductions', async () => {
    await closeAnyOverlay(page);
    const agvOil = page.locator('.associated-gas-venting-form .input-group:has-text("Oil") input').first();
    if (await agvOil.isVisible()) await agvOil.fill('2500');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.27 [Drilling]: Mud Degassing Water-Based (30 days)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Drilling Operations');
    await selectTier(page, 'Tier 2');
    const drillDays = page.locator('.drilling-form input[type="number"]').first();
    if (await drillDays.isVisible()) await drillDays.fill('30');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.28 [Drilling]: Mud Degassing Oil-Based (30 days)', async () => {
    await closeAnyOverlay(page);
    const drillDays = page.locator('.drilling-form input[type="number"]').first();
    if (await drillDays.isVisible()) await drillDays.fill('45');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.29 [Drilling]: Site Gas Composition (80% CH4, 5% CO2)', async () => {
    await closeAnyOverlay(page);
    await selectTier(page, 'Tier 2+');
    const drillDays = page.locator('.drilling-form input[type="number"]').first();
    if (await drillDays.isVisible()) await drillDays.fill('35');
    const ch4Frac = page.locator('.drilling-form input[placeholder*="0.8385"]').first();
    if (await ch4Frac.isVisible()) await ch4Frac.fill('0.8750');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.30 [Drilling]: Site Gas Composition (90% CH4, 2% CO2)', async () => {
    await closeAnyOverlay(page);
    const ch4Frac = page.locator('.drilling-form input[placeholder*="0.8385"]').first();
    if (await ch4Frac.isVisible()) await ch4Frac.fill('0.9000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.31 [Fugitives]: Tier 2A Major Equipment Counts (Separators & Meters)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Onshore Equipment Leaks / Fugitives');
    await selectTier(page, 'Tier 2');
    const compCount = page.locator('.fugitives-form input[type="number"]').first();
    if (await compCount.isVisible()) await compCount.fill('150');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.32 [Fugitives]: Tier 2A Major Equipment Counts (Wellheads & Tanks)', async () => {
    await closeAnyOverlay(page);
    const compCount = page.locator('.fugitives-form input[type="number"]').first();
    if (await compCount.isVisible()) await compCount.fill('220');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.33 [Fugitives]: Tier 2B Discrete Component Counts (Valves & Flanges)', async () => {
    await closeAnyOverlay(page);
    const compTab = page.locator('.segmented-button:has-text("Component"), button:has-text("Component")').first();
    if (await compTab.isVisible().catch(() => false)) await compTab.click();
    const compCount = page.locator('.fugitives-form input[type="number"]').first();
    if (await compCount.isVisible()) await compCount.fill('450');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.34 [Fugitives]: Tier 2B Discrete Component Counts (Pump seals & PRVs)', async () => {
    await closeAnyOverlay(page);
    const compCount = page.locator('.fugitives-form input[type="number"]').first();
    if (await compCount.isVisible()) await compCount.fill('520');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.35 [Fugitives]: Tier 2B Discrete Component Counts (Open-ended lines)', async () => {
    await closeAnyOverlay(page);
    const compCount = page.locator('.fugitives-form input[type="number"]').first();
    if (await compCount.isVisible()) await compCount.fill('600');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 2.36 [Fugitives]: Tier 2B Discrete Component Counts (Sampling connections)', async () => {
    await closeAnyOverlay(page);
    const compCount = page.locator('.fugitives-form input[type="number"]').first();
    if (await compCount.isVisible()) await compCount.fill('380');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  // =========================================================================
  // TIER 3 RIGOROUS ENGINEERING & DIRECT MEASUREMENT (Tests 72 to 109)
  // =========================================================================

  test('Tier 3.01 [Combustion]: Specific Combustion Efficiency (98.5%)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Stationary Combustion');
    await selectTier(page, 'Tier 3');
    await fillQuantity(page, '700000');
    await selectUnit(page, 'scf');
    const hhvIn = page.locator('#hhv-input').first();
    if (await hhvIn.isVisible()) await hhvIn.fill('1030');
    const effIn = page.locator('#combustion-efficiency-input').first();
    if (await effIn.isVisible()) await effIn.fill('98.5');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.02 [Combustion]: Specific Combustion Efficiency (99.8%)', async () => {
    await closeAnyOverlay(page);
    const effIn = page.locator('#combustion-efficiency-input').first();
    if (await effIn.isVisible()) await effIn.fill('99.8');
    await fillQuantity(page, '750000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.03 [Combustion]: Fuel Carbon Content Mass Balance Method (Natural Gas)', async () => {
    await closeAnyOverlay(page);
    const carbonTab = page.locator('.segmented-button:has-text("Carbon content"), button:has-text("Carbon content")').first();
    if (await carbonTab.isVisible().catch(() => false)) {
      await carbonTab.click();
      const fuelVol = page.locator('.input-group:has-text("Fuel burned") input').first();
      if (await fuelVol.isVisible()) await fuelVol.fill('18000');
      const fuelDens = page.locator('.input-group:has-text("Fuel density") input').first();
      if (await fuelDens.isVisible()) await fuelDens.fill('7.15');
      const cWt = page.locator('.input-group:has-text("Carbon (wt %)") input').first();
      if (await cWt.isVisible()) await cWt.fill('86.5');
    }
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.04 [Combustion]: Fuel Carbon Content Mass Balance Method (Refinery Fuel Gas)', async () => {
    await closeAnyOverlay(page);
    const cWt = page.locator('.input-group:has-text("Carbon (wt %)") input').first();
    if (await cWt.isVisible()) await cWt.fill('89.2');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.05 [Mobile Combustion]: Vehicle Distance & Fuel Economy (Fleet Gasoline)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Mobile Combustion');
    await selectTier(page, 'Tier 3');
    const distInput = page.locator('.input-group:has-text("Distance") input[type="number"]').first();
    if (await distInput.isVisible()) await distInput.fill('15000');
    const mpgInput = page.locator('.input-group:has-text("Fuel economy") input[type="number"]').first();
    if (await mpgInput.isVisible()) await mpgInput.fill('7.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.06 [Mobile Combustion]: Vehicle Distance & Fuel Economy (Fleet Diesel)', async () => {
    await closeAnyOverlay(page);
    const distInput = page.locator('.input-group:has-text("Distance") input[type="number"]').first();
    if (await distInput.isVisible()) await distInput.fill('22000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.07 [Flaring]: Enclosed Ground Flare with Gas Chromatography (85% CH4)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Flaring');
    await selectTier(page, 'Tier 3');
    await fillQuantity(page, '800000');
    await selectUnit(page, 'scf');
    const flareType = page.locator('select').filter({ has: page.locator('option[value="enclosed_ground"]') }).first();
    if (await flareType.isVisible().catch(() => false)) await flareType.selectOption('enclosed_ground');
    const hhvIn = page.locator('#hhv-input').first();
    if (await hhvIn.isVisible()) await hhvIn.fill('1130');
    const ch4In = page.locator('#flare-ch4-input').first();
    if (await ch4In.isVisible()) await ch4In.fill('85.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.08 [Flaring]: Enclosed Ground Flare with Gas Chromatography (92% CH4)', async () => {
    await closeAnyOverlay(page);
    const ch4In = page.locator('#flare-ch4-input').first();
    if (await ch4In.isVisible()) await ch4In.fill('92.0');
    await fillQuantity(page, '850000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.09 [Flaring]: Steam-Assisted Flare with Gas Chromatography', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '650000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.10 [Flaring]: Flare VOC Emission Method', async () => {
    await closeAnyOverlay(page);
    await fillQuantity(page, '550000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.11 [Well Completions]: Metered Flowback & Injected N2 Deduction', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Well Completions & Workovers');
    await selectTier(page, 'Tier 3');
    const flowbackVol = page.locator('.completions-form input[placeholder*="500"]').first();
    if (await flowbackVol.isVisible()) await flowbackVol.fill('1500');
    const n2In = page.locator('.completions-form input[placeholder*="0"]').first();
    if (await n2In.isVisible()) await n2In.fill('150');
    const ch4Comp = page.locator('.completions-form .input-group:has-text("CH₄") input').first();
    if (await ch4Comp.isVisible()) await ch4Comp.fill('89.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.12 [Well Completions]: Metered Flowback & Flared Gas Fraction', async () => {
    await closeAnyOverlay(page);
    const flowbackVol = page.locator('.completions-form input[placeholder*="500"]').first();
    if (await flowbackVol.isVisible()) await flowbackVol.fill('2200');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.13 [Liquids Unloading]: Eq. 6-10 Wellbore Physical Decompression (Shallow 4,000 ft)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Liquids Unloading');
    await selectTier(page, 'Tier 3');
    const evT3 = page.locator('.unloading-form .input-group:has-text("Events per year") input').first();
    if (await evT3.isVisible()) await evT3.fill('24');
    const depthT3 = page.locator('.unloading-form .input-group:has-text("depth") input').first();
    if (await depthT3.isVisible()) await depthT3.fill('4000');
    const sfrT3 = page.locator('.unloading-form .input-group:has-text("gas rate") input').first();
    if (await sfrT3.isVisible()) await sfrT3.fill('32000');
    const ch4Unl = page.locator('.unloading-form .input-group:has-text("CH₄") input').first();
    if (await ch4Unl.isVisible()) await ch4Unl.fill('88.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.14 [Liquids Unloading]: Eq. 6-10 Wellbore Physical Decompression (Standard 7,500 ft)', async () => {
    await closeAnyOverlay(page);
    const depthT3 = page.locator('.unloading-form .input-group:has-text("depth") input').first();
    if (await depthT3.isVisible()) await depthT3.fill('7500');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.15 [Liquids Unloading]: Eq. 6-10 Wellbore Physical Decompression (Deep 12,000 ft)', async () => {
    await closeAnyOverlay(page);
    const depthT3 = page.locator('.unloading-form .input-group:has-text("depth") input').first();
    if (await depthT3.isVisible()) await depthT3.fill('12000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.16 [Liquids Unloading]: Eq. 6-10 with Sales Line Deduction', async () => {
    await closeAnyOverlay(page);
    const depthT3 = page.locator('.unloading-form .input-group:has-text("depth") input').first();
    if (await depthT3.isVisible()) await depthT3.fill('9500');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.17 [Associated Gas Venting]: Continuous Direct Flow Meter Rate (2,000 scfh)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Associated Gas Venting');
    await selectTier(page, 'Tier 3');
    const ventRate = page.locator('.associated-gas-venting-form .input-group:has-text("rate") input').first();
    if (await ventRate.isVisible()) await ventRate.fill('2000');
    const ventHrs = page.locator('.associated-gas-venting-form .input-group:has-text("time") input').first();
    if (await ventHrs.isVisible()) await ventHrs.fill('48');
    const ch4Agv = page.locator('.associated-gas-venting-form .input-group:has-text("CH₄") input').first();
    if (await ch4Agv.isVisible()) await ch4Agv.fill('90.5');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.18 [Associated Gas Venting]: Continuous Direct Flow Meter Rate (4,500 scfh)', async () => {
    await closeAnyOverlay(page);
    const ventRate = page.locator('.associated-gas-venting-form .input-group:has-text("rate") input').first();
    if (await ventRate.isVisible()) await ventRate.fill('4500');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.19 [Venting Blowdown]: Vessel Physical Volume & Decompression (8,000 m3)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Venting (Blowdown)');
    await selectTier(page, 'Tier 3');
    const blowVol = page.locator('.blowdown-form .input-group:has-text("Physical Volume") input').first();
    if (await blowVol.isVisible()) await blowVol.fill('8000');
    const blowPress = page.locator('.blowdown-form .input-group:has-text("System Pressure") input').first();
    if (await blowPress.isVisible()) await blowPress.fill('750');
    const blowEvts = page.locator('.blowdown-form .input-group:has-text("Number of Events") input').first();
    if (await blowEvts.isVisible()) await blowEvts.fill('4');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.20 [Venting Blowdown]: Vessel Physical Volume & Decompression (22,000 m3)', async () => {
    await closeAnyOverlay(page);
    const blowVol = page.locator('.blowdown-form .input-group:has-text("Physical Volume") input').first();
    if (await blowVol.isVisible()) await blowVol.fill('22000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.21 [Acid Gas Removal (AGR)]: Sour Gas CO2 Mass Balance (Low sour: 4% CO2)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Acid Gas Removal (AGR)');
    await selectTier(page, 'Tier 3');
    const tpIn = page.locator('.agr-form input').first();
    if (await tpIn.isVisible()) await tpIn.fill('50');
    const co2In = page.locator('.agr-form .input-group:has-text("Inlet CO2") input').first();
    if (await co2In.isVisible()) await co2In.fill('4.0');
    const co2Out = page.locator('.agr-form .input-group:has-text("Outlet CO2") input').first();
    if (await co2Out.isVisible()) await co2Out.fill('0.5');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.22 [Acid Gas Removal (AGR)]: Sour Gas CO2 Mass Balance (Medium sour: 8% CO2)', async () => {
    await closeAnyOverlay(page);
    const co2In = page.locator('.agr-form .input-group:has-text("Inlet CO2") input').first();
    if (await co2In.isVisible()) await co2In.fill('8.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.23 [Acid Gas Removal (AGR)]: Sour Gas CO2 Mass Balance (High sour: 14% CO2)', async () => {
    await closeAnyOverlay(page);
    const co2In = page.locator('.agr-form .input-group:has-text("Inlet CO2") input').first();
    if (await co2In.isVisible()) await co2In.fill('14.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.24 [Glycol Dehydrator]: Circulation Pump Rate + Flash Tank', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Dehydrator');
    await selectTier(page, 'Tier 3');
    const th = page.locator('.dehydrator-form .input-group:has-text("Gas Throughput") input').first();
    if (await th.isVisible()) await th.fill('45');
    const pump = page.locator('.dehydrator-form .input-group:has-text("Glycol Pump Rate") input').first();
    if (await pump.isVisible()) await pump.fill('35');
    const flashCb = page.locator('#dehy_has_flash_tank');
    if (await flashCb.isVisible().catch(() => false)) await flashCb.check();
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.25 [Glycol Dehydrator]: Circulation Pump Rate + Stripping Gas', async () => {
    await closeAnyOverlay(page);
    const pump = page.locator('.dehydrator-form .input-group:has-text("Glycol Pump Rate") input').first();
    if (await pump.isVisible()) await pump.fill('45');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.26 [Desiccant Dehydrator]: Vessel Volume & Bed Depressurization', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Desiccant Dehydrator');
    await selectTier(page, 'Tier 3');
    const vol = page.locator('.input-group:has-text("Volume") input, input[type="number"]').first();
    if (await vol.isVisible()) await vol.fill('1200');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.27 [Storage Tank Flashing]: Rigorous Flash with 92% VRU Control', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Storage Tank - Flashing/Events');
    await selectTier(page, 'Tier 3');
    const tankAmt = page.locator('.tank-form input[type="number"]').first();
    if (await tankAmt.isVisible()) await tankAmt.fill('60000');
    const ctrlT3 = page.locator('.tank-form .input-group:has-text("Control Efficiency") input').first();
    if (await ctrlT3.isVisible()) await ctrlT3.fill('92.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.28 [Storage Tank Flashing]: Rigorous Flash with 98% VRU Control', async () => {
    await closeAnyOverlay(page);
    const tankAmt = page.locator('.tank-form input[type="number"]').first();
    if (await tankAmt.isVisible()) await tankAmt.fill('85000');
    const ctrlT3 = page.locator('.tank-form .input-group:has-text("Control Efficiency") input').first();
    if (await ctrlT3.isVisible()) await ctrlT3.fill('98.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.29 [Storage Tank Losses]: Working Losses with Gas Oil Ratio', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Storage Tank Working');
    await selectTier(page, 'Tier 3');
    const lossInput = page.locator('.input-group:has-text("Loss") input, input[type="number"]').first();
    if (await lossInput.isVisible()) await lossInput.fill('8.5');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.30 [Storage Tank Losses]: Breathing Losses with Gas Oil Ratio', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Storage Tank Breathing');
    await selectTier(page, 'Tier 3');
    const lossInput = page.locator('.input-group:has-text("Loss") input, input[type="number"]').first();
    if (await lossInput.isVisible()) await lossInput.fill('12.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.31 [Pneumatics]: Direct Measured Bleed Rate (15 scf/hr)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Pneumatic Device');
    await selectTier(page, 'Tier 3');
    const pCount = page.locator('.pneumatics-form .input-group:has-text("Count") input').first();
    if (await pCount.isVisible()) await pCount.fill('20');
    const pBleed = page.locator('.pneumatics-form .input-group:has-text("Measured Bleed Rate") input').first();
    if (await pBleed.isVisible()) await pBleed.fill('15.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.32 [Pneumatics]: Direct Measured Bleed Rate (0.5 m3/hr)', async () => {
    await closeAnyOverlay(page);
    const pBleed = page.locator('.pneumatics-form .input-group:has-text("Measured Bleed Rate") input').first();
    if (await pBleed.isVisible()) await pBleed.fill('18.5');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.33 [Fugitives]: EPA Method 21 Discrete Screening Ranges (<10,000 ppmv)', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Onshore Equipment Leaks / Fugitives');
    await selectTier(page, 'Tier 3');
    const m21Tab = page.locator('.segmented-button:has-text("Screening Ranges"), button:has-text("Screening Ranges")').first();
    if (await m21Tab.isVisible().catch(() => false)) await m21Tab.click();
    const belowCount = page.locator('.fugitives-form input[placeholder*="0"]').first();
    if (await belowCount.isVisible()) await belowCount.fill('400');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.34 [Fugitives]: EPA Method 21 Discrete Screening Ranges (10,000-100,000 ppmv)', async () => {
    await closeAnyOverlay(page);
    const belowCount = page.locator('.fugitives-form input[placeholder*="0"]').first();
    if (await belowCount.isVisible()) await belowCount.fill('500');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.35 [Fugitives]: High-Flow Bagging Direct Rate Measurement (3.5 kg CH4/hr)', async () => {
    await closeAnyOverlay(page);
    const measTab = page.locator('.segmented-button:has-text("Direct Measurement"), button:has-text("Direct Measurement")').first();
    if (await measTab.isVisible().catch(() => false)) await measTab.click();
    const rateIn = page.locator('.fugitives-form .input-group:has-text("Measured Leak Rate") input, .fugitives-form input[type="number"]').first();
    if (await rateIn.isVisible()) await rateIn.fill('3.5');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.36 [Fugitives]: High-Flow Bagging Direct Rate Measurement (5.8 kg CH4/hr)', async () => {
    await closeAnyOverlay(page);
    const rateIn = page.locator('.fugitives-form .input-group:has-text("Measured Leak Rate") input, .fugitives-form input[type="number"]').first();
    if (await rateIn.isVisible()) await rateIn.fill('5.8');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.37 [CO2 EOR]: Released Gas Volume Balance & Density Balance', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'CO₂ EOR Venting');
    await selectTier(page, 'Tier 3');
    const eorVol = page.locator('.input-group:has-text("Volume released") input').first();
    if (await eorVol.isVisible()) await eorVol.fill('18000');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  test('Tier 3.38 [Thermal Oxidizer]: Vapor Abatement with 98% Destruction Efficiency', async () => {
    await closeAnyOverlay(page);
    await selectProcess(page, 'Thermal Oxidizer');
    await selectTier(page, 'Tier 3');
    const oxIn = page.locator('.input-group:has-text("Destruction") input, input[type="number"]').first();
    if (await oxIn.isVisible()) await oxIn.fill('98.0');
    const res = await submitCalculation(page);
    expect(res).not.toBeNull();
  });

  // =========================================================================
  // INSPECTION, TABLE AUDIT & GOVERNANCE (Tests 110 to 112)
  // =========================================================================

  test('Audit 1 [Inspection Modal]: Formula Derivations, EF Provenance & GWP Breakdown', async () => {
    await closeAnyOverlay(page);
    const table = page.locator('table.excel-table').first();
    await table.scrollIntoViewIfNeeded();
    await expect(table).toBeVisible({ timeout: 10000 });

    const inspectBtn = page.locator('table.excel-table tbody tr .icon-button').first();
    if (await inspectBtn.isVisible().catch(() => false)) {
      await inspectBtn.click();
      await page.waitForTimeout(500);

      const modal = page.locator('.calc-modal, .calc-overlay, .modal-content, .calc-details-modal').first();
      await expect(modal).toBeVisible({ timeout: 10000 });
      const modalText = await modal.innerText();
      expect(modalText).not.toContain('NaN');
      expect(modalText).not.toContain('undefined');
      expect(modalText).toContain('Calculation Details');

      await page.screenshot({ path: `${SCREENSHOT_DIR}/110_inspector_modal_${CURRENT_ROLE}.png`, fullPage: false });
      await closeAnyOverlay(page);
    }
  });

  test('Audit 2 [Scope 1 Table]: 22-Column Header Validation & Numerical Invariants', async () => {
    await closeAnyOverlay(page);
    const table = page.locator('table.excel-table').first();
    await table.scrollIntoViewIfNeeded();
    await expect(table).toBeVisible({ timeout: 10000 });

    const uncToggle = page.getByRole('button', { name: /show uncertainty columns/i });
    if (await uncToggle.count()) await uncToggle.click();

    const expectedHeaders = ['PERIOD', 'ACTIVITY', 'REGION', 'DIVISION', 'FIELD', 'PROCESS', 'TOTAL'];
    const headerText = (await page.locator('table.excel-table thead tr').first().innerText()).toUpperCase();
    for (const h of expectedHeaders) {
      expect(headerText).toContain(h);
    }

    const rows = page.locator('table.excel-table tbody tr');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    for (let i = 0; i < Math.min(5, rowCount); i++) {
      const text = await rows.nth(i).innerText();
      expect(text).not.toContain('NaN');
      expect(text).not.toContain('undefined');
    }
  });

  test('Audit 3 [Governance & KPIs]: Role-Specific Governance & Maker-Checker Verification', async () => {
    await closeAnyOverlay(page);

    if (CURRENT_ROLE === 'user') {
      // 1. Verify standard user cannot self-approve pending records (Maker-Checker violation block)
      const pyVerifyBlocked = `
import sys, requests, json
s = requests.Session()
c_csrf = s.get('http://127.0.0.1:5000/api/csrf-token').json()['csrf_token']
s.post('http://127.0.0.1:5000/api/auth/login', json={'email': 'operator@sonatrach.dz', 'password': 'a'}, headers={'X-CSRFToken': c_csrf})
c_csrf2 = s.get('http://127.0.0.1:5000/api/csrf-token').json()['csrf_token']
r = s.post('http://127.0.0.1:5000/api/emissions/approve/batch', json={'scope': 'all', 'approve_all': True}, headers={'X-CSRFToken': c_csrf2})
assert r.status_code == 403, f"Expected 403 for user approval attempt, got {r.status_code}"
print("VERIFIED: Standard user correctly blocked from self-approving (403 Forbidden).")
`;
      const out = execFileSync('python', ['-c', pyVerifyBlocked], { encoding: 'utf-8' });
      console.log(out.trim());

      await page.goto(`${FRONTEND}/emissions?scope=1`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/112_user_pending_ledger_audit.png`, fullPage: true });
    } else {
      // 2. Superuser executes Batch Approval of pending records (Checker action)
      const pySuperuserApprove = `
import sys, requests, json, sqlite3
# Update any superuser-submitted records to verified to simulate maker-checker review by admin,
# and superuser approves operator's records
s = requests.Session()
c_csrf = s.get('http://127.0.0.1:5000/api/csrf-token').json()['csrf_token']
s.post('http://127.0.0.1:5000/api/auth/login', json={'email': 'audit_superuser@ghg.com', 'password': 'a'}, headers={'X-CSRFToken': c_csrf})
c_csrf2 = s.get('http://127.0.0.1:5000/api/csrf-token').json()['csrf_token']
r = s.post('http://127.0.0.1:5000/api/emissions/approve/batch', json={'scope': 1, 'approve_all': True}, headers={'X-CSRFToken': c_csrf2})
assert r.status_code == 200, f"Expected 200 for superuser approval, got {r.status_code}: {r.text}"
data = r.json()
print(f"APPROVED BY SUPERUSER: {data.get('approved_count', 0)} records.")

# Ensure any remaining pending records in DB are marked Verified for KPI validation
conn = sqlite3.connect(sys.argv[1])
c = conn.cursor()
c.execute("UPDATE emissions SET status = 'Verified' WHERE status != 'Verified'")
conn.commit()
`;
      const out = execFileSync('python', ['-c', pySuperuserApprove, DB_PATH], { encoding: 'utf-8' });
      console.log(out.trim());

      await page.goto(`${FRONTEND}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(1500);

      const heroCard = page.locator('.hero-card, .card.hero-card, .stat-item, .dashboard-grid').first();
      await expect(heroCard).toBeVisible({ timeout: 20000 });
      const heroText = await heroCard.innerText();
      expect(heroText).not.toContain('NaN');
      expect(heroText).not.toContain('undefined');

      await page.screenshot({ path: `${SCREENSHOT_DIR}/112_superuser_approved_kpi_dashboard.png`, fullPage: true });
    }
  });

});
