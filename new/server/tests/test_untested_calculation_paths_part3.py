"""
Deep forensic verification of previously unexercised calculation paths - Part 3.

Covers:
1. CombustionMethodCalculator (carbon_content, equipment, vehicle_distance, flare_voc, thermal_oxidizer)
2. AnomalyDetector & BatchAnomalyDetector (Z-score, IQR fences, plausibility bounds, history windowing)
3. Unit conversions & physical invariants (units.py, temperature, pressure, dimensions, gas volumes)
4. Vented completion advanced branches (native CO2 adjustment, injected N2 in m3, flowback duration bounds)
5. Production tank & wells advanced paths (auto GOR detection, amine unit count, CO2 EOR ft3 & bounds)
6. Vented well unloading (depth in meters/km, volume-based default method)
7. Dispatcher combustion & venting branches (comb_eff scaling, custom drilling EF, hours bounds, bleed units)
8. Dispatcher fugitive & onshore screening (time units, corr counts, method 21 splits, OGI bounds)
9. Midstream AGR & glycol dehydrator invariants (contactor shrinkage, control technologies, physical bounds)
"""
import math
import re
import pytest

from calculations.combustion_methods import (
    CombustionMethodCalculator,
    EQUIPMENT_FACTORS,
    VEHICLE_FACTORS,
)
from calculations.anomaly import (
    AnomalyDetector,
    plausibility_check,
    scope1_source,
    PLAUSIBILITY_REJECT_TCO2E,
    PLAUSIBILITY_FLAG_TCO2E,
)
from calculations.units import (
    convert,
    gas_volume_m3,
    unit_dimension,
    to_base,
    normalize_efficiency,
    scope3_ef_kg_per_unit,
    UnitError,
    AMBIGUOUS_TON,
)
from calculations.vented_completion import CompletionFlowbackCalculator
from calculations.vented_production_tank import TankFlashingCalculator, AcidGasRemovalCalculator
from calculations.vented_production_wells import CO2EORVentingCalculator
from calculations.vented_unloading import LiquidsUnloadingCalculator
from calculations.dispatcher import CalculationDispatcher
from calculations.fugitive_onshore import OnshoreScreeningMeasurementCalculator
from calculations.midstream import AGRCalculator, DehydratorCalculator


def test_combustion_methods_carbon_content_and_equipment():
    calc = CombustionMethodCalculator()

    # 1. Carbon content from fuel mass (tonnes)
    res_mass = calc.calculate("carbon_content", {
        "fuel_mass": 100.0,
        "fuel_mass_unit": "t",
        "carbon_wt_pct": 85.0,
        "oxidation_pct": 99.0,
    })
    # 100 t * 0.85 C * 0.99 ox * (44.01 / 12.011) = 308.384 t CO2
    expected_co2 = 100.0 * 0.85 * 0.99 * (44.01 / 12.011)
    assert pytest.approx(res_mass["results"]["co2"]["value"], rel=1e-3) == expected_co2
    assert res_mass["total_co2e"] == pytest.approx(expected_co2, rel=1e-3)

    # Carbon content from liquid fuel volume (gal) and density (lb/gal)
    res_vol = calc.calculate("carbon_content", {
        "fuel_volume": 10000.0,
        "fuel_volume_unit": "gal",
        "fuel_density": 7.0,
        "density_unit": "lb/gal",
        "carbon_wt_pct": 86.0,
    })
    # 10000 gal * 7.0 lb/gal / 2204.62 = 31.7515 t fuel
    # 31.7515 * 0.86 * 1.0 * (44.01 / 12.011) = 100.04 t CO2
    assert res_vol["results"]["co2"]["value"] > 90.0

    # Validation: missing carbon content or invalid percentage
    with pytest.raises(ValueError, match="carbon content"):
        calc.calculate("carbon_content", {"fuel_mass": 10.0})
    with pytest.raises(ValueError, match="cannot exceed 100 %"):
        calc.calculate("carbon_content", {"fuel_mass": 10.0, "carbon_wt_pct": 105.0})

    # 2. Equipment method: direct energy_mmbtu
    res_eq1 = calc.calculate("equipment", {
        "equipment_type": "boiler_ng_controlled",
        "energy_mmbtu": 5000.0,
    })
    assert res_eq1["results"]["co2"]["value"] > 0
    assert res_eq1["results"]["ch4"]["value"] > 0
    assert res_eq1["results"]["n2o"]["value"] > 0

    # Equipment method: engine rating hp * load * hours * heat rate
    res_eq2 = calc.calculate("equipment", {
        "equipment_type": "ic_4s_lean_ng",
        "engine_hp": 1500.0,
        "load_pct": 80.0,
        "operating_hours": 8000.0,
        "heat_rate_btu_hphr": 7500.0,
    })
    # energy = 1500 * 0.80 * 8000 * 7500 / 1e6 = 72,000 MMBtu
    assert res_eq2["intermediate"]["energy_mmbtu"] == pytest.approx(72000.0)

    # Equipment method: natural gas fuel volume
    res_eq3 = calc.calculate("equipment", {
        "equipment_type": "turbine_ng_uncontrolled",
        "fuel_volume": 1000.0,
        "fuel_volume_unit": "mcf",
        "hhv_btu_scf": 1020.0,
    })
    assert res_eq3["intermediate"]["energy_mmbtu"] == pytest.approx(1020.0)

    # Unknown equipment type
    with pytest.raises(ValueError, match="Unknown equipment type"):
        calc.calculate("equipment", {"equipment_type": "non_existent_engine"})


