"""
Tests for previously untested calculation paths, Part 2:
Thermodynamic edge cases, physical bounds, correlation equations,
and multi-gas uncertainty propagation.

Covers:
- calculations/uncertainty.py (propagate_co2e_uncertainty, SRSS bounds, tier resolution)
- calculations/units.py (compound denominators, temperature conversions, ambiguous units, leap years)
- calculations/midstream.py & stoichiometry.py (negative throughput, N2O abatement)
- calculations/vented_associated_gas.py & vented_lng_distribution.py (GOR units, LNG loss rates)
- calculations/vented_completion.py (GOR method, split disposition, recovered fate)
- calculations/vented_production_tank.py (Standing correlation, EUB rule of thumb, dump valve, cylindrical volume)
- calculations/vented_production_pneumatic.py & wells & CCUS transport (pumps, EOR, marine loading)
- calculations/fugitive_onshore.py (correlations, Method 21, OGI, direct measurement)
"""

import math
import pytest
from calculations.uncertainty import (
    propagate_co2e_uncertainty,
    combine_uncertainties_sum,
    resolve_tier,
    resolve_ef_uncertainty,
    Tier,
)
from calculations.units import (
    convert_temperature,
    convert_pressure,
    _scope3_activity_in_factor_unit,
    compute_scope3_co2e,
    volume_rate_m3_per_hour,
    annual_volume_m3,
    period_volume_m3,
    parse_factor_unit,
    factor_to_kg_per_activity,
    composition_fractions,
    parse_amount,
    UnitError,
    _temp_kind,
    _pressure_unit,
)
from calculations.midstream import DehydratorCalculator
from calculations.stoichiometry import NitricAcidCalculator
from calculations.vented_associated_gas import AssociatedGasVentingCalculator
from calculations.vented_lng_distribution import (
    LNGVentingCalculator,
    DistributionPneumaticsCalculator,
    DistributionNonRoutineCalculator,
)
from calculations.vented_completion import CompletionFlowbackCalculator
from calculations.vented_production_tank import TankFlashingCalculator, BlowdownCalculator
from calculations.vented_production_pneumatic import (
    PneumaticDeviceCalculator,
    PneumaticPumpCalculator,
    GasDehydrationCalculator,
)
from calculations.vented_production_wells import (
    CO2EORVentingCalculator,
    ProductionNonRoutineVentingCalculator,
)
from calculations.vented_ccus_transport import CrudeTransportLossesCalculator
from calculations.fugitive_onshore import (
    OnshoreEquipmentFugitiveCalculator,
    OnshoreComponentFugitiveCalculator,
    OnshoreScreeningMeasurementCalculator,
    convert_fugitive_flow_to_kg_hr,
    _normalize_mol_frac,
)
from input_validation import ValidationError


