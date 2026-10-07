"""
Test suite for GWP Scientific Uncertainty Propagation (IPCC AR5 Chapter 8 / IPCC 2006 GL Vol. 1 §3.3).
Verifies:
- propagate_co2e_uncertainty Taylor series formula
- GWP parameter uncertainty for CH4 (30%) and N2O (20%)
- Integration with inventory_uncertainty and /dashboard/uncertainty
"""
import math
import pytest
from app import app
from models import db, User, Emission, Facility
from calculations.uncertainty import (
    propagate_co2e_uncertainty,
    propagate_uncertainty,
    GWP_UNCERTAINTY_1SIGMA,
)
from services.inventory_uncertainty import inventory_uncertainty


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


@pytest.fixture
def admin_user():
    with app.app_context():
        user = User.query.filter_by(email="gwp_uncert_admin@example.com").first()
        if not user:
            user = User(
                email="gwp_uncert_admin@example.com",
                fullName="GWP Admin User",
                orgName="AdminOrg",
                sector="Energy",
                role="admin",
            )
            user.set_password("AdminPass123!")
            db.session.add(user)
            db.session.commit()
        return user


def test_propagate_co2e_uncertainty_formula():
    """
    Verify exact Taylor series error propagation per IPCC AR5 Chapter 8:
    sigma_co2e = sqrt(
        sigma_co2^2 +
        (GWP_ch4 * E_ch4)^2 * (u_ch4^2 + u_gwp_ch4^2) +
        (GWP_n2o * E_n2o)^2 * (u_n2o^2 + u_gwp_n2o^2)
    )
    """
    e_co2, u_co2 = 100.0, 0.05
    e_ch4, u_ch4 = 2.0, 0.10
    e_n2o, u_n2o = 0.1, 0.15

    # AR5 standard GWPs: CH4=28, N2O=265
    gwp_dict = {"CO2": 1.0, "CH4": 28.0, "N2O": 265.0}

    res = propagate_co2e_uncertainty(
        e_co2=e_co2, u_co2=u_co2,
        e_ch4=e_ch4, u_ch4=u_ch4,
        e_n2o=e_n2o, u_n2o=u_n2o,
        gwp_dict=gwp_dict,
        include_gwp_uncertainty=True,
    )

    expected_total_co2e = 100.0 + 2.0 * 28.0 + 0.1 * 265.0  # 182.5 tCO2e
    assert res["total_co2e"] == pytest.approx(expected_total_co2e)

    # Variance calculations:
    var_co2 = (100.0 * 0.05) ** 2  # 25.0
    var_ch4 = (2.0 * 28.0) ** 2 * (0.10 ** 2 + 0.30 ** 2)  # 56^2 * 0.10 = 313.6
    var_n2o = (0.1 * 265.0) ** 2 * (0.15 ** 2 + 0.20 ** 2)  # 26.5^2 * 0.0625 = 43.890625
    expected_var = var_co2 + var_ch4 + var_n2o
    expected_sigma = math.sqrt(expected_var)

    assert res["sigma_co2e"] == pytest.approx(expected_sigma, rel=1e-5)
    assert res["relative_uncertainty_1sigma"] == pytest.approx(expected_sigma / expected_total_co2e, rel=1e-5)
    assert res["relative_uncertainty_95pct"] == pytest.approx(2.0 * res["relative_uncertainty_1sigma"], rel=1e-5)
    assert res["gwp_uncertainty_included"] is True

    # Check bounds
    assert 0.0 <= res["lower_bound_95"] < res["total_co2e"] < res["upper_bound_95"]


def test_propagate_co2e_uncertainty_toggle_gwp():
    """Verify that including GWP uncertainty strictly increases the combined uncertainty."""
    e_co2, u_co2 = 50.0, 0.03
    e_ch4, u_ch4 = 5.0, 0.10
    e_n2o, u_n2o = 0.05, 0.10

    with_gwp = propagate_co2e_uncertainty(
        e_co2, u_co2, e_ch4, u_ch4, e_n2o, u_n2o, include_gwp_uncertainty=True
    )
    without_gwp = propagate_co2e_uncertainty(
        e_co2, u_co2, e_ch4, u_ch4, e_n2o, u_n2o, include_gwp_uncertainty=False
    )

    assert with_gwp["total_co2e"] == pytest.approx(without_gwp["total_co2e"])
    assert with_gwp["sigma_co2e"] > without_gwp["sigma_co2e"]
    assert with_gwp["relative_uncertainty_1sigma"] > without_gwp["relative_uncertainty_1sigma"]


def test_propagate_co2e_uncertainty_dict_inputs():
    """Verify propagate_co2e_uncertainty accepts dict objects from propagate_uncertainty."""
    co2_d = propagate_uncertainty(100.0, ef_uncertainty=0.05)
    ch4_d = propagate_uncertainty(2.0, ef_uncertainty=0.15)
    n2o_d = propagate_uncertainty(0.1, ef_uncertainty=0.20)

    res = propagate_co2e_uncertainty(co2_d, e_ch4=ch4_d, e_n2o=n2o_d)
    assert res["total_co2e"] > 100.0
    assert res["sigma_co2e"] > 0.0
    assert "gas_breakdown" in res
    assert "ch4" in res["gas_breakdown"]


def test_inventory_uncertainty_gwp_propagation(client):
    """Verify inventory_uncertainty propagates GWP uncertainty when requested."""
    with app.app_context():
        fac = Facility.query.first()
        if not fac:
            fac = Facility(name="GWP Facility", region="East", country="USA")
            db.session.add(fac)
            db.session.commit()

        # Add emission with CH4
        em = Emission(
            facility_id=fac.id,
            year=2024,
            month=1,
            process_type="combustion",
            fuel_type="Natural Gas",
            co2_emissions=100.0,
            ch4_emissions=1.0,
            n2o_emissions=0.01,
            co2e_total=100.0 + 1.0 * 28.0 + 0.01 * 265.0,
            status="Verified",
            uncertainty_ad=0.05,
            uncertainty_ef_co2=0.03,
            uncertainty_ef_ch4=0.10,
            uncertainty_ef_n2o=0.15,
            ef_key="catalog:NatGas_GWP",
        )
        db.session.add(em)
        db.session.commit()

        u_without = inventory_uncertainty(2024, facility_id=fac.id, include_gwp_uncertainty=False)
        u_with = inventory_uncertainty(2024, facility_id=fac.id, include_gwp_uncertainty=True)

        assert u_with["inventory_uncertainty_1sigma"] > u_without["inventory_uncertainty_1sigma"]
        assert u_with["gwp_uncertainty_included"] is True
        assert u_without["gwp_uncertainty_included"] is False


def test_dashboard_uncertainty_gwp_query_param(client, admin_user):
    """Verify /api/dashboard/uncertainty?gwp_uncertainty=true returns gwp_uncertainty_included=true."""
    client.post(
        "/api/auth/login",
        json={"email": "gwp_uncert_admin@example.com", "password": "AdminPass123!"},
    )
    res = client.get("/api/dashboard/uncertainty?gwp_uncertainty=true&year=2024")
    assert res.status_code == 200
    data = res.get_json()
    assert data["gwp_uncertainty_included"] is True
