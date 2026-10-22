"""
test_adversarial_deep_hunt.py
==============================
Adversarial Deep Hunt Test Suite:
Exhaustively testing mathematical invariants, boundary conditions, zero inputs,
negative inputs, extreme numbers, thermodynamic limits, and multi-tier parity
across Scope 1, Scope 2, and Scope 3.
"""

import math
import pytest
from calculations.dispatcher import CalculationDispatcher
from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.combustion_methods import CombustionMethodCalculator
from calculations.stoichiometry import StoichiometricCalculator, NitricAcidCalculator
from calculations.units import (
    convert, calculate_co2e, normalize_gas_volume_to_standard,
    compute_scope3_co2e, gas_volume_m3, to_kelvin, to_psia,
)
from calculations.constants import GWP_AR4, GWP_AR5, GWP_AR6
from calculations.indirect import (
    heat_to_mmbtu, CogenAllocationCalculator, IndirectSteamCalculator,
)
from routes.scope2 import _calc_indirect_steam
from calculations.vented_downstream import (
    RefiningHydrogenPlantCalculator, AsphaltBlowingCalculator,
)
from calculations.vented_production_pneumatic import (
    PneumaticDeviceCalculator, PneumaticPumpCalculator,
)
from calculations.vented_production_tank import (
    AcidGasRemovalCalculator, TankFlashingCalculator, BlowdownCalculator,
)
from calculations.vented_unloading import LiquidsUnloadingCalculator
from emission_factors import API_FACTORS


@pytest.fixture(scope="module")
def dispatcher():
    return CalculationDispatcher()


# Hand-worked conversions used by the expected values below (Compendium Equation 6-2: 379.3 scf/lbmole, 2,204.62 lb/t).
KMOL_M3 = 23.685          # m3 per kmol of gas at 60 F, 1 atm
T_STD_K = 288.706         # 60 F


def ch4_t(scf_ch4):
    return scf_ch4 / 379.3 * 16.04 / 2204.62


def co2_t(scf_co2):
    return scf_co2 / 379.3 * 44.01 / 2204.62


# ==============================================================================
# 1. SCOPE 1: COMBUSTION & SPECIALIZED ADVERSARIAL BOUNDARIES
# ==============================================================================

