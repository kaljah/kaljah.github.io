from playwright.sync_api import sync_playwright
import os
import json

def test_wizard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Monitor responses
        def on_response(response):
            if "upload/check" in response.url:
                print("UPLOAD/CHECK STATUS:", response.status)
                try:
                    data = response.json()
                    print("UPLOAD/CHECK DATA:", json.dumps(data, indent=2))
                except Exception as e:
                    print("Could not parse json:", e)
        page.on("response", on_response)
        
        # Login as superuser
        page.goto("http://localhost:5173/login")
        page.wait_for_selector("input[type='email']")
        page.fill("input[type='email']", "audit_superuser@ghg.com")
        page.fill("input[type='password']", "AuditPass!2026")
        page.click("button[type='submit']")
        page.wait_for_timeout(1500)
        print("Logged in. Current URL:", page.url)
        
        # Go to Scope 1 emissions
        page.goto("http://localhost:5173/emissions?scope=1")
        page.wait_for_timeout(1500)
        
        # Click Bulk Import button
        page.click("button:has-text('Bulk Import')")
        page.wait_for_timeout(1000)
        
        # Step 1: Click "Next"
        page.click("div[role='dialog'] button:has-text('Next')")
        page.wait_for_timeout(1000)
        
        # Step 2: Choose "Decimal point"
        page.click("button:has-text('Decimal point')")
        page.wait_for_timeout(500)
        
        # Set CSV file
        csv_path = os.path.abspath("berkine_2022_all_68_sources.csv")
        file_input = page.locator("input[type='file']")
        file_input.set_input_files(csv_path)
        page.wait_for_timeout(4000)
        
        browser.close()

if __name__ == "__main__":
    test_wizard()
