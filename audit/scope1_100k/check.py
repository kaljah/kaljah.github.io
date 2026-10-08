"""Compare an imported database with expected.jsonl.

python check.py --db run.db --expected out/expected.jsonl --csv out/scope1_audit_100k.csv \
                [--skipped skipped.json] --report report.json

Checks, per row:
  acceptance     accepted rows vs the expectation (accept / reject / ambiguous)
  oracle         CO2, CH4, N2O and CO2e against the independent oracle (relative tolerance 1e-4)
  metamorphic    within a group, emission / k must be equal (relative spread <= 1e-4)
  fidelity       stored quantity, unit, date, facility, factor_source, status, CO2e = sum(GWP x gas)
"""
import argparse
import calendar
import collections
import csv
import json
import math
import sqlite3

GWP = {"ch4": 28.0, "n2o": 265.0}
TOL = 1e-4

TIER_OF = {"default": "default", "custom": "custom", "specific": "specific"}


def rel(a, b):
    if a == b:
        return 0.0
    d = max(abs(a), abs(b))
    return abs(a - b) / d if d > 0 else 0.0


def load(args):
    exp = [json.loads(line) for line in open(args.expected)]
    rows = {}
    with open(args.csv, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows[r["source_ref"]] = r
    sql = """SELECT e.*, f.name AS fac_name FROM emissions e LEFT JOIN facilities f
             ON f.id = e.facility_id WHERE e.data_source_ref LIKE 'AUD-%%'"""
    if args.db.startswith(("postgresql", "postgres://")):
        # the same checks on a PostgreSQL import (DB_TYPE=postgres)
        import psycopg2
        import psycopg2.extras
        con = psycopg2.connect(args.db.replace("postgresql+psycopg2://", "postgresql://"))
        cur = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql)
        result = cur
    else:
        con = sqlite3.connect(args.db)
        con.row_factory = sqlite3.Row
        result = con.execute(sql.replace("%%", "%"))
    db = {}
    for r in result:
        db.setdefault(r["data_source_ref"], []).append(dict(r))
    skipped = {}
    if args.skipped:
        for s in json.load(open(args.skipped)):
            ref = s.get("source_ref")
            if ref:
                skipped[ref] = s.get("reason")
    return exp, rows, db, skipped