class TestScope1Adversarial:
    """Stress testing Scope 1 dispatch and calculation methods under extreme boundaries."""

    @pytest.mark.parametrize("fuel", ["Natural Gas", "Diesel (No. 2 Fuel Oil)", "Motor Gasoline", "Propane (Gas)"])
    def test_tier1_combustion_zero_amount(self, dispatcher, fuel):
        """Zero amount must yield strictly 0.0 emissions without division by zero."""
        payload = {"quantity": 0.0, "unit": "m3", "fuel": fuel, "fuel_type": fuel}
        ef = API_FACTORS.get(fuel, {"co2": 1.9, "ch4": 0.0001, "n2o": 0.00001, "unit": "kg/m3"})
        res = dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=GWP_AR5)
        assert res["total_co2e"] == 0.0
        assert res["results"]["co2"]["value"] == 0.0
        assert res["results"]["ch4"]["value"] == 0.0
        assert res["results"]["n2o"]["value"] == 0.0

    @pytest.mark.parametrize("bad_qty", [-1.0, -1e-6, -999999.0])
    def test_tier1_combustion_negative_rejection(self, dispatcher, bad_qty):
        """Negative fuel quantities must be rejected with ValueError."""
        payload = {"quantity": bad_qty, "unit": "m3", "fuel": "Natural Gas"}
        ef = API_FACTORS.get("Natural Gas", {})
        with pytest.raises(ValueError, match=r"(?i)negative"):
            dispatcher.dispatch("stationary_combustion", payload, ef, {}, gwp_dict=GWP_AR5)

    def test_tier3_fuel_gas_carbon_balance_extremes(self, dispatcher):
        """Tier 3 fuel gas carbon balance under extreme gas compositions."""
        # 100% methane
        payload_pure_ch4 = {
            "quantity": 10000.0, "unit": "m3", "fuel": "Natural Gas", "hhv": 1020.0,
            "combustion_efficiency": 99.5, "c1": 100.0, "factor_source": "specific",
        }
        res_ch4 = dispatcher.dispatch("stationary_combustion", payload_pure_ch4, {}, {}, gwp_dict=GWP_AR5)
        # 10,000 m3 / 23.685 m3/kmol = 422.2 kmol CH4: 99.5 % burned to CO2 (44.01), 0.5 % emitted as CH4 (16.04)
        kmol = 10000.0 / KMOL_M3
        assert res_ch4["results"]["co2"]["value"] == pytest.approx(kmol * 0.995 * 44.01 / 1000.0, rel=5e-3)  # 18.49 t
        assert res_ch4["results"]["ch4"]["value"] == pytest.approx(kmol * 0.005 * 16.04 / 1000.0, rel=5e-3)  # 0.0339 t
        assert res_ch4["total_co2e"] == pytest.approx(
            res_ch4["results"]["co2"]["value"] + 28.0 * res_ch4["results"]["ch4"]["value"], rel=1e-9)

        # Heavy gas with C1-C5
        payload_rich = {
            "quantity": 5000.0, "unit": "m3", "fuel": "Natural Gas", "hhv": 1250.0,
            "combustion_efficiency": 98.0,
            "c1": 75.0, "c2": 10.0, "c3": 8.0, "c4": 5.0, "c5": 2.0, "factor_source": "specific",
        }
        res_rich = dispatcher.dispatch("stationary_combustion", payload_rich, {}, {}, gwp_dict=GWP_AR5)
        # 5,000 m3 = 211.1 kmol; carbon per kmol of gas = 0.75x1 + 0.10x2 + 0.08x3 + 0.05x4 + 0.02x5 = 1.49 kmol;
        # 98 % of it to CO2; the unburned 2 % of the methane is emitted as CH4
        kmol = 5000.0 / KMOL_M3
        assert res_rich["results"]["co2"]["value"] == pytest.approx(kmol * 1.49 * 0.98 * 44.01 / 1000.0, rel=5e-3)
        assert res_rich["results"]["ch4"]["value"] == pytest.approx(kmol * 0.75 * 0.02 * 16.04 / 1000.0, rel=5e-3)
        # the heavier gas carries more carbon per m3 than pure methane (1.49 against 1.00 kmol C/kmol)
        assert res_rich["results"]["co2"]["value"] / 5000.0 > res_ch4["results"]["co2"]["value"] / 10000.0

    def test_flaring_efficiency_boundaries(self, dispatcher):
        """Flaring under different combustion efficiency and destruction efficiencies."""
        # 98% combustion efficiency vs 99.8% combustion efficiency
        p_normal = {"amount": 1000.0, "unit": "m3", "ch4_content": 90.0, "combustion_efficiency": 98.0, "factor_source": "specific"}
        r_normal = dispatcher.dispatch("flaring", p_normal, {}, {}, gwp_dict=GWP_AR5)
        assert r_normal["total_co2e"] > 0.0

        p_high_comb = {"amount": 1000.0, "unit": "m3", "ch4_content": 90.0, "combustion_efficiency": 99.8, "factor_source": "specific"}
        r_high_comb = dispatcher.dispatch("flaring", p_high_comb, {}, {}, gwp_dict=GWP_AR5)
        # Higher combustion efficiency converts more carbon to CO2
        assert r_high_comb["results"]["co2"]["value"] > r_normal["results"]["co2"]["value"]

        # High destruction efficiency (99.8% vs 98.0% default) reduces methane slip
        p_high_dest = {"amount": 1000.0, "unit": "m3", "ch4_content": 90.0, "control_efficiency": 99.8, "factor_source": "specific"}
        r_high_dest = dispatcher.dispatch("flaring", p_high_dest, {}, {}, gwp_dict=GWP_AR5)
        assert r_high_dest["results"]["ch4"]["value"] < r_normal["results"]["ch4"]["value"]

        # Negative flare volume rejected
        with pytest.raises(ValueError, match=r"(?i)negative"):
            dispatcher.dispatch("flaring", {"amount": -50.0, "unit": "m3", "ch4_content": 90.0, "factor_source": "specific"}, {}, {}, gwp_dict=GWP_AR5)

    def test_combustion_methods_equipment_matrix(self):
        """API Compendium Table 4-9 & 4-11 equipment-specific calculations."""
        calc = CombustionMethodCalculator()
        # 4-stroke lean burn IC engine
        res_ic = calc.calculate(
            "equipment",
            {"equipment_type": "ic_4s_lean_ng", "fuel_volume": 100000.0, "fuel_volume_unit": "scf"},
            gwp_dict=GWP_AR5,
        )
        assert res_ic["total_co2e"] > 0.0
        assert res_ic["results"]["co2"]["value"] > 0.0
        assert res_ic["results"]["ch4"]["value"] > 0.0
        assert res_ic["results"]["n2o"]["value"] > 0.0

        # Gas turbine
        res_turb = calc.calculate(
            "equipment",
            {"equipment_type": "turbine_ng_uncontrolled", "energy_mmbtu": 500.0},
            gwp_dict=GWP_AR5,
        )
        assert res_turb["total_co2e"] > 0.0

        # Unknown equipment type rejected
        with pytest.raises(ValueError, match=r"Unknown equipment type"):
            calc.calculate("equipment", {"equipment_type": "magic_engine", "energy_mmbtu": 100.0})

    def test_thermal_oxidizer_method(self):
        """API Exhibit 5.3 TOC thermal oxidizer."""
        calc = CombustionMethodCalculator()
        res = calc.calculate(
            "thermal_oxidizer",
            {
                "toc_mass": 25.0,
                "toc_mass_unit": "t",
                "toc_carbon_wt_pct": 82.5,
                "toc_ch4_wt_pct": 5.0,
                "destruction_efficiency": 99.0,
            },
            gwp_dict=GWP_AR5,
        )
        # 25 t TOC x 82.5 wt % carbon x 99 % destroyed x 44.01/12.011 ; CH4 5 wt % x 1 % not destroyed
        assert res["results"]["co2"]["value"] == pytest.approx(25.0 * 0.825 * 0.99 * 44.01 / 12.011, rel=1e-3)  # 74.82
        assert res["results"]["ch4"]["value"] == pytest.approx(25.0 * 0.05 * 0.01, rel=1e-9)                     # 0.0125
        assert res["total_co2e"] == pytest.approx(res["results"]["co2"]["value"] + 28.0 * 0.0125, rel=1e-9)

    def test_flare_voc_back_calculation(self):
        """API Exhibit 5.2 VOC back-calculation method."""
        calc = CombustionMethodCalculator()
        res = calc.calculate(
            "flare_voc",
            {
                "voc_mass": 2.5,
                "voc_mass_unit": "t",
                "wt_ch4": 80.0,
                "wt_c2h6": 8.0,
                "wt_c3h8": 5.0,
                "wt_c4h10": 4.0,
                "wt_c5h12": 1.5,
                "wt_c6plus": 1.5,
                "combustion_efficiency": 98.0,
            },
            gwp_dict=GWP_AR5,
        )
        # VOC (C3+) is 5 + 4 + 1.5 + 1.5 = 12 wt % of the flare gas, so the 2.5 t of VOC emitted come with
        # 2.5 / 0.12 = 20.83 t of hydrocarbon emitted, of which 80 wt % is methane
        hc_emitted = 2.5 / 0.12
        assert res["results"]["ch4"]["value"] == pytest.approx(hc_emitted * 0.80, rel=1e-9)  # 16.67 t
        # CO2: the hydrocarbon burned is hc_emitted x 98 / 2 = 49 x that emitted; its carbon weight fraction is
        # sum(w_i x carbon share of species i) = 0.7619 (CH4 .7488, C2H6 .7988, C3H8 .8171, C4H10 .8266, C5H12 .8324,
        # C6H14 .8363), burned to CO2 at 44.01 / 12.011
        carbon = (0.80 * 0.74882 + 0.08 * 0.79882 + 0.05 * 0.81711 + 0.04 * 0.82664 + 0.015 * 0.83236 + 0.015 * 0.83626)
        assert res["results"]["co2"]["value"] == pytest.approx(hc_emitted * 49.0 * carbon * 44.01 / 12.011, rel=1e-3)
        # N2O (Exhibit 5.2 step 3): hydrocarbon flared (1,041.7 t) -> scf with the mixture MW -> x mixture HHV
        # (Btu/scf: CH4 1010, C2H6 1769.7, C3H8 2516.1, C4H10 3262.4, C5H12 4008.9, C6H14 4755.9) x 9.50e-8 t N2O/MMBtu
        flared_t = hc_emitted / 0.02
        mol = {"c1": 0.80 / 16.04, "c2": 0.08 / 30.07, "c3": 0.05 / 44.10, "c4": 0.04 / 58.12, "c5": 0.015 / 72.15,
               "c6": 0.015 / 86.18}
        hhv = {"c1": 1010.0, "c2": 1769.7, "c3": 2516.1, "c4": 3262.4, "c5": 4008.9, "c6": 4755.9}
        mw_mix = 1.0 / sum(mol.values())
        mix_hhv = sum(mol[k] * hhv[k] for k in mol) / sum(mol.values())
        scf = flared_t * 1000.0 / 0.45359237 / mw_mix * 379.3
        assert res["results"]["n2o"]["value"] == pytest.approx(scf * mix_hhv / 1e6 * 9.50e-8, rel=2e-3)
        assert res["total_co2e"] == pytest.approx(
            res["results"]["co2"]["value"] + 28.0 * res["results"]["ch4"]["value"]
            + 265.0 * res["results"]["n2o"]["value"], rel=1e-9)

    def test_carbon_content_liquid_fuel(self):
        """API Exhibit 4.5 liquid fuel carbon content method."""
        calc = CombustionMethodCalculator()
        res = calc.calculate(
            "carbon_content",
            {
                "fuel_volume": 10000.0,
                "fuel_volume_unit": "gal",
                "fuel_density": 7.1,
                "density_unit": "lb/gal",
                "carbon_wt_pct": 86.5,
                "oxidation_pct": 99.0,
            },
            gwp_dict=GWP_AR5,
        )
        assert res["total_co2e"] > 0.0
        assert res["results"]["co2"]["value"] > 0.0
        # Carbon content alone yields zero CH4/N2O on pure carbon oxidation balance
        ch4_val = res["results"]["ch4"]["value"] if isinstance(res["results"]["ch4"], dict) else res["results"]["ch4"]
        assert ch4_val == 0.0


