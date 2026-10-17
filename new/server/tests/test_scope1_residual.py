"""Scope 1 behaviour left untested after test_scope1_coverage_gaps (second coverage pass, 2026-10-16).

Sign-in states on every Scope 1 route, failure atomicity (a failing commit leaves no record, no audit
entry and no raw error text), batch review rules, QA/QC export, formula escaping in exports, saved
column mappings, JSON import details, the bulk overwrite rules per role, entered Tier 3 factor units,
custom factors with a parent fuel, GWP standards on every entry path, decimal marks, Excel per role,
upload job visibility and the concurrent upload limit.
"""
import csv
import io
import json
import logging
import uuid

import pytest

from tests.test_bulk_uploaders import upload
from tests.test_scope1_coverage_gaps import ACTORS, _as, _seed, lifecycle_world  # noqa: F401

NG = {"process_type": "combustion", "fuel": "Natural Gas", "unit": "MMBtu", "factor_source": "default"}


def _fname(app, fid):
    from extensions import db
    from models import Facility

    with app.app_context():
        return db.session.get(Facility, fid).name


def _rec(app, eq):
    from models import Emission

    with app.app_context():
        return Emission.query.filter_by(equipment_id=eq).all()


def _counts(app):
    from models import ActivityLog, Emission

    with app.app_context():
        return Emission.query.count(), ActivityLog.query.count()


# ---------------------------------------------------------------- sign-in states on every Scope 1 route
ROUTES = [("get", "/api/emissions/"), ("post", "/api/emissions/"), ("put", "/api/emissions/1"),
          ("delete", "/api/emissions/1"), ("post", "/api/emissions/bulk-delete"), ("post", "/api/emissions/import"),
          ("post", "/api/emissions/bulk-upload"), ("post", "/api/emissions/upload/start"),
          ("post", "/api/emissions/upload/check"), ("get", "/api/emissions/upload/limits"),
          ("get", "/api/emissions/upload/status/x"), ("get", "/api/emissions/upload/errors/x"),
          ("get", "/api/emissions/export"), ("post", "/api/emissions/approve/1"), ("post", "/api/emissions/reject/1"),
          ("post", "/api/emissions/approve/batch"), ("post", "/api/emissions/reject/batch"),
          ("get", "/api/emissions/pending"), ("post", "/api/emissions/erp/sync"),
          ("get", "/api/emissions/template/csv"), ("get", "/api/emissions/template/excel"),
          ("get", "/api/emissions/upload/mappings"), ("post", "/api/emissions/upload/mappings"),
          ("get", "/api/qaqc/dashboard"), ("get", "/api/qaqc/export"), ("post", "/api/qaqc/resolve/1"),
          ("post", "/api/qaqc/bulk-resolve"), ("get", "/api/custom-factors"), ("post", "/api/custom-factors")]


@pytest.mark.parametrize("state,code", [("anonymous", 401), ("deleted", 401), ("disabled", 403)])
def test_every_scope1_route_refuses_without_a_valid_session(app, client, state, code):
    from extensions import db
    from models import User

    tag = uuid.uuid4().hex[:6]
    before = _counts(app)
    with app.app_context():
        u = User(email=f"ss_{tag}@test.com", fullName="S", orgName="T", sector="E", role="admin", location="Global")
        u.set_password("SessPass123!")
        db.session.add(u)
        db.session.commit()
        uid = u.id
        if state == "disabled":
            u.status = "disabled"
            db.session.commit()
        if state == "deleted":
            db.session.delete(u)
            db.session.commit()
    with client.session_transaction() as s:
        if state != "anonymous":
            s["user_id"] = uid
        else:
            s.pop("user_id", None)
    bad = []
    for method, url in ROUTES:
        res = getattr(client, method)(url, json={})
        if res.status_code != code:
            bad.append(f"{method.upper()} {url}: {res.status_code}")
        if state != "anonymous":   # the refused session is ended
            with client.session_transaction() as s:
                s["user_id"] = uid
    assert not bad, bad
    assert _counts(app)[0] == before[0]


