"""Regression tests for the 2026-10-15 whole-software code review (findings 1-6 and 9-15)."""
import io
import json
import time

import openpyxl
import pytest

from app import app
from audit_helpers import login, make_facility, make_user, uniq
from extensions import db
from models import ActivityLog, CustomFactor, Emission, Scope2Emission, SystemSetting, User


@pytest.fixture
def ctx():
    with app.app_context():
        yield


def _record(fac, maker, status, **kw):
    e = Emission(facility_id=fac.id, year=2024, month=7, process_type="Combustion", fuel_type="Natural Gas",
                 quantity=1.0, unit="MMBtu", co2e_total=1.0, status=status, created_by=maker.id,
                 qa_flag="Outlier", **kw)
    db.session.add(e)
    db.session.commit()
    return e.id


def _factor(status, created_by=None, **kw):
    cf = CustomFactor(name=uniq("CF"), co2_factor=50.0, ch4_factor=0.0, n2o_factor=0.0, unit="kg/MMBtu",
                      status=status, created_by=created_by, source="Lab", **kw)
    db.session.add(cf)
    db.session.commit()
    return cf


NG = {"process_type": "Combustion", "source_type": "Combustion", "unit": "MMBtu", "year": 2024, "month": 7,
      "factor_source": "custom", "amount": 1000, "quantity": 1000}


# ── 1, 6: QA/QC resolve goes through the maker-checker rules ──────────────────────────

def test_1_qaqc_resolve_decides_only_records_awaiting_review(ctx):
    maker = make_user("user", "West")
    fac = make_facility(region="West")
    draft, rejected, verified = (_record(fac, maker, s) for s in ("Draft", "Rejected", "Verified"))
    pending = _record(fac, maker, "Pending")
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert c.post(f"/api/qaqc/resolve/{draft}", json={"scope": 1, "resolution": "Verified"}).status_code == 409
        assert c.post(f"/api/qaqc/resolve/{rejected}", json={"scope": 1, "resolution": "Verified"}).status_code == 409
        assert c.post(f"/api/qaqc/resolve/{verified}", json={"scope": 1, "resolution": "Rejected"}).status_code == 409
        r = c.post(f"/api/qaqc/resolve/{pending}", json={"scope": 1, "resolution": "Verified"})
        assert r.status_code == 200, r.get_json()
    db.session.expire_all()
    assert [db.session.get(Emission, i).status for i in (draft, rejected, verified)] == ["Draft", "Rejected", "Verified"]
    rec = db.session.get(Emission, pending)
    assert rec.status == "Verified" and rec.approved_by_name and rec.qa_flag.startswith("[Verified]")
    # 6: the decision is in the facility's audit trail
    log = ActivityLog.query.filter(ActivityLog.action == "APPROVE").order_by(ActivityLog.id.desc()).first()
    assert log.facility_id == fac.id


def test_1_qaqc_bulk_resolve_skips_records_not_awaiting_review(ctx):
    maker = make_user("user", "West")
    fac = make_facility(region="West")
    draft = _record(fac, maker, "Draft")
    pending = _record(fac, maker, "Pending")
    with app.test_client() as c:
        login(c, make_user("superuser", "West"))
        r = c.post("/api/qaqc/bulk-resolve", json={"resolution": "Rejected", "records": [
            {"id": draft, "scope": 1}, {"id": pending, "scope": 1}]})
        body = r.get_json()
        assert r.status_code == 200 and body["resolved_count"] == 1, body
        assert [s["id"] for s in body["skipped"]] == [draft]
        assert c.post("/api/qaqc/bulk-resolve", json={"resolution": "Verified", "records": ["x"]}).status_code == 400
        assert c.post("/api/qaqc/bulk-resolve", json={"resolution": "Verified",
                                                      "records": [{"id": pending, "scope": 9}]}).status_code == 400
    db.session.expire_all()
    assert db.session.get(Emission, draft).status == "Draft"
    assert db.session.get(Emission, pending).status == "Rejected"
    logs = ActivityLog.query.filter(ActivityLog.action == "REJECT", ActivityLog.entity_id == str(pending)).count()
    assert logs == 1  # one entry per record, not one "bulk" entry without ids


def test_6_scope1_audit_entries_carry_their_facility(ctx):
    from utils import _resolve_log_facility

    fac = make_facility(region="West")
    rid = _record(fac, make_user("user", "West"), "Pending")
    assert _resolve_log_facility("Scope1Emission", rid) == fac.id


# ── 2, 5: custom factors ────────────────────────────────────────────────────────────

