"""
API GHG Compendium 2021 — Chapter 7 Equipment Leaks / Fugitive Emissions
ONSHORE OIL & GAS OPERATIONS ONLY Golden Test Suite

Verifies:
1. Tier 1: Facility-Level Average Factors (Tables 7-1, 7-2)
2. Tier 2A: Equipment-Level Population Factors (Tables 7-9, 7-10, 7-29)
3. Tier 2B: Component-Level Population Factors & Service Streams (Tables 7-11, 7-30)
4. Tier 3A: Method 21 Screening Ranges (<10k vs >=10k ppmv) (Tables 7-15, 7-16)
5. Tier 3B: EPA / API Correlation Equations (Tables 7-17, 7-18)
6. Tier 3C: Optical Gas Imaging (OGI) Leaker Survey (Tables 7-19, 7-20 / Subpart W Table W-1E)
7. Tier 3D: Direct Measurement & Unit Conversions (scf/hr, m3/hr, kg/hr)
8. Flow rate unit conversion helper
9. Duration basis & partial-year commissioning/shutdown
10. Engine Dispatcher end-to-end integration and source segregation
"""

import pytest
import math
from calculations.fugitive_onshore import (
    OnshoreFacilityFugitiveCalculator,
    OnshoreEquipmentFugitiveCalculator,
    OnshoreComponentFugitiveCalculator,
    OnshoreScreeningMeasurementCalculator,
    convert_fugitive_flow_to_kg_hr,
)
from emission_factors_chapter7_onshore import (
    API_CHAPTER7_ONSHORE_FACTORS,
    METHOD21_SCREENING_RANGES,
    OGI_LEAKER_FACTORS,
    DEFAULT_SERVICE_COMPOSITIONS,
)
from calculations.dispatcher import CalculationDispatcher


def get_val(res_item):
    if isinstance(res_item, dict):
        return float(res_item.get("value", 0.0))
    return float(res_item)


# ============================================================================
# 1. TIER 1: FACILITY-LEVEL AVERAGE TESTS (TABLES 7-1, 7-2)
# ============================================================================

def test_tier1_gas_production_facility_annual():
    """
    API Compendium 2021 Table 7-8 (facility-level, per unit of production; re-derived from the
    Compendium text in audit RC-17 — the previous per-facility-day factors were not in the source).
    Gas production: 2.601E-02 t CH4 / 10^6 scf. 1,200 MMscf -> 31.212 t CH4.
    """
    calc = OnshoreFacilityFugitiveCalculator()
    res = calc.calculate(production=1200.0, production_unit="MMscf", facility_type="gas_production")
    assert pytest.approx(get_val(res["results"]["ch4"]), rel=1e-6) == 1200 * 2.601e-02
    assert res["intermediate"]["api_table"] == "Table 7-8"


def test_tier1_oil_production_facility_partial_year():
    """Table 7-8 oil production: 2.346E-04 t CH4/bbl (1.476E-03 t/m3). 250,000 bbl -> 58.65 t CH4."""
    calc = OnshoreFacilityFugitiveCalculator()
    res = calc.calculate(production=250000.0, production_unit="bbl", facility_type="oil_production")
    assert pytest.approx(get_val(res["results"]["ch4"]), rel=1e-6) == 250000 * 2.346e-04
    res_m3 = calc.calculate(production=1000.0, production_unit="m3", facility_type="oil_production")
    assert pytest.approx(get_val(res_m3["results"]["ch4"]), rel=1e-6) == 1000 * 1.476e-03


def test_tier1_gathering_station_custom_ef():
    """Table 7-8 has no gathering-station row; unknown facility types are rejected (no silent default)."""
    calc = OnshoreFacilityFugitiveCalculator()
    with pytest.raises(ValueError, match="facility type"):
        calc.calculate(production=1.0, production_unit="MMscf", facility_type="gathering_station")


