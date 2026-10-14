"""Whole lifecycle in one flow: facilities and equity shares -> maker uploads (CSV, XLSX, JSON, single) ->
review (self-approval blocked, subset rejected, rest approved by a checker) -> audit chain, QA/QC ->
dashboards, equity allocation, intensity, uncertainty and exports all equal the approved records."""
import csv
import io
import logging
import math
import time
import uuid

import openpyxl
import pytest

from electricity_factors import GRID_FACTORS
from emission_factors.scope3_activity_factors import SCOPE3_ACTIVITY_FACTORS
from tests.audit_helpers import make_facility, make_user, upload

HDR = ["Date", "Facility", "Process Type", "Fuel", "Quantity", "Unit", "Factor Type", "Equipment ID"]


def _csv(rows, header):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


@pytest.fixture
def world(app):
    logging.disable(logging.CRITICAL)
    from extensions import db
    from models import ProductionData

    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        region = f"E2E{tag}"
        fa = make_facility(f"E2E A {tag}", region=region)
        fb = make_facility(f"E2E B {tag}", region=region)
        maker = make_user("user", location=region)
        checker = make_user("admin")
        ids = dict(fa=fa.id, fb=fb.id, na=fa.name, nb=fb.name, maker=maker.id, checker=checker.id)
        for fid, oil in ((fa.id, 10000.0), (fb.id, 4000.0)):
            db.session.add(ProductionData(facility_id=fid, year=2025, month=1, oil_amount=oil, oil_unit="bbl",
                                          gas_amount=0.0, gas_unit="mscf"))
        db.session.commit()
    return ids


def _as(client, app, user_id):
    from extensions import db
    from models import User

    with app.app_context():
        email = db.session.get(User, user_id).email
    client.get("/api/auth/logout")
    r = client.post("/api/auth/login", json={"email": email, "password": "AuditPass!2026"})
    assert r.status_code == 200, r.get_data(as_text=True)[:200]


def _wait(client, job):
    for _ in range(300):
        s = client.get(f"/api/emissions/upload/status/{job}").get_json()
        if s["status"] != "processing":
            return s
        time.sleep(0.05)
    raise AssertionError("upload did not finish")


def _status(app, model, pk):
    from extensions import db

    with app.app_context():
        db.session.expire_all()
        return db.session.get(model, pk).status


