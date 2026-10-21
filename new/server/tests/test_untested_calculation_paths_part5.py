"""
Comprehensive Test Suite Part 5 for Untested Calculation Paths & Invariants
Focus: Indirect Steam/Heat, Cogeneration Allocation, Activity Factors Matrix,
Midstream Compressors & Blanketed Tanks, Vented Gas Methods & Flare Facility Defaults.
Governing Standards: API Compendium 2021 4th Edition (Chapters 4, 5, 6, 8) & IPCC 2006 GL.
"""

import math
import pytest

from calculations.indirect import (
    heat_to_mmbtu,
    IndirectSteamCalculator,
    CogenAllocationCalculator,
)
from calculations.activity_factors import (
    ActivityFactorCalculator,
    ACTIVITY_FACTORS,
)
from calculations.vented_midstream import (
    GatheringCompressorVentingCalculator,
    GatheringStorageTankCalculator,
    GatheringNonRoutineVentingCalculator,
    ProcessingDehydrationCalculator,
    ProcessingBlanketedTankCalculator,
    ProcessingNonRoutineCalculator,
    TransmissionCompressorCalculator,
    TransmissionNonRoutineCalculator,
)
from calculations.vented_gas import VentedGasCalculator
from calculations.flare_defaults import (
    compute_emissions as flare_compute_emissions,
    facility_segment,
    PRODUCTION_DESTRUCTION,
    REFINERY_DESTRUCTION,
)
from calculations.legacy_engine import (
    compute_emissions as legacy_compute_emissions,
    MissingFactorError,
)