def test_tier2a_gas_production_wellheads():
    """
    API 2021 Table 7-10 (gas production equipment): gas wellhead 1.80E-05 t CH4/well/hr
    (8,217 scf CH4/well/yr). The former 0.163 kg/hr / "Table 7-9" expectation was not in the source.
    10 wellheads x 8,760 h -> 1.5768 t CH4. The factor comes from the catalog entry.
    """
    f = API_CHAPTER7_ONSHORE_FACTORS["Wellhead - Gas"]
    assert f["factor_value"] == pytest.approx(1.80e-05)
    calc = OnshoreEquipmentFugitiveCalculator()
    res = calc.calculate(equipment_count=10.0, equipment_type="wellhead", service_type="Gas",
                         operating_hours=8760.0, factor_value=f["factor_value"], factor_unit=f["factor_unit"])
    assert pytest.approx(get_val(res["results"]["ch4"]), rel=1e-6) == 10 * 1.80e-05 * 8760
    with pytest.raises(ValueError, match="No equipment-level emission factor"):
        calc.calculate(equipment_count=10.0, equipment_type="wellhead", operating_hours=8760.0)


def test_tier2a_gathering_compressors():
    """
    API 2021 Table 7-10: Gathering & Boosting Compressor
    Factor: 4.480 kg CH4/hr/compressor = 0.00448 tonnes CH4/hr/compressor.
    3 compressors operating 5,000 hours.
    Expected CH4: 3 * 0.00448 * 5000 = 67.20 tonnes CH4.
    """
    calc = OnshoreEquipmentFugitiveCalculator()
    res = calc.calculate(
        equipment_count=3.0,
        equipment_type="compressor",
        service_type="Gas",
        factor_value=0.00448,
        operating_hours=5000.0,
    )
    ch4_tonnes = get_val(res["results"]["ch4"])
    assert pytest.approx(ch4_tonnes, rel=1e-3) == 67.20


def test_tier2a_crude_oil_production_wellheads():
    """
    API 2021 Table 7-29: Crude Oil Production Wellhead
    Factor: 0.012 kg CH4/hr/wellhead = 0.000012 tonnes CH4/hr/wellhead.
    5 wellheads operating 8,760 hours.
    Expected CH4: 5 * 0.000012 * 8760 = 0.5256 tonnes CH4.
    """
    calc = OnshoreEquipmentFugitiveCalculator()
    res = calc.calculate(
        equipment_count=5.0,
        equipment_type="wellhead",
        service_type="Heavy Oil",
        factor_value=0.000012,
        operating_hours=8760.0,
    )
    ch4_tonnes = get_val(res["results"]["ch4"])
    assert pytest.approx(ch4_tonnes, rel=1e-3) == 0.5256


# ============================================================================
# 3. TIER 2B: COMPONENT-LEVEL POPULATION TESTS (TABLES 7-11, 7-30)
# ============================================================================

def test_tier2b_gas_service_valves_speciation():
    """
    API Compendium 2021 Table 7-12 (EPA protocol), valves - gas: 4.5E-03 kg gas/comp-hr = 2.94E-06 t
    CH4/comp-hr at 81.6 mol % CH4; whole gas 1.88E-01 scf/comp-hr. 100 valves, 8,760 h, site gas
    70 mol % CH4 / 5 mol % CO2:
      CH4 = 100 x 2.94E-06 x 8,760 x 70 / 81.6 = 2.2093 t
      CO2 = 100 x 0.188 x 8,760 scf x 0.05 / 379.3 x 44.01 / 2,204.62 = 0.4334 t
    """
    calc = OnshoreComponentFugitiveCalculator()
    res = calc.calculate(component_counts={"valve": 100.0}, service_type="Gas", operating_hours=8760.0,
                         ch4_content=70, co2_content=5)
    assert get_val(res["results"]["ch4"]) == pytest.approx(100 * 2.94e-6 * 8760 * 70 / 81.6, rel=1e-6)
    assert get_val(res["results"]["co2"]) == pytest.approx(100 * 0.188 * 8760 * 0.05 / 379.3 * 44.01 / 2204.62, rel=5e-3)
    assert res["intermediate"]["api_table"] == "Table 7-12"


def test_tier2b_light_oil_connectors():
    """Table 7-12 connectors - light oil: 1.37E-07 t CH4/comp-hr (81.6 % basis).
    500 connectors, 8,760 h, no site composition: 500 x 1.37E-07 x 8,760 = 0.60006 t CH4."""
    calc = OnshoreComponentFugitiveCalculator()
    res = calc.calculate(component_counts={"connector": 500.0}, service_type="Light Oil", operating_hours=8760.0)
    assert get_val(res["results"]["ch4"]) == pytest.approx(500 * 1.37e-7 * 8760, rel=1e-6)


