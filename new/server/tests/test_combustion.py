import pytest
from calculations.combustion import FlaringCalculator, CombustionCalculator

def test_flaring_calculator_basic():
    calc = FlaringCalculator()
    data = {
        'gas_volume': 1000, 
        'ch4_fraction': 0.85,
        'flare_type': 'elevated',
        'uncertainties': {}
    }
    res = calc.calculate(**data)
    assert res['results']['co2']['value'] > 0
    assert res['results']['ch4']['value'] > 0

def test_flaring_calculator_specific_c1_c10():
    calc = FlaringCalculator()
    data = {
        'gas_volume': 1000, 
        'ch4_fraction': 0.80,
        'flare_type': 'elevated',
        'uncertainties': {},
        'c1': 80.0,
        'c2': 10.0,
        'c3': 5.0,
        'co2_comp': 2.0
    }
    res = calc.calculate(**data)
    assert res['results']['co2']['value'] > 0
    assert res['results']['ch4']['value'] > 0

def test_stationary_combustion_calculator():
    calc = CombustionCalculator()
    data = {
        'fuel_quantity': 500,
        'fuel_unit': 'gal',
        'hhv': 138000,
        'fuel_type': 'liquids',
        'ef_co2': 73.96,
        'ef_ch4': 0.003,
        'ef_n2o': 0.0006,
        'ef_unit': 'kg/mmbtu',
        'uncertainties': {}
    }
    res = calc.calculate(**data)
    # 5.103 tonnes
    assert abs(res['results']['co2']['value'] - 5.103) < 0.1
