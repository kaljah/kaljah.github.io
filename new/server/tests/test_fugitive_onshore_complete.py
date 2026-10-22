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

    # Gas production facility: 50 MMscf x 2.601e-2 t CH4 / 10^6 scf (Table 7-8, 78.8 mol % basis)
    res_gas = calc.calculate(
        production=50.0,
        production_unit="mmscf",
        facility_type="gas_production",
    )
    assert res_gas["results"]["ch4"]["value"] == pytest.approx(50.0 * 2.601e-2, rel=1e-9)
    assert res_gas["total_co2e"] == pytest.approx(50.0 * 2.601e-2 * 28.0, rel=1e-9)   # AR5 GWP of CH4
    assert "Tier 1" in res_gas["intermediate"]["methodology"]

    # Onshore oil production facility: 10,000 bbl x 2.346e-4 t CH4/bbl (Table 7-8)
    res_oil = calc.calculate(
        production=10_000.0,
        production_unit="bbl",
        facility_type="oil_production",
    )
    assert res_oil["results"]["ch4"]["value"] == pytest.approx(10_000.0 * 2.346e-4, rel=1e-9)
    assert res_oil["total_co2e"] == pytest.approx(10_000.0 * 2.346e-4 * 28.0, rel=1e-9)


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
    # Table 7-12, gas service, tonne CH4/hr/component at 81.6 mol % CH4: valves 2.94E-06, flanges 2.54E-07,
    # connectors 1.30E-07, open-ended lines 1.30E-06, pump seals 1.57E-06; scaled to the site's 85 mol % CH4
    per_hr = 250 * 2.94e-6 + 600 * 2.54e-7 + 450 * 1.30e-7 + 30 * 1.30e-6 + 8 * 1.57e-6
    ch4 = per_hr * 8760 * 0.85 / 0.816
    assert res["results"]["ch4"]["value"] == pytest.approx(ch4, rel=1e-3)  # 9.10 t
    # CO2 from the whole-gas factors (scf gas/hr/component: 0.188, 1.63E-02, 8.36E-03, 8.36E-02, 0.100) x 3 mol % CO2
    gas_scf_hr = 250 * 0.188 + 600 * 1.63e-2 + 450 * 8.36e-3 + 30 * 8.36e-2 + 8 * 0.100
    co2 = gas_scf_hr * 8760 * 0.03 / 379.3 * 44.01 / 2204.62
    assert res["results"]["co2"]["value"] == pytest.approx(co2, rel=2e-3)  # 0.883 t
    assert res["total_co2e"] == pytest.approx(28.0 * res["results"]["ch4"]["value"] + res["results"]["co2"]["value"],
                                              rel=1e-9)


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
    # Table 7-26, gas valves: 2.5e-5 kg TOC/h below 10,000 ppmv, 9.8e-2 kg TOC/h at or above; CH4 share 0.85
    toc_kg_hr = 95 * 2.5e-5 + 5 * 9.8e-2
    assert res["results"]["ch4"]["value"] == pytest.approx(toc_kg_hr * 8760 / 1000 * 0.85, rel=1e-9)
    assert res["total_co2e"] == pytest.approx(toc_kg_hr * 8760 / 1000 * 0.85 * 28.0, rel=1e-9)
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
    # Tables 7-40 to 7-42, valves: leak rate 2.29e-6 x SV^0.746 kg TOC/h; default zero 7.8e-6 kg/h; 10,000 ppm pegged 0.064 kg/h
    toc_kg_hr = 10 * 7.8e-6 + 2.29e-6 * (500 ** 0.746 + 25000 ** 0.746) + 2 * 0.064
    assert res["results"]["ch4"]["value"] == pytest.approx(toc_kg_hr * 8760 / 1000 * 0.85, rel=1e-9)
    assert res["total_co2e"] == pytest.approx(toc_kg_hr * 8760 / 1000 * 0.85 * 28.0, rel=1e-9)
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
    # Table 7-23: gas valve leaker 4.9 scf whole gas/h; 4 leakers x 2,190 h at 90 mol % CH4 (60 F, 23.685 m3/kmol)
    ch4_t = 4 * 4.9 * 2190 * 0.028316846592 * 0.90 * (16.04 / 23.685) / 1000
    assert res["results"]["ch4"]["value"] == pytest.approx(ch4_t, rel=1e-9)
    assert res["total_co2e"] == pytest.approx(ch4_t * 28.0, rel=1e-9)
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
    # 2.5 m3/h of whole gas for 720 h at 85 mol % CH4 and 2 % CO2 (60 F, 23.685 m3/kmol)
    ch4_t = 2.5 * 720 * 0.85 * (16.04 / 23.685) / 1000
    co2_t = 2.5 * 720 * 0.02 * (44.01 / 23.685) / 1000
    assert res_vol["results"]["ch4"]["value"] == pytest.approx(ch4_t, rel=1e-9)
    assert res_vol["results"]["co2"]["value"] == pytest.approx(co2_t, rel=1e-9)
    assert res_vol["total_co2e"] == pytest.approx(ch4_t * 28.0 + co2_t, rel=1e-9)
    assert "Tier 3D" in res_vol["intermediate"]["methodology"]

    # Direct measurement in kg/hr
    res_mass = calc.calculate_direct_measurement(
        measured_rate=1.2,
        measurement_unit="kg/hr",
        operating_hours=720,
        ch4_mol=0.85,
        co2_mol=0.02,
    )
    # 1.2 kg/h is CH4 mass: 720 h -> 0.864 t; the CO2 follows from the 2 : 85 mole ratio
    assert res_mass["results"]["ch4"]["value"] == pytest.approx(1.2 * 720 / 1000, rel=1e-9)
    co2_t = 1.2 * 720 / 1000 * (0.02 / 0.85) * (44.01 / 16.04)
    assert res_mass["results"]["co2"]["value"] == pytest.approx(co2_t, rel=1e-9)
    assert res_mass["total_co2e"] == pytest.approx(1.2 * 720 / 1000 * 28.0 + co2_t, rel=1e-9)