def test_combustion_methods_vehicle_flare_voc_and_oxidizer():
    calc = CombustionMethodCalculator()

    # 1. Vehicle distance method
    res_veh = calc.calculate("vehicle_distance", {
        "distance": 50000.0,
        "distance_unit": "mile",
        "vehicle_type": "hd_diesel_advanced",
        "fuel_economy_mpg": 6.5,
    })
    assert res_veh["results"]["co2"]["value"] > 0
    assert res_veh["results"]["ch4"]["value"] > 0
    assert res_veh["results"]["n2o"]["value"] > 0
    assert res_veh["intermediate"]["fuel_gal"] == pytest.approx(50000.0 / 6.5)

    # Vehicle validation: invalid vehicle fuel
    with pytest.raises(ValueError, match="Vehicle fuel must be diesel or gasoline"):
        calc.calculate("vehicle_distance", {
            "distance": 1000.0,
            "vehicle_fuel": "jet_fuel",
            "fuel_economy_mpg": 10.0,
        })

    # 2. Flare VOC back-calculation (Exhibit 5.2)
    res_flare = calc.calculate("flare_voc", {
        "voc_mass": 5.0,  # 5 tonnes VOC emitted
        "voc_mass_unit": "t",
        "wt_ch4": 70.0,
        "wt_c2h6": 15.0,
        "wt_c3h8": 8.0,
        "wt_c4h10": 4.0,
        "wt_c5h12": 2.0,
        "wt_c6plus": 1.0,
        "wt_co2": 0.0,
        "combustion_efficiency": 98.0,
    })
    assert res_flare["results"]["co2"]["value"] > 0
    assert res_flare["results"]["ch4"]["value"] > 0
    assert res_flare["results"]["n2o"]["value"] > 0
    assert res_flare["intermediate"]["hc_emitted_t"] > 5.0

    # Flare VOC validation
    with pytest.raises(ValueError, match="flare gas analysis needs the VOC"):
        calc.calculate("flare_voc", {"voc_mass": 5.0, "wt_ch4": 100.0})
    with pytest.raises(ValueError, match="Combustion efficiency must be below 100 %"):
        calc.calculate("flare_voc", {
            "voc_mass": 5.0, "wt_c3h8": 50.0, "wt_ch4": 50.0, "combustion_efficiency": 100.0
        })

    # 3. Thermal oxidizer method (Exhibit 5.3)
    res_to1 = calc.calculate("thermal_oxidizer", {
        "toc_mass": 10.0,
        "toc_mass_unit": "t",
        "toc_carbon_wt_pct": 75.0,
        "toc_ch4_wt_pct": 10.0,
        "destruction_efficiency": 99.0,
    })
    # co2 = 10 * 0.75 * (44.01 / 12.011) * 0.99 = 27.206 t
    assert res_to1["results"]["co2"]["value"] == pytest.approx(10.0 * 0.75 * (44.01 / 12.011) * 0.99, rel=1e-3)
    # ch4 slip = 10 * 0.10 * (1 - 0.99) = 0.01 t
    assert res_to1["results"]["ch4"]["value"] == pytest.approx(0.01, rel=1e-3)

    # Thermal oxidizer from liquid loading
    res_to2 = calc.calculate("thermal_oxidizer", {
        "liquid_loaded": 100000.0,
        "liquid_unit": "gal",
        "loading_loss_lb_kgal": 5.0,
        "voc_fraction_of_toc": 85.0,
        "toc_carbon_wt_pct": 80.0,
        "toc_ch4_wt_pct": 5.0,
    })
    assert res_to2["results"]["co2"]["value"] > 0

    # Unknown method validation
    with pytest.raises(ValueError, match="Unknown combustion method"):
        calc.calculate("invalid_submethod", {})


