"""
Deep Forensic Unit Tests for Previously Untested Calculation Paths - Part 6.

Focuses on:
1. Anomaly detection & plausibility check: NaN, inf, extreme negative bounds, negative mean range ordering, IQR fences.
2. Control efficiency normalization in tank flashing, acid gas removal, and blowdown calculators.
3. Pneumatic devices & dehydration bounds: non-negative dehydrator counts, physical actuation model (Eq. 6-13).
4. Compressor seal fugitives: negative measured rate guards, processing, transmission, and production factors.
5. Production non-routine venting: PRV / ESD releases with zero methane (pure CO2 / acid gas streams).
6. Dispatcher string percentage uncertainty handling & CCS capture rate with % symbol.
7. Liquids unloading Tier 3 automated plunger (Eq. 6-11) pressure ratio mechanics and boundary enforcement.
8. Tier 3B correlation equations with mixed screening values, non-detects, and pegged counts.
9. Combustion Tier 3 liquid and solid fuel carbon mass balance (API Compendium Eq. 4-5 / Exhibit 4.5).
10. Legacy engine fallback execution with custom specific factors and missing factor error handling.
"""

import math
import pytest

from calculations.anomaly import AnomalyDetector, plausibility_check
from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.dispatcher import CalculationDispatcher
from calculations.fugitive import CompressorSealCalculator, ComponentFugitiveCalculator, EquipmentFugitiveCalculator
from calculations.fugitive_onshore import (
    OnshoreScreeningMeasurementCalculator,
    convert_fugitive_flow_to_kg_hr,
)
from calculations.legacy_engine import compute_emissions, MissingFactorError
from calculations.vented_production_pneumatic import GasDehydrationCalculator, PneumaticDeviceCalculator
from calculations.vented_production_tank import (
    AcidGasRemovalCalculator,
    BlowdownCalculator,
    TankFlashingCalculator,
)
from calculations.vented_production_wells import ProductionNonRoutineVentingCalculator
from calculations.vented_unloading import LiquidsUnloadingCalculator


def test_plausibility_check_nan_inf_and_extreme_negative():
    """Verify Bug 11 fix: plausibility_check rejects NaN, Inf, and extreme negative emissions."""
    # NaN must be rejected
    verdict, msg = plausibility_check(float("nan"))
    assert verdict == "reject"
    assert "not a valid finite number" in msg

    # Positive and negative infinity must be rejected
    verdict, msg = plausibility_check(float("inf"))
    assert verdict == "reject"
    assert "not a valid finite number" in msg

    verdict, msg = plausibility_check(float("-inf"))
    assert verdict == "reject"
    assert "not a valid finite number" in msg

    # Extreme negative emission exceeding reject bound (e.g. -200 million tonnes) must be rejected
    verdict, msg = plausibility_check(-2e8)
    assert verdict == "reject"
    assert "Implausible value" in msg

    # Extreme negative emission between flag and reject bound (e.g. -5 million tonnes) must be flagged
    verdict, msg = plausibility_check(-5e6)
    assert verdict == "flag"
    assert "Plausibility review" in msg

    # Valid emission
    verdict, msg = plausibility_check(500.0)
    assert verdict is None
    assert msg is None


def test_z_score_check_negative_mean_and_iqr_outliers():
    """Verify Bug 12 fix: _z_score_check produces ordered expected_range for negative mean and detects IQR outliers."""
    detector = AnomalyDetector()

    # Constant negative history: mean = -100.0
    res = detector._z_score_check(-200.0, [-100.0, -100.0, -100.0])
    assert res["flagged"] is True
    assert res["reason"] == "constant_history_deviation"
    low, high = res["expected_range"]
    assert low <= high, f"Expected range bounds inverted: [{low}, {high}]"
    assert low == -150.0
    assert high == -50.0

    # IQR fence outlier detection (at least 4 observations)
    # Quartiles of [10, 11, 12, 13]: Q1=10.75, Q3=12.25, IQR=1.5, fences = [6.25, 16.75]
    res_iqr = detector._z_score_check(25.0, [10.0, 11.0, 12.0, 13.0])
    assert res_iqr["flagged"] is True
    assert res_iqr["iqr_flagged"] is True
    low_iqr, high_iqr = res_iqr["expected_range"]
    assert low_iqr <= high_iqr

    # Zero history with positive new value
    res_zero = detector._z_score_check(50.0, [0.0, 0.0, 0.0])
    assert res_zero["flagged"] is True
    assert res_zero["reason"] == "constant_history_deviation"


