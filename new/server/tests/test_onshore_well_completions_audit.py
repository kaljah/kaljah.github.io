"""
Comprehensive Regression and Validation Test Suite for Onshore Well Completions.
Audits the complete pipeline against API GHG Compendium 2021 §6.2.3 and Tables 6-5 and 6-6.

Covers:
- Tier 1: API Tables 6-5 & 6-6 default emission factor calculations (Oil vs Gas, HF vs Non-HF, Vented vs REC, composition scaling)
- Tier 2: Engineering calculations (API Eq. 6-7 prod rate x duration, Liquid x GOR, Rate x Duration with unit conversions)
- Tier 3: Direct/measured flowback (API Eq. 6-4 N2 deduction, Eq. 6-5 initial unmetered flowback, Exhibit 6-3 exact match, fate partitioning)
- Input validation (rejection of negative, impossible, or malformed inputs)
- Prevention of double counting between venting, flaring, and recovery
"""
import pytest
import math
import json
from calculations.vented import CompletionFlowbackCalculator
from calculations.constants import GWP_AR5
from calculations.dispatcher import dispatcher
from calculations.legacy_engine import compute_emissions
from emission_factors import API_FACTORS


class TestOnshoreCompletionsTier1:
    """Verifies API Compendium 2021 Tables 6-5 & 6-6 default factor calculations."""

    @pytest.fixture
    def calc(self):
        return CompletionFlowbackCalculator()

    # --- TABLE 6-5: WITH HYDRAULIC FRACTURING ---

    def test_table_6_5_gas_well_uncontrolled(self, calc):
        """API Table 6-5: Gas Well with HF - Uncontrolled Venting = 28.8 t CH4/completion."""
        res = calc.calculate(
            tier="tier1",
            well_type="gas",
            fracturing=True,
            control_type="uncontrolled",
            events=1.0,
            gwp_dict=GWP_AR5,
        )
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 28.8
        assert pytest.approx(res["results"]["co2"]["value"], abs=1e-5) == 0.0
        assert pytest.approx(res["total_co2e"], rel=1e-4) == 28.8 * 28.0
        assert "Table 6-5" in res["metadata"]["standard"]

    def test_table_6_5_gas_well_rec(self, calc):
        """API Table 6-5: Gas Well with HF - REC with Venting = 13.542 t CH4/completion."""
        res = calc.calculate(
            tier="tier1",
            well_type="gas",
            fracturing=True,
            control_type="rec",
            events=1.0,
            gwp_dict=GWP_AR5,
        )
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 13.542
        assert pytest.approx(res["total_co2e"], rel=1e-4) == 13.542 * 28.0

    def test_table_6_5_oil_well_uncontrolled(self, calc):
        """API Table 6-5: Oil Well with HF - Uncontrolled Venting = 14.419 t CH4/completion."""
        res = calc.calculate(
            tier="tier1",
            well_type="oil",
            fracturing=True,
            control_type="uncontrolled",
            events=1.0,
            gwp_dict=GWP_AR5,
        )
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 14.419
        assert pytest.approx(res["total_co2e"], rel=1e-4) == 14.419 * 28.0

    def test_table_6_5_oil_well_rec(self, calc):
        """API Table 6-5: Oil Well with HF - REC with Venting = 0.615 t CH4/completion."""
        res = calc.calculate(
            tier="tier1",
            well_type="oil",
            fracturing=True,
            control_type="rec",
            events=1.0,
            gwp_dict=GWP_AR5,
        )
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 0.615
        assert pytest.approx(res["total_co2e"], rel=1e-4) == 0.615 * 28.0

    # --- TABLE 6-6: WITHOUT HYDRAULIC FRACTURING ---

    def test_table_6_6_gas_well_vented(self, calc):
        """API Table 6-6: Onshore Gas Well without HF - Vented = 1.7376 t CH4/completion."""
        res = calc.calculate(
            tier="tier1",
            well_type="gas",
            fracturing=False,
            events=1.0,
            gwp_dict=GWP_AR5,
        )
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 1.7376
        assert pytest.approx(res["total_co2e"], rel=1e-4) == 1.7376 * 28.0
        assert "Table 6-6" in res["metadata"]["standard"]

    def test_table_6_6_oil_well_vented(self, calc):
        """API Table 6-6: Onshore Oil Well without HF - Vented = 0.0141 t CH4/completion."""
        res = calc.calculate(
            tier="tier1",
            well_type="oil",
            fracturing=False,
            events=1.0,
            gwp_dict=GWP_AR5,
        )
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 0.0141
        assert pytest.approx(res["total_co2e"], rel=1e-4) == 0.0141 * 28.0

    def test_tier1_multi_event_scaling(self, calc):
        """Tier 1: Multi-event scaling (e.g. 5 completions)."""
        res = calc.calculate(
            tier="tier1",
            well_type="gas",
            fracturing=True,
            control_type="uncontrolled",
            events=5.0,
            gwp_dict=GWP_AR5,
        )
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 28.8 * 5.0
        assert pytest.approx(res["total_co2e"], rel=1e-4) == 28.8 * 5.0 * 28.0

    def test_table_6_5_footnote_c_ch4_adjustment(self, calc):
        """API Table 6-5 Footnote c: Gas CH4 content adjustment (relative to 81.6% base)."""
        # If CH4 content is 90%, CH4 scales by (0.90 / 0.816)
        res = calc.calculate(
            tier="tier1",
            well_type="gas",
            fracturing=True,
            control_type="uncontrolled",
            events=1.0,
            ch4_content=0.90,
            gwp_dict=GWP_AR5,
        )
        expected_ch4 = 28.8 * (0.90 / 0.816)
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == expected_ch4

    def test_table_6_5_footnote_c_co2_adjustment(self, calc):
        """API Table 6-5 Footnote c: Gas CO2 estimation based on relative concentrations."""
        # CH4 = 85%, CO2 = 5%
        # CO2 = CH4 * (0.05 / 0.85) * (44.01 / 16.04)
        ch4_frac = 0.85
        co2_frac = 0.05
        res = calc.calculate(
            tier="tier1",
            well_type="gas",
            fracturing=True,
            control_type="uncontrolled",
            events=1.0,
            ch4_content=ch4_frac,
            co2_content=co2_frac,
            gwp_dict=GWP_AR5,
        )
        expected_ch4 = 28.8 * (ch4_frac / 0.816)
        expected_co2 = expected_ch4 * (co2_frac / ch4_frac) * (44.01 / 16.04)
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == expected_ch4
        assert pytest.approx(res["results"]["co2"]["value"], rel=1e-4) == expected_co2
        assert pytest.approx(res["total_co2e"], rel=1e-4) == (expected_co2 * 1.0) + (expected_ch4 * 28.0)