def test_indirect_steam_and_cogen_allocation_comprehensive():
    # 1. heat_to_mmbtu: Energy units
    assert heat_to_mmbtu(1.0, "mmbtu") == pytest.approx(1.0)
    assert heat_to_mmbtu(1000000.0, "btu") == pytest.approx(1.0)
    assert heat_to_mmbtu(10.0, "therm") == pytest.approx(1.0)
    assert heat_to_mmbtu(1055.056, "mj") == pytest.approx(1.0, rel=1e-3)
    assert heat_to_mmbtu(1.055056, "gj") == pytest.approx(1.0, rel=1e-3)
    assert heat_to_mmbtu(293.071, "kwh") == pytest.approx(1.0, rel=1e-3)
    assert heat_to_mmbtu(0.293071, "mwh") == pytest.approx(1.0, rel=1e-3)

    # heat_to_mmbtu: Steam mass units with enthalpy
    # 1000 lb steam with 1000 Btu/lb enthalpy = 1.0 MMBtu
    assert heat_to_mmbtu(1000.0, "lb", steam_enthalpy_btu_lb=1000.0) == pytest.approx(1.0)
    assert heat_to_mmbtu(1.0, "klb", steam_enthalpy_btu_lb=1000.0) == pytest.approx(1.0)
    # 1000 kg steam with 1000 Btu/lb enthalpy: 1000 * 2.20462 * 1000 / 1e6 = 2.20462 MMBtu
    assert heat_to_mmbtu(1000.0, "kg", steam_enthalpy_btu_lb=1000.0) == pytest.approx(2.20462, rel=1e-4)
    # Steam mass with steam_enthalpy in MMBtu/unit
    assert heat_to_mmbtu(5.0, "tonne", steam_enthalpy=2.5) == pytest.approx(12.5)

    # Validations
    with pytest.raises(ValueError, match="is ambiguous"):
        heat_to_mmbtu(10.0, "ton")
    with pytest.raises(ValueError, match="needs its enthalpy"):
        heat_to_mmbtu(100.0, "lb")
    with pytest.raises(ValueError, match="Unknown unit"):
        heat_to_mmbtu(100.0, "lightyears")

    # 2. IndirectSteamCalculator
    steam_calc = IndirectSteamCalculator()
    res_steam = steam_calc.calculate(
        heat_energy=500.0,
        heat_unit="mmbtu",
        ef_co2=53.06,  # 53.06 kg CO2/MMBtu
        ef_ch4=0.001,  # 0.001 kg CH4/MMBtu
        ef_n2o=0.0001, # 0.0001 kg N2O/MMBtu
        boiler_efficiency=0.85,
        transmission_loss=0.05,
        uncertainties={},
    )
    # Net efficiency = 0.85 - 0.05 = 0.80 (Exhibit 8.3)
    # Fuel MMBtu = 500 / 0.80 = 625 MMBtu
    # CO2 = 625 * 53.06 / 1000 = 33.1625 t
    expected_co2 = (500.0 / (0.85 - 0.05)) * 53.06 / 1000.0
    assert res_steam["results"]["co2"]["value"] == pytest.approx(expected_co2, rel=1e-3)
    assert res_steam["results"]["ch4"]["value"] > 0
    assert res_steam["results"]["n2o"]["value"] > 0

    with pytest.raises(ValueError, match="Boiler efficiency.*are fractions"):
        steam_calc.calculate(100.0, ef_co2=50.0, boiler_efficiency=1.5, transmission_loss=0.05, uncertainties={})
    with pytest.raises(ValueError, match="Net efficiency must be greater than 0"):
        steam_calc.calculate(100.0, ef_co2=50.0, boiler_efficiency=0.8, transmission_loss=1.0, uncertainties={})

    # 3. CogenAllocationCalculator
    cogen = CogenAllocationCalculator()
    # WRI Efficiency Method (Equation 8-5)
    # heat_mmbtu = 1000, power_mmbtu = 500, e_h = 0.80, e_p = 0.35, total_emissions = 100 t CO2
    # heat_share = 1000 / 0.80 = 1250, power_share = 500 / 0.35 = 1428.57
    # denominator = 2678.57
    # allocated_heat = (1250 / 2678.57) * 100 = 46.67 t CO2
    res_wri = cogen.calculate(
        total_emissions=100.0,
        heat_output=1000.0,
        power_output=500.0,
        method="wri_efficiency",
    )
    expected_alloc_heat = (1250.0 / (1250.0 + 500.0 / 0.35)) * 100.0
    assert res_wri["results"]["co2"]["value"] == pytest.approx(expected_alloc_heat, rel=1e-3)

    # Energy Content Method
    res_energy = cogen.calculate(
        total_emissions=100.0,
        heat_output=1000.0,
        power_output=500.0,
        method="energy_content",
    )
    # allocated_heat = (1000 / 1500) * 100 = 66.67 t CO2
    assert res_energy["results"]["co2"]["value"] == pytest.approx((1000.0 / 1500.0) * 100.0)

    # Validations
    with pytest.raises(ValueError, match="Unknown cogeneration allocation method"):
        cogen.calculate(100.0, 1000.0, 500.0, method="invalid_method")
    with pytest.raises(ValueError, match="Heat efficiency must be between 0 and 100 %"):
        cogen.calculate(100.0, 1000.0, 500.0, heat_efficiency=0.0)