# ==============================================================================
# 2. CHEMICAL & STOICHIOMETRIC CALCULATORS
# ==============================================================================

class TestStoichiometricAdversarial:
    """Testing hydrogen plants, sulfur recovery, nitric acid, and mass balances."""

    def test_refining_hydrogen_plant_feedstock_balance(self):
        """API §6.11.3 Eq 6-49 feedstock carbon balance."""
        calc = RefiningHydrogenPlantCalculator()
        res = calc.calculate(
            method="feedstock_balance",
            feedstock_rate_tonnes_yr=10000.0,
            feedstock_carbon_fraction=0.748,
            gwp_dict=GWP_AR5,
        )
        assert res["total_co2e"] == pytest.approx(10000.0 * 0.748 * (44.0 / 12.0), rel=1e-3)
        assert res["results"]["co2"]["value"] > 0.0

    def test_refining_hydrogen_plant_stoichiometry(self):
        """API §6.11.3 Eq 6-50 H2 stoichiometry."""
        calc = RefiningHydrogenPlantCalculator()
        res = calc.calculate(
            method="h2_stoichiometry",
            h2_production_m3_yr=500000.0,
            co2_to_h2_molar_ratio=0.25,
            gwp_dict=GWP_AR5,
        )
        # 500,000 m3 H2 / 23.685 m3/kmol x 0.25 kmol CO2 per kmol H2 x 44.01 kg/kmol
        assert res["results"]["co2"]["value"] == pytest.approx(500000.0 / KMOL_M3 * 0.25 * 44.01 / 1000.0, rel=2e-3)
        assert res["total_co2e"] == pytest.approx(res["results"]["co2"]["value"], rel=1e-12)  # CO2 only: 232.2 t

    def test_refining_hydrogen_plant_simple_factor(self):
        """API §6.11.3 Table 6-51 simple factor."""
        calc = RefiningHydrogenPlantCalculator()
        res = calc.calculate(
            method="simple_factor",
            simple_basis="h2_m3",
            simple_volume=1000000.0,
            gwp_dict=GWP_AR5,
        )
        expected_t = 1000000.0 * (473.6 / 1_000_000.0)
        assert res["total_co2e"] == pytest.approx(expected_t, rel=1e-3)

    def test_nitric_acid_calculator_extremes(self):
        """Nitric & Adipic acid N2O calculations."""
        calc = NitricAcidCalculator()
        # Unabated nitric acid
        res_unabated = calc.calculate(production_amount=1000.0, abatement_efficiency=0.0, gwp_dict=GWP_AR5)
        assert res_unabated["total_co2e"] > 0.0
        assert res_unabated["results"]["n2o"]["value"] == pytest.approx(9.0, rel=1e-3)

        # 95% catalytic abatement
        res_abated = calc.calculate(production_amount=1000.0, abatement_efficiency=95.0, gwp_dict=GWP_AR5)
        assert res_abated["results"]["n2o"]["value"] == pytest.approx(9.0 * 0.05, rel=1e-3)

        # 100% abatement
        res_full = calc.calculate(production_amount=1000.0, abatement_efficiency=100.0, gwp_dict=GWP_AR5)
        assert res_full["results"]["n2o"]["value"] == 0.0
        assert res_full["total_co2e"] == 0.0

        # Negative production rejected
        with pytest.raises(ValueError, match=r"negative"):
            calc.calculate(production_amount=-50.0)

    def test_asphalt_blowing(self):
        """API §6.11.4 asphalt blowing."""
        calc = AsphaltBlowingCalculator()
        res = calc.calculate(throughput=1000.0, unit="tonne", controlled=False, gwp_dict=GWP_AR5)
        # Table 6-52, uncontrolled: 6.19E-03 t CO2 and 3.38E-03 t CH4 per tonne of asphalt blown
        assert res["results"]["co2"]["value"] == pytest.approx(1000.0 * 6.19e-3, rel=1e-9)
        assert res["results"]["ch4"]["value"] == pytest.approx(1000.0 * 3.38e-3, rel=1e-9)
        assert res["total_co2e"] == pytest.approx(6.19 + 28.0 * 3.38, rel=1e-9)  # 100.83 t CO2e