class TestOnshoreCompletionsTier2:
    """Verifies Tier 2 API Engineering calculations using site-specific operational data."""

    @pytest.fixture
    def calc(self):
        return CompletionFlowbackCalculator()

    def test_api_eq_6_7_production_rate_duration(self, calc):
        """API Eq. 6-7: Non-HF completion V_CC = V_Pi * T (daily production rate * vent duration)."""
        # Gas well without HF: initial prod rate = 100 Mcf/day for 2.5 days (60 hrs)
        # Net whole gas = 250 Mcf = 250,000 scf = 7,079.21 m3
        # CH4 = 85%, CO2 = 2%
        res = calc.calculate(
            tier="tier2",
            calculation_method="production_rate_duration",
            daily_production_rate=100.0,
            prod_rate_unit="mcf/day",
            vent_duration_hours=60.0,
            ch4_content=0.85,
            co2_content=0.02,
            events=1.0,
            gwp_dict=GWP_AR5,
        )
        vol_m3 = (100.0 * (60.0 / 24.0)) * 28.316846592
        expected_ch4 = (vol_m3 * 0.85 * 0.6785) / 1000.0
        expected_co2 = (vol_m3 * 0.02 * 1.861) / 1000.0
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == expected_ch4
        assert pytest.approx(res["results"]["co2"]["value"], rel=1e-4) == expected_co2
        assert "Equation 6-7" in res["metadata"]["standard"]

    def test_liquid_flowback_gor_with_sales_deduction(self, calc):
        """Tier 2: Liquid flowback * GOR minus sales gas."""
        bbl = 2000.0
        gor = 1200.0  # scf/bbl
        sales_scf = 400000.0  # scf sent to sales
        # Net gross gas = 2000 * 1200 - 400000 = 2,000,000 scf = 56,633.69 m3
        res = calc.calculate(
            tier="tier2",
            calculation_method="gor",
            liquid_flowback_bbl=bbl,
            gas_oil_ratio=gor,
            gas_produced_sales_scf=sales_scf,
            ch4_content=0.80,
            co2_content=0.03,
            events=1.0,
            gwp_dict=GWP_AR5,
        )
        vol_scf = 2000.0 * 1200.0 - 400000.0
        vol_m3 = vol_scf * 0.028316846592
        expected_ch4 = (vol_m3 * 0.80 * 0.6785) / 1000.0
        expected_co2 = (vol_m3 * 0.03 * 1.861) / 1000.0
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == expected_ch4
        assert pytest.approx(res["results"]["co2"]["value"], rel=1e-4) == expected_co2

    def test_flowback_rate_duration_mcf_hr_correctness(self, calc):
        """Tier 2: Flowback Rate (Mcf/hr) * Duration (hr) without 24x divisor error."""
        rate_mcf_hr = 0.5  # 500 scf/hr
        duration_hr = 24.0
        # Volume = 0.5 * 24 = 12 Mcf = 12,000 scf = 339.80 m3
        res = calc.calculate(
            tier="tier2",
            calculation_method="rate_duration",
            flowback_rate=rate_mcf_hr,
            rate_unit="mcf/hr",
            flowback_duration_hours=duration_hr,
            ch4_content=0.85,
            gwp_dict=GWP_AR5,
        )
        vol_m3 = 12.0 * 28.316846592
        expected_ch4 = (vol_m3 * 0.85 * 0.6785) / 1000.0
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == expected_ch4


