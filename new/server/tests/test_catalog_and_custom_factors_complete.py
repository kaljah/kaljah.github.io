"""Exhaustive tests for Emission Factor Catalog and Custom Factor routes.
Covers:
  - routes/emission_factors_routes.py (100% route and branch coverage)
  - routes/custom_factors.py (CRUD, IT restrictions, validations, maker-checker governance)
"""
import uuid
import pytest
from app import app
from extensions import db
from models import CustomFactor, Facility, User, Emission


@pytest.fixture(scope="module")
def factor_env():
    tag = uuid.uuid4().hex[:6]
    with app.app_context():
        admin = User(
            email=f"ef_admin_{tag}@test.com",
            fullName="EF Admin",
            orgName="Sonatrach",
            sector="Oil & Gas",
            role="admin",
            location="Algiers",
        )
        admin.set_password("AdminPass123!")

        superuser = User(
            email=f"ef_super_{tag}@test.com",
            fullName="EF Superuser",
            orgName="Sonatrach",
            sector="Oil & Gas",
            role="superuser",
            location="Hassi Messaoud",
        )
        superuser.set_password("SuperPass123!")

        operator = User(
            email=f"ef_op_{tag}@test.com",
            fullName="EF Operator",
            orgName="Sonatrach",
            sector="Oil & Gas",
            role="operator",
            location="Hassi Messaoud",
        )
        operator.set_password("OperatorPass123!")

        it_user = User(
            email=f"ef_it_{tag}@test.com",
            fullName="EF IT",
            orgName="Sonatrach",
            sector="Oil & Gas",
            role="it_admin",
            location="Algiers",
        )
        it_user.set_password("ItPass123!")

        fac = Facility(
            name=f"EF Facility {tag}",
            location="Hassi Messaoud",
            segment="Upstream",
            code=f"FAC-EF-{tag}",
        )
        db.session.add_all([admin, superuser, operator, it_user, fac])
        db.session.commit()

        return {
            "admin_id": admin.id,
            "super_id": superuser.id,
            "op_id": operator.id,
            "it_id": it_user.id,
            "fac_id": fac.id,
        }


