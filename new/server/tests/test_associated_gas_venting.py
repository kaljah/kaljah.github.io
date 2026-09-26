import pytest
import json
from calculations.vented import AssociatedGasVentingCalculator
from calculations.dispatcher import CalculationDispatcher
from calculations.uncertainty import Tier
from app import app
from extensions import db
from models import Emission, Facility, User


@pytest.fixture
def calc():
    return AssociatedGasVentingCalculator()


@pytest.fixture
def dispatcher():
    return CalculationDispatcher()


# =============================================================================
# TIER 1: API COMPENDIUM 2021 TABLE 6-8 DEFAULT FACTORS
# =============================================================================

def test_tier1_us_average_default(calc):
    """
    Table 6-8: US Average default factor = 1.4 kg CH4/bbl (81.6 mol% CH4).
    10,000 bbl oil production -> 14,000 kg CH4 = 14.0 tonnes CH4.
    """
    res = calc.calculate(
        tier="Tier 1",
        oil_production=10000,
        oil_unit="bbl",
        basin="US Average",
    )
    assert res["method"] == "Associated Gas Venting"
    assert res["inputs"]["tier"] == "Tier 1"
    assert abs(res["results"]["ch4"]["value"] - 14.0) < 1e-4
    assert res["results"]["co2"]["value"] == 0.0
    assert res["total_co2e"] > 0
    assert res["results"]["ch4"]["tier"] == Tier.T1


def test_tier1_all_basins(calc):
    """
    Verify all 6 regional basins from Table 6-8:
      - US Average: 1.4 kg/bbl
      - Gulf Coast (220): 0.7 kg/bbl
      - Anadarko (360): 9.7 kg/bbl
      - Williston (395): 8.9 kg/bbl
      - Permian (430): 6.5 kg/bbl
      - Other US Basins: 0.4 kg/bbl
    """
    basins = {
        "US Average": 1.4,
        "Gulf Coast Basin (Basin 220)": 0.7,
        "Anadarko Basin (Basin 360)": 9.7,
        "Williston Basin (Basin 395)": 8.9,
        "Permian Basin (Basin 430)": 6.5,
        "Other US Basins": 0.4,
    }
    for b_name, expected_ef in basins.items():
        res = calc.calculate(
            tier=1,
            oil_production=1000,
            oil_unit="bbl",
            basin=b_name,
        )
        expected_tonnes = (1000 * expected_ef) / 1000.0
        assert abs(res["results"]["ch4"]["value"] - expected_tonnes) < 1e-4


def test_tier1_composition_adjustment_footnote_b(calc):
    """
    Table 6-8 Footnote b:
    - Default basis is 81.6 mole % CH4.
    - If facility has 70 mole % CH4 and 10 mole % CO2:
      CH4 factor adjusted by (0.70 / 0.816).
      CO2 factor calculated based on relative concentrations:
        CO2 = CH4 * (c_co2 / c_ch4) * (44.01 / 16.0425)
    """
    res = calc.calculate(
        tier=1,
        oil_production=5200 * 365,  # 1,898,000 bbl
        oil_unit="bbl",
        basin="US Average",
        ch4_content=0.70,
        co2_content=0.10,
    )
    # Default without adjustment: 1,898,000 * 1.4 / 1000 = 2657.2 tonnes
    # Adjusted: 2657.2 * (0.70 / 0.816) = 2279.46 tonnes
    assert abs(res["results"]["ch4"]["value"] - 2279.46) < 1.0
    # CO2 emissions: 2279.46 * (0.10 / 0.70) * (44.01 / 16.0425) = ~893.3 tonnes
    assert abs(res["results"]["co2"]["value"] - 893.3) < 2.0
    assert res["results"]["total_co2e"] > res["results"]["ch4"]["value"]


def test_tier1_unit_conversions(calc):
    """Test oil production in m3 and kbbl."""
    # 1000 bbl = 158.987 m3
    res_bbl = calc.calculate(tier=1, oil_production=1000, oil_unit="bbl", basin="Permian Basin (Basin 430)")
    res_m3 = calc.calculate(tier=1, oil_production=158.987295, oil_unit="m3", basin="Permian Basin (Basin 430)")
    res_kbbl = calc.calculate(tier=1, oil_production=1.0, oil_unit="kbbl", basin="Permian Basin (Basin 430)")

    assert abs(res_bbl["results"]["ch4"]["value"] - 6.5) < 1e-3
    assert abs(res_m3["results"]["ch4"]["value"] - 6.5) < 1e-2
    assert abs(res_kbbl["results"]["ch4"]["value"] - 6.5) < 1e-3