def test_2_only_approved_factors_calculate(ctx):
    fac = make_facility(region="West")
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        for status, code in (("Pending", 422), ("Rejected", 422), ("Approved", 201)):
            cf = _factor(status)
            r = c.post("/api/emissions/", json=dict(NG, facility_id=fac.id, custom_factor_id=cf.id,
                                                    fuel=str(cf.id), fuel_type=str(cf.id)))
            assert r.status_code == code, (status, r.get_json())


def test_2_a_record_keeps_working_with_the_factor_it_was_saved_with(ctx):
    fac = make_facility(region="West")
    admin = make_user("admin", "Global")
    cf = _factor("Approved")
    with app.test_client() as c:
        login(c, admin)
        rid = c.post("/api/emissions/", json=dict(NG, facility_id=fac.id, custom_factor_id=cf.id, fuel=str(cf.id),
                                                  fuel_type=str(cf.id))).get_json()["id"]
        cf.status = "Pending"  # e.g. a record saved before approvals were enforced
        db.session.commit()
        assert c.put(f"/api/emissions/{rid}", json={"quantity": 2000}).status_code == 200
        other = _factor("Pending")
        r = c.put(f"/api/emissions/{rid}", json={"custom_factor_id": other.id, "fuel": str(other.id),
                                                 "fuel_type": str(other.id)})
        assert r.status_code == 422, r.get_json()


def test_2_bulk_import_refuses_an_unapproved_factor(ctx):
    from audit_helpers import upload

    fac = make_facility(name=uniq("ImpFac"), region="West")
    cf = _factor("Pending")
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        csv_text = ("facility,year,month,process_type,fuel_type,quantity,unit,factor_source\n"
                    f"{fac.name},2024,3,Combustion,{cf.name},100,MMBtu,custom\n")
        upload(c, csv_text, "1")
    assert Emission.query.filter_by(facility_id=fac.id).count() == 0


def test_superuser_approves_factors_but_never_their_own(ctx):
    admin = make_user("admin", "Global")
    su = make_user("superuser", "West")
    theirs = _factor("Pending", created_by=admin.id)
    own = _factor("Pending", created_by=su.id)
    with app.test_client() as c:
        login(c, su)
        assert c.post(f"/api/custom-factors/{theirs.id}/approve").status_code == 200
        assert c.post(f"/api/custom-factors/{own.id}/approve").status_code == 403
        login(c, make_user("user", "West"))
        assert c.post(f"/api/custom-factors/{own.id}/approve").status_code == 403
    db.session.expire_all()
    assert db.session.get(CustomFactor, theirs.id).status == "Approved"
    assert db.session.get(CustomFactor, own.id).status == "Pending"


def test_an_approved_factor_cannot_be_rejected(ctx):
    cf = _factor("Approved")
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert c.post(f"/api/custom-factors/{cf.id}/reject", json={"reason": "x"}).status_code == 409
    db.session.expire_all()
    assert db.session.get(CustomFactor, cf.id).status == "Approved"


def test_5_superuser_cannot_edit_another_accounts_factor(ctx):
    admin = make_user("admin", "Global")
    su = make_user("superuser", "East")
    theirs = _factor("Approved", created_by=admin.id)
    own = _factor("Pending", created_by=su.id)
    with app.test_client() as c:
        login(c, su)
        assert c.put(f"/api/custom-factors/{theirs.id}", json={"source": "made up"}).status_code == 403
        assert c.put(f"/api/custom-factors/{own.id}", json={"source": "Lab 2"}).status_code == 200
    db.session.expire_all()
    assert db.session.get(CustomFactor, theirs.id).source == "Lab"


# ── 3: IT cannot hand out global read access ────────────────────────────────────────

def _new_user_body(role, location="All"):
    return {"fullName": "A", "orgName": "O", "email": f"{uniq('n')}@audit.test", "sector": "s",
            "password": "Str0ng!Passw0rd", "role": role, "location": location}


def test_3_it_admin_cannot_create_or_take_over_auditors(ctx):
    auditor = make_user("auditor", "All")
    plain = make_user("user", "West")
    with app.test_client() as c:
        login(c, make_user("it_admin", "Global"))
        assert c.post("/api/auth/users", json=_new_user_body("auditor")).status_code == 403
        assert c.put(f"/api/auth/users/{plain.id}", json={"role": "auditor"}).status_code == 403
        assert c.put(f"/api/auth/users/{auditor.id}", json={"location": "West"}).status_code == 403
        assert c.post(f"/api/auth/users/{auditor.id}/reset-password",
                      json={"newPassword": "An0ther!Passw0rd"}).status_code == 403
        assert c.delete(f"/api/auth/users/{auditor.id}").status_code == 403
        assert c.post("/api/auth/users", json=_new_user_body("user", "West")).status_code == 201
        login(c, make_user("it_manager", "Global"))
        assert c.post("/api/auth/users", json=_new_user_body("auditor")).status_code == 201