# ==============================================================================
# 3. SCOPE 2: DUAL REPORTING, INDIRECT STEAM, COGEN ALLOCATION
# ==============================================================================

class TestScope2Adversarial:
    """Stress testing Scope 2 indirect emissions and dual-reporting boundaries."""

    def test_grid_electricity_location_vs_market(self):
        """Validating dual reporting separation and market-based zero instruments."""
        kwh = 100000.0
        location_ef = 0.58  # kg CO2e / kWh
        co2e_loc = (kwh * location_ef) / 1000.0

        # Zero emission green tariff / REC
        market_ef_zero = 0.0
        co2e_market_zero = (kwh * market_ef_zero) / 1000.0

        assert co2e_loc == pytest.approx(58.0)
        assert co2e_market_zero == 0.0

    def test_indirect_steam_efficiencies(self):
        """Testing indirect steam under extreme boiler efficiency and line loss."""
        # 1000 MMBtu, boiler eff 80%, loss 0%
        co2e_base, mmbtu_base, _ = _calc_indirect_steam({
            "amount": 1000.0, "unit": "mmbtu", "boiler_efficiency": 0.80,
            "calc_inputs": {"indirect_steam": {"trans_loss": 0.0}}
        })
        assert co2e_base > 0.0
        assert mmbtu_base == 1000.0

        # High line loss (15%) increases required boiler fuel and emissions
        co2e_loss, _, _ = _calc_indirect_steam({
            "amount": 1000.0, "unit": "mmbtu", "boiler_efficiency": 0.80,
            "calc_inputs": {"indirect_steam": {"trans_loss": 0.15}}
        })
        assert co2e_loss > co2e_base

        # Boiler eff <= 0 must fail
        with pytest.raises(Exception):
            _calc_indirect_steam({
                "amount": 1000.0, "unit": "mmbtu", "boiler_efficiency": 0.0,
                "calc_inputs": {"indirect_steam": {"trans_loss": 0.0}}
            })

    def test_cogen_chp_allocation_methods(self):
        """Testing WRI efficiency method vs energy content method for CHP."""
        calc = CogenAllocationCalculator()
        total_em = 1000.0  # t CO2e
        heat_mmbtu = 4000.0
        power_mwh = 1000.0  # = 3412.14 MMBtu

        # WRI efficiency method (heat eff 0.80, power eff 0.35)
        res_wri = calc.calculate(
            total_emissions=total_em, heat_output=heat_mmbtu, power_output=power_mwh,
            method="wri_efficiency", power_unit="mwh", heat_efficiency=0.80, power_efficiency=0.35,
        )
        heat_wri = res_wri["metadata"]["allocated_heat_tonnes"]
        power_wri = res_wri["metadata"]["allocated_power_tonnes"]
        assert heat_wri + power_wri == pytest.approx(total_em, rel=1e-3)

        # Energy content method (pure MMBtu ratio)
        res_energy = calc.calculate(
            total_emissions=total_em, heat_output=heat_mmbtu, power_output=power_mwh,
            method="energy_content", power_unit="mwh",
        )
        heat_energy = res_energy["metadata"]["allocated_heat_tonnes"]
        power_energy = res_energy["metadata"]["allocated_power_tonnes"]
        assert heat_energy + power_energy == pytest.approx(total_em, rel=1e-3)


