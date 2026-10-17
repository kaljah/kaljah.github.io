"""Scope 1 residual tests: factors, limits, GWP standards (split from test_scope1_residual.py)."""
import csv
import io
import json
import logging
import uuid
import pytest
from extensions import db
from models import CustomFactor, Emission, Facility, User
from tests.test_bulk_uploaders import upload
from tests.test_scope1_coverage_gaps import ACTORS, _as, _seed, lifecycle_world
from tests.test_scope1_residual import _fname, _rec, _counts, NG

# ---------------------------------------------------------------- entered Tier 3 factors: units, raw values, CO, CCS
def _calc(app, payload, factor=None):
    from calculations.constants import get_active_gwp
    from calculations.legacy_engine import compute_emissions
    from services.scope1_calc import resolve_factor

    with app.app_context():
        p = json.loads(json.dumps(payload))
        return compute_emissions(p, factor if factor is not None else (resolve_factor(dict(p)) or {}),
                                 gwp_dict=get_active_gwp(standard="AR5"))


T3 = {"process_type": "combustion", "factor_source": "specific", "fuel": "Natural Gas", "amount": 1000, "unit": "m3",
      "hhv": 1020, "combustion_efficiency": 0.995}


def test_entered_factors_in_another_unit_are_converted(app):
    em, m = _calc(app, {**T3, "specific_factors": {"co2": 1.9, "co2Unit": "kg/m3"}})
    per_scf, _ = _calc(app, {**T3, "specific_factors": {"co2": 1.9 / 35.3147, "co2Unit": "kg/scf"}})
    assert m == "server_specific" and per_scf["co2"] == pytest.approx(em["co2"], rel=1e-4)
    raw, _ = _calc(app, {**T3, "specific_factors": {"co2": 0, "co2Raw": 1.9 / 35.3147, "co2Unit": "kg/scf"}})
    assert raw["co2"] == pytest.approx(em["co2"], rel=1e-4)
    same, _ = _calc(app, {**T3, "specific_factors": {"co2Raw": 1.9, "co2Unit": "m3"}})
    assert same["co2"] == pytest.approx(1.9)
    with pytest.raises(ValueError, match="invalid raw value"):
        _calc(app, {**T3, "specific_factors": {"co2Raw": "abc", "co2Unit": "kg/scf"}})


def test_entered_factors_on_other_processes_and_co(app):
    em, m = _calc(app, {"process_type": "dehydrator", "factor_source": "specific", "amount": 100, "unit": "MMscf",
                        "specific_factors": {"co2": 0.5, "ch4": 2.0, "n2o": 0}})
    assert m == "server_specific" and em["ch4"] == pytest.approx(0.2) and em["co2"] == pytest.approx(0.05)
    fl, _ = _calc(app, {"process_type": "flaring", "factor_source": "specific", "fuel": "Natural Gas (Flaring)",
                        "amount": 1000, "unit": "m3", "specific_factors": {"co2": 2.0, "ch4": 0.01, "n2o": 0.0001, "co": 0.05}})
    assert fl["co"] == pytest.approx(0.05) and fl["co2"] == pytest.approx(2.0)


def test_ccs_capture_applies_to_entered_and_custom_factors(app):
    base, _ = _calc(app, {**T3, "specific_factors": {"co2": 1.9, "ch4": 0.01}})
    cap, _ = _calc(app, {**T3, "specific_factors": {"co2": 1.9, "ch4": 0.01}, "ccs_capture_rate": 60})
    assert cap["co2"] == pytest.approx(base["co2"] * 0.4)
    assert cap["ch4"] == pytest.approx(base["ch4"])
    assert cap["totalCo2e"] == pytest.approx(base["totalCo2e"] - base["co2"] * 0.6)
    cf = {"type": "custom", "co2": 70.0, "ch4": 0.0, "n2o": 0.0, "unit": "kg/MMBtu"}
    a, m = _calc(app, {"process_type": "combustion", "factor_source": "custom", "amount": 100, "unit": "MMBtu"}, cf)
    b, _ = _calc(app, {"process_type": "combustion", "factor_source": "custom", "amount": 100, "unit": "MMBtu",
                       "ccs_capture_rate": "25%"}, cf)
    assert b["co2"] == pytest.approx(a["co2"] * 0.75) and b["totalCo2e"] == pytest.approx(a["totalCo2e"] - a["co2"] * 0.25)
    with pytest.raises(ValueError):
        _calc(app, {**T3, "specific_factors": {"co2": 1.9}, "ccs_capture_rate": 150})


