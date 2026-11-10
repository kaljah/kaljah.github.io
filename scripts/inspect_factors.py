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
    
    # 2. Go to /emissions?scope=1
    page.goto("http://localhost:5173/emissions?scope=1")
    page.wait_for_timeout(2000)
    
    # 3. Select Region: click dropdown
    region_btn = page.locator("button.dropdown-selected:has-text('Select Region...')").first
    region_btn.click()
    page.wait_for_timeout(500)
    page.locator(".dropdown-menu-portal button:has-text('HBNS (Hassi Berkine South)')").first.click()
    page.wait_for_timeout(500)
    print("Region selected")
    
    # 4. Check Factor dropdown
    factor_btn = page.locator("button.dropdown-selected:has-text('Select factor')").first
    factor_btn.click()
    page.wait_for_timeout(500)
    factors = [b.inner_text().strip().replace('\n', ' - ') for b in page.query_selector_all(".dropdown-menu-portal button")]
    print(f"Factors available ({len(factors)}):", factors[:10])
    
    browser.close()
