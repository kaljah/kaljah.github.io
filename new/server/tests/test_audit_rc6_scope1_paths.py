"""RC-6 / RC-4 regressions: Scope 1 create, edit and import paths calculate and persist the same
values, and a missing factor is never booked as 0 t (BUG-003/007/015/030/037/042/050/068/071/109).

Hand values: EPA / API catalog natural gas 53.06 kg CO2, 1 g CH4, 0.1 g N2O per MMBtu, AR5 GWP 28 / 265.
"""
import math

import pytest

from extensions import db
from models import CustomFactor, Emission
from tests.audit_helpers import login, make_facility, make_user, uniq

NG = {"process_type": "Combustion", "source_type": "Combustion", "fuel": "Natural Gas", "fuel_type": "Natural Gas",
      "unit": "MMBtu", "year": 2024, "month": 7}


def ng_co2e(mmbtu):
    return mmbtu * (53.06 + 0.001 * 28 + 0.0001 * 265) / 1000.0


@pytest.fixture
def admin(client, app):
    with app.app_context():
        login(client, make_user("admin", "Global"))
        client.fac = make_facility(region="West")
        yield client


def _create(c, **kw):
    body = dict(NG, facility_id=c.fac.id)
    body.update(kw)
    return c.post("/api/emissions/", json=body)


def test_hand_value_natural_gas(admin):
    r = _create(admin, amount=1000, quantity=1000)
    assert r.status_code == 201, r.get_json()
    row = db.session.get(Emission, r.get_json()["id"])
    assert row.co2e_total == pytest.approx(ng_co2e(1000), rel=1e-6)


def test_bug003_put_quantity_recalculates(admin):
    rid = _create(admin, amount=1000, quantity=1000).get_json()["id"]
    assert admin.put(f"/api/emissions/{rid}", json={"quantity": 2000}).status_code == 200
    db.session.expire_all()
    row = db.session.get(Emission, rid)
    assert row.quantity == 2000
    assert row.co2e_total == pytest.approx(ng_co2e(2000), rel=1e-6)


def test_bug003_put_fuel_type_changes_factor(admin):
    rid = _create(admin, amount=1000, quantity=1000).get_json()["id"]
    before = db.session.get(Emission, rid).co2e_total
    assert admin.put(f"/api/emissions/{rid}", json={"fuel_type": "Bituminous Coal"}).status_code == 200
    db.session.expire_all()
    row = db.session.get(Emission, rid)
    assert row.fuel_type == "Bituminous Coal" and row.co2e_total != pytest.approx(before)


def test_bug030_create_persists_values_it_calculated_from(admin):
    r = admin.post("/api/emissions/", json={**{k: v for k, v in NG.items() if k not in ("fuel",)},
                                            "facility_id": admin.fac.id, "quantity": 500})
    assert r.status_code == 201, r.get_json()
    row = db.session.get(Emission, r.get_json()["id"])
    assert row.quantity == 500 and row.fuel_type == "Natural Gas"
    assert row.co2e_total == pytest.approx(ng_co2e(500), rel=1e-6)


def test_bug015_unknown_factor_is_rejected_not_zero(admin):
    before = Emission.query.count()
    r = _create(admin, fuel="Propane (Flaring)", fuel_type="Propane (Flaring)", amount=10, quantity=10, process_type="flaring")
    if r.status_code == 201:
        assert db.session.get(Emission, r.get_json()["id"]).co2e_total > 0
    else:
        assert r.status_code == 422 and Emission.query.count() == before
    r2 = _create(admin, fuel="No Such Fuel", fuel_type="No Such Fuel", amount=10, quantity=10)
    assert r2.status_code == 422
    assert Emission.query.count() == before + (1 if r.status_code == 201 else 0)


