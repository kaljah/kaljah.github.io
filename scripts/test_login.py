from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5173/login", timeout=15000)
    page.fill('input[type="email"]', "a@a")
    page.fill('input[type="password"]', "a")
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    print("URL after login:", page.url)
    page.screenshot(path="screenshots/after_login.png")
    print("Screenshot saved to screenshots/after_login.png")
    browser.close()
