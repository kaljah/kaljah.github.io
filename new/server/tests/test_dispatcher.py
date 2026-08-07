import pytest
from calculations.dispatcher import CalculationDispatcher
from calculations.units import normalize_gas_volume_to_standard, STD_TEMP_K, STD_PRESSURE_PSIA

def test_dispatcher_flaring_routing():
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'flaring',
        'factor_source': 'specific',
        'amount': 1000,
        'unit': 'm3',
        'c1': 80,
        'c2': 10,
        'co2_mol': 2
    }
    res = dispatcher.dispatch('flaring', payload, {}, {})
    assert res is not None
    assert 'results' in res
    assert res['results']['co2']['value'] > 0

def test_dispatcher_unit_normalization():
    dispatcher = CalculationDispatcher()
    payload_m3 = {
        'process_type': 'flaring',
        'factor_source': 'specific',
        'amount': 1000,
        'unit': 'm3',
        'c1': 80,
        'co2_mol': 2
    }
    payload_scf = {
        'process_type': 'flaring',
        'factor_source': 'specific',
        'amount': 35314.7,
        'unit': 'scf',
        'c1': 80,
        'co2_mol': 2
    }
    res_m3 = dispatcher.dispatch('flaring', payload_m3, {}, {})
    res_scf = dispatcher.dispatch('flaring', payload_scf, {}, {})
    diff = abs(res_m3['results']['co2']['value'] - res_scf['results']['co2']['value'])
    assert diff / res_m3['results']['co2']['value'] < 0.05

def test_dispatcher_combustion_fallback():
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'stationary_combustion',
        'factor_source': 'default',
        'amount': 500,
        'unit': 'gal',
        'fuel': 'Diesel (No. 2 Fuel Oil)'
    }
    factor_data = {
        'ef_co2': 73.96,
        'ef_ch4': 0.003,
        'ef_n2o': 0.0006,
        'hhv': 138000,
        'fuel_type': 'liquids',
        'unit': 'kg/mmbtu'
    }
    res = dispatcher.dispatch('stationary_combustion', payload, factor_data, {})
    assert res is not None

def test_tier3_strict_validation_unloading_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'unloading',
        'factor_source': 'specific',
        'calc_inputs': {
            'unloading': {
                'unload_depth': 2500
                # missing unload_diameter, unload_pressure, unload_events, ch4_content
            }
        }
    }
    with pytest.raises(ValueError, match="Missing required parameter for Tier 3 specific calculation"):
        dispatcher.dispatch('unloading', payload, {}, {})

def test_tier3_strict_validation_blowdown_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'blowdown',
        'factor_source': 'specific',
        'calc_inputs': {
            'blowdown': {
                'blowdown_volume': 100
                # missing blowdown_pressure, blowdown_events, ch4_content
            }
        }
    }
    with pytest.raises(ValueError, match="Missing required parameter for Tier 3 specific calculation"):
        dispatcher.dispatch('blowdown', payload, {}, {})

def test_tier3_strict_validation_pneumatics_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'pneumatic',
        'factor_source': 'specific',
        'calc_inputs': {
            'pneumatic': {
                'amount': 5
                # missing pneu_bleed_rate, pneu_hours, pneu_ch4_content
            }
        }
    }
    with pytest.raises(ValueError, match="Missing required parameter for Tier 3 specific calculation"):
        dispatcher.dispatch('pneumatic', payload, {}, {})

def test_tier3_strict_validation_agr_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'agr',
        'factor_source': 'specific',
        'calc_inputs': {
            'agr': {
                'agr_throughput': 100
                # missing agr_co2_in, agr_co2_out
            }
        }
    }
    with pytest.raises(ValueError, match="Missing required parameter for Tier 3 specific calculation"):
        dispatcher.dispatch('agr', payload, {}, {})

