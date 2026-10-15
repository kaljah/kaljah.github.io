"""Regression tests for the 2026-10-14 zero-baseline audit (BUG-0001..0074).

BUG-0001 and BUG-0002 are covered in tests/test_it_role_security.py and
tests/test_audit_rc1_authz_reports.py.
"""
import io
import time

import pytest

from app import app
from audit_helpers import login, make_facility, make_user, uniq
from extensions import db
from models import Emission


@pytest.fixture
def ctx():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.app_context():
        yield


CSV_HDR = "date,facility_name,process_type,fuel,quantity,unit,tier\n"


def _start(client, text, name):
    r = client.post("/api/emissions/upload/start", content_type="multipart/form-data",
                    data={"file": (io.BytesIO(text.encode()), name), "scope": "1", "decimal_mark": "point"})
    assert r.status_code in (200, 202), r.get_data(as_text=True)[:300]
    return r.get_json()["job_id"]


def _wait(client, jobs, timeout=90):
    t0 = time.time()
    while time.time() - t0 < timeout:
        states = [client.get(f"/api/emissions/upload/status/{j}").get_json()["status"] for j in jobs]
        if all(s not in ("processing", "queued", "pending", "running") for s in states):
            return states
        time.sleep(0.2)
    raise AssertionError(f"uploads did not finish: {states}")


# ── BUG-0003: concurrent identical uploads must not insert duplicates ──────────────

def test_bug0003_concurrent_identical_uploads_store_rows_once(ctx, monkeypatch):
    import calculations

    real = calculations.compute_emissions

    def slow(*a, **kw):  # keep each job running long enough for the three to overlap
        time.sleep(0.05)
        return real(*a, **kw)

    monkeypatch.setattr(calculations, "compute_emissions", slow)
    fac = make_facility(name=uniq("RaceFac"), region=uniq("R"))
    admin = make_user("admin", "Global")
    year = 2009
    text = CSV_HDR + "".join(f"{year}-{m:02d},{fac.name},stationary_combustion,Natural Gas,10,MMBtu,1\n"
                             for m in range(1, 13))
    with app.test_client() as c:
        login(c, admin)
        jobs = [_start(c, text, f"race{i}.csv") for i in range(3)]
        states = _wait(c, jobs)
        skipped = [c.get(f"/api/emissions/upload/status/{j}").get_json().get("skipped_count", 0) for j in jobs]
    db.session.expire_all()
    n = Emission.query.filter_by(facility_id=fac.id, year=year).count()
    assert n == 12, (n, states, skipped)
    assert sorted(skipped) == [0, 12, 12]


# ── BUG-0004 / BUG-0023: equity allocation ─────────────────────────────────────────

def _partner(code):
    from models import JvPartner
    from routes.equity_routes import ensure_default_partners

    ensure_default_partners()
    return JvPartner.query.filter_by(code=code).first()


def _alloc(client, fac, year):
    r = client.get(f"/api/equity/allocation?year={year}&facility_id={fac.id}")
    assert r.status_code == 200, r.get_data(as_text=True)[:300]
    row = r.get_json()[0]
    return row, {p["partner_code"]: p for p in row["partners"]}


def test_bug0004_operator_takes_the_remainder_not_100_on_top(ctx):
    fac = make_facility(region=uniq("R"))
    year = 2008
    db.session.add(Emission(facility_id=fac.id, year=year, month=3, process_type="combustion",
                            co2e_total=1000.0, ch4_emissions=2.0, status="Verified"))
    db.session.commit()
    admin = make_user("admin", "Global")
    eni = _partner("ENI")
    with app.test_client() as c:
        login(c, admin)
        r = c.post("/api/equity/shares", json={"facility_id": fac.id, "partner_id": eni.id,
                                               "equity_share_pct": 40, "effective_start_date": f"{year}-01-01"})
        assert r.status_code == 200, r.get_data(as_text=True)
        row, by = _alloc(c, fac, year)
    assert by["SH"]["equity_pct"] == pytest.approx(60.0)
    assert by["ENI"]["equity_pct"] == pytest.approx(40.0)
    assert sum(p["allocated_co2e"] for p in row["partners"]) == pytest.approx(1000.0)
    assert row["is_fully_allocated"]


