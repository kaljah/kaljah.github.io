import pytest
from calculations.constants import GWP_AR4, GWP_AR5, GWP_AR6, get_active_gwp
from calculations.units import calculate_co2e
from calculations.legacy_engine import compute_emissions

def test_constants_and_helpers():
    # Test lookup of standards
    ar4 = get_active_gwp('AR4')
    assert ar4['CH4'] == 25.0
    assert ar4['N2O'] == 298.0

    ar5 = get_active_gwp('AR5')
    assert ar5['CH4'] == 28.0
    assert ar5['N2O'] == 264.0

    ar6 = get_active_gwp('AR6')
    assert ar6['CH4'] == 27.9
    assert ar6['N2O'] == 273.0

    # Test 20-year horizon lookup
    ar5_20 = get_active_gwp('AR5', horizon='20')
    assert ar5_20['CH4'] == 82.5

def test_calculate_co2e_dynamic():
    # 10 t CO2, 2 t CH4, 1 t N2O
    co2, ch4, n2o = 10.0, 2.0, 1.0

    # AR4: 10*1 + 2*25 + 1*298 = 10 + 50 + 298 = 358.0
    co2e_ar4 = calculate_co2e(co2, ch4, n2o, gwp_dict=GWP_AR4)
    assert pytest.approx(co2e_ar4, 0.01) == 358.0

    # AR5: 10*1 + 2*28 + 1*264 = 10 + 56 + 264 = 330.0
    co2e_ar5 = calculate_co2e(co2, ch4, n2o, gwp_dict=GWP_AR5)
    assert pytest.approx(co2e_ar5, 0.01) == 330.0

    # AR6: 10*1 + 2*27.9 + 1*273 = 10 + 55.8 + 273 = 338.8
    co2e_ar6 = calculate_co2e(co2, ch4, n2o, gwp_dict=GWP_AR6)
    assert pytest.approx(co2e_ar6, 0.01) == 338.8

def test_legacy_engine_dynamic_gwp():
    payload = {
        'process_type': 'pneumatics',
        'device_count': 10,
        'quantity': 10,
        'unit': 'units'
    }
    factor_data = {'ch4': 1.5}

    em_ar5, method5 = compute_emissions(payload, factor_data=factor_data, gwp_dict=GWP_AR5)
    em_ar4, method4 = compute_emissions(payload, factor_data=factor_data, gwp_dict=GWP_AR4)

    assert 'totalCo2e' in em_ar5
    assert 'totalCo2e' in em_ar4
    assert pytest.approx(em_ar5['totalCo2e'], 0.001) == 0.42
    assert pytest.approx(em_ar4['totalCo2e'], 0.001) == 0.375
    assert pytest.approx(em_ar5['totalCo2e'] / em_ar4['totalCo2e'], 0.001) == 28.0 / 25.0
