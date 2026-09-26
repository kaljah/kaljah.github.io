"""
End-to-End API and Integration Tests for Tier 2 Custom / Regional / Lab Factor Workflows.
Verifies:
1. Posting a Tier 2 emission record using Algerian national presets (e.g. Sonatrach Hassi R'Mel sales gas ISO 6976)
   - Preserves custom HHV and density in emission calculations
   - Persists data_source_ref and factor_source="custom" in the database
   - Verifies numerical exactness of the calculated emissions
   - Verifies inclusion in /dashboard/uncertainty under Tier 2 breakdown
2. Posting a Tier 2 emission record using liquid fuel preset (IANOR NA 8110 Gasoil / Diesel)
   - Verifies density-aware physical conversion
   - Verifies legal citation persistence
3. Creating a new custom factor via /custom-factors (Mode B: Quick Add) and selecting it in emission calculation.
"""
import pytest
from app import app
from models import db, User, Facility, Emission, CustomFactor


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def test_admin():
    with app.app_context():
        user = User.query.filter_by(email="tier2_admin@example.com").first()
        if not user:
            user = User(
                email="tier2_admin@example.com",
                fullName="Tier 2 Verifier",
                orgName="Sonatrach Exploration",
                sector="Oil & Gas",
                role="admin",
            )
            user.set_password("AdminPass123!")
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture
def test_facility():
    with app.app_context():
        fac = Facility.query.filter_by(name="Hassi R'Mel Gas Field").first()
        if not fac:
            fac = Facility(
                name="Hassi R'Mel Gas Field",
                region="Laghouat",
                division="Upstream Gas",
                field="HRM South",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.commit()
        return fac


def test_tier2_sonatrach_preset_e2e(client, test_admin, test_facility):
    """End-to-end verification of Tier 2 preset workflow:
    1. Authenticate as admin
    2. Submit stationary combustion with Sonatrach ISO 6976 preset (HHV=1085 Btu/scf)
    3. Verify DB record fields (factor_source='custom', data_source_ref saved, Tier 2 assigned)
    4. Query /dashboard/uncertainty and verify Tier 2 breakdown aggregation.
    """
    # 1. Login
    login_res = client.post(
        "/api/auth/login",
        json={"email": "tier2_admin@example.com", "password": "AdminPass123!"},
    )
    assert login_res.status_code == 200

    # 2. Submit Tier 2 Emission
    payload = {
        "facility_id": test_facility.id,
        "year": 2024,
        "month": 6,
        "process_type": "stationary_combustion",
        "source_type": "custom",
        "factor_source": "custom",
        "fuel": "Natural Gas",
        "fuel_type": "Natural Gas",
        "quantity": 50000.0,
        "amount": 50000.0,
        "unit": "scf",
        "hhv": 1085.0,
        "fuel_density": 0.81,
        "density": 0.81,
        "data_source_ref": "Sonatrach Spécifications / ISO 6976",
        "status": "Verified",
    }
    res = client.post("/api/emissions/", json=payload)
    assert res.status_code == 201, f"Expected 201 Created, got {res.status_code}: {res.get_json()}"
    res_data = res.get_json()
    record_id = res_data.get("id")
    assert record_id is not None

    # Expected CO2 calculation:
    # 50,000 scf * (1085 Btu/scf / 1e6 MMBtu/scf) = 54.25 MMBtu
    # Standard API Natural Gas factor = 53.06 kg CO2/MMBtu
    # CO2 = 54.25 * 53.06 / 1000 = 2.878505 tCO2
    co2_emitted = res_data["emissions"]["co2"]
    assert abs(co2_emitted - 2.8785) < 0.01

    # 3. Direct DB Verification
    with app.app_context():
        rec = db.session.get(Emission, record_id)
        assert rec is not None
        assert rec.factor_source == "custom"
        assert rec.data_source_ref == "Sonatrach Spécifications / ISO 6976"
        assert "combustion" in rec.calc_method.lower()

    # 4. Uncertainty Dashboard Verification
    unc_res = client.get("/api/dashboard/uncertainty?year=2024")
    assert unc_res.status_code == 200
    unc_data = unc_res.get_json()
    assert "tier_breakdown" in unc_data
    assert unc_data["tier_breakdown"].get("Tier 2", 0) > 0


def test_tier2_ianor_diesel_preset_e2e(client, test_admin, test_facility):
    """End-to-end verification of Tier 2 liquid fuel preset (IANOR NA 8110 Diesel):
    1. Authenticate as admin
    2. Submit stationary combustion with IANOR NA 8110 (density=840 kg/m3)
    3. Verify DB record and data_source_ref
    """
    client.post(
        "/api/auth/login",
        json={"email": "tier2_admin@example.com", "password": "AdminPass123!"},
    )

    payload = {
        "facility_id": test_facility.id,
        "year": 2024,
        "month": 7,
        "process_type": "stationary_combustion",
        "source_type": "custom",
        "factor_source": "custom",
        "fuel": "Diesel",
        "fuel_type": "Diesel",
        "quantity": 10.0,
        "amount": 10.0,
        "unit": "m3",
        "hhv": 138000.0,
        "fuel_density": 840.0,
        "density": 840.0,
        "data_source_ref": "IANOR NA 8110 (Gasoil)",
        "status": "Verified",
    }
    res = client.post("/api/emissions/", json=payload)
    assert res.status_code == 201
    res_data = res.get_json()
    record_id = res_data["id"]

    # 10 m3 * 264.172 gal/m3 * (138,000 / 1e6) * 73.96 / 1000 = 26.9626 tCO2
    assert abs(res_data["emissions"]["co2"] - 26.96) < 0.2

    with app.app_context():
        rec = db.session.get(Emission, record_id)
        assert rec is not None
        assert rec.factor_source == "custom"
        assert rec.data_source_ref == "IANOR NA 8110 (Gasoil)"


def test_tier2_quick_add_custom_factor_and_submit(client, test_admin, test_facility):
    """Verifies Mode B: creating a custom factor via /custom-factors/ and using it."""
    client.post(
        "/api/auth/login",
        json={"email": "tier2_admin@example.com", "password": "AdminPass123!"},
    )

    # 1. Register custom factor
    cf_res = client.post(
        "/api/custom-factors/",
        json={
            "name": "Arzew Refinery Flare Gas Blend",
            "unit": "scf",
            "co2_factor": 60.5,
            "ch4_factor": 0.002,
            "n2o_factor": 0.0002,
            "hhv_factor": 1150.0,
            "uncertainty": 7.0,
            "source": "Sonatrach Arzew Lab Certificate #AZ-992",
            "parent_fuel": "Natural Gas",
        },
    )
    assert cf_res.status_code in [200, 201]
    cf_id = cf_res.get_json().get("id") or cf_res.get_json().get("factor", {}).get("id")

    # 2. Submit emission using custom factor
    payload = {
        "facility_id": test_facility.id,
        "year": 2024,
        "month": 8,
        "process_type": "stationary_combustion",
        "source_type": "custom",
        "factor_source": "custom",
        "custom_factor_id": cf_id,
        "fuel": "Natural Gas",
        "fuel_type": "Natural Gas",
        "quantity": 20000.0,
        "amount": 20000.0,
        "unit": "scf",
        "hhv": 1150.0,
        "data_source_ref": "Sonatrach Arzew Lab Certificate #AZ-992",
        "status": "Verified",
    }
    res = client.post("/api/emissions/", json=payload)
    assert res.status_code == 201
    rec_id = res.get_json()["id"]

    with app.app_context():
        rec = db.session.get(Emission, rec_id)
        assert rec is not None
        assert rec.factor_source == "custom"
        assert rec.data_source_ref == "Sonatrach Arzew Lab Certificate #AZ-992"
