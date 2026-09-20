"""
Battery 1: Midstream & Upstream Process Equipment Test Suite.
=============================================================
Thoroughly verifies specialized upstream/midstream oil & gas equipment:
1. Mud Degassing (water, oil, synthetic, custom EF, zero volume).
2. Well Completion Flowback (metered_volume, rate_duration, gor_liquid, flaring split).
3. Liquids Unloading (API Eq 6-3 tubing geometry, P & T correction, events).
4. Vessel/Pipeline Blowdowns (API Eq 6-4, Z-factor compressibility, flaring split).
5. Storage Tank Flashing & Working/Breathing (GOR flashing, flaring control, EF throughput).
6. Pneumatic Devices (continuous bleed, intermittent actuation, EPA Table W-1 defaults).
"""
import pytest
import math
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.vented import (
    MudDegassingCalculator,
    CompletionFlowbackCalculator,
    LiquidsUnloadingCalculator,
    BlowdownCalculator,
    TankFlashingCalculator,
    PneumaticDeviceCalculator,
)
from calculations.constants import GWP_AR5
from validation.reference_model.vented_processes import (
    IndependentMudDegassing,
    IndependentCompletions,
    IndependentLiquidsUnloading,
    IndependentBlowdown,
    IndependentStorageTanks,
    IndependentPneumatics,
)


def _val(x):
    if isinstance(x, dict):
        return x.get("value", 0.0)
    return float(x or 0.0)


class TestMudDegassingBattery:
    """Verifies drilling mud degassing calculations against independent reference."""

    @pytest.mark.parametrize("mud_type, expected_ef", [
        ("water_based", 0.15),
        ("oil_based", 0.35),
        ("synthetic", 0.25),
        ("unknown_default", 0.25),
    ])
    def test_mud_types_standard_factors(self, mud_type, expected_ef):
        calc = MudDegassingCalculator()
        vol = 2500.0  # m3
        res = calc.calculate(vol, mud_type, {}, gwp_dict=GWP_AR5)
        ref = IndependentMudDegassing.calculate(vol, "m3", mud_type, gwp_standard="AR5")

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == ref["ch4"]
        assert pytest.approx(res["total_co2e"], rel=1e-5) == ref["co2e"]
        assert res["inputs"]["ef_ch4_used"] == expected_ef

    def test_mud_custom_ef_override(self):
        calc = MudDegassingCalculator()
        vol = 1200.0
        custom_ef = 0.42  # kg/m3
        res = calc.calculate(vol, "water_based", {}, ef_ch4=custom_ef, gwp_dict=GWP_AR5)
        ref = IndependentMudDegassing.calculate(vol, "m3", "water_based", custom_ef=custom_ef, gwp_standard="AR5")

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == ref["ch4"]
        assert res["inputs"]["ef_ch4_used"] == custom_ef


class TestWellCompletionFlowbackBattery:
    """Verifies completions and workovers flowback across all 3 methodologies."""

    def test_metered_volume_uncontrolled(self):
        calc = CompletionFlowbackCalculator()
        vol_m3 = 50000.0
        res = calc.calculate(flowback_volume=vol_m3, ch4_content=0.88, control_efficiency=0.0, gwp_dict=GWP_AR5)
        ref = IndependentCompletions.calculate(method="metered_volume", flowback_volume=vol_m3, ch4_content=0.88, control_efficiency=0.0, gwp_standard="AR5")

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-4) == ref["ch4"]
        assert pytest.approx(res["total_co2e"], rel=1e-4) == ref["co2e"]

    def test_rate_duration_with_flaring_partition(self):
        calc = CompletionFlowbackCalculator()
        rate_mscfd = 450.0   # Mscf/day
        hours = 72.0         # 3 days flowback
        ctrl_eff = 0.95      # 95% routed to flare
        res = calc.calculate(
            calculation_method="rate_duration",
            flowback_rate=rate_mscfd,
            flowback_duration_hours=hours,
            ch4_content=0.85,
            co2_content=0.03,
            control_efficiency=ctrl_eff,
            hhv=1050.0,
            gwp_dict=GWP_AR5,
        )
        ref = IndependentCompletions.calculate(
            method="rate_duration",
            flowback_rate=rate_mscfd,
            duration_hours=hours,
            ch4_content=0.85,
            co2_content=0.03,
            control_efficiency=ctrl_eff,
            hhv=1050.0,
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-4) == ref["ch4"]
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-4) == ref["co2"]
        assert pytest.approx(_val(res["results"]["n2o"]), rel=1e-4) == ref["n2o"]
        assert pytest.approx(res["total_co2e"], rel=1e-4) == ref["co2e"]

    def test_gor_liquid_method(self):
        calc = CompletionFlowbackCalculator()
        bbl = 3000.0
        gor = 850.0  # scf/bbl
        res = calc.calculate(
            calculation_method="gor_liquid",
            liquid_flowback_bbl=bbl,
            gas_oil_ratio=gor,
            ch4_content=0.80,
            control_efficiency=0.98,
            gwp_dict=GWP_AR5,
        )
        ref = IndependentCompletions.calculate(
            method="gor_liquid",
            liquid_bbl=bbl,
            gor=gor,
            ch4_content=0.80,
            control_efficiency=0.98,
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-4) == ref["ch4"]
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-4) == ref["co2"]


