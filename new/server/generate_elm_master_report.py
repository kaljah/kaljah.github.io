"""
El Merk (Block 208) Master Publication Report Generator
=======================================================
Compiles an exhaustive publication-grade PDF generated dynamically from live database records:
- Executive Cover Page & Institutional Framing
- Table of Contents & Technical Glossary
- Executive Summaries (GHG, Methane, Flaring Performance)
- Matplotlib Figures generated directly from DB
- Accompanying Analytical Chapters & Scorecard Tables
- Granular Facility Ledger Breakdowns
- Executive MRV Sign-off & Verification Certificate with SHA-256 Seal
"""

import os
import sys
import io

# Ensure backend path is available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
from services.master_report_engine import generate_master_publication_pdf


def build_elm_master_pdf(
    output_pdf_path: str,
    start_year: int = 2021,
    end_year: int = 2025,
    gwp_standard: str = "AR5",
    language: str = "en",
) -> str:
    """Builds the El Merk Master Publication Report dynamically from live database records."""
    with app.app_context():
        buf = generate_master_publication_pdf(
            mode="regional",
            region_key="elm",
            start_year=start_year,
            end_year=end_year,
            gwp_standard=gwp_standard,
            language=language,
        )
        dest_dir = os.path.dirname(os.path.abspath(output_pdf_path))
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        with open(output_pdf_path, "wb") as f:
            f.write(buf.getvalue())
        print(f"El Merk master report built successfully from database: {output_pdf_path}")
        return output_pdf_path


if __name__ == "__main__":
    out_pdf = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "El_Merk_2025_Annual_GHG_Report.pdf")
    )
    build_elm_master_pdf(out_pdf)