def parse_num(s):
    s = str(s).strip().replace(",", "")
    return float(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--skipped")
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    exp, rows, db, skipped = load(args)

    R = {"counts": collections.Counter(), "by_family": collections.defaultdict(collections.Counter),
         "oracle_fail": [], "group_fail": [], "accept_mismatch": [], "fidelity": collections.defaultdict(list),
         "reject_reasons": collections.Counter(), "unexpected_reject_reasons": collections.Counter(),
         "ambiguous_accepted": [], "dup_records": []}
    groups = collections.defaultdict(list)

    for m in exp:
        ref = m["ref"]
        fam = m["family"]
        recs = db.get(ref, [])
        if len(recs) > 1:
            R["dup_records"].append(ref)
        rec = recs[0] if recs else None
        accepted = rec is not None
        R["counts"]["rows"] += 1
        R["by_family"][fam]["rows"] += 1
        R["by_family"][fam]["accepted" if accepted else "rejected"] += 1
        row = rows[ref]
        reason = skipped.get(ref)
        if not accepted and reason:
            R["reject_reasons"][f"{fam}: {reason[:110]}"] += 1

        if m["expect"] == "accept" and not accepted:
            R["counts"]["expected_accept_but_rejected"] += 1
            R["by_family"][fam]["expected_accept_but_rejected"] += 1
            R["unexpected_reject_reasons"][f"{fam}: {(reason or '(no reason captured)')[:140]}"] += 1
            if len(R["accept_mismatch"]) < 4000:
                R["accept_mismatch"].append({"ref": ref, "family": fam, "kind": "rejected", "reason": reason,
                                             "unit": row.get("unit"), "note": m.get("note")})
        elif m["expect"] == "reject" and accepted:
            R["counts"]["expected_reject_but_accepted"] += 1
            R["by_family"][fam]["expected_reject_but_accepted"] += 1
            if len(R["accept_mismatch"]) < 4000:
                R["accept_mismatch"].append({"ref": ref, "family": fam, "kind": "accepted", "why": m.get("reason"),
                                             "unit": row.get("unit"), "co2e": rec["co2e_total"]})
        elif m["expect"] == "either":
            R["counts"]["either_" + ("accepted" if accepted else "rejected")] += 1
        elif m["expect"] == "ambiguous":
            R["counts"]["ambiguous_rows"] += 1
            if accepted:
                R["counts"]["ambiguous_accepted"] += 1
                R["ambiguous_accepted"].append({"ref": ref, "why": m.get("reason"), "unit": row.get("unit"),
                                                "quantity": row.get("quantity"), "stored_qty": rec["quantity"],
                                                "stored_unit": rec["unit"], "co2e": rec["co2e_total"],
                                                "row": {k: v for k, v in row.items() if v not in ("", None)}})
            else:
                R["counts"]["ambiguous_rejected"] += 1
        else:
            R["counts"]["acceptance_ok"] += 1

        if not accepted:
            continue

        co2, ch4, n2o, tot = (float(rec[c] or 0) for c in ("co2_emissions", "ch4_emissions", "n2o_emissions", "co2e_total"))

        # --- fidelity ------------------------------------------------------------------------
        if any(math.isnan(x) or math.isinf(x) or x < 0 for x in (co2, ch4, n2o, tot)):
            R["fidelity"]["negative_or_nan"].append(ref)
        if rel(tot, co2 + GWP["ch4"] * ch4 + GWP["n2o"] * n2o) > 1e-9 and abs(tot - (co2 + 28 * ch4 + 265 * n2o)) > 1e-12:
            R["fidelity"]["co2e_not_sum_of_gases"].append(ref)
        if rec["year"] != m["year"] or rec["month"] != m["month"]:
            R["fidelity"]["period"].append(ref)
        if (rec["fac_name"] or "").lower() != row["facility_name"].strip().lower():
            R["fidelity"]["facility"].append(ref)
        if rec["status"] != "Pending":
            R["fidelity"]["status_not_pending"].append(ref)
        if rec["equipment_id"] != row["equipment_id"]:
            R["fidelity"]["equipment_id"].append(ref)
        want_src = m["tier"]
        if rec["factor_source"] != want_src:
            R["fidelity"]["factor_source"].append((ref, row.get("factor_type"), rec["factor_source"]))
        if row.get("quantity"):
            try:
                q_in = parse_num(row["quantity"])
                if rec["quantity"] is None or rel(float(rec["quantity"]), q_in) > 1e-12:
                    R["fidelity"]["quantity_changed"].append((ref, row["quantity"], rec["quantity"]))
            except ValueError:
                pass
            if (rec["unit"] or "") != row.get("unit", "").strip() and \
                    (rec["unit"] or "").lower() != row.get("unit", "").strip().lower():
                R["fidelity"]["unit_changed"].append((ref, row.get("unit"), rec["unit"]))
        elif rec["quantity"] is None:
            R["fidelity"]["quantity_missing_engineered"].append((ref, fam))

        # --- oracle --------------------------------------------------------------------------
        o = m.get("oracle")
        if o:
            scale = 1.0
            if o.get("prorate_year"):
                y, mo = m["year"], m["month"]
                scale = calendar.monthrange(y, mo)[1] / (366 if calendar.isleap(y) else 365)
            bad = {}
            for gas, val in (("co2", co2), ("ch4", ch4), ("n2o", n2o), ("co2e", tot)):
                e = o[gas] * scale
                if rel(val, e) > TOL and abs(val - e) > 1e-9:
                    bad[gas] = (val, e, val / e if e else None)
            R["counts"]["oracle_checked"] += 1
            R["by_family"][fam]["oracle_checked"] += 1
            if bad:
                R["counts"]["oracle_fail"] += 1
                R["by_family"][fam]["oracle_fail"] += 1
                R["oracle_fail"].append({"ref": ref, "family": fam, "unit": row.get("unit"), "fuel": row.get("fuel"),
                                         "note": m.get("note"), "bad": bad})
            else:
                R["counts"]["oracle_ok"] += 1

        if m.get("group"):
            groups[m["group"]].append((ref, fam, m.get("k") or 1, tot, co2, ch4, n2o, row))

    # --- metamorphic -------------------------------------------------------------------------
    for gid, mem in groups.items():
        if len(mem) < 2:
            continue
        R["counts"]["groups_checked"] += 1
        fam = mem[0][1]
        R["by_family"][fam]["groups_checked"] += 1
        norm = [(m[0], m[3] / m[2], m[7]) for m in mem]
        vals = [v for _, v, _ in norm]
        lo, hi = min(vals), max(vals)
        if hi > 0 and (hi - lo) / hi > TOL:
            R["counts"]["groups_failed"] += 1
            R["by_family"][fam]["groups_failed"] += 1
            med = sorted(vals)[len(vals) // 2]
            R["group_fail"].append({"group": gid, "family": fam, "spread": (hi - lo) / hi,
                                    "members": [{"ref": r, "per_k": v, "ratio_to_median": (v / med if med else None),
                                                 "unit": row.get("unit"), "detail": {k2: row.get(k2) for k2 in (
                                                     "quantity", "temp_unit", "press_unit", "operating_temperature",
                                                     "operating_pressure", "tank_unit", "pneu_bleed_unit", "agr_unit",
                                                     "comp_rate_unit", "rate_unit", "vent_rate_unit", "vent_volume_unit",
                                                     "blowdown_temp_unit", "blowdown_press_unit", "oil_unit", "gor_unit",
                                                     "combustion_efficiency", "c1", "fuel", "activity_key")
                                                     if row.get(k2)}} for r, v, row in norm]})

    R["by_family"] = {k: dict(v) for k, v in R["by_family"].items()}
    R["counts"] = dict(R["counts"])
    R["reject_reasons"] = R["reject_reasons"].most_common()
    R["unexpected_reject_reasons"] = R["unexpected_reject_reasons"].most_common()
    R["fidelity"] = {k: (len(v), v[:50]) for k, v in R["fidelity"].items()}
    json.dump(R, open(args.report, "w"), indent=1, default=str)
    print(json.dumps(R["counts"], indent=1))


if __name__ == "__main__":
    main()
