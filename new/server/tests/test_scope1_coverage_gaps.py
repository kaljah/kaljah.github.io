"""Scope 1 gaps found by the 2026-10-16 coverage review (what no earlier test exercised).

1. Every unit the import template offers for a process is accepted by at least one row: a catalog fuel
   the template lists for that process, or the template's own example row with that unit. The template
   used to offer 20 units no calculator accepts (stoichiometry volumes, associated gas bbl/day / m3/day,
   dehydrator "units", completions Nm3).
2. Tier 3 completions accept Nm3 (normal m3, 0 C), converted to standard m3 first.
"""
import csv
import io
import logging
import uuid

import pytest

from services import scope1_template as T
from tests.test_bulk_uploaders import upload

# columns of an example row that carry their own unit and must follow a changed quantity unit
SUB_UNIT_COLS = ("tank_unit", "agr_unit")


@pytest.fixture
def site(app, client):
    from extensions import db
    from models import Facility, User

    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        f = Facility(name=f"Gap {tag}", region=f"GapR{tag}", activity="EP", division="D", field="F",
                     segment="Upstream", code=f"GAP{tag}")
        u = User(email=f"gap_{tag}@test.com", fullName="Gap Admin", orgName="T", sector="Energy", role="admin",
                 location="Global Corporate Head Office")
        u.set_password("GapAdmin123!")
        db.session.add_all([f, u])
        db.session.commit()
        with client.session_transaction() as s:
            s["user_id"] = u.id
        return {"fid": f.id, "name": f.name}


def _upload_rows(client, rows):
    keys = sorted({k for r in rows for k in r})
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(keys)
    for r in rows:
        w.writerow([r.get(k, "") for k in keys])
    return upload(client, 1, buf.getvalue(), gft="auto")


def _saved(app, fid):
    from models import Emission

    with app.app_context():
        return {e.equipment_id: e for e in Emission.query.filter_by(facility_id=fid).all()}


def test_every_offered_unit_is_accepted_by_some_row(app, client, site):
    logging.disable(logging.CRITICAL)
    name = site["name"]
    rows, owner = [], {}
    fuels = T.fuels_by_process()
    for proc, units in T.PROCESS_UNITS.items():
        for unit in units:
            for fuel in fuels.get(proc, []):
                eq = f"G{len(rows):05d}"
                owner[eq] = (proc, unit)
                rows.append(dict(date="2025-01", facility_name=name, process_type=proc, fuel=fuel, quantity="10",
                                 unit=unit, equipment_id=eq, tier="1"))
    for i, (proc, tier, cells) in enumerate(T.examples(name)):
        for unit in T.PROCESS_UNITS[proc]:
            eq = f"X{len(rows):05d}"
            owner[eq] = (proc, unit)
            row = dict(cells, date="2025-01", unit=unit, equipment_id=eq, tier=tier)
            for col in SUB_UNIT_COLS:
                if col in row:
                    row[col] = unit
            rows.append(row)
    st = _upload_rows(client, rows)
    assert st["status"] == "completed", st
    saved = _saved(app, site["fid"])
    accepted = {owner[eq] for eq in saved}
    dead = sorted({pair for pair in owner.values()} - accepted)
    offered = sum(len(u) for u in T.PROCESS_UNITS.values())
    print(f"\n{len(rows)} rows, {len(saved)} saved; {offered - len(dead)}/{offered} offered units accepted")
    assert not dead, f"the template offers units nothing accepts: {dead}"


def test_completions_tier3_normal_cubic_metres(app):
    from calculations.legacy_engine import compute_emissions
    from calculations.units import NM3_TO_SM3

    def run(unit, qty):
        p = {"process_type": "completions", "factor_source": "specific", "amount": qty, "unit": unit,
             "calc_inputs": {"completions": {"comp_method": "metered_volume", "ch4_content": 82, "co2_content": 3,
                                             "comp_flare_eff": 0, "tier": "tier3"}}}
        with app.app_context():
            em, _ = compute_emissions(p, {})
        return em

    nm3, sm3 = run("Nm3", 25000), run("Sm3", 25000 * NM3_TO_SM3)
    assert nm3["ch4"] > 0
    assert nm3["ch4"] == pytest.approx(sm3["ch4"], rel=1e-12)
    assert nm3["co2"] == pytest.approx(sm3["co2"], rel=1e-12)
    assert nm3["ch4"] > run("Sm3", 25000)["ch4"]   # 1 Nm3 holds more gas than 1 m3 at 60 F


