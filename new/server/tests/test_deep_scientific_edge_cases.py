"""
Deep Scientific & Boundary Edge Cases Test Suite.
==================================================
Comprehensive empirical verification covering:
1. Extreme Thermodynamic & Fluid-Phase Boundaries (Z-factor, Nm3/Sm3/GOST, P/T limits).
2. Gas Chromatography & Multi-Component Singularities (Non-100% sums, high inerts, sour gas, C6+ splits, microscopic & astronomical bounds).
3. Dynamic Flare & Combustion Boundary Physics (Sub-90% efficiency, methane slip, fractional vs percentage normalization).
4. Multi-Horizon Regulatory GWP Matrices (AR4, AR5, AR6 across 20-yr and 100-yr horizons, mass invariance).
5. Property-Based Fuzz Testing (Hypothesis) across CalculationDispatcher to guarantee zero crashes and zero NaN.
"""

import math
import sys
import pytest
from pathlib import Path
from hypothesis import given, settings, strategies as st

repo_root = str(Path(__file__).resolve().parents[3])
server_dir = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from calculations.units import (
    normalize_gas_volume_to_standard,
    to_kelvin,
    to_celsius,
    to_fahrenheit,
    to_psia,
    from_psia,
    calculate_co2e,
    STD_TEMP_K,
    STD_TEMP_F,
    STD_TEMP_C,
    STD_PRESSURE_PSIA,
    NM3_TO_SM3,
    CONVERSIONS,
    VOLUME_UNITS_TO_M3,
    MASS_UNITS_TO_KG,
)
from calculations.constants import get_active_gwp, GWP_AR4, GWP_AR5, GWP_AR6
from calculations.combustion import CombustionCalculator, FlaringCalculator, _normalize_efficiency
from calculations.combustion_methods import CombustionMethodCalculator, HC_MW, HC_CARBON, HC_HHV_BTU_SCF
from calculations.vented_gas import VentedGasCalculator, _parse_fractions
from calculations.stoichiometry import StoichiometricCalculator
from calculations.dispatcher import CalculationDispatcher


@pytest.fixture(scope="module")
def dispatcher():
    return CalculationDispatcher()


# =============================================================================
# 1. EXTREME THERMODYNAMIC & FLUID-PHASE BOUNDARIES
# =============================================================================

class TestThermodynamicFluidPhaseBoundaries:
    """Tests extreme temperature, pressure, non-standard reference states, and compressibility."""

    def test_z_factor_real_gas_scaling(self):
        """High-pressure gas deviation: Z < 1 increases standard volume, Z > 1 decreases standard volume."""
        vol = 1000.0  # actual m3
        # Ideal gas Z = 1.0
        v_std_ideal = normalize_gas_volume_to_standard(vol, operating_temp=25.0, temp_unit="C", operating_press=100.0, press_unit="psig", z_factor=1.0)
        # Real gas at high pressure near critical point (Z = 0.82)
        v_std_dense = normalize_gas_volume_to_standard(vol, operating_temp=25.0, temp_unit="C", operating_press=100.0, press_unit="psig", z_factor=0.82)
        # Supercritical / repulsive state (Z = 1.15)
        v_std_repulsive = normalize_gas_volume_to_standard(vol, operating_temp=25.0, temp_unit="C", operating_press=100.0, press_unit="psig", z_factor=1.15)

        assert v_std_dense > v_std_ideal
        assert v_std_repulsive < v_std_ideal
        assert pytest.approx(v_std_dense * 0.82, rel=1e-6) == v_std_ideal
        assert pytest.approx(v_std_repulsive * 1.15, rel=1e-6) == v_std_ideal

    def test_z_factor_invalid_inputs_rejected(self):
        """Z-factor must be strictly positive and finite."""
        with pytest.raises(ValueError, match="strictly positive and finite"):
            normalize_gas_volume_to_standard(100.0, z_factor=0.0)
        with pytest.raises(ValueError, match="strictly positive and finite"):
            normalize_gas_volume_to_standard(100.0, z_factor=-0.5)
        with pytest.raises(ValueError, match="is not a number"):
            normalize_gas_volume_to_standard(100.0, z_factor="invalid_z")

    def test_normal_vs_standard_vs_gost_conversions(self):
        """
        API / ISO 13443 Standard: 60°F (15.56°C = 288.71 K)
        Normal m3 (Nm3): 0°C (273.15 K)
        Russian GOST condition: 20°C (293.15 K)
        """
        vol_nm3 = 10_000.0
        # 1 Nm3 at 0°C expands to ~1.05695 Sm3 at 60°F
        sm3_from_nm3 = vol_nm3 * NM3_TO_SM3
        assert sm3_from_nm3 > vol_nm3
        assert pytest.approx(sm3_from_nm3 / vol_nm3, rel=1e-4) == (STD_TEMP_K / 273.15)

        # GOST at 20°C is warmer than standard 15.56°C, so contains fewer standard moles
        gost_temp_k = 20.0 + 273.15
        vol_actual_gost = 10_000.0
        sm3_from_gost = normalize_gas_volume_to_standard(vol_actual_gost, operating_temp=20.0, temp_unit="C", operating_press=0.0, press_unit="psig")
        assert sm3_from_gost < vol_actual_gost
        assert pytest.approx(sm3_from_gost / vol_actual_gost, rel=1e-4) == (STD_TEMP_K / gost_temp_k)

    def test_temperature_boundary_defenses(self):
        """Sub-absolute zero temperatures must be cleanly rejected with descriptive ValueError."""
        with pytest.raises(ValueError, match="below absolute zero"):
            to_kelvin(-274.0, "C")
        with pytest.raises(ValueError, match="below absolute zero"):
            to_kelvin(-460.0, "F")
        with pytest.raises(ValueError, match="below absolute zero"):
            to_kelvin(-1.0, "K")

    def test_pressure_vacuum_boundary_defenses(self):
        """Negative absolute pressure must be rejected."""
        with pytest.raises(ValueError, match="below absolute vacuum"):
            to_psia(-15.0, "psig")  # -15 psig is below 0 psia