def test_bug0023_mid_year_share_change_follows_the_months_of_the_emissions(ctx):
    fac = make_facility(region=uniq("R"), equity_share_pct=0.0)  # operator holds nothing: ENI is the only partner
    year = 2007
    for m in range(1, 7):  # all emissions January to June
        db.session.add(Emission(facility_id=fac.id, year=year, month=m, process_type="combustion",
                                co2e_total=100.0, status="Verified"))
    db.session.commit()
    admin = make_user("admin", "Global")
    eni = _partner("ENI")
    with app.test_client() as c:
        login(c, admin)
        for start, end, pct in ((f"{year}-01-01", f"{year}-06-30", 50), (f"{year}-07-01", None, 100)):
            body = {"facility_id": fac.id, "partner_id": eni.id, "equity_share_pct": pct,
                    "effective_start_date": start, "effective_end_date": end}
            assert c.post("/api/equity/shares", json=body).status_code == 200
        row, by = _alloc(c, fac, year)
    assert by["ENI"]["allocated_co2e"] == pytest.approx(300.0)  # 50 % of 600 t, not 75.2 %
    assert row["unallocated_co2e"] == pytest.approx(300.0)


# ── Review queue, Scope 2 / Scope 3 calculation, facility scope ─────────────────────

def _s1(fac, year, month, status="Verified", **kw):
    e = Emission(facility_id=fac.id, year=year, month=month, process_type="combustion",
                 fuel_type="Natural Gas", quantity=10, unit="MMBtu", co2e_total=1.0, status=status, **kw)
    db.session.add(e)
    db.session.commit()
    return e


def test_bug0005_approve_all_leaves_drafts_alone(ctx):
    fac = make_facility(region=uniq("R"))
    maker = make_user("user", fac.region)
    draft = _s1(fac, 2006, 1, status="Draft", created_by=maker.id)
    pending = _s1(fac, 2006, 2, status="Pending", created_by=maker.id)
    admin = make_user("admin", "Global")
    with app.test_client() as c:
        login(c, admin)
        r = c.post("/api/emissions/approve/batch", json={"scope": "1", "approve_all": True})
        assert r.status_code == 200, r.get_data(as_text=True)
        assert draft.id not in r.get_json()["approved_ids"]
    db.session.expire_all()
    assert db.session.get(Emission, draft.id).status == "Draft"
    assert db.session.get(Emission, pending.id).status == "Verified"


def _scope2(c, fac, **kw):
    body = {"facility_id": fac.id, "year": 2024, "month": 5, "source_type": "electricity",
            "electricity_kwh": 100000, "grid_region": "Algerian National Grid", **kw}
    return c.post("/api/scope2", json=body)


def _scope2_row(rid):
    from models import Scope2Emission

    db.session.expire_all()
    return db.session.get(Scope2Emission, rid)


def _new_scope2_id(fac):
    from models import Scope2Emission

    return Scope2Emission.query.filter_by(facility_id=fac.id).order_by(Scope2Emission.id.desc()).first().id


