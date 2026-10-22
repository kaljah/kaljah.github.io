"""
Comprehensive Golden Test Suite for API GHG Compendium 2021 Section 6.3
Oil & Natural Gas Production Vented & Process Emissions

NOTE (2026-10-22): the worked examples of this section (Exhibits 6-7, 6-9 to 6-18, 6-21) are now asserted against the
numbers the exhibits print, to their printed precision, in test_compendium_exhibits_ch6_exploration_production.py; the
loose copies that used to be here (e.g. +/-0.5 t on 24.2 t, a CO2 check that passed on either of two values, a CH4
check that only required > 0) were removed so one stricter test per exhibit remains. What is left here are the
non-exhibit equations and factor-table checks, plus Exhibits 6-22 and 6-25.

Verifies:
- §6.3.2 Workovers without Hydraulic Fracturing (Exhibit 6-7)
- §6.3.5 Casing Gas Vents: Heavy Oil Throughput (Exhibit 6-9) & Migration (Exhibit 6-10)
- §6.3.6 Natural Gas-Driven Pneumatic Controllers: Continuous (Exhibit 6-11) & Intermittent Monitoring (Exhibit 6-12)
- §6.3.7 Chemical Injection Pneumatic Pumps (Table 6-16 & Eq 6-15)
- §6.3.8 Gas Treatment: Dehydration Processing (Exhibit 6-13), Kimray Pump (Exhibit 6-14), Desiccant (Exhibit 6-15)
- §6.3.8.4 Acid Gas Removal: DEA Amine CH4 (Exhibit 6-16) & CO2 Material Balance (Exhibit 6-17)
- §6.3.9 Storage Tanks: VBE Flashing (Exhibit 6-18a), Standing (Exhibit 6-18b), EUB (Exhibit 6-18c), Produced Water (Exhibit 6-21)
- §6.3.10 CO2 EOR Operations: Injection Pump Blowdown (Exhibit 6-22)
- §6.3.11 Production Non-Routine Venting: PRV & Offshore ESD (Table 6-28)
- §6.4.6.1 Equipment Blowdown: Separator Depressurization (Exhibit 6-25) & Table 6-32 Defaults
"""

import pytest
from compendium_exhibits_support import REL_ENGINE, assert_printed
from calculations.vented_production import (
    WorkoverWithoutFracturingCalculator,
    CasingGasVentCalculator,
    PneumaticDeviceCalculator,
    PneumaticPumpCalculator,
    GasDehydrationCalculator,
    AcidGasRemovalCalculator,
    TankFlashingCalculator,
    CO2EORVentingCalculator,
    ProductionNonRoutineVentingCalculator,
    BlowdownCalculator,
)


def _val(res_item):
    if res_item is None:
        return 0.0
    if isinstance(res_item, dict):
        return res_item.get("value", 0.0)
    return float(res_item)


# ==============================================================================
# §6.3.2 Workovers without Hydraulic Fracturing (Exhibit 6-7)
# ==============================================================================
class TestWorkoverWithoutFracturing:

    def test_oil_well_workover(self):
        """Oil well workovers use Table 6-9 factor (122 scf gas/event, 96 scf CH4)."""
        calc = WorkoverWithoutFracturingCalculator()
        res = calc.calculate(workovers=5, well_type="oil_well", ch4_content=0.788)
        assert _val(res["results"]["ch4"]) == pytest.approx(5 * 0.0018, abs=0.001)

    def test_flared_workover_disposition(self):
        """Flaring converts 98% of CH4 to CO2 and generates N2O. 10 gas well workovers x 3,114 scf (Table 6-9) at 80 % CH4;
        an entered efficiency of 0.98 is the flare's efficiency for both the CH4 destruction and the carbon conversion."""
        calc = WorkoverWithoutFracturingCalculator()
        res = calc.calculate(workovers=10, well_type="gas_well", ch4_content=0.80, disposition="flared", control_efficiency=0.98)
        v_ch4 = 10 * 3114 * 0.028316846592 * 0.80
        assert _val(res["results"]["ch4"]) == pytest.approx(v_ch4 * (16.04 / 23.685) / 1000 * 0.02, rel=1e-3)  # 2% unburnt
        assert _val(res["results"]["co2"]) == pytest.approx(v_ch4 * (44.01 / 23.685) / 1000 * 0.98, rel=1e-3)  # 98% combusted
        # N2O: 31,140 scf x 1,020 Btu/scf = 31.76 MMBtu x 1.0e-7 t N2O/MMBtu
        assert _val(res["results"]["n2o"]) == pytest.approx(31140 * 1020 / 1e6 * 1.0e-7, rel=1e-6)