def test_tank_flashing_control_efficiency_string_normalization():
    """Verify Bug 13 fix: TankFlashingCalculator accepts percentage strings without crashing."""
    calc = TankFlashingCalculator()

    # Pass control_efficiency as '95%' string for crude flashing
    res_str = calc.calculate(
        throughput=10000.0,
        liquid_type="crude",
        control_efficiency="95%",
        control_type="flare",
    )
    assert res_str["total_co2e"] > 0
    assert res_str["inputs"]["control_efficiency"] == 0.95
    assert res_str["results"]["co2"]["value"] > 0
    assert res_str["results"]["ch4"]["value"] > 0

    # Pass numeric percentage 95.0
    res_num = calc.calculate(
        throughput=10000.0,
        liquid_type="crude",
        control_efficiency=95.0,
        control_type="flare",
    )
    assert abs(res_str["total_co2e"] - res_num["total_co2e"]) < 1e-4

    # VRU control type
    res_vru = calc.calculate(
        throughput=10000.0,
        liquid_type="crude",
        control_efficiency="98%",
        control_type="vru",
    )
    assert res_vru["inputs"]["control_efficiency"] == 0.98
    assert res_vru["results"]["co2"]["value"] == 0.0
    assert res_vru["results"]["ch4"]["value"] < res_str["results"]["ch4"]["value"]


def test_acid_gas_removal_control_efficiency_string_normalization():
    """Verify Bug 13 fix: AcidGasRemovalCalculator accepts control_efficiency string without crashing."""
    calc = AcidGasRemovalCalculator()

    res = calc.calculate(
        method="throughput",
        sour_gas_mmscf_yr=100.0,
        sour_co2_content=0.08,
        sweet_co2_content=0.01,
        disposition="flared",
        control_efficiency="98%",
    )
    # Table 6-19 throughput factor 0.0185 t CH4/MMscf -> 1.85 t, flared at 98 %: 0.037 t escapes, 1.813 t burns to CO2.
    # Eq 6-18: CO2 = (V_sour x 8 % - V_sweet x 1 %) x 44.01 / 379.3 / 2,204.62 with V_sweet = V_sour x (1 - 8 %) (the
    # engine takes the sweet gas as the sour gas less its CO2 fraction).
    co2_vented = 100e6 * (0.08 - 0.92 * 0.01) * (44.01 / 379.3) / 2204.62
    assert res["results"]["ch4"]["value"] == pytest.approx(1.85 * 0.02, rel=1e-9)
    assert res["results"]["co2"]["value"] == pytest.approx(co2_vented + 1.85 * 0.98 * (44.01 / 16.04), rel=1e-5)
    assert res["total_co2e"] == pytest.approx(
        res["results"]["co2"]["value"] + 28.0 * res["results"]["ch4"]["value"] + 265.0 * res["results"]["n2o"]["value"],
        rel=1e-9)


def test_blowdown_control_efficiency_string_and_differential_mode():
    """Verify Bug 13 fix: BlowdownCalculator handles string control_efficiency and differential mode."""
    calc = BlowdownCalculator()

    # Blowdown with string control efficiency
    res = calc.calculate(
        blowdown_volume=100.0,
        pressure=500.0,
        events=5,
        ch4_content="85%",
        co2_content="5%",
        control_efficiency="90%",
        control_type="flare",
        blowdown_mode="differential",
        final_pressure=50.0,
    )
    # differential blowdown 500 -> 50 psig: gas released per event = V x (P1 - P2) / 14.696 = 100 x 450 / 14.696 standard m3, 5 events
    v_std = 5 * 100.0 * ((500.0 + 14.696) - (50.0 + 14.696)) / 14.696
    rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
    assert res["inputs"]["total_v_std_m3"] == pytest.approx(v_std, rel=1e-9)
    # 90 % of the gas to a flare (98 % destruction, 96.5 % carbon conversion), 10 % vented; the 5 % CO2 is vented / passes through
    assert res["results"]["ch4"]["value"] == pytest.approx(v_std * 0.85 * rho_ch4 / 1000 * (0.10 + 0.90 * 0.02), rel=1e-9)
    assert res["results"]["co2"]["value"] == pytest.approx(
        v_std * 0.85 * rho_co2 / 1000 * 0.90 * 0.965 + v_std * 0.05 * rho_co2 / 1000, rel=1e-9)


