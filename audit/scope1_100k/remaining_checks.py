"""Scope 1 checks beyond the CSV path (audit section 9):

  A. Excel (.xlsx) import of the 30 Compendium exhibit rows == CSV import of the same rows
  B. Edits (PUT): a changed quantity recalculates exactly like a new entry with that quantity;
     a metadata-only edit leaves the emissions untouched
  C. GWP switch AR5 -> AR6 -> AR5: every record's co2e == co2 + ch4 x GWP_CH4 + n2o x GWP_N2O of the
     active set, and switching back restores the original values
  D. Region-scoped user: sees and writes only facilities of their region
  E. Dashboard summary (Verified records) == SUM(co2e_total) of Verified Scope 1 rows in the DB

python remaining_checks.py <db_path>   -> prints a table, writes results/remaining_checks.json
"""
import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exhibits_e2e as E  # noqa: E402
from harness import ADMIN_EMAIL, ADMIN_PASSWORD, boot, run_csv  # noqa: E402

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"check": name, "ok": bool(ok), "detail": detail})
    print(f"{'OK  ' if ok else 'FAIL'} {name}  {detail}"[:260])


def close(a, b, rel=1e-9):
    return abs((a or 0) - (b or 0)) <= rel * max(abs(a or 0), abs(b or 0), 1e-12)


def rows_file(rows, suffix):
    header = ["source_ref", "date", "facility_name"] + sorted({k for r in rows for k in r} - {"source_ref", "date", "facility_name"})
    d = tempfile.mkdtemp()
    path = os.path.join(d, f"exhibits{suffix}")
    if suffix == ".csv":
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, header)
            w.writeheader()
            w.writerows(rows)
    else:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.append(header)
        for r in rows:
            ws.append([r.get(h, "") for h in header])
        wb.save(path)
    return path


def login(client, email, password):
    """Log in and make every mutating call carry the X-CSRFToken header, as src/api.js does."""
    tok = (client.get("/api/csrf-token").get_json() or {}).get("csrf_token") or (client.get("/api/csrf-token").get_json() or {}).get("csrfToken")
    client.environ_base["HTTP_X_CSRFTOKEN"] = tok
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    tok = (client.get("/api/csrf-token").get_json() or {})
    client.environ_base["HTTP_X_CSRFTOKEN"] = tok.get("csrf_token") or tok.get("csrfToken")


