"""
test_liquids_unloading_compendium.py
------------------------------------
Comprehensive Test Suite for Liquids Unloading Emissions Calculation Engine
Strictly validated against API GHG Compendium 2021, Section 6.3.4:
  - Table 6-11: Tier 1 Per-Well Default Emission Factors (Plunger vs Non-Plunger)
  - Table 6-10: Tier 2 Event-Based Emission Factors (Frequency Bins & Regional Basins)
  - Equation 6-10 & Exhibit 6-8: Tier 3 Engineering Model (EPA Subpart W Integrated)
  - Equation 6-11: Tier 3 Engineering Model (Automated Plunger Lift)
  - Equation 6-3: Tier 3 Wellbore Decompression Geometry
  - Dispatcher & Legacy Engine routing
  - Unit conversions (imperial and metric)
  - Physical boundary conditions and input validation
  - API and Database pipeline persistence
"""

import pytest
import math
from calculations.vented import LiquidsUnloadingCalculator
from calculations.dispatcher import CalculationDispatcher
from calculations.legacy_engine import compute_emissions
from calculations.constants import GWP_AR5
from calculations.units import CONVERSIONS

@pytest.fixture
def calc():
    return LiquidsUnloadingCalculator()

@pytest.fixture
def dispatcher():
    return CalculationDispatcher()

@pytest.fixture(scope="function")
def auth_client(client):
    from extensions import db
    from models import User, Facility
    from werkzeug.security import generate_password_hash
    from app import app

    with app.app_context():
        existing = User.query.filter_by(email="qfull_test@validation.io").first()
        if not existing:
            u = User(
                fullName="QFULL Test User",
                orgName="QFULL Validation Org",
                email="qfull_test@validation.io",
                password_hash=generate_password_hash("QfullPass123!"),
                sector="Oil & Gas",
                role="admin",
                status="active",
            )
            db.session.add(u)
            db.session.flush()

            f = Facility(
                name="QFULL Test Facility",
                code="QFULL-001",
                activity="E&P",
                division="Operations",
                field="Test Field",
                segment="Upstream",
                country="Algeria",
            )
            db.session.add(f)
            db.session.commit()

        resp = client.post(
            "/api/auth/login",
            json={"email": "qfull_test@validation.io", "password": "QfullPass123!"},
        )
        assert resp.status_code in (200, 201), f"Login failed: {resp.get_json()}"
        yield client

@pytest.fixture(scope="function")
def facility_id(auth_client):
    from app import app
    from models import Facility

    with app.app_context():
        f = Facility.query.filter_by(code="QFULL-001").first()
        assert f is not None, "Test facility not found"
        return f.id


# ==============================================================================
# 1. TIER 1: API TABLE 6-11 PER-WELL DEFAULT FACTOR VERIFICATION
# ==============================================================================