class TestLiquidsUnloadingBattery:
    """Verifies API Eq. 6-3 liquids unloading with tubing geometry and P/T correction."""

    def test_liquids_unloading_imperial_units(self):
        calc = LiquidsUnloadingCalculator()
        depth_ft = 8500.0
        diam_in = 2.875
        press_psig = 250.0
        temp_f = 120.0
        events = 15
        ch4 = 0.88

        res = calc.calculate(
            well_depth=depth_ft,
            diameter=diam_in,
            pressure=press_psig,
            ch4_content=ch4,
            events=events,
            uncertainties={},
            operating_temperature=temp_f,
            temp_unit="F",
            depth_unit="ft",
            diameter_unit="in",
            press_unit="psig",
            gwp_dict=GWP_AR5,
        )
        ref = IndependentLiquidsUnloading.calculate(
            well_depth=depth_ft,
            diameter=diam_in,
            pressure=press_psig,
            events=events,
            ch4_content=ch4,
            temp=temp_f,
            depth_unit="ft",
            diameter_unit="in",
            press_unit="psig",
            temp_unit="F",
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-4) == ref["ch4"]
        assert pytest.approx(res["total_co2e"], rel=1e-4) == ref["co2e"]

    def test_liquids_unloading_metric_units(self):
        calc = LiquidsUnloadingCalculator()
        depth_m = 2500.0
        diam_mm = 73.0
        press_bar = 20.0
        temp_c = 45.0
        events = 8

        res = calc.calculate(
            well_depth=depth_m,
            diameter=diam_mm,
            pressure=press_bar,
            ch4_content=0.90,
            events=events,
            uncertainties={},
            operating_temperature=temp_c,
            temp_unit="C",
            depth_unit="m",
            diameter_unit="mm",
            press_unit="bar",
            gwp_dict=GWP_AR5,
        )
        ref = IndependentLiquidsUnloading.calculate(
            well_depth=depth_m,
            diameter=diam_mm,
            pressure=press_bar,
            events=events,
            ch4_content=0.90,
            temp=temp_c,
            depth_unit="m",
            diameter_unit="mm",
            press_unit="bar",
            temp_unit="C",
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-3) == ref["ch4"]


