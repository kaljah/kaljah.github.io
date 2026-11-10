from playwright.sync_api import sync_playwright

def test_logins():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        users = [
            ("admin@ghg.com", "AuditPass!2026", "admin"),
            ("audit_superuser@ghg.com", "AuditPass!2026", "superuser"),
            ("audit_operator@ghg.com", "AuditPass!2026", "user"),
        ]
        
        for email, pwd, role in users:
            page.goto("http://localhost:5173/login")
            page.wait_for_selector("input[type='email']")
            page.fill("input[type='email']", email)
            page.fill("input[type='password']", pwd)
            page.click("button[type='submit']")
            page.wait_for_timeout(1500)
            url = page.url
            print(f"Role: {role:10s} | Email: {email:25s} | Result URL: {url}")
            # Clear cookies / storage for next user
            page.context.clear_cookies()
            page.evaluate("() => localStorage.clear()")
            
        browser.close()

if __name__ == "__main__":
    test_logins()
