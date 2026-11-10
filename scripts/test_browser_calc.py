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
    
    # Test submitting Heater 4 with custom factor 101
    res = page.evaluate('''async () => {
        const csrfRes = await fetch("/api/csrf-token");
        const csrfData = await csrfRes.json();
        
        const payload = {
            year: 2022,
            month: 12,
            facility_id: 37,
            process_type: "combustion",
            factor_source: "custom",
            custom_factor_id: 101,
            fuel: "HBNS Fuel Gas",
            fuel_type: "natural_gas",
            quantity: 24069698.74,
            unit: "m3",
            equipment_id: "Heater 4",
            group_name: "CPF",
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
    
    print("Result for Heater 4:", json.dumps(res, indent=2))
    
    # Clean up test record if inserted
    if res.get("status") == 201:
        rec_id = res["body"].get("id")
        print(f"Record {rec_id} inserted, cleaning up...")
        import sqlite3
        conn = sqlite3.connect("new/server/ghg_app.db")
        conn.cursor().execute("DELETE FROM emissions WHERE id=?", (rec_id,))
        conn.commit()
        conn.close()
        
    browser.close()