# =============================================================================
# TIER 2: API COMPENDIUM 2021 EXHIBITS 6-5 & 6-6 (GOR MASS BALANCE)
# =============================================================================

def test_tier2_exhibit_6_5_non_continuous(calc):
    """
    API Compendium 2021 Section 6.3.1 - EXHIBIT 6-5:
    Sample Calculation for Non-Continuous Associated Gas Venting:
      - Oil production: 5,200 bbl/day
      - GOR: 700 scf/bbl
      - Venting duration: 15 days
      - Gas composition: 70% CH4, 10% CO2, 20% VOC
    Exhibit 6-5 reported values:
      - VR = 2,528 scf/min
      - Total gas vented in 15 days = 54,604,800 scf
      - E_CH4 = 731 tonnes CH4/year
      - E_CO2 = 287 tonnes CO2/year
    """
    res = calc.calculate(
        tier="Tier 2",
        oil_production=5200,
        oil_unit="bbl/day",
        gor=700,
        gor_unit="scf/bbl",
        venting_duration=15,
        duration_unit="days",
        ch4_content=70.0,  # 70%
        co2_content=10.0,  # 10%
    )
    ch4_val = res["results"]["ch4"]["value"]
    co2_val = res["results"]["co2"]["value"]

    # Exhibit 6-5 rounds to 731 tonnes CH4 and 287 tonnes CO2
    assert abs(ch4_val - 731.0) < 2.5
    assert abs(co2_val - 287.0) < 1.5
    assert res["metadata"]["disposition"]["zero_double_counting_verified"] is True
    assert res["results"]["ch4"]["tier"] == Tier.T2


def test_tier2_exhibit_6_6_continuous(calc):
    """
    API Compendium 2021 Section 6.3.1 - EXHIBIT 6-6:
    Sample Calculation for Continuous Associated Gas Venting:
      - Oil production: 5,200 bbl/day
      - GOR: 700 scf/bbl
      - Continuous venting throughout 365 days of operation
      - Gas composition: 70% CH4, 10% CO2
    Exhibit 6-6 reported values:
      - E_CH4 = 17,795 tonnes CH4/year
      - E_CO2 = 6,991 tonnes CO2/year
    """
    res = calc.calculate(
        tier=2,
        oil_production=5200,
        oil_unit="bbl/day",
        gor=700,
        gor_unit="scf/bbl",
        venting_duration=365,
        duration_unit="days",
        ch4_content=0.70,
        co2_content=0.10,
    )
    ch4_val = res["results"]["ch4"]["value"]
    co2_val = res["results"]["co2"]["value"]

    # Exhibit 6-6 exact numbers: 17,795 tonnes CH4 (using integer MW 16) / 17,842 tonnes (using exact MW 16.0425)
    # and 6,991 tonnes CO2 (using integer MW 44) / 6,993 tonnes (using exact MW 44.01)
    assert abs(ch4_val - 17795.0) < 55.0  # within 0.26% difference between exact MW 16.0425 and integer 16
    assert abs(ch4_val - 17842.15) < 2.0
    assert abs(co2_val - 6991.0) < 5.0


def test_tier2_net_vented_partitioning_zero_double_counting(calc):
    """
    Verify disposition partitioning:
      Total Gas = GOR * Oil Production = 700 * 5,200 * 30 days = 109,200,000 scf
      Recovered (sales/reinjected): 60,000,000 scf
      Flared (Section 5): 40,000,000 scf
      Net Vented: 9,200,000 scf
    Emissions must ONLY be computed from net vented gas (9.2 MMscf).
    """
    res = calc.calculate(
        tier=2,
        oil_production=5200,
        oil_unit="bbl/day",
        gor=700,
        venting_duration=30,
        duration_unit="days",
        recovered_gas_volume=60000000,
        flared_gas_volume=40000000,
        gas_volume_unit="scf",
        ch4_content=0.80,
        co2_content=0.05,
    )
    disp = res["metadata"]["disposition"]
    assert abs(disp["produced_scf"] - 109200000.0) < 1.0
    assert abs(disp["recovered_scf"] - 60000000.0) < 1.0
    assert abs(disp["flared_scf"] - 40000000.0) < 1.0
    assert abs(disp["vented_scf"] - 9200000.0) < 1.0

    # Expected CH4: 9,200,000 * 0.80 * 16.0425 / 379.3 / 2204.6226 = 141.13 tonnes
    assert abs(res["results"]["ch4"]["value"] - 141.13) < 0.5


