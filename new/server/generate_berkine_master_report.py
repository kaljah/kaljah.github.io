"""
Groupement Berkine Master Publication Report Generator
======================================================
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
import argparse

# Ensure backend path is available
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
from services.master_report_engine import generate_master_publication_pdf


def build_master_pdf(
    output_pdf_path: str,
    start_year: int = 2022,
    end_year: int = 2022,
    gwp_standard: str = "AR5",
    language: str = "en",
) -> str:
    """Builds the Groupement Berkine Master Publication Report dynamically from live database records."""
    with app.app_context():
        buf = generate_master_publication_pdf(
            mode="regional",
            region_key="berkine",
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
        print(f"Groupement Berkine master report built successfully from database: {output_pdf_path}")
        return output_pdf_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Groupement Berkine Master Publication Report")
    parser.add_argument("--start-year", type=int, default=2022, help="Start year (default: 2022)")
    parser.add_argument("--end-year", type=int, default=2022, help="End year (default: 2022)")
    parser.add_argument("--lang", type=str, default="en", help="Language: 'en' or 'fr' (default: 'en')")
    parser.add_argument("--gwp", type=str, default="AR5", help="GWP standard: 'AR5' or 'SAR' (default: 'AR5')")
    parser.add_argument("--out", type=str, default=None, help="Output PDF file path")
    args = parser.parse_args()

    default_out = f"Groupement_Berkine_RY{args.start_year}_Master_Report.pdf" if args.start_year == args.end_year else f"Groupement_Berkine_{args.start_year}_{args.end_year}_Master_Report.pdf"
    out_pdf = os.path.abspath(args.out or os.path.join(os.path.dirname(__file__), "..", "..", default_out))
    
    build_master_pdf(out_pdf, start_year=args.start_year, end_year=args.end_year, gwp_standard=args.gwp, language=args.lang)
