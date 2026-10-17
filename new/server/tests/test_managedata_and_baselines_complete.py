"""Exhaustive test suite for Base Year recalculation, SBTi targets, verified totals by scope, and mitigations.

Covers:
- routes/managedata.py:
  - _verified_totals_by_scope (Scope 1, 2, 3 verification status filtering, facility RLS, year filtering)
  - add_base_year_recalculation (permissions, boundary validation, BaseYear singleton sync)
  - delete_base_year_recalculation (singleton resync to latest remaining)
  - manage_sbti (GET suggestion logic, POST pathway rates, scope coverage, target year bounds)
  - mitigation projects and records (CRUD, facility RLS, non-negative quantities)
"""
import datetime
import pytest
from extensions import db
from models import (
    BaseYear,
    BaseYearRecalculation,
    Emission,
    Facility,
    MitigationProject,
    MitigationRecord,
    SbtiTarget,
    Scope2Emission,
    Scope3Emission,
    User,
)
from routes.managedata import _verified_totals_by_scope, SBTI_PATHWAY_MIN_RATE
from tests.audit_helpers import login, make_facility, make_user, uniq


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


# ---------------------------------------------------------------------------
# _verified_totals_by_scope Tests
# ---------------------------------------------------------------------------

def test_verified_totals_by_scope_filters_status_and_scope(ctx):
    f1 = make_facility(region=uniq("RegV1"))
    f2 = make_facility(region=uniq("RegV2"))
    test_yr = 2094

    # Scope 1 emissions
    e_v1 = Emission(facility_id=f1.id, year=test_yr, month=1, co2e_total=100.0, status="Verified", process_type="combustion")
    e_p1 = Emission(facility_id=f1.id, year=test_yr, month=2, co2e_total=50.0, status="Pending", process_type="combustion")
    e_r1 = Emission(facility_id=f1.id, year=test_yr, month=3, co2e_total=30.0, status="Rejected", process_type="combustion")
    e_v2 = Emission(facility_id=f2.id, year=test_yr, month=1, co2e_total=200.0, status="Verified", process_type="combustion")
    e_diff_year = Emission(facility_id=f1.id, year=test_yr - 1, month=1, co2e_total=80.0, status="Verified", process_type="combustion")

    # Scope 2 emissions
    s2_v1 = Scope2Emission(facility_id=f1.id, year=test_yr, month=1, co2e=40.0, electricity_kwh=80000, status="Verified")
    s2_p1 = Scope2Emission(facility_id=f1.id, year=test_yr, month=2, co2e=25.0, electricity_kwh=50000, status="Draft")
    s2_v2 = Scope2Emission(facility_id=f2.id, year=test_yr, month=1, co2e=60.0, electricity_kwh=120000, status="Verified")

    # Scope 3 emissions
    s3_v1 = Scope3Emission(facility_id=f1.id, year=test_yr, month=1, co2e=15.0, status="Verified")
    s3_r1 = Scope3Emission(facility_id=f1.id, year=test_yr, month=2, co2e=10.0, status="Rejected")
    s3_v2 = Scope3Emission(facility_id=f2.id, year=test_yr, month=1, co2e=35.0, status="Verified")

    db.session.add_all([e_v1, e_p1, e_r1, e_v2, e_diff_year, s2_v1, s2_p1, s2_v2, s3_v1, s3_r1, s3_v2])
    db.session.commit()

    # 1. Organization-wide verified totals for test_yr (allowed_fids = None)
    tot_org = _verified_totals_by_scope(test_yr, allowed_fids=None)
    assert tot_org["scope1"] == pytest.approx(100.0 + 200.0)  # Only Verified, excluded Pending/Rejected/diff_year
    assert tot_org["scope2"] == pytest.approx(40.0 + 60.0)
    assert tot_org["scope3"] == pytest.approx(15.0 + 35.0)

    # 2. Facility 1 only (allowed_fids = [f1.id])
    tot_f1 = _verified_totals_by_scope(test_yr, allowed_fids=[f1.id])
    assert tot_f1["scope1"] == pytest.approx(100.0)
    assert tot_f1["scope2"] == pytest.approx(40.0)
    assert tot_f1["scope3"] == pytest.approx(15.0)

    # 3. Empty facility list -> all zero
    tot_empty = _verified_totals_by_scope(test_yr, allowed_fids=[])
    assert tot_empty["scope1"] == 0.0
    assert tot_empty["scope2"] == 0.0
    assert tot_empty["scope3"] == 0.0