# ---------------------------------------------------------------- record lifecycle, every combination
ACTORS = {  # name -> (role, region key)
    "admin": ("admin", None), "superuser": ("superuser", "in"), "superuser2": ("superuser", "in"),
    "user": ("user", "in"), "user2": ("user", "in"), "superuser_out": ("superuser", "out"),
    "user_out": ("user", "out"), "auditor": ("auditor", "in"), "it_admin": ("it_admin", None),
}
OWNERS = ("admin", "superuser", "user")
STATUSES = ("Pending", "Verified", "Rejected", "Draft")
ACTIONS = ("edit", "delete", "approve", "reject")


def expected_outcome(actor, owner, status, fac, action):
    """(HTTP status, resulting record status or None when deleted) from the documented rules:
    CLAUDE.md access control, services/maker_checker (BUG-067, BUG-0005, RC-2)."""
    role, region = ACTORS[actor]
    access = role == "admin" or (region == fac and role not in ("it_admin",))
    if action == "edit":
        if role in ("auditor", "it_admin"):
            return 403, status
        if not access or (role == "user" and owner != actor):
            return 403, status
        return 200, ("Pending" if status in ("Verified", "Rejected") and role != "admin" else status)
    if action == "delete":
        if role in ("auditor", "it_admin") or not access:
            return 403, status
        if role == "admin":
            return 200, None
        if status == "Verified" or (role == "user" and owner != actor):
            return 403, status
        return 200, None
    if role not in ("admin", "superuser") or not access:
        return 403, status
    if status != "Pending":
        return 409, status
    if action == "approve":
        return (403, status) if owner == actor else (200, "Verified")
    return 200, "Rejected"


@pytest.fixture(scope="module")
def lifecycle_world():
    from app import app as flask_app
    from extensions import db
    from models import Facility, User

    tag = uuid.uuid4().hex[:6]
    regions = {"in": f"LcIn{tag}", "out": f"LcOut{tag}"}
    with flask_app.app_context():
        facs = {k: Facility(name=f"Lc {k} {tag}", region=r, activity="EP", division="D", field="F",
                            segment="Upstream", code=f"LC{k}{tag}") for k, r in regions.items()}
        users = {}
        for name, (role, reg) in ACTORS.items():
            u = User(email=f"lc_{name}_{tag}@test.com", fullName=f"Lc {name}", orgName="T", sector="Energy",
                     role=role, location=regions[reg] if reg else "Global Corporate Head Office")
            u.set_password("LcPass12345!")
            users[name] = u
        db.session.add_all(list(facs.values()) + list(users.values()))
        db.session.commit()
        return {"fids": {k: f.id for k, f in facs.items()}, "uids": {k: u.id for k, u in users.items()}}


def test_record_lifecycle_every_role_owner_status_region_action(client, lifecycle_world):
    """9 accounts x 3 owners x 4 statuses x 2 regions x 4 actions = 864 cases, each on its own record."""
    import itertools

    from app import app as flask_app
    from extensions import db
    from models import ActivityLog, Emission

    logging.disable(logging.CRITICAL)
    w = lifecycle_world
    cases = list(itertools.product(ACTORS, OWNERS, STATUSES, ("in", "out"), ACTIONS))
    with flask_app.app_context():
        recs = []
        for i, (actor, owner, status, fac, action) in enumerate(cases):
            recs.append(Emission(record_id=str(uuid.uuid4()), year=2025, month=1 + i % 12, facility_id=w["fids"][fac],
                                 process_type="combustion", fuel_type="Natural Gas",
                                 quantity=100.0, unit="MMBtu", co2e_total=5.3, co2_emissions=5.3,
                                 status=status, created_by=w["uids"][owner], equipment_id=f"LC{i:04d}",
                                 approved_by=w["uids"]["admin"] if status == "Verified" else None))
        db.session.add_all(recs)
        db.session.commit()
        ids = [r.id for r in recs]

    fails = []
    for (actor, owner, status, fac, action), rid in zip(cases, ids):
        with client.session_transaction() as s:
            s["user_id"] = w["uids"][actor]
        with flask_app.app_context():
            logs_before = ActivityLog.query.count()
        if action == "edit":
            res = client.put(f"/api/emissions/{rid}", json={"equipment_id": f"EDITED{rid}"})
        elif action == "delete":
            res = client.delete(f"/api/emissions/{rid}")
        else:
            res = client.post(f"/api/emissions/{action}/{rid}", json={"scope": "1", "reason": "matrix"})
        code, after = expected_outcome(actor, owner, status, fac, action)
        with flask_app.app_context():
            rec = db.session.get(Emission, rid)
            logs_after = ActivityLog.query.count()
        got_status = rec.status if rec else None
        label = f"{actor} {action} {owner}'s {status} record ({fac})"
        if res.status_code != code:
            fails.append(f"{label}: HTTP {res.status_code}, expected {code}: {(res.get_json() or {}).get('error')}")
            continue
        if got_status != after:
            fails.append(f"{label}: status {got_status}, expected {after}")
        if code == 200:
            if action == "edit" and rec.equipment_id != f"EDITED{rid}":
                fails.append(f"{label}: edit not applied")
            if logs_after <= logs_before:
                fails.append(f"{label}: no audit entry")
            if action == "approve" and rec.approved_by != w["uids"][actor]:
                fails.append(f"{label}: approved_by {rec.approved_by}")
        else:
            if rec is None or rec.equipment_id != f"LC{cases.index((actor, owner, status, fac, action)):04d}":
                fails.append(f"{label}: refused but the record changed")
    print(f"\n{len(cases)} lifecycle cases, {len(fails)} mismatches")
    assert not fails, "\n".join(fails[:80])


