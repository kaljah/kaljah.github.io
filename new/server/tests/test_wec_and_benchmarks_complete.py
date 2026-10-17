"""Tests for EPA Waste Emissions Charge (40 CFR 99 / IRA s.136),
Decree 21-330 flaring intensity, NGSI methane intensity, and OGCI benchmarks.
"""
import uuid
import pytest
from app import app as flask_app
from extensions import db
from models import Facility, User, Emission, ProductionData, FlaringDetail
from services.intensity import (
    wec_applies_to_country,
    segment_category,
    facility_row,
    intensity_cells,
    WEC_CH4_DENSITY_T_PER_MSCF,
    WEC_RATE_USD_PER_T,
    WEC_FIRST_YEAR,
)


@pytest.fixture(scope="module")
def wec_world():
    tag = uuid.uuid4().hex[:6]
    with flask_app.app_context():
        # US facility for WEC testing
        us_fac = Facility(name=f"Permian Site {tag}", region=f"Texas{tag}", activity="EP", division="D",
                          field="F", segment="Upstream", code=f"US{tag}", country="United States")
        # Non-US facility for Decree 21-330 testing
        dz_fac = Facility(name=f"Hassi Messaoud {tag}", region=f"Ouargla{tag}", activity="EP", division="D",
                          field="F", segment="Upstream", code=f"DZ{tag}", country="Algeria")

        admin = User(email=f"wec_admin_{tag}@test.com", fullName="WEC Admin", orgName="Org",
                     sector="Energy", role="admin", location="Global Corporate Head Office")
        user = User(email=f"wec_user_{tag}@test.com", fullName="WEC User", orgName="Org",
                    sector="Energy", role="user", location=f"Texas{tag}")
        for u in (admin, user):
            u.set_password("WecPass123!")
        db.session.add_all([us_fac, dz_fac, admin, user])
        db.session.flush()

        # Seed US facility in 2034 (statutory WEC start year)
        # 10,000,000 m3 gas produced (~353,146 Mscf).
        # Upstream threshold is 0.20% -> allowed CH4 = 353,146 * 0.002 * 0.0192 = 13.56 t CH4
        # Emit 25 t CH4 -> excess = 11.44 t -> fee = 11.44 * 1500 = $17,160
        prod_us = ProductionData(facility_id=us_fac.id, year=2034, month=6,
                                 gas_amount=10_000_000, gas_unit="m3", oil_amount=50000, oil_unit="bbl")
        em_us = Emission(facility_id=us_fac.id, year=2034, month=6, process_type="venting",
                         quantity=1000, unit="m3", co2e_total=700.0, ch4_emissions=25.0, status="Verified")

        # Seed Algerian facility in 2024 for Decree 21-330 flaring intensity
        # Gas produced: 10,000,000 m3
        # Flared gas: 80,000 m3 (0.80% flaring intensity -> COMPLIANT <= 1.00%)
        prod_dz_24 = ProductionData(facility_id=dz_fac.id, year=2024, month=6,
                                    gas_amount=10_000_000, gas_unit="m3", oil_amount=100000, oil_unit="bbl")
        flare_dz_24 = Emission(facility_id=dz_fac.id, year=2024, month=6, process_type="flaring",
                               quantity=80_000, unit="m3", co2e_total=200.0, co2_emissions=180.0,
                               ch4_emissions=0.5, status="Verified")
        # Detail record with measured DRE
        fd_dz_24 = FlaringDetail(facility_id=dz_fac.id, year=2024, routine_knm3=60.0, non_routine_knm3=20.0,
                                 safety_knm3=0.0, measured_dre_pct=98.5, status="Verified")

        # 2025: Flared gas 150,000 m3 (1.50% flaring intensity -> NON-COMPLIANT > 1.00%)
        prod_dz_25 = ProductionData(facility_id=dz_fac.id, year=2025, month=6,
                                    gas_amount=10_000_000, gas_unit="m3", oil_amount=100000, oil_unit="bbl")
        flare_dz_25 = Emission(facility_id=dz_fac.id, year=2025, month=6, process_type="flaring",
                               quantity=150_000, unit="m3", co2e_total=375.0, co2_emissions=340.0,
                               ch4_emissions=0.9, status="Verified")

        db.session.add_all([prod_us, em_us, prod_dz_24, flare_dz_24, fd_dz_24, prod_dz_25, flare_dz_25])
        db.session.commit()
        return {"us_fid": us_fac.id, "dz_fid": dz_fac.id, "admin_id": admin.id, "user_id": user.id, "tag": tag}


def _login(client, uid):
    with client.session_transaction() as s:
        s["user_id"] = uid


# =============================================================================
# 1. Pure Helper Unit Tests: WEC Rules and Segment Classifiers
# =============================================================================

@pytest.mark.parametrize("country,expected", [
    ("United States", True), ("USA", True), ("us", True), ("U.S.A.", True),
    ("Algeria", False), ("France", False), ("", False), (None, False),
])
def test_wec_applies_to_country(country, expected):
    assert wec_applies_to_country(country) is expected


