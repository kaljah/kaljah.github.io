"""Executive Brief PDF (Dashboard 'Export Executive Brief', All Years) aggregates every status and every year,
but labels itself 'FISCAL YEAR <current>' and 'Total verified records'. Replays the generator's data request
(GET /api/emissions?limit=5000, no year/status) and checks the client source. Exits 1 while the bug exists.
Real PDF evidence: audit/work/F/exec_brief_allyears.pdf (+ brief.txt) captured via audit/work/F/pdf1.mjs."""
import sys, re, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
rows = c.get("/api/emissions/?limit=5000").get_json()
rows = rows.get("emissions") or rows.get("data") or rows
from collections import Counter
st = Counter(r["status"] for r in rows)
years = sorted({r["year"] for r in rows if r["year"]})
tot_all = sum(float(r["co2e_total"] or 0) for r in rows if r["scope"] in (1, 2))
ver = con.execute("select (select sum(co2e_total) from emissions where status='Verified')+(select sum(co2e) from scope2_emissions where status='Verified')").fetchone()[0]
src = open(r"C:/Users/samsung/Desktop/H2/new/client/src/utils/ModernReportGenerator.js", encoding="utf-8").read()
dash = open(r"C:/Users/samsung/Desktop/H2/new/client/src/pages/DashboardEnhanced.jsx", encoding="utf-8").read()
status_filtered = bool(re.search(r"status\s*===?\s*[\"']Verified", src))
passes_undefined = 'year: currentYear !== "all" ? currentYear : undefined' in dash
print(f"records fed to PDF: {len(rows)} statuses={dict(st)} years={years}")
print(f"PDF S1+S2 basis (stored co2e) = {tot_all:,.2f} ; dashboard Verified S1+S2 = {ver:,.2f}")
print(f"generator filters Verified: {status_filtered} ; dashboard passes year=undefined for All Years (-> 'FISCAL YEAR {__import__('datetime').date.today().year}'): {passes_undefined}")
bad = (set(st) - {"Verified"}) and not status_filtered or passes_undefined
sys.exit(1 if bad else 0)
