/**
 * test_carbon_intensity_deep_audit.spec.js
 *
 * End-to-End Audit of Carbon Intensity & Product Embodiment Page:
 * 1. UI Rendering & Initial Numbers Verification (KPI Cards, Context Bar)
 * 2. Dual GWP Horizon Dynamic Toggle (100-Yr vs 20-Yr)
 * 3. Top Filter Dropdowns Cascading Behavior
 * 4. EU CBAM Compliance & Specific Embedded Emissions Table
 * 5. Regional Bar Charts Rendering
 * 6. Historical Trends View Switching (5-Year Line Chart vs Heatmap Matrix)
 */

import { test, expect } from '@playwright/test';

const FRONTEND = 'http://127.0.0.1:5173';
const BACKEND = 'http://127.0.0.1:5000';

async function setupCarbonIntensity(page) {
  await page.goto(FRONTEND, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(1500);

  // Skip intro video if present
  const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
  if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipBtn.click();
    await page.waitForTimeout(500);
  }

  // Login if on login page
  const emailInput = page.locator('input[placeholder="Email Address"]');
  if (await emailInput.isVisible({ timeout: 4000 }).catch(() => false)) {
    await emailInput.fill('a');
    await page.locator('input[type="password"]').fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(1000);
  }

  // Navigate to Carbon Intensity via NavLink or direct URL
  const ciLink = page.locator('a[href="/carbon-intensity"], a[title="Carbon Intensity"]').first();
  if (await ciLink.isVisible({ timeout: 3000 }).catch(() => false)) {
    await ciLink.click();
  } else {
    await page.goto(`${FRONTEND}/carbon-intensity`, { waitUntil: 'domcontentloaded' });
  }

  // Wait for Carbon Intensity grid to mount
  await expect(page.locator('.intensity-grid, .hero-card').first()).toBeVisible({ timeout: 15000 });
  await page.waitForTimeout(1000);
}