class TestOnshoreCompletionsTier3:
    """Verifies Tier 3 direct measurement, API Eq. 6-4, Eq. 6-5, Exhibit 6-3, and gas fate."""

    @pytest.fixture
    def calc(self):
        return CompletionFlowbackCalculator()

    def test_api_eq_6_4_injected_n2_deduction(self, calc):
        """API Eq. 6-4: Net gas V_gas = V_t - EnF (injected N2 deduction)."""
        v_t_scf = 1_000_000.0
        n2_scf = 50_000.0
        # Net gas = 950,000 scf
        res = calc.calculate(
            tier="tier3",
            flowback_volume=v_t_scf,
            volume_unit="scf",
            injected_n2_volume=n2_scf,
            injected_n2_unit="scf",
            ch4_content=0.80,
            gwp_dict=GWP_AR5,
        )
        vol_m3 = 950_000.0 * 0.028316846592
        expected_ch4 = (vol_m3 * 0.80 * 0.6785) / 1000.0
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == expected_ch4
        assert res["inputs"]["net_flowback_scf"] == 950_000.0

    def test_injected_co2_not_deducted(self, calc):
        """API §6.2.3.1: Injected CO2 does NOT deduct from metered gas (EnF = 0)."""
        v_t_scf = 1_000_000.0
        res = calc.calculate(
            tier="tier3",
            flowback_volume=v_t_scf,
            volume_unit="scf",
            injected_gas_type="co2",
            injected_n2_volume=50_000.0,  # Should be ignored because gas type is co2
            ch4_content=0.80,
            gwp_dict=GWP_AR5,
        )
        vol_m3 = 1_000_000.0 * 0.028316846592
        expected_ch4 = (vol_m3 * 0.80 * 0.6785) / 1000.0
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == expected_ch4

    def test_api_exhibit_6_3_exact_benchmark(self, calc):
        """
        API Compendium 2021 EXHIBIT 6-3 Exact Verification:
        - Gas well with HF
        - V_t = 1,480,000 scf metered gas to flare
        - Injected N2 = 7,390 scf
        - Metered duration T_m = 20 hours
        - Initial flowback duration T_i = 4 hours (vented to open pits/tanks)
        - Gas composition: 70 mole % CH4
        - Flare efficiency: 98%
        API Published Results:
        - V_gas = 1,472,610 scf
        - V_i = 147,261 scf
        - Initial vented CH4 = 1.97 tonnes CH4
        - Flared unburnt CH4 = 0.39 tonnes CH4
        - Flared combustion CO2 (from CH4) = 53.5 tonnes CO2 (or 98.7 t if remaining 30% ethane combusted)
        """
        res = calc.calculate(
            tier="tier3",
            flowback_volume=1_480_000.0,
            volume_unit="scf",
            injected_n2_volume=7_390.0,
            injected_n2_unit="scf",
            flowback_duration_hours=20.0,
            initial_flowback_hours=4.0,
            ch4_content=0.70,
            disposition="flared",
            control_efficiency=0.98,
            hhv=1020.0,
            gwp_dict=GWP_AR5,
        )
        assert pytest.approx(res["inputs"]["net_flowback_scf"], rel=1e-5) == 1_472_610.0
        assert pytest.approx(res["inputs"]["initial_flowback_scf"], rel=1e-4) == 147_261.0
        # Initial vented CH4: ~1.97 tonnes (1.98 t using NIST density)
        assert pytest.approx(res["inputs"]["initial_vented_ch4_tonnes"], abs=0.02) == 1.97
        # Flared unburnt CH4: ~0.39 tonnes
        assert pytest.approx(res["inputs"]["flared_unburnt_ch4_tonnes"], abs=0.01) == 0.39
        # Total CH4 = 1.97 + 0.39 = 2.36 tonnes
        assert pytest.approx(res["results"]["ch4"]["value"], abs=0.02) == 2.37

    def test_gas_fate_partitioning_rec_zero_emissions(self, calc):
        """Tier 3: Recovered to sales line (REC) produces zero emissions for separated gas."""
        res = calc.calculate(
            tier="tier3",
            flowback_volume=100_000.0,
            volume_unit="m3",
            ch4_content=0.85,
            disposition="rec",
            gwp_dict=GWP_AR5,
        )
        # 100% recovered to sales -> 0 emissions
        assert pytest.approx(res["results"]["ch4"]["value"], abs=1e-6) == 0.0
        assert pytest.approx(res["results"]["co2"]["value"], abs=1e-6) == 0.0
        assert pytest.approx(res["total_co2e"], abs=1e-6) == 0.0

    def test_gas_fate_custom_split(self, calc):
        """Tier 3: Custom split between Vented (10%), Flared (60%), and Recovered REC (30%)."""
        v_m3 = 10_000.0
        res = calc.calculate(
            tier="tier3",
            flowback_volume=v_m3,
            volume_unit="m3",
            ch4_content=0.80,
            disposition="split",
            frac_vented=0.10,
            frac_flared=0.60,
            frac_recovered=0.30,
            control_efficiency=0.98,
            gwp_dict=GWP_AR5,
        )
        # Vented: 1000 m3 -> 1000 * 0.80 * 0.6785 / 1000 = 0.5428 t CH4
        # Flared unburnt: 6000 m3 -> 6000 * 0.80 * 0.6785 * 0.02 / 1000 = 0.065136 t CH4
        # Flared CO2: 6000 * 0.80 * 0.6785 * 0.98 * (44.01 / 16.04) / 1000 = 8.756 t CO2
        # Recovered: 3000 m3 -> 0 t
        expected_ch4 = 0.5428 + 0.065136
        expected_co2 = (6000.0 * 0.80 * 0.6785 * 0.98 * (44.01 / 16.04)) / 1000.0
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-3) == expected_ch4
        assert pytest.approx(res["results"]["co2"]["value"], rel=1e-3) == expected_co2


