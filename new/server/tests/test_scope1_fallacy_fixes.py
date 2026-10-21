"""
Regression test suite locking in remediation of all 8 Scope 1 Logical Fallacies (LF-01 through LF-08).
"""

import pytest
import math
from calculations.dispatcher import CalculationDispatcher
from calculations.legacy_engine import compute_emissions
from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.vented import LiquidsUnloadingCalculator, MudDegassingCalculator
from calculations.units import (
    normalize_gas_volume_to_standard,
    gas_volume_m3,
    CONVERSIONS,
    STD_TEMP_K,
    STD_PRESSURE_PSIA,
    UnitError,
)
from calculations.constants import GWP_AR5


@pytest.fixture
def dispatcher():
    return CalculationDispatcher()


def test_lf_01_drilling_default_factor_not_wiped_out(dispatcher):
    """LF-01: calc_drilling must not wipe out Table 6-2/6-3 factors with ef_ch4=0."""
    payload = {
        "process_type": "drilling",
        "factor_source": "default",
        "amount": 25.0,
        "quantity": 25.0,
        "unit": "days",
        "mud_type": "water_based",
        "location": "onshore",
    }
    factor_data = {
        "ch4": 0.0458,
        "unit": "tonne/day",
    }
    res = dispatcher.dispatch("drilling", payload, factor_data, {}, gwp_dict=GWP_AR5)
    assert res is not None
    assert res["total_co2e"] > 0
    assert res["results"]["ch4"]["value"] == pytest.approx(25.0 * 0.0458)


def test_lf_02_z_factor_zero_or_negative_rejected():
    """LF-02: normalize_gas_volume_to_standard must reject Z <= 0 with ValueError."""
    with pytest.raises(ValueError, match="Compressibility factor Z must be strictly positive"):
        normalize_gas_volume_to_standard(volume=1000.0, z_factor=0.0)

    with pytest.raises(ValueError, match="Compressibility factor Z must be strictly positive"):
        normalize_gas_volume_to_standard(volume=1000.0, z_factor=-0.85)

    with pytest.raises(ValueError, match="Compressibility factor Z is not a number"):
        normalize_gas_volume_to_standard(volume=1000.0, z_factor="not_a_number")


def test_lf_03_actual_volume_units_accepted():
    """LF-03: actual_m3, am3, and acf must be accepted by gas_volume_m3 and flaring."""
    # gas_volume_m3 acceptance
    vol_m3 = gas_volume_m3(100.0, "actual_m3")
    assert vol_m3 == 100.0

    vol_am3 = gas_volume_m3(100.0, "am3")
    assert vol_am3 == 100.0

    vol_acf = gas_volume_m3(1000.0, "acf")
    assert vol_acf == pytest.approx(1000.0 * 0.028316846592)

    # FlaringCalculator calculation with actual_m3
    calc = FlaringCalculator()
    res = calc.calculate(
        gas_volume=10_000.0,
        ch4_fraction=0.85,
        flare_type="elevated",
        uncertainties={},
        fuel_unit="actual_m3",
        operating_temperature=25.0,
        temp_unit="C",
        operating_pressure=20.0,
        press_unit="psig",
    )
    assert res["total_co2e"] > 0
    assert res["metadata"]["thermodynamic_normalized"] is True


def test_lf_04_downstream_flaring_destruction_scaling():
    """LF-04: Downstream flaring default destruction efficiency (99.5%) yields 0.25x CH4 vs 98%."""
    payload_up = {
        "process_type": "flaring",
        "amount": 1000.0,
        "unit": "m3",
        "fuel_type": "Natural Gas (Flaring)",
        "facility_segment": "upstream",
    }
    payload_down = {
        "process_type": "flaring",
        "amount": 1000.0,
        "unit": "m3",
        "fuel_type": "Natural Gas (Flaring)",
        "facility_segment": "downstream",
    }
    factor_data = {
        "co2": 1.9039,
        "ch4": 0.012447,
        "n2o": 0.0001,
        "unit": "kg/m3",
        "combustion_efficiency_ch4": 0.98,
    }

    res_up, _ = compute_emissions(payload_up, factor_data, gwp_dict=GWP_AR5)
    res_down, _ = compute_emissions(payload_down, factor_data, gwp_dict=GWP_AR5)

    assert res_up["ch4"] > 0
    assert res_down["ch4"] > 0
    # Downstream residual (1 - 0.995) / (1 - 0.98) = 0.005 / 0.02 = 0.25
    assert (res_down["ch4"] / res_up["ch4"]) == pytest.approx(0.25, rel=1e-4)


def test_lf_05_thermodynamic_standard_identity():
    """LF-05: Normalizing gas volume at standard conditions produces exact identity."""
    norm_vol = normalize_gas_volume_to_standard(
        volume=1000.0,
        operating_temp=60.0,
        temp_unit="F",
        operating_press=14.696,
        press_unit="psia",
        z_factor=1.0,
    )
    assert norm_vol == pytest.approx(1000.0, abs=1e-6)


def test_lf_06_stoichiometric_density_basis():
    """LF-06: CO2 density basis in flaring stoichiometry follows standard molar volume."""
    calc = FlaringCalculator()
    res = calc.calculate(
        gas_volume=10_000.0,
        ch4_fraction=0.80,
        flare_type="elevated",
        uncertainties={},
        c1=0.80,
        c2=0.10,
        c3=0.05,
        c4=0.02,
        co2_comp=0.03,
        combustion_efficiency=0.98,
        destruction_efficiency=0.98,
    )
    # Total carbon moles combusted = 1.23 * 0.98 + native 0.03 = 1.2354 moles/mole gas
    expected_co2 = (1.23 * 0.98 + 0.03) * 10_000.0 * CONVERSIONS["density_co2"] / 1000.0
    assert res["results"]["co2"]["value"] == pytest.approx(expected_co2, rel=1e-5)


def test_lf_07_negative_efficiency_rejected():
    """LF-07: Negative efficiencies must be rejected with ValueError."""
    comb = CombustionCalculator()
    with pytest.raises(ValueError, match="Combustion efficiency cannot be negative"):
        comb.calculate(fuel_quantity=100.0, combustion_efficiency=-0.05)

    flare = FlaringCalculator()
    with pytest.raises(ValueError, match="Combustion efficiency cannot be negative"):
        flare.calculate(gas_volume=100.0, ch4_fraction=0.9, flare_type="elevated", uncertainties={}, combustion_efficiency=-0.1)

    with pytest.raises(ValueError, match="Destruction efficiency cannot be negative"):
        flare.calculate(gas_volume=100.0, ch4_fraction=0.9, flare_type="elevated", uncertainties={}, destruction_efficiency=-0.05)


def test_lf_08_liquids_unloading_zero_activity(dispatcher):
    """LF-08: Zero activity amount/quantity in liquids unloading produces 0 emissions."""
    payload_zero = {
        "process_type": "liquids_unloading",
        "factor_source": "default",
        "amount": 0.0,
        "quantity": 0.0,
        "unit": "events",
        "events": 10,
        "well_count": 1,
        "unloading_type": "plunger",
        "ch4_content": 85.0,
    }
    factor_data = {
        "ch4": 0.185,
        "unit": "tonnes/event",
    }
    res = dispatcher.dispatch("liquids_unloading", payload_zero, factor_data, {}, gwp_dict=GWP_AR5)
    assert res["total_co2e"] == 0.0