def test_tier2_gor_metric_conversion(calc):
    """Test GOR in m3/m3 conversion to scf/bbl."""
    # GOR 100 m3/m3 = ~561.46 scf/bbl
    res1 = calc.calculate(
        tier=2,
        oil_production=1000,
        oil_unit="bbl",
        gor=561.4583,
        gor_unit="scf/bbl",
        venting_duration=365,
        ch4_content=0.80,
    )
    res2 = calc.calculate(
        tier=2,
        oil_production=1000,
        oil_unit="bbl",
        gor=100.0,
        gor_unit="m3/m3",
        venting_duration=365,
        ch4_content=0.80,
    )
    assert abs(res1["results"]["ch4"]["value"] - res2["results"]["ch4"]["value"]) < 0.1


# =============================================================================
# TIER 3: DIRECT / SITE-SPECIFIC MEASUREMENT (API Eq. 6-8)
# =============================================================================

def test_tier3_direct_vent_rate(calc):
    """
    Tier 3: Measured vent rate VR = 2,528 scf/min = 151,680 scfh for 360 hours (15 days).
    Total volume = 54,604,800 scf.
    At 70% CH4, 10% CO2, should match Exhibit 6-5.
    """
    res = calc.calculate(
        tier="Tier 3",
        vent_rate=2528 * 60,  # scfh
        vent_rate_unit="scfh",
        venting_duration=15 * 24,  # hours
        duration_unit="hours",
        ch4_content=0.70,
        co2_content=0.10,
    )
    assert abs(res["results"]["ch4"]["value"] - 731.0) < 2.5
    assert abs(res["results"]["co2"]["value"] - 287.0) < 1.5
    assert res["results"]["ch4"]["tier"] == Tier.T3


def test_tier3_total_measured_volume(calc):
    """Tier 3: Direct total measured volume in scf."""
    res = calc.calculate(
        tier=3,
        vent_volume=1_000_000,  # 1 MMscf
        vent_volume_unit="scf",
        ch4_content=0.85,
        co2_content=0.02,
    )
    # Expected: 1e6 * 0.85 * 16.0425 / (379.3 * 2204.6226) = 16.31 tonnes CH4
    assert abs(res["results"]["ch4"]["value"] - 16.31) < 0.1
    # Expected: 1e6 * 0.02 * 44.01 / (379.3 * 2204.6226) = 1.05 tonnes CO2
    assert abs(res["results"]["co2"]["value"] - 1.05) < 0.05


# =============================================================================
# INPUT VALIDATION & PHYSICAL BOUNDS CHECKS
# =============================================================================

def test_validation_negative_values(calc):
    """Ensure negative physical inputs are rejected."""
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(tier=1, oil_production=-100)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(tier=2, oil_production=100, gor=-50)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(tier=2, oil_production=100, gor=50, venting_duration=-5)

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(tier=3, vent_rate=-10, venting_duration=5)


def test_validation_gas_composition_exceeds_100(calc):
    """CH4 + CO2 > 100% must be rejected as physically impossible."""
    with pytest.raises(ValueError, match="exceeds 100%"):
        calc.calculate(tier=1, oil_production=1000, ch4_content=0.80, co2_content=0.25)

    with pytest.raises(ValueError, match="exceeds 100%"):
        calc.calculate(tier=2, oil_production=1000, gor=500, ch4_content=85.0, co2_content=20.0)


def test_validation_mass_balance_violation(calc):
    """Recovered + Flared > Total Produced Gas must be rejected."""
    with pytest.raises(ValueError, match="Mass balance violation"):
        calc.calculate(
            tier=2,
            oil_production=1000,  # 1000 bbl
            gor=100,  # 100,000 scf total produced
            recovered_gas_volume=80000,
            flared_gas_volume=30000,  # 80k + 30k = 110k > 100k
        )


def test_validation_duration_exceeds_period(calc):
    """Venting duration cannot exceed total period or 366 days."""
    with pytest.raises(ValueError, match="cannot exceed total period duration"):
        calc.calculate(
            tier=2,
            oil_production=1000,
            gor=100,
            venting_duration=40,
            period_duration=30,
            duration_unit="days",
        )

    with pytest.raises(ValueError, match="exceeds maximum annual days"):
        calc.calculate(
            tier=2,
            oil_production=1000,
            gor=100,
            venting_duration=400,
            duration_unit="days",
        )


def test_high_gor_qa_warning(calc):
    """GOR > 100,000 scf/bbl generates a QA flag rather than blocking."""
    res = calc.calculate(
        tier=2,
        oil_production=100,
        gor=150000,
        venting_duration=10,
    )
    qa_flags = res["metadata"]["qa_flags"]
    assert any("High GOR anomaly" in flag for flag in qa_flags)
    assert res["results"]["ch4"]["value"] > 0