# ── 4: the idle timeout is enforced ─────────────────────────────────────────────────

def _set_timeout(minutes):
    row = db.session.get(SystemSetting, "session_timeout_minutes")
    if row is None:
        db.session.add(SystemSetting(key="session_timeout_minutes", value=json.dumps(minutes)))
    else:
        row.value = json.dumps(minutes)
    db.session.commit()
    from services.session_policy import forget_cached_timeout

    forget_cached_timeout()  # as PUT /api/auth/sessions/policy does


def test_4_idle_session_ends_after_the_configured_timeout(ctx):
    _set_timeout(15)
    try:
        with app.test_client() as c:
            login(c, make_user("user", "West"))
            me = c.get("/api/auth/me")
            assert me.status_code == 200 and me.get_json()["idle_timeout_minutes"] == 15
            with c.session_transaction() as s:
                s["last_seen"] = time.time() - 14 * 60
            assert c.get("/api/notifications/").status_code == 200  # background polling ...
            with c.session_transaction() as s:
                assert s["last_seen"] < time.time() - 13 * 60  # ... is not activity
            assert c.get("/api/auth/me").status_code == 200  # 14 minutes idle: still signed in
            with c.session_transaction() as s:
                s["last_seen"] = time.time() - 16 * 60
            assert c.get("/api/auth/me").status_code == 401
    finally:
        _set_timeout(30)


def test_4_policy_reports_the_real_lockout_limit(ctx, monkeypatch):
    monkeypatch.setenv("LOGIN_ACCOUNT_LIMIT", "7 per 15 minutes")
    with app.test_client() as c:
        login(c, make_user("it_admin", "Global"))
        assert c.get("/api/auth/sessions/policy").get_json()["max_failed_logins"] == 7


# ── 9, 11: account management ───────────────────────────────────────────────────────

def test_9_the_last_active_admin_cannot_be_deleted(ctx):
    others = User.query.filter(User.role == "admin", User.status == "active").all()
    for u in others:
        u.status = "inactive"
    db.session.commit()
    try:
        last = make_user("admin", "Global")
        with app.test_client() as c:
            login(c, make_user("it_manager", "Global"))
            assert c.delete(f"/api/auth/users/{last.id}").status_code == 409
        assert db.session.get(User, last.id) is not None
    finally:
        for u in others:
            u.status = "active"
        db.session.commit()


def test_11_email_change_is_unique_ignoring_case(ctx):
    taken = make_user("user", "West", email=f"{uniq('Mixed')}@Audit.test")
    target = make_user("user", "West")
    with app.test_client() as c:
        login(c, make_user("it_admin", "Global"))
        r = c.put(f"/api/auth/users/{target.id}", json={"email": taken.email.upper()})
        assert r.status_code == 400, r.get_json()


# ── 12: batch items must be objects ─────────────────────────────────────────────────

def test_12_batch_items_that_are_not_objects_are_refused(ctx):
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        assert c.post("/api/facilities/import", json={"facilities": ["x"]}).status_code == 400
        assert c.post("/api/custom-factors/import", json={"factors": [1]}).status_code == 400


# ── 13: Scope 2 source label is safe in Excel ───────────────────────────────────────

def test_13_national_report_scope2_label_cannot_be_a_formula(ctx):
    fac = make_facility(name=uniq("RevFac"), region=uniq("R"))
    db.session.add(Scope2Emission(facility_id=fac.id, year=2012, month=1, source_type="=HYPERLINK(\"x\")",
                                  electricity_kwh=1000, emission_factor=0.5, co2e=0.5, status="Verified"))
    db.session.commit()
    with app.test_client() as c:
        login(c, make_user("admin", "Global"))
        r = c.get(f"/api/reports/national-inventory-export?year=2012&facility_id={fac.id}")
        assert r.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(r.data))
    cells = [cell for row in wb["Emissions Inventory"].iter_rows() for cell in row]
    assert not any(cell.data_type == "f" for cell in cells)


# ── 15: the avatar check does not resolve the host ──────────────────────────────────

def test_15_avatar_url_check_needs_no_dns(ctx, monkeypatch):
    import socket

    from routes.auth import is_safe_image_url

    def boom(*a, **k):
        raise AssertionError("DNS lookup")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    assert is_safe_image_url("https://images.example.org/me.png")[0] is True
    for bad in ("http://images.example.org/a.png", "https://127.0.0.1/a.png", "https://10.0.0.5/a.png",
                "https://localhost/a.png", "https://[::1]/a.png", "https://169.254.169.254/latest"):
        assert is_safe_image_url(bad)[0] is False, bad