# =============================================================================
# 2. GAS CHROMATOGRAPHY & MULTI-COMPONENT BOUNDARIES
# =============================================================================

class TestGasChromatographyAndCompositionBoundaries:
    """Tests non-100% sums, high inerts, sour gas, extended hydrocarbon splits, and magnitude boundaries."""

    def test_gas_composition_sums_and_tolerance(self):
        """Testing allowable vs unphysical GC composition totals."""
        calc = VentedGasCalculator()

        # 1. GC summing to 99.0% (within tolerance due to trace inerts or rounding)
        inputs_99 = {
            "gas_volume": 100_000,
            "gas_volume_unit": "scf",
            "ch4_content": "80.0",
            "co2_content": "15.0",
            "c2plus_content": "4.0",
        }
        res_99 = calc.calculate("volume", inputs_99)
        assert res_99["results"]["ch4"]["value"] > 0
        assert res_99["results"]["co2"]["value"] > 0

        # 2. GC exceeding physical 100.01% limit must be rejected
        inputs_over = {
            "gas_volume": 100_000,
            "gas_volume_unit": "scf",
            "ch4_content": "85.0",
            "co2_content": "15.0",
            "c2plus_content": "5.0",  # Sum = 105%
        }
        with pytest.raises(ValueError, match="exceeds 100"):
            calc.calculate("volume", inputs_over)

    def test_high_inert_sour_gas_stream(self):
        """High CO2 sour gas stream (e.g. 95% CO2 acid gas, 5% CH4)."""
        calc = VentedGasCalculator()
        inputs_sour = {
            "gas_volume": 50_000,
            "gas_volume_unit": "m3",
            "ch4_content": "5.0",
            "co2_content": "95.0",
            "c2plus_content": "0.0",
            "disposition": "vented",
        }
        res = calc.calculate("volume", inputs_sour)
        # CO2 mass should dominate CH4 mass
        co2_mass = res["results"]["co2"]["value"]
        ch4_mass = res["results"]["ch4"]["value"]
        assert co2_mass > ch4_mass * 10.0
        assert res["total_co2e"] > 0.0

    def test_extended_hydrocarbon_splits_c6plus(self):
        """Exhibit 5.2 / Exhibit 5.3: Extended C1 through C6+ hydrocarbon weighting."""
        calc = CombustionMethodCalculator()
        inputs = {
            "voc_mass": 10.0,  # 10 tonnes VOC emitted
            "voc_mass_unit": "t",
            "combustion_efficiency": "98",
            "wt_ch4": "80.0",
            "wt_c2h6": "8.0",
            "wt_c3h8": "4.0",
            "wt_c4h10": "3.0",
            "wt_c5h12": "2.0",
            "wt_c6plus": "1.0",
            "wt_co2": "2.0",
        }
        res = calc.calculate("flare_voc", inputs)
        inter = res["intermediate"]
        # Hydrocarbon average molecular weight and heating value must be calculated
        assert inter["hc_mw"] > 16.04  # Higher than pure methane due to heavy ends
        assert inter["hc_hhv_btu_scf"] > 1010.0
        assert res["results"]["co2"]["value"] > 0.0
        assert res["results"]["ch4"]["value"] > 0.0

    def test_microscopic_and_astronomical_quantities(self):
        """Engine stability under microscopic (1e-9) and astronomical (1e12) quantities."""
        calc = CombustionCalculator()

        # Microscopic: should compute tiny positive float without underflow exception
        r_micro = calc.calculate(1e-9, ef_co2=53.06, ef_ch4=0.001, ef_n2o=0.0001, ef_unit="kg/MMBtu", fuel_unit="m3", fuel_type="natural_gas", hhv=1020.0)
        assert r_micro["total_co2e"] > 0.0
        assert math.isfinite(r_micro["total_co2e"])

        # Astronomical: should compute large float without overflow exception or NaN
        r_astro = calc.calculate(1e12, ef_co2=53.06, ef_ch4=0.001, ef_n2o=0.0001, ef_unit="kg/MMBtu", fuel_unit="m3", fuel_type="natural_gas", hhv=1020.0)
        assert r_astro["total_co2e"] > 1e6
        assert math.isfinite(r_astro["total_co2e"])


