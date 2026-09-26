"""Equity allocation ignores effective dates; equity share POST accepts out-of-range pct."""
import sys
sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import make_db, api_client, sql
DB="repro_BUG046"; make_db(DB, overwrite=True)
a = api_client(DB,"admin")
sql(DB,"update facility_equity_shares set effective_end_date='2023-12-31' where id=1")  # Sonatrach 51% ends 2023
a.post("/api/equity/shares", json={"facility_id":169,"partner_id":1,"equity_share_pct":70,"effective_start_date":"2024-01-01"})
tot = sql(DB,"select sum(co2e_total) s from emissions where facility_id=169 and status='Verified' and year=2025")[0]["s"]
al = a.get("/api/equity/allocation?year=2025&facility_id=169").get_json()[0]
son = [p for p in al["partners"] if p["partner_code"]=="SH"][0]
print(f"2025 total verified co2e (SQL) = {tot:.2f}")
print(f"expected Sonatrach pct 70 (share effective 2024-01-01), alloc = {tot*0.70:.2f}")
print(f"actual   Sonatrach pct {son['equity_pct']}, alloc = {son['allocated_co2e']}")
r = a.post("/api/equity/shares", json={"facility_id":169,"partner_id":2,"equity_share_pct":500,"effective_start_date":"2030-01-01"})
r2 = a.post("/api/equity/shares", json={"facility_id":169,"partner_id":2,"equity_share_pct":-50,"effective_start_date":"2031-01-01"})
print(f"expected 400 for equity_share_pct=500 / -50; actual {r.status_code} / {r2.status_code}")
sys.exit(1 if (son["equity_pct"] != 70 or r.status_code == 200 or r2.status_code == 200) else 0)
