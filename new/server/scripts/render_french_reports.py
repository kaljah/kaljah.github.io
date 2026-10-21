"""
Renders French Localized Master Publication Reports to High-Resolution Screenshots
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pypdfium2
from app import app
from services.master_report_engine import generate_master_publication_pdf

OUTPUT_DIR = "C:/Users/samsung/.gemini/antigravity/brain/dd96e698-aa0b-4016-a59d-85ecf47988c4/screenshots/report_pages_fr"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def render_report(mode: str, region: str, prefix: str):
    print(f"Generating French report for {mode} ({region})...")
    with app.app_context():
        buf = generate_master_publication_pdf(
            mode=mode,
            region_key=region,
            start_year=2023,
            end_year=2025,
            gwp_standard="AR5",
            language="fr"
        )
    pdf = pypdfium2.PdfDocument(buf.getvalue())
    for i, page in enumerate(pdf):
        img = page.render(scale=2.0).to_pil()
        out_file = os.path.join(OUTPUT_DIR, f"{prefix}_page_{i + 1}.png")
        img.save(out_file)
        print(f"  Saved {out_file}")
    pdf.close()

if __name__ == "__main__":
    render_report("regional", "hmd", "hmd_fr")
    render_report("national", "national", "national_fr")
    render_report("comparison", "hmd", "benchmark_fr")
    print("All French reports rendered successfully!")
