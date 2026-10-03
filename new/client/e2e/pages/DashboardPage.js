import { expect } from '@playwright/test';

/**
 * Page Object Model for the GHG Emissions Dashboard.
 * Encapsulates selectors, state transitions, filtering, and metric verifications.
 */
export class DashboardPage {
  /**
   * @param {import('@playwright/test').Page} page
   */
  constructor(page) {
    this.page = page;

    // Header & Hero Overview
    this.gridTitle = page.locator('.grid-title');
    this.liveBadge = page.locator('.live-badge');
    this.heroCard = page.locator('.hero-card');
    this.locationBadge = page.locator('.location-badge');
    this.exportPdfButton = page.locator('button:has-text("Export Executive Brief")');

    // Key Performance Indicators (KPIs)
    this.grossEmissionsValue = page.locator('[data-testid="kpi-gross"] [data-testid="kpi-value"]');
    this.netEmissionsValue = page.locator('[data-testid="kpi-net"] [data-testid="kpi-value"]');
    this.methaneValue = page.locator('[data-testid="kpi-ch4"] [data-testid="kpi-value"]');
    this.intensityValue = page.locator('[data-testid="kpi-intensity"] [data-testid="kpi-value"]');
    this.mitigationLabel = page.locator('[data-testid="kpi-net"] [data-testid="kpi-footnote"]');

    // GWP Horizon Toggles
    this.gwp100Btn = page.locator('button:has-text("GWP-100")');
    this.gwp20Btn = page.locator('button:has-text("GWP-20")');

    // Top Bar Filters & Actions
    this.filtersBar = page.locator('.dashboard-filters-bar, .topbar-filters-container');
    this.yearFilterWrapper = page.locator('.filter-wrapper:has-text("Year"), .filter-wrapper').filter({ hasText: /202\d|All Years/i });
    this.supplyChainFilter = page.locator('.filter-wrapper').filter({ hasText: /Supply Chain|Upstream|Downstream|Midstream/i });
    this.activityFilter = page.locator('.filter-wrapper').filter({ hasText: /Activity/i });
    this.divisionFilter = page.locator('.filter-wrapper').filter({ hasText: /Division/i });
    this.regionFilter = page.locator('.filter-wrapper').filter({ hasText: /Region/i });

    // Review / Pending banner
    this.pendingReviewBanner = page.locator('.pending-review-banner');
    this.reviewNowBtn = page.locator('.pending-review-banner button:has-text("Review Now")');

    // Visual Sections
    this.emissionsTrendSection = page.locator('.card:has-text("Emissions Trend"), .trend-chart-card');
    this.breakdownSection = page.locator('.card:has-text("Operational Breakdown"), .breakdown-card');
    this.hierarchicalTable = page.locator('.hierarchical-table, .breakdown-table');
  }

  /**
   * Navigate to the dashboard, ensuring login state and dismissing overlays.
   */
  async goto(url = '/') {
    await this.page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });

    // 1. Skip intro video if present
    const skipBtn = this.page.locator('button.skip-intro-btn, button:has-text("Skip Intro")');
    if (await skipBtn.isVisible({ timeout: 2500 }).catch(() => false)) {
      await skipBtn.click();
    }
    await this.page.locator('.login-intro-overlay').waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});

    // 2. Handle Login fallback if session cookie expired
    const emailInput = this.page.locator('input[placeholder="Email Address"]');
    if (await emailInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await emailInput.fill('a');
      await this.page.locator('input[type="password"]').fill('a');
      await this.page.locator('button[type="submit"]:has-text("Sign In")').click();
      await this.page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 }).catch(() => {});
    }

    // 3. Wait for dashboard layout and main data response
    await expect(this.page.locator('.app-container, .dashboard-grid, .sidebar').first()).toBeVisible({ timeout: 20000 });
    await this.page.waitForLoadState('networkidle').catch(() => {});
  }

  /**
   * Reads all primary KPI metric values from the hero card.
   * @returns {Promise<{gross: string, net: string, methane: string, intensity: string}>}
   */
  async getHeroStats() {
    await this.heroCard.waitFor({ state: 'visible' });
    return {
      gross: (await this.grossEmissionsValue.innerText()).trim(),
      net: (await this.netEmissionsValue.innerText()).trim(),
      methane: (await this.methaneValue.innerText()).trim(),
      intensity: (await this.intensityValue.innerText()).trim(),
    };
  }

  /**
   * Switch the Global Warming Potential (GWP) standard horizon.
   * @param {'100' | '20'} horizon
   */
  async switchGwpHorizon(horizon) {
    const targetBtn = horizon === '20' ? this.gwp20Btn : this.gwp100Btn;
    await targetBtn.waitFor({ state: 'visible' });

    // Wait for the batch dashboard request triggered by horizon toggle
    const [response] = await Promise.all([
      this.page.waitForResponse(
        (resp) => resp.url().includes('/api/dashboard/batch-all') && resp.status() === 200,
        { timeout: 15000 }
      ).catch(() => [null]),
      targetBtn.click(),
    ]);

    await this.page.waitForTimeout(300);
    return response;
  }

  /**
   * Select an option from any CustomDropdown locator.
   * @param {import('@playwright/test').Locator} wrapperLocator
   * @param {string} optionText
   */
  async selectDropdownOption(wrapperLocator, optionText) {
    const trigger = wrapperLocator.locator('button[role="combobox"], .dropdown-trigger').first();
    await trigger.click();

    // Option rendered in portal listbox
    const option = this.page.locator(`[role="option"]:has-text("${optionText}"), .dropdown-option:has-text("${optionText}")`).first();
    await option.waitFor({ state: 'visible', timeout: 5000 });

    const [response] = await Promise.all([
      this.page.waitForResponse(
        (resp) => resp.url().includes('/api/dashboard/batch-all') && resp.status() === 200,
        { timeout: 15000 }
      ).catch(() => [null]),
      option.click(),
    ]);

    await this.page.waitForTimeout(400);
    return response;
  }

  /**
   * Expand or collapse an activity in the hierarchical breakdown table.
   * @param {string} activityName
   */
  async toggleActivityAccordion(activityName) {
    const row = this.page.locator(`.activity-row:has-text("${activityName}"), tr:has-text("${activityName}")`).first();
    await row.waitFor({ state: 'visible' });
    await row.click();
    await this.page.waitForTimeout(200);
  }

  /**
   * Trigger PDF report generation.
   */
  async triggerPdfExport() {
    await this.exportPdfButton.waitFor({ state: 'visible' });
    await this.exportPdfButton.click();
  }

  /**
   * Captures a named screenshot artifact in the e2e/artifacts directory.
   * @param {string} filename
   */
  async captureArtifact(filename) {
    await this.page.screenshot({
      path: `e2e/artifacts/${filename}`,
      fullPage: false,
    });
  }
}