def test_activity_factors_comprehensive_matrix():
    calc = ActivityFactorCalculator()

    # 1. Well Testing: wt_gas and wt_oil
    res_wt_gas = calc.calculate("wt_gas", amount=5.0, ch4_content=81.6, co2_content=2.0)
    assert res_wt_gas["results"]["ch4"]["value"] == pytest.approx(5.0 * 0.728)
    assert res_wt_gas["results"]["co2"]["value"] > 0

    res_wt_oil = calc.calculate("wt_oil", amount=10.0, ch4_content=81.6)
    assert res_wt_oil["results"]["ch4"]["value"] == pytest.approx(10.0 * 0.057)

    # 2. Workovers: wo_gas and wo_oil
    res_wo_gas = calc.calculate("wo_gas", amount=4.0)
    assert res_wo_gas["results"]["ch4"]["value"] == pytest.approx(4.0 * 0.0470)

    # 3. Casing gas: cg_primary_heavy (per bbl oil) and cg_migration (per well-day)
    res_cg_bbl = calc.calculate("cg_primary_heavy", amount=10000.0, unit="bbl")
    assert res_cg_bbl["results"]["ch4"]["value"] == pytest.approx(10000.0 * 3.28e-3)

    res_cg_day = calc.calculate("cg_migration", amount=10.0, days=180.0)
    assert res_cg_day["results"]["ch4"]["value"] == pytest.approx(10.0 * 180.0 * 0.00213)

    # 4. Dehydration: dh_glycol_production (per mmscf)
    res_dh = calc.calculate("dh_glycol_production", amount=50.0, unit="mmscf", ch4_content=78.8)
    assert res_dh["results"]["ch4"]["value"] == pytest.approx(50.0 * 0.0052859)

    # 5. AGR: throughput vs unit-day
    res_agr_tp = calc.calculate("agr_throughput", amount=100.0, unit="mmscf")
    assert res_agr_tp["results"]["ch4"]["value"] == pytest.approx(100.0 * 0.0185)

    res_agr_un = calc.calculate("agr_unit", amount=2.0, days=365.0)
    assert res_agr_un["results"]["ch4"]["value"] == pytest.approx(2.0 * 365.0 * 0.6482)

    # 6. Pneumatic controllers: gb_pc_high_bleed (unit_hr)
    res_pneu_hr = calc.calculate("gb_pc_high_bleed", amount=5.0, hours=4000.0, ch4_content=81.6)
    assert res_pneu_hr["results"]["ch4"]["value"] > 0

    # 7. Separator dump valve malfunction: crude and condensate (per bbl)
    res_sep_crude = calc.calculate("sep_dump_valve_crude", amount=50000.0, unit="bbl")
    assert res_sep_crude["results"]["ch4"]["value"] == pytest.approx(50000.0 * 2.70e-6)

    # 8. Produced water flashing: pw_250psi_10salt
    res_pw = calc.calculate("pw_250psi_10salt", amount=20000.0, unit="bbl")
    assert res_pw["results"]["ch4"]["value"] == pytest.approx(20000.0 * 0.0150e-3)

    # 9. Non-routine venting: compressor blowdown per compressor-year with year_fraction
    res_bd_comp = calc.calculate("gb_bd_compressor", amount=4.0, year_fraction=0.50)
    assert res_bd_comp["results"]["ch4"]["value"] == pytest.approx(4.0 * 0.50 * 0.07239)

    # 10. Crude loading losses: load_submerged_dedicated (TOC basis)
    res_load_toc = calc.calculate("load_submerged_dedicated", amount=2000000.0, unit="gal", toc_ch4_wt=15.0)
    # 2 Mgal * 0.91 t TOC/Mgal * 0.15 = 0.273 t CH4
    assert res_load_toc["results"]["ch4"]["value"] == pytest.approx(2.0 * 0.91 * 0.15)

    # Validations
    with pytest.raises(ValueError, match="Unknown activity factor"):
        calc.calculate("invalid_factor_key", 10.0)
    with pytest.raises(ValueError, match="Activity amount cannot be negative"):
        calc.calculate("wt_gas", -5.0)
    with pytest.raises(ValueError, match="The period must be a fraction of a year"):
        calc.calculate("gb_bd_compressor", 1.0, year_fraction=1.5)
    with pytest.raises(ValueError, match="Gas content cannot exceed 100 %"):
        calc.calculate("wt_gas", 1.0, ch4_content=150.0)


