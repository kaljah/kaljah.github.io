"""
Comprehensive Golden Test Suite for API GHG Compendium 2021 Sections 6.4, 6.5, 6.6
Midstream Gathering & Boosting, Gas Processing, Transmission & Storage

Verifies:
- §6.4.2 Gathering Reciprocating Compressor Rod Packing (Exhibit 6-24)
- §6.4.3 Gathering Storage Tanks (Table 6-31)
- §6.4.6 Gathering Non-Routine Venting (Exhibit 6-27)
- §6.5.2 Processing Dehydration & Kimray Pump (Exhibit 6-28)
- §6.5.3 Processing Blanketed Tanks (Exhibit 6-29)
- §6.5.5 Processing Plant Blowdowns (Exhibit 6-30)
- §6.6.1 Transmission Reciprocating Compressor Rod Packing (Exhibit 6-31)
- §6.6.1 Centrifugal Compressor Seals (Exhibit 6-32)
- §6.6.4 Transmission Non-Routine & Pipeline Blowdowns (Exhibit 6-33)
"""

import pytest
from calculations.vented_midstream import (
    GatheringCompressorVentingCalculator,
    GatheringStorageTankCalculator,
    GatheringNonRoutineVentingCalculator,
    ProcessingDehydrationCalculator,
    ProcessingBlanketedTankCalculator,
    ProcessingNonRoutineCalculator,
    TransmissionCompressorCalculator,
    TransmissionNonRoutineCalculator,
)


def _val(res_item):
    if res_item is None:
        return 0.0
    if isinstance(res_item, dict):
        return res_item.get("value", 0.0)
    return float(res_item)