class TestBlowdownBattery:
    """Verifies API Eq. 6-4 blowdown events with compressibility Z-factor."""

    def test_blowdown_with_z_factor_correction(self):
        calc = BlowdownCalculator()
        v_phys_m3 = 120.0
        p_psig = 900.0
        temp_f = 75.0
        z = 0.88  # Real gas compressibility factor
        events = 4
        ch4 = 0.86

        res = calc.calculate(
            blowdown_volume=v_phys_m3,
            pressure=p_psig,
            events=events,
            ch4_content=ch4,
            uncertainties={},
            operating_temperature=temp_f,
            temp_unit="F",
            press_unit="psig",
            z_factor=z,
            gwp_dict=GWP_AR5,
        )
        ref = IndependentBlowdown.calculate(
            blowdown_volume=v_phys_m3,
            pressure=p_psig,
            events=events,
            ch4_content=ch4,
            temp=temp_f,
            z_factor=z,
            press_unit="psig",
            temp_unit="F",
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-4) == ref["ch4"]
        assert pytest.approx(res["total_co2e"], rel=1e-4) == ref["co2e"]

    def test_blowdown_with_flaring_recovery(self):
        calc = BlowdownCalculator()
        v_phys_m3 = 50.0
        res = calc.calculate(
            blowdown_volume=v_phys_m3,
            pressure=500.0,
            events=2,
            ch4_content=0.85,
            uncertainties={},
            control_efficiency=0.98,
            hhv=1020.0,
            gwp_dict=GWP_AR5,
        )
        # 98% controlled should result in both CO2 and unburnt CH4 emissions
        assert _val(res["results"]["co2"]) > 0
        assert _val(res["results"]["ch4"]) > 0
        assert _val(res["results"]["n2o"]) > 0


class TestTankFlashingBattery:
    """Verifies storage tank flashing and working/breathing losses."""

    def test_flashing_gor_with_vapor_destruction(self):
        calc = TankFlashingCalculator()
        throughput_bbl = 25000.0
        gor = 42.0  # scf/bbl
        ctrl = 0.95  # 95% flare combustor
        res = calc.calculate(
            throughput=throughput_bbl,
            gas_oil_ratio=gor,
            ch4_content=0.75,
            control_efficiency=ctrl,
            uncertainties={},
            process_type="tank_flashing",
            gwp_dict=GWP_AR5,
        )
        ref = IndependentStorageTanks.calculate(
            throughput=throughput_bbl,
            gas_oil_ratio=gor,
            ch4_content=0.75,
            control_efficiency=ctrl,
            process_type="tank_flashing",
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-4) == ref["ch4"]
        assert pytest.approx(_val(res["results"]["co2"]), rel=1e-4) == ref["co2"]
        assert pytest.approx(res["total_co2e"], rel=1e-4) == ref["co2e"]

    def test_working_breathing_direct_ef(self):
        calc = TankFlashingCalculator()
        throughput_bbl = 10000.0
        ef_kg_bbl = 0.015  # kg CH4 / bbl
        res = calc.calculate(
            throughput=throughput_bbl,
            gas_oil_ratio=0,
            ch4_content=0,
            control_efficiency=0,
            uncertainties={},
            process_type="working_loss",
            ef_ch4=ef_kg_bbl,
            gwp_dict=GWP_AR5,
        )
        ref = IndependentStorageTanks.calculate(
            throughput=throughput_bbl,
            process_type="working_loss",
            ef_ch4=ef_kg_bbl,
            gwp_standard="AR5",
        )

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-5) == ref["ch4"]
        assert _val(res["results"]["ch4"]) == pytest.approx(0.15, rel=1e-5)  # 10000 * 0.015 / 1000


class TestPneumaticsBattery:
    """Verifies continuous bleed vs intermittent actuation pneumatic devices."""

    def test_continuous_bleed(self):
        calc = PneumaticDeviceCalculator()
        count = 12
        hours = 8760
        bleed_scfh = 6.0  # low bleed
        res = calc.calculate(count=count, hours=hours, bleed_rate=bleed_scfh, ch4_content=0.85, gwp_dict=GWP_AR5)
        ref = IndependentPneumatics.calculate(count=count, hours=hours, bleed_rate=bleed_scfh, ch4_content=0.85, gwp_standard="AR5")

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-4) == ref["ch4"]
        assert pytest.approx(res["total_co2e"], rel=1e-4) == ref["co2e"]

    def test_intermittent_actuation_epa_default(self):
        calc = PneumaticDeviceCalculator()
        count = 4
        actuations = 500  # 500 events per device
        # When bleed_rate is None or 0, EPA Subpart W default 13.5 scf/actuation is used
        res = calc.calculate(count=count, actuations=actuations, bleed_rate=None, ch4_content=0.88, gwp_dict=GWP_AR5)
        ref = IndependentPneumatics.calculate(count=count, actuations=actuations, bleed_rate=13.5, ch4_content=0.88, gwp_standard="AR5")

        assert pytest.approx(_val(res["results"]["ch4"]), rel=1e-4) == ref["ch4"]
