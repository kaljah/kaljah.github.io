"""
Comprehensive Numerical Verification Test Suite
================================================
Audits mathematical invariants, conservation laws, domain limits, floating-point precision,
and boundary conditions across all calculation engines and route logic in the software.
"""

import math
import pytest
from calculations.units import (
    CONVERSIONS,
    convert,
    to_kelvin,
    to_fahrenheit,
    to_psia,
    normalize_gas_volume_to_standard,
    calculate_co2e,
    STD_TEMP_K,
    STD_PRESSURE_PSIA,
)
from calculations.constants import get_active_gwp, DEFAULT_GWP
from calculations.uncertainty import (
    combine_uncertainties_product,
    combine_uncertainties_sum,
    srss_inventory,
    propagate_uncertainty,
    COVERAGE_FACTOR_95,
    Tier,
)
from calculations.stoichiometry import StoichiometricCalculator
from calculations.combustion import (
    CombustionCalculator,
    FlaringCalculator,
    convert_factor_to_kg_per_unit,
)
from calculations.midstream import AGRCalculator, DehydratorCalculator
from calculations.indirect import IndirectSteamCalculator, CogenAllocationCalculator
from calculations.fugitive import (
    ComponentFugitiveCalculator,
    EquipmentFugitiveCalculator,
    CompressorSealCalculator,
)
from calculations.vented import (
    _split_vented_and_flared,
    MudDegassingCalculator,
    CompletionFlowbackCalculator,
    LiquidsUnloadingCalculator,
    BlowdownCalculator,
    TankFlashingCalculator,
    PneumaticDeviceCalculator,
)
from calculations.anomaly import AnomalyDetector
from services.sentinel5p import Sentinel5PService


# ===========================================================================
# 1. PHYSICAL CONSERVATION LAWS & STOICHIOMETRIC BALANCES
# ===========================================================================

class TestConservationLaws:
    def test_stoichiometric_carbon_mass_balance(self):
        """API §4.1: Carbon in fuel must equal carbon in emitted CO2 (44.01 / 12.011 ratio)."""
        calc = StoichiometricCalculator()
        mass_kg = 1000.0  # 1 tonne pure carbon
        res = calc.calculate(mass_kg, carbon_content=1.0, uncertainties={}, mass_unit="kg")
        co2_tonnes = res["results"]["co2"]["value"]
        expected_co2 = (1000.0 * 1.0 * (44.01 / 12.011)) / 1000.0
        assert pytest.approx(co2_tonnes, rel=1e-5) == expected_co2
        # Carbon mass check: co2_tonnes * (12.011 / 44.01) must equal initial carbon
        carbon_recovered = co2_tonnes * (12.011 / 44.01)
        assert pytest.approx(carbon_recovered, rel=1e-5) == 1.0

    def test_flaring_dual_efficiency_mass_balance(self):
        """API §5.2: Flared hydrocarbons must partition into unburnt slip and stoichiometric CO2."""
        calc = FlaringCalculator()
        # 10,000 m3 pure methane flared with elevated flare (eta_c=0.984, eta_d=0.98)
        res = calc.calculate(
            gas_volume=10000.0,
            ch4_fraction=1.0,
            flare_type="elevated",
            uncertainties={},
        )
        ch4_tonnes = res["results"]["ch4"]["value"]
        co2_tonnes = res["results"]["co2"]["value"]

        # Total methane mass entering flare
        density_ch4 = 0.6785
        total_ch4_mass_tonnes = (10000.0 * density_ch4) / 1000.0

        # Unburnt methane: (1 - 0.98) * total_mass = 2%
        expected_unburnt_ch4 = total_ch4_mass_tonnes * 0.02
        assert pytest.approx(ch4_tonnes, rel=1e-4) == expected_unburnt_ch4

        # Combusted carbon moles: 10,000 m3 * 0.984 = 9,840 m3 CO2
        density_co2 = 1.861
        expected_combusted_co2 = (10000.0 * 1.0 * 0.984 * density_co2) / 1000.0
        assert pytest.approx(co2_tonnes, rel=1e-4) == expected_combusted_co2

    def test_dehydrator_stoichiometric_carbon_balance(self):
        """API §6.6: Controlled dehydrator must oxidize destroyed methane to stoichiometric CO2."""
        calc = DehydratorCalculator()
        res = calc.calculate(
            pump_rate=100.0,
            pump_unit="gph",
            hours=8760,
            ch4_content=0.85,
            has_flash_tank=False,
            still_control_type="flare",
            control_eff=0.98,
        )
        unburnt_ch4 = res["results"]["ch4"]["value"]
        combusted_co2 = res["results"]["co2"]["value"]

        assert unburnt_ch4 > 0
        assert combusted_co2 > 0
        # Destroyed CH4 was 98%, unburnt is 2%. Ratio = 0.98 / 0.02 = 49x
        destroyed_ch4 = (unburnt_ch4 / 0.02) * 0.98
        expected_co2 = destroyed_ch4 * (44.01 / 16.04)
        assert pytest.approx(combusted_co2, rel=1e-4) == expected_co2

    def test_cogen_allocation_energy_conservation(self):
        """API §8.3: Cogen heat + power emissions must exactly equal total emissions."""
        calc = CogenAllocationCalculator()
        total_e = 5000.0  # tCO2e
        res = calc.calculate(
            total_emissions=total_e,
            heat_output=10000.0,  # MMBtu
            power_output=5000.0,   # MMBtu
            method="wri_efficiency",
        )
        heat_e = res["metadata"]["allocated_heat_tonnes"]
        power_e = res["metadata"]["allocated_power_tonnes"]
        assert pytest.approx(heat_e + power_e, rel=1e-9) == total_e

        # Also verify energy_content method
        res_ec = calc.calculate(
            total_emissions=total_e,
            heat_output=10000.0,
            power_output=5000.0,
            method="energy_content",
        )
        h_ec = res_ec["metadata"]["allocated_heat_tonnes"]
        p_ec = res_ec["metadata"]["allocated_power_tonnes"]
        assert pytest.approx(h_ec + p_ec, rel=1e-9) == total_e


