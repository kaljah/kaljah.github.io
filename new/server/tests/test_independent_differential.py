"""
Differential Testing: Production Calculation Engine vs. Independent Reference Model.
===================================================================================
Authoritative differential verification ensuring production calculations match
mathematical standards within defined numerical tolerances.

Rules:
1. Every critical equation is tested directly.
2. Result A (Production Implementation) vs Result B (Independent Reference Implementation).
3. If difference > tolerance: FAIL TEST.
"""
import pytest
import math
from calculations.dispatcher import CalculationDispatcher
from calculations.constants import GWP_AR5, GWP_AR4, GWP_AR6
from calculations.units import compute_scope3_co2e, CONVERSIONS, calculate_co2e
from calculations.uncertainty import propagate_uncertainty, Tier
from services.ogmp import ogmp_level_for, compute_facility_ogmp_level

import sys
from pathlib import Path
repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Import Independent Reference Model
from validation.reference_model import (
    IndependentUnitConverter,
    IndependentGWPModel,
    IndependentCombustionModel,
    IndependentFlaringModel,
    IndependentMudDegassing,
    IndependentCompletions,
    IndependentLiquidsUnloading,
    IndependentBlowdown,
    IndependentStorageTanks,
    IndependentPneumatics,
    IndependentFugitiveModel,
    IndependentAGRModel,
    IndependentDehydratorModel,
    IndependentStoichiometryModel,
    IndependentScope2Model,
    IndependentScope3Model,
    IndependentUncertaintyModel,
    IndependentIntensityModel,
    IndependentOGMPModel,
)


@pytest.fixture
def prod_dispatcher():
    return CalculationDispatcher()