# ==============================================================================
# §6.3.5 Casing Gas Vents (Exhibits 6-9 & 6-10)
# ==============================================================================
class TestCasingGasVents:


    def test_table_6_13_well_basis(self):
        """Active well basis from Table 6-13 (1,310 scf gas/well-day) at the 81.6 mol % default CH4: 5 wells x 100 days."""
        calc = CasingGasVentCalculator()
        res = calc.calculate(method="well_count", well_status="active_wells", well_count=5, operating_days=100)
        assert _val(res["results"]["ch4"]) == pytest.approx(5 * 100 * 1310 * 0.816 / 379.3 * 16.04 / 2204.62, rel=1e-4)


# ==============================================================================
# §6.3.6 Natural Gas-Driven Pneumatic Controllers (Exhibits 6-11 & 6-12)
# ==============================================================================
class TestPneumaticControllers:


    def test_backwards_compatibility_continuous(self):
        """Existing test_vented.py signature: count=5, hours=8760, bleed_rate=10, ch4=0.80 -> ~6.727 tonnes."""
        calc = PneumaticDeviceCalculator()
        res = calc.calculate(count=5, hours=8760, bleed_rate=10, ch4_content=0.80)
        assert abs(_val(res["results"]["ch4"]) - 6.727) < 0.1

    def test_backwards_compatibility_intermittent_actuation(self):
        """Existing test_vented.py signature: count=2, actuations=500, bleed_rate=13.5, ch4=0.90."""
        calc = PneumaticDeviceCalculator()
        res = calc.calculate(count=2, actuations=500, bleed_rate=13.5, ch4_content=0.90)
        assert _val(res["results"]["ch4"]) > 0
        assert res["inputs"]["mode"] == "intermittent_actuation"


# ==============================================================================
# §6.3.7 Chemical Injection Pneumatic Pumps
# ==============================================================================
class TestPneumaticPumps:
    def test_piston_and_diaphragm_factors(self):
        calc = PneumaticPumpCalculator()
        res_piston = calc.calculate(pump_type="piston", pump_count=2, ch4_content=0.788)
        assert _val(res_piston["results"]["ch4"]) == pytest.approx(2 * 0.34, abs=0.05)

        res_dia = calc.calculate(pump_type="diaphragm", pump_count=1, ch4_content=0.788)
        assert _val(res_dia["results"]["ch4"]) == pytest.approx(3.12, abs=0.1)

    def test_engineering_model_eq_6_15(self):
        calc = PneumaticPumpCalculator()
        res = calc.calculate(
            method="engineering",
            pump_count=1,
            volume_liquid_pumped_ft3=500.0,
            pump_outlet_pressure_psig=150.0,
            gas_temperature_f=60.0,
            pump_inefficiency=0.30,
            ch4_content=0.85,
        )
        # Eq 6-15: V_G = (P_O + 14.7)/14.7 x T_A/(459.7 + T_G) x V_L x (1 + I), T_A = 520 R: 7,287 scf/yr
        v_g = (150.0 + 14.7) / 14.7 * 520.0 / (459.7 + 60.0) * 500.0 * 1.30
        # (the engine converts F to R with 459.67, the Compendium prints 459.7: 6e-5 apart)
        assert res["inputs"]["total_gas_scf"] == pytest.approx(v_g, rel=1e-4)
        assert _val(res["results"]["ch4"]) == pytest.approx(v_g * 0.028316846592 * 0.85 * (16.04 / 23.685) / 1000, rel=5e-4)


