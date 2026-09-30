"""BUG-113 repro: PDF export uses Helvetica, which has no subscript glyphs (own db 'browser_repro')."""
import sys, io
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client
c = api_client("browser_repro", "admin")
r = c.get("/api/reports/export?scope=all&year=2025")
pdf = r.data
import pdfplumber
with pdfplumber.open(io.BytesIO(pdf)) as p:
    fonts = {ch.get("fontname") for pg in p.pages for ch in pg.chars}
    text = "".join(pg.extract_text() or "" for pg in p.pages)
has_sub_font = any("DejaVu" in f or "Noto" in f or "Arial" in f for f in fonts)
ok = ("CO₂" in text or "CO2" in text) and "tCOne" not in text
print(f"HTTP {r.status_code}; fonts={sorted(fonts)[:4]}; 'tCOne' garbled in text: {'tCOne' in text}; expected readable CO2 labels")
sys.exit(0 if ok else 1)