class TestGatheringAndBoosting:
    def test_exhibit_6_24_gathering_compressor(self):
        """
        API Exhibit 6-24:
        4 reciprocating compressors, 8,470 hrs pressurized, 70% CH4, 9% CO2.
        EPA GHGRP factor.
        Expected: ECH4 = 0.62 tonnes CH4/yr, ECO2 = 0.22 tonnes CO2/yr.
        """
        calc = GatheringCompressorVentingCalculator()
        res = calc.calculate(
            compressor_count=4,
            pressurized_hours=8470.0,
            source_standard="us_ghgrp",
            ch4_content=0.70,
            co2_content=0.09,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(0.62, abs=0.05)
        assert _val(res["results"]["co2"]) == pytest.approx(0.22, abs=0.05)

    def test_gathering_storage_tank_table_6_31(self):
        calc = GatheringStorageTankCalculator()
        res = calc.calculate(tank_count=3, hours=8760, component_type="average_tank")
        assert _val(res["results"]["ch4"]) > 0

    def test_exhibit_6_27_gathering_non_routine(self):
        """
        API Exhibit 6-27:
        6 PRVs, 1 compressor start, 6 miles dig-in.
        Site gas has 79 mole % CH4 and no CO2.
        """
        calc = GatheringNonRoutineVentingCalculator()
        res_prv = calc.calculate(activity="prv_releases", events_or_count=6, ch4_content=0.79)
        assert _val(res_prv["results"]["ch4"]) == pytest.approx(6 * 0.00065, abs=0.001)

        res_start = calc.calculate(activity="compressor_starts", events_or_count=1, ch4_content=0.79)
        assert _val(res_start["results"]["ch4"]) == pytest.approx(0.16, abs=0.02)

        res_dig = calc.calculate(activity="pipeline_dig_in", events_or_count=6, ch4_content=0.79)
        assert _val(res_dig["results"]["ch4"]) == pytest.approx(6 * 0.0128, abs=0.01)


class TestGasProcessing:
    def test_exhibit_6_28_processing_dehydration(self):
        """
        API Exhibit 6-28:
        25 MMscf/day, 365 days, 90% CH4, 5% CO2.
        Table 6-35 factor: 0.0023315 tonnes CH4/MMscf.
        Table 6-36 Kimray pump factor: 0.0034096 tonnes CH4/MMscf.
        Expected: Dehy ECH4 = 22.06 tonnes CH4/yr, Pump ECH4 = 32.26 tonnes CH4/yr, Pump ECO2 = 4.93 tonnes CO2/yr.
        Total ECH4 = 54.32 tonnes CH4/yr.
        """
        calc = ProcessingDehydrationCalculator()
        res = calc.calculate(
            gas_throughput_mmscfd=25.0,
            operating_days=365.0,
            has_gas_assisted_pump=True,
            ch4_content=0.90,
            co2_content=0.05,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(22.06 + 32.26, abs=0.5)
        assert _val(res["results"]["co2"]) == pytest.approx(4.93, abs=0.3)

    def test_exhibit_6_29_blanketed_tank(self):
        """
        API Exhibit 6-29:
        32,000 bbl/yr liquid displacement, vapor temp = 75°F.
        Gas has 82% CH4, 1% CO2.
        Expected: ECH4 = 2.68 tonnes CH4/yr, ECO2 = 0.09 tonnes CO2/yr.
        """
        calc = ProcessingBlanketedTankCalculator()
        res = calc.calculate(
            liquid_displacement_bbl=32000.0,
            vapor_temperature_f=75.0,
            ch4_content=0.82,
            co2_content=0.01,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(2.68, abs=0.1)
        assert _val(res["results"]["co2"]) == pytest.approx(0.09, abs=0.02)

    def test_exhibit_6_30_processing_blowdowns(self):
        """
        API Exhibit 6-30:
        20 * 10^6 m3/day treated, 365 days.
        Table 6-39 factor: 0.1244 tonnes CH4 / 10^6 m3.
        Expected: ECH4 = 908 tonnes CH4/yr.
        """
        calc = ProcessingNonRoutineCalculator()
        res = calc.calculate(gas_throughput_m3_day=20_000_000.0, operating_days=365.0)
        assert _val(res["results"]["ch4"]) == pytest.approx(908.0, abs=2.0)


class TestTransmissionAndStorage:
    def test_exhibit_6_31_transmission_recip_compressor(self):
        """
        API Exhibit 6-31:
        5 reciprocating compressors.
        7,970 hrs operating (263 scf gas/hr), 630 hrs standby (385 scf gas/hr).
        90% CH4, negligible CO2.
        Expected: Operating = 180.5 tonnes CH4, Standby = 20.9 tonnes CH4, Total = 201.4 tonnes CH4/yr.
        """
        calc = TransmissionCompressorCalculator()
        res = calc.calculate(
            compressor_type="reciprocating",
            compressor_count=5,
            operating_hours=7970.0,
            standby_pressurized_hours=630.0,
            ch4_content=0.90,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(201.4, abs=1.0)

    def test_exhibit_6_32_transmission_centrifugal_seals(self):
        """
        API Exhibit 6-32:
        3 centrifugal compressors with wet seals, 2 with dry seals.
        Average annual factor: wet = 163.7 t CH4/yr, dry = 51.1 t CH4/yr (at 95% CH4).
        Expected: Wet = 491.1 tonnes CH4, Dry = 102.2 tonnes CH4, Total = 593.3 tonnes CH4/yr.
        """
        calc = TransmissionCompressorCalculator()
        res = calc.calculate(
            compressor_type="centrifugal",
            wet_seal_count=3,
            dry_seal_count=2,
            ch4_content=0.95,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(593.3, abs=2.0)

    def test_exhibit_6_33_transmission_non_routine(self):
        """
        API Exhibit 6-33:
        2 transmission stations (Table 6-43: 54 tonnes CH4/station-yr) -> 108 tonnes CH4/yr.
        50 miles pipeline (Table 6-43: 0.6135 tonnes CH4/mile-yr) -> 30.675 ~= 31 tonnes CH4/yr.
        """
        calc = TransmissionNonRoutineCalculator()
        res_sta = calc.calculate(activity="transmission_station", count_or_miles=2)
        assert _val(res_sta["results"]["ch4"]) == pytest.approx(108.0, abs=0.5)

        res_pipe = calc.calculate(activity="pipeline_blowdown", count_or_miles=50)
        assert _val(res_pipe["results"]["ch4"]) == pytest.approx(30.675, abs=0.5)
