"""
Tests for previously untested calculation paths, physical invariants, and defect remediations (Part 7).

Covers Bugs 20 through 30:
- Bug 20: parse_amount NaN and Inf rejection
- Bug 21: to_kelvin absolute zero (0 K) physical invariant
- Bug 22: to_psia absolute vacuum (0 psia) physical invariant
- Bug 23: IndirectSteamCalculator boiler efficiency and transmission loss string normalization
- Bug 24: CogenAllocationCalculator efficiency percentage string parsing
- Bug 25: Vented production wells (_route) control efficiency percentage normalization
- Bug 26: LiquidsUnloadingCalculator gas fraction percentage string parsing
- Bug 27: CombustionMethodCalculator percentage string handling in _num and _frac
- Bug 28: CCUS and CrudeTransportLosses non-negative bounds and percentage strings
- Bug 29: AGRCalculator and DehydratorCalculator gas composition percentage strings
- Bug 30: Downstream Refining & Petrochemical non-negative bounds and fire agent normalization
"""

import math
import pytest
from calculations.units import parse_amount, to_kelvin, to_psia, to_fahrenheit
from calculations.indirect import IndirectSteamCalculator, CogenAllocationCalculator
from calculations.vented_production_wells import (
    WorkoverWithoutFracturingCalculator,
    CasingGasVentCalculator,
    ProductionNonRoutineVentingCalculator,
)
from calculations.vented_unloading import LiquidsUnloadingCalculator
from calculations.combustion_methods import CombustionMethodCalculator
from calculations.vented_ccus_transport import CCUSVentingCalculator, CrudeTransportLossesCalculator
from calculations.midstream import AGRCalculator, DehydratorCalculator
from calculations.vented_downstream import (
    RefiningCokerCalculator,
    RefiningHydrogenPlantCalculator,
    AsphaltBlowingCalculator,
    PetrochemicalManufacturingCalculator,
    FireSuppressionCalculator,
)


def test_units_parse_amount_nan_and_inf_guards():
    """Verify Bug 20 fix: parse_amount rejects NaN, Inf, and -Inf."""
    with pytest.raises(ValueError, match="NaN or Infinite"):
        parse_amount(float("nan"))
    with pytest.raises(ValueError, match="NaN or Infinite"):
        parse_amount("nan")
    with pytest.raises(ValueError, match="NaN or Infinite"):
        parse_amount("NaN")
    with pytest.raises(ValueError, match="NaN or Infinite"):
        parse_amount(float("inf"))
    with pytest.raises(ValueError, match="NaN or Infinite"):
        parse_amount("inf")
    with pytest.raises(ValueError, match="NaN or Infinite"):
        parse_amount("-inf")

    # Valid values still succeed
    assert parse_amount(0.0) == 0.0
    assert parse_amount(1234.5) == 1234.5
    assert parse_amount("1234.5") == 1234.5
    assert parse_amount(None) == 0.0


def test_units_to_kelvin_absolute_zero_guard():
    """Verify Bug 21 fix: to_kelvin enforces T >= 0 K (absolute zero)."""
    with pytest.raises(ValueError, match="below absolute zero"):
        to_kelvin(-300, "c")  # -300 °C = -26.85 K
    with pytest.raises(ValueError, match="below absolute zero"):
        to_kelvin(-500, "f")  # -500 °F = -22.41 K
    with pytest.raises(ValueError, match="below absolute zero"):
        to_kelvin(-1.0, "k")
    with pytest.raises(ValueError, match="below absolute zero"):
        to_kelvin(-1.0, "r")

    # Physical valid boundary
    assert to_kelvin(0.0, "k") == 0.0
    assert to_kelvin(-273.15, "c") == 0.0
    assert to_kelvin(0.0, "c") == 273.15


def test_units_to_psia_absolute_vacuum_guard():
    """Verify Bug 22 fix: to_psia enforces P >= 0 psia (absolute vacuum)."""
    with pytest.raises(ValueError, match="below absolute vacuum"):
        to_psia(-10.0, "psia")
    with pytest.raises(ValueError, match="below absolute vacuum"):
        to_psia(-50.0, "psig")  # -50 + 14.696 = -35.3 psia
    with pytest.raises(ValueError, match="below absolute vacuum"):
        to_psia(-5.0, "bara")

    # Valid vacuum and gauge pressures
    assert to_psia(0.0, "psia") == 0.0
    assert to_psia(0.0, "psig") == 14.696
    # Slight vacuum (-2 psig is ~12.696 psia, physically valid)
    assert abs(to_psia(-2.0, "psig") - 12.696) < 1e-3