@pytest.mark.parametrize("hhv,msg", [("abc", "must be a number"), ("-5", "greater than 0"), (0, "greater than 0"),
                                     (True, "must be a number"), ("nan", "finite"), ({"x": 1}, "must be a number")])
def test_invalid_heating_values_are_refused_on_every_path(app, client, lifecycle_world, hhv, msg):
    w = lifecycle_world
    eq = f"HV{uuid.uuid4().hex[:6]}"
    body = {"year": 2025, "month": 1, "facility_id": w["fids"]["in"], "process_type": "combustion", "fuel": "Natural Gas",
            "amount": 1000, "unit": "scf", "factor_source": "custom", "hhv": hhv, "hhv_unit": "Btu/scf", "equipment_id": eq}
    _as(client, w, "user")
    res = client.post("/api/emissions/", json=body)
    # "nan" is already refused by the central request guard (400); the rest by the Scope 1 input check (422)
    assert res.status_code in (400, 422) and msg in res.get_json()["error"] and res.get_json()["field"] == "hhv", res.get_json()
    res = client.post("/api/emissions/import", json={"records": [{**body, "facility_id": _fname(app, w["fids"]["in"])}]})
    assert msg in json.dumps(res.get_json()), res.get_json()
    assert not _rec(app, eq)


# ---------------------------------------------------------------- custom factor with a parent fuel
def test_custom_factor_with_parent_fuel_and_gas_uncertainties(app, client, lifecycle_world):
    from extensions import db
    from models import CustomFactor

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    with app.app_context():
        cf = CustomFactor(name=f"Parent {tag}", co2_factor=60.0, ch4_factor=0.002, n2o_factor=0.0002, unit="kg/MMBtu",
                          source="lab", parent_fuel="Natural Gas", hhv_factor=1020.0, co2_uncertainty=2.0, ch4_uncertainty=40.0,
                          n2o_uncertainty=80.0, status="Approved", created_by=w["uids"]["admin"])
        db.session.add(cf)
        db.session.commit()
        cfid = cf.id
    _as(client, w, "admin")
    eq = f"PF{tag}"
    # 1000 scf of a fuel whose factor is per MMBtu: the parent fuel's heating value converts it
    res = client.post("/api/emissions/", json={"year": 2025, "month": 10, "facility_id": w["fids"]["in"],
                                               "process_type": "combustion", "fuel": f"Parent {tag}", "amount": 1000,
                                               "unit": "scf", "factor_source": "custom", "custom_factor_id": cfid,
                                               "equipment_id": eq})
    assert res.status_code == 201, res.get_json()
    e = _rec(app, eq)[0]
    mmbtu = 1000 * 1020 / 1e6
    assert e.co2_emissions == pytest.approx(mmbtu * 60.0 / 1000, rel=1e-6)
    assert e.uncertainty_ch4 is not None and e.uncertainty_ch4 > e.uncertainty


# ---------------------------------------------------------------- GWP standards on every entry path
@pytest.mark.parametrize("std,ch4,n2o", [("AR4", 25, 298), ("AR5", 28, 265), ("AR6", 29.8, 273)])
def test_gwp_standard_on_every_entry_path(app, client, lifecycle_world, std, ch4, n2o):
    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    _as(client, w, "admin")
    assert client.put("/api/auth/settings", json={"gwp_standard": std}).status_code == 200
    try:
        fname = _fname(app, w["fids"]["in"])
        rec = {**NG, "year": 2025, "month": 11, "amount": 1000}
        assert client.post("/api/emissions/", json={**rec, "facility_id": w["fids"]["in"], "equipment_id": f"G{tag}s"}).status_code == 201
        client.post("/api/emissions/import", json={"records": [{**rec, "facility_id": fname, "equipment_id": f"G{tag}j"}]})
        upload(client, 1, f"Date,Facility,Process Type,Fuel,Quantity,Unit,Equipment ID\n2025-11,{fname},combustion,"
                          f"Natural Gas,1000,MMBtu,G{tag}f\n")
        want = 1000 * (53.06 + 0.001 * ch4 + 0.0001 * n2o) / 1000
        for path in "sjf":
            e = _rec(app, f"G{tag}{path}")
            assert len(e) == 1, path
            assert e[0].co2e_total == pytest.approx(want, rel=1e-9), (path, e[0].co2e_total, want)
    finally:
        client.put("/api/auth/settings", json={"gwp_standard": "AR5"})