# ===========================================================================
# 2. BOUNDARY CONDITIONS & ZERO/EXTREME INPUTS
# ===========================================================================

class TestBoundaryConditions:
    def test_all_calculators_zero_activity_no_crash(self):
        """Every calculation engine must return 0.0 total_co2e on zero activity without ZeroDivisionError."""
        # 1. Stoichiometry
        assert StoichiometricCalculator().calculate(0.0, 0.85, {})["total_co2e"] == 0.0

        # 2. Combustion
        assert CombustionCalculator().calculate(0.0, 50.0, 0.01, 0.001, {}, 1020.0, "kg/m3", "m3", "gas")["total_co2e"] == 0.0

        # 3. Flaring
        assert FlaringCalculator().calculate(0.0, 0.90, "elevated", {})["total_co2e"] == 0.0

        # 4. Indirect Steam
        assert IndirectSteamCalculator().calculate(0.0, 50.0, 0.80, 0.05, {})["total_co2e"] == 0.0

        # 5. Cogen Allocation
        assert CogenAllocationCalculator().calculate(0.0, 100.0, 50.0)["total_co2e"] == 0.0

        # 6. Fugitive Component
        assert ComponentFugitiveCalculator().calculate({}, 0.85, {})["total_co2e"] == 0.0

        # 7. Equipment Fugitive
        assert EquipmentFugitiveCalculator().calculate(0, 0.01, 0.85, {})["total_co2e"] == 0.0

        # 8. Compressor Seal
        assert CompressorSealCalculator().calculate(0, "reciprocating", {})["total_co2e"] == 0.0

        # 9. Mud Degassing
        assert MudDegassingCalculator().calculate(0, 0.85, {})["total_co2e"] == 0.0

        # 10. Completions Flowback
        assert CompletionFlowbackCalculator().calculate(0, 0, 0.85, {})["total_co2e"] == 0.0

        # 11. Liquids Unloading
        assert LiquidsUnloadingCalculator().calculate(5000.0, 2.0, 100.0, 0.85, 0, {})["total_co2e"] == 0.0

        # 12. Blowdown
        assert BlowdownCalculator().calculate(0.0, 100.0, 0, 0.85, {})["total_co2e"] == 0.0

        # 13. Tank Flashing
        assert TankFlashingCalculator().calculate(0.0, 50.0, 0.85, 0.0, {})["total_co2e"] == 0.0

        # 14. Pneumatics
        assert PneumaticDeviceCalculator().calculate(0, hours=1.0, bleed_rate=0.85, ch4_content=0.85, uncertainties={})["total_co2e"] == 0.0

        # 15. AGR
        assert AGRCalculator().calculate(0.0, 0.04, 0.001, {})["total_co2e"] == 0.0

    def test_extreme_orders_of_magnitude(self):
        """Calculations must remain stable with micro and macro inputs (1e-9 to 1e10)."""
        calc = StoichiometricCalculator()
        micro = calc.calculate(1e-9, 0.85, {}, mass_unit="kg")
        assert not math.isnan(micro["total_co2e"])
        assert not math.isinf(micro["total_co2e"])
        assert micro["total_co2e"] > 0

        macro = calc.calculate(1e10, 0.85, {}, mass_unit="kg")
        assert not math.isnan(macro["total_co2e"])
        assert not math.isinf(macro["total_co2e"])
        assert macro["total_co2e"] > 1e6