def test_indirect_steam_percentage_strings_and_normalization():
    """Verify Bug 23 fix: IndirectSteamCalculator accepts percentage strings."""
    calc = IndirectSteamCalculator()
    res = calc.calculate(
        heat_energy=1000.0,
        ef_co2=53.06,  # kg/MMBtu
        boiler_efficiency="80%",
        transmission_loss="5%",
        uncertainties=None,
        heat_unit="mmbtu",
    )
    assert res["total_co2e"] > 0
    # Net efficiency: 0.80 * (1 - 0.05) = 0.76
    expected_co2 = (1000.0 / 0.76) * 53.06 / 1000.0
    assert abs(res["results"]["co2"]["value"] - expected_co2) < 1e-2


def test_cogen_allocation_percentage_strings():
    """Verify Bug 24 fix: CogenAllocationCalculator accepts percentage strings."""
    calc = CogenAllocationCalculator()
    res = calc.calculate(
        total_emissions=10000.0,
        heat_output=50000.0,
        power_output=20000.0,
        method="wri_efficiency",
        heat_efficiency="80%",
        power_efficiency="35%",
    )
    assert res["total_co2e"] > 0
    alloc_heat = res["metadata"]["allocated_heat_tonnes"]
    alloc_power = res["metadata"]["allocated_power_tonnes"]
    assert abs(alloc_heat + alloc_power - 10000.0) < 1e-3


def test_production_wells_route_percentage_normalization():
    """Verify Bug 25 fix: Well site calculators accept percentage strings in disposition and route."""
    calc_wo = WorkoverWithoutFracturingCalculator()
    res_wo = calc_wo.calculate(
        workovers=5.0,
        well_type="gas_well",
        ch4_content="80%",
        co2_content="5%",
        control_efficiency="98%",
        disposition="flared",
    )
    assert res_wo["total_co2e"] > 0
    assert res_wo["results"]["co2"]["value"] > 0

    calc_nr = ProductionNonRoutineVentingCalculator()
    res_nr = calc_nr.calculate(
        source_type="prv",
        equipment_count=10,
        ch4_content="85%",
        co2_content="3%",
        control_efficiency="95%",
        disposition="flared",
    )
    assert res_nr["total_co2e"] > 0


def test_vented_unloading_validate_fraction_percentage_strings():
    """Verify Bug 26 fix: LiquidsUnloadingCalculator accepts percentage strings."""
    calc = LiquidsUnloadingCalculator()
    res = calc.calculate_tier1(
        well_count=10,
        unloading_type="plunger",
        ch4_content="85%",
        co2_content="2%",
        control_efficiency="90%",
    )
    assert res["total_co2e"] > 0
    assert res["inputs"]["ch4_content"] == 0.85
    assert res["inputs"]["co2_content"] == 0.02


def test_combustion_methods_num_and_frac_percentage_strings():
    """Verify Bug 27 fix: CombustionMethodCalculator accepts percentage strings."""
    calc = CombustionMethodCalculator()

    # Carbon content method with percentage strings
    res_cc = calc.calculate(
        method="carbon_content",
        inputs={
            "fuel_volume": 10000.0,
            "unit": "gal",
            "fuel_density": 7.0,
            "density_unit": "lb/gal",
            "carbon_wt_pct": "86%",
            "oxidation_pct": "99%",
        },
    )
    assert res_cc["total_co2e"] > 0

    # Equipment method with percentage load
    res_eq = calc.calculate(
        method="equipment",
        inputs={
            "equipment_type": "ic_4s_lean_ng",
            "engine_hp": 1000.0,
            "load_pct": "75%",
            "operating_hours": 8000.0,
        },
    )
    assert res_eq["total_co2e"] > 0


def test_ccus_venting_non_negative_guards():
    """Verify Bug 28 fix: CCUSVentingCalculator enforces non-negative emissions."""
    calc = CCUSVentingCalculator()

    # Negative inlet should raise ValueError
    with pytest.raises(ValueError, match="negative"):
        calc.calculate(activity="stripper_vent", inlet_co2_tonnes=-100.0, capture_efficiency=0.90)

    # Negative monitoring vent should raise ValueError
    with pytest.raises(ValueError, match="negative"):
        calc.calculate(activity="monitoring_vent", vented_co2_tonnes=-50.0)

    # Valid stripper vent calculation
    res = calc.calculate(activity="stripper_vent", inlet_co2_tonnes=1000.0, capture_efficiency="90%")
    assert res["total_co2e"] > 0
    assert abs(res["results"]["co2"]["value"] - 100.0) < 1e-3


def test_crude_transport_percentage_string_and_bounds():
    """Verify Bug 28 fix: CrudeTransportLossesCalculator accepts percentage strings and enforces bounds."""
    calc = CrudeTransportLossesCalculator()

    # Pass ch4_weight_pct as string percentage
    res = calc.calculate(
        activity="loading",
        loading_service="submerged_dedicated",
        volume_loaded_gal=1_000_000.0,
        ch4_weight_pct="15%",
    )
    assert res["total_co2e"] > 0
    assert abs(res["inputs"]["net_ch4_tonnes"] - (0.91 * 0.15)) < 1e-4

    # wt % > 100 should raise ValueError
    with pytest.raises(ValueError, match="between 0 and 100"):
        calc.calculate(
            activity="loading",
            loading_service="submerged_dedicated",
            volume_loaded_gal=1_000_000.0,
            ch4_weight_pct=150.0,
        )