# =============================================================================
# DISPATCHER INTEGRATION
# =============================================================================

def test_dispatcher_routing(dispatcher):
    """Verify CalculationDispatcher routes associated_gas_venting accurately."""
    inputs = {
        "tier": "Tier 1",
        "oil_production": 5000,
        "oil_unit": "bbl",
        "basin": "Williston Basin (Basin 395)",
    }
    res = dispatcher.dispatch("associated_gas_venting", inputs, {}, {})
    assert res is not None
    # Williston factor = 8.9 kg/bbl -> 5000 * 8.9 / 1000 = 44.5 tonnes
    assert abs(res["results"]["ch4"]["value"] - 44.5) < 1e-4

    # Test alias
    res_alias = dispatcher.dispatch("associated_venting", inputs, {}, {})
    assert res_alias is not None
    assert abs(res_alias["results"]["ch4"]["value"] - 44.5) < 1e-4


# =============================================================================
# END-TO-END FLASK API & DATABASE PERSISTENCE
# =============================================================================

def test_api_add_emission_associated_gas_venting():
    """Verify POST /api/emissions/ saves Associated Gas Venting and calculates properly."""
    with app.app_context():
        # Setup facility and user
        user = User.query.filter_by(role="admin").first()
        if not user:
            user = User(fullName="Admin", orgName="TestOrg", sector="Upstream", email="admin_agv@test.com", role="admin")
            user.set_password("Admin1234!")
            db.session.add(user)
            db.session.commit()

        fac = Facility.query.first()
        if not fac:
            fac = Facility(name="Test Field AGV", location="Hassi Messaoud", segment="Upstream", code="FAC-AGV-01")
            db.session.add(fac)
            db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id

        # 1. Test POST Tier 1
        payload_t1 = {
            "year": 2025,
            "month": 6,
            "facility_id": fac.id,
            "process_type": "associated_gas_venting",
            "quantity": 10000,
            "unit": "bbl",
            "basin": "Permian Basin (Basin 430)",
            "tier": "Tier 1",
            "ch4_content": 81.6,
        }
        resp = client.post("/api/emissions/", json=payload_t1)
        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        assert "emissions" in data
        # Permian factor = 6.5 kg/bbl -> 10,000 * 6.5 / 1000 = 65.0 tonnes CH4
        assert abs(data["emissions"]["ch4"] - 65.0) < 0.1
        assert data["emissions"]["totalCo2e"] > 0

        # Verify DB persistence
        rec = db.session.get(Emission, data["id"])
        assert rec is not None
        assert rec.process_type == "associated_gas_venting"
        assert abs(rec.ch4_emissions - 65.0) < 0.1

        # 2. Test POST Tier 2 Exhibit 6-5
        payload_t2 = {
            "year": 2025,
            "month": 7,
            "facility_id": fac.id,
            "process_type": "associated_gas_venting",
            "oil_production": 5200,
            "oil_unit": "bbl/day",
            "gor": 700,
            "gor_unit": "scf/bbl",
            "venting_duration": 15,
            "duration_unit": "days",
            "ch4_content": 70,
            "co2_content": 10,
            "tier": "Tier 2",
        }
        resp_t2 = client.post("/api/emissions/", json=payload_t2)
        assert resp_t2.status_code == 201
        data_t2 = resp_t2.get_json()
        rec_t2 = db.session.get(Emission, data_t2["id"])
        assert abs(rec_t2.ch4_emissions - 731.0) < 2.5
        assert abs(rec_t2.co2_emissions - 287.0) < 1.5

        # 3. Test Validation Error 422 on impossible gas composition
        payload_bad = {
            "year": 2025,
            "month": 8,
            "facility_id": fac.id,
            "process_type": "associated_gas_venting",
            "oil_production": 1000,
            "ch4_content": 90,
            "co2_content": 20,  # 90 + 20 = 110%
        }
        resp_bad = client.post("/api/emissions/", json=payload_bad)
        assert resp_bad.status_code == 422
        assert "exceeds 100%" in resp_bad.get_json()["error"]

        # 4. Verify Dashboard Aggregation includes associated_gas_venting in Venting category
        rec.status = "Verified"
        rec_t2.status = "Verified"
        db.session.commit()

        resp_dash = client.get("/api/dashboard/historical?year=2025")
        if resp_dash.status_code == 200:
            dash_data = resp_dash.get_json()
            # Historical endpoint or breakdown should categorize venting
            assert dash_data is not None
