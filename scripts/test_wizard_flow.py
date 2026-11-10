from playwright.sync_api import sync_playwright
import os

def test_wizard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Login as superuser
        page.goto("http://localhost:5173/login")
        page.wait_for_selector("input[type='email']")
        page.fill("input[type='email']", "audit_superuser@ghg.com")
        page.fill("input[type='password']", "AuditPass!2026")
        page.click("button[type='submit']")
        page.wait_for_timeout(1000)
        
        # Go to Scope 1 emissions
        page.goto("http://localhost:5173/emissions?scope=1")
        page.wait_for_timeout(1500)
        
        # Click Bulk Import button
        page.click("button:has-text('Bulk Import')")
        page.wait_for_timeout(1000)
        
        # Step 1: Calculation tier. Click "Next"
        page.click("div[role='dialog'] button:has-text('Next')")
        page.wait_for_timeout(1000)
        
        # Step 2: Choose "Decimal point"
        page.click("button:has-text('Decimal point')")
        page.wait_for_timeout(500)
        
        # Set CSV file
        csv_path = os.path.abspath("berkine_2022_all_68_sources.csv")
        file_input = page.locator("input[type='file']")
        file_input.set_input_files(csv_path)
        page.wait_for_timeout(2000)
        
        # Check overwrite checkbox
        chk = page.locator("label:has-text('Overwrite') input[type='checkbox']")
        if chk.count() > 0:
            chk.check()
            page.wait_for_timeout(2000)
            
        page.screenshot(path="screenshots/wizard_su_mapping.png")
        print("Captured wizard_su_mapping.png")
        
        # Find start import button
        start_btn = page.locator("div[role='dialog'] button:has-text('Import')")
        print("Start button text:", start_btn.first.inner_text())
        
        browser.close()

if __name__ == "__main__":
    test_wizard()
