import math
import pytest


def test_bug01_flare_voc_native_co2_passthrough():
    """Bug 1: Flare VOC back-calculation must pass through 100% of native inert CO2."""
    from calculations.combustion_methods import CombustionMethodCalculator

    calc = CombustionMethodCalculator()
    res = calc.calculate("flare_voc", {
        "voc_mass": 2.21,
        "voc_mass_unit": "short_ton",
        "wt_ch4": 2.73,
        "wt_c2h6": 0.85,
        "wt_c3h8": 1.35,
        "wt_c4h10": 0.99,
        "wt_c5h12": 0.83,
        "wt_c6plus": 2.16,
        "wt_co2": 90.43,
        "combustion_efficiency": 98.0
    })
    # Native feed CO2 is ~1686 tonnes and combustion CO2 is ~497 tonnes -> total ~2183 tonnes
    assert res["results"]["co2"]["value"] == pytest.approx(2183.1, rel=5e-3)


def test_bug02_flaring_hhv_units():
    """Bug 2: Flaring N2O handles various heating value units cleanly."""
    from calculations.combustion import FlaringCalculator

    calc = FlaringCalculator()
    # MMBtu/Mscf
    res1 = calc.calculate(gas_volume=1000.0, fuel_unit="m3", flare_type="elevated", uncertainties={}, hhv=1.02, comps={"hhv_unit": "mmbtu/mscf"}, ch4_fraction=0.90)
    assert res1["results"]["n2o"]["value"] > 0
    # MJ/m3
    res2 = calc.calculate(gas_volume=1000.0, fuel_unit="m3", flare_type="elevated", uncertainties={}, hhv=38.0, comps={"hhv_unit": "mj/m3"}, ch4_fraction=0.90)
    assert res2["results"]["n2o"]["value"] > 0


def test_bug04_offshore_completion_duration():
    """Bug 4: Offshore completion factor scales with duration in days."""
    from calculations.vented_completion import CompletionFlowbackCalculator

    calc = CompletionFlowbackCalculator()
    res_1day = calc.calculate(events=1, location="offshore", completion_duration_days=1.0)
    res_5day = calc.calculate(events=1, location="offshore", completion_duration_days=5.0)
    assert res_5day["results"]["ch4"]["value"] == pytest.approx(res_1day["results"]["ch4"]["value"] * 5.0, rel=1e-5)


def test_bug05_frac_injected_co2_deduction():
    """Bug 5: Injected CO2 volume is deducted from flowback volume."""
    from calculations.vented_completion import CompletionFlowbackCalculator

    calc = CompletionFlowbackCalculator()
    res = calc.calculate(
        calculation_method="metered_volume",
        flowback_volume=100000.0,
        volume_unit="scf",
        injected_co2_volume=20000.0,
        injected_co2_unit="scf",
        ch4_content=0.85,
        co2_content=0.05,
    )
    # Net gas should be 100000 - 20000 = 80000 scf
    assert res["inputs"]["net_flowback_scf"] == pytest.approx(80000.0, rel=1e-3)


def test_bug07_unloading_pressure_clamp():
    """Bug 7: Eq 6-11 automated plunger lift clamps pressure differentials and validates boundaries."""
    from calculations.vented_unloading import LiquidsUnloadingCalculator

    calc = LiquidsUnloadingCalculator()
    # At exact atmospheric pressure boundary, sqrt(0) evaluates to 0 without domain error
    res = calc.calculate_tier3_equation_6_11(
        p_shut=14.696,
        p_line=50.0,
        p_sep=25.0,
        sfr_p=1000.0,
        t_p=0.5,
        events=10,
        well_count=1,
        ch4_content=0.85,
    )
    assert res["results"]["ch4"]["value"] == 0.0

    # Sub-atmospheric shut-in pressure is rejected with clear ValueError
    with pytest.raises(ValueError, match="Shut-in pressure"):
        calc.calculate_tier3_equation_6_11(
            p_shut=14.0,
            p_line=50.0,
            p_sep=25.0,
            sfr_p=1000.0,
            t_p=0.5,
            events=10,
            well_count=1,
            ch4_content=0.85,
        )


def test_bug08_tank_vbe_low_pressure():
    """Bug 8: Vasquez-Beggs VBE gas gravity adjustment handles low separator pressure without collapsing."""
    from calculations.vented_production_tank import TankFlashingCalculator

    calc = TankFlashingCalculator()
    res = calc.calculate(
        method="vbe",
        throughput=10000.0,
        separator_pressure_psig=15.0,  # <= 100 psig
        separator_temp_f=100.0,
        api_gravity=45.0,
        gas_specific_gravity=0.85,
        ch4_content=0.80,
    )
    assert res["results"]["ch4"]["value"] > 0.0


