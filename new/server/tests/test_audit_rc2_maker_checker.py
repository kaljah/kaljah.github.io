"""RC-2 maker-checker regressions (AUDIT_FINDINGS.md BUG-053/060/067/070/074/092)."""
import threading

import pytest

from extensions import db
from models import CapEmission, Emission, Notification, Scope2Emission
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def _emission(fac, status="Pending", created_by=None, **kw):
    e = Emission(facility_id=fac.id, year=2024, month=3, process_type="combustion", fuel_type="Natural Gas",
                 quantity=100, unit="MMBtu", co2e_total=5.3, status=status, created_by=created_by, **kw)
    db.session.add(e)
    db.session.commit()
    return e


# ── BUG-070: a decided record cannot be rejected / re-decided ─────────────────────

@pytest.mark.parametrize("status", ["Verified", "Rejected"])
def test_bug070_reject_requires_pending_status(client, ctx, status):
    fac = make_facility(region="West")
    admin = make_user("admin", "Global")
    e = _emission(fac, status=status, created_by=admin.id, approved_by=admin.id)
    login(client, make_user("superuser", "Global"))
    r = client.post(f"/api/emissions/reject/{e.id}", json={"scope": "1", "reason": "x"})
    assert r.status_code == 409
    db.session.expire_all()
    row = db.session.get(Emission, e.id)
    assert row.status == status and row.approved_by == admin.id


# ── BUG-067: segregation of duties and edit/delete gates ─────────────────────────

def test_bug067_last_modifier_cannot_approve(client, ctx):
    fac = make_facility(region="West")
    maker = make_user("user", "West")
    e = _emission(fac, created_by=maker.id)
    su = make_user("superuser", "Global")
    login(client, su)
    r = client.put(f"/api/emissions/{e.id}", json={"month": 4})
    assert r.status_code == 200, r.get_data(as_text=True)
    db.session.expire_all()
    assert db.session.get(Emission, e.id).updated_by == su.id
    assert client.post(f"/api/emissions/approve/{e.id}", json={"scope": "1"}).status_code == 403
    # batch path skips it too
    r = client.post("/api/emissions/approve/batch", json={"by_scope": {"1": [e.id]}})
    assert r.get_json()["approved_count"] == 0
    # another approver can
    with client.application.test_client() as other:
        login(other, make_user("admin", "Global"))
        assert other.post(f"/api/emissions/approve/{e.id}", json={"scope": "1"}).status_code == 200


def test_bug067_superuser_edit_of_verified_record_returns_it_to_review(client, ctx):
    fac = make_facility(region="West")
    admin = make_user("admin", "Global")
    e = _emission(fac, status="Verified", created_by=admin.id, approved_by=admin.id)
    login(client, make_user("superuser", "Global"))
    assert client.put(f"/api/emissions/{e.id}", json={"year": 2023}).status_code == 200
    db.session.expire_all()
    row = db.session.get(Emission, e.id)
    assert row.status == "Pending" and row.approved_by is None


def test_bug067_maker_cannot_delete_verified_record(client, ctx):
    fac = make_facility(region="West")
    maker = make_user("user", "West")
    e = _emission(fac, status="Verified", created_by=maker.id)
    login(client, maker)
    assert client.delete(f"/api/emissions/{e.id}").status_code == 403
    assert db.session.get(Emission, e.id) is not None
    s2 = Scope2Emission(facility_id=fac.id, year=2024, month=1, source_type="electricity", co2e=1.0,
                        status="Verified", created_by=maker.id)
    db.session.add(s2)
    db.session.commit()
    assert client.delete(f"/api/scope2/{s2.id}").status_code == 403


def test_bug067_maker_can_delete_own_pending_record(client, ctx):
    fac = make_facility(region="West")
    maker = make_user("user", "West")
    e = _emission(fac, status="Pending", created_by=maker.id)
    login(client, maker)
    assert client.delete(f"/api/emissions/{e.id}").status_code == 200


# ── BUG-074: concurrent decisions ───────────────────────────────────────────────

def test_bug074_only_one_concurrent_decision_wins(app, ctx):
    fac = make_facility(region="West")
    maker = make_user("user", "West")
    e = _emission(fac, created_by=maker.id)
    approvers = [make_user("admin", "Global"), make_user("admin", "Global")]
    results = []

    def act(u, decision):
        with app.test_client() as c:
            login(c, u)
            results.append(c.post(f"/api/emissions/{decision}/{e.id}", json={"scope": "1", "reason": "r"}).status_code)

    threads = [threading.Thread(target=act, args=(approvers[0], "approve")),
               threading.Thread(target=act, args=(approvers[1], "reject"))]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [200, 409], results


# ── BUG-092: the maker is told the outcome ──────────────────────────────────────

def test_bug092_maker_notified_on_reject_with_reason(client, ctx):
    fac = make_facility(region="West")
    maker = make_user("user", "West")
    e = _emission(fac, created_by=maker.id)
    login(client, make_user("admin", "Global"))
    assert client.post(f"/api/emissions/reject/{e.id}", json={"scope": "1", "reason": "meter misread"}).status_code == 200
    notes = Notification.query.filter_by(user_id=maker.id).all()
    assert any("rejected" in n.message and "meter misread" in n.message for n in notes)


# ── BUG-060: one status policy for every scope (only admin auto-verifies) ─────────

def test_bug060_superuser_scope2_manual_entry_is_pending(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("superuser", "Global"))
    r = client.post("/api/scope2", json={"facility_id": fac.id, "year": 2024, "month": 1,
                                         "electricity_kwh": 1000, "grid_region": "Algerian National Grid"})
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    assert r.get_json()["status"] == "Pending"


# ── BUG-053: CAP records go through maker-checker and validation ─────────────────

def test_bug053_cap_status_not_client_controlled(client, ctx):
    fac = make_facility(region="West")
    login(client, make_user("user", "West"))
    r = client.post("/api/cap/emissions", json={"facility_id": fac.id, "year": 2024, "source_module": "Flare",
                                                "pollutant": "NO2", "mass_tonnes": 1.5, "status": "Verified"})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert db.session.get(CapEmission, r.get_json()["id"]).status == "Pending"


@pytest.mark.parametrize("bad", [{"mass_tonnes": -1}, {"mass_tonnes": "abc"}, {"concentration_mg_nm3": -5, "flue_gas_volume_nm3": 1}])
def test_bug053_cap_rejects_invalid_numbers(client, ctx, bad):
    fac = make_facility(region="West")
    login(client, make_user("admin", "Global"))
    body = {"facility_id": fac.id, "year": 2024, "source_module": "Flare", "pollutant": "NO2"}
    body.update(bad)
    assert client.post("/api/cap/emissions", json=body).status_code == 400


def test_bug053_cap_compliance_uses_verified_only(client, ctx):
    fac = make_facility(region="West")
    db.session.add(CapEmission(facility_id=fac.id, year=2031, source_module="Flare", pollutant="NO2",
                               mass_tonnes=99.0, concentration_mg_nm3=9999.0, status="Pending"))
    db.session.commit()
    login(client, make_user("admin", "Global"))
    rows = client.get(f"/api/cap/compliance?year=2031&facility_id={fac.id}").get_json()
    no2 = [p for r in rows for p in r["pollutants"] if p["pollutant"] == "NO2"]
    assert no2, rows
    assert all(p["total_tonnes"] == 0 and p["measured_concentration_mg_nm3"] == 0 and p["is_compliant"] for p in no2)