def test_anomaly_detection_statistics_and_fences():
    detector = AnomalyDetector()

    # 1. Invalid values
    assert detector._z_score_check(None, [10.0, 11.0, 12.0])["reason"] == "invalid_value"
    assert detector._z_score_check(float("nan"), [10.0, 11.0, 12.0])["reason"] == "invalid_value"
    assert detector._z_score_check(float("inf"), [10.0, 11.0, 12.0])["reason"] == "invalid_value"

    # 2. Insufficient history (< 3 values)
    assert detector._z_score_check(15.0, [10.0, 11.0])["reason"] == "insufficient_history"
    assert not detector._z_score_check(15.0, [10.0, 11.0])["flagged"]

    # 3. Constant history (std == 0)
    # Slight deviation (<= 50%) -> not flagged
    res_const1 = detector._z_score_check(110.0, [100.0, 100.0, 100.0])
    assert not res_const1["flagged"]
    # Large deviation (> 50%) -> flagged
    res_const2 = detector._z_score_check(160.0, [100.0, 100.0, 100.0])
    assert res_const2["flagged"]
    assert res_const2["reason"] == "constant_history_deviation"
    # Zero mean with positive value
    res_const3 = detector._z_score_check(5.0, [0.0, 0.0, 0.0])
    assert res_const3["flagged"]

    # 4. Low variance std < 1e-6
    near_const = [10.0, 10.00000001, 10.00000002]
    res_low_var = detector._z_score_check(100.0, near_const)
    assert res_low_var["flagged"]
    assert res_low_var["z_score"] == 999.0

    # 5. Normal and IQR fences (>= 4 observations)
    normal_history = [100.0, 102.0, 98.0, 101.0, 99.0, 100.5, 99.5, 101.5]
    # Normal value
    res_norm = detector._z_score_check(100.2, normal_history)
    assert not res_norm["flagged"]
    assert abs(res_norm["z_score"]) < 1.0

    # Extreme outlier (> 3 sigma)
    res_outlier = detector._z_score_check(500.0, normal_history)
    assert res_outlier["flagged"]
    assert res_outlier["reason"] == "z_score"

    # 6. Plausibility checks
    assert plausibility_check(None) == (None, None)
    assert plausibility_check("invalid") == ("reject", "Calculated emissions are not a number")
    verdict_high, msg_high = plausibility_check(PLAUSIBILITY_REJECT_TCO2E + 1)
    assert verdict_high == "reject"
    verdict_flag, msg_flag = plausibility_check(PLAUSIBILITY_FLAG_TCO2E + 1)
    assert verdict_flag == "flag"
    verdict_z, msg_z = plausibility_check(500.0, z_flag="Z-score exceeded")
    assert verdict_z == "flag"
    assert plausibility_check(500.0) == (None, None)

    # 7. Source identifier helper
    assert scope1_source("EQ-101", "Natural Gas") == ("equipment", "EQ-101")
    assert scope1_source(None, "Diesel") == ("fuel", "Diesel")
    assert scope1_source(None, None) is None

    # 8. Historical windowing logic
    # Rows format: (year, month, value, status, qa_flag)
    rows = [
        (2025, 1, 10.0, "Verified", None),
        (2025, 2, 12.0, "Verified", None),
        (2025, 3, 11.0, "Verified", None),
        (2024, 1, 99.0, "Verified", None),  # 13 months before 2025-02 -> outside 12m window
    ]
    hist = AnomalyDetector._history(rows, 2025, 4)
    assert hist == [10.0, 12.0, 11.0]

    # Fallback to unflagged when < 3 Verified
    unverified_rows = [
        (2025, 1, 10.0, "Draft", None),
        (2025, 2, 12.0, "Draft", None),
        (2025, 3, 11.0, "Draft", None),
    ]
    fb_hist = AnomalyDetector._history(unverified_rows, 2025, 4)
    assert fb_hist == [10.0, 12.0, 11.0]


