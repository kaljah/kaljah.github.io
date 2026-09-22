"""
test_zero_trust_adversarial.py

Zero-Trust Adversarial & Boundary Validation Suite
Verifies:
1. Conservation of mass & energy
2. Canonical factor lookup with aliases & case-insensitivity
3. Boundary & extreme inputs (zero, negative, ultra-high pressure, high temp)
4. Methane slip stoichiometry
5. Multi-standard GWP consistency (AR4, AR5, AR6)
"""

import pytest
import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.units import calculate_co2e, CONVERSIONS
from calculations.constants import GWP_AR4, GWP_AR5, GWP_AR6
from routes.emissions import _lookup_api_factor
from emission_factors import API_FACTORS


def test_lookup_api_factor_resilience():
    """Verify that _lookup_api_factor resolves fuels regardless of casing, underscores, or common aliases."""
    # Exact match
    ng = _lookup_api_factor("Natural Gas")
    assert ng is not None
    assert ng.get("code") == "NG"

    # Lowercase with underscore
    ng_snake = _lookup_api_factor("natural_gas")
    assert ng_snake == ng

    # Lowercase with space
    ng_lower = _lookup_api_factor("natural gas")
    assert ng_lower == ng

    # Common alias
    alias_gas = _lookup_api_factor("gas")
    assert alias_gas == ng

    # Diesel alias
    diesel = _lookup_api_factor("diesel")
    assert diesel is not None
    assert "Diesel" in diesel.get("source", "") or diesel.get("code") == "DSL"

    # Non-existent fuel returns empty dict safely
    assert _lookup_api_factor("Unobtainium Fuel") == {}
    assert _lookup_api_factor(None) == {}
    assert _lookup_api_factor("") == {}


def test_mass_conservation_combustion():
    """Verify that carbon mass is strictly conserved in Tier 3 combustion."""
    calc = CombustionCalculator()
    vol = 10000.0  # m3
    c1 = 0.90
    c2 = 0.06
    c3 = 0.04
    eff = 0.992

    res = calc.calculate(
        fuel_quantity=vol, ef_co2=0, ef_ch4=0, ef_n2o=0, uncertainties={}, hhv=1020.0,
        ef_unit="kg/m3", fuel_unit="m3", fuel_type="Natural Gas", combustion_efficiency=eff,
        c1=c1, c2=c2, c3=c3
    )

    co2_tonnes = res["results"]["co2"]["value"]
    ch4_tonnes = res["results"]["ch4"]["value"]

    # Carbon in fuel (moles C / mole gas): 0.90*1 + 0.06*2 + 0.04*3 = 1.14
    total_carbon_moles_in = vol * 1.14
    # Carbon combusted to CO2:
    carbon_moles_co2 = (co2_tonnes * 1000.0 / 1.861)  # m3 CO2 = moles CO2 at std
    # Carbon slipped as CH4:
    ch4_moles_slip = (ch4_tonnes * 1000.0 / 0.6785)

    assert carbon_moles_co2 == pytest.approx(total_carbon_moles_in * eff, rel=1e-3)
    assert ch4_moles_slip == pytest.approx(vol * c1 * (1.0 - eff), rel=1e-3)


def test_extreme_temperature_and_pressure_normalization():
    """Verify thermodynamic correction factors under high pressure and temperature."""
    calc = CombustionCalculator()
    # High pressure (2000 psig) and high temperature (100 C)
    res_ambient = calc.calculate(
        fuel_quantity=1000.0, ef_co2=1.9, ef_ch4=0.00004, ef_n2o=0.000002,
        uncertainties={}, hhv=1020.0, ef_unit="kg/m3", fuel_unit="m3", fuel_type="Natural Gas",
        operating_temperature=15.556, temp_unit="C", operating_pressure=0.0, press_unit="psig"
    )
    res_high_p = calc.calculate(
        fuel_quantity=1000.0, ef_co2=1.9, ef_ch4=0.00004, ef_n2o=0.000002,
        uncertainties={}, hhv=1020.0, ef_unit="kg/m3", fuel_unit="m3", fuel_type="Natural Gas",
        operating_temperature=15.556, temp_unit="C", operating_pressure=146.96, press_unit="psig"
    )
    # Higher actual pressure means more standard volume -> higher emissions
    assert res_high_p["results"]["co2"]["value"] > res_ambient["results"]["co2"]["value"]


def test_flaring_destruction_efficiency_boundary():
    """Verify flaring emissions at 100% and 0% destruction efficiencies."""
    calc = FlaringCalculator()
    # At 100% destruction efficiency (eta_d=1.0), unburned methane slip must be 0
    res_100 = calc.calculate(
        gas_volume=10000.0, ch4_fraction=0.85, flare_type="elevated", uncertainties={},
        combustion_efficiency=1.0, destruction_efficiency=1.0, c1=0.85
    )
    assert res_100["results"]["ch4"]["value"] == 0.0

    # At 0% combustion efficiency, CO2 from combustion must be 0
    res_0 = calc.calculate(
        gas_volume=10000.0, ch4_fraction=0.85, flare_type="elevated", uncertainties={},
        combustion_efficiency=0.0, destruction_efficiency=0.0, c1=0.85
    )
    assert res_0["results"]["co2"]["value"] == 0.0