def test_gas_dehydration_count_non_negative_guard():
    """Verify Bug 14 fix: GasDehydrationCalculator rejects negative dehydrator_count."""
    calc = GasDehydrationCalculator()

    with pytest.raises(ValueError, match="dehydrator_count cannot be negative"):
        calc.calculate(
            dehydrator_type="glycol",
            use_unit_factor=True,
            dehydrator_count=-3,
        )

    # Valid count of 0 yields 0 emissions
    res_zero = calc.calculate(
        dehydrator_type="glycol",
        use_unit_factor=True,
        dehydrator_count=0,
    )
    assert res_zero["results"]["ch4"]["value"] == 0.0

    # Positive count
    res_pos = calc.calculate(
        dehydrator_type="glycol",
        use_unit_factor=True,
        dehydrator_count=2,
    )
    assert res_pos["results"]["ch4"]["value"] > 0


def test_pneumatic_device_case2_negative_count_guard():
    """Verify Bug 15 fix: PneumaticDeviceCalculator Case 2 (Eq 6-13) rejects negative count."""
    calc = PneumaticDeviceCalculator()

    with pytest.raises(ValueError, match="Device count cannot be negative"):
        calc.calculate(
            id_pipe_inches=2.0,
            length_pipe_ft=20.0,
            delta_vol_bonnet_scf=0.5,
            p_control_psig=30.0,
            actuations_per_year=1200,
            count=-2,
        )

    # Subpart W controller standards
    res_subw = calc.calculate(
        count=5,
        controller_type="high_bleed",
        source_standard="subpart_w",
        hours=8760,
    )
    # Subpart W high bleed is 37.3 scf/hr
    expected_scf = 5 * 37.3 * 8760
    assert abs(res_subw["inputs"]["total_gas_scf"] - expected_scf) < 1.0


def test_dispatcher_pct_string_handling():
    """Verify Bug 16 fix: CalculationDispatcher.dispatch handles meter/gc uncertainty with % symbol."""
    disp = CalculationDispatcher()

    payload = {
        "process_type": "stationary_combustion",
        "quantity": 1000.0,
        "unit": "m3",
        "fuel_type": "natural_gas",
        "factor_source": "specific",
        "hhv": 1020.0,
        "combustion_efficiency": 99.5,
        "c1": 0.90,
        "co2_comp": 0.02,
        "n2_mol": 0.08,  # an analysis must total 100 %
        "meter_uncertainty_pct": "5.0%",
        "gc_uncertainty_pct": "2.5%",
    }
    factors = {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "unit": "kg/m3"}

    res = disp.dispatch("stationary_combustion", payload, factors)
    # carbon balance: 0.90 CH4 x 1 mol C at 99.5 % combustion + 2 % native CO2; slip 0.5 % of the CH4 (60 F, 23.685 m3/kmol)
    co2 = 1000.0 * (0.90 * 0.995 + 0.02) * (44.01 / 23.685) / 1000
    ch4 = 1000.0 * 0.90 * 0.005 * (16.04 / 23.685) / 1000
    assert res["results"]["co2"]["value"] == pytest.approx(co2, rel=1e-9)
    assert res["results"]["ch4"]["value"] == pytest.approx(ch4, rel=1e-9)
    assert res["total_co2e"] == pytest.approx(co2 + 28.0 * ch4, rel=1e-9)
    assert "uncertainty_components" in res


def test_dispatcher_ccs_capture_rate_percentage_string():
    """Verify CalculationDispatcher._apply_capture reduces CO2 emissions by string percentage."""
    disp = CalculationDispatcher()

    # Run combustion with 90% CCS capture
    payload = {
        "process_type": "stationary_combustion",
        "quantity": 5000.0,
        "unit": "m3",
        "fuel_type": "natural_gas",
        "factor_source": "specific",
        "hhv": 1020.0,
        "combustion_efficiency": 99.5,
        "c1": 0.95,
        "co2_comp": 0.02,
        "n2_mol": 0.03,
        "ccs_capture_rate": "90%",
    }
    factors = {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "unit": "kg/m3"}

    res = disp.dispatch("stationary_combustion", payload, factors)
    assert res["inputs"]["ccs_capture_rate"] == 0.90
    assert res["total_co2e"] > 0


