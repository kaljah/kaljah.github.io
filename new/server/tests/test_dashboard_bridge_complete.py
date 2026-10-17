"""Tests for routes/dashboard_bridge.py: build_bridge pure helper,
/api/dashboard/yoy-bridge route, mathematical reconciliation, and categories.
"""
import uuid
import pytest
from app import app as flask_app
from extensions import db
from models import Facility, User, Emission, Scope2Emission, Scope3Emission
from routes.dashboard_bridge import build_bridge, BRIDGE_CATEGORIES, SCOPE3_CATEGORY


@pytest.fixture(scope="module")
def bridge_world():
    tag = uuid.uuid4().hex[:6]
    with flask_app.app_context():
        f1 = Facility(name=f"Bridge Fac1 {tag}", region=f"BReg{tag}", activity="EP", division="D",
                      field="F", segment="Upstream", code=f"BF1{tag}")
        f2 = Facility(name=f"Bridge Fac2 {tag}", region=f"Other{tag}", activity="EP", division="D",
                      field="F", segment="Upstream", code=f"BF2{tag}")
        admin = User(email=f"br_admin_{tag}@test.com", fullName="Bridge Admin", orgName="Org",
                     sector="Energy", role="admin", location="Global Corporate Head Office")
        it_user = User(email=f"br_it_{tag}@test.com", fullName="Bridge IT", orgName="Org",
                       sector="Energy", role="it_admin", location="Global Corporate Head Office")
        user = User(email=f"br_user_{tag}@test.com", fullName="Bridge User", orgName="Org",
                    sector="Energy", role="user", location=f"BReg{tag}")
        for u in (admin, it_user, user):
            u.set_password("BridgePass123!")
        db.session.add_all([f1, f2, admin, it_user, user])
        db.session.flush()

        # Seed 2 years of verified emissions for facility 1: 2024 and 2025
        # 2024: Combustion 100t, Flaring 50t, Venting 20t, Fugitive 10t, Scope 2 40t
        e24_comb = Emission(facility_id=f1.id, year=2024, month=6, process_type="combustion",
                            fuel_type="Diesel", quantity=1000, unit="gal", co2e_total=100.0,
                            co2_emissions=95.0, ch4_emissions=0.1, n2o_emissions=0.01, status="Verified")
        e24_flare = Emission(facility_id=f1.id, year=2024, month=6, process_type="flaring",
                             quantity=500, unit="m3", co2e_total=50.0, co2_emissions=45.0,
                             ch4_emissions=0.15, n2o_emissions=0.005, status="Verified")
        e24_vent = Emission(facility_id=f1.id, year=2024, month=6, process_type="venting",
                            quantity=200, unit="m3", co2e_total=20.0, ch4_emissions=0.7, status="Verified")
        e24_fug = Emission(facility_id=f1.id, year=2024, month=6, process_type="fugitive",
                           quantity=100, unit="units", co2e_total=10.0, ch4_emissions=0.35, status="Verified")
        s2_24 = Scope2Emission(facility_id=f1.id, year=2024, month=6, source_type="grid",
                               electricity_kwh=100000, co2e=40.0, co2e_location_based=40.0,
                               co2e_market_based=30.0, status="Verified")
        s3_24 = Scope3Emission(facility_id=f1.id, year=2024, month=6, category="Category 1",
                               activity_data=10000, unit="USD", emission_factor=0.5, co2e=15.0, status="Verified")

        # 2025: Combustion 120t, Flaring 40t, Venting 25t, Fugitive 15t, Scope 2 35t
        e25_comb = Emission(facility_id=f1.id, year=2025, month=6, process_type="combustion",
                            fuel_type="Diesel", quantity=1200, unit="gal", co2e_total=120.0,
                            co2_emissions=114.0, ch4_emissions=0.12, n2o_emissions=0.012, status="Verified")
        e25_flare = Emission(facility_id=f1.id, year=2025, month=6, process_type="flaring",
                             quantity=400, unit="m3", co2e_total=40.0, co2_emissions=36.0,
                             ch4_emissions=0.12, n2o_emissions=0.004, status="Verified")
        e25_vent = Emission(facility_id=f1.id, year=2025, month=6, process_type="venting",
                            quantity=250, unit="m3", co2e_total=25.0, ch4_emissions=0.85, status="Verified")
        e25_fug = Emission(facility_id=f1.id, year=2025, month=6, process_type="fugitive",
                           quantity=150, unit="units", co2e_total=15.0, ch4_emissions=0.5, status="Verified")
        s2_25 = Scope2Emission(facility_id=f1.id, year=2025, month=6, source_type="grid",
                               electricity_kwh=90000, co2e=35.0, co2e_location_based=35.0,
                               co2e_market_based=25.0, status="Verified")
        s3_25 = Scope3Emission(facility_id=f1.id, year=2025, month=6, category="Category 1",
                               activity_data=12000, unit="USD", emission_factor=0.5, co2e=18.0, status="Verified")

        db.session.add_all([e24_comb, e24_flare, e24_vent, e24_fug, s2_24, s3_24,
                            e25_comb, e25_flare, e25_vent, e25_fug, s2_25, s3_25])
        db.session.commit()
        return {"fid1": f1.id, "fid2": f2.id, "admin_id": admin.id, "it_id": it_user.id,
                "user_id": user.id, "tag": tag}