# ---------------------------------------------------------------- manual entry checks no test reached
def _seed(app, fid, uid, **kw):
    from extensions import db
    from models import Emission

    base = dict(record_id=str(uuid.uuid4()), year=2025, month=1, facility_id=fid, process_type="combustion",
                fuel_type="Natural Gas", quantity=100.0, unit="MMBtu", co2e_total=5.3,
                co2_emissions=5.3, status="Verified", created_by=uid)
    base.update(kw)
    with app.app_context():
        e = Emission(**base)
        db.session.add(e)
        db.session.commit()
        return e.id


def _as(client, w, actor):
    with client.session_transaction() as s:
        s["user_id"] = w["uids"][actor]


AGV = {"process_type": "associated_gas_venting", "fuel": "Associated Gas Venting - US Average", "amount": 1000,
       "unit": "bbl", "factor_source": "default", "year": 2025, "month": 3}


@pytest.mark.parametrize("change,field", [
    ({"ch4_content": 150}, "ch4_content"), ({"ch4_content": -1}, "ch4_content"), ({"ch4_content": "abc"}, "ch4_content"),
    ({"co2_content": 101}, "co2_content"), ({"co2_content": "x"}, "co2_content"),
    ({"ch4_content": 80, "co2_content": 30}, "ch4_content"),               # sum above 100 %
    ({"venting_duration": -1}, "venting_duration"), ({"venting_duration": 400}, "venting_duration"),
    ({"venting_duration": 9000, "duration_unit": "hours"}, "venting_duration"), ({"venting_duration": "x"}, "venting_duration"),
    ({"gor": -5}, "gor"), ({"gor": "x"}, "gor"),
    ({"recovered_gas_volume": -1}, "recovered_gas_volume"), ({"flared_gas_volume": "x"}, "flared_gas_volume"),
])
def test_associated_gas_inputs_are_checked(client, lifecycle_world, change, field):
    w = lifecycle_world
    _as(client, w, "user")
    res = client.post("/api/emissions/", json={**AGV, **change, "facility_id": w["fids"]["in"],
                                               "equipment_id": f"AG{uuid.uuid4().hex[:6]}"})
    assert res.status_code == 422 and res.get_json()["field"] == field, res.get_json()


def test_associated_gas_valid_boundaries_pass(client, lifecycle_world):
    w = lifecycle_world
    _as(client, w, "user")
    for i, ok in enumerate([{"ch4_content": 70, "co2_content": 30}, {"venting_duration": 366},
                            {"venting_duration": 8784, "duration_unit": "hours"}, {"gor": 0}]):
        res = client.post("/api/emissions/", json={**AGV, **ok, "facility_id": w["fids"]["in"],
                                                   "equipment_id": f"AGOK{i}{uuid.uuid4().hex[:4]}"})
        assert res.status_code == 201, (ok, res.get_json())