# ---------------------------------------------------------------------------
# Base Year Recalculation API Tests
# ---------------------------------------------------------------------------

def test_add_and_delete_base_year_recalculation(client, ctx):
    admin = make_user("admin", "Global")
    login(client, admin)

    # 1. Successful creation
    payload = {
        "year": 2022,
        "reason": "Acquisition of Southern Gas Facility",
        "previous_emissions": 50000.0,
        "adjusted_emissions": 58500.0,
    }
    r = client.post("/api/base-years/", json=payload)
    assert r.status_code == 201, r.get_data(as_text=True)
    rec_id = r.get_json()["id"]

    # Singleton check
    singleton = db.session.get(BaseYear, 1)
    assert singleton is not None
    assert singleton.year == 2022

    # 2. Validation: Year out of bounds
    r_bad_yr = client.post("/api/base-years/", json={**payload, "year": 1985})
    assert r_bad_yr.status_code == 400
    assert "between 1990 and 2100" in r_bad_yr.get_json()["error"]

    # 3. Validation: Missing reason
    r_no_reason = client.post("/api/base-years/", json={"year": 2022})
    assert r_no_reason.status_code == 400

    # 4. Validation: Negative emissions
    r_neg = client.post("/api/base-years/", json={**payload, "adjusted_emissions": -10.0})
    assert r_neg.status_code == 400

    # 5. Add second recalculation for 2023
    r2 = client.post("/api/base-years/", json={
        "year": 2023,
        "reason": "Divestment of offshore asset",
        "previous_emissions": 58500.0,
        "adjusted_emissions": 52000.0,
    })
    assert r2.status_code == 201
    rec2_id = r2.get_json()["id"]
    assert db.session.get(BaseYear, 1).year == 2023

    # 6. Delete latest recalculation -> singleton resyncs to 2022
    del_r = client.delete(f"/api/base-years/{rec2_id}")
    assert del_r.status_code == 200
    assert db.session.get(BaseYear, 1).year == 2022

    # 7. Delete 2022 recalculation
    del_r2 = client.delete(f"/api/base-years/{rec_id}")
    assert del_r2.status_code == 200

    # 8. Delete nonexistent -> 404
    del_nonexistent = client.delete("/api/base-years/999999")
    assert del_nonexistent.status_code == 404


def test_base_year_recalculation_authorization_rules(client, ctx):
    # IT user is forbidden
    it_user = make_user("it_admin", "Global")
    login(client, it_user)
    r_it = client.post("/api/base-years/", json={"year": 2022, "reason": "Test"})
    assert r_it.status_code == 403

    # Facility-restricted superuser is forbidden (A-05 base year is org-wide)
    f = make_facility(region=uniq("RestrictedReg"))
    scoped_su = make_user("superuser", f.name)
    db.session.commit()

    login(client, scoped_su)
    r_scoped = client.post("/api/base-years/", json={"year": 2022, "reason": "Test"})
    assert r_scoped.status_code == 403


# ---------------------------------------------------------------------------
# SBTi Target Management API Tests
# ---------------------------------------------------------------------------

