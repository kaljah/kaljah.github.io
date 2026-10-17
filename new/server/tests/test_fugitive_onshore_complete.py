"""Exhaustive test suite for API GHG Compendium Chapter 7 Onshore Equipment Leaks & Fugitives.

Covers:
- calculations/fugitive_onshore.py:
  - convert_fugitive_flow_to_kg_hr (volumetric, mass, whole-gas speciation, edge cases)
  - OnshoreFacilityFugitiveCalculator (Tier 1 facility-level average factors)
  - OnshoreEquipmentFugitiveCalculator (Tier 2A equipment-level population factors)
  - OnshoreComponentFugitiveCalculator (Tier 2B component-level population factors)
  - OnshoreScreeningMeasurementCalculator:
    - calculate_method21_ranges (Tier 3A EPA Method 21 screening ranges)
    - calculate_correlation_equation (Tier 3B correlation equations)
    - calculate_ogi_survey (Tier 3C Optical Gas Imaging leaker surveys)
    - calculate_direct_measurement (Tier 3D Hi-Flow / bagging direct measurement)
"""
import pytest
from calculations.fugitive_onshore import (
    convert_fugitive_flow_to_kg_hr,
    OnshoreFacilityFugitiveCalculator,
    OnshoreEquipmentFugitiveCalculator,
    OnshoreComponentFugitiveCalculator,
    OnshoreScreeningMeasurementCalculator,
    DENSITY_CH4,
    DENSITY_CO2,
    MW_CH4,
    MW_CO2,
)
from calculations.constants import DEFAULT_GWP


# ---------------------------------------------------------------------------
# Flow Rate Conversion Tests
# ---------------------------------------------------------------------------

def test_convert_fugitive_flow_volumetric():
    # 100 m3/hr whole gas with 80% CH4, 2% CO2
    res = convert_fugitive_flow_to_kg_hr(100.0, "m3/hr", ch4_mol=0.80, co2_mol=0.02)
    expected_ch4 = 100.0 * 0.80 * DENSITY_CH4
    expected_co2 = 100.0 * 0.02 * DENSITY_CO2
    assert res["ch4_kg_hr"] == pytest.approx(expected_ch4)
    assert res["co2_kg_hr"] == pytest.approx(expected_co2)

    # scf/hr
    res_scf = convert_fugitive_flow_to_kg_hr(3531.46667, "scf/hr", ch4_mol=0.80, co2_mol=0.02)
    assert res_scf["ch4_kg_hr"] == pytest.approx(expected_ch4, rel=1e-3)

    # Missing CH4 mol% on volumetric rate must raise ValueError
    with pytest.raises(ValueError) as exc:
        convert_fugitive_flow_to_kg_hr(100.0, "m3/hr", ch4_mol=None)
    assert "needs the gas CH4 content" in str(exc.value)


def test_convert_fugitive_flow_mass():
    # 50 kg/hr pure CH4 mass rate
    res = convert_fugitive_flow_to_kg_hr(50.0, "kg/hr")
    assert res["ch4_kg_hr"] == 50.0
    assert res["co2_kg_hr"] == 0.0

    # 50 kg/hr CH4 with CO2 speciation
    res_co2 = convert_fugitive_flow_to_kg_hr(50.0, "kg/hr", ch4_mol=0.80, co2_mol=0.05)
    expected_co2 = 50.0 * (0.05 / 0.80) * (MW_CO2 / MW_CH4)
    assert res_co2["ch4_kg_hr"] == 50.0
    assert res_co2["co2_kg_hr"] == pytest.approx(expected_co2)

    # lb/hr conversion (1 lb = 0.45359237 kg)
    res_lb = convert_fugitive_flow_to_kg_hr(100.0, "lb/hr")
    assert res_lb["ch4_kg_hr"] == pytest.approx(45.359237)


def test_convert_fugitive_flow_unknown_unit_raises():
    with pytest.raises(ValueError) as exc:
        convert_fugitive_flow_to_kg_hr(10.0, "gallons_per_century")
    assert "Unknown leak rate unit" in str(exc.value)


# ---------------------------------------------------------------------------
# Tier 1: Facility-Level Average Factors
# ---------------------------------------------------------------------------

def test_tier1_facility_calculator_oil_and_gas():
    calc = OnshoreFacilityFugitiveCalculator()

    # Gas processing facility: throughput in MMscf
    res_gas = calc.calculate(
        production=50.0,
        production_unit="mmscf",
        facility_type="gas_production",
    )
    assert res_gas["results"]["ch4"]["value"] > 0
    assert res_gas["total_co2e"] > 0
    assert "Tier 1" in res_gas["intermediate"]["methodology"]

    # Onshore oil production facility
    res_oil = calc.calculate(
        production=10_000.0,
        production_unit="bbl",
        facility_type="oil_production",
    )
    assert res_oil["results"]["ch4"]["value"] > 0
    assert res_oil["total_co2e"] > 0