class TestOnshoreCompletionsValidation:
    """Verifies robust validation for negative, impossible, and malformed inputs."""

    @pytest.fixture
    def calc(self):
        return CompletionFlowbackCalculator()

    def test_rejects_negative_volume(self, calc):
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate(tier="tier3", flowback_volume=-500.0)

    def test_rejects_negative_events(self, calc):
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate(tier="tier1", events=-1.0)

    def test_rejects_negative_duration(self, calc):
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate(tier="tier2", calculation_method="rate_duration", flowback_rate=1.0, flowback_duration_hours=-10.0)

    def test_rejects_invalid_ch4_content(self, calc):
        with pytest.raises(ValueError, match="Methane.*between 0 and 1"):
            calc.calculate(tier="tier3", flowback_volume=100.0, ch4_content=150.0)
        with pytest.raises(ValueError, match="cannot be negative"):
            calc.calculate(tier="tier3", flowback_volume=100.0, ch4_content=-0.1)

    def test_rejects_invalid_disposition_split_sum(self, calc):
        with pytest.raises(ValueError, match="Disposition.*must sum to 100%"):
            calc.calculate(
                tier="tier3",
                flowback_volume=100.0,
                disposition="split",
                frac_vented=0.50,
                frac_flared=0.60,
                frac_recovered=0.20,  # Sum = 1.3 != 1.0
            )

    def test_zero_volume_clean_zero_emissions(self, calc):
        res = calc.calculate(flowback_volume=0.0, ch4_content=0.85, gwp_dict=GWP_AR5)
        assert res["total_co2e"] == 0.0
        assert res["results"]["ch4"]["value"] == 0.0