def test_bug09_tank_dump_valve_annual_emissions():
    """Bug 9: Tank dump valve malfunction includes normal baseline flashing when include_baseline=True."""
    from calculations.vented_production_tank import TankFlashingCalculator

    calc = TankFlashingCalculator()
    # 100 hours of dump valve malfunction out of 8760 hours with baseline included
    res = calc.calculate(
        method="dump_valve",
        throughput=50000.0,
        liquid_type="crude",
        dump_valve_hours=100.0,
        include_baseline=True,
        ch4_content=0.80,
    )
    # Baseline normal flashing for 8660 hrs plus malfunction for 100 hrs is ~9.856 tonnes CH4
    assert res["results"]["ch4"]["value"] == pytest.approx(9.856, rel=1e-2)


def test_bug10_tank_depressurization_blowdown():
    """Bug 10: Depressurization mode defaults to atmospheric backpressure."""
    from calculations.vented_production_tank import BlowdownCalculator

    calc = BlowdownCalculator()
    res = calc.calculate(
        blowdown_volume=None,
        blowdown_mode="depressurization",
        pressure=100.0,  # 100 psig
        press_unit="psig",
        events=1,
        diameter_ft=4.0,
        length_ft=20.0,
        ch4_content=0.85,
    )
    assert res["results"]["ch4"]["value"] > 0.0


def test_bug11_dehydrator_gas_assisted_pump_count_mode():
    """Bug 11: Unit count mode accounts for Kimray gas-assisted pump when present."""
    from calculations.vented_production_pneumatic import GasDehydrationCalculator

    calc = GasDehydrationCalculator()
    res_no_pump = calc.calculate(dehydrator_type="glycol", use_unit_factor=True, dehydrator_count=1, has_gas_assisted_pump=False, ch4_content=0.80)
    res_with_pump = calc.calculate(dehydrator_type="glycol", use_unit_factor=True, dehydrator_count=1, has_gas_assisted_pump=True, ch4_content=0.80, co2_content=0.05)
    assert res_with_pump["results"]["ch4"]["value"] > res_no_pump["results"]["ch4"]["value"]
    assert res_with_pump["results"]["co2"]["value"] > 0.0


def test_bug12_fccu_air_blower_nitrogen_balance():
    """Bug 12: FCCU air blower calculates flue gas rate via nitrogen balance."""
    from calculations.vented_downstream import RefiningCatalystRegenCalculator

    calc = RefiningCatalystRegenCalculator()
    res = calc.calculate(
        approach="air_blower",
        air_rate_m3_min=1000.0,
        co2_pct=12.0,
        co_pct=1.0,
        operating_hours=8760.0,
    )
    assert res["results"]["co2"]["value"] > 0.0


def test_bug13_delayed_coker_water_volume():
    """Bug 13: Delayed coker quench water volume is positive when submerged."""
    from calculations.vented_downstream import RefiningCokerCalculator

    calc = RefiningCokerCalculator()
    res = calc.calculate(
        coker_type="delayed",
        vessel_diameter_ft=24.0,
        vessel_height_ft=90.0,
        coke_drum_outage_ft=10.0,  # 80 ft coke
        water_height_ft=40.0,      # 40 ft water
        p_overhead_psig=20.0,
    )
    assert res["results"]["ch4"]["value"] > 0.0


def test_bug14_smr_feed_native_co2():
    """Bug 14: SMR hydrogen plant stoichiometry includes feed native CO2."""
    from calculations.vented_downstream import RefiningHydrogenPlantCalculator

    calc = RefiningHydrogenPlantCalculator()
    res1 = calc.calculate(
        method="h2_stoichiometry",
        feedstock_comp={"CH4": 0.98, "CO2": 0.0},
        h2_production_scf_yr=1e8,
    )
    res2 = calc.calculate(
        method="h2_stoichiometry",
        feedstock_comp={"CH4": 0.96, "CO2": 0.02},
        h2_production_scf_yr=1e8,
    )
    assert res2["results"]["co2"]["value"] > res1["results"]["co2"]["value"]


def test_bug15_fire_suppression_clean_agent():
    """Bug 15: Fire suppression clean agents return f_gas and format correctly."""
    from calculations.vented_downstream import FireSuppressionCalculator

    calc = FireSuppressionCalculator()
    res = calc.calculate(agent_type="hfc-227ea", charge_capacity_kg=1000.0, release_fraction=0.10)
    assert res["results"]["f_gas"]["value"] > 0.0
    assert res["total_co2e"] > 0.0


def test_bug16_17_marine_loading_flared_vapors():
    """Bug 16 & 17: Marine transport flared vapors account for methane slip and N2O."""
    from calculations.vented_ccus_transport import CrudeTransportLossesCalculator

    calc = CrudeTransportLossesCalculator()
    res = calc.calculate(
        activity="loading",
        loading_service="marine_barges",
        volume_loaded_bbl=100000.0,
        control_efficiency=0.98,
        control_type="flare",
    )
    assert res["results"]["ch4"]["value"] > 0.0
    assert res["results"]["co2"]["value"] > 0.0
    assert res["results"]["n2o"]["value"] > 0.0


