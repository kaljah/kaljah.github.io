"""
Unit and Golden Tests for API Compendium 2021 Sections 6.9 & 6.10:
CCUS, Geological Storage & Crude Oil Transport Losses
"""

import pytest
import math
from calculations.vented_ccus_transport import (
    CCUSVentingCalculator,
    CrudeTransportLossesCalculator,
)


def _val(item):
    if item is None:
        return 0.0
    if isinstance(item, dict):
        return item.get("value", 0.0)
    return float(item)


class TestCCUSCompendium:
    """Tests for API Compendium 2021 §6.9 CCUS & Geological Storage."""

    def setup_method(self):
        self.calc = CCUSVentingCalculator()

    def test_stripper_offgas_venting(self):
        """Stripper off-gas venting with capture efficiency."""
        # 10,000 tonnes inlet CO2, 90% capture efficiency -> 1,000 tonnes CO2 vented
        res = self.calc.calculate(
            activity="stripper_vent",
            inlet_co2_tonnes=10000.0,
            capture_efficiency=0.90,
            ch4_slip_tonnes=0.5,
        )
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-3) == 1000.0
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 0.5
        assert res["total_co2e"] > 1000.0

    def test_wellhead_blowdown_eq_6_27(self):
        """Supercritical CO2 storage wellhead blowdown (Equation 6-27)."""
        # Volume 1.5 m3, density 650 kg/m3, CO2 wt frac 0.985
        res = self.calc.calculate(
            activity="wellhead_blowdown",
            physical_volume_m3=1.5,
            events=4.0,
            co2_density_kg_m3=650.0,
            co2_weight_fraction=0.985,
        )
        # Mass = 4 * 1.5 * 650 * 0.985 * 0.001 = 3.8415 tonnes CO2
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-3) == 3.8415


class TestCrudeTransportCompendium:
    """Tests for API Compendium 2021 §6.10 Crude Oil Transport."""

    def setup_method(self):
        self.calc = CrudeTransportLossesCalculator()

    def test_exhibit_6_35_crude_loading(self):
        """
        EXHIBIT 6-35 Golden Test:
        - 100,000 bbl crude oil loaded into tank trucks
        - Splash loading dedicated service: 2.20 tonne TOC / 10^6 gal
        - CH4 wt% = 12%
        - Expected: E_TOC = 9.24 tonnes, E_CH4 = 1.11 tonnes CH4
        """
        res = self.calc.calculate(
            activity="loading",
            volume_loaded_bbl=100000.0,
            loading_service="splash_dedicated",
            ch4_weight_pct=12.0,
        )
        assert pytest.approx(res["inputs"]["total_toc_tonnes"], rel=1e-2) == 9.24
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-2) == 1.11

    def test_exhibit_6_36_marine_ballasting(self):
        """
        EXHIBIT 6-36 Golden Test:
        - Ballast water = 80,000 bbl = 3.36 * 10^6 gal
        - Typical condition factor = 0.488 tonne TOC / 10^6 gal
        - CH4 wt% = 12%
        - Expected: E_TOC = 1.64 tonnes, E_CH4 = 0.20 tonnes CH4
        """
        res = self.calc.calculate(
            activity="ballasting",
            ballast_water_bbl=80000.0,
            ballast_condition="typical",
            ch4_weight_pct=12.0,
        )
        assert pytest.approx(res["inputs"]["total_toc_tonnes"], rel=1e-2) == 1.64
        assert pytest.approx(_val(res["results"]["ch4"]), abs=0.01) == 0.20

    def test_exhibit_6_37_marine_transit(self):
        """
        EXHIBIT 6-37 Golden Test:
        - Cargo = 500,000 bbl = 21.0 * 10^6 gal
        - Transit duration = 14 days (2 weeks)
        - Factor = 0.57 tonne TOC / (week * 10^6 gal)
        - CH4 wt% = 12%
        - Expected: E_TOC = 23.94 tonnes, E_CH4 = 2.87 tonnes CH4
        """
        res = self.calc.calculate(
            activity="transit",
            volume_transported_bbl=500000.0,
            trip_duration_days=14.0,
            ch4_weight_pct=12.0,
        )
        assert pytest.approx(res["inputs"]["total_toc_tonnes"], rel=1e-2) == 23.94
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-2) == 2.87