def test_statistical_outlier_goes_to_review_even_for_admin(app, client, lifecycle_world):
    from models import Emission

    w = lifecycle_world
    eq = f"AN{uuid.uuid4().hex[:6]}"
    for m, v in enumerate([100, 104, 97, 101, 99, 103], start=1):
        _seed(app, w["fids"]["in"], w["uids"]["admin"], year=2024, month=m + 4, equipment_id=eq, co2e_total=v)
    _as(client, w, "admin")
    # 1,000,000 MMBtu of natural gas ~ 53,100 t: far outside a ~100 t series
    res = client.post("/api/emissions/", json={"year": 2025, "month": 1, "facility_id": w["fids"]["in"],
                                               "process_type": "combustion", "fuel": "Natural Gas", "amount": 1_000_000,
                                               "unit": "MMBtu", "factor_source": "default", "equipment_id": eq})
    assert res.status_code == 201
    with app.app_context():
        rec = Emission.query.filter_by(equipment_id=eq, year=2025).one()
    assert rec.status == "Pending" and rec.qa_flag and rec.approved_by is None


def test_failed_anomaly_check_sends_the_record_to_review(app, client, lifecycle_world, monkeypatch):
    from calculations import anomaly
    from models import Emission

    def boom(*a, **k):
        raise RuntimeError("history unavailable")

    monkeypatch.setattr(anomaly.AnomalyDetector, "check_scope1", boom)
    w = lifecycle_world
    eq = f"AF{uuid.uuid4().hex[:6]}"
    _as(client, w, "admin")
    res = client.post("/api/emissions/", json={"year": 2025, "month": 2, "facility_id": w["fids"]["in"],
                                               "process_type": "combustion", "fuel": "Natural Gas", "amount": 10,
                                               "unit": "MMBtu", "factor_source": "default", "equipment_id": eq})
    assert res.status_code == 201
    with app.app_context():
        rec = Emission.query.filter_by(equipment_id=eq).one()
    assert rec.status == "Pending" and "could not run" in rec.qa_flag


@pytest.mark.parametrize("amount,code", [(1.0e7, 201),      # ~531,000 t: below the review bound
                                         (2.0e7, 201),      # ~1.06 Mt: flagged for review
                                         (2.0e9, 422)])     # ~106 Mt: refused
def test_plausibility_bounds_on_manual_entry(app, client, lifecycle_world, amount, code):
    from models import Emission

    w = lifecycle_world
    eq = f"PB{uuid.uuid4().hex[:6]}"
    _as(client, w, "admin")
    res = client.post("/api/emissions/", json={"year": 2025, "month": 4, "facility_id": w["fids"]["in"],
                                               "process_type": "combustion", "fuel": "Natural Gas", "amount": amount,
                                               "unit": "MMBtu", "factor_source": "default", "equipment_id": eq})
    assert res.status_code == code, res.get_json()
    with app.app_context():
        recs = Emission.query.filter_by(equipment_id=eq).all()
    if code == 422:
        assert not recs and res.get_json()["field"] == "amount"
    elif amount >= 2.0e7:
        assert recs[0].status == "Pending" and "Plausibility" in recs[0].qa_flag
    else:  # a first record of a new source has no history: an admin's entry is Verified
        assert recs[0].status == "Verified" and not recs[0].qa_flag


def test_edit_plausibility_reject_keeps_record_and_flag_demotes(app, client, lifecycle_world):
    from extensions import db
    from models import Emission

    w = lifecycle_world
    rid = _seed(app, w["fids"]["in"], w["uids"]["admin"], equipment_id=f"EP{uuid.uuid4().hex[:6]}",
                approved_by=w["uids"]["admin"])
    _as(client, w, "admin")
    res = client.put(f"/api/emissions/{rid}", json={"amount": 2.0e9, "unit": "MMBtu", "fuel": "Natural Gas"})
    assert res.status_code == 422
    with app.app_context():
        rec = db.session.get(Emission, rid)
        assert rec.quantity == 100.0 and rec.status == "Verified"
    res = client.put(f"/api/emissions/{rid}", json={"amount": 2.0e7, "unit": "MMBtu", "fuel": "Natural Gas"})
    assert res.status_code == 200, res.get_json()
    with app.app_context():
        rec = db.session.get(Emission, rid)
        assert rec.quantity == 2.0e7 and rec.status == "Pending" and "Plausibility" in rec.qa_flag
        assert rec.approved_by is None