def test_tier1_default_pneumatics():
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'pneumatic',
        'factor_source': 'default',
        'amount': 10,
        'unit': 'devices'
    }
    factor_data = {
        'ef_ch4': 345.0,
        'unit': 'kg/device-yr'
    }
    res = dispatcher.dispatch('pneumatic', payload, factor_data, {})
    assert res is not None
    assert res['results']['ch4']['value'] > 0

def test_agr_methane_slip_calculation():
    """CALC-03: Verify AGR calculates both CO2 mass balance and CH4 slip per API Table 6-5"""
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'agr',
        'factor_source': 'specific',
        'amount': 100, # 100 MMscf/yr
        'unit': 'mmscf',
        'agr_co2_in': 4.0, # 4%
        'agr_co2_out': 0.05, # 0.05%
        'agr_ch4_in': 85.0, # 85%
        'agr_ch4_slip': 0.1, # 0.1%
        'agr_control_eff': 0.0 # Uncontrolled vent
    }
    res = dispatcher.dispatch('agr', payload, {}, {})
    assert res is not None
    assert res['results']['co2']['value'] > 0
    assert res['results']['ch4']['value'] > 0
    assert res['total_co2e'] > res['results']['co2']['value']

def test_dehydrator_parametric_solubility():
    """CALC-02: Verify Glycol Dehydrator parametric TEG solubility model"""
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'dehydrator',
        'factor_source': 'specific',
        'amount': 50,
        'dehy_pump_rate': 15.0, # 15 gal/hr
        'dehy_pump_unit': 'gph',
        'dehy_hours': 8760,
        'dehy_ch4_content': 90.0,
        'dehy_press': 1000.0, # 1000 psig contactor
        'dehy_temp': 100.0, # 100°F
        'dehy_has_flash': True,
        'dehy_eff': 0.0
    }
    res = dispatcher.dispatch('dehydrator', payload, {}, {})
    assert res is not None
    assert res['results']['ch4']['value'] > 0
    assert res['inputs']['solubility_scf_gal'] > 10.0 # High pressure yields >10 scf/gal

def test_blowdown_temperature_correction():
    """CALC-06: Verify Blowdown calculator applies thermodynamic T-correction"""
    dispatcher = CalculationDispatcher()
    payload_cold = {
        'process_type': 'blowdown',
        'factor_source': 'specific',
        'blowdown_volume': 10.0, # 10 m3
        'blowdown_pressure': 500.0, # 500 psig
        'blowdown_events': 1,
        'ch4_content': 90.0,
        'blowdown_temp': 30.0, # 30°F (colder = denser gas = higher mass)
        'temp_unit': 'F'
    }
    payload_hot = {
        'process_type': 'blowdown',
        'factor_source': 'specific',
        'blowdown_volume': 10.0, # 10 m3
        'blowdown_pressure': 500.0, # 500 psig
        'blowdown_events': 1,
        'ch4_content': 90.0,
        'blowdown_temp': 120.0, # 120°F (hotter = less dense gas = lower mass)
        'temp_unit': 'F'
    }
    res_cold = dispatcher.dispatch('blowdown', payload_cold, {}, {})
    res_hot = dispatcher.dispatch('blowdown', payload_hot, {}, {})
    assert res_cold['results']['ch4']['value'] > res_hot['results']['ch4']['value']

def test_completions_flowback_methods():
    """CALC-07: Verify completions multi-method calculation (rate/duration & GOR)"""
    dispatcher = CalculationDispatcher()
    payload_rate = {
        'process_type': 'completions',
        'factor_source': 'specific',
        'comp_method': 'rate_duration',
        'comp_rate': 250.0, # 250 Mscf/day
        'comp_duration': 48.0, # 48 hours = 2 days -> 500 Mscf
        'comp_ch4_content': 85.0,
        'control_efficiency': 0.98
    }
    res_rate = dispatcher.dispatch('completions', payload_rate, {}, {})
    assert res_rate is not None
    assert res_rate['results']['ch4']['value'] > 0
    assert res_rate['results']['co2']['value'] > 0