def test_units_edge_cases_and_dimensional_conversions():
    # 1. convert(None) raises ValueError
    with pytest.raises(ValueError, match="Cannot convert None value"):
        convert(None, "m3", "scf")

    # 2. Temperature conversions
    assert convert(0.0, "degc", "degf") == pytest.approx(32.0)
    assert convert(100.0, "c", "k") == pytest.approx(373.15)
    assert convert(60.0, "f", "r") == pytest.approx(519.67)

    # 3. Pressure conversions
    assert convert(14.696, "psia", "kpa") == pytest.approx(101.325, rel=1e-3)
    assert convert(1.0, "bar", "kpa") == pytest.approx(100.0)
    assert convert(0.0, "psig", "psia") == pytest.approx(14.696)

    # 4. gas_volume_m3
    assert gas_volume_m3(100.0, "m3") == pytest.approx(100.0)
    assert gas_volume_m3(1000.0, "scf") == pytest.approx(1000.0 * 0.028316846592)
    assert gas_volume_m3(1.0, "mmscf") == pytest.approx(1e6 * 0.028316846592)

    # Incompatible units for gas composition method
    for bad_u in ("bbl", "kg", "kwh", "gal", "tonne"):
        with pytest.raises(UnitError, match="The gas composition method needs a gas volume"):
            gas_volume_m3(100.0, bad_u)

    # 5. unit_dimension and to_base
    dim_m3, factor_m3 = unit_dimension("m3")
    assert dim_m3 == "volume"
    assert factor_m3 == 1.0

    # Ambiguous ton
    with pytest.raises(UnitError, match=re.escape(AMBIGUOUS_TON)):
        unit_dimension("ton")
    with pytest.raises(UnitError, match=re.escape(AMBIGUOUS_TON)):
        unit_dimension("tons")

    # Mismatched dimension in to_base
    with pytest.raises(UnitError, match="is a volume unit, expected mass"):
        to_base(10.0, "m3", dimension="mass")

    # Unknown unit
    with pytest.raises(UnitError, match="Unknown unit"):
        unit_dimension("florgs")

    # 6. normalize_efficiency
    assert normalize_efficiency(98.0) == 0.98
    assert normalize_efficiency(0.98) == 0.98
    assert normalize_efficiency("98", unit="%") == 0.98
    assert normalize_efficiency("0.95", unit="fraction") == 0.95
    assert normalize_efficiency(-5.0) == 0.0
    assert normalize_efficiency(150.0) == 1.0

    # 7. scope3_ef_kg_per_unit
    assert scope3_ef_kg_per_unit(100.0, 5.0) == pytest.approx(50.0)  # 5 t * 1000 / 100 = 50 kg/unit
    assert scope3_ef_kg_per_unit(0.0, 5.0, ef=12.3) == 12.3
    assert scope3_ef_kg_per_unit("invalid", 5.0, ef=45.6) == 45.6