# ---------------------------------------------------------------- failure atomicity
@pytest.fixture
def failing_commit(app, monkeypatch):
    """Every commit raises; Flask answers 500 instead of re-raising into the test."""
    from extensions import db

    monkeypatch.setitem(app.config, "PROPAGATE_EXCEPTIONS", False)
    state = {"on": False}
    real = db.session.commit

    def commit():
        if state["on"]:
            raise RuntimeError("SECRET-DB-FAILURE")
        return real()

    monkeypatch.setattr(db.session, "commit", commit)
    return state


def test_a_failing_commit_saves_nothing_and_hides_the_error(app, client, lifecycle_world, failing_commit):
    logging.disable(logging.CRITICAL)
    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    pend = _seed(app, w["fids"]["in"], w["uids"]["user"], status="Pending", equipment_id=f"FC{tag}p")
    pend2 = _seed(app, w["fids"]["in"], w["uids"]["user"], status="Pending", equipment_id=f"FC{tag}q")
    mine = _seed(app, w["fids"]["in"], w["uids"]["admin"], status="Verified", equipment_id=f"FC{tag}v")
    fname = _fname(app, w["fids"]["in"])
    calls = [
        ("admin", "post", "/api/emissions/", {**NG, "year": 2025, "month": 5, "amount": 10, "facility_id": w["fids"]["in"],
                                              "equipment_id": f"FC{tag}new"}),
        ("admin", "put", f"/api/emissions/{mine}", {"equipment_id": f"FC{tag}changed"}),
        ("admin", "delete", f"/api/emissions/{mine}", None),
        ("admin", "post", "/api/emissions/bulk-delete", {"ids": [mine]}),
        ("admin", "post", f"/api/emissions/approve/{pend}", {"scope": "1"}),
        ("admin", "post", f"/api/emissions/reject/{pend}", {"scope": "1"}),
        ("admin", "post", "/api/emissions/approve/batch", {"scope": "1", "ids": [pend, pend2]}),
        ("admin", "post", "/api/emissions/reject/batch", {"scope": "1", "ids": [pend, pend2]}),
        ("admin", "post", "/api/emissions/import", {"records": [{**NG, "year": 2025, "month": 6, "amount": 10,
                                                                 "facility_id": fname, "equipment_id": f"FC{tag}json"}]}),
        ("admin", "post", "/api/emissions/bulk-upload", {"confirm": True, "records": [
            {"date": "2025-07-01", "facility_name": fname, "process_type": "combustion", "fuel": "Natural Gas",
             "quantity": "10", "unit": "MMBtu", "equipment": f"FC{tag}leg"}]}),
        ("admin", "post", f"/api/qaqc/resolve/{pend}", {"resolution": "Verified", "scope": 1}),
        ("admin", "post", "/api/qaqc/bulk-resolve", {"records": [{"id": pend, "scope": 1}], "resolution": "Verified"}),
        ("admin", "post", "/api/custom-factors", {"name": f"FC {tag}", "co2_factor": 50, "unit": "kg/MMBtu", "source": "lab"}),
        ("admin", "post", "/api/custom-factors/import", {"factors": [{"name": f"FCI {tag}", "unit": "kg/MMBtu",
                                                                      "co2_factor": 50, "source": "lab"}]}),
    ]
    problems = []
    for actor, method, url, body in calls:
        _as(client, w, actor)
        before = _counts(app)
        failing_commit["on"] = True
        res = getattr(client, method)(url, json=body) if body is not None else getattr(client, method)(url)
        failing_commit["on"] = False
        text = res.get_data(as_text=True)
        if res.status_code < 500:
            problems.append(f"{method.upper()} {url}: {res.status_code} {text[:120]}")
        if "SECRET-DB-FAILURE" in text:
            problems.append(f"{method.upper()} {url}: the raw error reached the client")
        if _counts(app) != before:
            problems.append(f"{method.upper()} {url}: records or audit entries changed {before} -> {_counts(app)}")
    from extensions import db
    from models import Emission
    with app.app_context():
        assert db.session.get(Emission, pend).status == "Pending"
        assert db.session.get(Emission, mine).equipment_id == f"FC{tag}v"
    assert not problems, "\n".join(problems)