@pytest.mark.parametrize("segment,expected", [
    ("Upstream Exploration", "upstream"), ("E&P Operations", "upstream"),
    ("Production Facility", "upstream"), ("Gas Processing Plant", "midstream"),
    ("LNG Terminal", "midstream"), ("Pipeline Transmission", "midstream"),
    ("Refining & Chemicals", "downstream"), ("Petrochemical Unit", "downstream"),
    ("Unknown Segment", None), ("", None), (None, None),
])
def test_segment_category(segment, expected):
    assert segment_category(segment) == expected


def test_wec_mathematical_fee_computation(wec_world):
    # Retrieve cells for US facility in 2034
    cells = intensity_cells(years=[2034], facility_id=wec_world["us_fid"])
    cell_list = [(2034, cells[(wec_world["us_fid"], 2034)])]
    us_fac = db.session.get(Facility, wec_world["us_fid"])

    row = facility_row(wec_world["us_fid"], cell_list, us_fac, year_value=2034)
    assert row["wec_rate_usd_per_t"] == 1500.0
    assert row["wec_status"] == "Taxable Liability"
    assert row["excess_ch4_tonnes"] > 0
    # Expected fee = excess * 1500
    assert row["wec_fee_usd"] == pytest.approx(row["excess_ch4_tonnes"] * 1500.0, abs=0.01)


def test_wec_non_us_and_prior_year_exemptions(wec_world):
    dz_fac = db.session.get(Facility, wec_world["dz_fid"])
    cells = intensity_cells(years=[2024], facility_id=wec_world["dz_fid"])
    cell_list = [(2024, cells[(wec_world["dz_fid"], 2024)])]

    # Non-US facility
    row_dz = facility_row(wec_world["dz_fid"], cell_list, dz_fac, year_value=2024)
    assert row_dz["wec_fee_usd"] is None
    assert "US subpart W" in row_dz["wec_status"]

    # US facility prior to statutory start year (e.g. 2024)
    us_fac = db.session.get(Facility, wec_world["us_fid"])
    row_us_early = facility_row(wec_world["us_fid"], cell_list, us_fac, year_value=2024)
    assert row_us_early["wec_fee_usd"] is None
    assert "charge starts with" in row_us_early["wec_status"]

    # All years aggregate view
    row_all_years = facility_row(wec_world["us_fid"], cell_list, us_fac, year_value="all")
    assert row_all_years["wec_status"] == "Select a single year"


# =============================================================================
# 2. Decree 21-330 Flaring Intensity: /api/dashboard/flaring-summary
# =============================================================================

def test_flaring_summary_decree_21_330_compliant(client, wec_world):
    _login(client, wec_world["admin_id"])
    res = client.get(f"/api/dashboard/flaring-summary?year=2024&facilityId={wec_world['dz_fid']}")
    assert res.status_code == 200
    data = res.get_json()

    # 80,000 m3 flared / 10,000,000 m3 produced = 0.800 %
    assert data["flaring_intensity_pct"] == pytest.approx(0.80, abs=0.01)
    assert data["regulatory_threshold_pct"] == 1.00
    assert data["statute"] == "Executive Decree 21-330 Article 9"
    assert data["is_compliant"] is True
    assert "COMPLIANT" in data["compliance_status"]
    assert data["measured_dre_pct"] == 98.5


def test_flaring_summary_decree_21_330_exceeds_threshold(client, wec_world):
    _login(client, wec_world["admin_id"])
    res = client.get(f"/api/dashboard/flaring-summary?year=2025&facilityId={wec_world['dz_fid']}")
    assert res.status_code == 200
    data = res.get_json()

    # 150,000 m3 flared / 10,000,000 m3 produced = 1.500 %
    assert data["flaring_intensity_pct"] == pytest.approx(1.50, abs=0.01)
    assert data["is_compliant"] is False
    assert "EXCEEDS THRESHOLD" in data["compliance_status"]

    # YoY change: from 80k m3 to 150k m3 -> (150-80)/80 * 100 = 87.5%
    assert data["yoy_change_pct"] == pytest.approx(87.5, abs=0.1)


# =============================================================================
# 3. NGSI & OGCI Benchmarks: /api/dashboard/granular-intensities
# =============================================================================

def test_granular_intensities_ngsi_and_ogci(client, wec_world):
    _login(client, wec_world["admin_id"])
    res = client.get(f"/api/dashboard/granular-intensities?year=2024&facilityId={wec_world['dz_fid']}")
    assert res.status_code == 200
    data = res.get_json()

    assert data["ogci_target_kg_boe"] == 17.0
    assert data["total_production_boe"] > 0
    assert data["ci_by_total_production_kg_boe"] is not None

    # Ratio to OGCI target
    ratio = data["ratio_to_ogci_target"]
    assert ratio is not None
    if data["ci_by_total_production_kg_boe"] <= 17.0:
        assert data["ogci_status"] == "WITHIN TARGET"
    else:
        assert "ABOVE TARGET" in data["ogci_status"]

    # NGSI methane intensity (wt %)
    # CH4 mass (tonnes) / (gross gas m3 * 0.00080) * 100%
    assert data["methane_intensity_ngsi_wt_pct"] is not None
    assert data["methane_intensity_ngsi_wt_pct"] > 0