def test_bug0006_grid_change_recalculates_the_market_method(ctx):
    fac = make_facility(region=uniq("R"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert _scope2(c, fac).status_code in (200, 201)
        rid = _new_scope2_id(fac)
        assert c.put(f"/api/scope2/{rid}", json={"grid_region": "US-CAMX (WECC California)"}).status_code == 200
    row = _scope2_row(rid)
    assert row.market_emission_factor is None
    assert row.co2e_market_based == pytest.approx(row.co2e_location_based)


def test_bug0007_cooling_factor_of_zero_is_kept(ctx):
    fac = make_facility(region=uniq("R"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.post("/api/scope2", json={"facility_id": fac.id, "year": 2024, "month": 5, "source_type": "cooling",
                                        "cooling_ton": 100, "emission_factor": 0})
        assert r.status_code in (200, 201), r.get_data(as_text=True)
    row = _scope2_row(_new_scope2_id(fac))
    assert row.co2e == 0.0 and row.emission_factor == 0.0


def test_bug0024_zero_instrument_with_supplier_factor_is_refused_and_edits_are_stable(ctx):
    fac = make_facility(region=uniq("R"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert _scope2(c, fac, market_instrument_type="rec", market_emission_factor=0.2).status_code == 400
        r = _scope2(c, fac, market_instrument_type="supplier_tariff", market_emission_factor=0.2)
        assert r.status_code in (200, 201)
        rid = _new_scope2_id(fac)
        before = _scope2_row(rid).co2e_market_based
        assert c.put(f"/api/scope2/{rid}", json={"electricity_kwh": 100000}).status_code == 200
    assert _scope2_row(rid).co2e_market_based == pytest.approx(before) == pytest.approx(20.0)


def test_bug0036_scope2_source_type_is_validated_on_edit(ctx):
    fac = make_facility(region=uniq("R"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert _scope2(c, fac).status_code in (200, 201)
        rid = _new_scope2_id(fac)
        assert c.put(f"/api/scope2/{rid}", json={"source_type": "banana"}).status_code == 400
    assert _scope2_row(rid).source_type == "electricity"


def test_bug0037_scope2_and_scope3_need_a_month(ctx):
    fac = make_facility(region=uniq("R"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.post("/api/scope2", json={"facility_id": fac.id, "year": 2024, "source_type": "electricity",
                                        "electricity_kwh": 1000, "grid_region": "Algerian National Grid"})
        assert r.status_code == 400
        r = c.post("/api/scope3", json={"facility_id": fac.id, "year": 2024, "category": "Category 1",
                                        "activity_data": 10, "emission_factor": 2})
        assert r.status_code == 400


def test_bug0008_supplier_reported_scope3_total_survives_an_activity_edit(ctx):
    from models import Scope3Emission

    fac = make_facility(region=uniq("R"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.post("/api/scope3", json={"facility_id": fac.id, "year": 2024, "month": 4, "category": "Category 1",
                                        "co2e": 500})
        assert r.status_code in (200, 201), r.get_data(as_text=True)
        rid = Scope3Emission.query.filter_by(facility_id=fac.id).first().id
        assert c.put(f"/api/scope3/{rid}", json={"activity_data": 10}).status_code == 200
        assert c.put(f"/api/scope3/{rid}", json={"emission_factor": 0}).status_code == 422
    db.session.expire_all()
    assert db.session.get(Scope3Emission, rid).co2e == pytest.approx(500.0)


def test_bug0032_empty_edit_keeps_a_verified_record_verified(ctx):
    fac = make_facility(region=uniq("R"))
    maker = make_user("superuser", fac.region)
    rec = _s1(fac, 2005, 3, created_by=maker.id)
    with app.test_client() as c:
        login(c, maker)
        for body in ({}, None):
            r = c.put(f"/api/emissions/{rec.id}", json=body)
            assert r.status_code == 200 and r.get_json()["status"] == "Verified"
    db.session.expire_all()
    assert db.session.get(Emission, rec.id).status == "Verified"


def test_bug0009_dashboard_cache_follows_a_scope_change(ctx):
    a, b = make_facility(region=uniq("RA")), make_facility(region=uniq("RB"))
    _s1(a, 2004, 1)
    user = make_user("user", a.region)
    with app.test_client() as c:
        login(c, user)
        first = c.get("/api/dashboard/batch-all?year=2004").get_json()
        user.location = b.region
        db.session.commit()
        second = c.get("/api/dashboard/batch-all?year=2004").get_json()
    assert first != second


def test_bug0010_location_scope_is_an_exact_match(ctx):
    from utils import get_allowed_facility_ids

    tag = uniq("Zq")
    one = make_facility(name=f"{tag}-North", region=f"{tag}-North")
    two = make_facility(name=f"{tag}-NorthEast", region=f"{tag}-NorthEast")
    assert get_allowed_facility_ids(make_user("user", f"{tag}-North")) == [one.id]
    assert get_allowed_facility_ids(make_user("user", tag)) == []
    assert two.id not in get_allowed_facility_ids(make_user("user", f" {tag}-north "))


def test_bug0011_bug0033_facility_names_and_codes_are_unique(ctx):
    name, code = uniq("Dup"), uniq("C")
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert c.post("/api/facilities", json={"name": name, "region": "West", "code": code}).status_code == 201
        assert c.post("/api/facilities", json={"name": name.upper(), "region": "West"}).status_code == 409
        other = c.post("/api/facilities", json={"name": uniq("Other"), "region": "West"}).get_json()["id"]
        assert c.put(f"/api/facilities/{other}", json={"code": code}).status_code == 409
        assert c.put(f"/api/facilities/{other}", json={"name": name}).status_code == 409


def test_bug0068_facility_delete_with_records_needs_confirmation(ctx):
    from models import Facility

    fac = make_facility(region=uniq("R"))
    _s1(fac, 2003, 1)
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.delete(f"/api/facilities/{fac.id}")
        assert r.status_code == 409 and r.get_json()["record_counts"]["scope1"] == 1
        assert c.delete(f"/api/facilities/{fac.id}?confirm=true").status_code == 200
    db.session.expire_all()
    assert db.session.get(Facility, fac.id) is None


# ── Duplicates and statuses of manual entry and the JSON import ─────────────────────

def _manual(fac, **kw):
    return {"facility_id": fac.id, "year": 2024, "month": 3, "process_type": "stationary_combustion",
            "fuel_type": "Natural Gas", "quantity": 10, "unit": "MMBtu", **kw}


def test_bug0028_manual_duplicate_is_refused_unless_confirmed(ctx):
    fac = make_facility(region=uniq("R"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert c.post("/api/emissions/", json=_manual(fac)).status_code == 201
        r = c.post("/api/emissions/", json=_manual(fac))
        assert r.status_code == 409 and r.get_json()["requires_confirmation"]
        assert c.post("/api/emissions/", json=_manual(fac, equipment_id="B-2")).status_code == 201
        assert c.post("/api/emissions/", json=_manual(fac, allow_duplicate=True)).status_code == 201
    rows = Emission.query.filter_by(facility_id=fac.id).order_by(Emission.id).all()
    assert len(rows) == 3
    assert rows[-1].qa_flag and rows[-1].status == "Pending"  # the confirmed repeat waits for a reviewer


def test_bug0012_json_import_detects_duplicates_and_reports_the_saved_status(ctx):
    fac = make_facility(region=uniq("R"))
    rec = {"facility_id": fac.id, "year": 2024, "month": 6, "process_type": "stationary_combustion",
           "fuel_type": "Natural Gas", "quantity": 10, "unit": "MMBtu"}
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.post("/api/emissions/import", json={"records": [rec]})
        assert r.status_code == 200, r.get_data(as_text=True)
        assert r.get_json()["status"] == "Verified"
        assert c.post("/api/emissions/import", json={"records": [rec]}).status_code == 400  # only a duplicate
    assert Emission.query.filter_by(facility_id=fac.id).count() == 1


def test_bug0026_rejected_rows_do_not_come_back_verified(ctx):
    fac = make_facility(name=uniq("RejFac"), region=uniq("R"))
    _s1(fac, 2002, 4, status="Rejected")
    admin = make_user("admin", "Global")
    text = ("date,facility_name,process_type,fuel,quantity,unit,tier,status\n"
            f"2002-04,{fac.name},stationary_combustion,Natural Gas,10,MMBtu,1,Rejected\n"
            f"2002-04,{fac.name},stationary_combustion,Natural Gas,10,MMBtu,1,\n")
    with app.test_client() as c:
        login(c, admin)
        job = _start(c, text, "rej.csv")
        _wait(c, [job])
        st = c.get(f"/api/emissions/upload/status/{job}").get_json()
    assert st["skipped_count"] == 1
    assert st["status_counts"] == {"Pending": 1}
    new = Emission.query.filter_by(facility_id=fac.id).filter(Emission.status != "Rejected").one()
    assert new.status == "Pending" and new.qa_flag


# ── Bulk delete, bulk overwrite, audit chain, mitigation, upload check ──────────────

def test_bug0013_bug0035_bulk_delete_validates_ids_and_audits_each_record(ctx):
    from models import ActivityLog

    fac = make_facility(region=uniq("R"))
    a, b = _s1(fac, 2001, 1), _s1(fac, 2001, 2)
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        for bad in ([True], ["x"], [None], [-1], "1", None):
            assert c.post("/api/emissions/bulk-delete", json={"ids": bad}).status_code == 400, bad
        r = c.post("/api/emissions/bulk-delete", json={"ids": [a.id, b.id]})
        assert r.status_code == 200 and r.get_json()["deleted"] == 2
    logged = {log.record_id for log in ActivityLog.query.filter_by(action="DELETE", entity="Emission").all()}
    assert {str(a.id), str(b.id)} <= logged


def test_bug0015_bulk_overwrite_follows_the_edit_rule(ctx):
    fac = make_facility(name=uniq("OwnFac"), region=uniq("R"))
    rec = {"facility_name": fac.name, "date": "2001-05-15", "process": "stationary_combustion",
           "fuel": "Natural Gas", "amount": 50, "unit": "MMBtu"}
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert c.post("/api/emissions/bulk-upload", json={"records": [rec], "confirm": True}).status_code in (200, 201)
    with app.test_client() as c:
        login(c, make_user("user", fac.region))
        c.post("/api/emissions/bulk-upload", json={"records": [{**rec, "amount": 0.001}], "confirm": True})
    db.session.expire_all()
    row = Emission.query.filter_by(facility_id=fac.id).one()
    assert row.quantity == 50 and row.status == "Verified"


def test_bug0016_boolean_facility_id_is_refused_and_the_chain_stays_verified(ctx):
    fac = make_facility(region=uniq("R"))
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.post("/api/emissions/", json={**_manual(fac), "facility_id": True})
        assert r.status_code == 422
        assert c.get("/api/audit/verify-chain").get_json()["status"] == "verified"


def test_bug0016_hash_reads_ids_as_stored():
    from services.audit_chain import _id_text

    assert _id_text(True) == _id_text(1) == "1"
    assert _id_text(None) == ""


def test_bug0018_only_admin_records_organisation_wide_mitigation(ctx):
    fac = make_facility(region=uniq("R"))
    body = {"type": "offset", "subtype": "probe", "year": 2025, "quantity_tco2e": 7}
    with app.test_client() as c:
        login(c, make_user("user", fac.region))
        assert c.post("/api/mitigation", json=body).status_code == 403
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        rid = c.post("/api/mitigation", json=body).get_json()["id"]
    with app.test_client() as c:
        login(c, make_user("superuser", fac.region))
        assert c.delete(f"/api/mitigation/{rid}").status_code == 403


def test_bug0019_one_file_check_at_a_time_per_user(ctx):
    from routes import emissions_import

    user = make_user("user", "West")
    with app.test_client() as c:
        login(c, user)
        emissions_import._active_checks.add(user.id)
        try:
            r = c.post("/api/emissions/upload/check", data={"scope": "1"}, content_type="multipart/form-data")
            assert r.status_code == 429
        finally:
            emissions_import._active_checks.discard(user.id)


# ── Percent fields (BUG-0020 / 0021 / 0022) ─────────────────────────────────────────

def _calc(payload):
    from calculations import compute_emissions
    from calculations.constants import get_active_gwp

    em, _ = compute_emissions(payload, {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu",
                                        "hhv": 1020}, gwp_dict=get_active_gwp())
    return em


def test_bug0020_capture_rate_one_is_one_percent(ctx):
    base = {"process_type": "stationary_combustion", "amount": 100, "unit": "MMBtu", "fuel": "Natural Gas",
            "factor_source": "default"}
    assert _calc({**base, "ccs_capture_rate": 1})["co2"] == pytest.approx(_calc(base)["co2"] * 0.99, rel=1e-9)


def test_bug0021_ch4_content_below_one_is_a_percentage(ctx):
    blow = {"process_type": "blowdown", "factor_source": "specific", "quantity": 5.0, "unit": "m3",
            "blowdown_volume": 5.0, "blowdown_pressure": 500.0, "blowdown_temp": 60.0, "blowdown_events": 10}
    low, high = _calc({**blow, "ch4_content": 0.9}), _calc({**blow, "ch4_content": 90})
    assert low["ch4"] == pytest.approx(high["ch4"] / 100, rel=1e-9)


def test_bug0022_agr_inlet_co2_key_does_not_change_the_basis(ctx):
    agr = {"process_type": "agr", "factor_source": "specific", "unit": "mmscf", "throughput": 100}
    by_generic = _calc({**agr, "co2_content": 0.9})["co2"]
    by_form = _calc({**agr, "agr_co2_in": 0.9})["co2"]
    assert by_generic == pytest.approx(by_form, rel=1e-9)
    assert _calc({**agr, "co2_content": 9})["co2"] == pytest.approx(by_generic * 10, rel=1e-6)


# ── Flaring card, migrations, restore ───────────────────────────────────────────────

def test_bug0027_unclassified_flaring_is_split_by_reported_stream_volumes(ctx):
    from models import FlaringDetail

    fac = make_facility(region=uniq("R"))
    db.session.add(FlaringDetail(facility_id=fac.id, year=2000, routine_knm3=3, non_routine_knm3=1, safety_knm3=0,
                                 status="Verified"))
    db.session.add(Emission(facility_id=fac.id, year=2000, month=1, process_type="flaring", quantity=1,
                            unit="MMscf", co2e_total=100.0, status="Verified"))
    db.session.commit()
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        d = c.get(f"/api/dashboard/flaring-summary?year=2000&facility_id={fac.id}").get_json()
    assert d["stream_tco2e_allocated"] is True
    assert d["routine_flaring"]["tco2e"] == pytest.approx(75.0)
    assert d["non_routine_flaring"]["tco2e"] == pytest.approx(25.0)
    assert d["unclassified_flaring"]["tco2e"] == 0


def test_bug0030_every_migration_downgrade_imports_what_it_uses():
    import ast
    import glob
    import os

    here = os.path.join(os.path.dirname(__file__), "..", "migrations", "versions")
    for path in glob.glob(os.path.join(here, "*.py")):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "downgrade"]:
            used = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
            defined = {a.asname or a.name for n in ast.walk(fn) if isinstance(n, (ast.Import, ast.ImportFrom))
                       for a in n.names}
            defined |= {t.id for n in ast.walk(fn) if isinstance(n, ast.Assign) for t in n.targets
                        if isinstance(t, ast.Name)}
            module_names = {a.asname or a.name for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
                            for a in n.names}
            missing = {"has_index", "has_table", "bind"} & used - defined - module_names
            assert not missing, (path, missing)


def test_bug0031_sqlite_restore_wins_over_the_live_wal(tmp_path, monkeypatch):
    import os
    import sqlite3
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    import restore

    live, backup = tmp_path / "live.db", tmp_path / "backup.db"
    b = sqlite3.connect(backup)
    b.execute("create table t (v int)")
    b.executemany("insert into t values (?)", [(i,) for i in range(2000)])
    b.commit()
    b.close()
    holder = sqlite3.connect(live)
    holder.execute("pragma journal_mode=wal")
    holder.execute("pragma wal_autocheckpoint=0")
    holder.execute("create table t (v int)")
    holder.executemany("insert into t values (?)", [(i,) for i in range(50)])
    holder.commit()  # the 50 rows sit in live.db-wal while this connection stays open
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{live}")
    ok, _ = restore.verify_sqlite_backup(str(backup))
    assert ok
    assert restore.restore_sqlite(str(backup), restore.sqlite_target())
    holder.close()
    check = sqlite3.connect(live)
    assert check.execute("select count(*) from t").fetchone()[0] == 2000
    check.close()
    assert restore.verify_sqlite_backup(str(tmp_path / "missing.db")) == (False, None)
