"""
CLEAN-SLATE VALIDATION: Scope 1 Direct Emissions
Validates all implemented Scope 1 pathways against independent mathematical expectations.
ZERO reuse of legacy tests. Designed completely from zero.
"""

import pytest
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(BASE_DIR, "new", "server")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, SERVER_DIR)

from validation.reference_model import (
    ref_calculate_combustion,
    ref_calculate_flaring,
    ref_calculate_pneumatic_devices,
    ref_calculate_blowdown,
    ref_calculate_agr,
    ref_calculate_component_fugitives,
    resolve_gwp,
)
from calculations.combustion import CombustionCalculator, FlaringCalculator
from calculations.vented import PneumaticDeviceCalculator, BlowdownCalculator
from calculations.midstream import AGRCalculator
from calculations.fugitive import ComponentFugitiveCalculator
from calculations.dispatcher import CalculationDispatcher


class TestCleanScope1Combustion:
    """Independent validation of stationary combustion calculations."""

    def test_combustion_standard_natural_gas(self):
        calc = CombustionCalculator()
        qty = 10000.0  # m3
        ef_co2 = 1.93   # kg/m3
        ef_ch4 = 0.0001
        ef_n2o = 0.00003

        ref = ref_calculate_combustion(qty, ef_co2=ef_co2, ef_ch4=ef_ch4, ef_n2o=ef_n2o, fuel_unit="m3", ef_unit="kg/m3")

        res = calc.calculate(
            fuel_quantity=qty,
            ef_co2=ef_co2,
            ef_ch4=ef_ch4,
            ef_n2o=ef_n2o,
            uncertainties={},
            hhv=None,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="gases",
        )

        assert abs(res["results"]["co2"]["value"] - ref["co2"]) < 1e-4
        assert abs(res["results"]["ch4"]["value"] - ref["ch4"]) < 1e-5
        assert abs(res["results"]["n2o"]["value"] - ref["n2o"]) < 1e-5
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-3

    def test_combustion_thermodynamic_normalization(self):
        calc = CombustionCalculator()
        qty = 5000.0
        temp = 50.0
        press = 100.0  # psig
        z = 0.98

        ref = ref_calculate_combustion(
            qty, ef_co2=1.93, ef_ch4=0.0001, ef_n2o=0.00003,
            temp=temp, temp_unit="C", press=press, press_unit="psig", z_factor=z
        )

        res = calc.calculate(
            fuel_quantity=qty,
            ef_co2=1.93,
            ef_ch4=0.0001,
            ef_n2o=0.00003,
            uncertainties={},
            hhv=None,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="gases",
            operating_temperature=temp,
            temp_unit="C",
            operating_pressure=press,
            press_unit="psig",
            z_factor=z,
        )

        assert abs(res["results"]["co2"]["value"] - ref["co2"]) < 1e-2
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-2

    def test_combustion_tier3_gas_composition_carbon_balance(self):
        calc = CombustionCalculator()
        qty = 20000.0
        # When passing C1-C10 to combustion calculator, C4 accounts for butanes (iC4+nC4), C5 for pentanes
        comps = {"c1": 0.88, "c2": 0.06, "c3": 0.03, "c4": 0.02, "co2_comp": 0.01}
        eff = 0.995

        ref = ref_calculate_combustion(
            qty, fuel_unit="m3", combustion_efficiency=eff, gas_composition=comps
        )

        res = calc.calculate(
            fuel_quantity=qty,
            ef_co2=0.0,
            ef_ch4=0.0,
            ef_n2o=0.0,
            uncertainties={},
            hhv=None,
            ef_unit="kg/m3",
            fuel_unit="m3",
            fuel_type="gases",
            combustion_efficiency=eff,
            **comps,
        )

        assert abs(res["results"]["co2"]["value"] - ref["co2"]) < 1e-2
        assert abs(res["results"]["ch4"]["value"] - ref["ch4"]) < 1e-3
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-2

    def test_combustion_zero_quantity_boundary(self):
        calc = CombustionCalculator()
        res = calc.calculate(
            fuel_quantity=0.0, ef_co2=1.93, ef_ch4=0.0001, ef_n2o=0.00003,
            uncertainties={}, hhv=None, ef_unit="kg/m3", fuel_unit="m3", fuel_type="gases"
        )
        assert res["results"]["co2"]["value"] == 0.0
        assert res["results"]["ch4"]["value"] == 0.0
        assert res["total_co2e"] == 0.0