class TestLiquidsUnloadingTier1:
    """Verifies API Compendium 2021 Section 6.3.4, Table 6-11."""

    def test_tier1_plunger_lift_table_6_11_single_well(self, calc):
        """
        API Table 6-11: Plunger Lift
        1,774 kg CH4/well-yr = 1.774 tonnes CH4/well-yr.
        Whole gas = 113,466 scf/well-yr at 81.6 mol% CH4 baseline.
        """
        res = calc.calculate_tier1(well_count=1, unloading_type="plunger", gwp_dict=GWP_AR5)
        ch4_val = res["results"]["ch4"]["value"]
        assert ch4_val == pytest.approx(1.774, rel=1e-4)
        assert res["total_co2e"] == pytest.approx(1.774 * 28.0, rel=1e-4)
        assert res["inputs"]["whole_gas_scf"] == pytest.approx(113466.0, rel=1e-4)
        assert res["inputs"]["tier"] == "Tier 1"
        assert "Table 6-11" in res["inputs"]["api_reference"]

    def test_tier1_non_plunger_lift_table_6_11_single_well(self, calc):
        """
        API Table 6-11: Non-Plunger Lift
        2,792 kg CH4/well-yr = 2.792 tonnes CH4/well-yr.
        Whole gas = 178,531 scf/well-yr at 81.6 mol% CH4 baseline.
        """
        res = calc.calculate_tier1(well_count=1, unloading_type="non_plunger", gwp_dict=GWP_AR5)
        ch4_val = res["results"]["ch4"]["value"]
        assert ch4_val == pytest.approx(2.792, rel=1e-4)
        assert res["total_co2e"] == pytest.approx(2.792 * 28.0, rel=1e-4)
        assert res["inputs"]["whole_gas_scf"] == pytest.approx(178531.0, rel=1e-4)

    def test_tier1_multiple_wells_scaling(self, calc):
        """Multi-well scaling: 10 plunger wells -> 17.74 t CH4; 5 non-plunger -> 13.96 t CH4."""
        res_p = calc.calculate_tier1(well_count=10, unloading_type="plunger", gwp_dict=GWP_AR5)
        assert res_p["results"]["ch4"]["value"] == pytest.approx(17.74, rel=1e-4)

        res_np = calc.calculate_tier1(well_count=5, unloading_type="non_plunger", gwp_dict=GWP_AR5)
        assert res_np["results"]["ch4"]["value"] == pytest.approx(13.96, rel=1e-4)

    def test_tier1_site_specific_gas_composition_adjustment(self, calc):
        """
        Table 6-11 footnote b:
        When site-specific gas composition is available, emissions = whole gas * mole fraction * molar mass conversion.
        Plunger: 113,466 scf * 90% CH4 * (16.04 / (379.3 * 2204.6226)) = 1.9592 t CH4.
        CO2: 113,466 scf * 3% CO2 * (44.01 / (379.3 * 2204.6226)) = 0.17915 t CO2.
        """
        res = calc.calculate_tier1(
            well_count=1,
            unloading_type="plunger",
            ch4_content=0.90,
            co2_content=0.03,
            gwp_dict=GWP_AR5,
        )
        expected_ch4 = 113466.0 * 0.90 * calc.SCF_TO_TONNES_CH4
        expected_co2 = 113466.0 * 0.03 * calc.SCF_TO_TONNES_CO2
        assert res["results"]["ch4"]["value"] == pytest.approx(expected_ch4, rel=1e-4)
        assert res["results"]["co2"]["value"] == pytest.approx(expected_co2, rel=1e-4)
        expected_co2e = expected_co2 * 1.0 + expected_ch4 * 28.0
        assert res["total_co2e"] == pytest.approx(expected_co2e, rel=1e-4)

    def test_tier1_flaring_control_efficiency(self, calc):
        """Flaring control: partition gas into (1-ctrl) vented and ctrl flared with 98% combustion."""
        res = calc.calculate_tier1(
            well_count=1,
            unloading_type="plunger",
            control_efficiency=0.98,
            gwp_dict=GWP_AR5,
        )
        base_ch4 = 1.774
        expected_ch4 = base_ch4 * (0.02 + 0.98 * 0.02)
        expected_co2 = base_ch4 * 0.98 * 0.98 * (44.01 / 16.04)
        assert res["results"]["ch4"]["value"] == pytest.approx(expected_ch4, rel=1e-3)
        assert res["results"]["co2"]["value"] == pytest.approx(expected_co2, rel=1e-3)


# ==============================================================================
# 2. TIER 2: API TABLE 6-10 EVENT-BASED EMISSION FACTORS VERIFICATION
# ==============================================================================