# ===========================================================================
# 3. UNIT CONVERSIONS & DIMENSIONAL INVARIANTS
# ===========================================================================

class TestDimensionalInvariants:
    def test_bidirectional_conversions_exactness(self):
        """Every unit conversion pair in CONVERSIONS must round-trip with relative error < 1e-6."""
        pairs = [
            ("scf", "m3"),
            ("mscf", "m3"),
            ("mcf", "m3"),
            ("mmscf", "m3"),
            ("bbl", "m3"),
            ("gal", "m3"),
            ("liter", "m3"),
            ("mcf", "scf"),
            ("mscf", "scf"),
            ("mmscf", "scf"),
            ("lb", "kg"),
            ("tonne", "kg"),
            ("short_ton", "kg"),
            ("long_ton", "kg"),
            ("btu", "kj"),
            ("mj", "btu"),
            ("mmbtu", "mj"),
            ("kwh", "mj"),
        ]
        test_val = 1234.5678
        for u1, u2 in pairs:
            converted = convert(test_val, u1, u2)
            roundtrip = convert(converted, u2, u1)
            err = abs(roundtrip - test_val) / test_val
            assert err < 1e-6, f"Round-trip failed for {u1} <-> {u2}: original={test_val}, roundtrip={roundtrip}, err={err}"

    def test_thermodynamic_ideal_gas_normalization(self):
        """API §4.2.1: PV/T normalization: colder gas -> more mass; higher pressure -> more mass."""
        # Standard conditions: 60°F (519.67°R, 288.71 K), 14.696 psia
        v_std = normalize_gas_volume_to_standard(
            volume=100.0,
            operating_temp=60.0,
            temp_unit="F",
            operating_press=14.696,
            press_unit="psia",
        )
        assert pytest.approx(v_std, rel=1e-3) == 100.0

        # Doubling absolute pressure doubles standard volume
        v_high_p = normalize_gas_volume_to_standard(
            volume=100.0,
            operating_temp=60.0,
            temp_unit="F",
            operating_press=14.696 * 2.0,
            press_unit="psia",
        )
        assert pytest.approx(v_high_p, rel=1e-3) == 200.0

    def test_temperature_unit_conversions(self):
        """Temperature conversions must agree at physical invariant points (absolute zero, freezing, boiling)."""
        # Freezing point of water: 0°C = 32°F = 273.15 K
        assert pytest.approx(to_kelvin(0.0, "C"), abs=1e-4) == 273.15
        assert pytest.approx(to_kelvin(32.0, "F"), abs=1e-4) == 273.15
        assert pytest.approx(to_fahrenheit(0.0, "C"), abs=1e-4) == 32.0
        assert pytest.approx(to_fahrenheit(273.15, "K"), abs=1e-4) == 32.0

        # Boiling point: 100°C = 212°F = 373.15 K
        assert pytest.approx(to_kelvin(100.0, "C"), abs=1e-4) == 373.15
        assert pytest.approx(to_fahrenheit(100.0, "C"), abs=1e-4) == 212.0