class TestCleanScope1Flaring:
    """Independent validation of dual-efficiency flaring calculations."""

    def test_flaring_elevated_dual_efficiency(self):
        calc = FlaringCalculator()
        vol = 50000.0  # m3
        ch4_frac = 0.88
        comps = {"co2_comp": 0.02}

        ref = ref_calculate_flaring(vol, ch4_fraction=ch4_frac, flare_type="elevated", gas_composition=comps)

        res = calc.calculate(
            gas_volume=vol,
            ch4_fraction=ch4_frac,
            flare_type="elevated",
            uncertainties={},
            fuel_unit="m3",
            **comps,
        )

        assert abs(res["results"]["co2"]["value"] - ref["co2"]) < 1e-2
        assert abs(res["results"]["ch4"]["value"] - ref["ch4"]) < 1e-2
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-1

    def test_flaring_enclosed_high_efficiency(self):
        calc = FlaringCalculator()
        vol = 25000.0
        ch4_frac = 0.92

        ref = ref_calculate_flaring(vol, ch4_fraction=ch4_frac, flare_type="enclosed")

        res = calc.calculate(
            gas_volume=vol,
            ch4_fraction=ch4_frac,
            flare_type="enclosed",
            uncertainties={},
            fuel_unit="m3",
        )

        assert abs(res["results"]["co2"]["value"] - ref["co2"]) < 1e-2
        assert abs(res["results"]["ch4"]["value"] - ref["ch4"]) < 1e-2
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-1


class TestCleanScope1VentingAndMidstream:
    """Independent validation of venting, blowdown, AGR, and fugitives."""

    def test_pneumatic_devices_intermittent(self):
        calc = PneumaticDeviceCalculator()
        count = 10
        hrs = 8760
        ch4_f = 0.90
        bleed_rate = 13.5

        ref = ref_calculate_pneumatic_devices(count, hours=hrs, device_type="intermittent", vent_rate_scf_hr=bleed_rate, ch4_fraction=ch4_f)

        res = calc.calculate(
            count=count,
            hours=hrs,
            bleed_rate=bleed_rate,
            ch4_content=ch4_f,
            uncertainties={},
        )

        assert abs(res["results"]["ch4"]["value"] - ref["ch4"]) < 1e-2
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-1

    def test_blowdown_depressuring(self):
        calc = BlowdownCalculator()
        vol_m3 = 50.0
        p_init = 600.0
        events = 2
        ch4_f = 0.88

        ref = ref_calculate_blowdown(vol_m3, initial_press=p_init, final_press=0.0, events=events, ch4_fraction=ch4_f, use_absolute_inventory=True)

        res = calc.calculate(
            blowdown_volume=vol_m3,
            pressure=p_init,
            events=events,
            ch4_content=ch4_f,
            press_unit="psig",
            uncertainties={},
        )

        assert abs(res["results"]["ch4"]["value"] - ref["ch4"]) < 1e-2
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-1

    def test_acid_gas_removal_sweetening(self):
        calc = AGRCalculator()
        feed_vol_mmscf = 100.0
        inlet = 0.04
        outlet = 0.0001
        ch4_in = 0.85

        res = calc.calculate(
            throughput=feed_vol_mmscf,
            co2_in=inlet,
            co2_out=outlet,
            ch4_in=ch4_in,
            acid_gas_control_eff=0.0,
            uncertainties={},
        )

        feed_vol_m3 = feed_vol_mmscf * 28316.846592
        ref = ref_calculate_agr(feed_vol_m3, co2_inlet_fraction=inlet, co2_outlet_fraction=outlet, ch4_inlet_fraction=ch4_in)

        assert abs(res["results"]["co2"]["value"] - ref["co2"]) < 1e-1
        assert abs(res["results"]["ch4"]["value"] - ref["ch4"]) < 1e-2
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-1

    def test_component_fugitives_valve_leaks(self):
        calc = ComponentFugitiveCalculator()
        valves = 150
        hrs = 8760
        ch4_f = 0.90
        ef_valve = 0.0045

        ref = ref_calculate_component_fugitives(valves, hours=hrs, component_type="valve", ef_kg_hr=ef_valve, ch4_fraction=ch4_f)

        res = calc.calculate(
            component_counts={"valves": {"count": valves, "ef": ef_valve, "unit": "kg/hr"}},
            ch4_content=ch4_f,
            uncertainties={},
        )

        assert abs(res["results"]["ch4"]["value"] - ref["ch4"]) < 1e-2
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-1


class TestCleanScope1DispatcherRouting:
    """Independent verification of the central calculation dispatcher across Scope 1."""

    def test_dispatcher_combustion_routing(self):
        dispatcher = CalculationDispatcher()
        inputs = {"quantity": 10000.0, "unit": "m3", "fuel_type": "Natural Gas"}
        factors = {"co2": 1.93, "ch4": 0.0001, "n2o": 0.00003, "unit": "kg/m3"}

        res = dispatcher.dispatch(
            process_type="stationary_combustion",
            inputs=inputs,
            emission_factors=factors,
            uncertainties={},
        )

        ref = ref_calculate_combustion(10000.0, ef_co2=1.93, ef_ch4=0.0001, ef_n2o=0.00003)
        assert abs(res["results"]["co2"]["value"] - ref["co2"]) < 1e-3
        assert abs(res["total_co2e"] - ref["co2e"]) < 1e-3