def test_vented_completion_advanced_branches():
    calc = CompletionFlowbackCalculator()

    # 1. Tier 1 Footnote c adjustments for native CO2
    res_native = calc.calculate(
        tier="tier1",
        well_type="gas",
        control_type="uncontrolled",
        events=2,
        ch4_content=75.0,  # 75 mol% CH4
        co2_content=5.0,   # 5 mol% native CO2
    )
    # y_co2 > 0 and actual_ch4_mol > 0 triggers co2_adjusted
    assert res_native["results"]["co2"]["value"] > 0
    assert res_native["results"]["ch4"]["value"] > 0
    assert res_native["total_co2e"] > 0

    # Flared Tier 1 well with combustion and flared N2O
    res_flared = calc.calculate(
        tier="tier1",
        well_type="gas",
        control_type="flared",
        events=1,
        control_efficiency=98.0,
        hhv=1050.0,
    )
    assert res_flared["results"]["n2o"]["value"] > 0
    assert res_flared["results"]["co2"]["value"] > 0

    # 2. Tier 3: Injected N2 deduction in m3 and Sm3
    res_n2_m3 = calc.calculate(
        tier="tier3",
        flowback_volume=100000.0,
        volume_unit="scf",
        events=1,
        ch4_content=80.0,
        injected_gas_type="n2",
        injected_n2_volume=500.0,
        injected_n2_unit="m3",
    )
    # 500 m3 = 17,657.3 scf N2 deducted from 100,000 scf
    assert res_n2_m3["results"]["ch4"]["value"] > 0

    # Injected N2 in MMscf
    res_n2_mmscf = calc.calculate(
        tier="tier3",
        flowback_volume=2000000.0,
        volume_unit="scf",
        events=1,
        ch4_content=80.0,
        injected_gas_type="n2",
        injected_n2_volume=0.5,
        injected_n2_unit="mmscf",
    )
    assert res_n2_mmscf["results"]["ch4"]["value"] > 0

    # 3. Initial flowback hours (API Eq. 6-5)
    # Missing metered duration (flowback_duration_hours <= 0) raises ValueError
    with pytest.raises(ValueError, match="Metered flowback duration"):
        calc.calculate(
            tier="tier3",
            flowback_volume=50000.0,
            volume_unit="scf",
            events=1,
            ch4_content=80.0,
            initial_flowback_hours=12.0,
            flowback_duration_hours=0.0,
        )

    # Valid initial flowback hours
    res_initial = calc.calculate(
        tier="tier3",
        flowback_volume=50000.0,
        volume_unit="scf",
        events=1,
        ch4_content=80.0,
        initial_flowback_hours=10.0,
        flowback_duration_hours=40.0,
    )
    assert res_initial["results"]["ch4"]["value"] > 0


def test_vented_production_tank_and_wells_advanced():
    # 1. Tank flashing: auto-detection of GOR method
    tank_calc = TankFlashingCalculator()
    res_gor_auto = tank_calc.calculate(
        throughput=5000.0,
        gas_oil_ratio=25.0,  # GOR provided with method=None
        method=None,
    )
    assert res_gor_auto["results"]["ch4"]["value"] > 0

    # Tank flashing: GOR = 0 (stabilized liquid)
    res_gor_zero = tank_calc.calculate(
        throughput=5000.0,
        gas_oil_ratio=0.0,
        method=None,
    )
    assert res_gor_zero["results"]["ch4"]["value"] == 0.0

    # 2. Amine unit count method (v_sour_scf <= 0 and n_units > 0)
    agr_calc = AcidGasRemovalCalculator()
    res_amine_units = agr_calc.calculate(
        method="unit_count",
        unit_count=3,
        operating_days=365.0,
    )
    assert res_amine_units["results"]["ch4"]["value"] > 0

    # Amine unit with sweet gas specified in MMscf
    res_sweet = agr_calc.calculate(
        sour_gas_mmscf_yr=100.0,
        sour_co2_content=10.0,
        sweet_gas_mmscf_yr=90.0,
        sweet_co2_content=0.5,
    )
    assert res_sweet["results"]["co2"]["value"] > 0

    # 3. Production Non-Routine Venting: CO2 EOR pump blowdown
    well_calc = CO2EORVentingCalculator()
    # physical_volume_ft3 converted to m3
    res_eor_ft3 = well_calc.calculate(
        activity="pump_blowdown",
        events=5,
        physical_volume_ft3=100.0,
        co2_density_kg_m3=1.85,
        co2_weight_fraction=95.0,
    )
    assert res_eor_ft3["results"]["co2"]["value"] > 0

    # Validation: negative physical volume, negative density, negative weight fraction
    with pytest.raises(ValueError, match="cannot be negative"):
        well_calc.calculate("pump_blowdown", events=1, physical_volume_m3=-10.0,
                            co2_density_kg_m3=1.85, co2_weight_fraction=0.9)
    with pytest.raises(ValueError, match="cannot be negative"):
        well_calc.calculate("pump_blowdown", events=1, physical_volume_m3=10.0,
                            co2_density_kg_m3=-1.85, co2_weight_fraction=0.9)
    with pytest.raises(ValueError, match="cannot be negative"):
        well_calc.calculate("pump_blowdown", events=1, physical_volume_m3=10.0,
                            co2_density_kg_m3=1.85, co2_weight_fraction=-0.5)


