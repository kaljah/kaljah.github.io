import pytest
from calculations.dispatcher import CalculationDispatcher


def test_dispatcher_flaring_routing():
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "flaring",
        "factor_source": "specific",
        "amount": 1000,
        "unit": "m3",
        "c1": 80,
        "c2": 10,
        "co2_mol": 2,
    }
    res = dispatcher.dispatch("flaring", payload, {}, {})
    assert res is not None
    assert "results" in res
    # 1,000 m3 at 80 % CH4 + 10 % C2H6 (carbon 0.80 + 0.20 = 1.00 mol C/mol) and 2 % CO2; default elevated flare:
    # 96.5 % of the carbon to CO2 and 98 % of the CH4 destroyed. 60 F molar volume 23.685 m3/kmol.
    rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
    assert res["results"]["co2"]["value"] == pytest.approx(1000 * (1.00 * 0.965 + 0.02) * rho_co2 / 1000, rel=1e-9)
    assert res["results"]["ch4"]["value"] == pytest.approx(1000 * 0.80 * 0.02 * rho_ch4 / 1000, rel=1e-9)


def test_dispatcher_unit_normalization():
    dispatcher = CalculationDispatcher()
    payload_m3 = {
        "process_type": "flaring",
        "factor_source": "specific",
        "amount": 1000,
        "unit": "m3",
        "c1": 80,
        "co2_mol": 2,
    }
    payload_scf = {
        "process_type": "flaring",
        "factor_source": "specific",
        "amount": 35314.7,
        "unit": "scf",
        "c1": 80,
        "co2_mol": 2,
    }
    res_m3 = dispatcher.dispatch("flaring", payload_m3, {}, {})
    res_scf = dispatcher.dispatch("flaring", payload_scf, {}, {})
    # 1,000 m3 = 35,314.7 scf: the same gas, so the same emissions (to the rounding of 35,314.7)
    for gas in ("co2", "ch4", "n2o"):
        assert res_scf["results"][gas]["value"] == pytest.approx(res_m3["results"][gas]["value"], rel=1e-4)
    # and the value itself: 1,000 m3 / 23.685 m3/kmol = 42.22 kmol of gas, 80 % CH4 burned at the 96.5 % default
    # carbon conversion plus the 2 % CO2 already in the gas (x 44.01), 2 % of the CH4 unburned (x 16.04)
    kmol = 1000.0 / 23.685
    assert res_m3["results"]["co2"]["value"] == pytest.approx(kmol * (0.80 * 0.965 + 0.02) * 44.01 / 1000.0, rel=5e-3)  # 1.472 t
    assert res_m3["results"]["ch4"]["value"] == pytest.approx(kmol * 0.80 * 0.02 * 16.04 / 1000.0, rel=5e-3)           # 0.0108 t


def test_dispatcher_combustion_fallback():
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "stationary_combustion",
        "factor_source": "default",
        "amount": 500,
        "unit": "gal",
        "fuel": "Diesel (No. 2 Fuel Oil)",
    }
    # the factor row as resolve_factor returns it: "co2" / "ch4" / "n2o" in kg per MMBtu (keys named ef_co2 etc. were
    # silently read as no factor and this test passed on a result of exactly 0)
    factor_data = {
        "co2": 73.96,
        "ch4": 0.003,
        "n2o": 0.0006,
        "hhv": 138000,
        "type": "liquids",
        "unit": "kg/MMBtu",
    }
    res = dispatcher.dispatch("stationary_combustion", payload, factor_data, {})
    assert res is not None
    mmbtu = 500 * 138000 / 1e6   # 69 MMBtu
    assert res["results"]["co2"]["value"] == pytest.approx(mmbtu * 73.96 / 1000, rel=1e-9)
    assert res["results"]["ch4"]["value"] == pytest.approx(mmbtu * 0.003 / 1000, rel=1e-9)
    assert res["results"]["n2o"]["value"] == pytest.approx(mmbtu * 0.0006 / 1000, rel=1e-9)


def test_tier3_strict_validation_unloading_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "unloading",
        "factor_source": "specific",
        "calc_inputs": {
            "unloading": {
                "unload_depth": 2500
                # missing unload_diameter, unload_pressure, unload_events, ch4_content
            }
        },
    }
    with pytest.raises(
        ValueError, match="Missing required parameter for Tier 3 specific calculation"
    ):
        dispatcher.dispatch("unloading", payload, {}, {})


def test_tier3_strict_validation_blowdown_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "blowdown",
        "factor_source": "specific",
        "calc_inputs": {
            "blowdown": {
                "blowdown_volume": 100
                # missing blowdown_pressure, blowdown_events, ch4_content
            }
        },
    }
    with pytest.raises(
        ValueError, match="Missing required parameter for Tier 3 specific calculation"
    ):
        dispatcher.dispatch("blowdown", payload, {}, {})


def test_tier3_strict_validation_pneumatics_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "pneumatic",
        "factor_source": "specific",
        "calc_inputs": {
            "pneumatic": {
                "amount": 5
                # missing pneu_bleed_rate, pneu_hours, pneu_ch4_content
            }
        },
    }
    with pytest.raises(
        ValueError, match="Missing required parameter for Tier 3 specific calculation"
    ):
        dispatcher.dispatch("pneumatic", payload, {}, {})


