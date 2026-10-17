"""
Test Untested Calculation Paths - Part 10
Forensic test suite covering Bugs 51 through 60:
- Bug 51: CCUS wellhead blowdown negative bounds and percentage weight fraction normalization.
- Bug 52: Crude transport transit loss non-negative volume, duration, and trips.
- Bug 53: Stoichiometric mass balance 0.5% / 1% carbon content normalization and negative fuel mass.
- Bug 54: Nitric acid production abatement efficiency 0.5% / 1% normalization.
- Bug 55: mass_to_kg non-negative mass validation.
- Bug 56: Component-level fugitive ch4_content percentage parsing and negative validation.
- Bug 57: Equipment-level fugitive non-negative count, EF, and percentage content.
- Bug 58: Compressor seal non-negative compressor count validation.
- Bug 59: AGRCalculator non-negative throughput and 0.5% / 1% CO2 concentration scaling.
- Bug 60: DehydratorCalculator 0.5% / 1% CH4 content normalization.
"""
import pytest
from calculations.vented_ccus_transport import (
    CCUSVentingCalculator,
    CrudeTransportLossesCalculator,
)
from calculations.stoichiometry import (
    mass_to_kg,
    StoichiometricCalculator,
    NitricAcidCalculator,
)
from calculations.fugitive import (
    ComponentFugitiveCalculator,
    EquipmentFugitiveCalculator,
    CompressorSealCalculator,
)
from calculations.midstream import (
    AGRCalculator,
    DehydratorCalculator,
)


# ==============================================================================
# Bug 51: CCUS Venting Calculator
# ==============================================================================
def test_ccus_venting_wellhead_blowdown_bounds_and_percent():
    calc = CCUSVentingCalculator()

    # Negative events
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="wellhead_blowdown", events=-1, physical_volume_m3=10, co2_density_kg_m3=650, co2_weight_fraction=0.98)

    # Negative volume
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="wellhead_blowdown", events=1, physical_volume_m3=-10, co2_density_kg_m3=650, co2_weight_fraction=0.98)

    # Negative density
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="wellhead_blowdown", events=1, physical_volume_m3=10, co2_density_kg_m3=-650, co2_weight_fraction=0.98)

    # Negative weight fraction
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="wellhead_blowdown", events=1, physical_volume_m3=10, co2_density_kg_m3=650, co2_weight_fraction="-5%")

    # Percentage string parsing in co2_weight_fraction
    res = calc.calculate(activity="wellhead_blowdown", events=2, physical_volume_m3=10, co2_density_kg_m3=650, co2_weight_fraction="98.5%")
    assert res["results"]["co2"]["value"] > 0
    assert res["total_co2e"] > 0


# ==============================================================================
# Bug 52: Crude Transport Losses Calculator
# ==============================================================================
def test_crude_transport_transit_bounds():
    calc = CrudeTransportLossesCalculator()

    # Negative volume
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="transit", volume_transported_bbl=-1000, trip_duration_days=5)

    # Negative duration
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="transit", volume_transported_bbl=1000, trip_duration_days=-5)

    # Negative trips
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(activity="transit", volume_transported_bbl=1000, trip_duration_days=5, trips_per_year=-2)

    res = calc.calculate(activity="transit", volume_transported_bbl=50000, trip_duration_days=7, trips_per_year=10)
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0


# ==============================================================================
# Bug 53, 54, 55: Stoichiometry and Mass Conversion
# ==============================================================================
def test_mass_to_kg_bounds():
    with pytest.raises(ValueError, match="cannot be negative"):
        mass_to_kg(-50, "tonne")


def test_stoichiometric_calculator_bounds_and_percent_normalization():
    calc = StoichiometricCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(fuel_mass=-100, carbon_content=0.85)

    # 0.5% and 1% carbon content must not be treated as 50% or 100%
    res_half_pct = calc.calculate(fuel_mass=1000, carbon_content="0.5%", mass_unit="kg")
    res_fifty_pct = calc.calculate(fuel_mass=1000, carbon_content="50%", mass_unit="kg")
    # 0.5% is exactly 1/100 of 50%
    assert res_half_pct["total_co2e"] == pytest.approx(res_fifty_pct["total_co2e"] / 100.0, rel=1e-4)

    # 1% carbon content must be exactly 1/100 of 100%
    res_one_pct = calc.calculate(fuel_mass=1000, carbon_content="1%", mass_unit="kg")
    res_hundred_pct = calc.calculate(fuel_mass=1000, carbon_content="100%", mass_unit="kg")
    assert res_one_pct["total_co2e"] == pytest.approx(res_hundred_pct["total_co2e"] / 100.0, rel=1e-4)


def test_nitric_acid_calculator_percent_abatement():
    calc = NitricAcidCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(production_amount=-50)

    # Abatement efficiency 0.5% vs 50%
    res_half_pct = calc.calculate(production_amount=100, abatement_efficiency="0.5%")
    res_fifty_pct = calc.calculate(production_amount=100, abatement_efficiency="50%")
    # 0.5% abatement leaves 99.5% unabated; 50% abatement leaves 50% unabated
    assert res_half_pct["total_co2e"] == pytest.approx(res_fifty_pct["total_co2e"] * (0.995 / 0.50), rel=1e-4)


# ==============================================================================
# Bug 56, 57, 58: Fugitive Calculators
# ==============================================================================
def test_component_fugitive_percent_parsing_and_bounds():
    calc = ComponentFugitiveCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(component_counts={"valves": 10}, ch4_content="-10%", uncertainties=None)

    # Percentage string parsing
    res = calc.calculate(component_counts={"valves": 10}, ch4_content="85%", uncertainties=None)
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0


def test_equipment_fugitive_bounds_and_percent():
    calc = EquipmentFugitiveCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(equipment_count=-5, ef=1.5, ch4_content="85%")

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(equipment_count=5, ef=-1.5, ch4_content="85%")

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(equipment_count=5, ef=1.5, ch4_content="-10%")

    res = calc.calculate(equipment_count=5, ef=0.5, ch4_content="90%")
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0


def test_compressor_seal_bounds():
    calc = CompressorSealCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(compressor_count=-2, seal_type="reciprocating")

    res = calc.calculate(compressor_count=3, seal_type="reciprocating", segment="production")
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0


# ==============================================================================
# Bug 59 & 60: Midstream AGR & Dehydrator Calculations
# ==============================================================================
def test_agr_calculator_bounds_and_percent_normalization():
    calc = AGRCalculator()

    # Negative throughput
    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(throughput=-10, co2_in=0.04)

    # 0.5% CO2 in vs 50% CO2 in
    res_half_pct = calc.calculate(throughput=10, co2_in="0.5%", co2_out=0.0)
    res_fifty_pct = calc.calculate(throughput=10, co2_in="50%", co2_out=0.0)
    # CO2 mass from 0.5% is exactly 1/100th of 50%
    assert res_half_pct["results"]["co2"]["value"] == pytest.approx(res_fifty_pct["results"]["co2"]["value"] / 100.0, rel=1e-4)


def test_dehydrator_calculator_percent_normalization():
    calc = DehydratorCalculator()

    with pytest.raises(ValueError, match="cannot be negative"):
        calc.calculate(throughput=-5, ch4_content="85%")

    res_half_pct = calc.calculate(throughput=10, ch4_content="0.5%")
    res_fifty_pct = calc.calculate(throughput=10, ch4_content="50%")
    # 0.5% CH4 gives exactly 1/100th of emissions from 50% CH4
    assert res_half_pct["total_co2e"] == pytest.approx(res_fifty_pct["total_co2e"] / 100.0, rel=1e-4)
