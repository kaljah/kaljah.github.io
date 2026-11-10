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
    
    # Let's inspect the entire Scope 1 form DOM to see how fields are structured
    fields_info = page.evaluate('''() => {
        const inputs = Array.from(document.querySelectorAll('input, select, button')).map(el => ({
            tag: el.tagName,
            type: el.type || '',
            id: el.id || '',
            name: el.name || '',
            placeholder: el.placeholder || '',
            text: el.innerText || '',
            className: el.className || ''
        }));
        return inputs;
    }''')
    
    print(f"Total interactive elements: {len(fields_info)}")
    for f in fields_info:
        if f['type'] != 'hidden' and (f['placeholder'] or f['name'] or f['id'] or 'dropdown' in f['className'].lower()):
            print("Element:", f)
            
    browser.close()