def test_vented_unloading_depth_and_default_method():
    calc = LiquidsUnloadingCalculator()

    # 1. Depth unit in meters and kilometers
    res_depth_m = calc.calculate_volume_based(
        well_depth=1500.0,
        depth_unit="m",
        diameter=4.5,
        diameter_unit="in",
        pressure=150.0,
        press_unit="psig",
        events=10,
        ch4_content=85.0,
    )
    assert res_depth_m["results"]["ch4"]["value"] > 0

    res_depth_km = calc.calculate_volume_based(
        well_depth=1.5,
        depth_unit="km",
        diameter=4.5,
        diameter_unit="in",
        pressure=150.0,
        press_unit="psig",
        events=10,
        ch4_content=85.0,
    )
    assert pytest.approx(res_depth_m["results"]["ch4"]["value"], rel=1e-3) == res_depth_km["results"]["ch4"]["value"]

    # Unknown depth unit
    with pytest.raises(ValueError, match="Unknown depth unit"):
        calc.calculate_volume_based(
            well_depth=1000.0,
            diameter=4.5,
            pressure=100.0,
            ch4_content=80.0,
            events=1,
            depth_unit="furlongs",
        )

    # 2. WellUnloadingCalculator.calculate default to volume-based
    res_default = calc.calculate(
        well_depth=5000.0,
        diameter=4.0,
        pressure=200.0,
        events=5,
        ch4_content=80.0,
    )
    assert res_default["results"]["ch4"]["value"] > 0
    assert "api_equation_6_3" in res_default["inputs"]["method"]


def test_dispatcher_branches_combustion_and_venting():
    disp = CalculationDispatcher()

    # 1. Combustion branch: comb_eff <= 1.0 fraction
    res_eff_frac = disp.dispatch("combustion", {
        "factor_source": "specific",
        "amount": 1000.0,
        "unit": "m3",
        "hhv": 1020.0,
        "comb_eff": 0.985,
        "co2_comp": 2.0,
        "n2_mol": 8.0,  # an analysis must total 100 %
        "c1": 90.0,
    }, {"co2": 1.9, "ch4": 0.05, "unit": "kg/m3", "type": "gases"}, {})
    assert res_eff_frac["results"]["co2"]["value"] > 0

    # Gas volume UnitError on non-gas unit with gas composition
    with pytest.raises(ValueError, match="needs a gas volume"):
        disp.dispatch("combustion", {
            "factor_source": "specific",
            "amount": 1000.0,
            "unit": "bbl",  # liquid unit
            "hhv": 1020.0,
            "comb_eff": 98.0,
            "c1": 95.0,     # triggers gas composition carbon balance
        }, {"co2": 0, "type": "gases"}, {})

    # Custom drilling emission factor
    res_drill_custom = disp.dispatch("drilling", {
        "amount": 10.0,
        "unit": "days",
        "mud_type": "oil_based",
    }, {"type": "custom", "ch4": 500.0}, {})  # 500 kg CH4/day -> 0.5 t CH4/day
    assert res_drill_custom["results"]["ch4"]["value"] == pytest.approx(5.0)

    # Completions auto-detection of comp_method = "rate_duration"
    res_comp_rate = disp.dispatch("completions", {
        "comp_rate": 10000.0,
        "comp_duration": 48.0,
        "ch4_content": 80.0,
    }, {}, {})
    assert res_comp_rate["results"]["ch4"]["value"] > 0

    # 2. Venting branch: blowdown volume from amount
    res_blowdown = disp.dispatch("venting", {
        "factor_source": "specific",
        "amount": 500.0,
        "unit": "m3",
        "blowdown_pressure": 100.0,
        "blowdown_events": 2,
        "ch4_content": 85.0,
    }, {}, {})
    assert res_blowdown["results"]["ch4"]["value"] > 0

    # Working loss factor with incompatible unit
    with pytest.raises(ValueError, match="Working-loss factor cannot be applied per bbl"):
        disp.dispatch("tank", {
            "factor_source": "specific",
            "tank_method": "working_loss",
            "amount": 1000.0,
            "unit": "bbl",
        }, {"ch4": 5.0, "unit": "kg/hr"}, {})

    # Pneumatic devices hours outside [0, 8784]
    with pytest.raises(ValueError, match="annual operating hours must be between 0 and 8,784"):
        disp.dispatch("pneumatics", {
            "factor_source": "specific",
            "amount": 5,
            "pneu_hours": 9000.0,
            "pneu_controller_type": "high_bleed",
        }, {}, {})

    # Pneumatic bleed rate with incompatible unit
    with pytest.raises(ValueError, match="Pneumatic bleed rate unit"):
        disp.dispatch("pneumatics", {
            "factor_source": "specific",
            "amount": 2,
            "pneu_bleed_rate": 15.0,
            "pneu_bleed_unit": "kg/hr",  # mass unit instead of volume rate
            "ch4_content": 85.0,
        }, {}, {})