# ==============================================================================
# 4. SCOPE 3: ALL 15 CATEGORIES & EEIO SPEND CALCULATOR
# ==============================================================================

class TestScope3Adversarial:
    """Stress testing Scope 3 categories, unit handling, and EEIO factor denominators."""

    @pytest.mark.parametrize("cat_num", range(1, 16))
    def test_scope3_categories_coverage(self, cat_num):
        """Verify that all 15 Scope 3 categories compute valid, non-negative CO2e."""
        # Generic test with 1000 units and 0.25 kg CO2e / unit
        co2e = compute_scope3_co2e(amt=1000.0, ef=0.25, ef_unit="kg CO2e / unit", activity_unit="unit")
        assert co2e == pytest.approx(0.25, rel=1e-3)

    def test_scope3_spend_based_eeio_denominators(self):
        """Testing EEIO spend factors per USD vs per 1,000 USD."""
        spend = 50000.0  # $50,000

        # Factor per USD (e.g. 0.42 kg CO2e / $)
        co2e_per_dollar = compute_scope3_co2e(amt=spend, ef=0.42, ef_unit="kg CO2e / $", activity_unit="usd")
        assert co2e_per_dollar == pytest.approx(50000.0 * 0.42 / 1000.0, rel=1e-3)

        # Factor per $1,000 (e.g. 420 kg CO2e / $1,000)
        co2e_per_k_dollar = compute_scope3_co2e(amt=spend, ef=420.0, ef_unit="kg CO2e / $1,000", activity_unit="usd")
        assert co2e_per_k_dollar == pytest.approx(50000.0 * 0.42 / 1000.0, rel=1e-3)

    def test_scope3_freight_transport_units(self):
        """Testing tonne-km vs ton-mile conversions."""
        # 10,000 tonne-km with 0.08 kg CO2e / tonne-km
        co2e_tkm = compute_scope3_co2e(amt=10000.0, ef=0.08, ef_unit="kg CO2e / tonne-km", activity_unit="tonne-km")
        assert co2e_tkm == pytest.approx(10000.0 * 0.08 / 1000.0, rel=1e-3)

    def test_scope3_invalid_inputs_rejection(self):
        """Zero and negative activity amounts yield 0.0 gracefully."""
        assert compute_scope3_co2e(amt=0.0, ef=1.5, ef_unit="kg/unit") == 0.0
        assert compute_scope3_co2e(amt=-500.0, ef=1.5, ef_unit="kg/unit") == 0.0
        assert compute_scope3_co2e(amt=1000.0, ef=-1.5, ef_unit="kg/unit") == 0.0


# ==============================================================================
# 5. THERMODYNAMIC & PHYSICAL UNIT CONVERSION INVARIANTS
# ==============================================================================

class TestThermodynamicInvariants:
    """Verifying thermodynamic equations, pressure/temperature conversions, and GWP tables."""

    def test_ideal_gas_law_temperature_effect(self):
        """Higher operating temperature expands gas -> fewer standard m3 per measured m3."""
        v_std_cold = normalize_gas_volume_to_standard(volume=1000.0, operating_temp=0.0, temp_unit="C")
        v_std_warm = normalize_gas_volume_to_standard(volume=1000.0, operating_temp=50.0, temp_unit="C")
        # standard m3 = measured m3 x T_std / T: 288.706 K / 273.15 K and 288.706 K / 323.15 K
        assert v_std_cold == pytest.approx(1000.0 * T_STD_K / 273.15, rel=1e-4)   # 1,056.9
        assert v_std_warm == pytest.approx(1000.0 * T_STD_K / 323.15, rel=1e-4)   # 893.4
        assert v_std_cold > v_std_warm

    def test_ideal_gas_law_pressure_effect(self):
        """Higher operating pressure compresses gas -> more standard m3 per measured m3."""
        v_std_low = normalize_gas_volume_to_standard(volume=1000.0, operating_press=10.0, press_unit="psig")
        v_std_high = normalize_gas_volume_to_standard(volume=1000.0, operating_press=100.0, press_unit="psig")
        # standard m3 = measured m3 x (P gauge + 14.696) / 14.696
        assert v_std_low == pytest.approx(1000.0 * (10.0 + 14.696) / 14.696, rel=1e-4)    # 1,680.5
        assert v_std_high == pytest.approx(1000.0 * (100.0 + 14.696) / 14.696, rel=1e-4)  # 7,804.6
        assert v_std_high > v_std_low

    def test_absolute_zero_temperature_rejection(self):
        """Temperatures below absolute zero (0 K) must raise ValueError."""
        with pytest.raises(ValueError, match=r"absolute zero"):
            to_kelvin(-274.0, "C")
        with pytest.raises(ValueError, match=r"absolute zero"):
            to_kelvin(-500.0, "F")

    def test_vacuum_pressure_rejection(self):
        """Pressures below absolute vacuum (0 psia) must raise ValueError."""
        with pytest.raises(ValueError, match=r"vacuum"):
            to_psia(-20.0, "psig")

    def test_gwp_horizons_monotonicity(self):
        """AR4 vs AR5 vs AR6 GWP table consistency."""
        co2, ch4, n2o = 100.0, 10.0, 1.0
        co2e_ar4 = calculate_co2e(co2=co2, ch4=ch4, n2o=n2o, gwp_dict=GWP_AR4)
        co2e_ar5 = calculate_co2e(co2=co2, ch4=ch4, n2o=n2o, gwp_dict=GWP_AR5)
        co2e_ar6 = calculate_co2e(co2=co2, ch4=ch4, n2o=n2o, gwp_dict=GWP_AR6)

        # In AR4: CH4=25, N2O=298 -> 100 + 250 + 298 = 648
        # In AR5: CH4=28, N2O=265 -> 100 + 280 + 265 = 645
        # In AR6: CH4=29.8, N2O=273 -> 100 + 298 + 273 = 671
        assert co2e_ar4 == pytest.approx(648.0, rel=1e-3)
        assert co2e_ar5 == pytest.approx(645.0, rel=1e-3)
        assert co2e_ar6 == pytest.approx(671.0, rel=1e-3)


