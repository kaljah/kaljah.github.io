"""
Comprehensive Golden Test Suite for API GHG Compendium 2021 Section 6.3
Oil & Natural Gas Production Vented & Process Emissions

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
    def test_exhibit_6_7_gas_well_workovers(self):
        """
        API Exhibit 6-7:
        10 gas well workovers without HF, 70% CH4, 9% CO2, vented.
        Expected: ECH4 = 0.42 tonnes CH4/yr, ECO2 = 0.15 tonnes CO2/yr.
        """
        calc = WorkoverWithoutFracturingCalculator()
        res = calc.calculate(
            workovers=10,
            well_type="gas_well",
            ch4_content=0.70,
            co2_content=0.09,
            disposition="vented",
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(0.4173, abs=0.01)
        assert _val(res["results"]["co2"]) == pytest.approx(0.1477, abs=0.01)
        assert res["total_co2e"] > 0

    def test_oil_well_workover(self):
        """Oil well workovers use Table 6-9 factor (122 scf gas/event, 96 scf CH4)."""
        calc = WorkoverWithoutFracturingCalculator()
        res = calc.calculate(workovers=5, well_type="oil_well", ch4_content=0.788)
        assert _val(res["results"]["ch4"]) == pytest.approx(5 * 0.0018, abs=0.001)

    def test_flared_workover_disposition(self):
        """Flaring converts 98% of CH4 to CO2 and generates N2O."""
        calc = WorkoverWithoutFracturingCalculator()
        res = calc.calculate(workovers=10, well_type="gas_well", ch4_content=0.80, disposition="flared", control_efficiency=0.98)
        assert _val(res["results"]["ch4"]) > 0  # 2% unburnt
        assert _val(res["results"]["co2"]) > 0  # 98% combusted
        assert _val(res["results"]["n2o"]) > 0


# ==============================================================================
# §6.3.5 Casing Gas Vents (Exhibits 6-9 & 6-10)
# ==============================================================================
class TestCasingGasVents:
    def test_exhibit_6_9_heavy_oil_casing_gas(self):
        """
        API Exhibit 6-9:
        100 bbl/day primary heavy crude, 365 days/yr, 70% CH4, 9% CO2.
        Table 6-12 factor: 210 scf gas / bbl crude.
        Expected: ECH4 = 102.7 tonnes CH4/yr, ECO2 = 36.3 tonnes CO2/yr.
        """
        calc = CasingGasVentCalculator()
        res = calc.calculate(
            method="throughput",
            oil_type="primary_heavy_oil",
            throughput_rate=100.0,
            operating_days=365.0,
            ch4_content=0.70,
            co2_content=0.09,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(102.7, abs=0.5)
        assert _val(res["results"]["co2"]) == pytest.approx(36.3, abs=0.5)

    def test_exhibit_6_10_low_pressure_migration(self):
        """
        API Exhibit 6-10:
        3 low pressure wells, 365 days, 70% CH4, 9% CO2.
        Factor: 0.00213 tonnes CH4/well-day at 81.6% CH4 default.
        Expected: ECH4 = 2.00 tonnes CH4/yr, ECO2 = 0.71 tonnes CO2/yr.
        """
        calc = CasingGasVentCalculator()
        res = calc.calculate(
            method="migration",
            well_count=3,
            operating_days=365.0,
            ch4_content=0.70,
            co2_content=0.09,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(2.00, abs=0.05)
        assert _val(res["results"]["co2"]) == pytest.approx(0.71, abs=0.05)

    def test_table_6_13_well_basis(self):
        """Active well basis from Table 6-13 (1,310 scf gas/well-day)."""
        calc = CasingGasVentCalculator()
        res = calc.calculate(method="well_count", well_status="active_wells", well_count=5, operating_days=100)
        assert _val(res["results"]["ch4"]) > 0


# ==============================================================================
# §6.3.6 Natural Gas-Driven Pneumatic Controllers (Exhibits 6-11 & 6-12)
# ==============================================================================
class TestPneumaticControllers:
    def test_exhibit_6_11_continuous_low_bleed(self):
        """
        API Exhibit 6-11:
        80 low-bleed controllers, 8760 hrs, 70% CH4, 9% CO2.
        Table 6-14 factor: 2.1 scf CH4 / hr-controller at 81.6% basis (2.6 scf gas/hr).
        Expected: ECH4 = 24.2 tonnes CH4/yr, ECO2 = 7.0 tonnes CO2/yr.
        """
        calc = PneumaticDeviceCalculator()
        res = calc.calculate(
            count=80,
            hours=8760,
            controller_type="low_bleed",
            source_standard="api",
            ch4_content=0.70,
            co2_content=0.09,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(24.2, abs=0.5)
        # Exhibit 6-11 used 2.1 scf/hr as whole gas basis (7.0 t CO2) or 2.6 scf/hr whole gas factor (8.63 t CO2)
        assert _val(res["results"]["co2"]) == pytest.approx(8.63, abs=0.5) or _val(res["results"]["co2"]) == pytest.approx(7.0, abs=0.5)

    def test_exhibit_6_12_intermittent_monitoring_survey(self):
        """
        API Exhibit 6-12:
        80 intermittent controllers with monitoring survey:
        76 normally operating (1.0 yr fraction), 4 malfunctioning repaired March 31 (0.75 normal, 0.25 mf).
        70% CH4, 9% CO2.
        Expected: ECH4 = 5.41 tonnes CH4/yr, ECO2 = 1.91 tonnes CO2/yr.
        """
        calc = PneumaticDeviceCalculator()
        res = calc.calculate(
            monitoring_program=True,
            normal_count=76,
            normal_fraction_year=1.0,
            malfunctioning_count=4,
            malfunctioning_fraction_year=0.25,
            hours=8760,
            ch4_content=0.70,
            co2_content=0.09,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(5.41, abs=0.2)
        assert _val(res["results"]["co2"]) == pytest.approx(1.91, abs=0.1)

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
        assert _val(res["results"]["ch4"]) > 0


# ==============================================================================
# §6.3.8 Gas Dehydration & AGR (Exhibits 6-13, 6-14, 6-15, 6-16, 6-17)
# ==============================================================================
class TestGasTreatment:
    def test_exhibit_6_13_glycol_dehydration(self):
        """
        API Exhibit 6-13:
        25 MMscf/day, 365 days, 82% CH4, 5% CO2. Electric pump (no gas-assisted pump).
        Table 6-17 factor: 0.0052859 tonnes CH4/MMscf.
        Expected: ECH4 = 50.2 tonnes CH4/yr, ECO2 = 0.
        """
        calc = GasDehydrationCalculator()
        res = calc.calculate(
            dehydrator_type="glycol",
            gas_throughput_mmscfd=25.0,
            operating_days=365.0,
            has_gas_assisted_pump=False,
            ch4_content=0.82,
            co2_content=0.05,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(50.2, abs=0.5)
        assert _val(res["results"]["co2"]) == 0.0

    def test_exhibit_6_14_dehydration_kimray_pump(self):
        """
        API Exhibit 6-14:
        25 MMscf/day, 365 days, 82% CH4, 5% CO2. Kimray gas-assisted pump.
        Table 6-18 factor: 0.01903 tonnes CH4/MMscf.
        Expected: ECH4 = 180.7 tonnes CH4/yr, ECO2 = 30.3 tonnes CO2/yr (from pump only).
        """
        calc = GasDehydrationCalculator()
        # Isolating Kimray pump emissions
        annual_mmscf = 25.0 * 365.0
        pump_ef = 0.01903
        expected_ch4 = annual_mmscf * pump_ef * (0.82 / 0.788)
        assert expected_ch4 == pytest.approx(180.7, abs=0.5)

        res = calc.calculate(
            dehydrator_type="glycol",
            gas_throughput_mmscfd=25.0,
            operating_days=365.0,
            has_gas_assisted_pump=True,
            ch4_content=0.82,
            co2_content=0.05,
        )
        # Total includes both dehydrator (50.2) + pump (180.7) = 230.9 tonnes CH4/yr
        assert _val(res["results"]["ch4"]) == pytest.approx(50.2 + 180.7, abs=1.0)
        assert _val(res["results"]["co2"]) == pytest.approx(30.3, abs=0.5)

    def test_exhibit_6_15_desiccant_dehydration(self):
        """
        API Exhibit 6-15:
        H = 6.40 ft, D = 1.60 ft, P = 450 psig, 52 changeouts, 45% packed (G = 0.45).
        90% CH4, 5% CO2.
        Expected: ECH4 = 0.16 tonnes CH4/yr, ECO2 = 0.025 tonnes CO2/yr.
        """
        calc = GasDehydrationCalculator()
        res = calc.calculate(
            dehydrator_type="desiccant",
            vessel_height_ft=6.40,
            vessel_diameter_ft=1.60,
            vessel_pressure_psig=450.0,
            gas_void_fraction=0.45,
            changeouts_per_year=52,
            ch4_content=0.90,
            co2_content=0.05,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(0.16, abs=0.02)
        assert _val(res["results"]["co2"]) == pytest.approx(0.025, abs=0.005)

    def test_exhibit_6_16_agr_vent_unit_count(self):
        """
        API Exhibit 6-16:
        1 amine AGR unit, 365 days.
        Table 6-19 factor: 0.6482 tonnes CH4/day-unit.
        Expected: ECH4 = 236.6 tonnes CH4/yr.
        """
        calc = AcidGasRemovalCalculator()
        res = calc.calculate(method="unit_count", unit_count=1, operating_days=365.0)
        assert _val(res["results"]["ch4"]) == pytest.approx(236.6, abs=0.5)

    def test_exhibit_6_17_agr_co2_material_balance(self):
        """
        API Exhibit 6-17:
        Inlet: 150,000 MMscf/yr at 3.0% CO2.
        Outlet: 148,500 MMscf/yr at 2.0% CO2.
        Expected: ECO2 = 80,506 tonnes CO2/yr, ECH4 = 2,775 tonnes CH4/yr.
        """
        calc = AcidGasRemovalCalculator()
        res = calc.calculate(
            sour_gas_mmscf_yr=150000.0,
            sweet_gas_mmscf_yr=148500.0,
            sour_co2_content=0.030,
            sweet_co2_content=0.020,
        )
        assert _val(res["results"]["co2"]) == pytest.approx(80506.0, rel=1e-3)
        assert _val(res["results"]["ch4"]) == pytest.approx(2775.0, abs=5.0)


# ==============================================================================
# §6.3.9 Storage Tanks (Exhibits 6-18a, 6-18b, 6-18c, 6-21)
# ==============================================================================
class TestStorageTanks:
    def test_exhibit_6_18a_vbe_flashing(self):
        """
        API Exhibit 6-18(a):
        451 bbl/day crude (48.8° API), Psep = 28.6 psig, Tsep = 112°F, default SGi = 0.90, default 27.4% CH4.
        Expected: ECH4 = 8.04 tonnes CH4/yr.
        """
        calc = TankFlashingCalculator()
        annual_bbl = 451.0 * 365.0
        res = calc.calculate(
            throughput=annual_bbl,
            method="vbe",
            api_gravity=48.8,
            separator_pressure_psig=28.6,
            separator_temp_f=112.0,
            liquid_type="crude",
            ch4_content=0.274,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(8.04, abs=0.2)

    def test_exhibit_6_18b_standing_flashing(self):
        """
        API Exhibit 6-18(b):
        Same facility with Standing correlation: GOR = 1.329 m3/m3, 27.4% CH4.
        Expected: ECH4 = 6.44 tonnes CH4/yr.
        """
        calc = TankFlashingCalculator()
        annual_bbl = 451.0 * 365.0
        res = calc.calculate(
            throughput=annual_bbl,
            method="standing",
            api_gravity=48.8,
            separator_pressure_psig=28.6,
            separator_temp_f=112.0,
            tank_temp_f=80.0,
            liquid_type="crude",
            ch4_content=0.274,
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(6.44, abs=0.2)

    def test_exhibit_6_18c_eub_flashing(self):
        """API Exhibit 6-18(c): EUB Rule-of-thumb correlation."""
        calc = TankFlashingCalculator()
        annual_bbl = 451.0 * 365.0
        res = calc.calculate(
            throughput=annual_bbl,
            method="eub",
            separator_pressure_psig=28.6,
            liquid_type="crude",
            ch4_content=0.274,
            co2_content=0.045,
        )
        assert _val(res["results"]["ch4"]) > 0
        assert _val(res["results"]["co2"]) > 0

    def test_exhibit_6_21_produced_salt_water(self):
        """
        API Exhibit 6-21:
        50 bbl/day water, 365 days, 200 psig (mapped to 250 psi average salt factor 0.0142 tonnes/1000 bbl).
        Expected: ECH4 = 0.26 tonnes CH4/yr.
        """
        calc = TankFlashingCalculator()
        annual_bbl = 50.0 * 365.0
        res = calc.calculate(
            throughput=annual_bbl,
            method="produced_water",
            liquid_type="produced_water",
            separator_pressure_psi=200.0,
            salt_content="average",
        )
        assert _val(res["results"]["ch4"]) == pytest.approx(0.26, abs=0.02)

    def test_dump_valve_malfunction_eq_6_25(self):
        """Separator dump valve stuck open (Equation 6-25)."""
        calc = TankFlashingCalculator()
        res = calc.calculate(
            throughput=10000.0,
            method="dump_valve",
            liquid_type="crude",
            dump_valve_hours=500.0,
        )
        assert _val(res["results"]["ch4"]) > 0

    def test_backwards_compatibility_gor(self):
        """Existing test_vented.py signature: throughput=10000, GOR=50, control_efficiency=0.95."""
        calc = TankFlashingCalculator()
        res = calc.calculate(throughput=10000, gas_oil_ratio=50, control_efficiency=0.95, ch4_content=0.80)
        assert _val(res["results"]["ch4"]) > 0
        assert _val(res["results"]["co2"]) > 0


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
        assert _val(res["results"]["co2"]) == pytest.approx(23.28, abs=0.5)

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
        assert _val(res["results"]["ch4"]) == pytest.approx(0.011, abs=0.002)

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