# =============================================================================
# 3. DYNAMIC FLARE & COMBUSTION BOUNDARY PHYSICS
# =============================================================================

class TestDynamicFlareAndCombustionBoundaries:
    """Tests sub-90% flare efficiency, flame lift-off methane slip, and ambiguous efficiency inputs."""

    @pytest.mark.parametrize("eff_val, expected_fraction", [
        (0.98, 0.98),
        (98.0, 0.98),
        ("98", 0.98),
        ("98%", 0.98),
        (0.60, 0.60),
        ("60%", 0.60),
        (0.005, 0.005),
    ])
    def test_efficiency_normalization_consistency(self, eff_val, expected_fraction):
        """Normalizes ratios and percentages consistently."""
        norm = _normalize_efficiency(eff_val)
        assert pytest.approx(norm, rel=1e-5) == expected_fraction

    def test_flare_methane_slip_under_wind_shear(self):
        """
        API Compendium §5.2 / EPA 40 CFR 60.18:
        When flare efficiency drops from 98% down to 60% due to cross-winds or flame lift-off:
        Uncombusted methane slip = (1 - DE).
        At 98% DE: Slip = 2.0%
        At 60% DE: Slip = 40.0%
        Methane emissions increase by exactly 40% / 2% = 20.0x!
        """
        calc = VentedGasCalculator()
        vol = 1_000_000.0  # 1 MMscf

        inputs_98 = {
            "gas_volume": vol,
            "gas_volume_unit": "scf",
            "ch4_content": "90.0",
            "co2_content": "5.0",
            "c2plus_content": "5.0",
            "disposition": "flared",
            "combustion_efficiency": "98",
        }
        res_98 = calc.calculate("volume", inputs_98)

        inputs_60 = {
            "gas_volume": vol,
            "gas_volume_unit": "scf",
            "ch4_content": "90.0",
            "co2_content": "5.0",
            "c2plus_content": "5.0",
            "disposition": "flared",
            "combustion_efficiency": "60",
        }
        res_60 = calc.calculate("volume", inputs_60)

        ch4_98 = res_98["results"]["ch4"]["value"]
        ch4_60 = res_60["results"]["ch4"]["value"]
        co2_98 = res_98["results"]["co2"]["value"]
        co2_60 = res_60["results"]["co2"]["value"]

        # Exact 20.0x methane slip multiplier
        assert pytest.approx(ch4_60 / ch4_98, rel=1e-4) == 20.0
        # CO2 decreases because less carbon is oxidized
        assert co2_60 < co2_98


# =============================================================================
# 4. MULTI-HORIZON REGULATORY GWP MATRICES
# =============================================================================