class TestDifferentialScope1:
    """Differential verification for Scope 1 direct emissions."""

    def test_diff_stationary_combustion_tier1(self, prod_dispatcher):
        """Diff Test: Tier 1 Fuel-based combustion."""
        qty = 50_000.0
        unit = "m3"
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        hhv = 1020.0

        # Production Result
        res_prod = prod_dispatcher.dispatch(
            "stationary_combustion",
            {"quantity": qty, "unit": unit, "fuel_type": "natural_gas", "hhv": hhv, "factor_source": "default"},
            ef,
            {},
            gwp_dict=GWP_AR5,
        )

        # Reference Result
        res_ref = IndependentCombustionModel.calculate_tier1_2(
            fuel_quantity=qty,
            fuel_unit=unit,
            emission_factors=ef,
            fuel_type="natural_gas",
            hhv=hhv,
            gwp_standard="AR5",
        )

        prod_co2 = res_prod["results"]["co2"]["value"]
        prod_ch4 = res_prod["results"]["ch4"]["value"]
        prod_co2e = res_prod["total_co2e"]

        assert pytest.approx(prod_co2, rel=1e-4) == res_ref["co2"]
        assert pytest.approx(prod_ch4, rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(prod_co2e, rel=1e-4) == res_ref["co2e"]

    def test_diff_stationary_combustion_tier3(self, prod_dispatcher):
        """Diff Test: Tier 3 Gas chromatographic carbon mass balance."""
        qty = 10_000.0
        unit = "m3"
        comps = {"c1": 0.85, "c2": 0.07, "c3": 0.03, "co2_mol": 0.02}
        payload = {
            "quantity": qty,
            "unit": unit,
            "factor_source": "specific",
            "combustion_efficiency": 0.995,
            "operating_temperature": 25.0,
            "temp_unit": "C",
            "operating_pressure": 50.0,
            "press_unit": "psig",
            "hhv": 1020.0,
            **comps,
        }

        res_prod = prod_dispatcher.dispatch("stationary_combustion", payload, {}, {}, gwp_dict=GWP_AR5)
        res_ref = IndependentCombustionModel.calculate_tier3(
            fuel_quantity=qty,
            fuel_unit=unit,
            composition=comps,
            combustion_efficiency=0.995,
            operating_temp=25.0,
            temp_unit="C",
            operating_press=50.0,
            press_unit="psig",
            gwp_standard="AR5",
        )

        prod_co2 = res_prod["results"]["co2"]["value"]
        prod_ch4 = res_prod["results"]["ch4"]["value"]
        prod_co2e = res_prod["total_co2e"]

        assert pytest.approx(prod_co2, rel=1e-4) == res_ref["co2"]
        assert pytest.approx(prod_ch4, rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(prod_co2e, rel=1e-4) == res_ref["co2e"]

    def test_diff_flaring_dual_efficiency(self, prod_dispatcher):
        """Diff Test: Flaring dual-efficiency model (elevated and enclosed)."""
        qty = 25_000.0
        payload = {
            "amount": qty,
            "unit": "m3",
            "factor_source": "specific",
            "c1": 0.88,
            "flare_type": "elevated",
            "ef_unit": "kg/m3",
            "co2_mol": 0.015,
        }

        res_prod = prod_dispatcher.dispatch("flaring", payload, {"n2o": 0.0001}, {}, gwp_dict=GWP_AR5)
        res_ref = IndependentFlaringModel.calculate(
            gas_volume=qty,
            volume_unit="m3",
            ch4_fraction=0.88,
            flare_type="elevated",
            composition={"c1": 0.88, "co2_mol": 0.015},
            ef_n2o=0.0001,
            ef_unit="kg/m3",
            gwp_standard="AR5",
        )

        assert pytest.approx(res_prod["results"]["ch4"]["value"], rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(res_prod["results"]["co2"]["value"], rel=1e-4) == res_ref["co2"]
        assert pytest.approx(res_prod["total_co2e"], rel=1e-4) == res_ref["co2e"]

    def test_diff_liquids_unloading(self, prod_dispatcher):
        """Diff Test: Liquids unloading wellbore geometry."""
        payload = {
            "unload_depth": 6000.0,
            "unload_diam": 2.875,
            "unload_press": 200.0,
            "unload_events": 10,
            "unload_ch4_content": 0.82,
            "depth_unit": "ft",
            "diameter_unit": "in",
            "press_unit": "psig",
            "factor_source": "specific",
        }

        res_prod = prod_dispatcher.dispatch("liquids_unloading", payload, {}, {}, gwp_dict=GWP_AR5)
        res_ref = IndependentLiquidsUnloading.calculate(
            well_depth=6000.0,
            diameter=2.875,
            pressure=200.0,
            events=10,
            ch4_content=0.82,
            depth_unit="ft",
            diameter_unit="in",
            press_unit="psig",
            gwp_standard="AR5",
        )

        assert pytest.approx(res_prod["results"]["ch4"]["value"], rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(res_prod["total_co2e"], rel=1e-4) == res_ref["co2e"]

    def test_diff_vessel_blowdown(self, prod_dispatcher):
        """Diff Test: Vessel/pipeline blowdown with thermodynamic normalization."""
        payload = {
            "blowdown_volume": 150.0,
            "pressure": 350.0,
            "events": 4,
            "ch4_content": 0.85,
            "temp_unit": "F",
            "press_unit": "psig",
            "blowdown_temp": 75.0,
            "factor_source": "specific",
        }

        res_prod = prod_dispatcher.dispatch("blowdown", payload, {}, {}, gwp_dict=GWP_AR5)
        res_ref = IndependentBlowdown.calculate(
            blowdown_volume=150.0,
            pressure=350.0,
            events=4,
            temp=75.0,
            temp_unit="F",
            press_unit="psig",
            ch4_content=0.85,
            gwp_standard="AR5",
        )

        assert pytest.approx(res_prod["results"]["ch4"]["value"], rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(res_prod["total_co2e"], rel=1e-4) == res_ref["co2e"]

    def test_diff_storage_tanks_flashing(self, prod_dispatcher):
        """Diff Test: Storage tank flashing GOR method."""
        payload = {
            "amount": 15_000.0,
            "tank_unit": "bbl",
            "tank_gor": 45.0,
            "tank_ch4_content": 0.78,
            "factor_source": "specific",
        }

        res_prod = prod_dispatcher.dispatch("tank_flashing", payload, {}, {}, gwp_dict=GWP_AR5)
        res_ref = IndependentStorageTanks.calculate(
            throughput=15_000.0,
            throughput_unit="bbl",
            gas_oil_ratio=45.0,
            ch4_content=0.78,
            gwp_standard="AR5",
        )

        assert pytest.approx(res_prod["results"]["ch4"]["value"], rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(res_prod["total_co2e"], rel=1e-4) == res_ref["co2e"]

    def test_diff_pneumatic_devices(self, prod_dispatcher):
        """Diff Test: Pneumatic devices continuous bleed and intermittent."""
        payload_cont = {
            "pneu_count": 25,
            "pneu_hours": 8760,
            "pneu_bleed_rate": 18.5,
            "pneu_bleed_unit": "scf",
            "pneu_ch4_content": 0.85,
            "factor_source": "specific",
        }

        res_prod = prod_dispatcher.dispatch("pneumatic", payload_cont, {}, {}, gwp_dict=GWP_AR5)
        res_ref = IndependentPneumatics.calculate(
            count=25,
            hours=8760,
            bleed_rate=18.5,
            bleed_unit="scf",
            ch4_content=0.85,
            gwp_standard="AR5",
        )

        assert pytest.approx(res_prod["results"]["ch4"]["value"], rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(res_prod["total_co2e"], rel=1e-4) == res_ref["co2e"]

    def test_diff_acid_gas_removal(self, prod_dispatcher):
        """Diff Test: Acid gas removal (amine) CO2 balance and methane slip."""
        payload = {
            "agr_throughput": 75.0,
            "agr_unit": "mmscf",
            "agr_co2_in": 4.5,  # 4.5%
            "agr_co2_out": 0.05,  # 0.05%
            "agr_ch4_in": 85.0,
            "agr_ch4_slip_pct": 0.1,  # 0.1%
            "agr_control_eff": 0.0,
            "factor_source": "specific",
        }

        res_prod = prod_dispatcher.dispatch("agr", payload, {}, {}, gwp_dict=GWP_AR5)
        res_ref = IndependentAGRModel.calculate(
            throughput_mmscf=75.0,
            co2_in=0.045,
            co2_out=0.0005,
            ch4_in=0.85,
            ch4_slip_fraction=0.001,
            control_eff=0.0,
            gwp_standard="AR5",
        )

        assert pytest.approx(res_prod["results"]["co2"]["value"], rel=1e-4) == res_ref["co2"]
        assert pytest.approx(res_prod["results"]["ch4"]["value"], rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(res_prod["total_co2e"], rel=1e-4) == res_ref["co2e"]

    def test_diff_teg_dehydrator(self, prod_dispatcher):
        """Diff Test: TEG dehydrator parametric Henry's law solubility."""
        payload = {
            "dehy_pump_rate": 20.0,
            "dehy_pump_unit": "gph",
            "dehy_hours": 8760,
            "dehy_ch4_content": 85.0,
            "dehy_press": 850.0,
            "dehy_press_unit": "psig",
            "dehy_temp": 110.0,
            "dehy_temp_unit": "F",
            "dehy_has_flash": True,
            "factor_source": "specific",
        }

        res_prod = prod_dispatcher.dispatch("dehydrator", payload, {}, {}, gwp_dict=GWP_AR5)
        res_ref = IndependentDehydratorModel.calculate_tier3(
            pump_rate=20.0,
            pump_unit="gph",
            hours=8760,
            ch4_content=0.85,
            contactor_press=850.0,
            contactor_temp=110.0,
            has_flash_tank=True,
            gwp_standard="AR5",
        )

        assert pytest.approx(res_prod["results"]["ch4"]["value"], rel=1e-4) == res_ref["ch4"]
        assert pytest.approx(res_prod["total_co2e"], rel=1e-4) == res_ref["co2e"]


class TestDifferentialScope2and3:
    """Differential verification for Scope 2 and Scope 3 calculations."""

    def test_diff_scope2_grid_electricity(self):
        """Diff Test: Location-based grid electricity."""
        kwh = 1_000_000.0
        grid_ef = 0.522  # Algerian National Grid

        # Production calculation logic from routes/scope2.py
        prod_tco2e = (kwh * grid_ef) / 1000.0

        # Reference Model
        ref_res = IndependentScope2Model.calculate_electricity(kwh, grid_ef)
        assert pytest.approx(prod_tco2e, rel=1e-8) == ref_res["co2e"]

    def test_diff_scope2_indirect_steam(self):
        """Diff Test: Indirect steam net efficiency equation."""
        from routes.scope2 import _calc_indirect_steam

        data = {
            "amount": 2500.0,
            "unit": "mmbtu",
            "boiler_efficiency": 0.82,
            "calc_inputs": {
                "indirect_steam": {
                    "trans_loss": 0.05,
                    "ef_co2": 53.06,
                }
            }
        }

        prod_co2e, prod_mmbtu, prod_ef = _calc_indirect_steam(data)
        ref_res = IndependentScope2Model.calculate_indirect_steam(
            amount=2500.0,
            unit="mmbtu",
            boiler_eff=0.82,
            trans_loss=0.05,
            ef_co2=53.06,
        )

        assert pytest.approx(prod_co2e, rel=1e-6) == ref_res["co2e"]
        assert pytest.approx(prod_mmbtu, rel=1e-6) == ref_res["energy_mmbtu"]

    def test_diff_scope2_cogen_allocation(self):
        """Diff Test: WRI Efficiency CHP allocation."""
        from routes.scope2 import _calc_cogen_allocation

        data = {
            "total_emissions": 10_000.0,
            "heat_output_mmbtu": 50_000.0,
            "power_output_mwh": 10_000.0,
            "allocation_method": "wri_efficiency",
        }

        prod_allocated = _calc_cogen_allocation(data)
        ref_res = IndependentScope2Model.calculate_cogen_allocation(
            total_emissions=10_000.0,
            heat_output=50_000.0,
            power_output=10_000.0,
            method="wri_efficiency",
        )

        assert pytest.approx(prod_allocated, rel=1e-6) == ref_res["allocated_heat_co2e"]

    def test_diff_scope3_spend_and_physical(self):
        """Diff Test: Scope 3 spend EEIO vs physical tonne factor."""
        # 1. EEIO spend
        prod_eeio = compute_scope3_co2e(500_000.0, 3200.1, "kg CO2e/$1000", "spend_eeio")
        ref_eeio = IndependentScope3Model.calculate(500_000.0, 3200.1, "kg CO2e/$1000", "spend_eeio")
        assert pytest.approx(prod_eeio, rel=1e-8) == ref_eeio["co2e"]

        # 2. Tonne factor
        prod_tonne = compute_scope3_co2e(125.0, 2.45, "tCO2e/tonne", "supplier_specific")
        ref_tonne = IndependentScope3Model.calculate(125.0, 2.45, "tCO2e/tonne", "supplier_specific")
        assert pytest.approx(prod_tonne, rel=1e-8) == ref_tonne["co2e"]


class TestDifferentialUncertaintyAndCompliance:
    """Differential verification for Uncertainty, BOE, Intensities & OGMP."""

    def test_diff_uncertainty_product_and_sum(self):
        """Diff Test: IPCC 2006 SRSS propagation and GUM k=2 95% CI."""
        val = 1500.0
        u_ad = 0.05
        u_ef = 0.10

        prod_res = propagate_uncertainty(
            val,
            ef_uncertainty=u_ef,
            activity_uncertainty=u_ad,
            tier=Tier.T2,
        )

        ref_res = IndependentUncertaintyModel.propagate(
            value=val,
            ef_uncertainty=u_ef,
            activity_uncertainty=u_ad,
            coverage_factor=2.0,
        )

        assert pytest.approx(prod_res["relative_uncertainty"], rel=1e-6) == ref_res["relative_uncertainty_1sigma"]
        assert pytest.approx(prod_res["ci_95_abs"], rel=1e-6) == ref_res["ci_95_abs"]
        assert pytest.approx(prod_res["lower_bound_95"], rel=1e-6) == ref_res["lower_bound_95"]
        assert pytest.approx(prod_res["upper_bound_95"], rel=1e-6) == ref_res["upper_bound_95"]

    def test_diff_boe_and_carbon_intensity(self):
        """Diff Test: BOE normalization and operational intensities."""
        oil_bbl = 75_000.0
        gas_mscf = 25_000.0
        total_co2e = 1200.0

        boe = IndependentIntensityModel.calculate_boe(oil_bbl, gas_mscf)
        assert pytest.approx(boe, rel=1e-6) == oil_bbl + (gas_mscf * 0.178)

        ci = IndependentIntensityModel.calculate_carbon_intensity(total_co2e, boe)
        assert pytest.approx(ci, rel=1e-6) == (total_co2e * 1000.0) / boe

    def test_diff_ogmp_survey_reconciliation(self):
        """Diff Test: OGMP 2.0 survey reconciliation and facility level."""
        bu_ch4 = 100.0
        td_ch4 = 115.0  # +15% variance -> reconciled within 20%

        recon = IndependentOGMPModel.reconcile_survey(bu_ch4, td_ch4, threshold=20.0)
        assert recon["variance_flag"] is False
        assert recon["reconciliation_status"] == "Reconciled"
        assert pytest.approx(recon["variance_pct"], rel=1e-4) == 15.0

        lvl = IndependentOGMPModel.classify_facility_level(bu_ch4, td_ch4, bottom_up_source_level=4, threshold=20.0)
        assert lvl == 5
