from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Create context with standard 1920x1080 viewport for high quality UI captures
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()
        
        # 1. Login
        print("Logging in to NeoCarbon web platform...")
        page.goto("http://localhost:5173/login", timeout=15000)
        page.fill('input[type="email"]', "a@a")
        page.fill('input[type="password"]', "a")
        page.click('button[type="submit"]')
        page.wait_for_timeout(2000)
        
        # 2. Scope 1 Form (Manual Entry Demonstration)
        print("Navigating to Scope 1 Manual Entry Form...")
        page.goto("http://localhost:5173/emissions?scope=1", timeout=15000)
        page.wait_for_timeout(2000)
        
        # Select HBNS
        region_btn = page.locator("button.dropdown-selected:has-text('Select Region...')").first
        if region_btn.is_visible():
            region_btn.click()
            page.wait_for_timeout(500)
            hbns_item = page.locator(".dropdown-menu-portal button:has-text('HBNS (Hassi Berkine South)')").first
            if hbns_item.is_visible():
                hbns_item.click()
                page.wait_for_timeout(500)
                
        # Fill Year
        year_input = page.locator("input[type='number']").first
        if year_input.is_visible():
            year_input.fill("2022")
            
        # Select Month (Dec or 12)
        month_select = page.locator("select.component-select").first
        if month_select.is_visible():
            month_select.select_option("12")
            
        # Equipment ID & Group
        eq_input = page.locator("input[placeholder*='e.g. T-101']").first
        if eq_input.is_visible():
            eq_input.fill("Heater 4")
            
        grp_input = page.locator("input[placeholder*='e.g. West facility']").first
        if grp_input.is_visible():
            grp_input.fill("CPF Separation Train")
            
        # Quantity
        qty_input = page.locator("input[placeholder*='0.00']").first
        if qty_input.is_visible():
            qty_input.fill("24069698.74")
            
        page.wait_for_timeout(1000)
        page.screenshot(path="screenshots/browser_scope1_manual_entry.png", full_page=False)
        print("Saved screenshots/browser_scope1_manual_entry.png")
        
        # 3. Manage Data - Sources Tab
        print("Navigating to Manage Data -> Sources...")
        page.goto("http://localhost:5173/manage-data", timeout=15000)
        page.wait_for_timeout(2000)
        
        # Click Sources tab
        sources_tab = page.locator("button:has-text('Sources'), [role='tab']:has-text('Sources')").first
        if sources_tab.is_visible():
            sources_tab.click()
            page.wait_for_timeout(1500)
            
        page.screenshot(path="screenshots/browser_manage_data_sources.png", full_page=False)
        print("Saved screenshots/browser_manage_data_sources.png")
        
        # 4. Dashboard (2022 Live View)
        print("Navigating to Dashboard...")
        page.goto("http://localhost:5173/", timeout=15000)
        page.wait_for_timeout(2500)
        
        # Try to select year 2022 in filter if present
        year_filter = page.locator("select:has-text('2022'), button:has-text('2022')").first
        if year_filter.is_visible():
            try:
                year_filter.select_option("2022")
                page.wait_for_timeout(2000)
            except Exception:
                pass
                
        page.screenshot(path="screenshots/browser_dashboard_2022.png", full_page=False)
        print("Saved screenshots/browser_dashboard_2022.png")
        
        # 5. Reports Page
        print("Navigating to Reports...")
        page.goto("http://localhost:5173/reports", timeout=15000)
        page.wait_for_timeout(2500)
        page.screenshot(path="screenshots/browser_reports_2022.png", full_page=False)
        print("Saved screenshots/browser_reports_2022.png")
        
        browser.close()
        print("Browser automation run completed successfully.")

if __name__ == "__main__":
    run()
