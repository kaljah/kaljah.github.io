from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:5173/", timeout=15000)
    page.wait_for_timeout(2000)
    print("URL after load:", page.url)
    print("Content preview:")
    text = page.inner_text("body")
    print(text[:1000])
    page.screenshot(path="screenshots/browser_page_load.png")
    browser.close()