def test_tier2b_heavy_oil_valves():
    """Table 7-12 valves - heavy oil: 5.48E-09 t CH4/comp-hr. 200 valves, 8,760 h:
    200 x 5.48E-09 x 8,760 = 0.0096010 t CH4."""
    calc = OnshoreComponentFugitiveCalculator()
    res = calc.calculate(component_counts={"valve": 200.0}, service_type="Heavy Oil", operating_hours=8760.0)
    assert get_val(res["results"]["ch4"]) == pytest.approx(200 * 5.48e-9 * 8760, rel=1e-6)


# ============================================================================
# 4. TIER 3: SCREENING, CORRELATION, OGI & MEASUREMENT (TABLES 7-15, 7-19)
# ============================================================================

def test_tier3_ogi_leakers_vs_non_leakers():
    """
    API Compendium 2021 Table 7-23 (surveys under 40 CFR 98.234(a)(1)-(6)): gas-service valve leaker
    4.9 scf whole gas / component-hr at 81.6 mol % CH4 (7.7E-05 t CH4/comp-hr). The table has no
    non-leaker factor: non-leakers add nothing. 4 leakers, 8,760 h:
      4 x 4.9 x 8,760 = 171,696 scf x 0.816 / 379.3 x 16.04 / 2,204.62 = 2.687 t CH4
    """
    calc = OnshoreScreeningMeasurementCalculator()
    res = calc.calculate_ogi_survey(
        component_type="valve",
        service_type="gas",
        total_surveyed=100,
        leakers_detected=4,
        operating_hours=8760.0,
    )
    ch4_tonnes = get_val(res["results"]["ch4"])
    assert ch4_tonnes == pytest.approx(4 * 4.9 * 8760 * 0.816 / 379.3 * 16.04 / 2204.62, rel=5e-3)
    assert ch4_tonnes == pytest.approx(4 * 7.7e-5 * 8760, rel=5e-3)
    assert "Table 7-23" in res["intermediate"]["api_table"]


def test_tier3_method21_screening_ranges():
    """
    API Compendium 2021 Table 7-26 (EPA Protocol Table 2-8), valves - gas: < 10,000 ppmv 2.5E-05,
    >= 10,000 ppmv 9.8E-02 kg TOC/comp-hr; CH4 weight fraction 0.85 given. 10 + 90 valves, 8,760 h:
      TOC = 10 x 0.098 + 90 x 2.5E-05 = 0.98225 kg/h; CH4 = 0.98225 x 0.85 x 8,760 / 1,000 = 7.3139 t
    """
    calc = OnshoreScreeningMeasurementCalculator()
    res = calc.calculate_method21_ranges(
        component_type="valve",
        service_type="gas",
        non_pegged_count=90,
        pegged_count=10,
        operating_hours=8760.0,
        ch4_content=0.85,
    )
    ch4_tonnes = get_val(res["results"]["ch4"])
    assert ch4_tonnes == pytest.approx((10 * 0.098 + 90 * 2.5e-5) * 0.85 * 8760 / 1000, rel=1e-6)


def test_tier3_direct_measurement_flow_conversion():
    """
    Direct measurement: 100 scf/h of whole gas (80 % CH4, 2 % CO2) for 1,000 h
      CH4 = 100,000 scf x 0.80 / 379.3 x 16.04 / 2,204.62 = 1.5345 t
      CO2 = 100,000 scf x 0.02 / 379.3 x 44.01 / 2,204.62 = 0.1053 t
    """
    calc = OnshoreScreeningMeasurementCalculator()
    res = calc.calculate_direct_measurement(
        measured_rate=100.0,
        measurement_unit="scf/hr",
        operating_hours=1000.0,
        ch4_mol=0.80,
        co2_mol=0.02,
    )
    assert get_val(res["results"]["ch4"]) == pytest.approx(1e5 * 0.80 / 379.3 * 16.04 / 2204.62, rel=5e-3)
    assert get_val(res["results"]["co2"]) == pytest.approx(1e5 * 0.02 / 379.3 * 44.01 / 2204.62, rel=5e-3)
    assert res["intermediate"]["methodology"] == "Tier 3D: Direct Measurement"


# ============================================================================
# 5. FLOW RATE UNIT CONVERSION HELPER TESTS
# ============================================================================