def test_a_failing_notification_check_does_not_lose_the_record(app, client, lifecycle_world, monkeypatch):
    from extensions import db
    from models import Goal, User

    w = lifecycle_world
    with app.app_context():
        db.session.merge(Goal(year=2002, target_amount=1.0))
        db.session.commit()
    monkeypatch.setattr(User, "preferences", property(lambda self: "{not json"), raising=False)
    _as(client, w, "admin")
    eq = f"NC{uuid.uuid4().hex[:4]}"
    try:
        res = client.post("/api/emissions/", json={**NG, "year": 2002, "month": 1, "amount": 10,
                                                   "facility_id": w["fids"]["in"], "equipment_id": eq})
    finally:
        monkeypatch.undo()
        with app.app_context():
            db.session.delete(db.session.get(Goal, 2002))
            db.session.commit()
    assert res.status_code == 201 and len(_rec(app, eq)) == 1


def test_goal_notifications_respect_the_preference_and_are_not_repeated(app, client, lifecycle_world):
    from extensions import db
    from models import Goal, Notification, User

    w = lifecycle_world
    uid = w["uids"]["admin"]
    year = 2001
    with app.app_context():
        db.session.merge(Goal(year=year, target_amount=0.001))   # any record exceeds it
        Notification.query.filter_by(user_id=uid).delete()
        u = db.session.get(User, uid)
        u.preferences = json.dumps({"notifTargets": False})
        db.session.commit()
    _as(client, w, "admin")

    def post():
        return client.post("/api/emissions/", json={**NG, "year": year, "month": 1, "amount": 10,
                                                    "facility_id": w["fids"]["in"],
                                                    "equipment_id": f"GP{uuid.uuid4().hex[:6]}"}).status_code

    def exceeded():
        with app.app_context():
            return Notification.query.filter_by(user_id=uid, title=f"Goal Exceeded for {year}").all()

    try:
        assert post() == 201 and not exceeded()                  # the user turned goal notices off
        with app.app_context():
            db.session.get(User, uid).preferences = json.dumps({"notifTargets": True})
            db.session.commit()
        assert post() == 201 and len(exceeded()) == 1
        first = exceeded()[0].message
        assert post() == 201
        notes = exceeded()
        assert len(notes) == 1 and notes[0].message != first     # updated, not repeated
    finally:
        with app.app_context():
            db.session.delete(db.session.get(Goal, year))
            db.session.get(User, uid).preferences = None
            db.session.commit()


# ---------------------------------------------------------------- record ids, aliases, edits of other fields
def test_records_are_addressable_by_record_id_and_prefixed_id(app, client, lifecycle_world):
    from extensions import db
    from models import Emission

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    a = _seed(app, w["fids"]["in"], w["uids"]["admin"], equipment_id=f"ID{tag}a")
    b = _seed(app, w["fids"]["in"], w["uids"]["admin"], equipment_id=f"ID{tag}b")
    with app.app_context():
        uuid_a = db.session.get(Emission, a).record_id
    _as(client, w, "admin")
    assert client.put(f"/api/emissions/{uuid_a}", json={"group_name": "Station 4"}).status_code == 200
    assert client.put(f"/api/emissions/s1_{b}", json={"data_source_ref": "MTR-77"}).status_code == 200
    with app.app_context():
        assert db.session.get(Emission, a).group_name == "Station 4"
        assert db.session.get(Emission, b).data_source_ref == "MTR-77"
    assert client.put("/api/emissions/999999999", json={"group_name": "x"}).status_code == 404
    assert client.delete("/api/emissions/999999999").status_code == 404
    assert client.delete("/api/emissions/not-a-record").status_code == 404
    assert client.delete(f"/api/emissions/s1_{b}").status_code == 200
    assert client.delete(f"/api/emissions/{uuid_a}").status_code == 200
    with app.app_context():
        assert db.session.get(Emission, a) is None and db.session.get(Emission, b) is None


