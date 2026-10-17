"""
Tests for previously untested calculation paths, boundary conditions, and thermodynamic edge cases.
Validates exact branches across:
- calculations/vented_exploration.py
- calculations/midstream.py
- calculations/vented_associated_gas.py
- calculations/vented_completion.py
- calculations/vented_lng_distribution.py
- calculations/vented_production_tank.py
- calculations/vented_production_pneumatic.py
- calculations/vented_production_wells.py
- calculations/fugitive_onshore.py
- calculations/uncertainty.py
- calculations/units.py
- calculations/dispatcher.py and dispatcher branches
"""

import math
import pytest
from calculations.vented_exploration import WellTestingCalculator, CoalSeamDrillingCalculator
from calculations.midstream import AGRCalculator, DehydratorCalculator
from calculations.vented_associated_gas import AssociatedGasVentingCalculator
from calculations.vented_completion import CompletionFlowbackCalculator
from calculations.vented_lng_distribution import (
    LNGVentingCalculator,
    DistributionPneumaticsCalculator,
    DistributionNonRoutineCalculator,
)
from calculations.vented_production_tank import BlowdownCalculator
from calculations.vented_production_pneumatic import PneumaticDeviceCalculator
from calculations.vented_production_wells import CO2EORVentingCalculator
from calculations.fugitive_onshore import (
    OnshoreFacilityFugitiveCalculator,
    OnshoreEquipmentFugitiveCalculator,
    OnshoreComponentFugitiveCalculator,
    OnshoreScreeningMeasurementCalculator,
    convert_fugitive_flow_to_kg_hr,
    _normalize_mol_frac,
)
from calculations.uncertainty import (
    srss_inventory,
    monte_carlo_simulation,
    propagate_uncertainty,
    resolve_ef_uncertainty,
)
from calculations.units import (
    to_fahrenheit,
    to_psia,
    to_celsius,
    from_psia,
    convert_temperature,
    normalize_gas_volume_to_standard,
    normalize_efficiency,
    scope3_ef_kg_per_unit,
    compute_scope3_co2e,
    to_base,
    period_volume_m3,
    parse_factor_unit,
    factor_to_kg_per_activity,
    per_source_hour_kg,
    composition_fractions,
    UnitError,
    STD_TEMP_F,
    STD_TEMP_C,
    STD_PRESSURE_PSIA,
)
from calculations.dispatcher import CalculationDispatcher


# =========================================================================
# 1. VENTED EXPLORATION PATHS
# =========================================================================
def test_vented_exploration_auto_tier_and_unit_conversions():
    wt = WellTestingCalculator()

    # Tier auto-detection: Tier 3 when measured_gas_volume is passed without tier
    res_t3_m3 = wt.calculate(
        well_type="gas", measured_gas_volume=1000.0, volume_unit="m3", ch4_content=0.85, co2_content=0.05
    )
    assert res_t3_m3["total_co2e"] > 0
    assert "Direct Metered Volume" in res_t3_m3["metadata"]["equation"]

    # Tier 3 with sm3 and mmscf units
    res_t3_sm3 = wt.calculate(
        well_type="gas", measured_gas_volume=1000.0, volume_unit="sm3", ch4_content=0.85, co2_content=0.05
    )
    assert pytest.approx(res_t3_sm3["total_co2e"], rel=1e-4) == res_t3_m3["total_co2e"]

    res_t3_mmscf = wt.calculate(
        well_type="gas", measured_gas_volume=0.0353147, volume_unit="mmscf", ch4_content=0.85, co2_content=0.05
    )
    assert pytest.approx(res_t3_mmscf["total_co2e"], rel=1e-2) == res_t3_m3["total_co2e"]

    # Tier auto-detection: Tier 2 gas well from gas_production_rate + test_duration_days
    res_t2_gas = wt.calculate(
        well_type="gas", gas_production_rate=500.0, test_duration_days=2.0, rate_unit="m3/day", ch4_content=0.85, co2_content=0.05
    )
    assert "Equation 6-1" in res_t2_gas["metadata"]["equation"]

    # Tier 2 gas well with other rate units: mmscf/day, scf/hr, m3/hr
    res_t2_mmscf = wt.calculate(
        well_type="gas", gas_production_rate=0.5, test_duration_days=1.0, rate_unit="mmscf/day", tier="tier2"
    )
    res_t2_scf_hr = wt.calculate(
        well_type="gas", gas_production_rate=1000.0, test_duration_days=1.0, rate_unit="scf/hr", tier="tier2"
    )
    res_t2_m3_hr = wt.calculate(
        well_type="gas", gas_production_rate=50.0, test_duration_days=1.0, rate_unit="m3/hr", tier="tier2"
    )
    assert res_t2_mmscf["total_co2e"] > 0
    assert res_t2_scf_hr["total_co2e"] > 0
    assert res_t2_m3_hr["total_co2e"] > 0

    # Tier auto-detection: Tier 2 oil well from GOR and oil production
    res_t2_oil = wt.calculate(
        well_type="oil", gor=50.0, gor_unit="m3/m3", oil_production_rate=100.0, oil_rate_unit="m3/day", test_duration_days=2.0
    )
    assert "Equation 6-3" in res_t2_oil["metadata"]["equation"]

    # Oil well error boundaries
    with pytest.raises(ValueError, match="Oil well testing Tier 2 requires non-negative GOR"):
        wt.calculate(well_type="oil", gor=-10.0, oil_production_total=100.0, tier="tier2")