def test_midstream_agr_and_dehydrator_percentage_strings():
    """Verify Bug 29 fix: AGRCalculator and DehydratorCalculator accept percentage strings."""
    agr = AGRCalculator()
    res_agr = agr.calculate(
        throughput=100.0,
        co2_in="4%",
        co2_out="0.05%",
        ch4_in="85%",
        ch4_slip_fraction="0.1%",
        acid_gas_control_eff="98%",
        acid_gas_control_type="flare",
    )
    assert res_agr["total_co2e"] > 0
    assert res_agr["inputs"]["co2_in_pct"] == 4.0
    assert res_agr["inputs"]["co2_out_pct"] == 0.05

    dehy = DehydratorCalculator()
    res_dehy = dehy.calculate(
        throughput=50.0,
        ch4_content="80%",
        control_eff="95%",
    )
    assert res_dehy["total_co2e"] > 0


def test_downstream_fluid_coker_negative_guard():
    """Verify Bug 30 fix: RefiningCokerCalculator rejects negative coke burned."""
    calc = RefiningCokerCalculator()
    with pytest.raises(ValueError, match="negative"):
        calc.calculate(coker_type="fluid", coke_burned_tonnes_yr=-500.0)
    with pytest.raises(ValueError, match="negative"):
        calc.calculate(coker_type="fluid", coke_burned_lb_yr=-1000.0)

    # Valid positive run
    res = calc.calculate(coker_type="fluid", coke_burned_tonnes_yr=1000.0)
    assert res["total_co2e"] > 0


def test_downstream_h2_plant_negative_guards():
    """Verify Bug 30 fix: RefiningHydrogenPlantCalculator rejects negative emissions."""
    calc = RefiningHydrogenPlantCalculator()
    with pytest.raises(ValueError, match="negative"):
        calc.calculate(method="feedstock_balance", feedstock_rate_tonnes_yr=-100.0, feedstock_carbon_fraction=0.85)

    with pytest.raises(ValueError, match="negative"):
        calc.calculate(method="h2_stoichiometry", h2_production_scf_yr=-10000.0, co2_to_h2_molar_ratio=0.25)

    with pytest.raises(ValueError, match="negative"):
        calc.calculate(method="simple_factor", simple_basis="h2_scf", simple_volume=-5000.0)

    # Valid run
    res = calc.calculate(method="simple_factor", simple_basis="h2_scf", simple_volume=1_000_000.0)
    assert res["total_co2e"] > 0


def test_downstream_asphalt_blowing_negative_guard():
    """Verify Bug 30 fix: AsphaltBlowingCalculator rejects negative throughput."""
    calc = AsphaltBlowingCalculator()
    with pytest.raises(ValueError, match="negative"):
        calc.calculate(throughput=-100.0, unit="bbl")

    res = calc.calculate(throughput=1000.0, unit="bbl")
    assert res["total_co2e"] > 0


def test_downstream_petrochemical_negative_guard():
    """Verify Bug 30 fix: PetrochemicalManufacturingCalculator rejects negative production."""
    calc = PetrochemicalManufacturingCalculator()
    with pytest.raises(ValueError, match="negative"):
        calc.calculate(process_type="methanol", production_tonnes=-50.0)

    res = calc.calculate(process_type="methanol", production_tonnes=1000.0)
    assert res["total_co2e"] > 0


def test_downstream_fire_suppression_release_rate_normalization():
    """Verify Bug 30 fix: FireSuppressionCalculator normalizes release rate strings and guards negatives."""
    calc = FireSuppressionCalculator()

    # Negative charge or discharge should raise
    with pytest.raises(ValueError, match="negative"):
        calc.calculate(agent_type="hfc_227ea", total_charge_kg=-100.0, annual_release_rate="2%")

    with pytest.raises(ValueError, match="negative"):
        calc.calculate(agent_type="hfc_227ea", total_charge_kg=100.0, direct_discharge_kg=-10.0, annual_release_rate="2%")

    # Percentage string for annual release rate
    res = calc.calculate(
        agent_type="hfc_227ea",
        total_charge_kg=1000.0,
        annual_release_rate="2%",
    )
    assert res["total_co2e"] > 0
    # Released tonnes: (1000 * 0.02) / 1000 = 0.02 tonnes * 3220 = 64.4 tonnes CO2e
    assert abs(res["total_co2e"] - 64.4) < 1e-2