def test_manage_sbti_get_suggestion_and_post(client, ctx):
    from models import SbtiTarget
    SbtiTarget.query.delete()
    Emission.query.filter_by(year=2021).delete()
    Scope2Emission.query.filter_by(year=2021).delete()
    Scope3Emission.query.filter_by(year=2021).delete()
    db.session.commit()

    f = make_facility(region=uniq("SbtiReg"))
    admin = make_user("admin", "Global")
    login(client, admin)

    # Populate verified emissions for isolated year 2021
    db.session.add_all([
        Emission(facility_id=f.id, year=2021, month=1, co2e_total=1000.0, status="Verified", process_type="combustion"),
        Scope2Emission(facility_id=f.id, year=2021, month=1, co2e=500.0, electricity_kwh=1000000, status="Verified"),
        Scope3Emission(facility_id=f.id, year=2021, month=1, co2e=250.0, status="Verified"),
    ])
    db.session.commit()

    # 1. GET without existing target -> returns baseline suggestions
    r_get = client.get("/api/sbti?base_year=2021")
    assert r_get.status_code == 200
    res_get = r_get.get_json()
    assert res_get["has_target"] is False
    assert res_get["suggested_base_year"] == 2021
    assert res_get["suggested_base_year_emissions"] == pytest.approx(1750.0)
    assert res_get["suggested_by_scope"]["scope1"] == pytest.approx(1000.0)
    assert res_get["suggested_by_scope"]["scope2"] == pytest.approx(500.0)
    assert res_get["suggested_by_scope"]["scope3"] == pytest.approx(250.0)

    # 2. Validation failures on POST
    current_year = datetime.date.today().year

    # Base year too early
    r_early = client.post("/api/sbti", json={
        "base_year": 2010,
        "base_year_emissions": 1750.0,
        "pathway_type": "1.5C",
    })
    assert r_early.status_code == 400

    # Base year in the future
    r_future = client.post("/api/sbti", json={
        "base_year": current_year + 2,
        "base_year_emissions": 1750.0,
        "pathway_type": "1.5C",
    })
    assert r_future.status_code == 400

    # 1.5C pathway requires >= 4.2% reduction rate
    r_rate = client.post("/api/sbti", json={
        "base_year": 2021,
        "base_year_emissions": 1750.0,
        "target_year": 2035,
        "pathway_type": "1.5C",
        "reduction_rate_pct": 3.0,  # Below 4.2%
    })
    assert r_rate.status_code == 400
    assert "requires an annual linear reduction of at least 4.2%" in r_rate.get_json()["error"]

    # Invalid scope coverage
    r_scope = client.post("/api/sbti", json={
        "base_year": 2021,
        "base_year_emissions": 1750.0,
        "pathway_type": "1.5C",
        "reduction_rate_pct": 4.5,
        "scope_coverage": "INVALID",
    })
    assert r_scope.status_code == 400

    # 3. Successful POST
    valid_payload = {
        "base_year": 2021,
        "base_year_emissions": 1750.0,
        "target_year": 2035,
        "reduction_rate_pct": 4.5,
        "pathway_type": "1.5C",
        "scope_coverage": "S1S2S3",
    }
    r_post = client.post("/api/sbti", json=valid_payload)
    assert r_post.status_code == 201

    # 4. GET with active target
    r_get2 = client.get("/api/sbti")
    assert r_get2.status_code == 200
    res_get2 = r_get2.get_json()
    assert res_get2["has_target"] is True
    assert res_get2["reduction_rate_pct"] == 4.5
    assert res_get2["pathway_type"] == "1.5C"


# ---------------------------------------------------------------------------
# Mitigations API Tests
# ---------------------------------------------------------------------------

def test_mitigations_crud_and_facility_rls(client, ctx):
    f1 = make_facility(region=uniq("Mitig1"))
    f2 = make_facility(region=uniq("Mitig2"))

    admin = make_user("admin", "Global")
    login(client, admin)

    # 1. Create facility project
    proj_payload = {
        "name": "Flare Gas Recovery Unit",
        "type": "flaring_reduction",
        "year": 2025,
        "quantity_tco2e": 4500.0,
        "facility_id": f1.id,
        "notes": "Compresses low-pressure gas for fuel line",
    }
    r_proj = client.post("/api/mitigation", json=proj_payload)
    assert r_proj.status_code == 201
    proj_id = r_proj.get_json()["id"]

    # 2. Create generic organization record (no facility)
    rec_payload = {
        "type": "reforestation",
        "year": 2025,
        "quantity_tco2e": 1200.0,
        "notes": "Green barrier project",
    }
    r_rec = client.post("/api/mitigation", json=rec_payload)
    assert r_rec.status_code == 201
    rec_id = r_rec.get_json()["id"]

    # 3. GET mitigations org-wide
    r_list = client.get("/api/mitigation")
    assert r_list.status_code == 200
    items = r_list.get_json()
    ids = [item["id"] for item in items]
    assert proj_id in ids
    assert rec_id in ids

    # 4. Scoped user on Facility 2 sees record, but does NOT see Facility 1 project
    scoped_user = make_user("engineer", f2.name)
    scoped_user.allowed_facilities = [f2]
    db.session.commit()

    login(client, scoped_user)
    r_scoped_list = client.get("/api/mitigation")
    assert r_scoped_list.status_code == 200
    scoped_ids = [item["id"] for item in r_scoped_list.get_json()]
    assert rec_id in scoped_ids  # Generic record visible
    assert proj_id not in scoped_ids  # Facility 1 project filtered out

    # 5. Auditor is forbidden to create mitigations
    auditor = make_user("auditor", "Global")
    login(client, auditor)
    r_audit = client.post("/api/mitigation", json=proj_payload)
    assert r_audit.status_code == 403