def test_source_type_is_accepted_for_process_type(app, client, lifecycle_world):
    w = lifecycle_world
    _as(client, w, "user")
    eq = f"ST{uuid.uuid4().hex[:4]}"
    body = {**NG, "year": 2025, "month": 8, "amount": 10, "facility_id": w["fids"]["in"], "equipment_id": eq}
    body["source_type"] = body.pop("process_type")
    assert client.post("/api/emissions/", json=body).status_code == 201
    assert _rec(app, eq)[0].process_type == "combustion"


def test_edit_with_a_corrupt_stored_payload_still_works(app, client, lifecycle_world):
    from extensions import db
    from models import Emission

    w = lifecycle_world
    rid = _seed(app, w["fids"]["in"], w["uids"]["user"], status="Pending", factor_source="default",
                source_payload="{corrupt", equipment_id=f"CP{uuid.uuid4().hex[:4]}")
    _as(client, w, "user")
    assert client.put(f"/api/emissions/{rid}", json={"amount": 300}).status_code == 200
    assert client.put(f"/api/emissions/{rid}", json={"metadata": {"meter": "M1"}}).status_code == 200
    with app.app_context():
        e = db.session.get(Emission, rid)
        assert e.quantity == 300 and json.loads(e.source_payload)["meter"] == "M1"


# ---------------------------------------------------------------- record list leftovers
def test_record_list_baseline_year_and_custom_factor_names(app, client, lifecycle_world):
    from extensions import db
    from models import BaseYear, CustomFactor

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    _as(client, w, "admin")
    with app.app_context():
        had_base = BaseYear.query.first() is not None
    if not had_base:   # no base year configured: the baseline view is empty, never an invented year
        res = client.get("/api/emissions/", query_string={"scope": "1", "year": "baseline"})
        assert res.status_code == 200 and res.get_json()["total"] == 0
    # a record saved with the factor id as its fuel shows the factor's name
    with app.app_context():
        cf = CustomFactor(name=f"Named {tag}", co2_factor=1, ch4_factor=0, n2o_factor=0, unit="kg/MMBtu", source="s",
                          status="Approved", created_by=w["uids"]["admin"])
        db.session.add(cf)
        db.session.commit()
        cfid = cf.id
    _seed(app, w["fids"]["in"], w["uids"]["admin"], year=1994, fuel_type=str(cfid), custom_factor_id=cfid,
          equipment_id=f"CN{tag}", source_payload=json.dumps({"factor_source": "custom", "custom_factor_id": cfid}))
    rows = client.get("/api/emissions/", query_string={"scope": "1", "year": 1994, "limit": 5000, "offset": 0}).get_json()["data"]
    row = next(r for r in rows if r.get("equipment_id") == f"CN{tag}")
    assert row["fuel"] == f"Named {tag}" and str(row["custom_factor_id"]) == str(cfid)
    # a malformed year / month is refused; a malformed page size falls back to the default
    for q, code in (({"year": "abc"}, 400), ({"month": "x"}, 400), ({"month": "13"}, 400), ({"limit": "abc"}, 200)):
        assert client.get("/api/emissions/", query_string={"scope": "1", **q}).status_code == code, q


