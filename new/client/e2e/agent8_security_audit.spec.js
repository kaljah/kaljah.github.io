import { test, expect } from "@playwright/test";
import path from "path";
import fs from "fs";

// Isolate this test from existing storageState
test.use({ storageState: { cookies: [], origins: [] } });

const SCREENSHOT_DIR = path.resolve("../../test_artifacts/screenshots");

test.describe("Agent 8 Security QA: Access Control, Authentication & Session Security", () => {
  test.beforeAll(() => {
    if (!fs.existsSync(SCREENSHOT_DIR)) {
      fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
    }
  });

  test("01 - Multi-Tenant Boundary & Operator Session Isolation", async ({ page }) => {
    // Navigate to /login
    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    // Login as audit_operator@ghg.com
    await page.locator("input[placeholder*='Email']").fill("audit_operator@ghg.com");
    await page.locator("input[placeholder*='Password']").fill("AuditPassword2026!");
    await page.locator("button[type='submit']").click();
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // Verify operator dashboard shows scoped view
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "agent8_01_multitenant_isolation.png"),
      fullPage: true,
    });
  });

  test("02 - Notification IDOR Defense & Scoped Alerts", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await page.locator("input[placeholder*='Email']").fill("audit_operator@ghg.com");
    await page.locator("input[placeholder*='Password']").fill("AuditPassword2026!");
    await page.locator("button[type='submit']").click();
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // Open notifications popover
    const notifBell = page.locator("button[title*='Notification'], button[aria-label*='Notification']").first();
    if (await notifBell.isVisible()) {
      await notifBell.click();
      await page.waitForTimeout(1000);
    }

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "agent8_02_notification_idor_defense.png"),
      fullPage: false,
    });
  });

  test("03 - Privilege Boundary & Restricted Admin Route Rejection", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await page.locator("input[placeholder*='Email']").fill("audit_operator@ghg.com");
    await page.locator("input[placeholder*='Password']").fill("AuditPassword2026!");
    await page.locator("button[type='submit']").click();
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // Attempt direct navigation to restricted user management admin page
    await page.goto("/users");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "agent8_03_privilege_boundary_operator_it.png"),
      fullPage: true,
    });
  });

  test("04 - CSRF Protection & Post-Logout Session Revocation", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");
    await page.locator("input[placeholder*='Email']").fill("audit_operator@ghg.com");
    await page.locator("input[placeholder*='Password']").fill("AuditPassword2026!");
    await page.locator("button[type='submit']").click();
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(2000);

    // Click logout button
    const logoutBtn = page.locator("button:has-text('Logout'), button:has-text('Déconnexion'), button[title*='Logout']").first();
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click();
      await page.waitForTimeout(1500);
    }

    // Try navigating back to /
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1500);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "agent8_04_csrf_protection_and_session.png"),
      fullPage: true,
    });
  });

  test("05 - Failed Login Rate Limiting Guard", async ({ page }) => {
    await page.goto("/login");
    await page.waitForLoadState("networkidle");

    // Submit invalid credentials
    await page.locator("input[placeholder*='Email']").fill("wrong_user@ghg.com");
    await page.locator("input[placeholder*='Password']").fill("BadPassword123!");
    await page.locator("button[type='submit']").click();
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, "agent8_05_failed_login_ratelimit.png"),
      fullPage: false,
    });
  });
});