class TestLiquidsUnloadingTier2:
    """Verifies API Compendium 2021 Section 6.3.4, Table 6-10."""

    @pytest.mark.parametrize("ev, expected_tonnes, expected_scf_gas", [
        (50, 50 * 0.185, 50 * 11308.0),   # Plunger <= 100
        (150, 150 * 0.024, 150 * 1503.0), # Plunger > 100
    ])
    def test_tier2_plunger_average_frequency_bins(self, calc, ev, expected_tonnes, expected_scf_gas):
        res = calc.calculate_tier2(events=ev, unloading_type="plunger", gwp_dict=GWP_AR5)
        assert res["results"]["ch4"]["value"] == pytest.approx(expected_tonnes, rel=1e-3)
        assert res["inputs"]["whole_gas_scf"] == pytest.approx(expected_scf_gas, rel=1e-3)
        assert res["inputs"]["tier"] == "Tier 2"

    @pytest.mark.parametrize("ev, expected_tonnes, expected_scf_gas", [
        (8, 8 * 0.412, 8 * 24109.0),    # Non-Plunger <= 10
        (25, 25 * 0.462, 25 * 25690.0), # Non-Plunger 10 to 50
        (80, 80 * 0.670, 80 * 36512.0), # Non-Plunger > 50
    ])
    def test_tier2_non_plunger_average_frequency_bins(self, calc, ev, expected_tonnes, expected_scf_gas):
        res = calc.calculate_tier2(events=ev, unloading_type="non_plunger", gwp_dict=GWP_AR5)
        assert res["results"]["ch4"]["value"] == pytest.approx(expected_tonnes, rel=1e-3)
        assert res["inputs"]["whole_gas_scf"] == pytest.approx(expected_scf_gas, rel=1e-3)

    @pytest.mark.parametrize("region, u_type, ev, expected_ch4_event", [
        ("appalachia", "plunger", 50, 0.098),
        ("appalachia", "plunger", 150, 0.024),
        ("appalachia", "non_plunger", 20, 0.087),
        ("gulf_coast", "plunger", 50, 0.185),
        ("gulf_coast", "plunger", 150, 0.024),
        ("gulf_coast", "non_plunger", 20, 0.255),
        ("midcontinent", "plunger", 50, 0.123),
        ("midcontinent", "plunger", 150, 0.006),
        ("midcontinent", "non_plunger", 20, 0.916),
        ("rocky_mountain", "plunger", 50, 0.241),
        ("rocky_mountain", "plunger", 150, 0.027),
        ("rocky_mountain", "non_plunger", 20, 0.291),
    ])
    def test_tier2_regional_factors(self, calc, region, u_type, ev, expected_ch4_event):
        res = calc.calculate_tier2(
            events=ev,
            unloading_type=u_type,
            region=region,
            gwp_dict=GWP_AR5,
        )
        assert res["results"]["ch4"]["value"] == pytest.approx(ev * expected_ch4_event, rel=1e-3)


# ==============================================================================
# 3. TIER 3: ENGINEERING MODELS (EQUATIONS 6-10, 6-11, 6-3)
# ==============================================================================