# ==============================================================================
# §6.3.9 Storage Tanks (Exhibits 6-18a, 6-18b, 6-18c, 6-21)
# ==============================================================================
class TestStorageTanks:




    def test_dump_valve_malfunction_eq_6_25(self):
        """Separator dump valve stuck open (Equation 6-25): E = CF x E_tank x T / 8,760, CF = 2.87 for crude service. The tank
        emission is Table 6-22's 0.193 kg CH4/bbl (large tanks, uncontrolled): 10,000 bbl -> 1.93 t/yr, 500 h stuck open."""
        calc = TankFlashingCalculator()
        res = calc.calculate(
            throughput=10000.0,
            method="dump_valve",
            liquid_type="crude",
            dump_valve_hours=500.0,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(2.87 * (10000.0 * 0.193e-3) * 500.0 / 8760.0, rel=1e-6)

    def test_backwards_compatibility_gor(self):
        """Existing test_vented.py signature: throughput=10000, GOR=50, control_efficiency=0.95. The efficiency is the SHARE of the
        gas sent to a flare (default flare 98 % destruction / 96.5 % carbon conversion); the other 5 % is vented."""
        calc = TankFlashingCalculator()
        res = calc.calculate(throughput=10000, gas_oil_ratio=50, control_efficiency=0.95, ch4_content=0.80)
        v_ch4 = 10000 * 50 * 0.028316846592 * 0.80
        assert _val(res["results"]["ch4"]) == pytest.approx(v_ch4 * (16.04 / 23.685) / 1000 * (0.05 + 0.95 * 0.02), rel=1e-9)
        assert _val(res["results"]["co2"]) == pytest.approx(v_ch4 * (44.01 / 23.685) / 1000 * 0.95 * 0.965, rel=1e-9)


# ==============================================================================
# §6.3.10 CO2 EOR Operations (Exhibit 6-22)
# ==============================================================================
class TestCO2EOROperations:
    def test_exhibit_6_22_injection_pump_blowdown(self):
        """
        API Exhibit 6-22:
        1 blowdown event, 36.4 m3, 98.5 wt% CO2, rho = 650 kg/m3.
        Expected: ECO2 = 23 tonnes CO2/yr.
        """
        calc = CO2EORVentingCalculator()
        res = calc.calculate(
            activity="pump_blowdown",
            events=1,
            physical_volume_m3=36.4,
            co2_density_kg_m3=650.0,
            co2_weight_fraction=0.985,
        )
        # exhibit: 36.4 m3 x 650 kg/m3 x 0.985 x 0.001 = 23.3, printed "23"
        assert_printed(_val(res["results"]["co2"]), "23", rel=0.0002, what="CO2")

    def test_dissolved_co2_retention_eq_6_26(self):
        calc = CO2EORVentingCalculator()
        res = calc.calculate(
            activity="dissolved_retention",
            oil_production_bbl=50000.0,
            co2_retained_tonnes_per_bbl=0.00025,
        )
        assert _val(res["results"]["co2"]) == pytest.approx(12.5, abs=0.1)


# ==============================================================================
# §6.3.11 Production Non-Routine Venting
# ==============================================================================
class TestProductionNonRoutine:
    def test_table_6_28_prv_and_esd(self):
        calc = ProductionNonRoutineVentingCalculator()
        res_prv = calc.calculate(source_type="prv", equipment_count=10, ch4_content=0.788)
        assert _val(res_prv["results"]["ch4"]) == pytest.approx(10 * 0.00065, abs=0.001)

        res_esd = calc.calculate(source_type="esd_platform", equipment_count=1, ch4_content=0.788)
        assert _val(res_esd["results"]["ch4"]) == pytest.approx(4.9276, abs=0.01)


# ==============================================================================
# §6.4.6.1 Equipment Blowdown (Exhibit 6-25 & Table 6-32)
# ==============================================================================
class TestBlowdowns:
    def test_exhibit_6_25_separator_blowdown(self):
        """
        API Exhibit 6-25:
        Separator: 4 ft diam, 10 ft long, liquid occupies 1/3 (gas = 83.8 ft3).
        100 psig, 80°F, z = 0.9864, 90% CH4, 1 event.
        Expected: ECH4 = 0.011 tonnes CH4.
        """
        calc = BlowdownCalculator()
        res = calc.calculate(
            diameter_ft=4.0,
            length_ft=10.0,
            liquid_volume_fraction=1.0 / 3.0,
            pressure=100.0,
            operating_temperature=80.0,
            temp_unit="F",
            press_unit="psig",
            z_factor=0.9864,
            ch4_content=0.90,
            events=1,
        )
        assert_printed(_val(res["results"]["ch4"]), "0.011", gas="ch4", rel=0.0002, what="CH4")

    def test_table_6_32_gathering_blowdowns(self):
        calc = BlowdownCalculator()
        res_comp = calc.calculate(activity_type="compressor", equipment_count=2, ch4_content=0.788)
        assert _val(res_comp["results"]["ch4"]) == pytest.approx(2 * 0.07239, abs=0.01)

    def test_backwards_compatibility_blowdown(self):
        """Existing test_vented.py signature: 1000 ft3 (28.32 m3), 100 psig, ch4=0.85 -> ~0.127 tonnes."""
        calc = BlowdownCalculator()
        res = calc.calculate(
            blowdown_volume=1000 * 0.0283168,
            pressure=100,
            events=1,
            ch4_content=0.85,
        )
        assert abs(_val(res["results"]["ch4"]) - 0.127) < 0.01