# ---------------------------------------------------------------- batch review
def test_batch_review_rules(app, client, lifecycle_world):
    from extensions import db
    from models import Emission

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    mk = lambda owner, fac="in", status="Pending": _seed(app, w["fids"][fac], w["uids"][owner], status=status,  # noqa: E731
                                                         equipment_id=f"BR{tag}{uuid.uuid4().hex[:4]}")
    a, b, own, out, done = mk("user"), mk("user"), mk("superuser"), mk("user_out", "out"), mk("user", status="Verified")
    _as(client, w, "superuser")
    for body in ({}, {"scope": "all", "ids": [a]}, {"scope": "9", "ids": [a]}, {"scope": "1", "ids": "1,2"},
                 {"scope": "1", "ids": [True]}, {"scope": "1", "ids": [-3]}, {"scope": "1", "ids": [2**31]},
                 {"scope": "1", "ids": [1.5]}, {"scope": "1", "ids": ["x"]}):
        res = client.post("/api/emissions/approve/batch", json=body)
        assert res.status_code == 400, (body, res.get_json())
    res = client.post("/api/emissions/approve/batch", json={"by_scope": {"1": [a, own, out, done, 999999999]}})
    body = res.get_json()
    assert res.status_code == 200 and body["approved_ids"] == [a], body
    reasons = {s["id"]: s["reason"] for s in body["skipped"]}
    assert "another reviewer must approve" in reasons[own]
    assert reasons[out] == "Outside your facilities or region"
    assert reasons[done] == "Already Verified" and reasons[999999999] == "Record not found"
    res = client.post("/api/emissions/reject/batch", json={"scope": "1", "ids": [b, own], "reason": "meter fault"})
    body = res.get_json()
    assert res.status_code == 200 and sorted(body["rejected_ids"]) == sorted([b, own]) and body["rejected_count"] == 2
    with app.app_context():
        assert db.session.get(Emission, b).status == "Rejected"
    # approve-all decides only what the reviewer may: their region, never their own records
    c, own2, out2 = mk("user"), mk("superuser"), mk("user_out", "out")
    res = client.post("/api/emissions/approve/batch", json={"scope": "all", "approve_all": True})
    assert res.status_code == 200, res.get_json()
    with app.app_context():
        st = {k: db.session.get(Emission, v).status for k, v in (("c", c), ("own2", own2), ("out2", out2))}
    assert st == {"c": "Verified", "own2": "Pending", "out2": "Pending"}, st
    _as(client, w, "user")
    assert client.post("/api/emissions/approve/batch", json={"scope": "1", "ids": [own2]}).status_code == 403
    assert client.post("/api/emissions/erp/sync").status_code == 403
    _as(client, w, "admin")
    assert client.post("/api/emissions/erp/sync").status_code == 501
    assert client.post(f"/api/emissions/approve/{own2}", json={"scope": "x"}).status_code == 400


def test_two_reviewers_deciding_the_same_record_at_once(app, lifecycle_world):
    """Concurrent decisions: exactly one wins; the other is told the record was already decided."""
    import threading

    from extensions import db
    from models import Emission

    w = lifecycle_world
    rid = _seed(app, w["fids"]["in"], w["uids"]["user"], status="Pending", equipment_id=f"CC{uuid.uuid4().hex[:4]}")
    barrier = threading.Barrier(2)
    codes = []

    def review(actor, action):
        with app.test_client() as c:
            with c.session_transaction() as s:
                s["user_id"] = w["uids"][actor]
            barrier.wait()
            codes.append(c.post(f"/api/emissions/{action}/{rid}", json={"scope": "1"}).status_code)

    ts = [threading.Thread(target=review, args=("superuser", "approve")),
          threading.Thread(target=review, args=("admin", "reject"))]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    assert sorted(codes) == [200, 409], codes
    with app.app_context():
        assert db.session.get(Emission, rid).status in ("Verified", "Rejected")