def test_vented_midstream_compressors_and_blanketed_tanks():
    # 1. GatheringCompressorVentingCalculator (Table 6-30 & Eq 6-29)
    g_comp = GatheringCompressorVentingCalculator()
    for src in ("us_zimmerle", "us_ghgrp", "canada_alberta"):
        res_gc = g_comp.calculate(
            compressor_count=3.0,
            pressurized_hours=8000.0,
            source_standard=src,
            ch4_content=82.0,
            co2_content=1.5,
            disposition="flared",
            control_efficiency=0.98,
        )
        assert res_gc["results"]["ch4"]["value"] > 0
        assert res_gc["results"]["co2"]["value"] > 0
        assert res_gc["results"]["n2o"]["value"] > 0

    # 2. GatheringStorageTankCalculator (Table 6-31)
    g_tank = GatheringStorageTankCalculator()
    for ctype in ("average_tank", "single_unit_vent", "thief_hatch"):
        res_gt = g_tank.calculate(tank_count=4.0, hours=8760.0, component_type=ctype)
        assert res_gt["results"]["ch4"]["value"] > 0

    # 3. GatheringNonRoutineVentingCalculator (Table 6-33)
    g_nr = GatheringNonRoutineVentingCalculator()
    for act in ("prv_releases", "pipeline_dig_in", "compressor_starts", "oil_pump_station"):
        res_gnr = g_nr.calculate(activity=act, events_or_count=10.0)
        assert res_gnr["results"]["ch4"]["value"] > 0

    # 4. ProcessingDehydrationCalculator (Table 6-35 & 6-36)
    proc_dehy = ProcessingDehydrationCalculator()
    # Without Kimray pump
    res_dehy_only = proc_dehy.calculate(gas_throughput_mmscfd=100.0, operating_days=300.0, has_gas_assisted_pump=False)
    # With Kimray pump: emissions increase and stoichiometric CO2 is calculated
    res_dehy_pump = proc_dehy.calculate(
        gas_throughput_mmscfd=100.0,
        operating_days=300.0,
        has_gas_assisted_pump=True,
        co2_content=2.0,
    )
    assert res_dehy_pump["results"]["ch4"]["value"] > res_dehy_only["results"]["ch4"]["value"]
    assert res_dehy_pump["results"]["co2"]["value"] > 0

    # 5. ProcessingBlanketedTankCalculator (Exhibit 6-29)
    tank_blanket = ProcessingBlanketedTankCalculator()
    # At standard 60 °F, Rankine ratio is exactly 1.0
    res_std_t = tank_blanket.calculate(
        liquid_displacement_bbl=1000.0,
        vapor_temperature_f=60.0,
        ch4_content=82.0,
    )
    # At elevated 120 °F, thermal expansion reduces standard gas volume
    res_hot_t = tank_blanket.calculate(
        liquid_displacement_bbl=1000.0,
        vapor_temperature_f=120.0,
        ch4_content=82.0,
    )
    assert res_hot_t["results"]["ch4"]["value"] < res_std_t["results"]["ch4"]["value"]

    # 6. ProcessingNonRoutineCalculator (Table 6-39)
    proc_nr = ProcessingNonRoutineCalculator()
    res_pnr_m3 = proc_nr.calculate(gas_throughput_m3_day=500000.0, operating_days=365.0)
    res_pnr_scf = proc_nr.calculate(gas_throughput_mmscfd=20.0, operating_days=365.0)
    assert res_pnr_m3["results"]["ch4"]["value"] > 0
    assert res_pnr_scf["results"]["ch4"]["value"] > 0

    # 7. TransmissionCompressorCalculator (Tables 6-40 & 6-41)
    trans_comp = TransmissionCompressorCalculator()
    # Reciprocating rod packing: operating + standby pressurized hours
    res_recip = trans_comp.calculate(
        compressor_type="reciprocating",
        compressor_count=2.0,
        operating_hours=7000.0,
        standby_pressurized_hours=1000.0,
    )
    assert res_recip["results"]["ch4"]["value"] > 0

    # Centrifugal seals: wet and dry seals
    res_cent = trans_comp.calculate(
        compressor_type="centrifugal",
        wet_seal_count=2.0,
        dry_seal_count=4.0,
    )
    assert res_cent["results"]["ch4"]["value"] > 0

    # 8. TransmissionNonRoutineCalculator (Table 6-43)
    trans_nr = TransmissionNonRoutineCalculator()
    for act in ("transmission_station", "storage_station", "pipeline_blowdown", "compressor_blowdowns"):
        res_tnr = trans_nr.calculate(activity=act, count_or_miles=5.0)
        assert res_tnr["results"]["ch4"]["value"] > 0