def test_tier3_strict_validation_agr_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "agr",
        "factor_source": "specific",
        "calc_inputs": {
            "agr": {
                "agr_throughput": 100
                # missing agr_co2_in, agr_co2_out
            }
        },
    }
    with pytest.raises(
        ValueError, match="Missing required parameter for Tier 3 specific calculation"
    ):
        dispatcher.dispatch("agr", payload, {}, {})


def test_tier1_default_pneumatics():
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "pneumatic",
        "factor_source": "default",
        "amount": 10,
        "unit": "devices",
    }
    factor_data = {"ef_ch4": 345.0, "unit": "kg/device-yr"}
    res = dispatcher.dispatch("pneumatic", payload, factor_data, {})
    assert res is not None
    assert res["results"]["ch4"]["value"] == pytest.approx(10 * 345.0 / 1000.0, rel=1e-9)   # 10 devices x 345 kg/yr


def test_agr_methane_slip_calculation():
    """CALC-03: Verify AGR calculates both CO2 mass balance and CH4 slip per API Table 6-5"""
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "agr",
        "factor_source": "specific",
        "amount": 100,  # 100 MMscf/yr
        "unit": "mmscf",
        "agr_co2_in": 4.0,  # 4%
        "agr_co2_out": 0.05,  # 0.05%
        "agr_ch4_in": 85.0,  # 85%
        "agr_ch4_slip": 0.001,  # a FRACTION of the inlet CH4 (0.1 %); the test used 0.1, which is 10 %
        "agr_control_eff": 0.0,  # Uncontrolled vent
    }
    res = dispatcher.dispatch("agr", payload, {}, {})
    assert res is not None
    # 100 MMscf inlet = 2,831,685 m3. CO2 removed = V x (c_in - c_out) / (1 - c_out) (the sweet gas volume is the inlet
    # less the CO2 removed), vented uncontrolled; CH4 slip = V x 85 % x 0.1 %. 60 F molar volume 23.685 m3/kmol.
    v_in = 100e6 * 0.028316846592
    assert res["results"]["co2"]["value"] == pytest.approx(
        v_in * (0.04 - 0.0005) / (1 - 0.0005) * (44.01 / 23.685) / 1000, rel=1e-9)
    assert res["results"]["ch4"]["value"] == pytest.approx(v_in * 0.85 * 0.001 * (16.04 / 23.685) / 1000, rel=1e-9)
    assert res["total_co2e"] == pytest.approx(
        res["results"]["co2"]["value"] + 28.0 * res["results"]["ch4"]["value"], rel=1e-9)


def test_dehydrator_parametric_solubility():
    """The parametric TEG solubility model (S = 0.0032 P^0.96 ...) had no API Compendium source and was
    removed (audit/TIER3_BROWSER_TEST.md #12): its inputs are rejected with guidance."""
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "dehydrator",
        "factor_source": "specific",
        "amount": 50,
        "dehy_pump_rate": 15.0,
        "dehy_pump_unit": "gph",
        "dehy_hours": 8760,
        "dehy_ch4_content": 90.0,
        "dehy_press": 1000.0,
        "dehy_temp": 100.0,
    }
    with pytest.raises(ValueError, match="GLYCalc"):
        dispatcher.dispatch("dehydrator", payload, {}, {})


def test_blowdown_temperature_correction():
    """CALC-06: Verify Blowdown calculator applies thermodynamic T-correction"""
    dispatcher = CalculationDispatcher()
    payload_cold = {
        "process_type": "blowdown",
        "factor_source": "specific",
        "blowdown_volume": 10.0,  # 10 m3
        "blowdown_pressure": 500.0,  # 500 psig
        "blowdown_events": 1,
        "ch4_content": 90.0,
        "blowdown_temp": 30.0,  # 30°F (colder = denser gas = higher mass)
        "temp_unit": "F",
    }
    payload_hot = {
        "process_type": "blowdown",
        "factor_source": "specific",
        "blowdown_volume": 10.0,  # 10 m3
        "blowdown_pressure": 500.0,  # 500 psig
        "blowdown_events": 1,
        "ch4_content": 90.0,
        "blowdown_temp": 120.0,  # 120°F (hotter = less dense gas = lower mass)
        "temp_unit": "F",
    }
    res_cold = dispatcher.dispatch("blowdown", payload_cold, {}, {})
    res_hot = dispatcher.dispatch("blowdown", payload_hot, {}, {})
    # standard m3 = 10 m3 x (500 + 14.696)/14.696 x 288.706 K / T: 30 F = 272.04 K, 120 F = 322.04 K; x 90 % CH4
    # x 16.04 / 23.685 kg/m3
    for res, kelvin, v_std in ((res_cold, 272.039, 371.69), (res_hot, 322.039, 313.98)):
        assert 10.0 * (514.696 / 14.696) * 288.706 / kelvin == pytest.approx(v_std, rel=1e-4)
        assert res["results"]["ch4"]["value"] == pytest.approx(v_std * 0.90 * 16.04 / 23.685 / 1000.0, rel=2e-3)
    assert res_cold["results"]["ch4"]["value"] > res_hot["results"]["ch4"]["value"]


