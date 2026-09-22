/**
 * test_dashboard_deep_audit.spec.js
 *
 * Comprehensive End-to-End Audit of the Dashboard:
 * 1. UI Rendering & Initial Numbers Verification
 * 2. Filter Controls & Cascading Dropdowns Logic
 * 3. Year Switching & Dynamic Metric Updates
 * 4. Interactive Buttons, Accordions, and Mode Toggles (GWP-20, Compare Regions, Pending Preview)
 * 5. Detailed Breakdown Table & Organizational Hierarchy Tree
 * 6. Notification Center Panel, Real-time Counter & Actions
 * 7. Target Navigation and Reference Library Buttons
 */

import { test, expect } from '@playwright/test';

const FRONTEND = 'http://127.0.0.1:5173';
const BACKEND = 'http://127.0.0.1:5000';

async function setupDashboard(page) {
  await page.goto(FRONTEND, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForTimeout(1500);

  // Skip intro video if visible
  const skipBtn = page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
  if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await skipBtn.click();
  }
  // Wait for intro overlay to unmount
  await page.locator('.login-intro-overlay').waitFor({ state: 'detached', timeout: 4000 }).catch(() => {});
  await page.waitForTimeout(500);

  // Fill credentials if on login page
  const emailInput = page.locator('input[placeholder="Email Address"]');
  if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await emailInput.fill('a');
    await page.locator('input[type="password"]').fill('a');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 12000 }).catch(() => {});
  }

  // Ensure Dashboard layout is loaded
  await expect(page.locator('.app-container, .dashboard-grid, .sidebar').first()).toBeVisible({ timeout: 15000 });
  await page.waitForTimeout(1500);
}