def test_production_non_routine_prv_zero_ch4():
    """Verify Bug 17 fix: PRV release with zero methane correctly computes CO2 emissions."""
    calc = ProductionNonRoutineVentingCalculator()

    # PRV on pure CO2 stream (c_ch4 = 0.0, c_co2 = 0.95)
    res = calc.calculate(
        source_type="prv",
        equipment_count=10,
        ch4_content=0.0,
        co2_content=0.95,
    )
    # Table 6-28 PRV whole gas is 43 scf/yr per PRV -> 10 PRVs = 430 scf
    assert res["inputs"]["total_gas_scf"] == 430.0
    assert res["results"]["ch4"]["value"] == 0.0
    # CO2 must be strictly greater than 0
    assert res["results"]["co2"]["value"] > 0.0
    assert res["total_co2e"] > 0.0

    # ESD platform release with zero methane
    res_esd = calc.calculate(
        source_type="esd_platform",
        equipment_count=1,
        ch4_content=0.0,
        co2_content=0.40,
    )
    assert res_esd["results"]["ch4"]["value"] == 0.0
    assert res_esd["results"]["co2"]["value"] > 0.0


def test_compressor_seal_negative_measured_rate_guard():
    """Verify Bug 18 fix: CompressorSealCalculator rejects negative measured leak rates."""
    calc = CompressorSealCalculator()

    with pytest.raises(ValueError, match="measured_kg_hr cannot be negative"):
        calc.calculate(
            compressor_count=2,
            seal_type="centrifugal_wet",
            measured_kg_hr=-10.0,
        )

    # Valid measured leak rate
    res_meas = calc.calculate(
        compressor_count=2,
        seal_type="centrifugal_wet",
        measured_kg_hr=15.0,
        hours=4000,
    )
    assert res_meas["results"]["ch4"]["value"] == (2 * 15.0 * 4000) / 1000.0


def test_compressor_seal_all_industry_segments():
    """Verify CompressorSealCalculator across all industry segments and seal types."""
    calc = CompressorSealCalculator()

    # Processing segment
    res_proc_wet = calc.calculate(compressor_count=1, seal_type="centrifugal_wet", segment="processing", hours=8760)
    assert abs(res_proc_wet["results"]["ch4"]["value"] - (86426.0 / 1000.0)) < 0.1

    res_proc_dry = calc.calculate(compressor_count=1, seal_type="centrifugal_dry", segment="processing", hours=8760)
    assert abs(res_proc_dry["results"]["ch4"]["value"] - (28192.0 / 1000.0)) < 0.1

    res_proc_recip = calc.calculate(compressor_count=1, seal_type="reciprocating", segment="processing", hours=1000)
    assert abs(res_proc_recip["results"]["ch4"]["value"] - (2.7 * 1000 / 1000.0)) < 0.01

    # Transmission & Storage segment
    res_trans_wet = calc.calculate(compressor_count=1, seal_type="centrifugal_wet", segment="transmission", hours=1000)
    assert abs(res_trans_wet["results"]["ch4"]["value"] - (18.4 * 1000 / 1000.0)) < 0.01

    res_trans_dry = calc.calculate(compressor_count=1, seal_type="centrifugal_dry", segment="transmission", hours=1000)
    assert abs(res_trans_dry["results"]["ch4"]["value"] - (5.75 * 1000 / 1000.0)) < 0.01

    res_trans_recip = calc.calculate(compressor_count=1, seal_type="reciprocating", segment="transmission", hours=1000)
    assert abs(res_trans_recip["results"]["ch4"]["value"] - (4.72 * 1000 / 1000.0)) < 0.01


def test_liquids_unloading_tier3_equation_6_11_pressure_ratio():
    """Verify LiquidsUnloadingCalculator Eq. 6-11 automated plunger pressure ratio and physical boundaries."""
    calc = LiquidsUnloadingCalculator()

    # Pshut >= Patm requirement
    with pytest.raises(ValueError, match="must be greater than or equal to atmospheric"):
        calc.calculate_tier3_equation_6_11(
            p_shut=10.0,
            p_line=100.0,
            p_sep=50.0,
            sfr_p=1000.0,
            t_p=2.0,
            p_atm=14.7,
            ch4_content=0.85,
        )

    # Pline > Psep requirement
    with pytest.raises(ValueError, match="must be strictly greater than separator"):
        calc.calculate_tier3_equation_6_11(
            p_shut=120.0,
            p_line=50.0,
            p_sep=60.0,
            sfr_p=1000.0,
            t_p=2.0,
            p_atm=14.7,
            ch4_content=0.85,
        )

    # Valid execution: Pshut = 100 psia, Patm = 14.7 psia, Pline = 80 psia, Psep = 30 psia
    # Ratio = sqrt(85.3) / sqrt(50) = 9.2358 / 7.0711 = 1.30613
    res = calc.calculate_tier3_equation_6_11(
        p_shut=100.0,
        p_line=80.0,
        p_sep=30.0,
        sfr_p=500.0,
        t_p=3.0,
        events=10,
        ch4_content=0.85,
        co2_content=0.03,
        control_efficiency=0.95,
    )
    expected_ratio = math.sqrt(100.0 - 14.696) / math.sqrt(80.0 - 30.0)
    assert abs(res["inputs"]["press_ratio"] - expected_ratio) < 1e-4
    assert res["total_co2e"] > 0

    # 0 events yields exact zero result
    res_zero = calc.calculate_tier3_equation_6_11(
        p_shut=100.0,
        p_line=80.0,
        p_sep=30.0,
        sfr_p=500.0,
        t_p=3.0,
        events=0,
        ch4_content=0.85,
    )
    assert res_zero["total_co2e"] == 0.0


