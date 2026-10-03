import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage.js';

test.describe('GHG Emissions Dashboard - E2E Test Suite (POM Pattern)', () => {
  /** @type {DashboardPage} */
  let dashboard;

  test.beforeEach(async ({ page }) => {
    dashboard = new DashboardPage(page);
    await dashboard.goto('/');
  });

  test('1. Core Dashboard Layout & Initial KPI Metrics Verification', async () => {
    // Verify core branding and live status indicator
    await expect(dashboard.gridTitle).toBeVisible();
    await expect(dashboard.gridTitle).toContainText('GHG Emissions Dashboard');
    await expect(dashboard.liveBadge).toBeVisible();

    // Verify hero overview panel and metric cards exist
    await expect(dashboard.heroCard).toBeVisible();
    const stats = await dashboard.getHeroStats();

    expect(stats.gross).not.toBe('');
    expect(stats.net).not.toBe('');
    expect(stats.methane).not.toBe('');
    expect(stats.intensity).not.toBe('');

    // Capture visual baseline artifact
    await dashboard.captureArtifact('dashboard-initial-baseline.png');
  });

  test('2. Dual GWP Horizon Dynamic Toggling (GWP-100 vs GWP-20)', async () => {
    // Initial state: GWP-100
    await expect(dashboard.gwp100Btn).toBeVisible();
    await expect(dashboard.gwp20Btn).toBeVisible();

    const initialStats = await dashboard.getHeroStats();

    // Toggle to near-term GWP-20 (Methane multiplier ~84x vs 28x, increasing CO2e)
    await dashboard.switchGwpHorizon('20');
    await dashboard.captureArtifact('dashboard-gwp-20-toggled.png');

    const gwp20Stats = await dashboard.getHeroStats();
    expect(gwp20Stats.gross).not.toBe('');

    // Revert back to standard GWP-100
    await dashboard.switchGwpHorizon('100');
    const revertedStats = await dashboard.getHeroStats();
    expect(revertedStats.gross).toBe(initialStats.gross);
  });

  test('3. Organizational Hierarchy & Breakdown Table Interaction', async () => {
    // Verify Breakdown section is present
    await expect(dashboard.breakdownSection.first()).toBeVisible({ timeout: 10000 });

    // Look for activity accordion row if present and toggle it
    const activityRow = dashboard.page.locator('tr.act-row').first();
    if (await activityRow.isVisible().catch(() => false)) {
      await activityRow.click();
      await dashboard.page.waitForTimeout(300);
      await dashboard.captureArtifact('dashboard-breakdown-expanded.png');
    }
  });

  test('4. Executive Summary PDF Export Button State', async () => {
    await expect(dashboard.exportPdfButton).toBeVisible();
    await expect(dashboard.exportPdfButton).toBeEnabled();

    // Verify button label and presence of export icon
    await expect(dashboard.exportPdfButton).toContainText(/Export Executive Brief/i);
  });

  test('5. Responsive Mobile / Tablet Layout Validation', async ({ page }) => {
    // Test on tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(400);
    await expect(dashboard.heroCard).toBeVisible();
    await dashboard.captureArtifact('dashboard-tablet-view.png');

    // Test on desktop standard viewport
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.waitForTimeout(400);
    await expect(dashboard.heroCard).toBeVisible();
  });
});