def test_bug042_custom_factor_survives_recalculation(admin):
    cf = CustomFactor(name=uniq("CF"), co2_factor=2.0, ch4_factor=0.01, n2o_factor=0.0, unit="kg/MMBtu")
    db.session.add(cf)
    db.session.commit()
    r = _create(admin, factor_source="custom", custom_factor_id=cf.id, fuel=str(cf.id), fuel_type=str(cf.id),
                amount=1000, quantity=1000)
    assert r.status_code == 201, r.get_json()
    rid = r.get_json()["id"]
    first = db.session.get(Emission, rid).co2e_total
    assert first > 0
    assert admin.put(f"/api/emissions/{rid}", json={"recalculate": True}).status_code == 200
    db.session.expire_all()
    row = db.session.get(Emission, rid)
    assert row.factor_source == "custom" and row.custom_factor_id == cf.id
    assert row.co2e_total == pytest.approx(first, rel=1e-9)


def test_bug042_custom_record_without_factor_is_rejected(admin):
    r = _create(admin, factor_source="custom", amount=10, quantity=10, fuel="999999", fuel_type="999999")
    assert r.status_code == 422


def test_bug037_put_keeps_propagated_uncertainty(admin):
    rid = _create(admin, amount=1000, quantity=1000).get_json()["id"]
    u_post = db.session.get(Emission, rid).uncertainty
    assert admin.put(f"/api/emissions/{rid}", json={"recalculate": True}).status_code == 200
    db.session.expire_all()
    assert db.session.get(Emission, rid).uncertainty == pytest.approx(u_post, rel=1e-12)


@pytest.mark.parametrize("bad", [-5, "abc"])
def test_bug050_negative_or_bad_amount_rejected(admin, bad):
    r = _create(admin, process_type="loading", amount=bad, quantity=bad)
    assert r.status_code == 422


@pytest.mark.parametrize("ptype", ["indirect_steam", "cogen_allocation"])
def test_bug068_scope2_process_types_rejected_in_scope1(admin, ptype):
    assert _create(admin, process_type=ptype, amount=10, quantity=10).status_code == 422


def test_bug007_implausible_value_rejected(admin):
    r = _create(admin, amount=1e13, quantity=1e13)
    assert r.status_code == 422


def test_bug007_large_value_flagged_and_pending_even_for_admin(admin):
    r = _create(admin, amount=3e7, quantity=3e7)  # ~1.6 Mt
    assert r.status_code == 201
    row = db.session.get(Emission, r.get_json()["id"])
    assert row.status == "Pending" and row.qa_flag


def test_bug109_inconsistent_activity_rejected(admin):
    body = dict(NG, facility_id=admin.fac.id, amount=2641.72, quantity=2641.72, unit="gal",
                calc_inputs={"Combustion": {"amount": 10}})
    assert admin.post("/api/emissions/", json=body).status_code == 422


def test_bug109_unit_required_for_catalog_factor(admin):
    body = dict(NG, facility_id=admin.fac.id, amount=10, quantity=10)
    body.pop("unit")
    assert admin.post("/api/emissions/", json=body).status_code == 422


def _scope1_total(summary):
    rows = summary if isinstance(summary, list) else summary.get("data", summary.get("yearly", []))
    return sum(float(r.get("scope1_total") or 0) for r in rows) if isinstance(rows, list) else float(summary.get("scope1_total") or 0)


def test_bug071_dashboard_reflects_new_record_immediately(admin):
    y = 2024
    q = f"/api/dashboard/batch-all?year={y}&facilityId={admin.fac.id}"
    before = _scope1_total(admin.get(q).get_json()["summary"])  # primes the cache
    assert _create(admin, amount=1000, quantity=1000, year=y).status_code == 201
    after = _scope1_total(admin.get(q).get_json()["summary"])
    assert after - before == pytest.approx(ng_co2e(1000), rel=1e-6)


def test_bug067_bulk_delete_respects_status(client, app):
    with app.app_context():
        fac = make_facility(region="West")
        maker = make_user("user", "West")
        e = Emission(facility_id=fac.id, year=2024, month=1, process_type="combustion", status="Verified",
                     created_by=maker.id, co2e_total=1)
        db.session.add(e)
        db.session.commit()
        login(client, maker)
        r = client.post("/api/emissions/bulk-delete", json={"ids": [e.id]})
        assert r.get_json()["deleted"] == 0
        assert db.session.get(Emission, e.id) is not None