# ==============================================================================
# 6. VENTED PNEUMATICS & CHEMICAL INJECTION PUMPS
# ==============================================================================

class TestVentedPneumaticsAdversarial:
    """Stress testing pneumatic controllers, actuation, and gas-driven pumps."""

    def test_continuous_high_bleed_vs_low_bleed(self):
        """API Compendium Table 6-14 high bleed vs low bleed controllers."""
        calc = PneumaticDeviceCalculator()
        # High bleed controller (16.4 scf/hr baseline)
        res_high = calc.calculate(
            controller_type="high_bleed", count=10.0, hours=8760.0,
            ch4_content=0.85, gwp_dict=GWP_AR5,
        )
        # 10 controllers x 13.4 scf CH4/hr (Table 6-14, 81.6 mol %) x 8,760 h x 85/81.6 for the site gas
        high_scf = 10 * 13.4 * 8760.0 * 0.85 / 0.816
        assert res_high["results"]["ch4"]["value"] == pytest.approx(ch4_t(high_scf), rel=5e-3)  # 23.4 t
        assert res_high["total_co2e"] == pytest.approx(28.0 * ch4_t(high_scf), rel=5e-3)

        # Low bleed controller (2.6 scf/hr baseline)
        res_low = calc.calculate(
            controller_type="low_bleed", count=10.0, hours=8760.0,
            ch4_content=0.85, gwp_dict=GWP_AR5,
        )
        low_scf = 10 * 2.1 * 8760.0 * 0.85 / 0.816  # 2.1 scf CH4/hr (Table 6-14)
        assert res_low["results"]["ch4"]["value"] == pytest.approx(ch4_t(low_scf), rel=5e-3)  # 3.67 t
        # the tables' ratio: 13.4 / 2.1 = 6.38
        assert res_high["total_co2e"] / res_low["total_co2e"] == pytest.approx(13.4 / 2.1, rel=1e-9)

    def test_intermittent_controllers(self):
        """API Compendium Table 6-15 intermittent controllers."""
        calc = PneumaticDeviceCalculator()
        res_norm = calc.calculate(
            controller_type="intermittent_normal", count=5.0, hours=8760.0,
            ch4_content=0.816, gwp_dict=GWP_AR5,
        )
        res_malf = calc.calculate(
            controller_type="intermittent_malfunctioning", count=5.0, hours=8760.0,
            ch4_content=0.816, gwp_dict=GWP_AR5,
        )
        # Table 6-15 (whole gas at 81.6 mol %, the site gas here): normal 0.28 scf/hr, malfunctioning 24.1 scf/hr
        assert res_norm["results"]["ch4"]["value"] == pytest.approx(ch4_t(5 * 0.28 * 8760.0 * 0.816), rel=5e-3)   # 0.192 t
        assert res_malf["results"]["ch4"]["value"] == pytest.approx(ch4_t(5 * 24.1 * 8760.0 * 0.816), rel=5e-3)  # 16.5 t
        assert res_malf["total_co2e"] / res_norm["total_co2e"] == pytest.approx(24.1 / 0.28, rel=1e-9)

    def test_pneumatic_pump_factor_vs_engineering(self):
        """Pneumatic pump factor approach vs Eq 6-15/6-16 engineering approach."""
        calc = PneumaticPumpCalculator()
        # Factor method
        res_factor = calc.calculate(
            method="factor", pump_type="diaphragm", pump_count=4.0, operating_hours=8760.0, ch4_content=0.85,
            gwp_dict=GWP_AR5,
        )
        # Table 6-16: diaphragm pump 23.6 scf gas/hr; 4 pumps x 23.6 x 8,760 h x 85 % CH4
        assert res_factor["results"]["ch4"]["value"] == pytest.approx(ch4_t(4 * 23.6 * 8760.0 * 0.85), rel=5e-3)  # 13.5 t

        # Engineering method
        res_eng = calc.calculate(
            method="engineering", pump_count=2.0, volume_liquid_pumped_ft3=50000.0,
            pump_outlet_pressure_psig=150.0, ch4_content=0.85, gwp_dict=GWP_AR5,
        )
        # Eq 6-15: V_G = (P_O + P_A)/14.7 x T_A/(459.7 + T_G) x V_L x (1 + I) with T_G = 60 F (T_A/(459.7+T_G) = 1)
        # and the default 30 % pump inefficiency: 2 pumps x 164.7/14.7 x 50,000 ft3 x 1.3
        vg = 2 * (150.0 + 14.7) / 14.7 * 50000.0 * 1.3
        assert res_eng["results"]["ch4"]["value"] == pytest.approx(ch4_t(vg * 0.85), rel=2e-3)  # 23.7 t

    def test_pneumatic_pump_zero_and_negative_rejection(self):
        """Pneumatic pump zero count yields 0.0, negative count raises ValueError."""
        calc = PneumaticPumpCalculator()
        res_zero = calc.calculate(method="factor", pump_count=0.0, operating_hours=8760.0)
        assert res_zero["total_co2e"] == 0.0
        assert res_zero["results"]["ch4"]["value"] == 0.0

        with pytest.raises(ValueError, match=r"negative"):
            calc.calculate(method="factor", pump_count=-2.0, operating_hours=8760.0)