def _login(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid


# =============================================================================
# 1. Pure Helper Tests: build_bridge
# =============================================================================

def test_build_bridge_mathematical_reconciliation():
    rows = [
        {"year": 2023, "combustion": 100.0, "flaring": 50.0, "venting": 30.0, "fugitive": 20.0,
         "process": 5.0, "other": 5.0, "scope2_total": 40.0},
        {"year": 2024, "combustion": 120.0, "flaring": 45.0, "venting": 35.0, "fugitive": 15.0,
         "process": 6.0, "other": 4.0, "scope2_total": 50.0},
    ]
    bridge = build_bridge(rows, year=2024, include_scope3=False)
    assert bridge is not None
    assert bridge["year"] == 2024
    assert bridge["prev_year"] == 2023
    assert bridge["reconciles"] is True

    # Mathematical identity: start + sum(deltas) == end
    start = bridge["start"]
    end = bridge["end"]
    sum_deltas = sum(s["delta"] for s in bridge["steps"])
    assert start + sum_deltas == pytest.approx(end, abs=0.01)

    # Check step names
    names = [s["name"] for s in bridge["steps"]]
    assert names == ["Combustion", "Flaring", "Venting", "Fugitive", "Process & other", "Scope 2"]


def test_build_bridge_with_scope3():
    rows = [
        {"year": 2023, "combustion": 100.0, "flaring": 0.0, "venting": 0.0, "fugitive": 0.0,
         "process": 0.0, "other": 0.0, "scope2_total": 10.0, "scope3": 50.0},
        {"year": 2024, "combustion": 110.0, "flaring": 0.0, "venting": 0.0, "fugitive": 0.0,
         "process": 0.0, "other": 0.0, "scope2_total": 15.0, "scope3": 70.0},
    ]
    bridge = build_bridge(rows, year=2024, include_scope3=True)
    assert bridge is not None
    assert bridge["scope3"] is True
    assert bridge["reconciles"] is True

    step_map = {s["name"]: s["delta"] for s in bridge["steps"]}
    assert step_map["Combustion"] == pytest.approx(10.0)
    assert step_map["Scope 2"] == pytest.approx(5.0)
    assert step_map["Scope 3"] == pytest.approx(20.0)
    assert bridge["start"] == pytest.approx(160.0)
    assert bridge["end"] == pytest.approx(195.0)


def test_build_bridge_edge_cases():
    # Empty rows
    assert build_bridge([], 2024) is None

    # Single year only: cannot compute delta
    single_year = [{"year": 2024, "combustion": 100.0}]
    assert build_bridge(single_year, 2024) is None

    # Year with no prior year
    rows = [
        {"year": 2022, "combustion": 50.0},
        {"year": 2024, "combustion": 100.0},
    ]
    assert build_bridge(rows, 2022) is None  # 2022 has no earlier candidate
    assert build_bridge(rows, 2023) is None  # 2023 not in dataset

    # Unspecified year picks max year
    bridge = build_bridge(rows, year=None)
    assert bridge is not None
    assert bridge["year"] == 2024
    assert bridge["prev_year"] == 2022


# =============================================================================
# 2. Endpoint Tests: /api/dashboard/yoy-bridge
# =============================================================================

def test_yoy_bridge_requires_auth(client):
    res = client.get("/api/dashboard/yoy-bridge")
    assert res.status_code == 401


def test_yoy_bridge_refuses_it_role(client, bridge_world):
    _login(client, bridge_world["it_id"])
    res = client.get("/api/dashboard/yoy-bridge")
    assert res.status_code == 403
    assert "IT Administrators cannot access" in res.get_json()["error"]


def test_yoy_bridge_invalid_year(client, bridge_world):
    _login(client, bridge_world["user_id"])
    res = client.get("/api/dashboard/yoy-bridge?year=not-a-year")
    assert res.status_code == 400
    assert "year" in res.get_json()["error"].lower()


def test_yoy_bridge_calculation_and_reconciliation(client, bridge_world):
    _login(client, bridge_world["admin_id"])
    res = client.get(f"/api/dashboard/yoy-bridge?year=2025&facilityId={bridge_world['fid1']}")
    assert res.status_code == 200
    data = res.get_json()
    assert data is not None
    assert data["year"] == 2025
    assert data["prev_year"] == 2024
    assert data["reconciles"] is True

    # 2024 start: S1 (100+50+20+10=180) + S2 (40) = 220
    # 2025 end:   S1 (120+40+25+15=200) + S2 (35) = 235
    assert data["start"] == pytest.approx(220.0, abs=0.1)
    assert data["end"] == pytest.approx(235.0, abs=0.1)
    assert sum(s["delta"] for s in data["steps"]) == pytest.approx(15.0, abs=0.1)


def test_yoy_bridge_market_vs_location_scope2(client, bridge_world):
    _login(client, bridge_world["admin_id"])
    # Location based
    res_loc = client.get(f"/api/dashboard/yoy-bridge?year=2025&facilityId={bridge_world['fid1']}&scope2_method=location")
    data_loc = res_loc.get_json()
    s2_loc_delta = next(s["delta"] for s in data_loc["steps"] if s["name"] == "Scope 2")

    # Market based: 2024 was 30t, 2025 was 25t -> delta -5t
    res_mkt = client.get(f"/api/dashboard/yoy-bridge?year=2025&facilityId={bridge_world['fid1']}&scope2_method=market")
    data_mkt = res_mkt.get_json()
    s2_mkt_delta = next(s["delta"] for s in data_mkt["steps"] if s["name"] == "Scope 2")

    assert s2_loc_delta == pytest.approx(35.0 - 40.0)  # -5.0
    assert s2_mkt_delta == pytest.approx(25.0 - 30.0)  # -5.0
    assert data_loc["reconciles"] is True
    assert data_mkt["reconciles"] is True


def test_yoy_bridge_with_scope3_route(client, bridge_world):
    _login(client, bridge_world["admin_id"])
    res = client.get(f"/api/dashboard/yoy-bridge?year=2025&facilityId={bridge_world['fid1']}&includeScope3=true")
    assert res.status_code == 200
    data = res.get_json()
    assert data["scope3"] is True
    s3_step = next((s for s in data["steps"] if s["name"] == "Scope 3"), None)
    assert s3_step is not None
    assert s3_step["delta"] == pytest.approx(18.0 - 15.0)  # 3.0
    assert data["reconciles"] is True