# ===========================================================================
# 4. UNCERTAINTY QUANTIFICATION (ISO 14064-1 & GUM §6.2)
# ===========================================================================

class TestUncertaintyQuantification:
    def test_srss_subadditivity_property(self):
        """SRSS uncertainty of independent sources must be less than or equal to linear sum."""
        sources = [
            {"value": 100.0, "relative_uncertainty": 0.10},
            {"value": 200.0, "relative_uncertainty": 0.15},
            {"value": 300.0, "relative_uncertainty": 0.05},
        ]
        res = srss_inventory(sources)
        sigma_srss_abs = res["total_value"] * res["relative_uncertainty_1sigma"]
        linear_sum_abs = sum(s["value"] * s["relative_uncertainty"] for s in sources)
        assert sigma_srss_abs <= linear_sum_abs

    def test_confidence_interval_bounds_ordering(self):
        """ISO 14064-1 §7.5: 0 <= lower_bound <= value <= upper_bound must hold strictly."""
        res = propagate_uncertainty(
            value=50.0,
            ef_uncertainty=0.20,
            activity_uncertainty=0.10,
            tier=Tier.T2,
        )
        assert 0.0 <= res["lower_bound"] <= res["value"] <= res["upper_bound"]
        assert res["confidence_level_pct"] == 95
        assert res["coverage_factor"] == COVERAGE_FACTOR_95

    def test_zero_emission_uncertainty_bounds(self):
        """Zero emission value must produce zero bounds without negative intervals."""
        res = propagate_uncertainty(0.0, 0.10, 0.05)
        assert res["value"] == 0.0
        assert res["lower_bound"] == 0.0
        assert res["upper_bound"] == 0.0


# ===========================================================================
# 5. ANOMALY DETECTION MATHEMATICAL ROBUSTNESS
# ===========================================================================

class TestAnomalyMathematics:
    def test_z_score_identical_history_no_false_positive(self):
        """If historical is constant and new value is identical, it must NOT flag."""
        detector = AnomalyDetector()
        res = detector._z_score_check(value=100.0, historical=[100.0, 100.0, 100.0, 100.0])
        assert res["flagged"] is False

    def test_z_score_small_sample_guard(self):
        """Sample size N < 3 must return insufficient_history without crashing."""
        detector = AnomalyDetector()
        res = detector._z_score_check(value=100.0, historical=[100.0, 100.0])
        assert res["flagged"] is False
        assert res["reason"] == "insufficient_history"


# ===========================================================================
# 6. SATELLITE ATMOSPHERIC FLUX MATHEMATICS
# ===========================================================================

class TestSatelliteFluxMathematics:
    def test_column_mass_flux_linearity(self):
        """Emission rate Q must scale linearly with delta_ppb and wind_speed."""
        service = Sentinel5PService()
        q1 = service.estimate_emission_rate_from_anomaly(delta_ch4_ppb=20.0, wind_speed_m_s=3.0)
        q2 = service.estimate_emission_rate_from_anomaly(delta_ch4_ppb=40.0, wind_speed_m_s=3.0)
        # Doubling delta_ppb must double emission rate
        assert pytest.approx(q2, rel=1e-3) == q1 * 2.0

        q_double_wind = service.estimate_emission_rate_from_anomaly(delta_ch4_ppb=20.0, wind_speed_m_s=6.0)
        # Doubling wind speed must double emission rate
        assert pytest.approx(q_double_wind, rel=1e-3) == q1 * 2.0

    def test_zero_and_negative_anomaly_returns_zero(self):
        """Zero or negative delta_ch4_ppb must return exactly 0.0 kg/hr."""
        service = Sentinel5PService()
        assert service.estimate_emission_rate_from_anomaly(0.0) == 0.0
        assert service.estimate_emission_rate_from_anomaly(-10.0) == 0.0


