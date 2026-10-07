"""Tests for Scope 2 Dual Reporting Architecture (GHG Protocol Scope 2 Guidance).

Validates:
1. Dual calculation of Location-Based and Market-Based emissions.
2. Market instruments: REC / PPA zero emissions, custom supplier tariffs.
3. Fallback to location-based / residual grid when no market instrument is specified.
4. Recalculation on update.
5. Dual reporting persistence in bulk import.
6. Report generation outputting both location-based and market-based metrics.
"""
import pytest
from extensions import db
from models import Scope2Emission, Facility
from tests.audit_helpers import login, make_facility, make_user


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield


def test_scope2_default_is_dual_reported_with_grid_fallback(client, ctx):
    """When no market instrument is claimed, market-based emissions fall back to location-based."""
    fac = make_facility(region="West")
    user = make_user("admin", "Global")
    login(client, user)

    r = client.post(
        "/api/scope2",
        json={
            "facility_id": fac.id,
            "year": 2026,
            "month": 1,
            "source_type": "electricity",
            "electricity_kwh": 10000,
            "grid_region": "Algerian National Grid",
        },
    )
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    data = r.get_json()
    assert "co2e_location_based" in data["record"]
    assert "co2e_market_based" in data["record"]

    loc_val = data["record"]["co2e_location_based"]
    mkt_val = data["record"]["co2e_market_based"]
    assert loc_val > 0
    assert mkt_val == loc_val  # Fallback to location-based grid factor

    # Verify directly from DB
    emission = db.session.get(Scope2Emission, data["id"])
    assert emission.co2e_location_based == loc_val
    assert emission.co2e_market_based == mkt_val
    assert emission.co2e == loc_val


def test_scope2_market_instrument_zero_ppa_rec(client, ctx):
    """Renewable Energy Certificates (REC) or zero-carbon PPAs yield 0 market-based emissions."""
    fac = make_facility(region="West")
    user = make_user("admin", "Global")
    login(client, user)

    r = client.post(
        "/api/scope2",
        json={
            "facility_id": fac.id,
            "year": 2026,
            "month": 2,
            "source_type": "electricity",
            "electricity_kwh": 50000,
            "grid_region": "Algerian National Grid",
            "market_instrument_type": "REC",
        },
    )
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    data = r.get_json()["record"]

    assert data["co2e_location_based"] > 0
    assert data["co2e_market_based"] == 0.0
    assert data["market_instrument_type"] == "REC"
    assert data["market_emission_factor"] == 0.0


def test_scope2_market_instrument_custom_supplier_tariff(client, ctx):
    """A supplier-specific contract with a certified emission factor computes distinct market CO2e."""
    fac = make_facility(region="West")
    user = make_user("admin", "Global")
    login(client, user)

    kwh = 20000
    supplier_ef = 0.25  # kg CO2e / kWh

    r = client.post(
        "/api/scope2",
        json={
            "facility_id": fac.id,
            "year": 2026,
            "month": 3,
            "source_type": "electricity",
            "electricity_kwh": kwh,
            "grid_region": "Algerian National Grid",
            "market_instrument_type": "supplier_contract",
            "market_emission_factor": supplier_ef,
        },
    )
    assert r.status_code in (200, 201), r.get_data(as_text=True)
    data = r.get_json()["record"]

    expected_market_co2e = (kwh * supplier_ef) / 1000.0  # 5.0 tCO2e
    assert round(data["co2e_market_based"], 4) == round(expected_market_co2e, 4)
    assert data["co2e_location_based"] != data["co2e_market_based"]
    assert data["market_emission_factor"] == supplier_ef


def test_scope2_update_recalculates_dual_values(client, ctx):
    """Updating activity or market contract recalculates both location and market figures."""
    fac = make_facility(region="West")
    user = make_user("admin", "Global")
    login(client, user)

    # 1. Create standard record
    r1 = client.post(
        "/api/scope2",
        json={
            "facility_id": fac.id,
            "year": 2026,
            "month": 4,
            "source_type": "electricity",
            "electricity_kwh": 10000,
            "grid_region": "Algerian National Grid",
        },
    )
    rec_id = r1.get_json()["id"]

    # 2. Update with PPA
    r2 = client.put(
        f"/api/scope2/{rec_id}",
        json={
            "electricity_kwh": 20000,
            "market_instrument_type": "renewable_ppa",
            "market_emission_factor": 0.0,
        },
    )
    assert r2.status_code == 200

    # 3. Verify updated dual metrics
    db.session.expire_all()
    updated = db.session.get(Scope2Emission, rec_id)
    assert updated.electricity_kwh == 20000
    assert updated.co2e_location_based > 0
    assert updated.co2e_market_based == 0.0
    assert updated.market_instrument_type == "renewable_ppa"


def test_scope2_bulk_import_dual_reporting(client, ctx):
    """Bulk import correctly parses and persists market-based attributes."""
    fac = make_facility(region="West")
    user = make_user("admin", "Global")
    login(client, user)

    records = [
        {
            "facility_id": fac.id,
            "year": 2026,
            "month": 5,
            "consumption": 10000,
            "unit": "kWh",
            "grid_region": "Algerian National Grid",
            "market_instrument_type": "REC",
        },
        {
            "facility_id": fac.id,
            "year": 2026,
            "month": 6,
            "consumption": 10000,
            "unit": "kWh",
            "grid_region": "Algerian National Grid",
            "market_instrument_type": "supplier_specific",
            "market_emission_factor": 0.12,
        },
    ]

    r = client.post("/api/scope2/bulk-import", json={"records": records})
    assert r.status_code == 200, r.get_data(as_text=True)

    imported = (
        Scope2Emission.query.filter_by(facility_id=fac.id, year=2026)
        .filter(Scope2Emission.month.in_([5, 6]))
        .all()
    )
    assert len(imported) == 2

    rec_row = next(e for e in imported if e.month == 5)
    assert rec_row.co2e_market_based == 0.0
    assert rec_row.co2e_location_based > 0

    supp_row = next(e for e in imported if e.month == 6)
    assert supp_row.co2e_location_based > 0
    assert round(supp_row.co2e_market_based, 4) == round((10000 * 0.12) / 1000.0, 4)


def test_scope2_listing_and_reports_include_dual_metrics(client, ctx):
    """Listing endpoints and report generations include both location and market figures."""
    fac = make_facility(region="West")
    user = make_user("admin", "Global")
    login(client, user)

    client.post(
        "/api/scope2",
        json={
            "facility_id": fac.id,
            "year": 2026,
            "month": 7,
            "source_type": "electricity",
            "electricity_kwh": 30000,
            "grid_region": "Algerian National Grid",
            "market_instrument_type": "REC",
        },
    )

    # 1. Test GET /api/scope2
    r_list = client.get(f"/api/scope2?facility_id={fac.id}&year=2026")
    assert r_list.status_code == 200
    rows = r_list.get_json()
    row = next(r for r in rows if r["month"] == 7)
    assert "co2e_location_based" in row
    assert "co2e_market_based" in row
    assert row["co2e_market_based"] == 0.0
    assert row["co2e_location_based"] > 0