def test_bug18_vented_gas_reported_mass_flaring():
    """Bug 18: Reported mass venting flaring burns CH4 to CO2 and preserves native CO2."""
    from calculations.vented_gas import VentedGasCalculator

    calc = VentedGasCalculator()
    res = calc.calculate("reported_mass", {
        "ch4_mass": 10.0,
        "co2_mass": 5.0,
        "mass_unit": "t",
        "control_efficiency": 0.98,
        "disposition": "flared",
    })
    # 9.8 tonnes CH4 burned -> 26.9 tonnes CO2 + 5.0 tonnes native CO2 = 31.9 tonnes CO2
    assert res["results"]["co2"]["value"] == pytest.approx(31.9, rel=2e-2)
    assert res["results"]["ch4"]["value"] == pytest.approx(0.2, rel=1e-5)


def test_bug20_method21_toc_to_co2():
    """Bug 20: Method 21 screening derives CO2 from whole gas."""
    from calculations.fugitive_onshore import OnshoreScreeningMeasurementCalculator

    calc = OnshoreScreeningMeasurementCalculator()
    res = calc.calculate_method21_ranges(
        component_type="valve",
        service_type="gas",
        non_pegged_count=10,
        pegged_count=1,
        operating_hours=8760.0,
        ch4_content=0.85,
        co2_content=0.05,
    )
    assert res["results"]["co2"]["value"] > 0.0


def test_bug21_sf6_usage_factor_isolation():
    """Bug 21: SF6 Eq 7-25 does not double-count maintenance recharge."""
    from calculations.fugitive_other import ElectricalEquipmentCalculator

    calc = ElectricalEquipmentCalculator()
    res = calc.calculate("usage_factor", {
        "nameplate_capacity": 500.0,
        "capacity_unit": "kg",
        "equipment_type": "closed_pressure_us",
    })
    # Nameplate capacity 500 kg * 0.14 = 70 kg = 0.070 t
    assert res["results"]["f_gas"]["value"] == pytest.approx(0.070, rel=1e-4)


def test_bug22_indirect_steam_ton_accepted():
    """Bug 22: Heat to MMBtu accepts standard short_ton and rejects ambiguous bare ton."""
    from calculations.indirect import heat_to_mmbtu

    mmbtu = heat_to_mmbtu(10.0, "short_ton", steam_enthalpy_btu_lb=1170.0)
    assert mmbtu > 0.0

    with pytest.raises(ValueError, match="ambiguous"):
        heat_to_mmbtu(10.0, "ton", steam_enthalpy_btu_lb=1170.0)


def test_bug26_gas_analysis_h2s():
    """Bug 26: Gas analysis parser exports h2s in composition dictionary."""
    from calculations.gas_analysis import composition

    comps = composition({"c1": 80.0, "co2": 5.0, "h2s": 2.0, "n2": 13.0})
    assert "h2s" in comps
    assert comps["h2s"] == pytest.approx(0.02, rel=1e-4)


def test_bug40_drilling_inputs_idempotency():
    """Bug 40: Drilling dispatcher does not mutate input dictionary in-place."""
    from calculations.dispatcher import CalculationDispatcher

    dispatcher = CalculationDispatcher()
    inputs = {"amount": 48.0, "unit": "hours", "process_type": "drilling", "drilling_type": "onshore", "factor_source": "default"}
    dispatcher.dispatch("drilling", inputs, {}, {}, {})
    # Original amount must remain 48.0, not mutated to 2.0
    assert inputs["amount"] == 48.0
    assert inputs["unit"] == "hours"


def test_bug43_bitumen_api_gravity():
    """Bug 43: Bitumen 1.0 °API gravity is not inverted to 10 °API."""
    from calculations.vented_production_tank import TankFlashingCalculator

    # Calling calculate directly with raw 1.0 API
    calc = TankFlashingCalculator()
    res = calc.calculate(method="vbe", throughput=1000.0, api_gravity=1.0, separator_pressure_psig=50.0, separator_temp_f=100.0)
    assert res["results"]["ch4"]["value"] > 0.0


def test_bug50_nitric_acid_unit_parsing():
    """Bug 50: Compound factor denominator 'tonne product' parses cleanly."""
    from calculations.units import factor_to_kg_per_activity

    kg = factor_to_kg_per_activity(2.0, "kg N2O/tonne product", "t")
    assert kg == pytest.approx(2.0, rel=1e-5)


def test_bug52_uncertainty_covariance():
    """Bug 52: Total CO2e uncertainty supports cross-gas covariance."""
    from calculations.uncertainty import propagate_co2e_uncertainty

    unc_no_cov = propagate_co2e_uncertainty(100.0, 0.05, 10.0, 0.05, 0.0, 0.0)
    unc_with_cov = propagate_co2e_uncertainty(100.0, 0.05, 10.0, 0.05, 0.0, 0.0, cov_co2_ch4=-0.5)
    assert unc_with_cov["relative_uncertainty_95pct"] < unc_no_cov["relative_uncertainty_95pct"]
