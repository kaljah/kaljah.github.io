"""Dashboard source split mis-classifies process types (fuel_gas -> Other; pneumatic/tank/dehydrator/unloading/
completions/agr/drilling vents -> Other; mobile combustion -> 'Stationary Combustion'). Exits 1 while bug exists."""
import sys, sqlite3; sys.path.insert(0, r"C:/Users/samsung/Desktop/H2/audit/tools")
from auditlib import api_client, db_path
c = api_client("repro_F", "admin")
con = sqlite3.connect(db_path("repro_F"))
# Independent classification (API Compendium 2021 source categories): combustion / flaring / vented / fugitive / other
COMB = ("combustion", "fuel_gas", "mobile", "stationary")
FLARE = ("flar", "flare")
VENT = ("vent", "pneumatic", "tank_", "dehydrator", "unloading", "completion", "agr", "drilling", "loading", "blowdown")
def cls(pt):
    p = (pt or "").lower()
    if any(k in p for k in FLARE): return "flaring"
    if any(k in p for k in COMB): return "combustion"
    if "fugitive" in p: return "fugitive"
    if any(k in p for k in VENT): return "venting"
    return "other"
exp = {}
for pt, v in con.execute("select process_type, sum(co2e_total) from emissions where status='Verified' group by 1"):
    exp[cls(pt)] = exp.get(cls(pt), 0) + (v or 0)
S = c.get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all").get_json()["summary"]
got = {k: sum(r[k] for r in S) for k in ("combustion", "flaring", "venting", "other")}
print("expected:", {k: round(v, 2) for k, v in exp.items()})
print("API     :", {k: round(v, 2) for k, v in got.items()})
fuel_gas = con.execute("select sum(co2e_total) from emissions where status='Verified' and process_type='fuel_gas'").fetchone()[0]
print(f"fuel_gas combustion CO2e={fuel_gas:,.2f} reported under 'Other Sources' ; API other={got['other']:,.2f} expected other={exp.get('other',0):,.2f}")
sys.exit(1 if abs(got["other"] - exp.get("other", 0)) > 1 else 0)