def test_dispatcher_branches_fugitive_and_onshore_screen():
    disp = CalculationDispatcher()

    # 1. Fugitive dispatcher time units
    for t_unit, raw_t in [("days", 30.0), ("months", 2.0), ("years", 1.0)]:
        res_t = disp.dispatch("fugitive", {
            "factor_source": "specific",
            "fugitive_tier": "tier3",
            "fugitive_method": "correlation",
            "correlation_type": "valves",
            "service": "gas",
            "amount": 1,
            "time": raw_t,
            "time_unit": t_unit,
            "screening_ppm": 2500.0,
        }, {}, {})
        assert res_t["results"]["ch4"]["value"] > 0

    # 2. Correlation method: corr_screened_count
    res_corr = disp.dispatch("fugitive", {
        "factor_source": "specific",
        "fugitive_tier": "tier3",
        "fugitive_method": "correlation",
        "correlation_type": "valves",
        "service": "gas",
        "corr_screened_count": 5,
        "screening_ppm": 2500.0,
        "operating_hours": 8760.0,
    }, {}, {})
    assert res_corr["results"]["ch4"]["value"] > 0

    # 3. Method 21 screening: split count above/below 10,000 ppm
    res_m21_low = disp.dispatch("fugitive", {
        "factor_source": "specific",
        "fugitive_tier": "tier3",
        "fugitive_method": "method21",
        "component_type": "valves",
        "service": "gas",
        "component_count": 10,
        "screening_ppm": 500.0,  # < 10000 -> all below
    }, {}, {})
    assert res_m21_low["results"]["ch4"]["value"] > 0

    res_m21_high = disp.dispatch("fugitive", {
        "factor_source": "specific",
        "fugitive_tier": "tier3",
        "fugitive_method": "method21",
        "component_type": "valves",
        "service": "gas",
        "component_count": 10,
        "screening_ppm": 15000.0,  # >= 10000 -> all pegged
    }, {}, {})
    assert res_m21_high["results"]["ch4"]["value"] > res_m21_low["results"]["ch4"]["value"]

    # 4. Direct measurement: missing rate_unit raises ValueError
    with pytest.raises(ValueError, match="Select the unit of the measured leak rate"):
        disp.dispatch("fugitive", {
            "factor_source": "specific",
            "fugitive_tier": "tier3",
            "fugitive_method": "measurement",
            "measured_rate": 2.5,
            # rate_unit omitted
        }, {}, {})

    # 5. OnshoreScreeningMeasurementCalculator edge cases
    calc_screen = OnshoreScreeningMeasurementCalculator()
    # Method 21: negative count or zero count
    with pytest.raises(ValueError, match="Component counts cannot be negative"):
        calc_screen.calculate_method21_ranges("valve", "gas", -1, 5)
    with pytest.raises(ValueError, match="Enter the number of components"):
        calc_screen.calculate_method21_ranges("valve", "gas", 0, 0)

    # Correlation: negative screening ppm
    with pytest.raises(ValueError, match="Screening concentration cannot be negative"):
        calc_screen.calculate_correlation_equation("valve", screening_values_ppm=[-50.0])

    # OGI: leakers > surveyed or sum of fractions > 1.0001
    with pytest.raises(ValueError, match="cannot exceed total surveyed"):
        calc_screen.calculate_ogi_survey("valve", "gas", total_surveyed=10, leakers_detected=15)
    with pytest.raises(ValueError, match="cannot exceed 100 %"):
        calc_screen.calculate_ogi_survey("valve", "gas", leakers_detected=1, ch4_mol=80.0, co2_mol=25.0)

    # Direct measurement: negative rate or operating hours > 8784
    with pytest.raises(ValueError, match="Measured flow rate cannot be negative"):
        calc_screen.calculate_direct_measurement(-1.0)
    with pytest.raises(ValueError, match="must be between 0 and 8,784"):
        calc_screen.calculate_direct_measurement(1.0, operating_hours=9000.0)


