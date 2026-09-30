"""
Unit and Golden Tests for API Compendium 2021 Sections 6.7 & 6.8:
LNG Operations & Natural Gas Distribution Vented Emissions
"""

import pytest
import math
from calculations.vented_lng_distribution import (
    LNGVentingCalculator,
    DistributionPneumaticsCalculator,
    DistributionNonRoutineCalculator,
)


def _val(item):
    if item is None:
        return 0.0
    if isinstance(item, dict):
        return item.get("value", 0.0)
    return float(item)


class TestLNGVentingCompendium:
    """Tests for API Compendium 2021 §6.7 LNG Operations."""

    def setup_method(self):
        self.calc = LNGVentingCalculator()

    def test_pipeline_transfer_foam_insulation(self):
        """Table 6-44: Transfer line boil-off gas with foam insulation (0.0012% per km)."""
        res = self.calc.calculate(
            activity="loading_transfer",
            transfer_volume_m3=100000.0,
            pipe_length_km=2.0,
            insulation_type="foam",
            ch4_content=0.98,
        )
        assert _val(res["results"]["ch4"]) > 0.0
        assert res["total_co2e"] > 0.0
        assert res["metadata"]["tables"] == "Table 6-44"

    def test_pipeline_transfer_vacuum_insulation(self):
        """Table 6-44: Vacuum insulation has lower boil-off loss (0.00012% per km)."""
        res_foam = self.calc.calculate(
            activity="loading_transfer",
            transfer_volume_m3=100000.0,
            pipe_length_km=1.0,
            insulation_type="foam",
        )
        res_vac = self.calc.calculate(
            activity="loading_transfer",
            transfer_volume_m3=100000.0,
            pipe_length_km=1.0,
            insulation_type="vacuum",
        )
        assert pytest.approx(_val(res_vac["results"]["ch4"]) * 10.0, rel=1e-3) == _val(res_foam["results"]["ch4"])

    def test_direct_bog_venting_and_flaring(self):
        """Direct boil-off venting with flaring control efficiency."""
        res_vented = self.calc.calculate(
            activity="direct_bog_vent",
            vented_gas_scf=1_000_000.0,
            ch4_content=0.95,
            disposition="vented",
        )
        res_flared = self.calc.calculate(
            activity="direct_bog_vent",
            vented_gas_scf=1_000_000.0,
            ch4_content=0.95,
            disposition="flared",
            control_efficiency=0.98,
        )
        assert pytest.approx(_val(res_flared["results"]["ch4"]), rel=1e-2) == _val(res_vented["results"]["ch4"]) * 0.02
        assert _val(res_flared["results"]["co2"]) > 0.0

    def test_recovered_bog_zero_emissions(self):
        """Recovered BOG has zero atmospheric venting."""
        res = self.calc.calculate(
            activity="direct_bog_vent",
            vented_gas_scf=500_000.0,
            disposition="recovered",
        )
        assert _val(res["results"]["ch4"]) == 0.0
        assert res["total_co2e"] == 0.0


class TestDistributionPneumaticsCompendium:
    """Tests for API Compendium 2021 §6.8.1 Natural Gas Distribution Pneumatics."""

    def setup_method(self):
        self.calc = DistributionPneumaticsCalculator()

    def test_isolation_valves_table_6_45(self):
        """Table 6-45: Pneumatic isolation valves (0.366 tonnes CH4/yr)."""
        res = self.calc.calculate(
            controller_type="isolation_valves",
            controller_count=10.0,
        )
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 3.66

    def test_control_loops_table_6_45(self):
        """Table 6-45: Control loops (3.465 tonnes CH4/yr)."""
        res = self.calc.calculate(
            controller_type="control_loops",
            controller_count=5.0,
        )
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 17.325

    def test_industrial_meter_regulator(self):
        """Table 6-45: Industrial meter regulator venting (3.847 tonnes CH4/yr)."""
        res = self.calc.calculate(
            controller_type="industrial_meter_regulator",
            controller_count=2.0,
        )
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 7.694


class TestDistributionNonRoutineCompendium:
    """Tests for API Compendium 2021 §6.8.2 & Exhibit 6-34 Distribution Non-Routine Releases."""

    def setup_method(self):
        self.calc = DistributionNonRoutineCalculator()

    def test_mr_station_blowdown_table_6_46(self):
        """Table 6-46: M&R Station blowdown (0.002895 tonnes CH4/station-yr)."""
        res = self.calc.calculate(
            activity="mr_station_blowdown",
            count_or_miles=10.0,
        )
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 0.02895

    def test_odorizer_and_sampling_table_6_46(self):
        """Table 6-46: Odorizer & gas sampling (0.02275 tonnes CH4/station-yr)."""
        res = self.calc.calculate(
            activity="odorizer_sampling",
            count_or_miles=4.0,
        )
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 0.091

    def test_pipeline_blowdown_and_dig_in_table_6_46(self):
        """Table 6-46: Pipeline blowdowns (0.03220 t/mi) and dig-ins (0.03040 t/mi)."""
        res_bd = self.calc.calculate(
            activity="pipeline_blowdown",
            count_or_miles=100.0,
        )
        res_di = self.calc.calculate(
            activity="pipeline_dig_in",
            count_or_miles=100.0,
        )
        assert pytest.approx(_val(res_bd["results"]["ch4"]), rel=1e-3) == 3.220
        assert pytest.approx(_val(res_di["results"]["ch4"]), rel=1e-3) == 3.040

    def test_prv_releases_table_6_46(self):
        """Table 6-46: PRV releases (9.591e-4 tonnes CH4/mi)."""
        res = self.calc.calculate(
            activity="prv_releases",
            count_or_miles=50.0,
        )
        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == 0.047955