# ---------------------------------------------------------------- decimal marks, Excel per role
@pytest.mark.parametrize("cell,mark,expect", [("1,234.5", "point", 1234.5), ("1.234,5", "comma", 1234.5),
                                              ("1 234,5", "comma", 1234.5), ("1,5", "comma", 1.5),
                                              ("1,000", None, None), ("1.000,5", "point", None)])
def test_decimal_marks(app, client, lifecycle_world, cell, mark, expect):
    w = lifecycle_world
    fname = _fname(app, w["fids"]["in"])
    eq = f"DM{uuid.uuid4().hex[:6]}"
    _as(client, w, "user")
    form = {"decimal_mark": mark} if mark else {}
    st = upload(client, 1, f"Date,Facility,Process Type,Fuel,Quantity,Unit,Equipment ID\n2025-12,{fname},combustion,"
                           f"Natural Gas,\"{cell}\",MMBtu,{eq}\n", **form)
    recs = _rec(app, eq)
    if expect is None:
        assert not recs and st["skipped_count"] == 1, st
    else:
        assert recs and recs[0].quantity == pytest.approx(expect), st["skipped_preview"]


@pytest.mark.parametrize("actor", ["admin", "superuser", "user"])
def test_excel_upload_matches_csv_for_every_role(app, client, lifecycle_world, actor):
    import openpyxl

    w = lifecycle_world
    fname = _fname(app, w["fids"]["in"])
    tag = uuid.uuid4().hex[:4]
    head = ["Date", "Facility", "Process Type", "Fuel", "Quantity", "Unit", "Factor Type", "Equipment ID"]
    rows = [["2025-01", fname, "combustion", "Natural Gas", 5000, "scf", "default"],
            ["2025-02", fname, "combustion", "Diesel (No. 2 Fuel Oil)", 120.5, "gal", "default"],
            ["2025-03", fname, "flaring", "Natural Gas (Flaring)", 800, "m3", "default"]]
    _as(client, w, actor)
    upload(client, 1, ",".join(head) + "\n" + "\n".join(",".join(map(str, r + [f"XC{tag}{i}"])) for i, r in enumerate(rows)) + "\n")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(head)
    for i, r in enumerate(rows):
        ws.append(r + [f"XX{tag}{i}"])
    buf = io.BytesIO()
    wb.save(buf)
    st = upload(client, 1, buf.getvalue(), filename="rows.xlsx")
    assert st["skipped_count"] == 0, st["skipped_preview"]
    for i in range(len(rows)):
        a, b = _rec(app, f"XC{tag}{i}")[0], _rec(app, f"XX{tag}{i}")[0]
        assert b.co2e_total == pytest.approx(a.co2e_total, rel=1e-12) and b.status == a.status
        assert b.status == ("Verified" if actor == "admin" else "Pending")


# ---------------------------------------------------------------- dry run, job visibility, upload limit
@pytest.mark.parametrize("actor", ["admin", "superuser", "user"])
def test_dry_run_check_saves_nothing(app, client, lifecycle_world, actor):
    w = lifecycle_world
    fname = _fname(app, w["fids"]["in"])
    eq = f"DR{uuid.uuid4().hex[:6]}"
    _as(client, w, actor)
    before = _counts(app)[0]
    body = (f"Date,Facility,Process Type,Fuel,Quantity,Unit,Equipment ID\n2025-01,{fname},combustion,Natural Gas,10,MMBtu,{eq}\n"
            f"2025-13,{fname},combustion,Natural Gas,10,MMBtu,{eq}x\n")
    res = client.post("/api/emissions/upload/check", data={"scope": "1", "sample": "abc",
                                                           "file": (io.BytesIO(body.encode()), "c.csv")},
                      content_type="multipart/form-data")
    assert res.status_code == 200, res.get_json()
    out = res.get_json()
    assert _counts(app)[0] == before and not _rec(app, eq)
    assert json.dumps(out).count("Invalid date") >= 1


