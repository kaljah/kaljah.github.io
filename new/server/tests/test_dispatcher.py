import pytest
from calculations.dispatcher import CalculationDispatcher

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
                # missing unload_diameter, unload_pressure, unload_time, unload_events, ch4_content
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

def test_tier3_strict_validation_dehydrator_missing_fields():
    dispatcher = CalculationDispatcher()
    payload = {
        'process_type': 'dehydrator',
        'factor_source': 'specific',
        'calc_inputs': {
            'dehydrator': {
                'dehy_throughput': 50
                # missing dehy_pump_rate, dehy_hours, dehy_ch4_content
            }
        }
    }
    with pytest.raises(ValueError, match="Missing required parameter for Tier 3 specific calculation"):
        dispatcher.dispatch('dehydrator', payload, {}, {})

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

