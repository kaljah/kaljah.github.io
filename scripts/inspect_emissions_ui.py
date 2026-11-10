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
    page.screenshot(path="screenshots/browser_scope1_form.png", full_page=True)
    
    # Inspect inputs, selects, labels
    print("Page URL:", page.url)
    selects = page.query_selector_all("select")
    print(f"Found {len(selects)} select elements:")
    for s in selects:
        name = s.get_attribute("name") or s.get_attribute("id") or "unnamed"
        options = [o.inner_text().strip() for o in s.query_selector_all("option")]
        print(f"  Select [{name}]: {options[:5]} (total {len(options)})")
        
    inputs = page.query_selector_all("input")
    print(f"\nFound {len(inputs)} input elements:")
    for inp in inputs:
        itype = inp.get_attribute("type")
        iname = inp.get_attribute("name") or inp.get_attribute("id") or inp.get_attribute("placeholder")
        print(f"  Input [{itype} - {iname}]")
        
    browser.close()