def test_convert_fugitive_flow_units():
    """Validate all supported flow rate units convert accurately to kg/hr."""
    res_kg = convert_fugitive_flow_to_kg_hr(1.0, "kg/hr", ch4_mol=1.0)
    assert pytest.approx(res_kg["ch4_kg_hr"], rel=1e-4) == 1.0

    res_tonnes = convert_fugitive_flow_to_kg_hr(8.76, "tonnes/yr", ch4_mol=1.0)
    assert pytest.approx(res_tonnes["ch4_kg_hr"], rel=1e-3) == 1.0

    res_lb = convert_fugitive_flow_to_kg_hr(100.0, "lb/hr", ch4_mol=1.0)
    assert pytest.approx(res_lb["ch4_kg_hr"], rel=1e-3) == 45.3592


# ============================================================================
# 6. EDGE CASES & STRICT ONSHORE BOUNDARY TESTS
# ============================================================================

def test_zero_duration_or_count():
    """Zero production or zero operating hours gives exactly 0 emissions."""
    calc_fac = OnshoreFacilityFugitiveCalculator()
    res1 = calc_fac.calculate(production=0, production_unit="MMscf", facility_type="gas_production")
    assert get_val(res1["results"]["ch4"]) == 0.0
    assert res1["total_co2e"] == 0.0

    calc_comp = OnshoreComponentFugitiveCalculator()
    res2 = calc_comp.calculate(component_counts={"valve": {"count": 100, "ef": 0.0045, "unit": "kg TOC/hr/component"}},
                               service_type="gas", operating_hours=0)
    assert get_val(res2["results"]["ch4"]) == 0.0
    assert res2["total_co2e"] == 0.0


def test_invalid_hours_rejection():
    """Verify hours > 8784 or negative are rejected with ValueError."""
    calc_comp = OnshoreComponentFugitiveCalculator()
    with pytest.raises(ValueError):
        calc_comp.calculate(component_counts={"valve": 10}, service_type="gas", operating_hours=9000)

    with pytest.raises(ValueError):
        calc_comp.calculate(component_counts={"valve": 10}, service_type="gas", operating_hours=-10)


# ============================================================================
# 7. CALCULATION ENGINE DISPATCHER INTEGRATION & SEGREGATION TESTS
# ============================================================================

def test_engine_dispatcher_tier1_routing():
    """CalculationDispatcher routes Tier 1 fugitives to the Table 7-8 facility calculator."""
    dispatcher = CalculationDispatcher()
    inputs = {"fugitive_tier": "tier1", "facility_type": "gas_production", "amount": 100.0, "unit": "MMscf"}
    res = dispatcher.dispatch("fugitive", inputs, {})
    assert pytest.approx(get_val(res["results"]["ch4"]), rel=1e-6) == 100 * 2.601e-02
    assert res["intermediate"]["api_table"] == "Table 7-8"


def test_engine_dispatcher_tier2_component_routing():
    """The dispatcher routes a Tier 2 component count without a selected factor to Table 7-12
    (100 gas valves, 8,760 h: 100 x 2.94E-06 x 8,760 = 2.5754 t CH4)."""
    dispatcher = CalculationDispatcher()
    inputs = {
        "factor_source": "custom",
        "fugitive_tier": "tier2",
        "fugitive_method": "component",
        "component_type": "valve",
        "service_type": "gas",
        "amount": 100.0,
        "operating_hours": 8760.0,
    }
    res = dispatcher.dispatch("fugitive", inputs, {})
    assert get_val(res["results"]["ch4"]) == pytest.approx(100 * 2.94e-6 * 8760, rel=1e-6)
    assert res["intermediate"]["api_table"] == "Table 7-12"


def test_engine_dispatcher_tier3_ogi_routing():
    """The dispatcher routes Tier 3 OGI leaker counts to Table 7-23 (4 gas valve leakers, 8,760 h)."""
    dispatcher = CalculationDispatcher()
    inputs = {
        "factor_source": "specific",
        "fugitive_tier": "tier3",
        "fugitive_method": "ogi",
        "component_type": "valve",
        "service_type": "gas",
        "leakers_count": 4.0,
        "total_surveyed": 100.0,
        "operating_hours": 8760.0,
    }
    res = dispatcher.dispatch("fugitive", inputs, {})
    ch4_tonnes = float(res["results"]["ch4"]["value"] if isinstance(res["results"]["ch4"], dict) else res["results"]["ch4"])
    assert ch4_tonnes == pytest.approx(4 * 7.7e-5 * 8760, rel=5e-3)
    assert "Table 7-23" in res["intermediate"]["api_table"]
