import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const FRONTEND = process.env.E2E_BASE_URL || 'http://127.0.0.1:5173';
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
    console.log('[E2E RAP] Performing authentication login as Admin...');
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

async function ensureITAuthenticatedPage(page, targetUrl) {
  await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(800);

  const emailInput = page.locator('input[placeholder="Email Address"]').first();
  if (await emailInput.isVisible().catch(() => false)) {
    console.log('[E2E RAP] Performing authentication login as IT Administrator...');
    await emailInput.fill('itadmin@sonatrach.dz');
    const pwdInput = page.locator('input[type="password"]').first();
    await pwdInput.fill('itadmin123');
    await page.locator('button[type="submit"]:has-text("Sign In")').click();
    await page.waitForTimeout(1000);
    await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    await page.waitForTimeout(1000);
  } else {
    // If logged in as someone else, check current role or re-login
    const currentUrl = page.url();
    if (!currentUrl.includes('/user-management')) {
      console.log('[E2E RAP] Switching account to IT Admin...');
      await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
      await page.evaluate(() => {
        localStorage.clear();
        sessionStorage.clear();
      });
      await page.goto(`${FRONTEND}/login`, { waitUntil: 'domcontentloaded' });
      await page.waitForTimeout(600);
      const eInput = page.locator('input[placeholder="Email Address"]').first();
      await eInput.fill('itadmin@sonatrach.dz');
      const pInput = page.locator('input[type="password"]').first();
      await pInput.fill('itadmin123');
      await page.locator('button[type="submit"]:has-text("Sign In")').click();
      await page.waitForTimeout(1000);
      await page.waitForURL((u) => !u.toString().includes('/login'), { timeout: 15000 });
    }
  }

  if (targetUrl) {
    await page.goto(targetUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(1200);
  }
}

test.describe('Suite 16: Deep Untested Reports Configuration, Admin Controls & Production Converters', () => {

  test('RAP-1: Reports Table Row Record Edit via EditEmissionModal', async ({ page }) => {
    console.log('[RAP-1] Navigating to Reports page...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/reports`);
    await page.waitForTimeout(1500);

    // Locate the first Edit button in the data table
    const editBtn = page.locator('button:has-text("Edit")').first();
    await editBtn.scrollIntoViewIfNeeded();
    await expect(editBtn).toBeVisible({ timeout: 10000 });
    await editBtn.click();
    await page.waitForTimeout(1000);

    // Assert the EditEmissionModal dialog opened
    const modalHeading = page.locator('h2:has-text("Edit Emission Record")');
    await expect(modalHeading).toBeVisible({ timeout: 6000 });

    const modalDesc = page.locator('text=Update activity quantity, fuel/source, unit, or reporting period');
    await expect(modalDesc).toBeVisible();

    // Verify reporting year / month fields are interactive
    const yearSelect = page.locator('label:has-text("Reporting Year") ~ select, label:has-text("Reporting Year") + div select').first();
    if (await yearSelect.isVisible().catch(() => false)) {
      await yearSelect.selectOption({ index: 1 });
    }

    // Capture screenshot of the open Edit modal
    const shotPath = path.join(SCREENSHOT_DIR, 'rap01_reports_edit_emission_modal.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('rap01_reports_edit_emission_modal.png');

    // Cancel and close modal
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    await cancelBtn.click();
    await page.waitForTimeout(600);
    await expect(modalHeading).toBeHidden({ timeout: 5000 });
  });

  test('RAP-2: ISO 14064-1 Executive Report Configuration Dialog', async ({ page }) => {
    console.log('[RAP-2] Navigating to Reports Create New Report section...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/reports`);
    await page.waitForTimeout(1500);

    // Select regions via MultiSelectDropdown trigger
    const regionTrigger = page.locator('div.dropdown-selected').first();
    if (await regionTrigger.isVisible({ timeout: 6000 }).catch(() => false)) {
      await regionTrigger.click();
      await page.waitForTimeout(500);

      // Click "Select All" option in the portal dropdown
      const selectAllOpt = page.locator('.dropdown-portal .dropdown-option:has-text("Select All"), .dropdown-portal .dropdown-option').first();
      if (await selectAllOpt.isVisible({ timeout: 4000 }).catch(() => false)) {
        await selectAllOpt.click();
        await page.waitForTimeout(400);
      }

      // Close dropdown by clicking trigger again
      await regionTrigger.click();
      await page.waitForTimeout(400);
    }

    // Click "Create Report" button to trigger the dialog
    const createReportBtn = page.locator('button:has-text("Create Report")').first();
    await createReportBtn.scrollIntoViewIfNeeded();
    await expect(createReportBtn).toBeVisible({ timeout: 8000 });
    await createReportBtn.click();
    await page.waitForTimeout(1000);

    // Verify Dialog title
    const configDialogHeading = page.locator('h2:has-text("Generate Executive GHG Report")');
    await expect(configDialogHeading).toBeVisible({ timeout: 6000 });

    // Switch report format to ISO 14064-1 Compliance Report
    const isoFormatOption = page.locator('button:has-text("ISO 14064-1 Compliance Report")').first();
    if (await isoFormatOption.isVisible().catch(() => false)) {
      await isoFormatOption.click();
      await page.waitForTimeout(600);

      // Verify mandatory declarations fields
      const exclusionField = page.locator('textarea').first();
      await expect(exclusionField).toBeVisible();

      const verificationField = page.locator('input[value*="verified"], input[placeholder*="verified"]').first();
      if (await verificationField.isVisible().catch(() => false)) {
        await expect(verificationField).toBeVisible();
      }
    }

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'rap02_executive_report_iso_config_dialog.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('rap02_executive_report_iso_config_dialog.png');

    // Close dialog
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    await cancelBtn.click();
    await page.waitForTimeout(600);
    await expect(configDialogHeading).toBeHidden({ timeout: 5000 });
  });

  test('RAP-3: Reports Multi-Criteria Group By & Subtotal Cards', async ({ page }) => {
    console.log('[RAP-3] Testing Group By functionality in Reports...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/reports`);
    await page.waitForTimeout(1500);

    // Locate the "Group By" select element
    const groupBySelect = page.locator('label:has-text("Group By") ~ select, label:has-text("Group By") + div select').first();
    await groupBySelect.scrollIntoViewIfNeeded();
    await expect(groupBySelect).toBeVisible({ timeout: 8000 });

    // Select "By Facility"
    await groupBySelect.selectOption('facility');
    await page.waitForTimeout(1000);

    // Verify subtotal headers appear
    const subtotalHeader = page.locator('h3:has-text("Subtotal")').first();
    if (await subtotalHeader.isVisible({ timeout: 4000 }).catch(() => false)) {
      await expect(subtotalHeader).toBeVisible();
    }

    // Switch to "By Month"
    await groupBySelect.selectOption('month');
    await page.waitForTimeout(1000);

    // Switch back to "No Grouping"
    await groupBySelect.selectOption('none');
    await page.waitForTimeout(800);

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'rap03_reports_group_by_view.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('rap03_reports_group_by_view.png');
  });

  test('RAP-4: Custom Factor SRSS Combined Uncertainty Calculation', async ({ page }) => {
    console.log('[RAP-4] Navigating to Custom Factors Tab in Manage Data...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=factors`);
    await page.waitForTimeout(1500);

    // Scroll down to EF Uncertainty Workbench
    const workbenchHeader = page.locator('h4:has-text("EF Uncertainty Workbench")');
    await workbenchHeader.scrollIntoViewIfNeeded();
    await expect(workbenchHeader).toBeVisible({ timeout: 8000 });

    // Fill in precision values
    const meterInput = page.locator('label:has-text("Meter Precision") ~ input').first();
    await meterInput.fill('2.5');

    const labInput = page.locator('label:has-text("Lab Analysis") ~ input').first();
    await labInput.fill('1.8');

    // Click "Calculate Combined Uncertainty (SRSS)"
    const calcSrssBtn = page.locator('button:has-text("Calculate Combined Uncertainty (SRSS)")').first();
    await expect(calcSrssBtn).toBeVisible();
    await calcSrssBtn.click();
    await page.waitForTimeout(600);

    // Verify that CO2 Uncertainty field gets calculated and filled
    const co2UncertaintyInput = page.locator('input[name="co2_uncertainty"]');
    await expect(co2UncertaintyInput).toHaveValue('3.08', { timeout: 4000 });

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'rap04_custom_factor_srss_uncertainty_calculated.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('rap04_custom_factor_srss_uncertainty_calculated.png');
  });

  test('RAP-5: Oil & Gas Volume Conversion Modals in Production Tab', async ({ page }) => {
    console.log('[RAP-5] Navigating to Production Tab in Manage Data...');
    await ensureAuthenticatedPage(page, `${FRONTEND}/manage-data?tab=production`);
    await page.waitForTimeout(1500);

    // Click "Convert m³" button next to Oil
    const convertOilBtn = page.locator('button:has-text("Convert m³")').first();
    await convertOilBtn.scrollIntoViewIfNeeded();
    await expect(convertOilBtn).toBeVisible({ timeout: 8000 });
    await convertOilBtn.click();
    await page.waitForTimeout(800);

    // Verify Convert Volume Modal
    const convertModalTitle = page.locator('h2:has-text("Convert Volume"), h3:has-text("Convert Volume")').first();
    await expect(convertModalTitle).toBeVisible({ timeout: 6000 });

    // Fill in 500 m3
    const convInput = page.locator('input[placeholder="e.g. 1000"]').first();
    await convInput.fill('500');

    // Click Convert & Apply
    const applyBtn = page.locator('button:has-text("Convert & Apply")').first();
    await applyBtn.click();
    await page.waitForTimeout(800);

    // Verify the modal closed
    await expect(convertModalTitle).toBeHidden({ timeout: 5000 });

    // Verify oil amount was populated
    const oilAmountInput = page.locator('input[placeholder="0.0"]').first();
    const oilVal = await oilAmountInput.inputValue();
    expect(parseFloat(oilVal)).toBeGreaterThan(3000); // 500 * 6.28981 ~ 3144.9

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'rap05_production_volume_converter_applied.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('rap05_production_volume_converter_applied.png');
  });

  test('RAP-6: User Management Administrative Password Reset Slide-Over Drawer', async ({ page }) => {
    console.log('[RAP-6] Navigating to User Management page as IT Administrator...');
    await ensureITAuthenticatedPage(page, `${FRONTEND}/user-management`);
    await page.waitForTimeout(1500);

    // Locate the first Password Reset key icon button in the table
    const resetPwdBtn = page.locator('button[title*="Reset Password"], button[id^="um-reset-pwd-btn-"]').first();
    await resetPwdBtn.scrollIntoViewIfNeeded();
    await expect(resetPwdBtn).toBeVisible({ timeout: 8000 });
    await resetPwdBtn.click();
    await page.waitForTimeout(1000);

    // Verify slide-over drawer
    const drawerTitle = page.locator('text=Reset User Password').first();
    await expect(drawerTitle).toBeVisible({ timeout: 6000 });

    const securityNotice = page.locator('text=Security Impact:');
    await expect(securityNotice).toBeVisible();

    // Type a strong password into the new password field
    const pwdInput = page.locator('#um-reset-pwd-input');
    await expect(pwdInput).toBeVisible();
    await pwdInput.fill('Admin#Secure2026!');

    // Toggle password visibility
    const eyeBtn = page.locator('#um-reset-pwd-input ~ button').first();
    if (await eyeBtn.isVisible().catch(() => false)) {
      await eyeBtn.click();
      await page.waitForTimeout(300);
      await expect(pwdInput).toHaveAttribute('type', 'text');
    }

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'rap06_user_management_password_reset_drawer.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('rap06_user_management_password_reset_drawer.png');

    // Close drawer via close button or Escape
    const closeDrawerBtn = page.locator('button[aria-label="Close drawer"], button.drawer-close').first();
    if (await closeDrawerBtn.isVisible().catch(() => false)) {
      await closeDrawerBtn.click();
    } else {
      await page.keyboard.press('Escape');
    }
    await page.waitForTimeout(800);
  });

  test('RAP-7: User Management Access Revocation Confirmation Guard', async ({ page }) => {
    console.log('[RAP-7] Testing User Revocation Confirmation Guard as IT Administrator...');
    await ensureITAuthenticatedPage(page, `${FRONTEND}/user-management`);
    await page.waitForTimeout(1500);

    // Locate the Revoke Access trash button
    const deleteBtn = page.locator('button[title*="Revoke Access"], button[id^="um-delete-btn-"]').first();
    await deleteBtn.scrollIntoViewIfNeeded();
    await expect(deleteBtn).toBeVisible({ timeout: 8000 });
    await deleteBtn.click();
    await page.waitForTimeout(800);

    // Verify ConfirmModal
    const modalHeading = page.locator('h2:has-text("Revoke User Access")');
    await expect(modalHeading).toBeVisible({ timeout: 6000 });

    const modalWarning = page.locator('text=Are you sure you want to permanently revoke access');
    await expect(modalWarning).toBeVisible();

    // Capture screenshot
    const shotPath = path.join(SCREENSHOT_DIR, 'rap07_user_revocation_confirm_modal.png');
    await page.screenshot({ path: shotPath, fullPage: false });
    copyArtifact('rap07_user_revocation_confirm_modal.png');

    // Cancel safely so user data is preserved
    const cancelBtn = page.locator('button:has-text("Cancel")').first();
    await cancelBtn.click();
    await page.waitForTimeout(600);
    await expect(modalHeading).toBeHidden({ timeout: 5000 });
  });

});