def test_upload_jobs_are_visible_to_their_owner_and_admins_only(app, client, lifecycle_world):
    import time

    w = lifecycle_world
    fname = _fname(app, w["fids"]["in"])
    _as(client, w, "user")
    res = client.post("/api/emissions/upload/start", data={"scope": "1", "file": (io.BytesIO(
        f"Date,Facility,Process Type,Fuel,Quantity,Unit\n2025-13,{fname},combustion,Natural Gas,1,MMBtu\n".encode()), "e.csv")},
        content_type="multipart/form-data")
    job = res.get_json()["job_id"]
    for _ in range(400):
        if client.get(f"/api/emissions/upload/status/{job}").get_json()["status"] != "processing":
            break
        time.sleep(0.05)
    assert client.get(f"/api/emissions/upload/errors/{job}").status_code == 200
    for other in ("user2", "superuser", "user_out"):
        _as(client, w, other)
        assert client.get(f"/api/emissions/upload/status/{job}").status_code == 404, other
        assert client.get(f"/api/emissions/upload/errors/{job}").status_code == 404, other
    _as(client, w, "admin")
    assert client.get(f"/api/emissions/upload/status/{job}").status_code == 200
    assert client.get(f"/api/emissions/upload/errors/{job}").status_code == 200
    assert client.get("/api/emissions/upload/errors/no-such-job").status_code == 404


def test_concurrent_upload_limit_per_user(app, client, lifecycle_world, monkeypatch):
    import routes.emissions_import as imp

    w = lifecycle_world
    monkeypatch.setenv("MAX_CONCURRENT_UPLOADS_PER_USER", "1")
    running = {"n": 1}
    monkeypatch.setattr(imp, "active_job_count", lambda uid: running["n"])
    _as(client, w, "user2")
    assert client.get("/api/emissions/upload/limits").status_code == 200
    r = client.post("/api/emissions/upload/start", data={"scope": "1", "file": (io.BytesIO(b"Date\n"), "a.csv")},
                    content_type="multipart/form-data")
    assert r.status_code == 429 and "uploads in progress" in r.get_json()["error"]
    running["n"] = 0
    r = client.post("/api/emissions/upload/start", data={"scope": "1", "file": (io.BytesIO(b"Date\n"), "a.csv")},
                    content_type="multipart/form-data")
    assert r.status_code == 200, r.get_json()


# ---------------------------------------------------------------- every numeric input of every method, bad values
SIGNED = {"blowdown_temp", "operating_temperature", "tank_api_gravity", "operating_pressure"}
TEXT_COLS = {"date", "facility_name", "process_type", "fuel", "unit", "tier", "equipment_id", "group", "source_ref",
             "region", "activity", "division", "field"}
RAW_ERRORS = ("could not convert", "float()", "invalid literal", "Traceback", "NoneType", "object has no attribute")