# ---------------------------------------------------------------- QA/QC export and dashboard
def test_qaqc_export_filters_scope_and_escapes_formulas(app, client, lifecycle_world):
    w = lifecycle_world
    year, tag = 1997, uuid.uuid4().hex[:4]
    for status in ("Pending", "Verified", "Rejected"):
        for fac in ("in", "out"):
            _seed(app, w["fids"][fac], w["uids"]["admin"], year=year, status=status,
                  record_id=f"QX{tag}{status[0]}{fac}", qa_flag="=HYPERLINK(\"http://x\")", process_type="+combustion")
    _seed(app, w["fids"]["in"], w["uids"]["admin"], year=year, record_id=f"QX{tag}noflag")

    def rows(actor, **q):
        _as(client, w, actor)
        res = client.get("/api/qaqc/export", query_string={"year": year, **q})
        if res.status_code != 200:
            return res.status_code, None
        data = list(csv.reader(io.StringIO(res.get_data(as_text=True))))
        return 200, {r[0]: r for r in data[1:] if r and r[0].startswith(f"QX{tag}")}

    code, got = rows("admin")
    assert code == 200 and set(got) == {f"QX{tag}P{f}" for f in ("in", "out")} | {f"QX{tag}V{f}" for f in ("in", "out")}
    assert all(r[5].startswith("'") and r[6].startswith("'") for r in got.values())   # formulas are text
    assert set(rows("admin", status="rejected")[1]) == {f"QX{tag}Rin", f"QX{tag}Rout"}
    assert set(rows("admin", status="verified")[1]) == {f"QX{tag}Vin", f"QX{tag}Vout"}
    assert set(rows("admin", status="pending")[1]) == {f"QX{tag}Pin", f"QX{tag}Pout"}
    assert set(rows("admin", status="active")[1]) == {f"QX{tag}Pin", f"QX{tag}Pout"}
    assert set(rows("admin", status="weird")[1]) == {f"QX{tag}{s}{f}" for s in "PVR" for f in ("in", "out")}
    assert set(rows("superuser")[1]) == {f"QX{tag}Pin", f"QX{tag}Vin"}
    assert rows("admin", scope="2")[1] == {}
    assert rows("admin", year="abc")[0] == 200
    assert rows("user")[0] == 403
    _as(client, w, "user")
    assert client.get("/api/qaqc/dashboard").status_code == 403
    _as(client, w, "superuser")
    assert client.get("/api/qaqc/dashboard").status_code == 200


def test_qaqc_resolve_outside_region_and_unknown_records(app, client, lifecycle_world):
    w = lifecycle_world
    out = _seed(app, w["fids"]["out"], w["uids"]["user_out"], status="Pending", qa_flag="z 4")
    _as(client, w, "superuser")
    assert client.post(f"/api/qaqc/resolve/{out}", json={"resolution": "Verified", "scope": 1}).status_code == 403
    assert client.post("/api/qaqc/resolve/999999999", json={"resolution": "Verified", "scope": 1}).status_code == 404
    res = client.post("/api/qaqc/bulk-resolve", json={"records": [{"id": out, "scope": 1}, {"id": 999999999, "scope": 1}],
                                                      "resolution": "Rejected"})
    body = res.get_json()
    assert res.status_code == 200, body
    reasons = {s.get("id"): s.get("reason") for s in body.get("skipped", [])}
    assert reasons.get(out) == "access_denied" and reasons.get(999999999) == "not_found", body


# ---------------------------------------------------------------- export: formulas, Scope 2 / 3 region scope
def test_export_escapes_formula_cells(app, client, lifecycle_world):
    import openpyxl

    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    for i, bad in enumerate(("=1+1", "@SUM(A1)", "+cmd", "-2+3", "%0A", " =x", "\t=y", "\r=z")):
        _seed(app, w["fids"]["in"], w["uids"]["admin"], year=1993, record_id=f"FX{tag}{i}", equipment_id=bad,
              group_name=bad, process_type="combustion")
    _as(client, w, "admin")
    res = client.get("/api/emissions/export", query_string={"scope": "1", "year": 1993, "format": "xlsx"})
    assert res.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res.data))
    cells = [c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row if isinstance(c.value, str)]
    risky = [v for v in cells if v.lstrip(" \t\r").startswith(("=", "@", "+", "%")) or v.startswith(("\t", "\r"))]
    assert not risky, risky


