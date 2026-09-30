import os
from playwright.sync_api import sync_playwright
import pypdfium2 as pdfium

def main():
    resume_html = os.path.abspath("neocarbon_resume_page.html")
    resume_pdf = os.path.abspath("neocarbon_resume_page.pdf")
    resume_png = os.path.abspath("preview_resume_page.png")
    
    uploaded_pdf = "C:/Users/samsung/.gemini/antigravity/brain/e7993666-78c6-4598-a534-0fcc16ef590d/.user_uploaded/media_1790676404712.pdf"
    complete_pdf = os.path.abspath("neocarbon_flyer_complete_4pages.pdf")

    print("1. Rendering neocarbon_resume_page.html...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1240, "height": 1754}, device_scale_factor=2)
        page.goto(f"file:///{resume_html.replace(os.sep, '/')}", wait_until="networkidle")

        # Take high-resolution screenshot of .page-sheet
        resume_elem = page.locator(".page-sheet").first
        resume_elem.screenshot(path=resume_png)
        print(f"Saved PNG preview to: {resume_png}")

        # Render 1-page PDF
        page.pdf(
            path=resume_pdf,
            format="A4",
            print_background=True,
            margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
        )
        print(f"Saved 1-page PDF to: {resume_pdf}")
        browser.close()

    print("2. Merging uploaded flyer with new résumé page...")
    merged = pdfium.PdfDocument.new()

    doc_orig = pdfium.PdfDocument(uploaded_pdf)
    print(f"Original flyer pages: {len(doc_orig)}")
    merged.import_pages(doc_orig)

    doc_resume = pdfium.PdfDocument(resume_pdf)
    print(f"Resume pages: {len(doc_resume)}")
    merged.import_pages(doc_resume)

    merged.save(complete_pdf)
    print(f"Saved 4-page complete flyer to: {complete_pdf}")

    # Verify final page count
    final_doc = pdfium.PdfDocument(complete_pdf)
    print(f"Final merged document page count: {len(final_doc)}")

if __name__ == "__main__":
    main()
