from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5173/login")
    page.fill('input[type="email"]', "a@a")
    page.fill('input[type="password"]', "a")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)
    
    # Test submitting source 24
    res = page.evaluate('''async () => {
        const csrfRes = await fetch("/api/csrf-token");
        const csrfData = await csrfRes.json();
        
        const payload = {
            year: 2022,
            month: 12,
            facility_id: 37,
            process_type: "combustion",
            factor_source: "custom",
            custom_factor_id: 224,
            fuel: "HBNS - Leak \u2013 CPF Gas Processin EF",
            fuel_type: "HBNS - Leak \u2013 CPF Gas Processin EF",
            quantity: 1.0,
            unit: "Unit",
            equipment_id: "Leak \u2013 CPF Gas Processin",
            group_name: "HBNS - Equipment Leaks",
            status: "Verified",
            allow_duplicate: true
        };
        
        const postRes = await fetch("/api/emissions/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfData.csrf_token
            },
            body: JSON.stringify(payload)
        });
        
        return { status: postRes.status, body: await postRes.json() };
    }''')
    
    print("Result for Source 24:", json.dumps(res, indent=2))
    browser.close()