def test_bad_values_in_every_numeric_input_never_store_impossible_emissions(app, client, lifecycle_world):
    """Each template example row with each of its numeric inputs set to -5, text, nan, inf or 1e30: a row is
    refused with a readable reason, or stored with finite, non-negative emissions; a negative is accepted only
    where it is physical (temperatures, gauge pressure, API gravity)."""
    import math
    import time

    from services import scope1_template as T

    logging.disable(logging.CRITICAL)
    w = lifecycle_world
    fname = _fname(app, w["fids"]["in"])
    tag = uuid.uuid4().hex[:4]
    rows, meta = [], {}
    for proc, tier, cells in T.examples(fname):
        for c in T.columns_for(tier, (proc,), True):
            if c.choices or c.key in TEXT_COLS:
                continue
            for bad in ("-5", "abc", "nan", "inf", "1e30"):
                eq = f"BV{tag}{len(rows):05d}"
                meta[eq] = (proc, tier, c.key, bad)
                rows.append(dict(cells, date="2025-01", tier=tier, equipment_id=eq, **{c.key: bad}))
    keys = sorted({k for r in rows for k in r})
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(keys)
    for r in rows:
        wr.writerow([r.get(k, "") for k in keys])
    _as(client, w, "admin")
    res = client.post("/api/emissions/upload/start", data={"scope": "1", "global_factor_type": "auto", "decimal_mark": "point",
                                                           "file": (io.BytesIO(buf.getvalue().encode()), "bad.csv")},
                      content_type="multipart/form-data")
    job = res.get_json()["job_id"]
    for _ in range(3000):
        if client.get(f"/api/emissions/upload/status/{job}").get_json()["status"] != "processing":
            break
        time.sleep(0.1)
    errs = list(csv.DictReader(io.StringIO(client.get(f"/api/emissions/upload/errors/{job}").get_data(as_text=True))))
    reasons = {r.get("equipment_id"): r.get("Error Reason") or "" for r in errs}
    from models import Emission
    with app.app_context():
        saved = {e.equipment_id: e for e in Emission.query.filter(Emission.equipment_id.like(f"BV{tag}%")).all()}
    problems = []
    for eq, (proc, tier, key, bad) in meta.items():
        e = saved.get(eq)
        if e is None:
            if any(s in reasons.get(eq, "") for s in RAW_ERRORS):
                problems.append(f"{proc} T{tier} {key}={bad}: raw error '{reasons[eq][:80]}'")
            continue
        vals = (e.co2e_total, e.co2_emissions, e.ch4_emissions, e.n2o_emissions)
        if any(v is not None and (not math.isfinite(v) or v < 0) for v in vals):
            problems.append(f"{proc} T{tier} {key}={bad}: stored {vals}")
        if bad == "-5" and key not in SIGNED:
            problems.append(f"{proc} T{tier} {key}=-5 accepted")
        if bad in ("abc", "nan", "inf"):
            problems.append(f"{proc} T{tier} {key}={bad} accepted")
    print(f"\n{len(rows)} bad-value rows, {len(saved)} stored")
    assert not problems, "\n".join(sorted(set(problems))[:80])


@pytest.mark.parametrize("decision,body", [
    ("approve", {"scope": "all", "approve_all": True}),          # BatchReviewWizard "approve all"
    ("reject", {"scope": "all", "reject_all": True, "reason": "x"}),
    ("approve", {"scope": "1", "approve_all": True}),            # ManageData "approve all" for one scope
    ("reject", {"scope": "1", "reject_all": True, "reason": "x"})])
def test_approve_all_and_reject_all_as_the_screens_send_them(app, client, decision, body):
    """Every approve-all / reject-all answered 400 "Invalid scope: cap" (the removed CAP record type)."""
    from extensions import db
    from models import Emission, Facility, User

    tag = uuid.uuid4().hex[:6]
    with app.app_context():   # a region of its own, so approve-all touches only this test's records
        f = Facility(name=f"AA {tag}", region=f"AAR{tag}", activity="EP", division="D", field="F", segment="Upstream",
                     code=f"AA{tag}")
        rev = User(email=f"aa_r_{tag}@t.com", fullName="R", orgName="T", sector="E", role="superuser", location=f"AAR{tag}")
        mk = User(email=f"aa_m_{tag}@t.com", fullName="M", orgName="T", sector="E", role="user", location=f"AAR{tag}")
        for u in (rev, mk):
            u.set_password("AaPass12345!")
        db.session.add_all([f, rev, mk])
        db.session.commit()
        ids = [_seed(app, f.id, mk.id, status="Pending", equipment_id=f"AA{tag}{i}") for i in range(3)]
        rid = rev.id
    with client.session_transaction() as s:
        s["user_id"] = rid
    res = client.post(f"/api/emissions/{decision}/batch", json=body)
    assert res.status_code == 200, res.get_json()
    want = "Verified" if decision == "approve" else "Rejected"
    with app.app_context():
        assert [db.session.get(Emission, i).status for i in ids] == [want] * 3