def test_exploration_drilling_percentage_inputs():
    dc = CoalSeamDrillingCalculator()
    # ch4_content and co2_content passed as percentages > 1.0 (e.g. 85.0% and 10.0%)
    res = dc.calculate(drilling_gas_vented_scf=100_000.0, ch4_content=85.0, co2_content=10.0)
    assert res["total_co2e"] > 0
    assert res["results"]["ch4"]["value"] > 0
    assert res["results"]["co2"]["value"] > 0


# =========================================================================
# 2. MIDSTREAM PATHS
# =========================================================================
def test_midstream_agr_and_dehydrator_untested_bounds():
    agr = AGRCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        agr.calculate(throughput=10.0, co2_in=-0.05, co2_out=0.01)

    with pytest.raises(ValueError, match="CO2 concentrations cannot be negative"):
        agr.calculate(throughput=10.0, co2_in=0.05, co2_out=-0.01)

    with pytest.raises(ValueError, match="CO2 concentration cannot exceed 100 %"):
        agr.calculate(throughput=10.0, co2_in=150.0, co2_out=1.0)

    dehyd = DehydratorCalculator()
    with pytest.raises(ValueError, match="CH4 content cannot exceed 100 %"):
        dehyd.calculate(throughput=10.0, ch4_content=150.0)


# =========================================================================
# 3. ASSOCIATED GAS VENTING PATHS
# =========================================================================
def test_vented_associated_gas_untested_branches():
    ag = AssociatedGasVentingCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        ag.calculate(oil_production=-50.0, gor=500.0, tier="tier2")

    with pytest.raises(ValueError, match="cannot be negative"):
        ag.calculate(oil_production=100.0, gor=-50.0, tier="tier2")

    with pytest.raises(ValueError, match="cannot be negative"):
        ag.calculate(vent_volume=-100.0, tier="tier3")

    with pytest.raises(ValueError, match="Unknown tier for Associated Gas Venting"):
        ag.calculate(oil_production=100.0, gor=500.0, ch4_content=0.8, tier="Tier 99")


# =========================================================================
# 4. VENTED COMPLETION PATHS
# =========================================================================
def test_vented_completion_scf_day_unit():
    comp = CompletionFlowbackCalculator()
    res = comp.calculate(
        calculation_method="rate_duration",
        daily_production_rate=50000.0,
        prod_rate_unit="scf/day",
        vent_duration_days=2.0,
        ch4_content=0.85,
    )
    assert res["total_co2e"] > 0
    assert res["results"]["ch4"]["value"] > 0
    assert "Eq. 6-7" in res["metadata"]["calculation_method"]


# =========================================================================
# 5. LNG & DISTRIBUTION VENTING PATHS
# =========================================================================
def test_vented_lng_and_distribution_negative_guards():
    lng = LNGVentingCalculator()
    with pytest.raises(ValueError, match="co2_content cannot be negative"):
        lng.calculate(activity="loading_transfer", transfer_volume_m3=100.0, co2_content=-0.05)

    dp = DistributionPneumaticsCalculator()
    with pytest.raises(ValueError, match="co2_content cannot be negative"):
        dp.calculate(controller_type="average", controller_count=5, co2_content=-0.05)

    dn = DistributionNonRoutineCalculator()
    with pytest.raises(ValueError, match="ch4_content cannot be negative"):
        dn.calculate(activity="mr_station_blowdown", count_or_miles=5, ch4_content=-0.05)


