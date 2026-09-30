import os
import sys
from playwright.sync_api import sync_playwright

def render():
    html_path = os.path.abspath("neocarbon_software_flyer.html")
    pdf_path = os.path.abspath("neocarbon_software_flyer.pdf")
    p1_img = os.path.abspath("preview_flyer_page_1.png")
    p2_img = os.path.abspath("preview_flyer_page_2.png")

    print(f"Loading {html_path}...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 1754}, device_scale_factor=2)
        
        page.goto(f"file:///{html_path.replace(os.sep, '/')}", wait_until="networkidle")
        
        # Hide the control-bar for screenshots
        page.evaluate("document.querySelector('.control-bar').style.display = 'none'")

        # Screenshot Page 1
        page1 = page.locator("#page-1")
        page1.screenshot(path=p1_img)
        print(f"Saved {p1_img}")

        # Screenshot Page 2
        page2 = page.locator("#page-2")
        page2.screenshot(path=p2_img)
        print(f"Saved {p2_img}")

        # Generate Print PDF
        page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
        )
        print(f"Saved {pdf_path}")

        browser.close()

if __name__ == "__main__":
    render()