class TestOnshoreCompletionsEndToEndPipeline:
    """Verifies dispatcher, legacy engine, and factor catalog end-to-end integration."""

    def test_catalog_contains_api_table_6_5_and_6_6(self):
        """Verifies that all 6 API Compendium 2021 factors are present in API_FACTORS."""
        required_codes = [
            "CompGasHF_Uncontrolled",
            "CompGasHF_REC",
            "CompOilHF_Uncontrolled",
            "CompOilHF_REC",
            "CompGasNoHF_Vented",
            "CompOilNoHF_Vented",
        ]
        factors_by_code = {f.get("code"): f for f in API_FACTORS.values() if isinstance(f, dict)}
        for code in required_codes:
            assert code in factors_by_code, f"Missing factor code: {code}"

    def test_dispatcher_tier1_flow(self):
        """Verifies dispatcher handles Tier 1 factor selection correctly."""
        payload = {
            "tier": "tier1",
            "well_type": "gas",
            "fracturing": True,
            "control_type": "uncontrolled",
            "amount": 2.0,
            "unit": "events",
        }
        res = dispatcher.dispatch("completions", payload, {}, {}, gwp_dict=GWP_AR5)
        assert res is not None
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 28.8 * 2.0
        assert "Table 6-5" in res["metadata"]["standard"]

    def test_compute_emissions_end_to_end(self):
        """Verifies compute_emissions pipeline returns rich result and correct method."""
        payload = {
            "process_type": "completions",
            "tier": "tier3",
            "amount": 5000.0,
            "unit": "m3",
            "ch4_content": 85.0,
            "disposition": "flared",
            "control_efficiency": 98.0,
        }
        res, method = compute_emissions(payload, {}, gwp_dict=GWP_AR5)
        assert res["ch4"] > 0
        assert res["co2"] > 0
        assert res["totalCo2e"] > 0
        assert "_full_api_res" in res


