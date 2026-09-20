"""
Battery 4: Compressor Seals & Specialized Equipment Fugitives Test Suite.
========================================================================
Verifies detailed fugitive methodologies across compressors, equipment, and components:
1. Compressor Seals (API §7.2.3: centrifugal wet, dry, reciprocating rod packing).
2. Equipment-Level Fugitives (API §7.2.2: hourly vs annual EFs, tonne vs kg, methane scaling).
3. Component-Level Fugitives (API §7.2: multi-component inventories, screening factors).
"""
import pytest
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.fugitive import (
    CompressorSealCalculator,
    EquipmentFugitiveCalculator,
    ComponentFugitiveCalculator,
)
from calculations.constants import GWP_AR5
from validation.reference_model.fugitives import IndependentFugitiveModel


def _val(x):
    if isinstance(x, dict):
        return x.get("value", 0.0)
    return float(x or 0.0)


class TestCompressorSealBattery:
    """Verifies API §7.2.3 compressor seal leakage across all mechanical configurations."""

    @pytest.mark.parametrize("seal_type, count, expected_ef", [
        ("centrifugal_wet", 4, 15.0),
        ("centrifugal_dry", 6, 1.5),
        ("reciprocating", 10, 1.2),
    ])
    def test_compressor_seal_types(self, seal_type, count, expected_ef):
        calc = CompressorSealCalculator()
        res = calc.calculate(compressor_count=count, seal_type=seal_type, uncertainties={}, gwp_dict=GWP_AR5)
        ref = IndependentFugitiveModel.calculate_compressor_seal(count=count, seal_type=seal_type, gwp_standard="AR5")

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == ref["ch4"]
        assert pytest.approx(res["total_co2e"], rel=1e-5) == ref["co2e"]
        # Explicit annual check: count * ef * 8760 / 1000
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == (count * expected_ef * 8760.0) / 1000.0


class TestEquipmentFugitiveBattery:
    """Verifies API §7.2.2 equipment-level fugitives with unit and methane normalizations."""

    def test_hourly_factor_hydrocarbon_gas(self):
        calc = EquipmentFugitiveCalculator()
        count = 8
        ef_kg_hr = 0.45  # kg total gas / hr / equipment
        ch4_content = 0.82

        res = calc.calculate(
            equipment_count=count,
            ef=ef_kg_hr,
            ch4_content=ch4_content,
            uncertainties={},
            ef_unit="kg/hr",
            gwp_dict=GWP_AR5,
        )
        ref = IndependentFugitiveModel.calculate_equipment(
            count=count,
            ef=ef_kg_hr,
            ef_unit="kg/hr",
            ch4_content=ch4_content,
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == ref["ch4"]
        assert pytest.approx(res["total_co2e"], rel=1e-5) == ref["co2e"]

    def test_annual_factor_already_methane(self):
        calc = EquipmentFugitiveCalculator()
        count = 15
        ef_tonne_yr = 1.25  # tonnes CH4 / yr / equipment

        res = calc.calculate(
            equipment_count=count,
            ef=ef_tonne_yr,
            ch4_content=0.75,  # Should be ignored because factor is already methane
            uncertainties={},
            ef_unit="tonne CH4/yr",
            gwp_dict=GWP_AR5,
        )
        ref = IndependentFugitiveModel.calculate_equipment(
            count=count,
            ef=ef_tonne_yr,
            ef_unit="tonne CH4/yr",
            ch4_content=0.75,
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == ref["ch4"]
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == count * ef_tonne_yr


class TestComponentFugitiveBattery:
    """Verifies API §7.2 average factor method with component count dictionaries."""

    def test_multi_component_facility_inventory(self):
        calc = ComponentFugitiveCalculator()
        component_counts = {
            "valves": {"count": 250, "ef": 0.026, "unit": "kg/hr"},
            "connectors": {"count": 1200, "ef": 0.003, "unit": "kg/hr"},
            "flanges": {"count": 800, "ef": 0.0015, "unit": "kg/hr"},
            "relief_valves": {"count": 45, "ef": 0.088, "unit": "kg ch4/hr", "is_methane": True},
        }
        ch4_content = 0.85

        res = calc.calculate(component_counts=component_counts, ch4_content=ch4_content, uncertainties={}, gwp_dict=GWP_AR5)
        ref = IndependentFugitiveModel.calculate_component(component_counts=component_counts, ch4_content=ch4_content, gwp_standard="AR5")

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == ref["ch4"]
        assert pytest.approx(res["total_co2e"], rel=1e-5) == ref["co2e"]
