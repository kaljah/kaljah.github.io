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
    assert res["results"]["co2"]["value"] > 0


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
    diff = abs(res_m3["results"]["co2"]["value"] - res_scf["results"]["co2"]["value"])
    assert diff / res_m3["results"]["co2"]["value"] < 0.05


def test_dispatcher_combustion_fallback():
    dispatcher = CalculationDispatcher()
    payload = {
        "process_type": "stationary_combustion",
        "factor_source": "default",
        "amount": 500,
        "unit": "gal",
        "fuel": "Diesel (No. 2 Fuel Oil)",
    }
    factor_data = {
        "ef_co2": 73.96,
        "ef_ch4": 0.003,
        "ef_n2o": 0.0006,
        "hhv": 138000,
        "fuel_type": "liquids",
        "unit": "kg/mmbtu",
    }
    res = dispatcher.dispatch("stationary_combustion", payload, factor_data, {})
    assert res is not None


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
    assert res["results"]["ch4"]["value"] > 0


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
        "agr_ch4_slip": 0.1,  # 0.1%
        "agr_control_eff": 0.0,  # Uncontrolled vent
    }
    res = dispatcher.dispatch("agr", payload, {}, {})
    assert res is not None
    assert res["results"]["co2"]["value"] > 0
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > res["results"]["co2"]["value"]


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
    assert res_cold["results"]["ch4"]["value"] > res_hot["results"]["ch4"]["value"]


def test_completions_flowback_methods():
    """CALC-07: Verify completions multi-method calculation (rate/duration & GOR)"""
    dispatcher = CalculationDispatcher()
    payload_rate = {
        "process_type": "completions",
        "factor_source": "specific",
        "comp_method": "rate_duration",
        "comp_rate": 250.0,  # 250 Mscf/day
        "comp_duration": 48.0,  # 48 hours = 2 days -> 500 Mscf
        "comp_ch4_content": 85.0,
        "control_efficiency": 0.98,
    }
    res_rate = dispatcher.dispatch("completions", payload_rate, {}, {})
    assert res_rate is not None
    assert res_rate["results"]["ch4"]["value"] > 0
    assert res_rate["results"]["co2"]["value"] > 0


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
    co2_val = res["results"]["co2"]["value"]
    assert 24.0 < co2_val < 27.0