def test_edit_metadata_is_merged_into_the_source_payload(app, client, lifecycle_world):
    import json

    from extensions import db
    from models import Emission

    w = lifecycle_world
    rid = _seed(app, w["fids"]["in"], w["uids"]["user"], status="Pending", source_payload=json.dumps({"keep": 1}))
    _as(client, w, "user")
    assert client.put(f"/api/emissions/{rid}", json={"metadata": {"meter": "M-7"}}).status_code == 200
    with app.app_context():
        assert json.loads(db.session.get(Emission, rid).source_payload) == {"keep": 1, "meter": "M-7"}


def test_goal_notifications_at_80_percent_and_when_exceeded(app, client, lifecycle_world):
    from extensions import db
    from models import Emission, Goal, Notification, Scope2Emission
    from sqlalchemy import func

    w = lifecycle_world
    year, uid = 2003, w["uids"]["admin"]     # a year no other test writes; the goal is set relative to its total
    with app.app_context():
        base = (db.session.query(func.sum(Emission.co2e_total))
                .filter(Emission.year == year, Emission.status == "Verified").scalar() or 0) \
            + (db.session.query(func.sum(Scope2Emission.co2e))
               .filter(Scope2Emission.year == year, Scope2Emission.status == "Verified").scalar() or 0)
        target = 4 * base + 1000.0
        g = db.session.get(Goal, year) or Goal(year=year)
        g.target_amount = target
        db.session.add(g)
        Notification.query.filter_by(user_id=uid).delete()
        db.session.commit()
    _as(client, w, "admin")

    def post(t):   # natural gas at 53.088 kg CO2e/MMBtu; records stay below the 1 Mt review bound
        while t > 1e-9:
            part = min(t, 5e5)
            r = client.post("/api/emissions/", json={"year": year, "month": 1, "facility_id": w["fids"]["in"],
                                                     "process_type": "combustion", "fuel": "Natural Gas",
                                                     "amount": part / 0.053088, "unit": "MMBtu", "factor_source": "default",
                                                     "equipment_id": f"GOAL{uuid.uuid4().hex[:6]}"})
            assert r.status_code == 201, r.get_json()
            t -= part

    def titles():
        with app.app_context():
            return {n.title for n in Notification.query.filter_by(user_id=uid).all()}

    try:
        post(0.5 * target - base)                                   # 50 % of the goal
        goal_titles = {f"Goal Warning for {year}", f"Goal Exceeded for {year}"}
        assert not goal_titles & titles(), titles()
        post(0.35 * target)                                         # 85 %
        assert f"Goal Warning for {year}" in titles()
        assert f"Goal Exceeded for {year}" not in titles()
        post(0.30 * target)                                         # 115 %
        assert f"Goal Exceeded for {year}" in titles()
    finally:
        with app.app_context():
            db.session.delete(db.session.get(Goal, year))
            db.session.commit()