# =========================================================================
# 1. UNCERTAINTY: PROPAGATE CO2E AND RESOLUTION
# =========================================================================
def test_uncertainty_propagate_co2e_and_tier_fallbacks():
    # propagate_co2e_uncertainty full multi-gas propagation
    res = propagate_co2e_uncertainty(
        e_co2={"value": 100.0, "relative_uncertainty_1sigma": 0.05},
        e_ch4=10.0,
        u_ch4=0.10,
        e_n2o=1.0,
        u_n2o=0.08,
        include_gwp_uncertainty=True,
    )
    assert res["total_co2e"] > 0
    assert res["sigma_co2e"] > 0
    assert res["relative_uncertainty_95pct"] > 0
    assert res["lower_bound_95"] < res["upper_bound_95"]

    # Without GWP parameter uncertainty
    res_no_gwp = propagate_co2e_uncertainty(
        e_co2=100.0,
        u_co2=0.05,
        e_ch4=10.0,
        u_ch4=0.10,
        include_gwp_uncertainty=False,
    )
    assert res_no_gwp["total_co2e"] > 0
    assert res_no_gwp["sigma_co2e"] < res["sigma_co2e"]

    # Custom GWP dictionary and uncertainties
    res_custom = propagate_co2e_uncertainty(
        e_co2=50.0,
        u_co2=0.02,
        e_ch4=5.0,
        u_ch4=0.05,
        gwp_dict={"CH4": 30.0, "N2O": 270.0},
        gwp_uncertainties={"ch4": 0.25, "n2o": 0.15},
    )
    assert res_custom["total_co2e"] == 50.0 + 5.0 * 30.0

    # Zero emissions edge case
    res_zero = propagate_co2e_uncertainty(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert res_zero["total_co2e"] == 0.0
    assert res_zero["relative_uncertainty_1sigma"] == 0.0

    # Additive uncertainty cancelation (total_val < 1e-12)
    assert combine_uncertainties_sum(10.0, 0.1, -10.0, 0.1) == 0.0

    # Tier resolution
    assert resolve_tier(None) == Tier.T1
    assert resolve_tier("tier3") == Tier.T3
    assert resolve_tier("tier2") == Tier.T2

    # Fallback to 15% on unknown gas
    assert resolve_ef_uncertainty("combustion", "sf6", Tier.T1) == 0.15


# =========================================================================
# 2. UNITS: ADVANCED CONVERSIONS & AMBIGUOUS BOUNDS
# =========================================================================
def test_units_additional_untested_conversions():
    # Rankine conversion
    assert pytest.approx(convert_temperature(0.0, "C", "R"), rel=1e-4) == 491.67

    # Pressure conversions
    assert pytest.approx(convert_pressure(14.696, "psia", "atm"), rel=1e-3) == 1.0
    assert pytest.approx(convert_pressure(101.325, "kpa", "psia"), rel=1e-3) == 14.696

    with pytest.raises(UnitError, match="Unknown temperature unit"):
        _temp_kind("invalid_temp_unit", "c")

    with pytest.raises(UnitError, match="Unknown pressure unit"):
        _pressure_unit("invalid_press_unit", "psig")

    # _scope3_activity_in_factor_unit
    assert pytest.approx(_scope3_activity_in_factor_unit("kg-km", "tonne-km"), rel=1e-5) == 0.001

    with pytest.raises(ValidationError, match="cannot be converted"):
        _scope3_activity_in_factor_unit("kg-km", "tonne")

    with pytest.raises(ValidationError, match="cannot be converted"):
        _scope3_activity_in_factor_unit("kg-km", "m3-km")

    # Scope 3 CO2e calculations
    res_s3_per = compute_scope3_co2e(100.0, 0.5, ef_unit="kg CO2e per MWh", activity_unit="MWh")
    assert res_s3_per == 0.05  # 100 * 0.5 kg / 1000 = 0.05 t

    with pytest.raises(ValidationError, match="ambiguous"):
        compute_scope3_co2e(100.0, 0.5, ef_unit="ton CO2e/km")

    with pytest.raises(ValidationError, match="unknown mass"):
        compute_scope3_co2e(100.0, 0.5, ef_unit="unknown_mass CO2e/km")

    # Volume rates & leap years
    v_hr = volume_rate_m3_per_hour("scf", plain_volume_per="hour")
    v_day = volume_rate_m3_per_hour("scf", plain_volume_per="day")
    assert v_hr > 0 and v_day > 0

    assert annual_volume_m3(100.0, "scf/day") > 0
    assert annual_volume_m3(100.0, "m3") == 100.0

    # Leap year Feb (29 days out of 366)
    v_leap = period_volume_m3(3660.0, "m3/year", year=2024, month=2)
    assert pytest.approx(v_leap, rel=1e-5) == 290.0

    # parse_factor_unit and factor_to_kg_per_activity
    spec_ch4 = parse_factor_unit("kgCH4/scf")
    assert spec_ch4["gas"].lower() == "ch4"

    spec_co2 = parse_factor_unit("tonneCO2/m3")
    assert spec_co2["gas"].lower() == "co2"

    with pytest.raises(UnitError, match="is not a mass unit"):
        parse_factor_unit("meters/scf")

    spec_exp = parse_factor_unit("kg/10^6 scf")
    assert spec_exp["denominators"][0][1] > 1000

    spec_word = parse_factor_unit("kg/million scf")
    assert spec_word["denominators"][0][1] > 1000

    with pytest.raises(UnitError, match="operating hours are required"):
        factor_to_kg_per_activity(1.0, "kg/hr", "count")

    with pytest.raises(UnitError, match="is per well but the activity is in 'm3'"):
        factor_to_kg_per_activity(1.0, "kg/well", "m3")

    with pytest.raises(UnitError, match="has no denominator compatible"):
        factor_to_kg_per_activity(1.0, "kg/hr", "m3", hours=10)

    # composition_fractions
    with pytest.raises(ValueError, match="ambiguous"):
        composition_fractions({"co2": 0.3, "n2": 0.4})

    with pytest.raises(ValueError, match="sums to"):
        composition_fractions({"c1": 80.0, "co2": 30.0})

    fr_norm, meta_norm = composition_fractions({"c1": 99.0, "co2": 0.0})
    assert meta_norm["renormalised"] is True
    assert pytest.approx(fr_norm["c1"], rel=1e-4) == 1.0

    with pytest.raises(ValueError, match="contains a comma"):
        parse_amount("1,000")


# =========================================================================
# 3. MIDSTREAM & STOICHIOMETRY BOUNDS
# =========================================================================
def test_midstream_and_stoichiometry_additional_bounds():
    dehyd = DehydratorCalculator()
    with pytest.raises(ValueError, match="Throughput cannot be negative"):
        dehyd.calculate(throughput=-5.0)

    with pytest.raises(ValueError, match="CH4 content cannot be negative"):
        dehyd.calculate(throughput=10.0, ch4_content=-0.1)

    na = NitricAcidCalculator()
    with pytest.raises(ValueError, match="N2O emission factor cannot be negative"):
        na.calculate(production_amount=100.0, ef_n2o=-1.0)

    with pytest.raises(ValueError, match="Abatement efficiency cannot be negative"):
        na.calculate(production_amount=100.0, abatement_efficiency=-0.1)

    with pytest.raises(ValueError, match="Abatement efficiency cannot exceed 100 %"):
        na.calculate(production_amount=100.0, abatement_efficiency=150.0)


# =========================================================================
# 4. VENTED ASSOCIATED & LNG BOUNDS
# =========================================================================
def test_vented_associated_and_lng_additional_bounds():
    ag = AssociatedGasVentingCalculator()
    with pytest.raises(ValueError, match="Control efficiency must be between 0.0 and 1.0"):
        ag.calculate(oil_production=100.0, gor=500.0, control_efficiency=-0.2, tier="tier1")

    with pytest.raises(ValueError, match="Unknown GOR unit"):
        ag.calculate(oil_production=100.0, gor=500.0, gor_unit="bad_u/bad_v", tier="tier2")

    lng = LNGVentingCalculator()
    with pytest.raises(ValueError, match="transfer_volume cannot be negative"):
        lng.calculate(activity="loading_transfer", transfer_volume_m3=-10.0)

    with pytest.raises(ValueError, match="ch4_content cannot be negative"):
        lng.calculate(activity="loading_transfer", transfer_volume_m3=100.0, ch4_content=-0.1)

    with pytest.raises(ValueError, match="vented_gas cannot be negative"):
        lng.calculate(activity="direct_bog_vent", vented_gas_scf=-50.0)

    dp = DistributionPneumaticsCalculator()
    with pytest.raises(ValueError, match="ch4_content cannot be negative"):
        dp.calculate(controller_count=5, ch4_content=-0.1)

    dn = DistributionNonRoutineCalculator()
    with pytest.raises(ValueError, match="co2_content cannot be negative"):
        dn.calculate(activity="mr_station_blowdown", count_or_miles=5, co2_content=-0.05)


# =========================================================================
# 5. COMPLETION FLOWBACK: GOR & SPLIT DISPOSITION
# =========================================================================
def test_completion_gor_and_split_disposition():
    comp = CompletionFlowbackCalculator()

    # Tier 2: Liquid Flowback * GOR method
    res_gor = comp.calculate(
        calculation_method="gor",
        liquid_flowback_bbl=500.0,
        gas_oil_ratio=200.0,
        gas_produced_sales_scf=10000.0,
        ch4_content=0.85,
    )
    assert res_gor["total_co2e"] > 0
    assert "Liquid Flowback" in res_gor["metadata"]["calculation_method"]

    # Rate * Duration with duration_hours
    res_hours = comp.calculate(
        calculation_method="rate_duration",
        daily_production_rate=50000.0,
        vent_duration_hours=48.0,
        ch4_content=0.85,
    )
    assert res_hours["total_co2e"] > 0

    # Disposition: split
    res_split = comp.calculate(
        calculation_method="flowback_rate",
        flowback_rate=1000.0,
        flowback_duration_hours=10.0,
        ch4_content=0.85,
        disposition="split",
        frac_vented=0.5,
        frac_flared=0.3,
        frac_recovered=0.2,
    )
    assert res_split["total_co2e"] > 0

    # Split fractions do not sum to 100%
    with pytest.raises(ValueError, match="must sum to 100%"):
        comp.calculate(
            calculation_method="flowback_rate",
            flowback_rate=1000.0,
            flowback_duration_hours=10.0,
            ch4_content=0.85,
            disposition="split",
            frac_vented=0.5,
            frac_flared=0.2,
            frac_recovered=0.1,
        )

    # Recovered disposition
    res_rec = comp.calculate(
        calculation_method="flowback_rate",
        flowback_rate=1000.0,
        flowback_duration_hours=10.0,
        ch4_content=0.85,
        disposition="recovered",
    )
    assert res_rec["results"]["ch4"]["value"] == 0.0

    # Negative rate error
    with pytest.raises(ValueError, match="cannot be negative"):
        comp.calculate(calculation_method="flowback_rate", flowback_rate=-10.0, flowback_duration_hours=10.0)


# =========================================================================
# 6. PRODUCTION TANK: UNTESTED METHODS & BLOWDOWN CYLINDER
# =========================================================================
def test_production_tank_and_blowdown_untested_methods():
    tank = TankFlashingCalculator()

    # Standing correlation
    res_standing = tank.calculate(
        throughput=1000.0,
        method="standing",
        api_gravity=45.0,
        separator_pressure_psig=50.0,
        separator_temp_f=100.0,
    )
    assert res_standing["total_co2e"] > 0
    assert res_standing["inputs"]["method"] == "standing"

    # EUB rule of thumb
    res_eub = tank.calculate(
        throughput=1000.0,
        method="eub",
        separator_pressure_psig=50.0,
    )
    assert res_eub["total_co2e"] > 0
    assert res_eub["inputs"]["method"] == "eub"

    # Dump valve with hours (crude and condensate)
    res_dump_crude = tank.calculate(
        throughput=1000.0,
        method="dump_valve",
        dump_valve_hours=500.0,
        liquid_type="crude",
    )
    assert res_dump_crude["total_co2e"] > 0

    res_dump_cond = tank.calculate(
        throughput=1000.0,
        method="dump_valve",
        dump_valve_hours=500.0,
        liquid_type="condensate",
    )
    assert res_dump_cond["total_co2e"] > 0

    # Produced water with salt content
    res_water = tank.calculate(
        throughput=1000.0,
        method="produced_water",
        separator_pressure_psi=250.0,
        salt_content="10%",
        co2_content=0.0,
    )
    assert res_water["total_co2e"] > 0

    # Working loss zero factor
    res_wl_zero = tank.calculate(
        throughput=1000.0,
        method="working_loss",
        ef_ch4=0.0,
    )
    assert res_wl_zero["total_co2e"] == 0.0

    # Standard GOR approach
    res_gor = tank.calculate(throughput=1000.0, method="gor", gas_oil_ratio=150.0)
    assert res_gor["total_co2e"] > 0

    # Blowdown cylindrical volume (diameter_ft and length_ft)
    bd = BlowdownCalculator()
    res_bd_cyl = bd.calculate(
        events=2,
        pressure=100.0,
        press_unit="psig",
        diameter_ft=2.0,
        length_ft=50.0,
        liquid_volume_fraction=0.1,
    )
    assert res_bd_cyl["total_co2e"] > 0

    # Negative pressure error caught by validate_inputs
    with pytest.raises(ValueError, match="Input pressure cannot be negative"):
        bd.calculate(events=2, pressure=-20.0, press_unit="psia", blowdown_volume=10.0)


# =========================================================================
# 7. PNEUMATIC PUMP, WELLS & CCUS TRANSPORT
# =========================================================================
def test_pneumatic_wells_and_ccus_additional_branches():
    pneu = PneumaticDeviceCalculator()
    with pytest.raises(ValueError, match="Device counts cannot be negative"):
        pneu.calculate(monitoring_program=True, normal_count=-1)

    pump = PneumaticPumpCalculator()
    with pytest.raises(ValueError, match="Liquid volume cannot be negative"):
        pump.calculate(method="engineering", pump_count=1, volume_liquid_pumped_ft3=-10.0, pump_outlet_pressure_psig=50.0)

    with pytest.raises(ValueError, match="Gas temperature must be above absolute zero"):
        pump.calculate(method="engineering", pump_count=1, volume_liquid_pumped_ft3=100.0, pump_outlet_pressure_psig=50.0, gas_temperature_f=-460.0)

    dehy = GasDehydrationCalculator()
    with pytest.raises(ValueError, match="operating_days cannot be negative"):
        dehy.calculate(dehydrator_type="glycol", operating_days=-5.0)

    with pytest.raises(ValueError, match="Gas throughput cannot be negative"):
        dehy.calculate(dehydrator_type="glycol", gas_throughput_mmscfd=-1.0, operating_days=10.0)

    eor = CO2EORVentingCalculator()
    res_eor_diss = eor.calculate(
        activity="dissolved_retention",
        oil_production_bbl=1000.0,
        co2_retained_tonnes_per_bbl=0.05,
    )
    assert res_eor_diss["total_co2e"] > 0

    plat = ProductionNonRoutineVentingCalculator()
    with pytest.raises(ValueError, match="equipment_count cannot be negative"):
        plat.calculate(source_type="prv", equipment_count=-2)

    marine = CrudeTransportLossesCalculator()
    with pytest.raises(ValueError, match="ch4_weight_pct cannot be negative"):
        marine.calculate(activity="loading", volume_loaded_gal=100000.0, ch4_weight_pct=-5.0)

    with pytest.raises(ValueError, match="volume_loaded cannot be negative"):
        marine.calculate(activity="loading", volume_loaded_gal=-1000.0)

    res_ballast = marine.calculate(activity="ballasting", ballast_water_bbl=5000.0)
    assert res_ballast["total_co2e"] > 0

    with pytest.raises(ValueError, match="ballast_water cannot be negative"):
        marine.calculate(activity="ballasting", ballast_water_gal=-1000.0)


# =========================================================================
# 8. FUGITIVE ONSHORE: COMPONENT, CORRELATION, OGI & DIRECT MEASUREMENT
# =========================================================================
def test_fugitive_onshore_additional_exhaustive_branches():
    with pytest.raises(ValueError, match="mole fraction cannot be negative"):
        _normalize_mol_frac(-0.1, "CH4")

    with pytest.raises(ValueError, match="Measured flow rate cannot be negative"):
        convert_fugitive_flow_to_kg_hr(-1.0, "scf/hr")

    with pytest.raises(ValueError, match="Sum of CH4 and CO2 mole fractions cannot exceed 100 %"):
        convert_fugitive_flow_to_kg_hr(1.0, "scf/hr", ch4_mol=0.8, co2_mol=0.3)

    eq = OnshoreEquipmentFugitiveCalculator()
    with pytest.raises(ValueError, match="is not CH4-specific"):
        eq.calculate(equipment_type="wellhead", equipment_count=1, factor_value=1.0, factor_unit="kg TOC/well/hr", ch4_wt_fraction=None)

    with pytest.raises(ValueError, match="CH4 weight fraction must be between 0 and 100 %"):
        eq.calculate(equipment_type="wellhead", equipment_count=1, factor_value=1.0, factor_unit="kg TOC/well/hr", ch4_wt_fraction=-0.1)

    comp = OnshoreComponentFugitiveCalculator()
    with pytest.raises(ValueError, match="cannot be negative"):
        comp.calculate(component_counts={"valve": -5}, service_type="gas")

    with pytest.raises(ValueError, match="Table 7-12 has no factor"):
        comp.calculate(component_counts={"unknown_valve": 5}, service_type="gas")

    res_comp_ef = comp.calculate(
        component_counts={"valve": {"count": 10, "ef": 0.05, "unit": "kg CH4/hr/component"}},
        service_type="gas",
    )
    assert res_comp_ef["total_co2e"] > 0

    screen = OnshoreScreeningMeasurementCalculator()
    with pytest.raises(ValueError, match="Unknown correlation component"):
        screen.calculate_correlation_equation(component_type="unknown_comp", service_type="gas", screening_values_ppm=[100.0])

    with pytest.raises(ValueError, match="must be a whole number of components"):
        screen.calculate_correlation_equation(component_type="valve", service_type="gas", screening_values_ppm=[100.0], zero_count=-1)

    with pytest.raises(ValueError, match="Enter at least one screened component"):
        screen.calculate_correlation_equation(component_type="valve", service_type="gas", screening_values_ppm=[], zero_count=0)

    with pytest.raises(ValueError, match="CH4 weight fraction must be between 0 and 100 %"):
        screen.calculate_correlation_equation(component_type="valve", service_type="gas", screening_values_ppm=[100.0], ch4_content=-0.1)

    with pytest.raises(ValueError, match="Operating hours cannot be negative"):
        screen.calculate_correlation_equation(component_type="valve", service_type="gas", screening_values_ppm=[100.0], operating_hours=-10)

    with pytest.raises(ValueError, match="Table 7-23 has no leaker factor"):
        screen.calculate_ogi_survey(component_type="unknown_comp", service_type="gas", leakers_detected=1)

    with pytest.raises(ValueError, match="Operating hours cannot be negative"):
        screen.calculate_ogi_survey(component_type="valve", service_type="gas", leakers_detected=1, operating_hours=-10)

    with pytest.raises(ValueError, match="cannot exceed 100 %"):
        screen.calculate_ogi_survey(component_type="valve", service_type="gas", leakers_detected=1, ch4_mol=0.8, co2_mol=0.3)

    with pytest.raises(ValueError, match="Measured flow rate cannot be negative"):
        screen.calculate_direct_measurement(measured_rate=-5.0)

    with pytest.raises(ValueError, match="must be between 0 and 8,784"):
        screen.calculate_direct_measurement(measured_rate=10.0, operating_hours=9000)