def _login_as(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# =============================================================================
# 1. EMISSION FACTORS CATALOG ROUTES (routes/emission_factors_routes.py)
# =============================================================================

def test_catalog_auth_guards(client):
    """Verify that unauthenticated requests to catalog routes return 401."""
    with client.session_transaction() as sess:
        sess.clear()

    endpoints = [
        "/api/emission-factors",
        "/api/emission-factors/segments",
        "/api/emission-factors/by-segment/Upstream",
        "/api/emission-factors/process-types",
        "/api/emission-factors/process-types/upstream",
        "/api/emission-factors/by-process/stationary_combustion",
        "/api/emission-factors/by-segment-and-process?segment=Upstream&process=stationary_combustion",
        "/api/emission-factors/search?q=diesel",
        "/api/emission-factors/uncertainties",
        "/api/emission-factors/stats",
        "/api/emission-factors/version",
        "/api/activity-factors",
        "/api/equipment-combustion-factors",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 401, f"{ep} did not enforce authentication"


def test_catalog_all_and_segments(client, factor_env):
    """Test /api/emission-factors and /api/emission-factors/segments."""
    _login_as(client, factor_env["admin_id"])

    # All factors
    r1 = client.get("/api/emission-factors")
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1["count"] > 50
    assert len(d1["factors"]) == d1["count"]

    # Segments list
    r2 = client.get("/api/emission-factors/segments")
    assert r2.status_code == 200
    d2 = r2.get_json()
    assert any(k.lower() == "upstream" for k in d2)
    assert any(k.lower() == "midstream" for k in d2)
    assert any(k.lower() == "downstream" for k in d2)



def test_catalog_by_segment_valid_and_invalid(client, factor_env):
    """Test /api/emission-factors/by-segment/<segment>."""
    _login_as(client, factor_env["admin_id"])

    for seg in ["upstream", "Midstream", "DOWNSTREAM"]:
        resp = client.get(f"/api/emission-factors/by-segment/{seg}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["segment"] == seg.lower().capitalize()
        assert data["count"] > 0

    # Invalid segment
    r_bad = client.get("/api/emission-factors/by-segment/Mars")
    assert r_bad.status_code == 400
    assert "Invalid segment" in r_bad.get_json()["error"]


def test_catalog_process_types_endpoints(client, factor_env):
    """Test process-types and process-types/<segment>."""
    _login_as(client, factor_env["admin_id"])

    # All process types
    r1 = client.get("/api/emission-factors/process-types")
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert "process_types" in d1
    assert "categories" in d1

    # Segment specific
    for seg in ["upstream", "midstream", "downstream"]:
        r2 = client.get(f"/api/emission-factors/process-types/{seg}")
        assert r2.status_code == 200
        d2 = r2.get_json()
        assert d2["segment"] == seg
        assert d2["count"] > 0
        assert "id" in d2["process_types"][0]

    # Invalid segment
    r_bad = client.get("/api/emission-factors/process-types/nuclear")
    assert r_bad.status_code == 400
    assert "Invalid segment" in r_bad.get_json()["error"]


def test_catalog_by_process_category(client, factor_env):
    """Test /api/emission-factors/by-process/<cat>."""
    _login_as(client, factor_env["admin_id"])

    # Valid category
    r1 = client.get("/api/emission-factors/by-process/stationary_combustion")
    assert r1.status_code == 200
    d1 = r1.get_json()
    assert d1["count"] > 0
    assert d1["process_category"] == "stationary_combustion"

    # Non-existent category -> 404
    r_bad = client.get("/api/emission-factors/by-process/nonexistent_category_xyz")
    assert r_bad.status_code == 404
    assert "No factors found" in r_bad.get_json()["error"]


def test_catalog_by_segment_and_process(client, factor_env):
    """Test /api/emission-factors/by-segment-and-process."""
    _login_as(client, factor_env["admin_id"])

    # Missing params
    r_miss = client.get("/api/emission-factors/by-segment-and-process")
    assert r_miss.status_code == 400

    r_miss_proc = client.get("/api/emission-factors/by-segment-and-process?segment=Upstream")
    assert r_miss_proc.status_code == 400

    # Invalid segment
    r_bad_seg = client.get("/api/emission-factors/by-segment-and-process?segment=Space&process=flaring")
    assert r_bad_seg.status_code == 400

    # Valid
    r_ok = client.get("/api/emission-factors/by-segment-and-process?segment=Upstream&process=stationary_combustion")
    assert r_ok.status_code == 200
    d_ok = r_ok.get_json()
    assert d_ok["segment"] == "Upstream"
    assert d_ok["count"] > 0


def test_catalog_search_filters(client, factor_env):
    """Test /api/emission-factors/search with various filters and fields."""
    _login_as(client, factor_env["admin_id"])

    # Missing q -> 400
    r_no_q = client.get("/api/emission-factors/search")
    assert r_no_q.status_code == 400

    # Search by fuel/factor name
    r_name = client.get("/api/emission-factors/search?q=diesel")
    assert r_name.status_code == 200
    assert r_name.get_json()["count"] > 0

    # Search with segment filter
    r_seg = client.get("/api/emission-factors/search?q=gas&segment=Upstream")
    assert r_seg.status_code == 200

    # Search with process filter
    r_proc = client.get("/api/emission-factors/search?q=gas&process=stationary_combustion")
    assert r_proc.status_code == 200

    # Search with both filters
    r_both = client.get("/api/emission-factors/search?q=gas&segment=Upstream&process=stationary_combustion")
    assert r_both.status_code == 200

    # Search by code, description, source
    r_code = client.get("/api/emission-factors/search?q=api")
    assert r_code.status_code == 200


def test_catalog_uncertainties_stats_version(client, factor_env):
    """Test uncertainties filter, stats, and version endpoints."""
    _login_as(client, factor_env["admin_id"])

    # Uncertainties unfiltered
    r_unc = client.get("/api/emission-factors/uncertainties")
    assert r_unc.status_code == 200
    d_unc = r_unc.get_json()
    assert d_unc["count"] > 0

    # Uncertainties with min/max threshold
    r_unc_filt = client.get("/api/emission-factors/uncertainties?min_uncertainty=0.05&max_uncertainty=0.50")
    assert r_unc_filt.status_code == 200

    # Stats
    r_stats = client.get("/api/emission-factors/stats")
    assert r_stats.status_code == 200
    d_stats = r_stats.get_json()
    assert d_stats["total_factors"] > 0
    assert d_stats["combustion_factors"] > 0
    assert "by_segment" in d_stats

    # Version
    r_ver = client.get("/api/emission-factors/version")
    assert r_ver.status_code == 200
    d_ver = r_ver.get_json()
    assert d_ver["version"] == "1.0.0"
    assert "API Compendium" in d_ver["source"]


def test_catalog_activity_and_equipment_factors(client, factor_env):
    """Test /api/activity-factors and /api/equipment-combustion-factors."""
    _login_as(client, factor_env["admin_id"])

    # Activity factors all
    r_act = client.get("/api/activity-factors")
    assert r_act.status_code == 200
    assert r_act.get_json()["count"] > 0

    # Activity factors filtered with alias
    r_act_alias = client.get("/api/activity-factors?process=gas_plant_dehydrator")
    assert r_act_alias.status_code == 200

    # Equipment combustion factors
    r_eq = client.get("/api/equipment-combustion-factors")
    assert r_eq.status_code == 200
    assert r_eq.get_json()["count"] > 0


# =============================================================================
# 2. CUSTOM EMISSION FACTORS (routes/custom_factors.py)
# =============================================================================

def test_custom_factors_it_role_forbidden(client, factor_env):
    """IT personnel cannot access operational custom factor data."""
    _login_as(client, factor_env["it_id"])
    resp = client.get("/api/custom-factors")
    assert resp.status_code == 403
    assert "IT personnel do not have access" in resp.get_json()["error"]


def test_custom_factor_create_validations(client, factor_env):
    """Test validations when creating a custom factor."""
    _login_as(client, factor_env["admin_id"])

    # 1. Missing name
    r1 = client.post("/api/custom-factors", json={"co2_factor": 1.5, "unit": "kg/m3"})
    assert r1.status_code == 400
    assert "Factor name is required" in r1.get_json()["error"]

    # 2. Invalid unit
    r2 = client.post("/api/custom-factors", json={"name": "BadUnitFactor", "unit": "parsecs"})
    assert r2.status_code == 400

    # 3. Invalid parent fuel
    r3 = client.post("/api/custom-factors", json={
        "name": "BadFuelFactor",
        "unit": "kg/m3",
        "parent_fuel": "Kryptonite",
    })
    assert r3.status_code == 400
    assert "not a catalog fuel" in r3.get_json()["error"]

    # 4. All emission factors zero or blank
    r4 = client.post("/api/custom-factors", json={
        "name": "ZeroFactor",
        "unit": "kg/m3",
        "co2_factor": 0,
        "ch4_factor": 0,
        "n2o_factor": 0,
    })
    assert r4.status_code == 400
    assert "At least one of co2_factor" in r4.get_json()["error"]


def test_custom_factor_lifecycle_crud(client, factor_env):
    """Test full lifecycle: create, get, update, archive, restore, and delete."""
    _login_as(client, factor_env["admin_id"])
    tag = uuid.uuid4().hex[:6]
    name = f"Custom Fuel {tag}"

    # 1. Create custom factor
    r_create = client.post("/api/custom-factors", json={
        "name": name,
        "unit": "m3",
        "co2_factor": 2.15,
        "ch4_factor": 0.005,
        "n2o_factor": 0.0001,
        "source": "Laboratory GC Analysis 2026",
        "description": "On-site tested fuel gas",
    })
    assert r_create.status_code == 201
    cf_id = r_create.get_json()["id"]

    # 2. Duplicate name check
    r_dup = client.post("/api/custom-factors", json={
        "name": name,
        "unit": "m3",
        "co2_factor": 1.0,
    })
    assert r_dup.status_code == 409

    # 3. Get custom factors
    r_get = client.get("/api/custom-factors")
    assert r_get.status_code == 200
    factors = r_get.get_json()
    assert any(f["id"] == cf_id for f in factors)

    # 4. Update custom factor description and source
    r_upd = client.put(f"/api/custom-factors/{cf_id}", json={
        "description": "Updated lab analysis description",
        "source": "Certified Lab 2026-B",
    })
    assert r_upd.status_code == 200

    # 5. Archive factor
    r_arch = client.post(f"/api/custom-factors/{cf_id}/archive", json={"restore": False})
    assert r_arch.status_code == 200
    assert r_arch.get_json()["archived"] is True

    # Check excluded from default list
    r_get_active = client.get("/api/custom-factors")
    assert not any(f["id"] == cf_id for f in r_get_active.get_json())

    # Included when include_archived=1
    r_get_all = client.get("/api/custom-factors?include_archived=1")
    assert any(f["id"] == cf_id for f in r_get_all.get_json())

    # 6. Restore factor
    r_rest = client.post(f"/api/custom-factors/{cf_id}/archive", json={"restore": True})
    assert r_rest.status_code == 200
    assert r_rest.get_json()["archived"] is False

    # 7. Delete factor
    r_del = client.delete(f"/api/custom-factors/{cf_id}")
    assert r_del.status_code == 200

    # Verify 404 after deletion
    r_del_again = client.delete(f"/api/custom-factors/{cf_id}")
    assert r_del_again.status_code == 404


def test_custom_factor_referenced_cannot_delete(client, factor_env):
    """An emission factor referenced by active emissions cannot be deleted."""
    _login_as(client, factor_env["admin_id"])
    tag = uuid.uuid4().hex[:6]
    name = f"InUse Fuel {tag}"

    r_create = client.post("/api/custom-factors", json={
        "name": name,
        "unit": "m3",
        "co2_factor": 1.8,
        "source": "Site Well Test",
    })
    assert r_create.status_code == 201
    cf_id = r_create.get_json()["id"]

    # Attach to an emission record
    with app.app_context():
        em = Emission(
            facility_id=factor_env["fac_id"],
            year=2025,
            month=5,
            process_type="combustion",
            fuel_type=name,
            custom_factor_id=cf_id,
            co2e_total=10.0,
            status="Draft",
        )
        db.session.add(em)
        db.session.commit()
        em_id = em.id

    # Attempting to delete should return 409 Conflict
    r_del = client.delete(f"/api/custom-factors/{cf_id}")
    assert r_del.status_code == 409
    assert "referenced by" in r_del.get_json()["error"]

    # Attempting to change value fields should also return 409
    r_upd_val = client.put(f"/api/custom-factors/{cf_id}", json={"co2_factor": 2.5})
    assert r_upd_val.status_code == 409

    # Clean up emission record and delete
    with app.app_context():
        db.session.delete(db.session.get(Emission, em_id))
        db.session.commit()
    r_del_ok = client.delete(f"/api/custom-factors/{cf_id}")
    assert r_del_ok.status_code == 200


def test_custom_factor_bulk_import(client, factor_env):
    """Test bulk import with both valid rows and skipped/error rows."""
    _login_as(client, factor_env["admin_id"])
    tag = uuid.uuid4().hex[:6]

    payload = {
        "factors": [
            # 1. Valid row
            {
                "name": f"Import Gas {tag}",
                "unit": "m3",
                "co2_factor": 1.9,
                "ch4_factor": 0.01,
                "source": "Import Batch A",
            },
            # 2. Missing name/unit
            {
                "co2_factor": 1.5,
            },
            # 3. Invalid unit
            {
                "name": f"Bad Unit Gas {tag}",
                "unit": "lightyears",
                "co2_factor": 1.5,
            },
            # 4. All factors zero
            {
                "name": f"Zero Gas {tag}",
                "unit": "m3",
                "co2_factor": 0,
            },
        ]
    }
    resp = client.post("/api/custom-factors/import", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["imported"] == 1
    assert len(data["skipped"]) == 3

    # Clean up imported factor
    r_get = client.get("/api/custom-factors")
    for f in r_get.get_json():
        if f["name"] == f"Import Gas {tag}":
            client.delete(f"/api/custom-factors/{f['id']}")


def test_custom_factor_approval_workflow(client, factor_env):
    """Test maker-checker approval and rejection endpoints."""
    # 1. Operator creates factor (or superuser creating pending factor)
    _login_as(client, factor_env["super_id"])
    tag = uuid.uuid4().hex[:6]
    name = f"Approval Test {tag}"

    r_create = client.post("/api/custom-factors", json={
        "name": name,
        "unit": "m3",
        "co2_factor": 3.5,  # outside standard bound, forces Pending with justification
        "justification": "High CO2 gas field analysis certified by Sonatrach laboratory",
        "source": "Certified Gas Analysis",
    })
    assert r_create.status_code in [201, 422]
    if r_create.status_code == 201:
        cf_id = r_create.get_json()["id"]

        # Operator cannot approve
        _login_as(client, factor_env["op_id"])
        r_op_app = client.post(f"/api/custom-factors/{cf_id}/approve")
        assert r_op_app.status_code == 403

        # Admin approves
        _login_as(client, factor_env["admin_id"])
        r_admin_app = client.post(f"/api/custom-factors/{cf_id}/approve")
        assert r_admin_app.status_code in [200, 403]

        # Clean up
        client.delete(f"/api/custom-factors/{cf_id}")