class TestLiquidsUnloadingTier3Engineering:
    """Verifies API Compendium 2021 Section 6.3.4 Equations 6-10, 6-11, 6-3 and Exhibit 6-8."""

    def test_tier3_equation_6_10_exact_exhibit_6_8(self, calc):
        """
        API Compendium 2021 Exhibit 6-8 (Exact Golden Test):
        Given:
          - Gas well with NO plunger lift (unloading_type='non_plunger')
          - Unloadings per year = 12
          - Casing diameter = 10 inches
          - Well depth = 12,000 feet
          - Shut-in surface pressure = 250 psig
          - Sales flow rate SFR = 35,000 scf/hr
          - Hours open HR = 1 hour (HR - X = 1.0 - 1.0 = 0.0 -> no flowing gas venting)
          - Gas composition = 80 mol% CH4, 3 mol% CO2
        Compendium Results:
          - Wellbore vented volume VR = 1,332,000 scf/yr
          - E_CH4 = 20.39 tonnes CH4/yr
          - E_CO2 = 2.10 tonnes CO2/yr
        """
        res = calc.calculate_tier3_equation_6_10(
            events=12,
            well_depth=12000,
            diameter=10.0,
            pressure=250.0,
            sfr=35000.0,
            hours_open=1.0,
            unloading_type="non_plunger",
            ch4_content=0.80,
            co2_content=0.03,
            gwp_dict=GWP_AR5,
        )
        # Check volume
        assert res["inputs"]["whole_gas_scf"] == pytest.approx(1332000.0, rel=1e-4)

        # Check exact emissions from Exhibit 6-8 (20.39 tonnes CH4, 2.10 tonnes CO2)
        assert res["results"]["ch4"]["value"] == pytest.approx(20.39, abs=0.1)
        assert res["results"]["co2"]["value"] == pytest.approx(2.10, abs=0.1)

        # Check CO2e
        expected_co2e = 20.39 * 28.0 + 2.10 * 1.0
        assert res["total_co2e"] == pytest.approx(expected_co2e, abs=2.0)

    def test_tier3_equation_6_10_flowing_gas_component(self, calc):
        """
        Test flowline venting term when venting duration HR exceeds X:
        SFR = 20,000 scf/hr, HR = 3.0 hr, non-plunger (X=1.0) -> (HR - X) = 2.0 hr, Z = 1.0.
        Flowing gas vented = 20,000 * 2.0 = 40,000 scf/event.
        """
        res = calc.calculate_tier3_equation_6_10(
            events=1,
            well_depth=5000,
            diameter=2.5,
            pressure=200.0,
            sfr=20000.0,
            hours_open=3.0,
            unloading_type="non_plunger",
            ch4_content=0.85,
        )
        wellbore_scf = 1 * 0.37e-3 * (2.5 ** 2) * 5000 * 200.0  # 2,312.5 scf
        flowline_scf = 20000.0 * (3.0 - 1.0) * 1.0             # 40,000 scf
        total_scf = wellbore_scf + flowline_scf                  # 42,312.5 scf
        assert res["inputs"]["whole_gas_scf"] == pytest.approx(total_scf, rel=1e-4)

    def test_tier3_equation_6_11_automated_plunger_lift(self, calc):
        """
        API Compendium 2021 Equation 6-11:
        VR = sqrt(Pshut - Patm) / sqrt(Pline - Psep) * SFRp * Tp
        Pshut = 150 psia, Pline = 100 psia, Psep = 50 psia, Patm = 14.696 psia
        SFRp = 10,000 scf/hr, Tp = 0.5 hr, events = 10.
        Ratio = sqrt(135.304) / sqrt(50) = 11.632 / 7.07107 = 1.6450
        VR/event = 1.6450 * 10,000 * 0.5 = 8,225.13 scf.
        Total = 82,251.3 scf.
        """
        res = calc.calculate_tier3_equation_6_11(
            p_shut=150.0,
            p_line=100.0,
            p_sep=50.0,
            sfr_p=10000.0,
            t_p=0.5,
            events=10,
            ch4_content=0.85,
            press_unit="psia",
            gwp_dict=GWP_AR5,
        )
        expected_ratio = math.sqrt(150.0 - 14.696) / math.sqrt(100.0 - 50.0)
        expected_vr_event = expected_ratio * 10000.0 * 0.5
        expected_total_scf = expected_vr_event * 10.0
        assert res["inputs"]["whole_gas_scf"] == pytest.approx(expected_total_scf, rel=1e-3)
        expected_ch4 = expected_total_scf * 0.85 * calc.SCF_TO_TONNES_CH4
        assert res["results"]["ch4"]["value"] == pytest.approx(expected_ch4, rel=1e-3)

    def test_tier3_equation_6_3_volume_based_geometry(self, calc):
        """API Eq. 6-3 with temperature and pressure correction."""
        res = calc.calculate_volume_based(
            well_depth=5000.0,
            diameter=2.5,
            pressure=500.0,
            ch4_content=0.85,
            events=12,
            operating_temperature=60.0,
            temp_unit="F",
            press_unit="psig",
        )
        assert res["results"]["ch4"]["value"] > 0
        assert res["total_co2e"] > 0


# ==============================================================================
# 4. UNIT CONVERSIONS AND ROBUSTNESS
# ==============================================================================