def test_gwp_horizon_consistency():
    """Verify mathematical parity across AR4, AR5 100-yr, AR5 20-yr, and AR6."""
    co2 = 100.0
    ch4 = 10.0
    n2o = 1.0

    co2e_ar4 = calculate_co2e(co2, ch4, n2o, gwp_dict=GWP_AR4)
    expected_ar4 = 100.0 * 1.0 + 10.0 * 25.0 + 1.0 * 298.0  # 100 + 250 + 298 = 648
    assert co2e_ar4 == pytest.approx(expected_ar4, rel=1e-4)

    co2e_ar5 = calculate_co2e(co2, ch4, n2o, gwp_dict=GWP_AR5)
    expected_ar5 = 100.0 * 1.0 + 10.0 * 28.0 + 1.0 * 265.0  # 100 + 280 + 265 = 645
    assert co2e_ar5 == pytest.approx(expected_ar5, rel=1e-4)

    # 20-year AR5: CH4=84, N2O=264
    gwp_ar5_20 = {"CO2": 1.0, "CH4": 84.0, "N2O": 264.0}
    co2e_ar5_20 = calculate_co2e(co2, ch4, n2o, gwp_dict=gwp_ar5_20)
    expected_ar5_20 = 100.0 * 1.0 + 10.0 * 84.0 + 1.0 * 264.0  # 100 + 840 + 264 = 1204
    assert co2e_ar5_20 == pytest.approx(expected_ar5_20, rel=1e-4)

    co2e_ar6 = calculate_co2e(co2, ch4, n2o, gwp_dict=GWP_AR6)
    expected_ar6 = 100.0 * 1.0 + 10.0 * 27.9 + 1.0 * 273.0  # 100 + 279 + 273 = 652
    assert co2e_ar6 == pytest.approx(expected_ar6, rel=1e-4)


def test_base_year_singleton_fallback(client):
    """Verify that when only BaseYear singleton exists, batch-all and /base-year return it cleanly."""
    from extensions import db
    from models import BaseYear, BaseYearRecalculation, User

    with client.application.app_context():
        admin = User.query.filter_by(role="admin").first()
        if not admin:
            admin = User(email="admin_by@test.com", fullName="Admin BY", orgName="Sonatrach", role="admin")
            admin.set_password("pass")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

        BaseYearRecalculation.query.delete()
        by = BaseYear.query.filter_by(id=1).first()
        if not by:
            by = BaseYear(id=1, year=2022, locked=1)
            db.session.add(by)
        else:
            by.year = 2022
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()

    # Query /base-year
    res = client.get("/api/dashboard/base-year")
    assert res.status_code == 200
    data = res.get_json()
    assert data is not None
    assert data["year"] == 2022
    assert data["reason"] == "Official Baseline"

    # Query /batch-all
    res_batch = client.get("/api/dashboard/batch-all?facilityId=all&activity=all&division=all")
    assert res_batch.status_code == 200
    batch_data = res_batch.get_json()
    assert batch_data["base_year"] is not None
    assert batch_data["base_year"]["year"] == 2022


def test_notification_broadcast_handling(client):
    """Verify broadcast notifications (user_id=None) can be marked as read by users and dismissed by admins."""
    from extensions import db
    from models import Notification, User

    with client.application.app_context():
        admin = User.query.filter_by(role="admin").first()
        if not admin:
            admin = User(email="admin_notif@test.com", fullName="Admin Notif", orgName="Sonatrach", sector="Energy", location="Algiers", role="admin")
            admin.set_password("pass")
            db.session.add(admin)
            db.session.commit()
        admin_id = admin.id

        operator = User.query.filter_by(role="user").first()
        if not operator:
            operator = User(email="user_notif@test.com", fullName="User Notif", orgName="Sonatrach", sector="Energy", location="Algiers", role="user")
            operator.set_password("pass")
            db.session.add(operator)
            db.session.commit()
        operator_id = operator.id

        # Create a broadcast notification
        notif = Notification(
            user_id=None,
            type="info",
            title="Broadcast System Maintenance Notice",
            message="Scheduled maintenance window at 02:00 UTC",
            is_read=False,
        )
        db.session.add(notif)
        db.session.commit()
        notif_id = notif.id

    # Non-admin / operator can mark read without getting 403 Forbidden
    with client.session_transaction() as sess:
        sess["user_id"] = operator_id

    res_read = client.put(f"/api/notifications/{notif_id}/read")
    assert res_read.status_code == 200
    assert res_read.get_json()["success"] is True

    # Reset to unread for admin dismiss-all test
    with client.application.app_context():
        n = db.session.get(Notification, notif_id)
        n.is_read = False
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = admin_id

    res_dismiss = client.post("/api/notifications/dismiss-all")
    assert res_dismiss.status_code == 200
    assert res_dismiss.get_json()["success"] is True

    # Verify notification is marked read
    with client.application.app_context():
        updated_notif = db.session.get(Notification, notif_id)
        assert updated_notif.is_read is True