def test_tier1_facility_validation():
    calc = OnshoreFacilityFugitiveCalculator()
    with pytest.raises(ValueError):
        calc.calculate(production=100.0, production_unit="bbl", facility_type="invalid_type")
    with pytest.raises(ValueError):
        calc.calculate(production=-5.0, production_unit="bbl", facility_type="oil_production")


# ---------------------------------------------------------------------------
# Tier 2A: Equipment-Level Population Factors
# ---------------------------------------------------------------------------

def test_tier2a_equipment_calculator():
    calc = OnshoreEquipmentFugitiveCalculator()

    res = calc.calculate(
        equipment_count=10,
        equipment_type="wellhead",
        service_type="Gas",
        operating_hours=8760,
        factor_value=0.015,
        factor_unit="tonne CH4/well/hr",
    )
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0
    assert "Tier 2A" in res["intermediate"]["methodology"]

    # Verify linear scaling with operating hours
    res_half = calc.calculate(
        equipment_count=10,
        equipment_type="wellhead",
        service_type="Gas",
        operating_hours=4380,
        factor_value=0.015,
        factor_unit="tonne CH4/well/hr",
    )
    assert res_half["results"]["ch4"]["value"] == pytest.approx(res["results"]["ch4"]["value"] / 2.0, rel=1e-3)


# ---------------------------------------------------------------------------
# Tier 2B: Component-Level Population Factors
# ---------------------------------------------------------------------------

def test_tier2b_component_calculator():
    calc = OnshoreComponentFugitiveCalculator()

    components = {
        "valves": 250,
        "flanges": 600,
        "connectors": 450,
        "open_ended_line": 30,
        "pump_seals": 8,
    }

    res = calc.calculate(
        component_counts=components,
        service_type="Gas",
        operating_hours=8760,
        ch4_content=85.0,
        co2_content=3.0,
    )
    assert res["results"]["ch4"]["value"] > 0
    assert res["results"]["co2"]["value"] > 0
    assert res["total_co2e"] >= res["results"]["ch4"]["value"] * DEFAULT_GWP["CH4"]


# ---------------------------------------------------------------------------
# Tier 3: Screening & Measurement Methodologies
# ---------------------------------------------------------------------------

def test_tier3a_method21_screening_ranges():
    calc = OnshoreScreeningMeasurementCalculator()

    res = calc.calculate_method21_ranges(
        component_type="valve",
        service_type="gas",
        non_pegged_count=95,
        pegged_count=5,
        operating_hours=8760,
        ch4_content=85.0,
    )
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0
    assert "Tier 3A" in res["intermediate"]["methodology"]


def test_tier3b_correlation_equations():
    calc = OnshoreScreeningMeasurementCalculator()

    res = calc.calculate_correlation_equation(
        component_type="valves",
        screening_values_ppm=[500, 25000],
        zero_count=10,
        pegged_10k_count=2,
        operating_hours=8760,
        ch4_content=85.0,
    )
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0
    assert "Tier 3B" in res["intermediate"]["methodology"]


def test_tier3c_ogi_leaker_survey():
    calc = OnshoreScreeningMeasurementCalculator()

    res = calc.calculate_ogi_survey(
        component_type="valve",
        service_type="gas",
        total_surveyed=100,
        leakers_detected=4,
        operating_hours=2190,  # 1 quarter
        ch4_mol=0.90,
    )
    assert res["results"]["ch4"]["value"] > 0
    assert res["total_co2e"] > 0
    assert "Tier 3C" in res["intermediate"]["methodology"]


def test_tier3d_direct_measurement():
    calc = OnshoreScreeningMeasurementCalculator()

    # Direct measurement in m3/hr
    res_vol = calc.calculate_direct_measurement(
        measured_rate=2.5,
        measurement_unit="m3/hr",
        operating_hours=720,
        ch4_mol=0.85,
        co2_mol=0.02,
    )
    assert res_vol["results"]["ch4"]["value"] > 0
    assert res_vol["results"]["co2"]["value"] > 0
    assert res_vol["total_co2e"] > 0
    assert "Tier 3D" in res_vol["intermediate"]["methodology"]

    # Direct measurement in kg/hr
    res_mass = calc.calculate_direct_measurement(
        measured_rate=1.2,
        measurement_unit="kg/hr",
        operating_hours=720,
        ch4_mol=0.85,
        co2_mol=0.02,
    )
    assert res_mass["results"]["ch4"]["value"] > 0
    assert res_mass["total_co2e"] > 0