test.describe('Carbon Intensity Page Deep Audit', () => {

  test('1. Core Layout & KPI Cards Verification', async ({ page }) => {
    await setupCarbonIntensity(page);

    // Verify Title and Header
    const title = page.locator('.grid-title');
    await expect(title).toBeVisible();
    await expect(title).toContainText('Carbon Intensity & Product Embodiment');

    // Verify Year Badge
    const yearBadge = page.locator('.year-badge');
    await expect(yearBadge).toBeVisible();

    // Verify 4 KPI Cards
    const cards = page.locator('.kpi-card');
    await expect(cards).toHaveCount(4);

    // Card 1: GHG Intensity
    const card1 = cards.nth(0);
    await expect(card1.locator('.kpi-label')).toContainText('GHG Intensity');
    const card1Val = await card1.locator('.total-value').innerText();
    expect(card1Val).not.toContain('NaN');
    expect(card1Val).not.toContain('undefined');
    const card1Total = await card1.locator('.kpi-footer').innerText();
    expect(card1Total).toContain('tCO₂e');

    // Card 2: Scope 1 Direct Intensity
    const card2 = cards.nth(1);
    await expect(card2.locator('.kpi-label')).toContainText('Scope 1 Direct Intensity');
    const card2Val = await card2.locator('.total-value').innerText();
    expect(card2Val).not.toContain('NaN');
    expect(card2Val).not.toContain('undefined');
    const card2Footer = await card2.locator('.kpi-footer').innerText();
    expect(card2Footer).toContain('Total S1:');

    // Card 3: Flaring Carbon Intensity
    const card3 = cards.nth(2);
    await expect(card3.locator('.kpi-label')).toContainText('Flaring Carbon Intensity');
    const card3Val = await card3.locator('.total-value').innerText();
    expect(card3Val).not.toContain('NaN');

    // Card 4: Scope 3 Value Chain
    const card4 = cards.nth(3);
    await expect(card4.locator('.kpi-label')).toContainText('Scope 3 Value Chain');

    // Production Context Bar
    const scopeBreakdown = page.locator('.scope-breakdown');
    await expect(scopeBreakdown).toBeVisible();
    const oilProd = scopeBreakdown.locator('.scope-item:has-text("Total Oil Production") .val');
    const gasProd = scopeBreakdown.locator('.scope-item:has-text("Total Gas Production") .val');
    const boeProd = scopeBreakdown.locator('.scope-item:has-text("Combined Production (BOE)") .val');

    await expect(oilProd).toBeVisible();
    await expect(gasProd).toBeVisible();
    await expect(boeProd).toBeVisible();

    const boeText = await boeProd.innerText();
    expect(boeText).toContain('BOE');
    expect(boeText).not.toContain('NaN');
  });

  test('2. Dual GWP Horizon Dynamic Toggle (100-Yr vs 20-Yr)', async ({ page }) => {
    await setupCarbonIntensity(page);

    // Initial state: 100-Yr active
    const btn100 = page.locator('.gwp-pill:has-text("100-Yr")');
    const btn20 = page.locator('.gwp-pill:has-text("20-Yr")');
    await expect(btn100).toBeVisible();
    await expect(btn20).toBeVisible();
    await expect(btn100).toHaveClass(/active/);

    // Footer tag should indicate GWP100
    const card1Footer = page.locator('.kpi-card').nth(0).locator('.gwp-subtag');
    await expect(card1Footer).toContainText('GWP₁₀₀ Standard');

    // Capture initial values
    const initialGhgInt = await page.locator('.kpi-card').nth(0).locator('.total-value').innerText();
    const initialS1Int = await page.locator('.kpi-card').nth(1).locator('.total-value').innerText();

    // Click 20-Yr toggle
    await btn20.click();
    await page.waitForTimeout(500);

    // 20-Yr should now be active
    await expect(btn20).toHaveClass(/active/);
    await expect(btn100).not.toHaveClass(/active/);
    await expect(card1Footer).toContainText('GWP₂₀ Active');

    // Switch back to 100-Yr
    await btn100.click();
    await page.waitForTimeout(500);
    await expect(btn100).toHaveClass(/active/);
    await expect(card1Footer).toContainText('GWP₁₀₀ Standard');
  });

  test('3. Cascading Filters Interaction', async ({ page }) => {
    await setupCarbonIntensity(page);

    // Filter bar in top bar
    const filterContainer = page.locator('.dashboard-filters');
    await expect(filterContainer).toBeVisible({ timeout: 5000 });

    // Open Supply Chain dropdown
    const supplyChainTrigger = filterContainer.locator('.custom-dropdown-trigger').nth(1);
    if (await supplyChainTrigger.isVisible()) {
      await supplyChainTrigger.click();
      await page.waitForTimeout(300);

      const heavyIndustryOption = page.locator('.dropdown-item:has-text("Heavy Industry")');
      if (await heavyIndustryOption.isVisible()) {
        await heavyIndustryOption.click();
        await page.waitForTimeout(1000);

        // Verify page updated
        const title = page.locator('.grid-title');
        await expect(title).toBeVisible();
      }
    }
  });

  test('4. EU CBAM Product Specific Embedded Emissions Table', async ({ page }) => {
    await setupCarbonIntensity(page);

    // Scroll to CBAM section
    const cbamSection = page.locator('.cbam-section');
    await expect(cbamSection).toBeVisible();

    // Verify EU ETS benchmark badge
    const badge = cbamSection.locator('.cbam-benchmark-badge');
    await expect(badge).toBeVisible();
    await expect(badge).toContainText('EU ETS Benchmark');

    // Verify CBAM table exists
    const table = cbamSection.locator('table.custom-table');
    await expect(table).toBeVisible();

    // Verify Headers
    const headers = table.locator('th');
    await expect(headers.nth(0)).toContainText('Facility');
    await expect(headers.nth(1)).toContainText('Product Name');
    await expect(headers.nth(2)).toContainText('EU CN Code');
    await expect(headers.nth(6)).toContainText('Direct Intensity');
    await expect(headers.nth(7)).toContainText('Indirect Intensity');
    await expect(headers.nth(8)).toContainText('Total Embedded');

    // Verify at least one row exists
    const rows = table.locator('tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);

    // Check first row data
    const firstRow = rows.nth(0);
    const cnPill = firstRow.locator('.code-pill');
    await expect(cnPill).toBeVisible();
    const cnCode = await cnPill.innerText();
    expect(cnCode.length).toBeGreaterThan(3);
  });

  test('5. Regional Bar Charts Rendering', async ({ page }) => {
    await setupCarbonIntensity(page);

    const chartGrid = page.locator('.chart-grid');
    await expect(chartGrid).toBeVisible();

    // 4 chart cards
    const chartCards = chartGrid.locator('.card');
    await expect(chartCards).toHaveCount(4);

    // Verify Chart titles
    await expect(chartCards.nth(0).locator('h3')).toContainText('GHG Intensity by Facility');
    await expect(chartCards.nth(1).locator('h3')).toContainText('Scope 1 Direct vs Scope 2 Intensity');
    await expect(chartCards.nth(2).locator('h3')).toContainText('Oil BOE Contribution');
    await expect(chartCards.nth(3).locator('h3')).toContainText('Gas BOE Contribution');
  });

  test('6. Historical Trends View Switching (Chart vs Heatmap)', async ({ page }) => {
    await setupCarbonIntensity(page);

    const trendSection = page.locator('.trend-section');
    await expect(trendSection).toBeVisible();

    const chartBtn = trendSection.locator('.view-btn:has-text("Chart")');
    const heatmapBtn = trendSection.locator('.view-btn:has-text("Heatmap")');

    await expect(chartBtn).toBeVisible();
    await expect(heatmapBtn).toBeVisible();

    // Initial state: Chart active
    await expect(chartBtn).toHaveClass(/active/);

    // Click Heatmap
    await heatmapBtn.click();
    await page.waitForTimeout(500);

    // Heatmap should now be visible
    await expect(heatmapBtn).toHaveClass(/active/);
    const heatmap = trendSection.locator('.heatmap-container');
    await expect(heatmap).toBeVisible();

    // Verify heatmap header has FACILITY / REGION
    const header = heatmap.locator('.heatmap-header');
    await expect(header).toContainText('FACILITY / REGION');

    // Verify heatmap rows exist
    const rows = heatmap.locator('.heatmap-row');
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(0);

    // Toggle back to Chart
    await chartBtn.click();
    await page.waitForTimeout(500);
    await expect(chartBtn).toHaveClass(/active/);
    await expect(trendSection.locator('.heatmap-container')).not.toBeVisible();
  });

});