@pytest.fixture(autouse=True)
def _restore_logging():
    """Tests here silence logging while they flood the importer; later tests must see errors again."""
    yield
    logging.disable(logging.NOTSET)


# ---------------------------------------------------------------- zero activity on every process
# Tier 3 examples whose activity is a method input (event count, device count, screening counts), not quantity
_OWN_ACTIVITY = {("unloading", "3"), ("pneumatic", "3"), ("fugitive", "3")}


def test_zero_activity_is_zero_emissions_on_every_process(app, client, lifecycle_world):
    """Quantity 0 stores zero (Tier 1 completions stored one completion, hundreds of tonnes; drilling, pneumatics
    and component fugitives were refused with "Unknown unit" or "operating hours are required")."""
    import time

    from services import scope1_template as T

    w = lifecycle_world
    fname = _fname(app, w["fids"]["in"])
    tag = uuid.uuid4().hex[:4]
    rows, meta = [], {}
    for i, (proc, tier, cells) in enumerate(T.examples(fname)):
        eq = f"Z{tag}E{i:03d}"
        meta[eq] = (proc, tier)
        rows.append(dict(cells, date="2025-01", tier=tier, equipment_id=eq, quantity="0"))
    for proc, names in T.fuels_by_process().items():
        for j, fuel in enumerate(names[:3]):
            eq = f"Z{tag}F{proc[:8]}{j}"
            meta[eq] = (proc, "1")
            rows.append(dict(date="2025-01", facility_name=fname, process_type=proc, fuel=fuel, quantity="0", tier="1",
                             unit=T.PROCESS_UNITS[proc][0], equipment_id=eq, operating_hours="744", activity_days="31"))
    keys = sorted({k for r in rows for k in r})
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(keys)
    for r in rows:
        wr.writerow([r.get(k, "") for k in keys])
    _as(client, w, "admin")
    res = client.post("/api/emissions/upload/start", data={"scope": "1", "global_factor_type": "auto",
                                                           "file": (io.BytesIO(buf.getvalue().encode()), "zero.csv")},
                      content_type="multipart/form-data")
    job = res.get_json()["job_id"]
    for _ in range(3000):
        if client.get(f"/api/emissions/upload/status/{job}").get_json()["status"] != "processing":
            break
        time.sleep(0.1)
    errs = {r.get("equipment_id"): r.get("Error Reason") or "" for r in csv.DictReader(io.StringIO(
        client.get(f"/api/emissions/upload/errors/{job}").get_data(as_text=True)))}
    from models import Emission
    with app.app_context():
        saved = {e.equipment_id: e.co2e_total for e in Emission.query.filter(Emission.equipment_id.like(f"Z{tag}%")).all()}
    problems = [f"{meta[eq]}: {v} t from quantity 0" for eq, v in saved.items() if v and meta[eq] not in _OWN_ACTIVITY]
    problems += [f"{meta[eq]}: refused '{msg[:90]}'" for eq, msg in errs.items() if eq in meta and
                 ("Unknown unit '" in msg and "drilling" in msg or "operating hours are required" in msg)]
    assert len(saved) >= len(rows) - 6, (len(saved), len(rows), errs)     # only unit mismatches are refused
    assert not problems, "\n".join(problems)


def test_zero_completions_are_zero_and_counts_are_counts(app, client, lifecycle_world):
    from services import scope1_template as T

    w = lifecycle_world
    fuel = T.fuels_by_process()["completions"][0]     # a catalog factor per completion event
    _as(client, w, "admin")
    out = {}
    for n in (0, 1, 3):
        eq = f"ZC{uuid.uuid4().hex[:6]}"
        res = client.post("/api/emissions/", json={"year": 2025, "month": 2, "facility_id": w["fids"]["in"],
                                                   "process_type": "completions", "fuel": fuel,
                                                   "amount": n, "unit": "events", "factor_source": "default",
                                                   "equipment_id": eq})
        assert res.status_code == 201, res.get_json()
        out[n] = _rec(app, eq)[0].co2e_total
    assert out[0] == 0 and out[1] > 0
    assert out[3] == pytest.approx(3 * out[1], rel=1e-9)