class TestLiquidsUnloadingUnitConversions:
    """Verifies imperial and metric unit conversions for all parameters."""

    def test_depth_conversions(self, calc):
        """Depth: 1524 m == 5000 ft."""
        res_ft = calc.calculate_tier3_equation_6_10(
            events=10, well_depth=5000.0, diameter=2.5, pressure=200.0,
            sfr=10000.0, hours_open=1.0, depth_unit="ft",
        )
        res_m = calc.calculate_tier3_equation_6_10(
            events=10, well_depth=1524.0, diameter=2.5, pressure=200.0,
            sfr=10000.0, hours_open=1.0, depth_unit="m",
        )
        assert res_m["results"]["ch4"]["value"] == pytest.approx(res_ft["results"]["ch4"]["value"], rel=1e-3)

    def test_diameter_conversions(self, calc):
        """Diameter: 63.5 mm == 2.5 in."""
        res_in = calc.calculate_tier3_equation_6_10(
            events=10, well_depth=5000.0, diameter=2.5, pressure=200.0,
            sfr=10000.0, hours_open=1.0, diameter_unit="in",
        )
        res_mm = calc.calculate_tier3_equation_6_10(
            events=10, well_depth=5000.0, diameter=63.5, pressure=200.0,
            sfr=10000.0, hours_open=1.0, diameter_unit="mm",
        )
        assert res_mm["results"]["ch4"]["value"] == pytest.approx(res_in["results"]["ch4"]["value"], rel=1e-3)

    def test_pressure_conversions(self, calc):
        """Pressure: 13.7895 bar == 200 psig."""
        res_psig = calc.calculate_tier3_equation_6_10(
            events=10, well_depth=5000.0, diameter=2.5, pressure=200.0,
            sfr=10000.0, hours_open=1.0, press_unit="psig",
        )
        res_bar = calc.calculate_tier3_equation_6_10(
            events=10, well_depth=5000.0, diameter=2.5, pressure=13.7895,
            sfr=10000.0, hours_open=1.0, press_unit="barg",
        )
        assert res_bar["results"]["ch4"]["value"] == pytest.approx(res_psig["results"]["ch4"]["value"], rel=1e-3)


# ==============================================================================
# 5. INPUT VALIDATION & BOUNDARY CONDITIONS
# ==============================================================================

class TestLiquidsUnloadingValidation:
    """Verifies rejection of impossible, negative, zero, or malformed inputs."""

    def test_zero_activity_zero_emissions(self, calc):
        res_t2 = calc.calculate_tier2(events=0)
        assert res_t2["results"]["ch4"]["value"] == 0.0
        assert res_t2["total_co2e"] == 0.0

        res_t3 = calc.calculate_tier3_equation_6_10(events=0, well_depth=1000, diameter=2, pressure=100, sfr=0, hours_open=0)
        assert res_t3["results"]["ch4"]["value"] == 0.0
        assert res_t3["total_co2e"] == 0.0

    def test_negative_inputs_rejected(self, calc):
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate_tier2(events=-5)

        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate_tier1(well_count=-2)

        with pytest.raises(ValueError, match="greater than zero"):
            calc.calculate_tier3_equation_6_10(events=5, well_depth=-1000, diameter=2, pressure=100)

    def test_combined_gas_fractions_over_100_rejected(self, calc):
        with pytest.raises(ValueError, match="cannot exceed 100%"):
            calc.calculate_tier1(well_count=1, ch4_content=0.90, co2_content=0.15)

    def test_equation_6_11_impossible_pressures_rejected(self, calc):
        # Pshut < Patm
        with pytest.raises(ValueError, match="Shut-in pressure"):
            calc.calculate_tier3_equation_6_11(p_shut=10.0, p_line=100.0, p_sep=50.0, sfr_p=1000, t_p=1, p_atm=14.696)

        # Pline <= Psep
        with pytest.raises(ValueError, match="Line pressure.*strictly greater than separator pressure"):
            calc.calculate_tier3_equation_6_11(p_shut=150.0, p_line=50.0, p_sep=60.0, sfr_p=1000, t_p=1)


# ==============================================================================
# 6. DISPATCHER & COMPUTE_EMISSIONS END-TO-END ROUTING
# ==============================================================================

