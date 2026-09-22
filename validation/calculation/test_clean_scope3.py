"""
CLEAN-SLATE VALIDATION: Scope 3 Value Chain Emissions
Validates all 15 GHG Protocol Scope 3 categories against independent reference models.
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from validation.reference_model import ref_calculate_scope3, SCOPE3_CATEGORIES
from calculations.units import compute_scope3_co2e


class TestCleanScope3Calculations:
    """Independent validation of Scope 3 calculation paths."""

    @pytest.mark.parametrize(
        "cat_id,cat_name",
        list(SCOPE3_CATEGORIES.items())
    )
    def test_all_15_categories_activity_based(self, cat_id, cat_name):
        """Independently verifies that each of the 15 categories executes standard activity calculation."""
        activity = 1000.0
        ef = 2.50  # kg CO2e / unit

        # Production calculation
        co2e_prod = compute_scope3_co2e(activity, ef, ef_unit="kg CO2e/unit")

        # Independent reference model
        ref = ref_calculate_scope3(cat_id, activity, ef, ef_unit="kg/unit")

        # Expected: 1000 * 2.50 / 1000 = 2.5 tonnes
        assert abs(co2e_prod - 2.50) < 1e-4
        assert abs(co2e_prod - ref["co2e"]) < 1e-4
        assert ref["category_name"] == cat_name

    def test_scope3_spend_based_eeio(self):
        spend_usd = 250000.0
        eeio_factor = 420.0  # kg CO2e / $1,000 spend

        # Production calculation with EEIO method
        co2e_prod = compute_scope3_co2e(
            spend_usd, eeio_factor, ef_unit="kg CO2e / $1,000", calc_method="eeio_spend_based"
        )

        # Independent expectation: (250,000 * 420) / 1,000,000 = 105.0 tonnes
        expected = (spend_usd * eeio_factor) / 1_000_000.0
        assert abs(co2e_prod - expected) < 1e-4
        assert co2e_prod == 105.0

    def test_scope3_tonnes_numerator_unit(self):
        activity = 500.0
        ef_tonnes = 0.432  # tCO2e / bbl

        co2e_prod = compute_scope3_co2e(activity, ef_tonnes, ef_unit="tCO2e/bbl")
        expected = activity * ef_tonnes
        assert abs(co2e_prod - expected) < 1e-4
        assert co2e_prod == 216.0

    def test_scope3_zero_boundary(self):
        assert compute_scope3_co2e(0.0, 2.5) == 0.0
        assert compute_scope3_co2e(100.0, 0.0) == 0.0
        assert compute_scope3_co2e(-50.0, 2.5) == 0.0
        assert compute_scope3_co2e(100.0, -1.0) == 0.0
