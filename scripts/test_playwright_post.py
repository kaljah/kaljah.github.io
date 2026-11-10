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
    
    # 2. Check in-page axios / fetch
    res = page.evaluate('''async () => {
        try {
            // Using window.fetch or the axios instance
            const csrfRes = await fetch("/api/csrf-token");
            const csrfData = await csrfRes.json();
            
            const postRes = await fetch("/api/emissions/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrfData.csrf_token
                },
                body: JSON.stringify({
                    year: 2022,
                    month: 1,
                    facility_id: 37,
                    process_type: "combustion",
                    fuel_type: "natural_gas",
                    quantity: 1000.0,
                    unit: "m3",
                    equipment_id: "TEST-BROWSER-01",
                    status: "Verified",
                    allow_duplicate: true
                })
            });
            const postData = await postRes.json();
            return { status: postRes.status, data: postData };
        } catch (e) {
            return { error: e.toString() };
        }
    }''')
    print("Browser evaluate result:", res)
    
    browser.close()