def test_midstream_agr_and_dehydrator_invariants():
    # 1. Acid Gas Removal (AGR / Amine sweetening)
    agr = AGRCalculator()

    # Normal sweetening with contactor shrinkage
    res_agr = agr.calculate(
        throughput=500.0,  # 500 MMscf/yr
        co2_in=0.05,       # 5 mol% CO2
        co2_out=0.001,     # 0.1 mol% CO2
        ch4_slip_fraction=0.001,
        acid_gas_control_type="vent",
    )
    assert res_agr["results"]["co2"]["value"] > 0
    assert res_agr["results"]["ch4"]["value"] > 0

    # Thermal oxidizer destruction: destroys slipped CH4 into CO2
    res_to = agr.calculate(
        throughput=500.0,
        co2_in=0.05,
        co2_out=0.001,
        ch4_slip_fraction=0.001,
        acid_gas_control_eff=0.98,
        acid_gas_control_type="thermal_oxidizer",
    )
    # CO2 should be native CO2 + combusted CH4
    assert res_to["results"]["co2"]["value"] > res_agr["results"]["co2"]["value"]
    assert res_to["results"]["ch4"]["value"] < res_agr["results"]["ch4"]["value"]

    # AGI (Acid Gas Injection / CCUS) sequesters both
    res_agi = agr.calculate(
        throughput=500.0,
        co2_in=0.05,
        co2_out=0.001,
        ch4_slip_fraction=0.001,
        acid_gas_control_eff=0.99,
        acid_gas_control_type="agi",
    )
    assert res_agi["results"]["co2"]["value"] < res_agr["results"]["co2"]["value"]
    assert res_agi["results"]["ch4"]["value"] < res_agr["results"]["ch4"]["value"]

    # Validation: negative CO2, outlet >= 100%, slip > 1.0
    with pytest.raises(ValueError, match="cannot be negative"):
        agr.calculate(100.0, co2_in=-0.05)
    with pytest.raises(ValueError, match="Outlet CO2 must be below 100 %"):
        agr.calculate(100.0, co2_in=0.05, co2_out=1.0)
    with pytest.raises(ValueError, match="CH4 slip is a fraction"):
        agr.calculate(100.0, co2_in=0.05, ch4_slip_fraction=1.5)

    # 2. Glycol Dehydrator Calculator
    dehyd = DehydratorCalculator()
    res_dh = dehyd.calculate(
        throughput=200.0,  # 200 MMscf/yr
        ch4_content=82.0,
        control_eff=95.0,
    )
    assert res_dh["results"]["ch4"]["value"] > 0
    assert res_dh["total_co2e"] > 0

    # Validation: negative throughput, negative CH4 content, CH4 > 100%
    with pytest.raises(ValueError, match="Throughput cannot be negative"):
        dehyd.calculate(throughput=-50.0)
    with pytest.raises(ValueError, match="CH4 content cannot be negative"):
        dehyd.calculate(throughput=50.0, ch4_content=-10.0)
    with pytest.raises(ValueError, match="CH4 content cannot exceed 100 %"):
        dehyd.calculate(throughput=50.0, ch4_content=110.0)
    with pytest.raises(ValueError, match="glycol circulation rate has no API Compendium method"):
        dehyd.calculate(pump_rate=15.0)