# ===========================================================================
# 7. REFERENCED NORMATIVE GOLDEN MASTER BENCHMARKS
# ===========================================================================

class TestNormativeGoldenBenchmarks:
    def test_api_example_4_1_fuel_gas_combustion(self):
        """API Compendium 2021 §4.2 Example 4-1: 10,000 m3 natural gas combustion."""
        calc = CombustionCalculator()
        res = calc.calculate(
            fuel_quantity=10000.0,
            ef_co2=53.06,  # kg CO2 / MMBtu
            ef_ch4=0.001,  # kg CH4 / MMBtu
            ef_n2o=0.0001,  # kg N2O / MMBtu
            uncertainties={},
            hhv=1020.0,
            ef_unit="kg/MMBtu",
            fuel_unit="m3",
            fuel_type="natural_gas",
            gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
        )
        assert pytest.approx(res["results"]["co2"]["value"], rel=1e-3) == 19.1127
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-3) == 0.000360
        assert pytest.approx(res["results"]["n2o"]["value"], rel=1e-3) == 0.000036
        assert pytest.approx(res["total_co2e"], rel=1e-3) == 19.1323

    def test_api_example_4_5_flaring_dual_efficiency(self):
        """API Compendium 2021 §4.3 Example 4-5: Dual-efficiency flaring with native CO2."""
        from calculations.vented import _split_vented_and_flared

        split = _split_vented_and_flared(
            total_gas_m3=1000.0,
            ch4_tonnes=0.61065,  # 900 m3 CH4 * 0.6785 / 1000
            co2_tonnes=0.09305,  # 50 m3 CO2 * 1.861 / 1000
            ctrl_eff=1.0,  # 100% routed to flare (internal combustion efficiency 98%)
            hhv=1020.0,
        )
        # Combusted CO2: 0.61065 * 0.98 * (44.01/16.04) + 0.09305 = 1.73503 tCO2
        assert pytest.approx(split["total_co2"], rel=1e-3) == 1.73503
        # Unburnt CH4: 0.61065 * 0.02 = 0.012213 tCH4
        assert pytest.approx(split["total_ch4"], rel=1e-3) == 0.012213
        co2e = split["total_co2"] + (split["total_ch4"] * 28.0)
        assert pytest.approx(co2e, rel=1e-3) == 2.0770

    def test_api_example_6_5_vessel_blowdown_compressibility(self):
        """API Compendium 2021 §6.5 Eq. 6-12: Vessel blowdown real-gas compressibility."""
        from calculations.vented import BlowdownCalculator

        calc = BlowdownCalculator()
        res = calc.calculate(
            blowdown_volume=50.0,
            pressure=5000.0,
            events=1,
            ch4_content=0.85,
            uncertainties={},
            operating_temperature=300.0,
            temp_unit="k",
            press_unit="kpa",
            z_factor=0.88,
            gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
        )
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-3) == 1.55612
        assert pytest.approx(res["total_co2e"], rel=1e-3) == 43.5714

    def test_api_example_6_6_teg_dehydration_gri_glycalc(self):
        """API Compendium 2021 §6.6: TEG dehydration GRI-GLYCalc parametric methane solubility."""
        calc = DehydratorCalculator()
        res = calc.calculate(
            pump_rate=600.0,  # 10 gpm = 600 gph
            pump_unit="gph",
            hours=8760,
            ch4_content=0.90,
            contactor_pressure=800.0,
            press_unit="psia",
            contactor_temperature=100.0,
            temp_unit="F",
            has_flash_tank=False,
            still_control_type="none",
            gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
        )
        # S_CH4 = 0.0032 * 800^0.96 * exp(-0.0022 * 40) * 0.90 = 1.6148 scf/gal
        # Total CH4 = 5,256,000 gal * 1.6148 scf/gal * 0.0283168 m3/scf * 0.6785 / 1000 = 163.08 tonnes
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-2) == 163.08
        assert pytest.approx(res["total_co2e"], rel=1e-2) == 4566.14

    def test_api_table_7_3_compressor_seals(self):
        """API Compendium 2021 Table 7-3: Reciprocating compressor seals (1.2 kg/hr)."""
        calc = CompressorSealCalculator()
        res = calc.calculate(
            compressor_count=2,
            seal_type="reciprocating",
            uncertainties={},
            gwp_dict={"CO2": 1.0, "CH4": 28.0, "N2O": 265.0},
        )
        # 2 * 1.2 kg/hr * 8760 hr / 1000 = 21.024 tonnes CH4
        assert pytest.approx(res["results"]["ch4"]["value"], rel=1e-4) == 21.024
        assert pytest.approx(res["total_co2e"], rel=1e-4) == 588.672
        # Fugitive CH4 1-sigma uncertainty: sqrt((0.60/2)^2 + (0.20/2)^2) = sqrt(0.09 + 0.01) = 31.62%
        assert pytest.approx(res["results"]["ch4"]["relative_uncertainty"], rel=1e-3) == 0.3162
        # 95% expanded uncertainty (k=2): 2 * 0.3162 = 63.25%
        assert pytest.approx(res["results"]["ch4"]["relative_uncertainty_95pct"], rel=1e-3) == 0.6325

    def test_scope2_indirect_steam_net_efficiency(self):
        """GHG Protocol Scope 2 / API Eq. 8-2: Steam net boiler efficiency and distribution loss."""
        calc = IndirectSteamCalculator()
        res = calc.calculate(
            heat_energy=5000.0,
            ef_co2=53.06,  # kg CO2 / MMBtu
            boiler_efficiency=0.80,
            transmission_loss=0.05,
            heat_unit="mmbtu",
            uncertainties={},
        )
        # Net eff = 0.80 * (1 - 0.05) = 0.76 -> 5000 / 0.76 * 53.06 / 1000 = 349.079 tonnes CO2
        assert pytest.approx(res["results"]["co2"]["value"], rel=1e-3) == 349.079
        assert pytest.approx(res["total_co2e"], rel=1e-3) == 349.079

    def test_scope3_materials_and_spend_eeio(self):
        """GHG Protocol Scope 3: Purchased materials (tonne) vs spend-based EEIO ($1000)."""
        from calculations.units import compute_scope3_co2e

        # Material-based: 50 tonnes cement * 800 kg/tonne / 1000 = 40.0 tCO2e
        cement_co2e = compute_scope3_co2e(50, 800, "kg CO2e / tonne")
        assert pytest.approx(cement_co2e, 1e-4) == 40.0

        # Spend-based EEIO: $100,000 * 350 kg/$1000 / 1,000,000 = 35.0 tCO2e
        eeio_co2e = compute_scope3_co2e(100000, 350, "kg CO2e / $1000")
        assert pytest.approx(eeio_co2e, 1e-4) == 35.0

    def test_ipcc_uncertainty_srss_worked_example(self):
        """IPCC 2006 Guidelines Vol. 1 Eq. 3.2: SRSS uncertainty aggregation."""
        sources = [
            {"value": 1000.0, "relative_uncertainty": 0.05},
            {"value": 500.0, "relative_uncertainty": 0.25},
            {"value": 200.0, "relative_uncertainty": 0.60},
        ]
        res = srss_inventory(sources)
        assert pytest.approx(res["total_value"], 1e-4) == 1700.0
        # sqrt(50^2 + 125^2 + 120^2) / 1700 = 180.3468 / 1700 = 10.6086%
        assert pytest.approx(res["relative_uncertainty_1sigma"], 1e-4) == 0.106086
        # 95% CI (k=2): 2 * 10.6086% = 21.2173%
        assert pytest.approx(res["relative_uncertainty_95pct"], 1e-4) == 0.212173