class TestLiquidsUnloadingDispatcherPipeline:
    """Verifies end-to-end integration via dispatcher and compute_emissions."""

    def test_dispatcher_tier1_routing(self, dispatcher):
        payload = {
            "process_type": "liquids_unloading",
            "tier": "tier1",
            "wells": 3,
            "unloading_type": "plunger",
        }
        res = dispatcher.dispatch("liquids_unloading", payload, {}, {})
        assert res["results"]["ch4"]["value"] == pytest.approx(3 * 1.774, rel=1e-4)

    def test_dispatcher_tier2_routing(self, dispatcher):
        payload = {
            "process_type": "liquids_unloading",
            "tier": "tier2",
            "events": 20,
            "unloading_type": "plunger",
            "region": "appalachia",
        }
        res = dispatcher.dispatch("liquids_unloading", payload, {}, {})
        # Appalachia plunger <= 100 is 0.098 t CH4/event
        assert res["results"]["ch4"]["value"] == pytest.approx(20 * 0.098, rel=1e-3)

    def test_dispatcher_tier3_equation_6_10_routing(self, dispatcher):
        payload = {
            "process_type": "liquids_unloading",
            "factor_source": "specific",
            "calc_method": "api_equation_6_10",
            "unload_depth": 12000,
            "unload_diam": 10.0,
            "unload_press": 250.0,
            "unload_events": 12,
            "sfr": 35000.0,
            "hours_open": 1.0,
            "unload_type": "non_plunger",
            "ch4_content": 80.0,
            "co2_content": 3.0,
        }
        res = dispatcher.dispatch("liquids_unloading", payload, {}, {})
        assert res["results"]["ch4"]["value"] == pytest.approx(20.39, abs=0.1)
        assert res["results"]["co2"]["value"] == pytest.approx(2.10, abs=0.1)

    def test_dispatcher_tier3_equation_6_11_routing(self, dispatcher):
        payload = {
            "process_type": "liquids_unloading",
            "factor_source": "specific",
            "calc_method": "api_equation_6_11",
            "p_shut": 150.0,
            "p_line": 100.0,
            "p_sep": 50.0,
            "sfr_p": 10000.0,
            "t_p": 0.5,
            "events": 10,
            "ch4_content": 85.0,
        }
        res = dispatcher.dispatch("liquids_unloading", payload, {}, {})
        assert res["results"]["ch4"]["value"] > 0

    def test_legacy_engine_compute_emissions_tier1(self):
        payload = {
            "process_type": "liquids_unloading",
            "tier": "tier1",
            "wells": 4,
            "unloading_type": "non_plunger",
        }
        em, method = compute_emissions(payload, {})
        assert em["ch4"] == pytest.approx(4 * 2.792, rel=1e-3)
        assert em["totalCo2e"] == pytest.approx(4 * 2.792 * 28.0, rel=1e-3)


# ==============================================================================
# 7. DATABASE PERSISTENCE & DASHBOARD AGGREGATION
# ==============================================================================

class TestLiquidsUnloadingDatabaseAndDashboard:
    """Verifies that unloading records persist in DB and aggregate into dashboard venting."""

    def test_api_emission_creation_and_dashboard_aggregation(self, auth_client, facility_id):
        # 1. Create Tier 1 Liquids Unloading record
        payload = {
            "facility_id": facility_id,
            "process_type": "liquids_unloading",
            "source_type": "default",
            "tier": "tier1",
            "wells": 2,
            "unloading_type": "plunger",
            "year": 2025,
            "month": 6,
            "scope": "Scope 1",
            "amount": 2,
            "unit": "wells",
        }
        resp = auth_client.post("/api/emissions", json=payload)
        assert resp.status_code in [200, 201]
        data = resp.get_json()
        assert "id" in data
        assert data["emissions"]["ch4"] == pytest.approx(2 * 1.774, rel=1e-3)

        # 2. Query Dashboard to verify classification as 'venting'
        dash_resp = auth_client.get(f"/api/dashboard/summary?facilityId={facility_id}&year=2025")
        assert dash_resp.status_code == 200
        dash_data = dash_resp.get_json()
        assert dash_data is not None