def test_completions_flowback_methods():
    """CALC-07: Verify completions multi-method calculation (rate/duration & GOR)"""
    dispatcher = CalculationDispatcher()
    payload_rate = {
        "process_type": "completions",
        "factor_source": "specific",
        "comp_method": "rate_duration",
        "comp_rate": 250.0,
        "comp_rate_unit": "mscf/day",  # without it the rate is Mcf per HOUR (the form's default): 12,000 Mcf, not 500
        "comp_duration": 48.0,  # 48 hours = 2 days -> 500 Mscf
        "comp_ch4_content": 85.0,
        "control_efficiency": 0.98,
    }
    res_rate = dispatcher.dispatch("completions", payload_rate, {}, {})
    assert res_rate is not None
    # 500 Mscf = 14,158 m3 of gas, 85 % CH4. control_efficiency 0.98 alone = 98 % of the gas sent to a flare running at the
    # default 98 % CH4 destruction / 96.5 % carbon conversion; the other 2 % is vented.
    v_ch4 = 500e3 * 0.028316846592 * 0.85
    rho_co2, rho_ch4 = 44.01 / 23.685, 16.04 / 23.685
    assert res_rate["results"]["ch4"]["value"] == pytest.approx(
        v_ch4 * rho_ch4 / 1000 * (0.02 + 0.98 * 0.02), rel=1e-9)
    assert res_rate["results"]["co2"]["value"] == pytest.approx(v_ch4 * rho_co2 / 1000 * 0.98 * 0.965, rel=1e-9)


def test_dispatcher_nitric_acid_production_n2o():
    """Verify nitric acid production produces N2O, zero CO2, and respects abatement."""
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "nitric_acid_production",
        "factor_source": "specific",
        "amount": 100.0,
        "unit": "tonne",
        "ef_n2o": 9.0,  # 9 kg N2O/tonne
        "abatement_efficiency": 80.0,  # 80% reduction
    }
    res = dispatcher.dispatch("nitric_acid_production", payload, {}, {})
    assert res is not None
    # 100 t * 9 kg/t * (1 - 0.8) = 180 kg = 0.18 tonnes N2O
    assert pytest.approx(res["results"]["n2o"]["value"], rel=1e-3) == 0.18
    # No stoichiometric carbon in nitric acid -> co2 and ch4 must be 0
    assert res["results"]["co2"]["value"] == 0.0
    assert res["results"]["ch4"]["value"] == 0.0
    # CO2e should be N2O * GWP (~265 or 298)
    assert res["total_co2e"] > 0


def test_dispatcher_adipic_acid_production_n2o():
    """Verify adipic acid production routes to N2O with high uncontrolled factor."""
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "adipic_acid_production",
        "factor_source": "specific",
        "amount": 50.0,
        "unit": "tonne",
        "ef_n2o": 300.0,  # 300 kg N2O/tonne
        "abatement_efficiency": 0.0,
    }
    res = dispatcher.dispatch("adipic_acid_production", payload, {}, {})
    assert res is not None
    # 50 t * 300 kg/t = 15,000 kg = 15.0 tonnes N2O
    assert pytest.approx(res["results"]["n2o"]["value"], rel=1e-3) == 15.0
    assert res["results"]["co2"]["value"] == 0.0


def test_dispatcher_solid_fuel_combustion_energy():
    """Verify solid fuel (coal) combustion calculates proper MMBtu energy without 25000x undercount."""
    dispatcher = CalculationDispatcher()
    # 10 metric tonnes of Bituminous Coal
    payload = {
        "process_type": "stationary_combustion",
        "factor_source": "default",
        "amount": 10.0,
        "unit": "tonne",
        "fuel": "Bituminous Coal",
        "fuel_type": "Bituminous Coal",
    }
    factor_data = {
        "co2": 93.26,  # kg CO2/MMBtu
        "ch4": 0.011,
        "n2o": 0.0016,
        "hhv": 24930,  # 24.93 MMBtu/short ton
        "unit": "kg/MMBtu",
        "type": "solids",
    }
    res = dispatcher.dispatch("stationary_combustion", payload, factor_data, {})
    assert res is not None
    # 10 tonnes = 11.0231 short tons.
    # Energy = 11.0231 * 24.93 = ~274.8 MMBtu.
    # CO2 = 274.8 * 93.26 kg = ~25,628 kg = ~25.6 metric tonnes CO2.
    mmbtu = 10.0 * 1.10231131 * 24.93
    assert res["results"]["co2"]["value"] == pytest.approx(mmbtu * 93.26 / 1000.0, rel=1e-4)    # 25.63 t
    assert res["results"]["ch4"]["value"] == pytest.approx(mmbtu * 0.011 / 1000.0, rel=1e-4)    # 0.00302 t
    assert res["results"]["n2o"]["value"] == pytest.approx(mmbtu * 0.0016 / 1000.0, rel=1e-4)   # 0.00044 t