def test_vented_gas_volume_methods_and_flaring_stoichiometry():
    v_calc = VentedGasCalculator()

    # 1. Method "volume" with scf, mcf, mmscf, m3
    res_v_scf = v_calc.calculate("volume", {"gas_volume": 100000.0, "unit": "scf", "ch4_content": 85.0})
    res_v_m3 = v_calc.calculate("volume", {"gas_volume": 2831.68, "unit": "m3", "ch4_content": 85.0})
    assert res_v_scf["results"]["ch4"]["value"] == pytest.approx(res_v_m3["results"]["ch4"]["value"], rel=1e-3)

    # 2. Method "gor": GOR * oil rate * hours / 24.0 (Eq 6-3)
    res_gor = v_calc.calculate("gor", {
        "gor": 500.0,
        "oil_rate": 200.0,
        "vent_hours": 12.0,
        "ch4_content": 80.0,
    })
    # gas volume = 500 * 200 * 12 / 24 = 50,000 scf
    assert res_gor["intermediate"]["gas_volume_scf"] == pytest.approx(50000.0)

    # 3. Method "rate_days": gas rate * rate_unit * days
    res_rd = v_calc.calculate("rate_days", {
        "gas_rate": 10.0,
        "gas_rate_unit": "mmscf/day",
        "days": 5.0,
        "ch4_content": 90.0,
    })
    assert res_rd["intermediate"]["gas_volume_scf"] == pytest.approx(50000000.0)

    # 4. Method "actual": temperature and pressure correction (Eq 3-5)
    res_act = v_calc.calculate("actual", {
        "actual_volume": 10000.0,
        "actual_unit": "ft3",
        "gas_temp_f": 100.0,
        "gas_pressure_atm": 2.0,
        "ch4_content": 85.0,
    })
    # V_scf = 10000 * 2.0 * (519.67 / (100 + 459.67)) = 18570.6 scf
    expected_v = 10000.0 * 2.0 * (519.67 / 559.67)
    assert res_act["intermediate"]["gas_volume_scf"] == pytest.approx(expected_v)

    # 5. Method "desiccant": vessel geometry and refills (Eq 6-16)
    res_desiccant = v_calc.calculate("desiccant", {
        "vessel_height_ft": 15.0,
        "vessel_diameter_ft": 4.0,
        "vessel_pressure_psig": 200.0,
        "gas_fraction": 45.0,  # 45% void fraction
        "refills": 12.0,
        "ch4_content": 85.0,
    })
    assert res_desiccant["results"]["ch4"]["value"] > 0

    # 6. Method "co2_mass": physical volume * density * wt%
    res_co2m = v_calc.calculate("co2_mass", {
        "physical_volume_m3": 100.0,
        "co2_density": 1.85,
        "co2_wt_pct": 98.0,
        "events": 2.0,
    })
    # co2 = 2 * 100 * 1.85 * 0.98 / 1000 = 0.3626 t CO2
    assert res_co2m["results"]["co2"]["value"] == pytest.approx(2.0 * 100.0 * 1.85 * 0.98 / 1000.0)
    assert res_co2m["results"]["ch4"]["value"] == 0.0

    # 7. Method "reported_mass" and "thc_mass"
    res_rep = v_calc.calculate("reported_mass", {"ch4_mass": 10.0, "co2_mass": 5.0, "control_efficiency": 90.0})
    assert res_rep["results"]["ch4"]["value"] == pytest.approx(1.0)
    assert res_rep["results"]["co2"]["value"] == pytest.approx(0.5)

    res_thc = v_calc.calculate("thc_mass", {"thc_loss": 20.0, "ch4_wt_pct": 70.0, "co2_wt_pct": 10.0})
    assert res_thc["results"]["ch4"]["value"] == pytest.approx(14.0)
    assert res_thc["results"]["co2"]["value"] == pytest.approx(2.0)

    # 8. Method "agr_balance": sour CO2 - sweet CO2 with Table 6-19 throughput CH4
    res_agr = v_calc.calculate("agr_balance", {
        "sour_gas_volume": 100.0,
        "sweet_gas_volume": 90.0,
        "gas_volume_unit": "mmscf",
        "sour_co2_content": 10.0,
        "sweet_co2_content": 1.0,
    })
    assert res_agr["results"]["co2"]["value"] > 0
    assert res_agr["results"]["ch4"]["value"] > 0

    # 9. Flaring stoichiometry with C2+ ethane equivalent carbon counting
    res_flared = v_calc.calculate("volume", {
        "gas_volume": 100000.0,
        "unit": "scf",
        "ch4_content": 80.0,
        "co2_content": 2.0,
        "c2plus_content": 8.0,  # 8% C2+
        "disposition": "flared",
        "combustion_efficiency": 98.0,
    })
    assert res_flared["results"]["co2"]["value"] > 0
    assert res_flared["results"]["ch4"]["value"] > 0

    # Validations
    with pytest.raises(ValueError, match="Gas temperature must be above absolute zero"):
        v_calc.calculate("actual", {"actual_volume": 100.0, "gas_temp_f": -500.0, "gas_pressure_atm": 1.0, "ch4_content": 80.0})
    with pytest.raises(ValueError, match="Sweet gas carries more CO2 than the sour gas"):
        v_calc.calculate("agr_balance", {"sour_gas_volume": 100.0, "sweet_gas_volume": 100.0, "gas_volume_unit": "scf",
                                         "sour_co2_content": 2.0, "sweet_co2_content": 5.0})