# =========================================================================
# 6. PRODUCTION TANK, PNEUMATICS, AND WELLS PATHS
# =========================================================================
def test_blowdown_pneumatic_and_wells_untested_bounds():
    bd = BlowdownCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        bd.calculate(events=-1, pressure=100.0, blowdown_volume=10.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        bd.calculate(events=1, pressure=100.0, blowdown_volume=-10.0)

    with pytest.raises(ValueError, match="cannot be negative"):
        bd.calculate(events=1, pressure=-20.0, press_unit="psig", blowdown_volume=10.0)

    pneu = PneumaticDeviceCalculator()
    with pytest.raises(ValueError, match="Year fractions cannot be negative"):
        pneu.calculate(monitoring_program=True, normal_count=5, normal_fraction_year=-0.2)

    eor = CO2EORVentingCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        eor.calculate(
            activity="pump_blowdown",
            physical_volume_m3=10.0,
            co2_density_kg_m3=-1.5,
            co2_weight_fraction=0.5,
        )

    with pytest.raises(ValueError, match="cannot be negative"):
        eor.calculate(
            activity="pump_blowdown",
            physical_volume_m3=10.0,
            co2_density_kg_m3=1.8,
            co2_weight_fraction=-0.1,
        )


# =========================================================================
# 7. FUGITIVE ONSHORE PATHS
# =========================================================================
def test_fugitive_onshore_untested_conversions_and_bounds():
    # _normalize_mol_frac with value > 100%
    with pytest.raises(ValueError, match="CH4 mole fraction must be between 0 and 100 %"):
        _normalize_mol_frac(150.0, "CH4")

    # convert_fugitive_flow_to_kg_hr volume rate without CH4
    with pytest.raises(ValueError, match="A volumetric leak rate needs the gas CH4 content"):
        convert_fugitive_flow_to_kg_hr(10.0, "mcf/day", ch4_mol=None)

    with pytest.raises(ValueError, match="Unknown leak rate unit 'invalid_leak_unit'"):
        convert_fugitive_flow_to_kg_hr(10.0, "invalid_leak_unit", ch4_mol=0.8)

    # Facility fugitives production units: m3, mm3
    fac = OnshoreFacilityFugitiveCalculator()
    res_m3 = fac.calculate(production=1_000_000.0, production_unit="m3", facility_type="gas_production")
    res_mm3 = fac.calculate(production=1.0, production_unit="mm3", facility_type="gas_production")
    assert pytest.approx(res_m3["total_co2e"], rel=1e-5) == res_mm3["total_co2e"]

    with pytest.raises(ValueError, match="cannot be negative"):
        fac.calculate(production=-100.0, production_unit="bbl", facility_type="oil_production")

    # Equipment fugitives bounds
    eq = OnshoreEquipmentFugitiveCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        eq.calculate(equipment_type="wellhead", equipment_count=-5, factor_value=1.0)

    with pytest.raises(ValueError, match="Operating hours .* must be between 0 and 8,784"):
        eq.calculate(
            equipment_type="wellhead", equipment_count=1, operating_hours=9000, factor_value=1.0
        )

    # Screening measurement errors
    screen = OnshoreScreeningMeasurementCalculator()
    with pytest.raises(ValueError, match="Table 7-26 has no screening factor"):
        screen.calculate_method21_ranges(component_type="unknown_device", service_type="gas", non_pegged_count=1, pegged_count=0)

    with pytest.raises(ValueError, match="Component counts cannot be negative"):
        screen.calculate_method21_ranges(
            component_type="valve", service_type="gas", non_pegged_count=-1, pegged_count=0
        )

    with pytest.raises(ValueError, match="Enter the number of components below and / or at or above 10,000 ppmv"):
        screen.calculate_method21_ranges(
            component_type="valve", service_type="gas", non_pegged_count=0, pegged_count=0
        )

    with pytest.raises(ValueError, match="Operating hours cannot be negative"):
        screen.calculate_method21_ranges(
            component_type="valve", service_type="gas", non_pegged_count=5, pegged_count=0, operating_hours=-10
        )

    # Correlation equation checks
    with pytest.raises(ValueError, match="Screening concentration cannot be negative"):
        screen.calculate_correlation_equation(
            component_type="valve", service_type="gas", screening_values_ppm=[-50.0]
        )

    # Correlation with zero ppm count and list of 0s
    res_zero = screen.calculate_correlation_equation(
        component_type="valve", service_type="gas", screening_values_ppm=[0.0, 100.0], zero_count=1
    )
    assert res_zero["total_co2e"] > 0

    # OGI survey checks
    with pytest.raises(ValueError, match="Detected leakers must be a whole number"):
        screen.calculate_ogi_survey(component_type="valve", service_type="gas", leakers_detected=2.5)

    with pytest.raises(ValueError, match="cannot exceed total surveyed"):
        screen.calculate_ogi_survey(
            component_type="valve", service_type="gas", leakers_detected=5, total_surveyed=3
        )


# =========================================================================
# 8. UNCERTAINTY MODULE PATHS
# =========================================================================
def test_uncertainty_untested_paths():
    # srss_inventory fallback when relative_uncertainty is None
    res_comb = srss_inventory(
        [
            {"value": 100.0, "uncertainty": 0.1},
            {"value": 200.0, "uncertainty_1sigma": 0.05},
        ]
    )
    assert res_comb["total_value"] == 300.0
    assert res_comb["relative_uncertainty_95pct"] > 0

    # Total value <= 0
    res_zero = srss_inventory([{"value": 0.0, "uncertainty": 0.05}])
    assert res_zero["relative_uncertainty_95pct"] == 0.0

    # monte_carlo_simulation empty list
    mc_empty = monte_carlo_simulation([])
    assert mc_empty["mean"] == 0.0
    assert mc_empty["iterations"] == 10000

    # monte_carlo_simulation purely deterministic (value <= 0 or u_rel == 0)
    mc_det = monte_carlo_simulation([{"value": 50.0, "uncertainty": 0.0}])
    assert mc_det["mean"] == 50.0
    assert mc_det["std"] == 0.0

    # propagate_uncertainty with uncertainties_dict overrides
    res_prop = propagate_uncertainty(
        100.0,
        0.05,
        uncertainties_dict={"_activity_uncertainty": 0.08, "_composition_uncertainty": 0.04},
    )
    assert res_prop["relative_uncertainty_95pct"] > 0

    # propagate_uncertainty with unparseable strings gracefully fallback to 0.05
    res_str = propagate_uncertainty(100.0, "invalid_ef", activity_uncertainty="invalid_act")
    assert res_str["relative_uncertainty_95pct"] > 0

    # resolve_ef_uncertainty fallback on unknown process category
    unc_fallback = resolve_ef_uncertainty("unknown_category", "ch4", "T1")
    assert unc_fallback == 0.15


# =========================================================================
# 9. UNITS MODULE PATHS
# =========================================================================
def test_units_untested_branches():
    assert to_fahrenheit(None) == STD_TEMP_F
    assert to_psia(None) == STD_PRESSURE_PSIA
    assert to_celsius(None) == STD_TEMP_C
    assert from_psia(None) == 0.0
    assert normalize_gas_volume_to_standard(0.0) == 0.0
    assert normalize_gas_volume_to_standard(-10.0) == 0.0

    with pytest.raises(UnitError, match="A target temperature unit is required"):
        convert_temperature(100, "C", None)

    # normalize_efficiency
    assert normalize_efficiency("invalid_pct", default=0.5) == 0.5
    assert normalize_efficiency(-10.0) == 0.0

    # scope3_ef_kg_per_unit
    assert scope3_ef_kg_per_unit("invalid", "invalid", ef=2.5) == 2.5

    # compute_scope3_co2e
    assert compute_scope3_co2e("invalid", 1.0) == 0.0
    assert compute_scope3_co2e(0.0, 1.0) == 0.0
    assert compute_scope3_co2e(-5.0, 1.0) == 0.0

    from input_validation import ValidationError
    with pytest.raises(ValidationError, match="ambiguous"):
        compute_scope3_co2e(10.0, 1.0, ef_unit="kg CO2e/ton")

    # to_base dimension mismatch
    with pytest.raises(UnitError, match="Unit 'kg' is a mass unit, expected energy"):
        to_base(10, "kg", dimension="energy")

    # period_volume_m3 with non-integer year/month
    vol = period_volume_m3(100.0, "MMscf/d", year="invalid", month="invalid")
    assert vol > 0

    # parse_factor_unit error paths
    with pytest.raises(UnitError, match="has no denominator"):
        parse_factor_unit("kg")

    with pytest.raises(UnitError, match="has no numerator"):
        parse_factor_unit("/scf")

    with pytest.raises(UnitError, match="ambiguous"):
        parse_factor_unit("ton/scf")

    with pytest.raises(UnitError, match="has a zero denominator"):
        parse_factor_unit("kg/0 scf")

    # factor_to_kg_per_activity error paths
    with pytest.raises(UnitError, match="needs the fuel heating value"):
        factor_to_kg_per_activity(1.0, "kg/MMBtu", "m3")

    with pytest.raises(UnitError, match="cannot be applied to activity unit"):
        factor_to_kg_per_activity(1.0, "kg/meter", "scf")

    # per_source_hour_kg without time denominator
    with pytest.raises(UnitError, match="has no time basis"):
        per_source_hour_kg(1.0, "kg/source")

    # composition_fractions edge cases
    cf, _ = composition_fractions({"c1": 90.0, "co2": None, "c2": "", "c3": "-"})
    assert "c1" in cf
    assert "co2" not in cf

    with pytest.raises(ValueError, match="must be a finite, non-negative number"):
        composition_fractions({"c1": -5.0})

    with pytest.raises(ValueError, match="must be a finite, non-negative number"):
        composition_fractions({"c1": float("inf")})


# =========================================================================
# 10. DISPATCHER & DISPATCHER BRANCHES PATHS
# =========================================================================
def test_dispatcher_untested_branches():
    disp = CalculationDispatcher()

    # _require missing field
    with pytest.raises(ValueError, match="Missing required field: throughput"):
        disp._require("throughput", {}, "gas throughput")

    # _normalize_volume unsupported target
    with pytest.raises(ValueError, match="Unsupported target volume unit 'liters'"):
        disp._normalize_volume(100.0, "m3", target_unit="liters")

    # _liquid_bbl gas unit error
    with pytest.raises(ValueError, match="is a gas volume; give the liquid volume"):
        disp._liquid_bbl(100.0, "scf", "tank oil throughput")

    # _require_float invalid numeric
    with pytest.raises(ValueError, match="Invalid numeric value"):
        disp._require_float({"rate": "not_a_number"}, "rate", "flow rate")

    # _fuel_density non-positive
    with pytest.raises(ValueError, match="Fuel density must be a positive number"):
        disp._fuel_density({"density": -500.0})

    # dispatch with non-numeric amount
    with pytest.raises(ValueError, match="Invalid numeric quantity/amount"):
        disp.dispatch("combustion", {"amount": "abc", "unit": "m3", "fuel": "natural_gas"}, {})

    # generic calculation amount < 0
    with pytest.raises(ValueError, match="Activity amount must be a finite, non-negative number"):
        disp._generic_calculation({"amount": -10.0}, {"unit": "kg/m3", "co2": 1.0}, {})

    # generic calculation missing unit
    with pytest.raises(ValueError, match="Missing required field: unit"):
        disp._generic_calculation({"amount": 10.0}, {"unit": "kg/m3", "co2": 1.0}, {})


def test_exploration_additional_tier_and_rate_checks():
    wt = WellTestingCalculator()
    # Auto-detection falling back to Tier 1 default when no rate/volume is passed
    res_t1 = wt.calculate(well_type="gas_exploratory", events=2)
    assert res_t1["total_co2e"] > 0
    assert "Table 6-4" in res_t1["metadata"]["equation"]

    # Tier 2 gas well negative rate error
    with pytest.raises(ValueError, match="Gas well testing Tier 2 requires non-negative gas_production_rate"):
        wt.calculate(well_type="gas", tier="tier2", gas_production_rate=-5.0, test_duration_days=1.0)


def test_uncertainty_additional_edge_cases():
    # composition_uncertainty with unparseable string gracefully ignored
    res_str = propagate_uncertainty(100.0, 0.05, composition_uncertainty="invalid_comp")
    assert res_str["relative_uncertainty_95pct"] > 0

    # resolve_ef_uncertainty with invalid tier fallback to 0.15
    unc_fallback = resolve_ef_uncertainty("combustion", "ch4", "T99")
    assert unc_fallback == 0.15


def test_units_scale_activity_and_denominators():
    from input_validation import ValidationError
    with pytest.raises(ValidationError, match="cannot be matched to the factor's unit"):
        compute_scope3_co2e(100.0, 1.0, ef_unit="kg CO2e/tonne", activity_unit="invalid_unit")

    with pytest.raises(UnitError, match="has an empty denominator"):
        parse_factor_unit("kg/  ")

    with pytest.raises(UnitError, match="has more than one activity denominator"):
        factor_to_kg_per_activity(1.0, "kg/scf/m3", "scf")


def test_dispatcher_branches_fugitive_exhaustive():
    disp = CalculationDispatcher()
    # time_unit conversions: day, month, year
    res_day = disp.dispatch("fugitive", {"amount": 5, "unit": "count", "component_type": "valve", "time_unit": "days", "operating_days": 10, "service": "gas"}, {"unit": "kg/hr/source", "ch4": 0.005})
    res_mo = disp.dispatch("fugitive", {"amount": 5, "unit": "count", "component_type": "valve", "time_unit": "months", "operating_days": 2, "service": "gas"}, {"unit": "kg/hr/source", "ch4": 0.005})
    res_yr = disp.dispatch("fugitive", {"amount": 5, "unit": "count", "component_type": "valve", "time_unit": "years", "operating_days": 1, "service": "gas"}, {"unit": "kg/hr/source", "ch4": 0.005})
    assert res_day["total_co2e"] > 0
    assert res_mo["total_co2e"] > 0
    assert res_yr["total_co2e"] > 0

    # process_type="facility_fugitive"
    res_fac = disp.dispatch("facility_fugitive", {"amount": 100000.0, "unit": "bbl", "facility_type": "oil_production"}, {})
    assert res_fac["total_co2e"] > 0

    # sub_mode auto-detects ogi when leakers_count is passed
    res_ogi = disp.dispatch("fugitive", {"factor_source": "specific", "fugitive_tier": "tier3", "leakers_count": 2, "component_type": "valve", "service_type": "gas", "operating_hours": 100}, {})
    assert res_ogi["total_co2e"] > 0

    # screening_values_ppm parsed from comma-separated string
    res_corr_str = disp.dispatch("fugitive", {"factor_source": "specific", "fugitive_tier": "tier3", "fugitive_method": "correlation", "component_type": "valve", "service_type": "gas", "screening_values_ppm": "100, 200, 300", "operating_hours": 100}, {})
    assert res_corr_str["total_co2e"] > 0

    # single fugitive_ppm with amount=3
    res_corr_single = disp.dispatch("fugitive", {"factor_source": "specific", "fugitive_tier": "tier3", "fugitive_method": "correlation", "component_type": "valve", "service_type": "gas", "fugitive_ppm": 250.0, "amount": 3, "operating_hours": 100}, {})
    assert res_corr_single["total_co2e"] > 0

    # unknown fugitive Tier 3 method
    with pytest.raises(ValueError, match="Unknown fugitive Tier 3 method"):
        disp.dispatch("fugitive", {"factor_source": "specific", "fugitive_tier": "tier3", "fugitive_method": "unknown_tier3_method", "component_type": "valve"}, {})


def test_dispatcher_branches_venting_and_combustion_exhaustive():
    disp = CalculationDispatcher()
    # Flaring with ch4_content without c1
    res_flare = disp.dispatch("flaring", {"factor_source": "specific", "amount": 1000.0, "unit": "scf", "flare_type": "open", "ch4_content": 0.85}, {})
    assert res_flare["total_co2e"] > 0

    # Tank venting with non-per-bbl factor unit setting ef_ch4_kg_bbl = 0.0
    res_tank = disp.dispatch("tank_venting", {"amount": 1000.0, "unit": "bbl", "method": "flash"}, {"ch4": 0.5, "unit": "kg/scf"})
    assert res_tank["total_co2e"] > 0

    # Pneumatic bleed rate without CH4 content raises error
    with pytest.raises(ValueError, match="Missing required field: gas CH4 content"):
        disp.dispatch("pneumatics", {"factor_source": "specific", "amount": 1, "pneu_bleed_rate": 10.0, "pneu_bleed_unit": "scf/hr"}, {})