# ---------------------------------------------------------------- the record list: filters and scope
def test_record_list_filters_paging_and_scope(app, client, lifecycle_world):
    w = lifecycle_world
    fin, fout = w["fids"]["in"], w["fids"]["out"]
    year = 1995   # no other test writes this year
    tag = uuid.uuid4().hex[:4]
    seeded = []
    for i in range(24):
        kw = dict(year=year, month=1 + i % 12, status=("Verified", "Pending", "Rejected", "Draft")[i % 4],
                  process_type=("combustion", "flaring")[i % 2], fuel_type=("Natural Gas", "Diesel")[i % 2],
                  division=("Prod", "Gas")[i % 2], field=("North", "South")[(i // 2) % 2],
                  calc_method=("server_default", "api2021_generic")[(i // 3) % 2], equipment_id=f"LS{tag}{i:02d}")
        fid = fin if i < 16 else fout
        seeded.append((fid, kw))
        _seed(app, fid, w["uids"]["admin"], **kw)

    def ids(actor, **q):
        _as(client, w, actor)
        res = client.get("/api/emissions/", query_string={"scope": "1", "year": year, "limit": 5000, "offset": 0, **q})
        assert res.status_code == 200, res.get_json()
        return {r.get("equipment_id") for r in res.get_json()["data"]
                if str(r.get("equipment_id") or "").startswith(f"LS{tag}")}

    def want(pred):
        return {kw["equipment_id"] for fid, kw in seeded if pred(fid, kw)}

    assert ids("admin") == want(lambda f, k: True)
    assert ids("superuser") == want(lambda f, k: f == fin)            # region scope
    assert ids("user_out") == want(lambda f, k: f == fout)
    assert ids("admin", month=3) == want(lambda f, k: k["month"] == 3)
    assert ids("admin", status="Verified,Pending") == want(lambda f, k: k["status"] in ("Verified", "Pending"))
    assert ids("admin", facility_id=fout) == want(lambda f, k: f == fout)
    assert ids("admin", process="flaring") == want(lambda f, k: k["process_type"] == "flaring")
    assert ids("admin", division="gas") == want(lambda f, k: k["division"] == "Gas")
    assert ids("admin", field="nor") == want(lambda f, k: k["field"] == "North")
    assert ids("admin", method="api2021") == want(lambda f, k: k["calc_method"] == "api2021_generic")
    assert ids("admin", search="Diesel") == want(lambda f, k: k["fuel_type"] == "Diesel")
    assert ids("admin", search="100%") == set()                       # LIKE wildcards are literal
    assert ids("admin", scope="2") == set()

    # paging: an offset that is not a multiple of the page size is honoured exactly
    _as(client, w, "admin")
    q = {"scope": "1", "year": year, "facility_id": fin}
    full = client.get("/api/emissions/", query_string={**q, "limit": 5000, "offset": 0}).get_json()
    page = client.get("/api/emissions/", query_string={**q, "limit": 5, "offset": 3}).get_json()
    assert full["total"] == 16 and page["total"] == 16 and len(page["data"]) == 5
    assert [r["id"] for r in page["data"]] == [r["id"] for r in full["data"]][3:8]
    for bad in ({"limit": "x", "offset": "y"}, {"page": "x"}, {"limit": "-4"}, {"limit": "all"}):
        res = client.get("/api/emissions/", query_string={**q, **bad})
        assert res.status_code == 200 and res.get_json()["total"] == 16, (bad, res.get_json())


# ---------------------------------------------------------------- export and review queue: region scope
def test_export_is_scoped_and_filtered(app, client, lifecycle_world):
    w = lifecycle_world
    fin, fout = w["fids"]["in"], w["fids"]["out"]
    year, tag = 1996, uuid.uuid4().hex[:4]
    seeded = []
    for i in range(12):
        rid = f"EXP{tag}{i:02d}"
        kw = dict(record_id=rid, year=year, month=1 + i % 6, process_type=("combustion", "flaring")[i % 2],
                  fuel_type=("Natural Gas", "Diesel")[i % 2], division=("Prod", "Gas")[i % 2],
                  field=("North", "South")[(i // 2) % 2], calc_method=("server_default", "api2021_generic")[(i // 3) % 2])
        fid = fin if i < 8 else fout
        seeded.append((fid, kw))
        _seed(app, fid, w["uids"]["admin"], **kw)

    def got(actor, **q):
        _as(client, w, actor)
        res = client.get("/api/emissions/export", query_string={"scope": "1", "year": year, "format": "json", **q})
        return res.status_code, {r["record_id"] for r in (res.get_json() or {}).get("data", [])
                                 if str(r.get("record_id", "")).startswith(f"EXP{tag}")}

    def want(pred):
        return {kw["record_id"] for fid, kw in seeded if pred(fid, kw)}

    assert got("admin") == (200, want(lambda f, k: True))
    assert got("superuser") == (200, want(lambda f, k: f == fin))
    assert got("user") == (200, want(lambda f, k: f == fin))
    assert got("user_out") == (200, want(lambda f, k: f == fout))
    assert got("user", facility_id=fout)[0] == 403                   # another region's facility
    assert got("it_admin")[0] == 403
    assert got("admin", month=2) == (200, want(lambda f, k: k["month"] == 2))
    assert got("admin", facility_id=fout) == (200, want(lambda f, k: f == fout))
    assert got("admin", process="flaring") == (200, want(lambda f, k: k["process_type"] == "flaring"))
    assert got("admin", division="gas") == (200, want(lambda f, k: k["division"] == "Gas"))
    assert got("admin", field="sou") == (200, want(lambda f, k: k["field"] == "South"))
    assert got("admin", method="api2021") == (200, want(lambda f, k: k["calc_method"] == "api2021_generic"))
    assert got("admin", search="diesel") == (200, want(lambda f, k: k["fuel_type"] == "Diesel"))
    _as(client, w, "superuser")
    res = client.get("/api/emissions/export", query_string={"scope": "1", "year": year, "format": "xlsx"})
    assert res.status_code == 200 and res.data[:2] == b"PK"               # an xlsx workbook


def test_review_queue_is_scoped_and_closed_to_makers(app, client, lifecycle_world):
    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    rin = _seed(app, w["fids"]["in"], w["uids"]["user"], status="Pending", equipment_id=f"Q{tag}in",
                ef_used_co2=53.06, ef_used_ch4=0.001, ef_used_n2o=0.0001)
    rout = _seed(app, w["fids"]["out"], w["uids"]["user_out"], status="Pending", equipment_id=f"Q{tag}out")
    draft = _seed(app, w["fids"]["in"], w["uids"]["user"], status="Draft", equipment_id=f"Q{tag}dr")

    def queue(actor, **q):
        _as(client, w, actor)
        res = client.get("/api/emissions/pending", query_string={"all": "true", **q})
        return res.status_code, {r["id"] for r in (res.get_json() or {}).get("scope1", [])}

    code, ids = queue("superuser")
    assert code == 200 and rin in ids and rout not in ids and draft not in ids
    code, ids = queue("admin")
    assert code == 200 and {rin, rout} <= ids and draft not in ids
    assert queue("user")[0] == 403 and queue("auditor")[0] == 403
    _as(client, w, "admin")
    assert client.get("/api/emissions/pending", query_string={"limit": "x"}).status_code == 200
    rows = client.get("/api/emissions/pending", query_string={"all": "true"}).get_json()["scope1"]
    row = next(r for r in rows if r["id"] == rin)
    assert "CO2: 53.06" in str(row) and "CH4: 0.001" in str(row)       # the factors shown to the reviewer


# ---------------------------------------------------------------- Excel: Tier 3 parameter sheets
def test_excel_tier3_sheet_parameters_reach_the_rows(app, client, lifecycle_world):
    import openpyxl

    from extensions import db
    from models import Emission, Facility

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    _as(client, w, "admin")
    with app.app_context():
        fname = db.session.get(Facility, w["fids"]["in"]).name
    comp = dict(c1=87.5, c2=5.2, c3=2.1, c4=1.0, c5=0.5, co2_mol=1.8, n2_mol=1.9, combustion_efficiency=99.5)
    head = ["Date", "Facility", "Process Type", "Fuel", "Quantity", "Unit", "Tier", "Equipment ID"]
    # reference: the same composition inline in a CSV row
    inline = ",".join(head + list(comp)) + "\n" + ",".join(
        ["2025-05", fname, "combustion", "Natural Gas", "50000", "scf", "3", f"T3{tag}csv"] + [str(v) for v in comp.values()]) + "\n"
    st = upload(client, 1, inline, gft="auto")
    assert st["skipped_count"] == 0, st["skipped_preview"]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Entry"
    ws.append(head)
    ws.append(["2025-05", fname, "combustion", "Natural Gas", 50000, "scf", "3", f"T3{tag}x"])     # all months
    ws.append(["2025-06", fname, "combustion", "Natural Gas", 50000, "scf", "3", f"T3{tag}m"])     # month-specific
    t3 = wb.create_sheet("Gas Composition")
    t3.append(["Equipment ID", "Date"] + list(comp))
    t3.append([f"T3{tag}x", None] + list(comp.values()))
    t3.append([f"T3{tag}m", "2025-06"] + list(comp.values()))
    t3.append([f"T3{tag}m", "2025-07"] + [99, 0, 0, 0, 0, 0.5, 0.5, 99.5])                              # other month: unused
    t3.append([None, None] + [1] * 8)                                                             # no equipment: ignored
    buf = io.BytesIO()
    wb.save(buf)
    st = upload(client, 1, buf.getvalue(), filename="t3.xlsx", gft="auto")
    assert st["skipped_count"] == 0, st["skipped_preview"]
    with app.app_context():
        ref = Emission.query.filter_by(equipment_id=f"T3{tag}csv").one()
        for eq in (f"T3{tag}x", f"T3{tag}m"):
            rec = Emission.query.filter_by(equipment_id=eq).one()
            assert rec.co2e_total == pytest.approx(ref.co2e_total, rel=1e-12), eq
            assert rec.co2_emissions == pytest.approx(ref.co2_emissions, rel=1e-12), eq




@pytest.fixture(autouse=True)
def _restore_logging():
    yield
    logging.disable(logging.NOTSET)
