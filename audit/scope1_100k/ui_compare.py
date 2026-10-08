"""Compare what the UI rendered (ui_table_read.json) and the table's data feed with the database.

python ui_compare.py --db ui.db --read ui_table_read.json --base http://127.0.0.1:5000 --report ui_compare.json
"""
import argparse
import collections
import json
import re
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def num(cell):
    """Displayed number -> (value, half-unit of the last displayed digit)."""
    s = cell.replace(",", "").strip()
    m = re.match(r"^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", s)
    if not m:
        return None, None
    t = m.group(1)
    v = float(t)
    if "e" in t.lower():
        mant = t.lower().split("e")[0]
        dec = len(mant.split(".")[1]) if "." in mant else 0
        exp = int(t.lower().split("e")[1])
        return v, 0.5 * 10 ** (exp - dec)
    dec = len(t.split(".")[1]) if "." in t else 0
    return v, 0.5 * 10 ** (-dec)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--read", required=True)
    ap.add_argument("--base")
    ap.add_argument("--report", required=True)
    a = ap.parse_args()
    con = sqlite3.connect(a.db)
    con.row_factory = sqlite3.Row
    db = {r["equipment_id"]: dict(r) for r in con.execute(
        "SELECT e.*, f.name AS fac_name FROM emissions e LEFT JOIN facilities f ON f.id = e.facility_id")}
    d = json.load(open(a.read))
    H = [h.strip().upper() for h in d["heads"]]
    idx = {h: i for i, h in enumerate(H)}
    R = {"rendered_rows": 0, "mismatch": collections.Counter(), "examples": collections.defaultdict(list),
         "pages_identical_to_previous": [p["pager"] for p in d["pages"] if p.get("next_identical")],
         "duplicates_across_pages": 0}
    seen = collections.Counter()
    rendered = [(r, "page") for p in d["pages"] for r in p["rows"]] + [(r, "search") for f in d["found"] for r in f["rows"]]
    page_rows = [r for p in d["pages"] for r in p["rows"]]
    for r in page_rows:
        seen[r[idx["EQUIPMENT ID"]]] += 1
    R["duplicates_across_pages"] = sum(c - 1 for c in seen.values() if c > 1)

    def bad(kind, eq, disp, dbv):
        R["mismatch"][kind] += 1
        if len(R["examples"][kind]) < 8:
            R["examples"][kind].append({"equipment_id": eq, "displayed": disp, "db": dbv})

    for r, src in rendered:
        if len(r) < len(H) - 1:
            continue
        eq = r[idx["EQUIPMENT ID"]]
        rec = db.get(eq)
        R["rendered_rows"] += 1
        if not rec:
            bad("row_not_in_db", eq, r, None)
            continue
        if r[idx["PERIOD"]] != f"{rec['year']}-{rec['month']:02d}":
            bad("period", eq, r[idx["PERIOD"]], (rec["year"], rec["month"]))
        if r[idx["REGION"]] not in (rec["fac_name"], rec["region"]):
            bad("region_column", eq, r[idx["REGION"]], {"facility": rec["fac_name"], "region": rec["region"]})
        if (r[idx["ACTIVITY"]] or "") != (rec["activity"] or "") and r[idx["ACTIVITY"]] not in ("-", "—"):
            bad("activity", eq, r[idx["ACTIVITY"]], rec["activity"])
        if r[idx["EMISSION SOURCE"]] not in ((rec["group_name"] or ""), "-", "—"):
            bad("emission_source", eq, r[idx["EMISSION SOURCE"]], rec["group_name"])
        fuel = r[idx["ACTIVITY/FUEL"]]
        if fuel not in ("-", "—") and fuel != (rec["fuel_type"] or ""):
            bad("fuel", eq, fuel, rec["fuel_type"])
        if fuel in ("-", "—") and rec["fuel_type"]:
            bad("fuel_hidden", eq, fuel, rec["fuel_type"])
        q = r[idx["QUANTITY"]]
        qv, qtol = num(q)
        if rec["quantity"] is None:
            if q not in ("-", "—", ""):
                bad("quantity_shown_but_null", eq, q, None)
        else:
            if qv is None or abs(qv - rec["quantity"]) > qtol * 1.0001 + 1e-12:
                bad("quantity_value", eq, q, rec["quantity"])
            unit_disp = q.split(" ", 1)[1] if " " in q else ""
            if unit_disp.strip() != (rec["unit"] or "").strip():
                bad("quantity_unit", eq, q, rec["unit"])
        for col, field in (("CO₂ (T)", "co2_emissions"), ("CH₄ (T)", "ch4_emissions"), ("N₂O (T)", "n2o_emissions"),
                           ("TOTAL (TCO₂E)", "co2e_total")):
            v, tol = num(r[idx[col]])
            dbv = float(rec[field] or 0)
            if v is None or abs(v - dbv) > tol * 1.0001 + 1e-15:
                bad(field, eq, r[idx[col]], dbv)
            elif dbv > 0 and v == 0:
                R["mismatch"][f"{field}_displayed_as_zero"] += 1
        ft = r[idx["FACTOR TYPE"]]
        want = {"default": "Default", "specific": "Specific"}.get(rec["factor_source"])
        if rec["factor_source"] == "custom":
            want = "Custom" if rec["custom_factor_id"] else "Tier 2"
        if ft != want:
            bad("factor_type", eq, ft, rec["factor_source"])
        if "Pending" not in r[idx["TOTAL (TCO₂E)"]]:
            bad("status_badge", eq, r[idx["TOTAL (TCO₂E)"]], rec["status"])

    # full data feed of the table (same endpoint, offset paging), every record
    if a.base:
        import requests
        from harness import ADMIN_EMAIL, ADMIN_PASSWORD

        s = requests.Session()
        s.post(a.base + "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).raise_for_status()
        feed, off = [], 0
        while True:
            j = s.get(f"{a.base}/api/emissions?scope=1&limit=5000&offset={off}").json()
            rows = j.get("emissions") or j.get("data") or []
            feed += rows
            off += 5000
            if off >= j.get("total", 0) or not rows:
                break
        R["feed_records"] = len(feed)
        R["feed_unique_equipment"] = len({x.get("equipment_id") for x in feed})
        fm = collections.Counter()
        ex = collections.defaultdict(list)
        for x in feed:
            rec = db.get(x.get("equipment_id"))
            if not rec:
                fm["not_in_db"] += 1
                continue
            for jk, dk in (("co2_emissions", "co2_emissions"), ("ch4_emissions", "ch4_emissions"),
                           ("n2o_emissions", "n2o_emissions"), ("co2e_total", "co2e_total"), ("quantity", "quantity"),
                           ("unit", "unit"), ("year", "year"), ("month", "month"), ("status", "status"),
                           ("factor_source", "factor_source")):
                if jk in x and x[jk] != rec[dk] and not (isinstance(x[jk], float) and rec[dk] is not None
                                                          and abs(x[jk] - rec[dk]) <= 1e-12 * max(1, abs(rec[dk]))):
                    fm[jk] += 1
                    if len(ex[jk]) < 5:
                        ex[jk].append((x.get("equipment_id"), x[jk], rec[dk]))
        R["feed_mismatch"] = dict(fm)
        R["feed_examples"] = dict(ex)
        R["feed_keys"] = sorted(feed[0].keys()) if feed else []
    R["mismatch"] = dict(R["mismatch"])
    json.dump(R, open(a.report, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in R.items() if k not in ("examples", "feed_keys", "feed_examples")}, indent=1))


if __name__ == "__main__":
    main()