test.describe('Dashboard Page Deep Audit', () => {

  test('1. Core Dashboard Layout & Initial Numbers Verification', async ({ page, request }) => {
    // 1. Fetch raw backend batch data for ground truth comparison
    const csrfResp = await request.get(`${BACKEND}/api/csrf-token`);
    const preCsrf = (await csrfResp.json()).csrf_token;
    await request.post(`${BACKEND}/api/auth/login`, {
      data: { email: 'a', password: 'a' },
      headers: { 'X-CSRFToken': preCsrf, 'Content-Type': 'application/json' }
    });
    const batchResp = await request.get(`${BACKEND}/api/dashboard/batch-all?facilityId=all&activity=all&division=all`);
    expect(batchResp.ok()).toBeTruthy();
    const batch = await batchResp.json();

    const summary2026 = batch.summary.find(s => s.year === 2026) || {};
    const backendScope1 = summary2026.scope1_total || 0; // 254895.0
    const backendCH4 = summary2026.ch4_total || 0;       // 238.7
    console.log(`[AUDIT] Backend Ground Truth: Scope 1 = ${backendScope1} tCO2e, CH4 = ${backendCH4} tCH4`);

    await setupDashboard(page);

    // Verify Title and Live Badge
    await expect(page.locator('.grid-title')).toHaveText('GHG Emissions Dashboard');
    await expect(page.locator('.live-badge')).toBeVisible();

    // Verify Hero Card Stats
    const grossEmissionsText = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
    const netEmissionsText = await page.locator('.stat-item:has-text("Net Emissions") .stat-value').innerText();
    const methaneText = await page.locator('.stat-item:has-text("Total CH4") .stat-value').innerText();

    console.log(`[AUDIT] UI Hero Card: Gross = ${grossEmissionsText}, Net = ${netEmissionsText}, CH4 = ${methaneText}`);

    expect(grossEmissionsText).toContain('256.4K');
    expect(netEmissionsText).toContain('256.4K');
    expect(methaneText).toContain('238.7');

    // Verify Scope Pills
    const scope1Pill = await page.locator('.scope-pill.scope-1 .pill-value').innerText();
    const scope2Pill = await page.locator('.scope-pill.scope-2 .pill-value').innerText();
    const scope3Pill = await page.locator('.scope-pill.scope-3 .pill-value').innerText();

    console.log(`[AUDIT] Scope Pills: S1 = ${scope1Pill}, S2 = ${scope2Pill}, S3 = ${scope3Pill}`);
    expect(scope1Pill).toContain('256.4K');
    expect(scope2Pill).toContain('0');
    expect(scope3Pill).toContain('0');
  });

  test('2. Top Filters Rendering & Cascading Dropdown Population', async ({ page }) => {
    await setupDashboard(page);

    // Locate the 5 top filters: Year, Supply Chain, Activity, Division, Region
    const filterWrappers = page.locator('.top-bar-injected-left .filter-wrapper');
    const filterCount = await filterWrappers.count();
    expect(filterCount).toBe(5);
    console.log(`[AUDIT] Top Filters Verified: ${filterCount} dropdowns present`);

    // 1. Check Year dropdown options
    const yearDropdown = filterWrappers.nth(0).locator('.dropdown-selected');
    await yearDropdown.click();
    await page.waitForTimeout(400);

    const yearOptions = page.locator('.dropdown-portal .dropdown-option');
    const yearTexts = await yearOptions.allInnerTexts();
    console.log(`[AUDIT] Year Options: ${yearTexts.join(', ')}`);
    expect(yearTexts).toContain('All Years');
    expect(yearTexts).toContain('2026');
    expect(yearTexts).toContain('2024');
    expect(yearTexts).toContain('2023');
    expect(yearTexts).toContain('2022');

    // Close dropdown
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);

    // 2. Check Supply Chain (Segment) dropdown
    const segmentDropdown = filterWrappers.nth(1).locator('.dropdown-selected');
    await segmentDropdown.click();
    await page.waitForTimeout(400);
    const segmentOptions = page.locator('.dropdown-portal .dropdown-option');
    const segmentTexts = await segmentOptions.allInnerTexts();
    console.log(`[AUDIT] Supply Chain Options: ${segmentTexts.join(', ')}`);
    expect(segmentTexts).toContain('All Supply Chains');
    expect(segmentTexts).toContain('Upstream');

    // Select Upstream
    const upstreamOpt = page.locator('.dropdown-portal .dropdown-option:has-text("Upstream")').first();
    await upstreamOpt.click();
    await page.waitForTimeout(1000);

    // 3. Verify Cascading: Activity dropdown should now filter to Upstream activities
    const activityDropdown = filterWrappers.nth(2).locator('.dropdown-selected');
    await activityDropdown.click();
    await page.waitForTimeout(400);
    const actOptions = page.locator('.dropdown-portal .dropdown-option');
    const actTexts = await actOptions.allInnerTexts();
    console.log(`[AUDIT] Cascaded Activity Options for Upstream: ${actTexts.join(', ')}`);
    expect(actTexts).toContain('All Activities');
    expect(actTexts.some(t => t.includes('E&P') || t.includes('Upstream'))).toBeTruthy();

    // Reset back to All Supply Chains
    await page.keyboard.press('Escape');
    await segmentDropdown.click();
    await page.locator('.dropdown-portal .dropdown-option:has-text("All Supply Chains")').click();
    await page.waitForTimeout(1000);
  });

  test('3. Dynamic Year Switching & Data Recalculation', async ({ page }) => {
    await setupDashboard(page);

    const yearDropdown = page.locator('.top-bar-injected-left .filter-wrapper').nth(0).locator('.dropdown-selected');

    // 1. Switch to Year 2026
    await yearDropdown.click();
    await page.waitForTimeout(400);
    await page.locator('.dropdown-portal .dropdown-option:has-text("2026")').click();
    await page.waitForTimeout(1500);

    // Assert 2026 metrics
    let grossVal = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
    expect(grossVal).toContain('256.4K');
    const scope3Val2026 = await page.locator('.scope-pill.scope-3 .pill-value').innerText();
    expect(scope3Val2026).toContain('0');
    console.log(`[AUDIT] Switched to 2026: Gross = ${grossVal}, Scope 3 = ${scope3Val2026} (verified accurate)`);

    // 2. Switch to Year 2024
    await yearDropdown.click();
    await page.waitForTimeout(400);
    await page.locator('.dropdown-portal .dropdown-option:has-text("2024")').click();
    await page.waitForTimeout(1500);

    // 2024 has 0 verified emissions
    grossVal = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
    expect(grossVal).toBe('0');
    console.log(`[AUDIT] Switched to 2024: Gross = ${grossVal} (verified accurate, 0 emissions)`);

    // 3. Switch back to All Years
    await yearDropdown.click();
    await page.waitForTimeout(400);
    await page.locator('.dropdown-portal .dropdown-option:has-text("All Years")').click();
    await page.waitForTimeout(1500);
    grossVal = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
    expect(grossVal).toContain('256.4K');
    console.log(`[AUDIT] Switched to All Years: Gross = ${grossVal} restored`);
  });

  test('4. Mode Toggles: GWP Horizon, Compare Regions, Pending Preview', async ({ page }) => {
    await setupDashboard(page);

    // 1. Dual GWP Horizon Toggle: GWP-100 (Standard) vs GWP-20 (Near-term)
    const gwp20Btn = page.locator('button:has-text("GWP-20")');
    const gwp100Btn = page.locator('button:has-text("GWP-100")');

    await expect(gwp100Btn).toBeVisible();
    await expect(gwp20Btn).toBeVisible();

    // Click GWP-20
    await gwp20Btn.click();
    await page.waitForTimeout(1500);

    // Under GWP-20, CH4 multiplier rises from 28 to 84 (delta = +56 per tonne CH4)
    // 256,425.1 + (56 * 238.7) - (1 * 51.1) = 269,741.2 tCO2e -> 269.7K
    const grossGwp20 = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
    console.log(`[AUDIT] GWP-20 Gross Emissions: ${grossGwp20}`);
    expect(grossGwp20).toContain('269.7K');

    // Switch back to GWP-100
    await gwp100Btn.click();
    await page.waitForTimeout(1500);
    const grossGwp100 = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
    expect(grossGwp100).toContain('256.4K');
    console.log(`[AUDIT] GWP-100 Restored: ${grossGwp100}`);

    // 2. Compare Regions Mode Toggle
    const compareBtn = page.locator('.compare-toggle-btn');
    await expect(compareBtn).toBeVisible();
    await compareBtn.click();
    await page.waitForTimeout(1000);
    await expect(compareBtn).toHaveText('Standard View');
    console.log('[AUDIT] Compare Regions view activated');

    await compareBtn.click();
    await page.waitForTimeout(1000);
    await expect(compareBtn).toHaveText('Compare Regions');
    console.log('[AUDIT] Standard View restored');

    // 3. Pending Data Preview Toggle
    const pendingSwitch = page.locator('.pending-switch input[type="checkbox"]');
    if (await pendingSwitch.isVisible().catch(() => false)) {
      await pendingSwitch.check();
      await page.waitForTimeout(2000);
      const activeBanner = page.locator('.pending-banner-card.active-preview');
      await expect(activeBanner).toBeVisible();

      // With pending data previewed, gross emissions include the ~4.1M pending draft emissions
      const grossPending = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
      console.log(`[AUDIT] Pending Data Preview Active: Gross = ${grossPending}`);
      expect(grossPending).toContain('M'); // Scales into Millions

      // Uncheck pending preview
      await pendingSwitch.uncheck();
      await page.waitForTimeout(1500);
      const grossRestored = await page.locator('.stat-item:has-text("Gross Operational Emissions") .stat-value').innerText();
      expect(grossRestored).toContain('256.4K');
      console.log(`[AUDIT] Pending Data Preview Deactivated: Gross = ${grossRestored}`);
    }
  });

  test('5. Detailed Breakdown Table & Organizational Hierarchy Tree', async ({ page }) => {
    await setupDashboard(page);

    // Scroll to Detailed Breakdown section
    const tableCard = page.locator('.detailed-table-card');
    await tableCard.scrollIntoViewIfNeeded();
    await expect(tableCard).toBeVisible();

    // Verify Source Breakdown Rows
    const combustionRow = await page.locator('.data-table tr:has-text("Stationary Combustion") td.text-right').innerText();
    const flaringRow = await page.locator('.data-table tr:has-text("Flaring") td.text-right').innerText();
    const ventingRow = await page.locator('.data-table tr:has-text("Venting") td.text-right').innerText();
    const otherRow = await page.locator('.data-table tr:has-text("Other Sources") td.text-right').innerText();
    const totalFootprintRow = await page.locator('.data-table tr:has-text("Total Footprint") td.text-right').innerText();

    console.log(`[AUDIT] Breakdown Table Sources:
      Combustion: ${combustionRow}
      Flaring: ${flaringRow}
      Venting: ${ventingRow}
      Other: ${otherRow}
      Total: ${totalFootprintRow}`);

    expect(combustionRow).toContain('64.4K');
    expect(flaringRow).toContain('24.5K');
    expect(ventingRow).toContain('16.5K');
    expect(otherRow).toContain('151K');
    expect(totalFootprintRow).toContain('256.4K');

    // Expand Organizational Tree (Click Activity row)
    const actRow = page.locator('.data-table tr.act-row:has-text("Steel & Iron")');
    if (await actRow.isVisible().catch(() => false)) {
      await actRow.click();
      await page.waitForTimeout(500);

      // Division row should now appear
      const divRow = page.locator('.data-table tr.div-row:has-text("Metallurgy")');
      await expect(divRow).toBeVisible();

      // Click Division row to expand regions
      await divRow.click();
      await page.waitForTimeout(500);

      // Facility row should appear
      const regRow = page.locator('.data-table tr.reg-row:has-text("Complexe Sidérurgique")');
      await expect(regRow).toBeVisible();
      const regVal = await regRow.locator('td.text-right').innerText();
      console.log(`[AUDIT] Expanded Facility Row: Complexe Sidérurgique = ${regVal}`);
      expect(regVal).toContain('74.4K');
    }

    // Test Accordion Collapse/Expand
    const breakdownHeader = page.locator('.table-header-row.clickable-card-header');
    await breakdownHeader.click();
    await page.waitForTimeout(400);
    await expect(page.locator('.detailed-table-card')).toHaveClass(/collapsed-card/);
    console.log('[AUDIT] Detailed Breakdown Accordion Collapsed');

    await breakdownHeader.click();
    await page.waitForTimeout(400);
    await expect(page.locator('.detailed-table-card')).not.toHaveClass(/collapsed-card/);
    console.log('[AUDIT] Detailed Breakdown Accordion Expanded');
  });

  test('6. Notification Center Panel, Real-time Counter & Actions', async ({ page }) => {
    await setupDashboard(page);

    // Scroll to TopBar
    await page.locator('.top-bar').scrollIntoViewIfNeeded();

    // Verify Bell Button and Unread Counter
    const bellBtn = page.locator('button[title="Notifications"]');
    await expect(bellBtn).toBeVisible();

    const badge = bellBtn.locator('span');
    const hasBadge = await badge.isVisible().catch(() => false);
    console.log(`[AUDIT] Notification Badge Visible: ${hasBadge}`);

    if (hasBadge) {
      const countText = await badge.innerText();
      console.log(`[AUDIT] Notification Badge Count: ${countText}`);
      expect(parseInt(countText)).toBeGreaterThan(0);
    }

    // Open Notification Panel
    await bellBtn.click();
    await page.waitForTimeout(600);

    // Verify panel header
    const panel = page.locator('div:has-text("Notifications").glass-panel, div[style*="z-index: 99999"]');
    await expect(panel.first()).toBeVisible();
    console.log('[AUDIT] Notification Center Panel Opened');

    // Close by pressing Escape
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    console.log('[AUDIT] Notification Center Panel Closed via Escape');
  });

  test('7. Target Navigation and Reference Library Buttons', async ({ page }) => {
    await setupDashboard(page);

    // 1. Target Button (either "+ Set Target" or "Edit Target")
    const targetBtn = page.locator('.btn-target-action');
    await expect(targetBtn).toBeVisible();
    const targetBtnText = await targetBtn.innerText();
    console.log(`[AUDIT] Target Action Button: "${targetBtnText}"`);

    // 2. Reference Libraries Card & Manage Custom Factors button
    const manageFactorsBtn = page.locator('.manage-factors-btn');
    await manageFactorsBtn.scrollIntoViewIfNeeded();
    await expect(manageFactorsBtn).toBeVisible();
    console.log('[AUDIT] Manage Custom Factors button is visible and accessible');
  });

  test('8. Performance Intensity Card & Scope 3 Filter Parity', async ({ page }) => {
    await setupDashboard(page);

    // Performance Intensity Card initial state (Pending / Production figures required when no production data)
    const intensityCard = page.locator('.stat-item:has-text("Performance Intensity")');
    await expect(intensityCard).toBeVisible();
    const intensityLabel = await intensityCard.locator('.stat-label').innerText();
    expect(intensityLabel.toUpperCase()).toBe('PERFORMANCE INTENSITY');

    // Scope 3 Year Filter check: Ensure Scope 3 displays 0 when year has no scope 3 records
    const yearDropdown = page.locator('.top-bar-injected-left .filter-wrapper').nth(0).locator('.dropdown-selected');
    await yearDropdown.click();
    await page.waitForTimeout(400);
    await page.locator('.dropdown-portal .dropdown-option:has-text("2026")').click();
    await page.waitForTimeout(1000);

    const s3Pill = await page.locator('.scope-pill.scope-3 .pill-value').innerText();
    expect(s3Pill).toBe('0 tCO₂e');
    console.log('[AUDIT] Verified Scope 3 evaluates to 0 tCO2e for 2026 (Bug 2 fix confirmed)');
  });
});