def main(db_path):
    app = boot(db_path)
    from extensions import db
    from models import Emission, Facility, User

    client = app.test_client()
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)

    # ---------------- A. Excel vs CSV ----------------
    def tagged(tag):
        return [dict(E.B, source_ref=f"{tag}-{i:03d}-{ex}", **row) for i, (ex, _d, row, _e, _t) in enumerate(E.CASES)]

    run_csv(app, rows_file(tagged("CSV"), ".csv"))
    job = run_csv(app, rows_file(tagged("XLS"), ".xlsx"))
    with app.app_context():
        recs = {e.data_source_ref: e for e in Emission.query.filter(Emission.data_source_ref.like("CSV-%") |
                                                                     Emission.data_source_ref.like("XLS-%")).all()}
    diffs, missing = [], []
    for i, (ex, *_r) in enumerate(E.CASES):
        a, b = recs.get(f"CSV-{i:03d}-{ex}"), recs.get(f"XLS-{i:03d}-{ex}")
        if a is None or b is None:
            missing.append(ex)
            continue
        for g in ("co2_emissions", "ch4_emissions", "n2o_emissions", "co2e_total", "quantity"):
            if not close(getattr(a, g), getattr(b, g)):
                diffs.append((ex, g, getattr(a, g), getattr(b, g)))
    check("A. xlsx import == csv import (30 exhibit rows)", not diffs and not missing,
          f"missing={missing} diffs={diffs[:5]} skipped={[s.get('reason') for s in job.get('skipped', [])][:3]}")

    # ---------------- B. edits ----------------
    with app.app_context():
        fac = Facility.query.filter_by(name="In Amenas CPF").first()
        fid = fac.id
    base = {"facility_id": fid, "year": 2024, "month": 11, "process_type": "combustion", "factor_source": "default",
            "fuel": "Diesel (No. 2 Fuel Oil)", "fuel_type": "Diesel (No. 2 Fuel Oil)", "quantity": 5000, "amount": 5000,
            "unit": "L", "activity": "Exploration & Production"}
    r1 = client.post("/api/emissions/", json=dict(base, equipment_id="EDIT-1"))
    r2 = client.post("/api/emissions/", json=dict(base, quantity=8000, amount=8000, equipment_id="EDIT-REF"))
    check("B0. manual entries created", r1.status_code == 201 and r2.status_code == 201, f"{r1.status_code} {r2.status_code}")
    with app.app_context():
        e1 = Emission.query.filter_by(equipment_id="EDIT-1").first()
        ref = Emission.query.filter_by(equipment_id="EDIT-REF").first()
        eid, before = e1.id, (e1.co2_emissions, e1.co2e_total)
        ref_vals = (ref.co2_emissions, ref.ch4_emissions, ref.n2o_emissions, ref.co2e_total)
    r = client.put(f"/api/emissions/{eid}", json=dict(base, quantity=8000, amount=8000, equipment_id="EDIT-1"))
    with app.app_context():
        e1 = db.session.get(Emission, eid)
        got = (e1.co2_emissions, e1.ch4_emissions, e1.n2o_emissions, e1.co2e_total)
        status_after = e1.status
    check("B1. PUT quantity 5000 -> 8000 L recalculates like a new 8000 L entry",
          r.status_code == 200 and all(close(x, y) for x, y in zip(got, ref_vals)),
          f"http={r.status_code} got={got} ref={ref_vals} status={status_after}")
    r = client.put(f"/api/emissions/{eid}", json={"equipment_id": "EDIT-1b", "description": "metadata only"})
    with app.app_context():
        e1 = db.session.get(Emission, eid)
        got2 = (e1.co2_emissions, e1.ch4_emissions, e1.n2o_emissions, e1.co2e_total)
    check("B2. metadata-only PUT keeps the emissions", r.status_code == 200 and all(close(x, y) for x, y in zip(got2, got)),
          f"http={r.status_code} {got2}")

    # ---------------- C. GWP switch ----------------
    from calculations.constants import GWP_STANDARDS

    def snapshot():
        with app.app_context():
            return {e.id: (e.co2_emissions or 0, e.ch4_emissions or 0, e.n2o_emissions or 0, e.co2e_total or 0)
                    for e in Emission.query.all()}

    s_ar5 = snapshot()
    results_c = {}
    for std in ("AR6", "AR4", "AR5"):
        r = client.put("/api/auth/settings", json={"gwp_standard": std})
        g = GWP_STANDARDS[std]
        gch4, gn2o = g.get("CH4") or g.get("ch4"), g.get("N2O") or g.get("n2o")
        snap = snapshot()
        bad = [(i, v) for i, v in snap.items() if not close(v[3], v[0] + v[1] * gch4 + v[2] * gn2o, 1e-6)]
        gases_moved = [i for i, v in snap.items() if not all(close(v[k], s_ar5[i][k], 1e-9) for k in range(3))]
        results_c[std] = (r.status_code, len(snap), len(bad), len(gases_moved))
        check(f"C. GWP {std}: co2e == co2 + ch4 x {gch4} + n2o x {gn2o} on every record; gas masses unchanged",
              r.status_code == 200 and not bad and not gases_moved,
              f"http={r.status_code} records={len(snap)} bad={bad[:3]} gas_changed={len(gases_moved)}")
    s_back = snapshot()
    check("C. AR5 -> AR6 -> AR4 -> AR5 restores every record", all(close(s_back[i][3], s_ar5[i][3], 1e-9) for i in s_ar5),
          f"{sum(1 for i in s_ar5 if not close(s_back[i][3], s_ar5[i][3], 1e-9))} differ")

    # ---------------- D. region-scoped user ----------------
    from werkzeug.security import generate_password_hash
    with app.app_context():
        if not User.query.filter_by(email="illizi.user@ghg.test").first():
            db.session.add(User(fullName="Illizi User", orgName="Audit", sector="Oil & Gas", email="illizi.user@ghg.test",
                                role="user", status="active", location="Illizi",
                                password_hash=generate_password_hash("Illizi-Passw0rd!2026")))
            db.session.commit()
        own = Facility.query.filter_by(name="In Amenas CPF").first().id
        other = Facility.query.filter_by(name="Hassi Messaoud Gas Plant").first().id
        n_illizi = Emission.query.join(Facility, Emission.facility_id == Facility.id).filter(Facility.region == "Illizi").count()
    uc = app.test_client()
    login(uc, "illizi.user@ghg.test", "Illizi-Passw0rd!2026")
    ok_post = uc.post("/api/emissions/", json=dict(base, facility_id=own, equipment_id="REGION-OK"))
    bad_post = uc.post("/api/emissions/", json=dict(base, facility_id=other, equipment_id="REGION-BAD"))
    check("D1. region user can enter data for an own-region facility", ok_post.status_code == 201, str(ok_post.status_code))
    check("D2. region user is refused for another region's facility", bad_post.status_code in (400, 403),
          f"{bad_post.status_code} {bad_post.get_data(as_text=True)[:120]}")
    lst = uc.get("/api/emissions/?scope=1&per_page=1000&limit=1000")
    body = lst.get_json() or {}
    items = body.get("data") or body.get("emissions") or body.get("items") or (body if isinstance(body, list) else [])
    regions = {str(x.get("region") or x.get("facility_region") or "") for x in items}
    with app.app_context():
        fac_regions = {f.id: f.region for f in Facility.query.all()}
    other_rows = [x for x in items if fac_regions.get(x.get("facility_id")) not in (None, "Illizi")]
    check("D3. region user lists only own-region records", lst.status_code == 200 and not other_rows,
          f"http={lst.status_code} n={len(items)} (Illizi rows in DB {n_illizi + 1}) other={len(other_rows)} regions={sorted(regions)[:5]}")

    # ---------------- E. dashboard reconciliation ----------------
    # spread records over another year and facility so the filters are exercised
    for k, (fname, yr, mo, qty) in enumerate([("Hassi Messaoud Gas Plant", 2023, 5, 12000), ("Hassi Messaoud Gas Plant", 2024, 7, 3000),
                                              ("Arzew GNL-1Z", 2023, 1, 777)]):
        with app.app_context():
            f_id = Facility.query.filter_by(name=fname).first().id
        r = client.post("/api/emissions/", json=dict(base, facility_id=f_id, year=yr, month=mo, quantity=qty, amount=qty,
                                                     equipment_id=f"DASH-{k}"))
        assert r.status_code == 201, r.get_data(as_text=True)[:200]
    from sqlalchemy import func
    with app.app_context():
        Emission.query.update({Emission.status: "Verified"}, synchronize_session=False)
        # one record left Pending: it must not be counted
        Emission.query.filter_by(equipment_id="DASH-2").update({Emission.status: "Pending"}, synchronize_session=False)
        db.session.commit()
        hm = Facility.query.filter_by(name="Hassi Messaoud Gas Plant").first().id

        def dbsum(*flt):
            q = db.session.query(func.sum(Emission.co2e_total), func.sum(Emission.co2_emissions),
                                 func.sum(Emission.ch4_emissions), func.sum(Emission.n2o_emissions)).filter(
                Emission.status == "Verified", *flt)
            return [float(x or 0) for x in q.one()]

        want = {"all": dbsum(), "2024": dbsum(Emission.year == 2024), "2023": dbsum(Emission.year == 2023),
                "HM": dbsum(Emission.facility_id == hm), "HM-2023": dbsum(Emission.facility_id == hm, Emission.year == 2023)}
    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()
    queries = {"all": "", "2024": "?year=2024", "2023": "?year=2023", "HM": f"?facilityId={hm}", "HM-2023": f"?facilityId={hm}&year=2023"}

    def totals(rows):
        rows = rows if isinstance(rows, list) else [rows]
        return [sum(float(r.get(k) or 0) for r in rows) for k in ("scope1_total", "co2_total", "ch4_total", "n2o_total")]

    for name, qs in queries.items():
        got = totals(client.get("/api/dashboard/summary" + qs).get_json())
        check(f"E. dashboard summary {name}: Scope 1 co2e / co2 / ch4 / n2o == DB sums of Verified rows",
              all(close(a, b, 1e-6) for a, b in zip(got, want[name])), f"dash={[round(x, 4) for x in got]} db={[round(x, 4) for x in want[name]]}")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "remaining_checks.json")
    json.dump(RESULTS, open(out, "w"), indent=1, default=str)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(tempfile.gettempdir(), "remaining_checks.db"))