def test_export_scopes_2_and_3_follow_the_region(app, client, lifecycle_world):
    from extensions import db
    from models import Scope2Emission, Scope3Emission

    w = lifecycle_world
    with app.app_context():
        for fac in ("in", "out"):
            db.session.add(Scope2Emission(year=1992, month=1, facility_id=w["fids"][fac], source_type="electricity",
                                          electricity_kwh=10, co2e=1.0, status="Verified",
                                          created_by=w["uids"]["admin"], division="Gas", field="North"))
            db.session.add(Scope3Emission(year=1992, month=1, facility_id=w["fids"][fac], category="Category 1",
                                          co2e=1.0, status="Verified", created_by=w["uids"]["admin"]))
        db.session.commit()

    def facs(actor, scope, **q):
        _as(client, w, actor)
        res = client.get("/api/emissions/export", query_string={"scope": scope, "year": 1992, "format": "json", **q})
        assert res.status_code == 200, res.get_json()
        return {r.get("facility") for r in res.get_json()["data"]}

    fin, fout = _fname(app, w["fids"]["in"]), _fname(app, w["fids"]["out"])
    for scope in ("2", "3"):
        assert facs("superuser", scope) == {fin}
        assert facs("admin", scope) >= {fin, fout}
        assert facs("admin", scope, facility_id=w["fids"]["out"]) == {fout}
        assert facs("admin", scope, search="zzz-no-match") == set()
    assert facs("admin", "2", division="gas", field="nor") >= {fin, fout}


# ---------------------------------------------------------------- saved column mappings
def test_saved_mapping_validation_and_limit(app, client, lifecycle_world):
    from routes.emissions_mappings import MAX_SAVED_MAPPINGS

    w = lifecycle_world
    _as(client, w, "user2")
    h = {"name": "x", "headers": ["Qty", "col", "c"]}
    for bad in ({**h, "mapping": []}, {**h, "mapping": {}}, {**h, "mapping": {"a": 1}}, {**h, "mapping": {"k" * 101: "col"}},
                {**h, "mapping": {str(i): "c" for i in range(501)}}, {"name": "x", "headers": [], "mapping": {"q": "Qty"}},
                {"name": "", "headers": ["Qty"], "mapping": {"q": "Qty"}}, {**h, "scope": "9", "mapping": {"q": "Qty"}}):
        assert client.post("/api/emissions/upload/mappings", json=bad).status_code == 400, bad
    for i in range(MAX_SAVED_MAPPINGS):
        r = client.post("/api/emissions/upload/mappings", json={"name": f"m{i}", "headers": ["Qty"],
                                                                "mapping": {"quantity": "Qty"}})
        assert r.status_code in (200, 201), r.get_json()
    r = client.post("/api/emissions/upload/mappings", json={"name": "one too many", "headers": ["Qty"],
                                                            "mapping": {"quantity": "Qty"}})
    assert r.status_code == 400 and "delete one first" in r.get_json()["error"]


def test_a_saved_mapping_drives_the_import(app, client, lifecycle_world):
    w = lifecycle_world
    _as(client, w, "user")
    fname = _fname(app, w["fids"]["in"])
    eq = f"MP{uuid.uuid4().hex[:4]}"
    mapping = {"date": "Month", "facility_name": "Site", "process_type": "Kind", "fuel": "Gas",
               "quantity": "Qty", "unit": "U", "equipment_id": "Tag"}
    st = upload(client, 1, f"Month,Site,Kind,Gas,Qty,U,Tag\n2025-03,{fname},combustion,Natural Gas,10,MMBtu,{eq}\n",
                mapping=mapping)
    assert st["skipped_count"] == 0, st["skipped_preview"]
    assert _rec(app, eq)[0].quantity == 10


# ---------------------------------------------------------------- JSON import details
def test_json_import_roles_and_dashes(app, client, lifecycle_world):
    w = lifecycle_world
    tag = uuid.uuid4().hex[:4]
    rec = {**NG, "year": 2025, "month": 9, "amount": 10, "facility_id": w["fids"]["in"], "equipment_id": f"JD{tag}"}
    for actor in ("auditor", "it_admin"):
        _as(client, w, actor)
        assert client.post("/api/emissions/import", json={"records": [rec]}).status_code == 403
    _as(client, w, "user")
    res = client.post("/api/emissions/import", json={"records": [{**rec, "group_name": "-", "data_source_ref": "-"}]})
    assert res.status_code == 200 and res.get_json()["imported"] == 1, res.get_json()
    e = _rec(app, f"JD{tag}")[0]
    assert e.data_source_ref in (None, "")                   # "-" is "no value"


