"""Compare the records stored by the Phase 2 CSV run (gb_ry2022_phase2_csv.py) with the Phase 1 engine results and
the report's printed figures.

    cd new/server && python scripts/gb_ry2022_phase2_compare.py <phase2 out folder>

Writes <out>/phase2_comparison.csv and prints the rows that differ.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.dirname(HERE)
sys.path.insert(0, SERVER)
sys.path.insert(0, os.path.join(SERVER, "tests"))
from calculations.constants import GWP_AR4  # noqa: E402
import gb_ry2022_cases as C  # noqa: E402

out = sys.argv[1]
res = json.load(open(os.path.join(out, "phase2_results.json"), encoding="utf-8"))
recs = res["readback"]["scope1"]["emissions"]
by_tag = {r["equipment_id"]: r for r in recs}
s2 = {r["facility_id"]: r for r in res["readback"]["scope2"]}
CODE = {"HBNS": "HBNS", "El Merk": "EMK"}
FID = {"HBNS": 1, "El Merk": 2}


def pct(a, b):
    return None if a is None or not b else (a - b) / b * 100.0


rows = []
for s in C.SOURCES:
    if s["kind"] != "reproduce":
        continue
    eng = C.run_source(s, GWP_AR4)
    if s["payload"][0] == "scope2":
        r = s2.get(FID[s["site"]])
        stored = {"co2": r and r["co2"], "ch4": r and r["ch4"], "n2o": r and r["n2o"], "co2e": r and r["co2e"],
                  "co2e_market": r and r["co2e_market_based"]}
    else:
        r = by_tag.get(f"{CODE[s['site']]}-{s['name']}")
        stored = {"co2": r and r["co2_emissions"], "ch4": r and r["ch4_emissions"], "n2o": r and r["n2o_emissions"],
                  "co2e": r and r["co2e_total"]}
    row = {"site": s["site"], "module": s["module"], "source": s["name"], "found": bool(r),
           "fuel_stored": (r or {}).get("fuel") or (r or {}).get("grid_region"), "status": (r or {}).get("status")}
    for g in ("co2", "ch4", "n2o", "co2e"):
        row[f"{g}_printed"] = s["printed"].get(g)
        row[f"{g}_engine"] = eng[g]
        row[f"{g}_csv"] = stored[g]
        row[f"{g}_csv_vs_engine_pct"] = pct(stored[g], eng[g])
        row[f"{g}_csv_vs_printed_pct"] = pct(stored[g], s["printed"].get(g))
    if "co2e_market" in stored:
        row["co2e_market_csv"] = stored["co2e_market"]
    rows.append(row)

with open(os.path.join(out, "phase2_comparison.csv"), "w", newline="", encoding="utf-8") as fh:
    cols = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    w = csv.DictWriter(fh, fieldnames=cols)
    w.writeheader()
    w.writerows(rows)

print(f"{'site':8} {'source':28} {'gas':5} {'printed':>12} {'engine':>12} {'csv':>12} {'csv/eng%':>9} {'csv/pr%':>8}")
for r in rows:
    if not r["found"]:
        print(f"{r['site']:8} {r['source']:28} NOT STORED")
        continue
    for g in ("co2", "ch4", "n2o", "co2e"):
        d = r[f"{g}_csv_vs_engine_pct"]
        if d is not None and abs(d) > 0.05:
            f = lambda v: "" if v is None else f"{v:,.3f}"  # noqa: E731
            print(f"{r['site']:8} {r['source'][:28]:28} {g:5} {f(r[g + '_printed']):>12} {f(r[g + '_engine']):>12} "
                  f"{f(r[g + '_csv']):>12} {d:+9.2f} {'' if r[g + '_csv_vs_printed_pct'] is None else format(r[g + '_csv_vs_printed_pct'], '+8.2f')}")
for site in ("HBNS", "El Merk"):
    tot_csv = sum((r["co2e_csv"] or 0) for r in rows if r["site"] == site)
    tot_eng = sum(r["co2e_engine"] for r in rows if r["site"] == site)
    print(f"{site}: reproduced sources CO2e csv {tot_csv:,.1f} engine {tot_eng:,.1f} ({pct(tot_csv, tot_eng):+.3f} %)")
