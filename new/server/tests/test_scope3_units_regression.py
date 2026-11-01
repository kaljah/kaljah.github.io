import pytest
from calculations.units import compute_scope3_co2e, _scope3_activity_in_factor_unit
from input_validation import ValidationError
from tests.audit_helpers import make_user, make_facility, login


def test_scope3_natural_gas_hhv_conversion():
    """Item 1.4: Natural gas uses EF 54.18 kg/MMBtu.
    When activity is in mcf, 1 mcf = 1.020 MMBtu via HHV (1020 Btu/scf).
    5000 mcf * 1.020 MMBtu/mcf * 54.18 kg/MMBtu / 1000 = 276.318 tCO2e.
    """
    scale = _scope3_activity_in_factor_unit("mcf", "mmbtu")
    assert scale == pytest.approx(1.020, rel=1e-4)

    co2e_mcf = compute_scope3_co2e(5000.0, 54.18, "kg CO2e / MMBtu", activity_unit="mcf")
    assert co2e_mcf == pytest.approx(276.318, rel=1e-4)

    co2e_mmbtu = compute_scope3_co2e(5000.0, 54.18, "kg CO2e / MMBtu", activity_unit="MMBtu")
    assert co2e_mmbtu == pytest.approx(270.9, rel=1e-4)


def test_scope3_incompatible_units_rejected():
    """Item 1.4: Incompatible activity units must be rejected with ValidationError."""
    # Liquid volume (bbl) against energy factor (MMBtu)
    with pytest.raises(ValidationError) as exc1:
        compute_scope3_co2e(100.0, 54.18, "kg CO2e / MMBtu", activity_unit="bbl")
    assert "cannot be converted" in exc1.value.message

    # Gas volume (mcf) against liquid factor (bbl)
    with pytest.raises(ValidationError) as exc2:
        compute_scope3_co2e(100.0, 433.44, "kg CO2e / bbl", activity_unit="mcf")
    assert "cannot be converted" in exc2.value.message

    # Spend (USD) against energy factor (MMBtu)
    with pytest.raises(ValidationError) as exc3:
        compute_scope3_co2e(100.0, 54.18, "kg CO2e / MMBtu", activity_unit="USD")
    assert ("cannot be converted" in exc3.value.message or "cannot be matched" in exc3.value.message)


def test_scope3_explicit_factor_unit_stored(client, app):
    """Item 1.4: Verify that factor_unit is explicitly stored with its denominator."""
    from models import Scope3Emission
    from extensions import db

    with app.app_context():
        admin = make_user("admin")
        fac = make_facility()
        login(client, admin)

        payload = {
            "facility_id": fac.id,
            "year": 2026,
            "month": 6,
            "category": "Category 11",
            "sub_category": "Natural Gas",
            "activity_data": 2000.0,
            "unit": "mcf",
            "emission_factor": 54.18,
            "factor_unit": "kg CO2e / MMBtu",
            "status": "Verified",
        }
        resp = client.post("/api/scope3", json=payload)
        assert resp.status_code == 201, resp.get_json()
        rec_id = resp.get_json()["id"]

        rec = db.session.get(Scope3Emission, rec_id)
        assert rec is not None
        assert rec.factor_unit == "kg CO2e / MMBtu"
        # 2000 mcf * 1.020 * 54.18 / 1000 = 110.5272
        assert rec.co2e == pytest.approx(110.5272, rel=1e-3)