def test_screening_correlation_equations_mixed_arrays():
    """Verify OnshoreScreeningMeasurementCalculator correlation approach with mixed values, non-detects, and pegged counts."""
    calc = OnshoreScreeningMeasurementCalculator()

    # Component: valve in gas service
    res = calc.calculate_correlation_equation(
        component_type="valves",
        screening_values_ppm=[0.0, 50.0, 500.0, 5000.0],
        zero_count=2,
        pegged_10k_count=1,
        pegged_100k_count=1,
        operating_hours=4000.0,
        ch4_content=0.60,
    )
    assert res["total_co2e"] > 0
    assert res["intermediate"]["toc_default_zero_kg_hr"] > 0
    assert res["intermediate"]["toc_correlation_kg_hr"] > 0
    assert res["intermediate"]["toc_pegged_kg_hr"] > 0
    assert res["intermediate"]["screening_count"] == 8

    # Negative ppm must raise ValueError
    with pytest.raises(ValueError, match="Screening concentration cannot be negative"):
        calc.calculate_correlation_equation(
            component_type="valve",
            screening_values_ppm=[-10.0],
        )


def test_combustion_tier3_liquid_fuel_carbon_mass_balance():
    """Verify CombustionCalculator Tier 3 liquid fuel carbon mass balance (Exhibit 4.5)."""
    calc = CombustionCalculator()

    # 10,000 tonnes of fuel oil with 86.5 wt% carbon and 99.5% combustion efficiency
    # CO2 = 10,000 * 1000 * 0.865 * 0.995 * (44.01 / 12.011) / 1000 = 3153.69 tonnes CO2
    res_mass = calc.calculate(
        fuel_quantity=10000.0,
        fuel_unit="tonne",
        fuel_type="liquids",
        carbon_wt="86.5%",
        combustion_efficiency="99.5%",
    )
    expected_co2 = 10000.0 * 1000.0 * 0.865 * 0.995 * (44.01 / 12.011) / 1000.0
    assert abs(res_mass["results"]["co2"]["value"] - expected_co2) < 1.0

    # Liquid volume (bbl) with density 850 kg/m3
    # 5,000 bbl = 794.9365 m3 * 850 kg/m3 = 675,696 kg fuel
    res_vol = calc.calculate(
        fuel_quantity=5000.0,
        fuel_unit="bbl",
        fuel_type="crude",
        density=850.0,
        carbon_wt=85.0,
        combustion_efficiency=1.0,
    )
    expected_co2_vol = (5000.0 * 0.1589873 * 850.0) * 0.85 * (44.01 / 12.011) / 1000.0
    assert abs(res_vol["results"]["co2"]["value"] - expected_co2_vol) < 1.0


def test_legacy_engine_fallback_specific_factors_and_missing_factor():
    """Verify legacy compute_emissions fallback with custom specific factors and missing factor error."""
    # Factor fallback with custom specific factors
    payload = {
        "process_type": "stationary_combustion",
        "quantity": 1000.0,
        "unit": "m3",
        "factor_source": "specific",
        "specificFactors": {
            "co2": 2.15,
            "ch4": 0.0003,
            "n2o": 0.00005,
            "unit": "kg/m3",
        },
    }
    em, method = compute_emissions(payload)
    assert method == "server_specific"
    assert abs(em["co2"] - (1000.0 * 2.15 / 1000.0)) < 1e-4
    assert abs(em["ch4"] - (1000.0 * 0.0003 / 1000.0)) < 1e-6
    assert em["totalCo2e"] > 0

    # Missing factor error when factor_data has no emission factors
    bad_payload = {
        "process_type": "combustion",
        "quantity": 500.0,
        "unit": "m3",
        "factor_source": "default",
        "fuel": "nonexistent_fuel_catalog_xyz",
    }
    with pytest.raises(MissingFactorError, match="No emission factor found"):
        compute_emissions(bad_payload, factor_data={})