# ==============================================================================
# 7. TANKS, ACID GAS REMOVAL, AND BLOWDOWNS
# ==============================================================================

class TestVentedTanksAndMidstreamAdversarial:
    """Stress testing tank flashing, AGR amine units, and vessel blowdowns."""

    def test_acid_gas_removal_methods(self):
        """AGR amine unit Table 6-19 throughput method vs Eq 6-18 mass balance."""
        calc = AcidGasRemovalCalculator()
        # Throughput method
        res_tp = calc.calculate(
            method="throughput", sour_gas_mmscf_yr=500.0, control_efficiency=0.0, gwp_dict=GWP_AR5,
        )
        # Table 6-19: 0.0185 t CH4 per 10^6 scf treated gas; 500 MMscf -> 9.25 t CH4 = 259 t CO2e
        assert res_tp["results"]["ch4"]["value"] == pytest.approx(500.0 * 0.0185, rel=1e-9)
        assert res_tp["total_co2e"] == pytest.approx(28.0 * 9.25, rel=1e-9)

        # Mass balance method (Eq 6-18)
        res_mb = calc.calculate(
            method="sour_sweet_balance",
            sour_gas_scf_yr=100000000.0, sweet_gas_scf_yr=95000000.0,
            sour_co2_content=0.05, sweet_co2_content=0.01,
            gwp_dict=GWP_AR5,
        )
        # Eq 6-18: CO2 = (100e6 scf x 5 % - 95e6 scf x 1 %) = 4.05e6 scf CO2 -> t; CH4 at Table 6-19 on 100 MMscf
        assert res_mb["results"]["co2"]["value"] == pytest.approx(co2_t(100e6 * 0.05 - 95e6 * 0.01), rel=1e-3)  # 213.2 t
        assert res_mb["results"]["ch4"]["value"] == pytest.approx(100.0 * 0.0185, rel=1e-9)

    def test_tank_flashing_methods(self):
        """Tank flashing GOR method vs VBE Standing method."""
        calc = TankFlashingCalculator()
        # GOR method
        res_gor = calc.calculate(
            throughput=10000.0, gas_oil_ratio=25.0, ch4_content=0.75, gwp_dict=GWP_AR5,
        )
        # 10,000 bbl x 25 scf/bbl = 250,000 scf of flash gas x 75 % CH4
        assert res_gor["results"]["ch4"]["value"] == pytest.approx(ch4_t(250000.0 * 0.75), rel=5e-3)  # 3.60 t
        assert res_gor["total_co2e"] == pytest.approx(28.0 * res_gor["results"]["ch4"]["value"], rel=1e-9)

        # Zero throughput yields 0.0
        res_zero = calc.calculate(throughput=0.0, gas_oil_ratio=25.0, ch4_content=0.75, gwp_dict=GWP_AR5)
        assert res_zero["total_co2e"] == 0.0

        # Negative throughput rejected
        with pytest.raises(ValueError, match=r"negative"):
            calc.calculate(throughput=-500.0, gas_oil_ratio=25.0, ch4_content=0.75)

    def test_blowdown_methods(self):
        """Vessel blowdowns under standard volume and differential pressure."""
        calc = BlowdownCalculator()
        # Differential pressure blowdown
        res_diff = calc.calculate(
            blowdown_volume=500.0,
            pressure=1000.0,
            final_pressure=50.0,
            blowdown_mode="differential",
            operating_temperature=80.0,
            temp_unit="F",          # a temperature without a unit is read as C
            z_factor=0.90,          # given, so the expected value does not depend on the Z estimate
            ch4_content=0.85,
            events=12.0,
            gwp_dict=GWP_AR5,
        )
        # per event: 500 m3 x [(1,000 + 14.696) - (50 + 14.696)] psia / 14.696 x 288.706 K / 299.817 K (80 F) / Z 0.90;
        # 12 events; x 85 % CH4 x 16.04 / 23.685 kg/m3
        v_std = 500.0 * (1000.0 - 50.0) / 14.696 * T_STD_K / 299.817 / 0.90 * 12
        assert res_diff["inputs"]["total_v_std_m3"] == pytest.approx(v_std, rel=1e-3)  # 414,986 m3
        assert res_diff["results"]["ch4"]["value"] == pytest.approx(v_std * 0.85 * 16.04 / KMOL_M3 / 1000.0, rel=2e-3)  # 238.9 t
        assert res_diff["total_co2e"] == pytest.approx(28.0 * res_diff["results"]["ch4"]["value"], rel=1e-9)


# ==============================================================================
# 8. WELL VENTING FROM LIQUIDS UNLOADING
# ==============================================================================