def test_legacy_engine_and_flare_defaults_deep_branches():
    # 1. Flare defaults: Downstream facility autodetection applies 99.5% destruction
    downstream_payload = {
        "process_type": "flaring",
        "amount": 1000.0,
        "unit": "m3",
        "facility_segment": "downstream",
    }
    catalog_factor = {
        "co2": 1.8,
        "ch4": 0.05,
        "unit": "kg/m3",
        "combustion_efficiency_ch4": PRODUCTION_DESTRUCTION,
    }
    res_downstream, _ = flare_compute_emissions(downstream_payload, catalog_factor)
    # Refinery destruction (0.995) applies residual factor (1 - 0.995)/(1 - 0.98) = 0.25 (75% lower CH4)
    res_upstream, _ = flare_compute_emissions({**downstream_payload, "facility_segment": "upstream"}, catalog_factor)
    assert res_downstream["ch4"] < res_upstream["ch4"]

    # 2. Legacy engine: Specific factor resolution and conversions
    spec_payload = {
        "process_type": "combustion",
        "amount": 100.0,
        "unit": "m3",
        "factor_source": "specific",
        "specific_factors": {
            "co2": 2.5,
            "ch4": 0.02,
            "n2o": 0.001,
            "unit": "m3",
        },
    }
    res_spec, method_spec = legacy_compute_emissions(spec_payload)
    assert method_spec == "server_specific"
    assert res_spec["co2"] == pytest.approx(100.0 * 2.5 / 1000.0)
    assert res_spec["ch4"] == pytest.approx(100.0 * 0.02 / 1000.0)
    assert res_spec["n2o"] == pytest.approx(100.0 * 0.001 / 1000.0)

    # 3. MissingFactorError: Positive amount with no factor resolved
    with pytest.raises(MissingFactorError, match="No emission factor found"):
        legacy_compute_emissions({
            "process_type": "combustion",
            "amount": 1000.0,
            "unit": "m3",
            "fuel": "unknown_mysterious_fuel",
        }, factor_data={})

    # Zero amount passes without MissingFactorError
    res_zero, _ = legacy_compute_emissions({
        "process_type": "combustion",
        "amount": 0.0,
        "unit": "m3",
        "fuel": "zero_fuel",
    }, factor_data={})
    assert res_zero["totalCo2e"] == 0.0
