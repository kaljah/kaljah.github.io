"""calculations/fugitive_onshore.py: the remaining refusals (API Compendium 2021 Tables 7-8, 7-12, 7-26); the
rest is in test_fugitive_onshore_complete.py."""
import pytest

from calculations.fugitive_onshore import (OnshoreComponentFugitiveCalculator, OnshoreFacilityFugitiveCalculator,
                                           OnshoreScreeningMeasurementCalculator, convert_fugitive_flow_to_kg_hr)


def test_volumetric_leak_rate_needs_the_gas_ch4():
    with pytest.raises(ValueError, match="needs the gas CH4 content"):
        convert_fugitive_flow_to_kg_hr(10, "scf/hr")
    with pytest.raises(ValueError, match="needs the gas CH4 content"):
        convert_fugitive_flow_to_kg_hr(10, "Mcf/day")                                           # shared rate parser
    from calculations.units import CONVERSIONS, volume_rate_m3_per_hour

    res = convert_fugitive_flow_to_kg_hr(24, "Mcf/day", ch4_mol=90)
    assert res["ch4_kg_hr"] == pytest.approx(24 * volume_rate_m3_per_hour("mcf/day") * 0.9 * CONVERSIONS["density_ch4"])


def test_gas_production_unit_refused():
    with pytest.raises(ValueError, match="Gas production must be in"):
        OnshoreFacilityFugitiveCalculator().calculate(100, "bbl", "gas_production", ch4_content=90)


@pytest.mark.parametrize("counts,kw,match", [
    ({"valve": 1}, dict(ch4_content=150), "between 0 and 100"),
    ({"valve": {"count": 2, "ef": 0.01, "unit": "kg TOC/hr/component"}}, dict(service_type="Water/Oil"),
     "CH4 weight fraction of TOC for 'Water/Oil'"),
    ({"widget": 3}, {}, "Table 7-12 has no factor for 'widget'"),
])
def test_component_refusals(counts, kw, match):
    with pytest.raises(ValueError, match=match):
        OnshoreComponentFugitiveCalculator().calculate(counts, **kw)


def test_unknown_component_with_no_count_is_skipped():
    res = OnshoreComponentFugitiveCalculator().calculate({"widget": 0, "valve": 1}, ch4_content=80)
    assert res["results"]["ch4"]["value"] > 0


@pytest.mark.parametrize("w", [-5, 150])
def test_method21_ch4_weight_range(w):
    with pytest.raises(ValueError, match="CH4 weight fraction must be between 0 and 100"):
        OnshoreScreeningMeasurementCalculator().calculate_method21_ranges("valve", "gas", 10, 0, ch4_content=w)