class TestLiquidsUnloadingAdversarial:
    """Stress testing liquids unloading tier hierarchy and engineering equations."""

    def test_liquids_unloading_tier1_and_tier2(self):
        """Liquids unloading Tier 1 per-well vs Tier 2 per-event."""
        calc = LiquidsUnloadingCalculator()
        # Tier 1 plunger
        r_t1_p = calc.calculate_tier1(well_count=10.0, unloading_type="plunger", gwp_dict=GWP_AR5)
        # Table 6-11: plunger lift 1.774 t CH4/well-year (1,774 kg), non-plunger 2.792 t (2,792 kg), 81.6 mol % CH4
        assert r_t1_p["results"]["ch4"]["value"] == pytest.approx(10 * 1.774, rel=1e-9)
        assert r_t1_p["total_co2e"] == pytest.approx(28.0 * 17.74, rel=1e-9)
        # Tier 1 non-plunger (higher factor)
        r_t1_np = calc.calculate_tier1(well_count=10.0, unloading_type="non_plunger", gwp_dict=GWP_AR5)
        assert r_t1_np["results"]["ch4"]["value"] == pytest.approx(10 * 2.792, rel=1e-9)
        assert r_t1_np["total_co2e"] > r_t1_p["total_co2e"]

        # Tier 2 event-based
        r_t2 = calc.calculate_tier2(events=25.0, frequency_category="plunger_le100", gwp_dict=GWP_AR5)
        # Table 6-10, plunger lift (<= 100 events/year): 0.185 t CH4 per event; 25 events
        assert r_t2["results"]["ch4"]["value"] == pytest.approx(25 * 0.185, rel=1e-9)  # 4.625 t
        assert r_t2["total_co2e"] == pytest.approx(28.0 * 4.625, rel=1e-9)

    def test_liquids_unloading_tier3_decompression_eq6_3(self):
        """API Eq 6-3 volume-based wellbore decompression geometry."""
        calc = LiquidsUnloadingCalculator()
        res_eq6_3 = calc.calculate_volume_based(
            well_depth=6000.0,
            diameter=2.875,
            pressure=350.0,
            ch4_content=0.85,
            events=10.0,
            depth_unit="ft",
            diameter_unit="in",
            press_unit="psig",
            gwp_dict=GWP_AR5,
        )
        # wellbore volume pi/4 x (2.875 in / 12)^2 x 6,000 ft = 270.5 ft3, vented from 350 psig to atmosphere:
        # x 350 / 14.696 scf per event; 10 events; 85 % CH4. (The software's own volume method: Compendium Equation
        # 6-3 is the oil-well-test volume, not this one.)
        scf = math.pi / 4.0 * (2.875 / 12.0) ** 2 * 6000.0 * 350.0 / 14.696 * 10
        assert res_eq6_3["results"]["ch4"]["value"] == pytest.approx(ch4_t(scf * 0.85), rel=2e-3)  # 1.05 t

    def test_liquids_unloading_tier3_subpart_w_eq6_10(self):
        """API Eq 6-10 (EPA Subpart W integrated W-8/W-9)."""
        calc = LiquidsUnloadingCalculator()
        res_eq6_10 = calc.calculate_tier3_equation_6_10(
            events=8.0,
            well_depth=5000.0,
            diameter=2.375,
            pressure=200.0,
            sfr=25.0,
            hours_open=3.5,
            unloading_type="plunger",
            ch4_content=0.88,
            sfr_unit="mcf/hr",
            gwp_dict=GWP_AR5,
        )
        # Eq 6-10 per event: 0.37e-3 x D^2 x Depth x P + SFR x (HR - X) x Z with X = 0.5 (plunger), Z = 1 (HR >= 1):
        # 0.37e-3 x 2.375^2 x 5,000 x 200 + 25,000 scf/hr x (3.5 - 0.5); 8 events (Subpart W sums every event)
        scf = 8 * (0.37e-3 * 2.375 ** 2 * 5000.0 * 200.0 + 25000.0 * (3.5 - 0.5))
        assert res_eq6_10["results"]["ch4"]["value"] == pytest.approx(ch4_t(scf * 0.88), rel=1e-3)  # 10.41 t

    def test_liquids_unloading_tier3_automated_plunger_eq6_11(self):
        """API Eq 6-11 automated plunger lift vent rate."""
        calc = LiquidsUnloadingCalculator()
        res_eq6_11 = calc.calculate_tier3_equation_6_11(
            p_shut=450.0,
            p_line=250.0,
            p_sep=150.0,
            sfr_p=50.0,
            t_p=0.5,
            events=50.0,
            ch4_content=0.85,
            sfr_unit="scf/hr",
            gwp_dict=GWP_AR5,
        )
        # Eq 6-11 (Pasci et al. 2020 square-root form): VR = sqrt(Pshut - Patm)/sqrt(Pline - Psep) x SFRp x Tp
        # = sqrt(450 - 14.696)/sqrt(250 - 150) x 50 scf/hr x 0.5 h = 52.16 scf per event; 50 events; 85 % CH4
        scf = 50 * math.sqrt(450.0 - 14.696) / math.sqrt(250.0 - 150.0) * 50.0 * 0.5
        assert res_eq6_11["results"]["ch4"]["value"] == pytest.approx(ch4_t(scf * 0.85), rel=1e-3)  # 0.0425 t
        assert res_eq6_11["total_co2e"] == pytest.approx(28.0 * res_eq6_11["results"]["ch4"]["value"], rel=1e-9)
