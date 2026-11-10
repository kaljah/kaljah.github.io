from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    # 1. Login
    page.goto("http://localhost:5173/login")
    page.fill('input[type="email"]', "a@a")
    page.fill('input[type="password"]', "a")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    
    # 2. Go to /manage-data
    page.goto("http://localhost:5173/manage-data")
    page.wait_for_timeout(2000)
    page.screenshot(path="screenshots/browser_manage_data.png", full_page=True)
    
    # Check tabs on manage-data
    tabs = [b.inner_text().strip() for b in page.query_selector_all("button[role='tab'], .tab-button, [class*='tab']")]
    print("Manage Data Tabs:", [t for t in tabs if t])
    
    # 3. Go to /reports
    page.goto("http://localhost:5173/reports")
    page.wait_for_timeout(2000)
    page.screenshot(path="screenshots/browser_reports.png", full_page=True)
    print("Reports URL:", page.url)
    
    browser.close()