class TestMultiHorizonRegulatoryGWP:
    """Tests IPCC AR4, AR5, AR6 across 100-yr and 20-yr horizons and mass invariance."""

    def test_physical_gas_mass_invariance_across_gwp(self):
        """Physical metric tonnes of CO2, CH4, and N2O MUST NOT CHANGE when GWP profile changes."""
        calc = CombustionCalculator()
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}

        gwp_ar4 = get_active_gwp("AR4", horizon="100")
        gwp_ar5 = get_active_gwp("AR5", horizon="100")
        gwp_ar6 = get_active_gwp("AR6", horizon="100")

        r_ar4 = calc.calculate(100_000, ef_co2=53.06, ef_ch4=0.001, ef_n2o=0.0001, ef_unit="kg/MMBtu", fuel_unit="m3", fuel_type="natural_gas", hhv=1020.0, gwp_dict=gwp_ar4)
        r_ar5 = calc.calculate(100_000, ef_co2=53.06, ef_ch4=0.001, ef_n2o=0.0001, ef_unit="kg/MMBtu", fuel_unit="m3", fuel_type="natural_gas", hhv=1020.0, gwp_dict=gwp_ar5)
        r_ar6 = calc.calculate(100_000, ef_co2=53.06, ef_ch4=0.001, ef_n2o=0.0001, ef_unit="kg/MMBtu", fuel_unit="m3", fuel_type="natural_gas", hhv=1020.0, gwp_dict=gwp_ar6)

        # Physical mass identical across all standards
        assert r_ar4["results"]["co2"]["value"] == r_ar5["results"]["co2"]["value"] == r_ar6["results"]["co2"]["value"]
        assert r_ar4["results"]["ch4"]["value"] == r_ar5["results"]["ch4"]["value"] == r_ar6["results"]["ch4"]["value"]
        assert r_ar4["results"]["n2o"]["value"] == r_ar5["results"]["n2o"]["value"] == r_ar6["results"]["n2o"]["value"]

        # Pure methane CO2e is strictly monotonic across assessment reports: AR6 (29.8) > AR5 (28.0) > AR4 (25.0)
        co2e_ch4_ar4 = calculate_co2e(ch4=10.0, gwp_dict=gwp_ar4)
        co2e_ch4_ar5 = calculate_co2e(ch4=10.0, gwp_dict=gwp_ar5)
        co2e_ch4_ar6 = calculate_co2e(ch4=10.0, gwp_dict=gwp_ar6)
        assert co2e_ch4_ar6 > co2e_ch4_ar5 > co2e_ch4_ar4

        # In multi-gas combustion, AR4 CO2e can exceed AR5 when N2O reduction (298 -> 265) outweighs CH4 increase (25 -> 28)
        m_ch4 = r_ar5["results"]["ch4"]["value"]
        m_n2o = r_ar5["results"]["n2o"]["value"]
        expected_diff = (m_n2o * (298 - 265)) - (m_ch4 * (28 - 25))
        actual_diff = r_ar4["total_co2e"] - r_ar5["total_co2e"]
        assert pytest.approx(actual_diff, rel=1e-5) == expected_diff
        assert r_ar6["total_co2e"] > r_ar5["total_co2e"]

    def test_twenty_year_methane_forcing_impact(self):
        """20-year horizon magnifies methane CO2e by 84/28 = 3.0x under AR5."""
        ch4_tonnes = 10.0
        co2e_100 = calculate_co2e(ch4=ch4_tonnes, gwp_dict=get_active_gwp("AR5", horizon="100"))
        co2e_20 = calculate_co2e(ch4=ch4_tonnes, gwp_dict=get_active_gwp("AR5", horizon="20"))

        assert pytest.approx(co2e_20 / co2e_100, rel=1e-5) == 3.0


# =============================================================================
# 5. PROPERTY-BASED FUZZ TESTING (HYPOTHESIS)
# =============================================================================

class TestPropertyBasedFuzzing:
    """Hypothesis-driven fuzz testing of core dispatchers to guarantee zero crashes and mathematical invariants."""

    @settings(max_examples=60, deadline=None)
    @given(
        qty=st.floats(min_value=0.01, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
        hhv=st.floats(min_value=500.0, max_value=2500.0, allow_nan=False, allow_infinity=False),
        eff=st.floats(min_value=50.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    )
    def test_combustion_fuzz_invariants(self, dispatcher, qty, hhv, eff):
        """Fuzz testing stationary combustion with randomized quantities, HHVs, and efficiencies."""
        ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        params = {
            "quantity": qty,
            "unit": "m3",
            "fuel_type": "natural_gas",
            "hhv": hhv,
            "combustion_efficiency": eff,
            "factor_source": "default",
        }
        res = dispatcher.dispatch("stationary_combustion", params, ef, {}, gwp_dict=GWP_AR5)

        # Invariants:
        assert res["total_co2e"] > 0.0
        assert math.isfinite(res["total_co2e"])
        assert not math.isnan(res["total_co2e"])
        assert res["results"]["co2"]["value"] >= 0.0
        assert res["results"]["ch4"]["value"] >= 0.0

    @settings(max_examples=50, deadline=None)
    @given(
        temp_c=st.floats(min_value=-50.0, max_value=250.0, allow_nan=False, allow_infinity=False),
        press_psig=st.floats(min_value=0.0, max_value=2000.0, allow_nan=False, allow_infinity=False),
        z_fact=st.floats(min_value=0.70, max_value=1.30, allow_nan=False, allow_infinity=False),
    )
    def test_thermodynamic_fuzz_invariants(self, temp_c, press_psig, z_fact):
        """Fuzz testing thermodynamic normalization across wide operational envelopes."""
        vol_actual = 5000.0
        v_std = normalize_gas_volume_to_standard(
            volume=vol_actual,
            operating_temp=temp_c,
            temp_unit="C",
            operating_press=press_psig,
            press_unit="psig",
            z_factor=z_fact,
        )
        assert v_std > 0.0
        assert math.isfinite(v_std)
        assert not math.isnan(v_std)