def test_full_pipeline(app, client, world):
    from models import Emission, Scope2Emission, Scope3Emission

    w = world
    # -- equity shares: A 60 %, B 50 % to the operator
    _as(client, app, w["checker"])
    partners = client.get("/api/equity/partners").get_json()
    op = next((p for p in partners if p.get("is_operator")), partners[0])
    for fid, pct in ((w["fa"], 60.0), (w["fb"], 50.0)):
        r = client.post("/api/equity/shares", json={"facility_id": fid, "partner_id": op["id"],
                                                    "equity_share_pct": pct, "effective_start_date": "2021-01-01"})
        assert r.status_code in (200, 201), r.get_data(as_text=True)[:300]

    # -- maker: single, CSV, XLSX, JSON uploads for Scope 1, 2 and 3
    _as(client, app, w["maker"])
    r = client.post("/api/emissions/", json={"year": 2025, "month": 1, "facility_id": w["fa"],
                                             "process_type": "combustion", "fuel": "Natural Gas", "amount": 1000,
                                             "unit": "MMBtu", "factor_source": "default", "equipment_id": "SINGLE"})
    assert r.status_code == 201, r.get_data(as_text=True)[:300]
    rows = [["2025-01", w["na"], "combustion", "Diesel (No. 2 Fuel Oil)", 800, "gal", "default", "CSV-A"],
            ["2025-01", w["nb"], "combustion", "Natural Gas", 2500, "MMBtu", "default", "CSV-B"],
            ["2025-01", w["nb"], "combustion", "Natural Gas", 300, "MMBtu", "default", "TO-REJECT"]]
    st = upload(client, _csv(rows, HDR), "1")[2]
    assert st["skipped_count"] == 0, st.get("skipped_preview")

    wb = openpyxl.Workbook()
    wb.active.append(HDR)
    wb.active.append(["2025-01", w["nb"], "combustion", "Diesel (No. 2 Fuel Oil)", 500, "gal", "default", "XLSX-B"])
    out = io.BytesIO()
    wb.save(out)
    r = client.post("/api/emissions/upload/start", data={"file": (io.BytesIO(out.getvalue()), "x.xlsx"), "scope": "1",
                                                         "overwrite_duplicates": "true"},
                    content_type="multipart/form-data")
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    assert _wait(client, r.get_json()["job_id"])["skipped_count"] == 0

    r = client.post("/api/emissions/import", json={"records": [
        {"year": 2025, "month": 1, "facility_id": w["na"], "process_type": "combustion", "fuel": "Natural Gas",
         "amount": 700, "unit": "MMBtu", "factor_source": "default", "equipment_id": "JSON-A"}]})
    assert r.status_code in (200, 201) and not r.get_json().get("errors"), r.get_json()

    s2 = _csv([["2025-01", w["na"], "electricity", 20000, "kWh", list(GRID_FACTORS)[0]]],
              ["Date", "Facility", "Source Type", "Consumption", "Unit", "Grid Region"])
    st = upload(client, s2, "2")[2]
    assert st["skipped_count"] == 0, st.get("skipped_preview")
    name, unit, _ = SCOPE3_ACTIVITY_FACTORS[4][0]
    s3 = _csv([["2025-01", w["nb"], "Category 4", name, 50, unit, ""]],
              ["Date", "Facility", "Category", "Sub Category", "Amount", "Unit", "Emission Factor"])
    st = upload(client, s3, "3")[2]
    assert st["skipped_count"] == 0, st.get("skipped_preview")

    with app.app_context():
        s1 = Emission.query.filter(Emission.facility_id.in_([w["fa"], w["fb"]])).all()
        assert len(s1) == 6 and {e.status for e in s1} == {"Pending"}, [e.status for e in s1]
        s1_ids = {e.equipment_id: e.id for e in s1}
        s2_ids = [e.id for e in Scope2Emission.query.filter_by(facility_id=w["fa"]).all()]
        s3_ids = [e.id for e in Scope3Emission.query.filter_by(facility_id=w["fb"]).all()]
    assert len(s2_ids) == 1 and len(s3_ids) == 1

    # nothing is official before review
    _as(client, app, w["checker"])
    for fid in (w["fa"], w["fb"]):
        rows = client.get(f"/api/dashboard/summary?year=2025&facility_id={fid}").get_json()
        assert not rows or (rows[0]["scope1_total"] == 0 and rows[0]["scope2_total"] == 0)

    # -- the maker cannot approve their own records
    _as(client, app, w["maker"])
    r = client.post(f"/api/emissions/approve/{s1_ids['SINGLE']}", json={"scope": "1"})
    assert r.status_code in (400, 403), r.get_data(as_text=True)[:200]
    assert _status(app, Emission, s1_ids["SINGLE"]) == "Pending"

    # -- the checker rejects one record and approves the rest
    _as(client, app, w["checker"])
    r = client.post(f"/api/emissions/reject/{s1_ids['TO-REJECT']}", json={"scope": "1", "reason": "bad meter reading"})
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    keep = [i for k, i in s1_ids.items() if k != "TO-REJECT"]
    r = client.post("/api/emissions/approve/batch", json={"by_scope": {"1": keep, "2": s2_ids, "3": s3_ids}})
    assert r.status_code == 200 and r.get_json()["success"], r.get_data(as_text=True)[:400]

    with app.app_context():
        s1 = {e.equipment_id: e for e in Emission.query.filter(Emission.facility_id.in_([w["fa"], w["fb"]])).all()}
        assert s1["TO-REJECT"].status == "Rejected"
        assert all(e.status == "Verified" for k, e in s1.items() if k != "TO-REJECT")
        verified = [e for e in s1.values() if e.status == "Verified"]
        verified_refs = {e.record_id for e in verified}
        a_s1 = sum(e.co2e_total for e in verified if e.facility_id == w["fa"])
        b_s1 = sum(e.co2e_total for e in verified if e.facility_id == w["fb"])
        s2_co2e = Scope2Emission.query.filter_by(facility_id=w["fa"]).one().co2e
        s3_co2e = Scope3Emission.query.filter_by(facility_id=w["fb"]).one().co2e
        total_s1 = a_s1 + b_s1

    # -- audit chain unbroken across upload, rejection and approval; QA/QC runs
    chain = client.get("/api/audit/verify-chain").get_json()
    assert chain["status"] == "verified" and chain["is_intact"] and chain["issue_count"] == 0
    assert client.get("/api/qaqc/dashboard").status_code == 200

    # -- dashboard summary equals the approved records
    for fid, exp in ((w["fa"], a_s1), (w["fb"], b_s1)):
        row = client.get(f"/api/dashboard/summary?year=2025&facility_id={fid}").get_json()[0]
        assert row["scope1_total"] == pytest.approx(exp, rel=1e-6)
    row = client.get(f"/api/dashboard/summary?year=2025&facility_id={w['fa']}").get_json()[0]
    assert row["scope2_total"] == pytest.approx(s2_co2e, rel=1e-6)

    # -- equity allocation: facility A at 60 %, facility B at 50 %
    alloc = {a["facility_id"]: a for a in client.get("/api/equity/allocation?year=2025").get_json()}
    pa = next(p for p in alloc[w["fa"]]["partners"] if p["partner_id"] == op["id"])
    pb = next(p for p in alloc[w["fb"]]["partners"] if p["partner_id"] == op["id"])
    assert pa["equity_pct"] == 60 and pb["equity_pct"] == 50
    assert pa["allocated_co2e"] == pytest.approx((a_s1 + s2_co2e) * 0.6, abs=0.011)
    assert pb["allocated_co2e"] == pytest.approx(b_s1 * 0.5, abs=0.011)

    # -- the export carries exactly the approved records, no rounding drift
    ex = client.get("/api/emissions/export?year=2025").get_json()["data"]
    mine = [r for r in ex if r["record_id"] in verified_refs]
    assert len(mine) == len(verified)
    assert sum(r["co2e_total"] for r in mine) == pytest.approx(total_s1, rel=1e-9)

    # -- intensity: kg CO2e per BOE of the facility's production (A: 10,000 bbl, B: 4,000 bbl)
    stats = {s["facility_id"]: s for s in client.get("/api/dashboard/intensity-stats?year=2025").get_json()}
    ia, ib = stats[w["fa"]], stats[w["fb"]]
    assert ia["scope1_intensity"] == pytest.approx(a_s1 * 1000 / 10000, rel=1e-6)
    assert ia["scope2_intensity"] == pytest.approx(s2_co2e * 1000 / 10000, rel=1e-6)
    assert ib["scope1_intensity"] == pytest.approx(b_s1 * 1000 / 4000, rel=1e-6)
    assert ib["scope3_intensity"] == pytest.approx(s3_co2e * 1000 / 4000, rel=1e-6)
    assert ia["co2_intensity"] == pytest.approx(ia["scope1_intensity"] + ia["scope2_intensity"], rel=1e-6)

    # -- uncertainty: reported at 95 % (k = 2); Scope 2 combines a 5 % factor and a 2 % activity term
    u = client.get(f"/api/dashboard/uncertainty?year=2025&facility_id={w['fa']}").get_json()
    for cat in u["categories"]:
        assert cat["uncertainty_decimal"] == pytest.approx(2 * cat["uncertainty_1sigma"], rel=1e-9)
    s2cat = next(c for c in u["categories"] if c["category"].startswith("Scope 2"))
    assert s2cat["uncertainty_decimal"] == pytest.approx(math.hypot(0.05, 0.02), rel=1e-6)
