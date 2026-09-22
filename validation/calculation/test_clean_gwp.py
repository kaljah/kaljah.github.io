"""
CLEAN-SLATE VALIDATION: Global Warming Potential (GWP) Matrix
Validates IPCC AR4, AR5, AR6 (100-yr and 20-yr horizons) and dynamic resolution.
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from validation.reference_model import resolve_gwp
from calculations.constants import (
    GWP_AR4,
    GWP_AR5,
    GWP_AR6,
    GWP_STANDARDS,
    get_active_gwp,
)
from calculations.units import calculate_co2e


class TestCleanGWPStandards:
    """Independent validation of GWP constants and standards against IPCC authoritative reports."""

    def test_ar4_constants_ipcc_2007(self):
        """IPCC Fourth Assessment Report (2007) GWP values."""
        ref_100 = resolve_gwp("AR4", "100")
        assert GWP_AR4["CO2"] == ref_100["CO2"] == 1.0
        assert GWP_AR4["CH4"] == ref_100["CH4"] == 25.0
        assert GWP_AR4["N2O"] == ref_100["N2O"] == 298.0

        ref_20 = resolve_gwp("AR4", "20")
        assert GWP_AR4["CH4_20"] == ref_20["CH4"] == 72.0
        assert GWP_AR4["N2O_20"] == ref_20["N2O"] == 289.0

    def test_ar5_constants_ipcc_2013(self):
        """IPCC Fifth Assessment Report (2013, WG1 Table 8.7) GWP values."""
        ref_100 = resolve_gwp("AR5", "100")
        assert GWP_AR5["CO2"] == ref_100["CO2"] == 1.0
        assert GWP_AR5["CH4"] == ref_100["CH4"] == 28.0
        assert GWP_AR5["N2O"] == ref_100["N2O"] == 265.0

        ref_20 = resolve_gwp("AR5", "20")
        assert GWP_AR5["CH4_20"] == ref_20["CH4"] == 82.5
        assert GWP_AR5["N2O_20"] == ref_20["N2O"] == 268.0

    def test_ar6_constants_ipcc_2021(self):
        """IPCC Sixth Assessment Report (2021, WG1 Chapter 7) GWP values."""
        ref_100 = resolve_gwp("AR6", "100")
        assert GWP_AR6["CO2"] == ref_100["CO2"] == 1.0
        assert GWP_AR6["CH4"] == ref_100["CH4"] == 27.9
        assert GWP_AR6["N2O"] == ref_100["N2O"] == 273.0

        ref_20 = resolve_gwp("AR6", "20")
        assert GWP_AR6["CH4_20"] == ref_20["CH4"] == 82.5
        assert GWP_AR6["N2O_20"] == ref_20["N2O"] == 273.0


class TestCleanGWPResolutionAndCalculation:
    """Validates calculate_co2e with explicit GWP resolution and prevents standard cross-mixing."""

    def test_co2e_different_gwp_versions(self):
        ch4_tonnes = 10.0
        n2o_tonnes = 1.0
        co2_tonnes = 50.0

        # AR4: 50*1 + 10*25 + 1*298 = 598.0
        gwp_ar4 = get_active_gwp("AR4", horizon="100")
        co2e_ar4 = calculate_co2e(co2=co2_tonnes, ch4=ch4_tonnes, n2o=n2o_tonnes, gwp_dict=gwp_ar4)
        assert abs(co2e_ar4 - 598.0) < 1e-4

        # AR5: 50*1 + 10*28 + 1*265 = 595.0
        gwp_ar5 = get_active_gwp("AR5", horizon="100")
        co2e_ar5 = calculate_co2e(co2=co2_tonnes, ch4=ch4_tonnes, n2o=n2o_tonnes, gwp_dict=gwp_ar5)
        assert abs(co2e_ar5 - 595.0) < 1e-4

        # AR6: 50*1 + 10*27.9 + 1*273 = 50 + 279 + 273 = 602.0
        gwp_ar6 = get_active_gwp("AR6", horizon="100")
        co2e_ar6 = calculate_co2e(co2=co2_tonnes, ch4=ch4_tonnes, n2o=n2o_tonnes, gwp_dict=gwp_ar6)
        assert abs(co2e_ar6 - 602.0) < 1e-4

        # AR5 20-year horizon: 50*1 + 10*82.5 + 1*268 = 50 + 825 + 268 = 1143.0
        gwp_ar5_20 = get_active_gwp("AR5", horizon="20")
        co2e_ar5_20 = calculate_co2e(co2=co2_tonnes, ch4=ch4_tonnes, n2o=n2o_tonnes, gwp_dict=gwp_ar5_20)
        assert abs(co2e_ar5_20 - 1143.0) < 1e-4

    def test_prevent_mixing_standards(self):
        """Ensures requesting AR6 doesn't accidentally leak AR5 N2O or vice-versa."""
        res_ar6 = get_active_gwp("AR6")
        assert res_ar6["N2O"] == 273.0
        assert res_ar6["N2O"] != 265.0  # Must not be AR5

        res_ar5 = get_active_gwp("AR5")
        assert res_ar5["N2O"] == 265.0
        assert res_ar5["N2O"] != 273.0  # Must not be AR6