class TestOnshoreCompletionsFullPipelineApi:
    """Verifies end-to-end UI -> API -> Calculation Engine -> Database -> Output pipeline."""

    @pytest.fixture
    def api_client(self):
        from app import app
        from models import db, User, Facility
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as c:
            with app.app_context():
                user = User.query.filter_by(email="completions_audit@test.com").first()
                if not user:
                    user = User(
                        email="completions_audit@test.com",
                        fullName="Completions Engineer",
                        orgName="Audit Energy",
                        sector="Energy",
                        role="admin",
                    )
                    user.set_password("Password123!")
                    db.session.add(user)
                    db.session.commit()
                else:
                    user.role = "admin"
                    db.session.commit()
                if not db.session.get(Facility, 999):
                    fac = Facility(id=999, name="Onshore Completion Pad 42")
                    db.session.add(fac)
                    db.session.commit()
                c.post("/api/auth/login", json={"email": "completions_audit@test.com", "password": "Password123!"})
            yield c

    def test_api_tier1_completion_flow(self, api_client):
        """Tier 1: Post 2 gas well completions with REC, verify emissions and DB storage."""
        from app import app
        from models import db, Emission
        payload = {
            "year": 2024,
            "month": 5,
            "facility_id": 999,
            "process_type": "completions",
            "tier": "tier1",
            "well_type": "gas",
            "fracturing": True,
            "control_type": "rec",
            "disposition": "rec",
            "fuel": "Gas Well Completion - Hydraulic Fracturing (REC with Venting)",
            "amount": 2.0,
            "quantity": 2.0,
            "unit": "events",
            "calc_inputs": {
                "completions": {
                    "tier": "tier1",
                    "well_type": "gas",
                    "fracturing": True,
                    "disposition": "rec",
                    "amount": 2.0,
                    "unit": "events",
                }
            },
        }
        res = api_client.post("/api/emissions/", json=payload)
        assert res.status_code == 200 or res.status_code == 201
        data = res.get_json()
        assert "emissions" in data
        # Table 6-5: 13.542 t CH4 * 2 events = 27.084 t CH4
        assert pytest.approx(data["emissions"]["ch4"], rel=1e-3) == 27.084
        assert data["emissions"]["totalCo2e"] > 0

        with app.app_context():
            saved = Emission.query.filter_by(facility_id=999, process_type="completions", month=5, year=2024).order_by(Emission.id.desc()).first()
            assert saved is not None
            assert pytest.approx(saved.ch4_emissions, rel=1e-3) == 27.084
            assert saved.calc_method == "Well Completion Flowback"
            saved_payload = json.loads(saved.source_payload)
            assert saved_payload["tier"] == "tier1"
            assert "REC" in saved_payload["fuel"]

    def test_api_tier2_completion_rate_duration(self, api_client):
        """Tier 2: Rate x Duration (50 Mcf/hr * 20 hrs = 1000 Mcf), site CH4 = 85%."""
        payload = {
            "year": 2024,
            "month": 6,
            "facility_id": 999,
            "process_type": "completions",
            "tier": "tier2",
            "calc_method": "rate_duration",
            "comp_rate": 50.0,
            "comp_rate_unit": "Mcf/hr",
            "comp_duration": 20.0,
            "ch4_content": 85.0,
            "co2_content": 1.5,
            "comp_disposition": "vented",
            "amount": 1.0,
            "quantity": 1.0,
            "unit": "events",
            "calc_inputs": {
                "completions": {
                    "tier": "tier2",
                    "calc_method": "rate_duration",
                    "comp_rate": 50.0,
                    "comp_rate_unit": "Mcf/hr",
                    "comp_duration": 20.0,
                    "ch4_content": 85.0,
                    "co2_content": 1.5,
                    "comp_disposition": "vented",
                }
            },
        }
        res = api_client.post("/api/emissions/", json=payload)
        assert res.status_code in [200, 201]
        data = res.get_json()
        assert data["emissions"]["ch4"] > 0
        assert data["emissions"]["co2"] > 0
        # 1000 Mcf = 28,316.8 m3 * 0.85 * 0.6785 / 1000 = ~16.33 t CH4
        assert pytest.approx(data["emissions"]["ch4"], rel=1e-2) == 16.33

    def test_api_tier3_completion_metered_with_n2_deduction(self, api_client):
        """Tier 3: Metered volume 10,000 m3 with 2,000 m3 N2 deduction -> net 8,000 m3."""
        payload = {
            "year": 2024,
            "month": 7,
            "facility_id": 999,
            "process_type": "completions",
            "tier": "tier3",
            "comp_volume": 10000.0,
            "volume_unit": "m3",
            "comp_injected_n2": 2000.0,
            "comp_injected_n2_unit": "m3",
            "ch4_content": 85.0,
            "co2_content": 2.0,
            "comp_disposition": "vented",
            "amount": 1.0,
            "quantity": 1.0,
            "unit": "events",
            "calc_inputs": {
                "completions": {
                    "tier": "tier3",
                    "comp_volume": 10000.0,
                    "volume_unit": "m3",
                    "comp_injected_n2": 2000.0,
                    "comp_injected_n2_unit": "m3",
                    "ch4_content": 85.0,
                    "co2_content": 2.0,
                    "comp_disposition": "vented",
                }
            },
        }
        res = api_client.post("/api/emissions/", json=payload)
        assert res.status_code in [200, 201]
        data = res.get_json()
        # Net gas = 8000 m3; CH4 = 8000 * 0.85 * (16.04/379.3) * (35.3147/2204.62) = ~4.614 t
        assert pytest.approx(data["emissions"]["ch4"], rel=1e-2) == 4.614

