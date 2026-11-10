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
    
    # Look at facility dropdown
    fac_select = page.query_selector("select[name='facility_id'], select#facility_id")
    if not fac_select:
        # Check all custom dropdowns or native selects
        selects = page.query_selector_all("select")
        print("Selects found:", len(selects))
        for s in selects:
            print("Select id/name:", s.get_attribute("id"), s.get_attribute("name"))
            opts = [o.inner_text().strip() for o in s.query_selector_all("option")]
            print("  Options:", opts[:10])
            
    # Check process dropdown
    proc_select = page.query_selector("select[name='process_type'], select#process_type")
    if proc_select:
        print("Process options:", [o.inner_text().strip() for o in proc_select.query_selector_all("option")])
        
    browser.close()