# ---------------------------------------------------------------- bulk overwrite rules per role
@pytest.mark.parametrize("uploader,owner,allowed,status", [
    ("user", "user", True, "Pending"), ("user", "user2", False, None), ("superuser", "user", True, "Pending"),
    ("admin", "user", True, "Verified"), ("user_out", "user", False, None)])
def test_bulk_overwrite_rules(app, client, lifecycle_world, uploader, owner, allowed, status):
    from extensions import db
    from models import ActivityLog, Emission

    w = lifecycle_world
    eq = f"OW{uuid.uuid4().hex[:6]}"
    rid = _seed(app, w["fids"]["in"], w["uids"][owner], status="Verified", equipment_id=eq, fuel_type="Natural Gas",
                quantity=100.0, year=2025, month=2, approved_by=w["uids"]["admin"])
    fname = _fname(app, w["fids"]["in"])
    _as(client, w, uploader)
    st = upload(client, 1, "Date,Facility,Process Type,Fuel,Quantity,Unit,Equipment ID\n"
                           f"2025-02,{fname},combustion,Natural Gas,250,MMBtu,{eq}\n", overwrite_duplicates="true")
    with app.app_context():
        e = db.session.get(Emission, rid)
        recs = Emission.query.filter_by(equipment_id=eq).all()
        log = ActivityLog.query.filter_by(action="BULK_OVERWRITE", record_id=str(rid)).first()
    assert len(recs) == 1, "an overwrite never adds a second record"
    if allowed:
        assert st["skipped_count"] == 0, st["skipped_preview"]
        assert e.quantity == 250 and e.status == status and e.updated_by == w["uids"][uploader]
        assert log is not None and "100" in (log.old_values or "")
    else:
        assert st["skipped_count"] == 1 and e.quantity == 100 and e.status == "Verified" and log is None


def test_in_file_repeats(app, client, lifecycle_world):
    w = lifecycle_world
    fname = _fname(app, w["fids"]["in"])
    _as(client, w, "user")
    eq = f"IF{uuid.uuid4().hex[:6]}"
    body = ("Date,Facility,Process Type,Fuel,Quantity,Unit,Equipment ID\n"
            f"2025-03,{fname},combustion,Natural Gas,10,MMBtu,{eq}\n2025-03,{fname},combustion,Natural Gas,20,MMBtu,{eq}\n")
    st = upload(client, 1, body)
    assert st["skipped_count"] == 1 and "earlier in this file" in st["skipped_preview"][0]["reason"]
    assert [e.quantity for e in _rec(app, eq)] == [10]
    eq2 = eq + "b"
    st = upload(client, 1, body.replace(eq, eq2), overwrite_duplicates="true")
    assert st["skipped_count"] == 0 and [e.quantity for e in _rec(app, eq2)] == [20]


def test_legacy_bulk_upload_duplicates(app, client, lifecycle_world):
    w = lifecycle_world
    fname = _fname(app, w["fids"]["in"])
    eq = f"LD{uuid.uuid4().hex[:6]}"
    _seed(app, w["fids"]["in"], w["uids"]["user"], status="Pending", equipment_id=eq, year=2025, month=4)
    _as(client, w, "user")
    rec = {"date": "2025-04-01", "facility_name": fname, "process_type": "combustion", "fuel": "Natural Gas",
           "quantity": "70", "unit": "MMBtu", "equipment": eq}
    body = client.post("/api/emissions/bulk-upload", json={"records": [rec]}).get_json()
    assert body["status"] == "preview" and len(body.get("duplicates", [])) == 1, body
    res = client.post("/api/emissions/bulk-upload", json={"records": [rec], "confirm": True})
    assert res.status_code in (200, 201), res.get_json()
    assert [e.quantity for e in _rec(app, eq)] == [70]               # confirmed: overwritten, not duplicated


