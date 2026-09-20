"""
Emission Factor Selection, Resolution, and Precedence Verification Suite.
========================================================================
Validates emission factor resolution across:
1. Catalog Factor Resolution: segments (Upstream/Midstream/Downstream) and categories.
2. Custom vs Default Factor Precedence: custom factor overrides catalog defaults.
3. Fallback and Unit Handling: conversion between factor and activity units.
4. Scope 2 Grid Factor Resolution: regional grids and eGRID factors.
"""
import pytest
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from emission_factors import (
    ALL_EMISSION_FACTORS,
    SEGMENTS,
    CATEGORIES,
    get_factor_by_segment,
    get_factor_by_process_category,
    get_factors_by_segment_and_category,
)
from electricity_factors import GRID_FACTORS
from calculations.combustion import convert_factor_to_kg_per_unit
from calculations.dispatcher import CalculationDispatcher
from calculations.constants import GWP_AR5


@pytest.fixture(scope="module")
def dispatcher():
    return CalculationDispatcher()


class TestCatalogFactorIntegrity:
    """Validates structure and completeness of the API 2021 factor catalog."""

    def test_catalog_has_comprehensive_factors(self):
        """API Compendium 2021 database must contain all published factors."""
        assert len(ALL_EMISSION_FACTORS) >= 50

    def test_catalog_segments_represented(self):
        """Every registered segment has non-empty factor sets."""
        for seg in SEGMENTS:
            factors = get_factor_by_segment(seg.capitalize())
            assert len(factors) > 0, f"No factors found for segment {seg}"

    def test_factor_metadata_validity(self):
        """Every factor must have unit, category, and valid numerical emissions."""
        for name, data in ALL_EMISSION_FACTORS.items():
            assert "unit" in data, f"Factor {name} missing unit"
            has_gas = any(g in data for g in ["co2", "ch4", "n2o", "factor"])
            assert has_gas, f"Factor {name} has no gas factor value"
            for g in ["co2", "ch4", "n2o"]:
                if g in data and data[g] is not None:
                    val = float(data[g])
                    assert val >= 0.0, f"Negative factor {val} in {name} for {g}"


class TestFactorPrecedenceAndCustomOverrides:
    """Verifies that user-supplied custom factors override default catalog values."""

    def test_custom_factor_overrides_default(self, dispatcher):
        qty = 5000.0
        unit = "m3"
        # Standard default factor
        default_ef = {"co2": 53.06, "ch4": 0.001, "n2o": 0.0001, "unit": "kg/MMBtu"}
        # Custom user-provided factor with different values
        custom_ef = {"co2": 65.0, "ch4": 0.005, "n2o": 0.0005, "unit": "kg/MMBtu"}

        res_default = dispatcher.dispatch(
            "stationary_combustion",
            {"quantity": qty, "unit": unit, "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "default"},
            default_ef,
            {},
            gwp_dict=GWP_AR5,
        )
        res_custom = dispatcher.dispatch(
            "stationary_combustion",
            {"quantity": qty, "unit": unit, "fuel_type": "natural_gas", "hhv": 1020.0, "factor_source": "custom"},
            custom_ef,
            {},
            gwp_dict=GWP_AR5,
        )

        assert res_custom["results"]["co2"]["value"] > res_default["results"]["co2"]["value"]
        ratio = res_custom["results"]["co2"]["value"] / res_default["results"]["co2"]["value"]
        assert pytest.approx(ratio, rel=1e-4) == 65.0 / 53.06


class TestGridFactorResolution:
    """Validates Scope 2 grid electricity factor repository."""

    @pytest.mark.parametrize("grid_name", [
        "Algerian National Grid",
        "US Average",
        "US-ERCOT",
        "UK National Grid",
    ])
    def test_grid_factors_validity(self, grid_name):
        assert grid_name in GRID_FACTORS
        factor_info = GRID_FACTORS[grid_name]
        assert factor_info["factor"] > 0.0
        assert "kWh" in factor_info["unit"]
        assert "source" in factor_info


class TestUnitAwareFactorConversion:
    """Tests convert_factor_to_kg_per_unit dimensional transformations."""

    def test_energy_factor_with_volume_activity(self):
        # 53.06 kg/MMBtu with natural gas in m3 (requires HHV)
        hhv = 1020.0
        kg_per_m3 = convert_factor_to_kg_per_unit(
            value=53.06,
            factor_unit="kg/MMBtu",
            activity_unit="m3",
            hhv=hhv,
            fuel_type="natural_gas",
        )
        # 1 m3 = 35.3146667 scf -> * 1020 Btu = 36020.96 Btu = 0.03602096 MMBtu
        # 0.03602096 MMBtu * 53.06 kg/MMBtu = 1.91127 kg/m3
        assert pytest.approx(kg_per_m3, rel=1e-4) == 1.91127

    def test_mass_factor_unit_scaling(self):
        # 2.5 tonne CO2 / tonne fuel -> in kg/tonne
        kg_per_t = convert_factor_to_kg_per_unit(
            value=2.5,
            factor_unit="tonne/tonne",
            activity_unit="tonne",
        )
        assert pytest.approx(kg_per_t, rel=1e-6) == 2500.0
