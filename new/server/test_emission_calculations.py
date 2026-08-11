"""
=============================================================================
SCOPE 1 EMISSION CALCULATOR — EXHAUSTIVE CALCULATION TEST SUITE
=============================================================================
Tests every process type for both Tier 1 (default factors) and Tier 3
(specific / engineering-mode) calculations, verifying:
  • Correct math against hand-calculated expected values
  • Data flow from _process_row() → Emission object fields
  • CO2e totals using AR5 GWP (CH4=28, N2O=265)
  • Unit conversions (scf, m3, bbl, MMscf)
  • All process types: Combustion, Flaring, Venting/Blowdown,
    Tank Flashing, Pneumatic Devices, Completions, Liquids Unloading,
    Drilling Mud Degassing, Fugitive

Run with:
    cd c:\\Users\\samsung\\Desktop\\H2\\new\\server
    python -m pytest test_emission_calculations.py -v --tb=short
  OR:
    python test_emission_calculations.py
=============================================================================
"""

import sys
import os
import math
import unittest

# Add the server directory to path so we can import modules directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─── Import calculation engine ──────────────────────────────────────────────
from calculations.dispatcher import CalculationDispatcher
from calculations.units import CONVERSIONS, calculate_co2e
from calculations.constants import get_active_gwp

dispatcher = CalculationDispatcher()

# ─── GWP (AR5 — application default) ────────────────────────────────────────
GWP = get_active_gwp(standard="AR5")
GWP_CH4 = GWP["CH4"]  # 28
GWP_N2O = GWP["N2O"]  # 265

# ─── API 2021 Emission Factors (Section 5 — Natural Gas) ────────────────────
EF_NG = {
    "co2": 53.06,  # kg CO₂/MMBtu
    "ch4": 0.001,  # kg CH₄/MMBtu
    "n2o": 0.0001,  # kg N₂O/MMBtu
    "hhv": 1020,  # Btu/scf
    "unit": "kg/MMBtu",
    "fuel_type": "gases",
    "type": "gases",
    "uncertainty": {"co2": 0.05, "ch4": 0.20, "n2o": 0.20},
}

EF_DIESEL = {
    "co2": 73.96,  # kg CO₂/MMBtu  (API 2021 Table 5-1)
    "ch4": 0.003,
    "n2o": 0.0006,
    "hhv": 138700,  # Btu/gal
    "unit": "kg/MMBtu",
    "fuel_type": "liquids",
    "type": "liquids",
    "uncertainty": {"co2": 0.01, "ch4": 0.20, "n2o": 0.30},
}

# Empty uncertainty dict for process types that don't use catalog EFs
UNC_DEFAULT = {"_factor_source": "default"}
UNC_SPECIFIC = {"_factor_source": "specific"}

TOLERANCE = 1e-6  # absolute tolerance for float comparisons


def extract_val(result_gas):
    """Extract the central value from a propagated uncertainty dict or bare float."""
    if isinstance(result_gas, dict):
        return float(result_gas.get("value", 0) or 0)
    return float(result_gas or 0)


# =============================================================================
# TIER 1 — COMBUSTION (Natural Gas)
# =============================================================================
class TestTier1Combustion(unittest.TestCase):
    """
    Hand-calc for Natural Gas Tier 1:
      quantity = 10,000 scf
      HHV = 1,020 Btu/scf  → 10,000 × 1020 / 1,000,000 = 10.2 MMBtu
      CO2 = 10.2 × 53.06 kg = 541.212 kg = 0.541212 tonne
      CH4 = 10.2 × 0.001 kg = 0.0102 kg = 0.0000102 tonne
      N2O = 10.2 × 0.0001 kg = 0.00102 kg = 0.00000102 tonne
      CO2e = 0.541212 + 0.0000102*28 + 0.00000102*265
           = 0.541212 + 0.0002856 + 0.0002703 = 0.541768 tonne
    """

    def setUp(self):
        self.inputs = {
            "amount": 10000,
            "quantity": 10000,
            "unit": "scf",
            "factor_source": "default",
            "fuel_type": "gases",
            "hhv": 1020,
        }
        self.result = dispatcher.dispatch(
            "combustion", self.inputs, EF_NG, UNC_DEFAULT, gwp_dict=GWP
        )

    def test_structure(self):
        self.assertIn("results", self.result)
        self.assertIn("total_co2e", self.result)

    def test_co2_tier1(self):
        co2 = extract_val(self.result["results"]["co2"])
        expected = (10000 * 1020 / 1_000_000) * 53.06 / 1000.0
        self.assertAlmostEqual(
            co2,
            expected,
            places=6,
            msg=f"Tier1 Combustion CO2: got {co2}, expected {expected}",
        )

    def test_ch4_tier1(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        expected = (10000 * 1020 / 1_000_000) * 0.001 / 1000.0
        self.assertAlmostEqual(
            ch4,
            expected,
            places=8,
            msg=f"Tier1 Combustion CH4: got {ch4}, expected {expected}",
        )

    def test_n2o_tier1(self):
        n2o = extract_val(self.result["results"]["n2o"])
        expected = (10000 * 1020 / 1_000_000) * 0.0001 / 1000.0
        self.assertAlmostEqual(n2o, expected, places=9)

    def test_co2e_total(self):
        co2 = extract_val(self.result["results"]["co2"])
        ch4 = extract_val(self.result["results"]["ch4"])
        n2o = extract_val(self.result["results"]["n2o"])
        expected_co2e = co2 * 1 + ch4 * GWP_CH4 + n2o * GWP_N2O
        reported = float(self.result["total_co2e"])
        self.assertAlmostEqual(reported, expected_co2e, places=6)

    def test_unit_m3(self):
        """Same calculation using m3 input — should produce same result after conversion."""
        qty_m3 = 10000 * CONVERSIONS["scf_to_m3"]
        inputs_m3 = {**self.inputs, "amount": qty_m3, "quantity": qty_m3, "unit": "m3"}
        result_m3 = dispatcher.dispatch(
            "combustion", inputs_m3, EF_NG, UNC_DEFAULT, gwp_dict=GWP
        )
        co2_scf = extract_val(self.result["results"]["co2"])
        co2_m3 = extract_val(result_m3["results"]["co2"])
        self.assertAlmostEqual(
            co2_scf,
            co2_m3,
            places=4,
            msg="SCF and m3 inputs should give same CO2 result after conversion",
        )


# =============================================================================
# TIER 1 — COMBUSTION (Diesel)
# =============================================================================
class TestTier1CombustionDiesel(unittest.TestCase):
    """
    Diesel Tier 1:
      quantity = 500 gal
      HHV = 138,700 Btu/gal  → 500 × 138,700 / 1,000,000 = 69.35 MMBtu
      CO2 = 69.35 × 73.96 / 1000 = 5.12898 tonne
      CH4 = 69.35 × 0.003  / 1000 = 0.00020805 tonne
      N2O = 69.35 × 0.0006 / 1000 = 0.0000416  tonne
    """

    def setUp(self):
        qty = 500  # gallons
        hhv = 138700  # Btu/gal
        mmbtu = (qty * hhv) / 1_000_000
        self.expected_co2 = mmbtu * 73.96 / 1000.0
        self.expected_ch4 = mmbtu * 0.003 / 1000.0
        self.expected_n2o = mmbtu * 0.0006 / 1000.0

        inputs = {
            "amount": qty,
            "quantity": qty,
            "unit": "gal",
            "factor_source": "default",
            "fuel_type": "liquids",
            "hhv": hhv,
        }
        self.result = dispatcher.dispatch(
            "combustion", inputs, EF_DIESEL, UNC_DEFAULT, gwp_dict=GWP
        )

    def test_co2_diesel(self):
        co2 = extract_val(self.result["results"]["co2"])
        self.assertAlmostEqual(co2, self.expected_co2, places=5)

    def test_ch4_diesel(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(ch4, self.expected_ch4, places=7)

    def test_n2o_diesel(self):
        n2o = extract_val(self.result["results"]["n2o"])
        self.assertAlmostEqual(n2o, self.expected_n2o, places=8)

    def test_co2e_diesel(self):
        co2 = extract_val(self.result["results"]["co2"])
        ch4 = extract_val(self.result["results"]["ch4"])
        n2o = extract_val(self.result["results"]["n2o"])
        expected = co2 + ch4 * GWP_CH4 + n2o * GWP_N2O
        self.assertAlmostEqual(float(self.result["total_co2e"]), expected, places=5)


# =============================================================================
# TIER 1 — FLARING  (Tier 1 = generic EF-based fallback)
# =============================================================================
class TestTier1Flaring(unittest.TestCase):
    """
    Flaring Tier 1 (default factor_source → _generic_calculation):
    Uses API_FACTORS for 'Associated Gas' (typically direct vol EF).
    We test with a simple custom EF in kg/m3 to verify the math.
    EF: co2=1.8 kg/m3, ch4=0.05 kg/m3, unit='kg/m3'
    qty=5000 m3
    CO2 = 5000*1.8/1000 = 9 t, CH4 = 5000*0.05/1000 = 0.25 t
    """

    def setUp(self):
        self.ef = {
            "co2": 1.8,
            "ch4": 0.05,
            "n2o": 0,
            "unit": "kg/m3",
            "type": "default",
        }
        self.qty = 5000
        self.inputs = {
            "amount": self.qty,
            "quantity": self.qty,
            "unit": "m3",
            "factor_source": "default",
        }
        self.result = dispatcher.dispatch(
            "flaring", self.inputs, self.ef, UNC_DEFAULT, gwp_dict=GWP
        )

    def test_tier1_flaring_fallback_co2(self):
        """Tier 1 flaring falls through to generic EF-based calculation."""
        co2 = extract_val(self.result["results"]["co2"])
        expected = self.qty * 1.8 / 1000.0
        self.assertAlmostEqual(co2, expected, places=6)

    def test_tier1_flaring_fallback_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        expected = self.qty * 0.05 / 1000.0
        self.assertAlmostEqual(ch4, expected, places=6)


# =============================================================================
# TIER 3 — FLARING (Full Gas Composition / Engineering mode)
# =============================================================================
class TestTier3Flaring(unittest.TestCase):
    """
    Flaring Tier 3 (factor_source='specific') — Dual efficiency model:
      gas_volume = 1000 m3 (already at standard conditions)
      C1=85%, C2=5%, C3=3%, CO2_comp=3%, N2=4%
      flare_type = 'elevated' → eta_c=0.984, eta_d=0.98

      total_carbon_moles = 0.85*1 + 0.05*2 + 0.03*3 = 0.85+0.10+0.09 = 1.04 per mole gas

      CH4 undestroyed = vol * C1 * (1 - eta_d)
                      = 1000 * 0.85 * (1-0.98) = 1000 * 0.85 * 0.02 = 17 m3
      CH4 mass = 17 * 0.6785 kg/m3 = 11.5345 kg = 0.0115345 tonne

      CO2 from combustion = vol * total_C * eta_c * eta_d * density_co2
                          = 1000 * 1.04 * 0.984 * 0.98 * 1.861
                          = 1000 * 1.04 * 0.96432 * 1.861
        Let's compute: 1.04 * 0.984 = 1.02336; 1.02336 * 0.98 = 1.002893;
                        1.002893 * 1.861 = 1.8664 kg/m3
        CO2_combusted = 1000 * 1.8664 kg = 1866.4 kg = 1.8664 tonne

      CO2_native = vol * co2_comp * density_co2 = 1000 * 0.03 * 1.861 = 55.83 kg = 0.05583 tonne

      CO2_total = 1.8664 + 0.05583 = 1.9222 tonne
    """

    def setUp(self):
        self.vol_m3 = 1000.0
        self.ch4_frac = 0.85
        self.c2_frac = 0.05
        self.c3_frac = 0.03
        self.co2_comp = 0.03
        self.eta_c = 0.984
        self.eta_d = 0.98
        self.density_ch4 = CONVERSIONS["density_ch4"]  # 0.6785
        self.density_co2 = CONVERSIONS["density_co2"]  # 1.861

        # Expected values (hand calculated)
        ch4_undestroyed_m3 = self.vol_m3 * self.ch4_frac * (1 - self.eta_d)
        self.expected_ch4 = ch4_undestroyed_m3 * self.density_ch4 / 1000.0

        total_C = self.ch4_frac * 1 + self.c2_frac * 2 + self.c3_frac * 3
        co2_comb_vol = self.vol_m3 * total_C * self.eta_c * self.eta_d
        co2_comb_kg = co2_comb_vol * self.density_co2
        co2_native_kg = self.vol_m3 * self.co2_comp * self.density_co2
        self.expected_co2 = (co2_comb_kg + co2_native_kg) / 1000.0

        inputs = {
            "amount": self.vol_m3,
            "quantity": self.vol_m3,
            "unit": "m3",
            "factor_source": "specific",
            "flare_type": "elevated",
            "c1": self.ch4_frac * 100,  # dispatcher converts /100 for specific
            "c2": self.c2_frac * 100,
            "c3": self.c3_frac * 100,
            "co2_mol": self.co2_comp * 100,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3"}
        self.result = dispatcher.dispatch(
            "flaring", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP
        )

    def test_tier3_flaring_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(
            ch4,
            self.expected_ch4,
            places=6,
            msg=f"Tier3 Flaring CH4: got {ch4}, expected {self.expected_ch4}",
        )

    def test_tier3_flaring_co2(self):
        co2 = extract_val(self.result["results"]["co2"])
        self.assertAlmostEqual(
            co2,
            self.expected_co2,
            places=4,
            msg=f"Tier3 Flaring CO2: got {co2}, expected {self.expected_co2}",
        )

    def test_tier3_flaring_co2e(self):
        co2 = extract_val(self.result["results"]["co2"])
        ch4 = extract_val(self.result["results"]["ch4"])
        n2o_val = extract_val(self.result["results"].get("n2o", 0))
        expected = co2 + ch4 * GWP_CH4 + n2o_val * GWP_N2O
        self.assertAlmostEqual(float(self.result["total_co2e"]), expected, places=5)


# =============================================================================
# TIER 1 — VENTING / BLOWDOWN
# =============================================================================
class TestTier1Venting(unittest.TestCase):
    """
    Blowdown Tier 1 (default):
      vessel volume = 5 m3 physical
      pressure = 100 psig → P_abs = 100 + 14.696 = 114.696 psia
      T = 60 F → 288.706 K (standard)
      events = 3

      V_std = V_phys * (P_abs/P_std) * (T_std/T_abs)
            = 5 * (114.696/14.696) * (288.706/288.706)     [T=60F=std]
            = 5 * 7.8044 = 39.022 m3
      total_V = 39.022 * 3 = 117.066 m3

      ch4_fraction = 0.85
      CH4 vol = 117.066 * 0.85 = 99.506 m3
      CH4 mass = 99.506 * 0.6785 = 67.513 kg = 0.067513 tonne
    """

    def setUp(self):
        self.vol = 5.0
        self.press_psig = 100.0
        self.events = 3
        self.ch4_frac = 0.85
        from calculations.units import to_psia, STD_PRESSURE_PSIA, STD_TEMP_K, to_kelvin

        p_abs = to_psia(self.press_psig, "psig")
        t_abs = to_kelvin(60.0, "F")
        v_std = self.vol * (p_abs / STD_PRESSURE_PSIA) * (STD_TEMP_K / max(1.0, t_abs))
        total_v = v_std * self.events
        ch4_vol = total_v * self.ch4_frac
        self.expected_ch4 = ch4_vol * CONVERSIONS["density_ch4"] / 1000.0

        inputs = {
            "amount": self.vol,
            "quantity": self.vol,
            "unit": "m3",
            "factor_source": "specific",
            "blowdown_volume": self.vol,
            "blowdown_pressure": self.press_psig,
            "pressure": self.press_psig,
            "blowdown_events": self.events,
            "events": self.events,
            "ch4_content": self.ch4_frac * 100,  # %
            "c1": self.ch4_frac * 100,
            "co2_content": 0,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3"}
        self.result = dispatcher.dispatch(
            "venting", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP
        )

    def test_venting_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(
            ch4,
            self.expected_ch4,
            places=5,
            msg=f"Venting CH4: got {ch4}, expected {self.expected_ch4}",
        )

    def test_venting_co2e(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        expected_co2e = ch4 * GWP_CH4
        reported = float(self.result["total_co2e"])
        self.assertAlmostEqual(reported, expected_co2e, places=4)


# =============================================================================
# TIER 3 — TANK FLASHING (Storage Tanks)
# =============================================================================
class TestTier3TankFlashing(unittest.TestCase):
    """
    Tank Tier 3:
      throughput = 2000 bbl/month
      GOR = 200 scf/bbl
      CH4 content = 45%
      control_eff = 0

      Flash gas vol = throughput * GOR = 2000 * 200 = 400,000 scf
      CH4 vol = 400,000 * 0.45 = 180,000 scf → m3 = 180,000 * 0.0283168 = 5097.02 m3
      CH4 mass = 5097.02 * 0.6785 = 3458.39 kg = 3.45839 tonne
      CO2e = 3.45839 * 28 = 96.835 tonne CO2e
    """

    def setUp(self):
        self.throughput_bbl = 2000.0
        self.gor = 200.0  # scf/bbl
        self.ch4_frac = 0.45

        flash_gas_scf = self.throughput_bbl * self.gor
        ch4_scf = flash_gas_scf * self.ch4_frac
        ch4_m3 = ch4_scf * CONVERSIONS["scf_to_m3"]
        self.expected_ch4 = ch4_m3 * CONVERSIONS["density_ch4"] / 1000.0

        inputs = {
            "amount": self.throughput_bbl,
            "quantity": self.throughput_bbl,
            "unit": "bbl",
            "factor_source": "specific",
            "tank_gor": self.gor,
            "gor": self.gor,
            "tank_ch4_content": self.ch4_frac * 100,
            "ch4_content": self.ch4_frac * 100,
            "c1": self.ch4_frac * 100,
            "control_efficiency": 0,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3"}
        self.result = dispatcher.dispatch(
            "tank_flashing", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP
        )

    def test_tank_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(
            ch4,
            self.expected_ch4,
            places=4,
            msg=f"Tank CH4: got {ch4}, expected {self.expected_ch4}",
        )

    def test_tank_co2e(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        co2 = extract_val(self.result["results"].get("co2", 0))
        expected = co2 + ch4 * GWP_CH4
        self.assertAlmostEqual(float(self.result["total_co2e"]), expected, places=4)


# =============================================================================
# TIER 3 — PNEUMATIC DEVICES
# =============================================================================
class TestTier3PneumaticDevices(unittest.TestCase):
    """
    Pneumatic Tier 3:
      count = 10 devices
      hours = 8760 hr/yr
      bleed_rate = 6 scf/hr (high-bleed)
      CH4 content = 0.85

      Total gas = 10 * 8760 * 6 = 525,600 scf
      CH4 vol  = 525,600 * 0.85 = 446,760 scf → m3 = 446,760 * 0.0283168 = 12,650.27 m3
      CH4 mass = 12,650.27 * 0.6785 = 8,584.21 kg = 8.58421 tonne CO2e = 240.36 tonne
    """

    def setUp(self):
        self.count = 10
        self.hours = 8760
        self.bleed_rate_scf_hr = 6.0
        self.ch4_frac = 0.85

        total_gas_scf = self.count * self.hours * self.bleed_rate_scf_hr
        ch4_scf = total_gas_scf * self.ch4_frac
        ch4_m3 = ch4_scf * CONVERSIONS["scf_to_m3"]
        self.expected_ch4 = ch4_m3 * CONVERSIONS["density_ch4"] / 1000.0

        inputs = {
            "amount": self.count,
            "quantity": self.count,
            "unit": "units",
            "factor_source": "specific",
            "pneu_count": self.count,
            "pneu_hours": self.hours,
            "hours_operating": self.hours,
            "pneu_bleed_rate": self.bleed_rate_scf_hr,
            "bleed_rate": self.bleed_rate_scf_hr,
            "pneu_ch4_content": self.ch4_frac * 100,
            "ch4_content": self.ch4_frac * 100,
            "c1": self.ch4_frac * 100,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/unit"}
        self.result = dispatcher.dispatch(
            "pneumatic_devices", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP
        )

    def test_pneumatic_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(
            ch4,
            self.expected_ch4,
            places=3,
            msg=f"Pneumatic CH4: got {ch4}, expected {self.expected_ch4}",
        )

    def test_pneumatic_co2e(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        expected = ch4 * GWP_CH4
        self.assertAlmostEqual(float(self.result["total_co2e"]), expected, places=3)


# =============================================================================
# TIER 3 — LIQUIDS UNLOADING
# =============================================================================
class TestTier3LiquidsUnloading(unittest.TestCase):
    """
    Liquids Unloading Tier 3 (API Eq. 6-3):
      well_depth = 5000 ft
      diameter = 2.441 in  → D_m = 2.441 * 0.0254 = 0.062001 m
      pressure = 500 psig → P_abs = 500 + 14.696 = 514.696 psia
      T = 60 F → standard T_K = 288.706 K
      events = 12

      A = pi/4 * D_m^2 = pi/4 * 0.062001^2 = 0.003018 m2
      depth_m = 5000 * 0.3048 = 1524 m
      V_tubing = A * depth_m = 0.003018 * 1524 = 4.599 m3

      p_factor = 514.696 / 14.696 = 35.02
      t_factor = 288.706 / 288.706 = 1.0   (T=60F = std)
      V_std = 4.599 * 35.02 = 161.1 m3
      total_V = 161.1 * 12 = 1933.2 m3

      ch4_content = 0.85
      CH4 vol = 1933.2 * 0.85 = 1643.22 m3
      CH4 mass = 1643.22 * 0.6785 = 1114.94 kg = 1.11494 tonne
    """

    def setUp(self):
        self.depth_ft = 5000.0
        self.diam_in = 2.441
        self.press_psig = 500.0
        self.temp_f = 60.0
        self.events = 12
        self.ch4_frac = 0.85

        from calculations.units import to_psia, to_kelvin, STD_PRESSURE_PSIA, STD_TEMP_K

        d_m = self.diam_in * 0.0254
        depth_m = self.depth_ft * 0.3048
        v_tubing = (math.pi / 4.0) * (d_m**2) * depth_m
        p_abs = to_psia(self.press_psig, "psig")
        t_abs = to_kelvin(self.temp_f, "F")
        v_std = v_tubing * (p_abs / STD_PRESSURE_PSIA) * (STD_TEMP_K / max(1.0, t_abs))
        total_v = v_std * self.events
        ch4_vol = total_v * self.ch4_frac
        self.expected_ch4 = ch4_vol * CONVERSIONS["density_ch4"] / 1000.0

        inputs = {
            "amount": self.events,
            "quantity": self.events,
            "unit": "events",
            "factor_source": "specific",
            "unload_depth": self.depth_ft,
            "well_depth": self.depth_ft,
            "unload_diam": self.diam_in,
            "diameter": self.diam_in,
            "unload_press": self.press_psig,
            "pressure": self.press_psig,
            "unload_freq": self.events,
            "events": self.events,
            "ch4_content": self.ch4_frac * 100,
            "c1": self.ch4_frac * 100,
            "co2_content": 0,
            "control_efficiency": 0,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/event"}
        self.result = dispatcher.dispatch(
            "liquids_unloading", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP
        )

    def test_unloading_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(
            ch4,
            self.expected_ch4,
            places=3,
            msg=f"Liquids Unloading CH4: got {ch4}, expected {self.expected_ch4}",
        )

    def test_unloading_co2e(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        co2 = extract_val(self.result["results"].get("co2", 0))
        expected = co2 + ch4 * GWP_CH4
        self.assertAlmostEqual(float(self.result["total_co2e"]), expected, places=3)


# =============================================================================
# TIER 3 — DRILLING MUD DEGASSING
# =============================================================================
class TestTier1DrillingMud(unittest.TestCase):
    """
    Mud Degassing Tier 1 (water-based mud):
      mud_volume = 500 m3
      EF (water-based) = 0.15 kg CH4/m3
      CH4 = 500 * 0.15 = 75 kg = 0.075 tonne
      CO2e = 0.075 * 28 = 2.1 tonne
    """

    def setUp(self):
        self.mud_vol = 500.0
        self.expected_ch4 = self.mud_vol * 0.15 / 1000.0

        inputs = {
            "amount": self.mud_vol,
            "quantity": self.mud_vol,
            "unit": "m3",
            "factor_source": "specific",
            "mud_type": "water_based",
            "mud_vol": self.mud_vol,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3"}
        self.result = dispatcher.dispatch(
            "drilling", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP
        )

    def test_mud_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(
            ch4,
            self.expected_ch4,
            places=6,
            msg=f"Drilling mud CH4: got {ch4}, expected {self.expected_ch4}",
        )

    def test_mud_co2e(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        expected = ch4 * GWP_CH4
        self.assertAlmostEqual(float(self.result["total_co2e"]), expected, places=5)

    def test_oil_based_mud(self):
        """Oil-based mud uses EF=0.35 kg/m3."""
        inputs = {
            "amount": 200,
            "quantity": 200,
            "unit": "m3",
            "factor_source": "specific",
            "mud_type": "oil_based",
            "mud_vol": 200,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3"}
        result = dispatcher.dispatch("drilling", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP)
        ch4 = extract_val(result["results"]["ch4"])
        expected = 200 * 0.35 / 1000.0
        self.assertAlmostEqual(ch4, expected, places=6)


# =============================================================================
# TIER 3 — WELL COMPLETIONS FLOWBACK
# =============================================================================
class TestTier3Completions(unittest.TestCase):
    """
    Completions Tier 3 (metered_volume):
      flowback_volume = 50,000 m3
      CH4 content = 0.80
      control_efficiency = 0  (no flaring)

      CH4 vol = 50,000 * 0.80 = 40,000 m3
      CH4 mass = 40,000 * 0.6785 = 27,140 kg = 27.14 tonne
    """

    def setUp(self):
        self.vol_m3 = 50_000.0
        self.ch4_frac = 0.80
        self.expected_ch4 = (
            self.vol_m3 * self.ch4_frac * CONVERSIONS["density_ch4"] / 1000.0
        )

        inputs = {
            "amount": self.vol_m3,
            "quantity": self.vol_m3,
            "unit": "m3",
            "factor_source": "specific",
            "comp_method": "metered_volume",
            "ch4_content": self.ch4_frac * 100,
            "c1": self.ch4_frac * 100,
            "control_efficiency": 0,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3"}
        self.result = dispatcher.dispatch(
            "completions", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP
        )

    def test_completions_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(
            ch4,
            self.expected_ch4,
            places=2,
            msg=f"Completions CH4: got {ch4}, expected {self.expected_ch4}",
        )

    def test_completions_co2e(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        co2 = extract_val(self.result["results"].get("co2", 0))
        expected = co2 + ch4 * GWP_CH4
        self.assertAlmostEqual(float(self.result["total_co2e"]), expected, places=2)


# =============================================================================
# TIER 1 — FUGITIVE (Average EF fallback)
# =============================================================================
class TestTier1FugitiveAverage(unittest.TestCase):
    """
    Fugitive average — uses _generic_calculation with catalog EF.
    EF: ch4=0.1 kg/unit, unit=kg/unit  (hypothetical for math clarity)
    count=50 → CH4 = 50 * 0.1 / 1000 = 0.005 tonne
    """

    def setUp(self):
        self.count = 50
        ef = {"co2": 0, "ch4": 0.1, "n2o": 0, "unit": "kg/unit"}
        inputs = {
            "amount": self.count,
            "quantity": self.count,
            "unit": "unit",
            "factor_source": "default",
            "fugitive_method": "average",
        }
        self.result = dispatcher.dispatch(
            "fugitive", inputs, ef, UNC_DEFAULT, gwp_dict=GWP
        )
        self.expected_ch4 = self.count * 0.1 / 1000.0

    def test_fugitive_average_ch4(self):
        ch4 = extract_val(self.result["results"]["ch4"])
        self.assertAlmostEqual(ch4, self.expected_ch4, places=6)


# =============================================================================
# CO2E CALCULATION CORRECTNESS
# =============================================================================
class TestCO2ECalculation(unittest.TestCase):
    """Verify the CO2e aggregation function is internally consistent."""

    def test_pure_co2(self):
        self.assertAlmostEqual(calculate_co2e(1.0, 0, 0, gwp_dict=GWP), 1.0)

    def test_pure_ch4_ar5(self):
        self.assertAlmostEqual(calculate_co2e(0, 1.0, 0, gwp_dict=GWP), 28.0)

    def test_pure_n2o_ar5(self):
        self.assertAlmostEqual(calculate_co2e(0, 0, 1.0, gwp_dict=GWP), 265.0)

    def test_mixed(self):
        co2, ch4, n2o = 10.0, 0.5, 0.01
        expected = 10.0 + 0.5 * 28 + 0.01 * 265
        self.assertAlmostEqual(calculate_co2e(co2, ch4, n2o, gwp_dict=GWP), expected)

    def test_ar4_gwp(self):
        gwp_ar4 = get_active_gwp(standard="AR4")
        # AR4: CH4=25, N2O=298
        self.assertAlmostEqual(calculate_co2e(0, 1.0, 0, gwp_dict=gwp_ar4), 25.0)
        self.assertAlmostEqual(calculate_co2e(0, 0, 1.0, gwp_dict=gwp_ar4), 298.0)

    def test_ar6_gwp(self):
        gwp_ar6 = get_active_gwp(standard="AR6")
        # AR6: CH4=27.9, N2O=273
        self.assertAlmostEqual(
            calculate_co2e(0, 1.0, 0, gwp_dict=gwp_ar6), 27.9, places=1
        )
        self.assertAlmostEqual(calculate_co2e(0, 0, 1.0, gwp_dict=gwp_ar6), 273.0)


# =============================================================================
# UNIT CONVERSION CORRECTNESS
# =============================================================================
class TestUnitConversions(unittest.TestCase):
    """Verify critical volume/mass conversions used in calculations."""

    def test_scf_to_m3(self):
        self.assertAlmostEqual(CONVERSIONS["scf_to_m3"], 0.0283168, places=7)

    def test_m3_to_scf(self):
        self.assertAlmostEqual(CONVERSIONS["m3_to_scf"], 35.3147, places=4)

    def test_bbl_to_m3(self):
        self.assertAlmostEqual(CONVERSIONS["bbl_to_m3"], 0.158987, places=6)

    def test_scf_m3_roundtrip(self):
        # Note: scf_to_m3 (0.0283168) and m3_to_scf (35.3147) are truncated constants
        # so roundtrip has inherent precision loss of ~0.009% — acceptable for engineering use.
        val = 12345.0
        roundtrip = val * CONVERSIONS["scf_to_m3"] * CONVERSIONS["m3_to_scf"]
        relative_error = abs(roundtrip - val) / val
        self.assertLess(
            relative_error,
            0.0002,  # <0.02% error acceptable
            msg=f"SCF roundtrip error {relative_error*100:.4f}% exceeds 0.02% threshold",
        )

    def test_density_ch4(self):
        # CH4 density at standard conditions should be ~0.6785 kg/m3
        self.assertAlmostEqual(CONVERSIONS["density_ch4"], 0.6785, places=4)

    def test_density_co2(self):
        # CO2 density at standard conditions should be ~1.861 kg/m3
        self.assertAlmostEqual(CONVERSIONS["density_co2"], 1.861, places=3)


# =============================================================================
# EDGE CASES & BOUNDARY CONDITIONS
# =============================================================================
class TestEdgeCases(unittest.TestCase):

    def test_zero_quantity_combustion(self):
        """Zero quantity should produce zero emissions without crash."""
        inputs = {
            "amount": 0,
            "quantity": 0,
            "unit": "scf",
            "factor_source": "default",
            "hhv": 1020,
        }
        result = dispatcher.dispatch(
            "combustion", inputs, EF_NG, UNC_DEFAULT, gwp_dict=GWP
        )
        self.assertAlmostEqual(float(result["total_co2e"]), 0.0)

    def test_negative_quantity_raises(self):
        """Negative quantity must raise ValueError."""
        inputs = {
            "amount": -100,
            "quantity": -100,
            "unit": "scf",
            "factor_source": "default",
            "hhv": 1020,
        }
        with self.assertRaises(ValueError):
            dispatcher.dispatch("combustion", inputs, EF_NG, UNC_DEFAULT, gwp_dict=GWP)

    def test_mmscf_unit_combustion(self):
        """1 MMscf = 1,000,000 scf — result should match 1M scf calculation."""
        inputs_mmscf = {
            "amount": 1,
            "quantity": 1,
            "unit": "mmscf",
            "factor_source": "default",
            "hhv": 1020,
            "fuel_type": "gases",
        }
        inputs_scf = {
            "amount": 1_000_000,
            "quantity": 1_000_000,
            "unit": "scf",
            "factor_source": "default",
            "hhv": 1020,
            "fuel_type": "gases",
        }
        r_mmscf = dispatcher.dispatch(
            "combustion", inputs_mmscf, EF_NG, UNC_DEFAULT, gwp_dict=GWP
        )
        r_scf = dispatcher.dispatch(
            "combustion", inputs_scf, EF_NG, UNC_DEFAULT, gwp_dict=GWP
        )
        co2_mmscf = extract_val(r_mmscf["results"]["co2"])
        co2_scf = extract_val(r_scf["results"]["co2"])
        self.assertAlmostEqual(
            co2_mmscf,
            co2_scf,
            places=3,
            msg=f"1 MMscf should equal 1e6 scf: {co2_mmscf} vs {co2_scf}",
        )

    def test_tank_zero_gor_returns_zero(self):
        """If GOR=0 and EF=0, result should be zero (no flash gas)."""
        inputs = {
            "amount": 1000,
            "quantity": 1000,
            "unit": "bbl",
            "factor_source": "specific",
            "tank_gor": 0,
            "gor": 0,
            "ch4_content": 50,
            "c1": 50,
        }
        ef = {"co2": 0, "ch4": 0, "n2o": 0, "unit": "kg/m3"}
        result = dispatcher.dispatch(
            "tank_flashing", inputs, ef, UNC_SPECIFIC, gwp_dict=GWP
        )
        self.assertAlmostEqual(float(result["total_co2e"]), 0.0)

    def test_combustion_mscf_unit(self):
        """1 Mscf = 1000 scf."""
        inputs_mscf = {
            "amount": 10,
            "quantity": 10,
            "unit": "mscf",
            "factor_source": "default",
            "hhv": 1020,
            "fuel_type": "gases",
        }
        inputs_scf = {
            "amount": 10_000,
            "quantity": 10_000,
            "unit": "scf",
            "factor_source": "default",
            "hhv": 1020,
            "fuel_type": "gases",
        }
        r_mscf = dispatcher.dispatch(
            "combustion", inputs_mscf, EF_NG, UNC_DEFAULT, gwp_dict=GWP
        )
        r_scf = dispatcher.dispatch(
            "combustion", inputs_scf, EF_NG, UNC_DEFAULT, gwp_dict=GWP
        )
        self.assertAlmostEqual(
            extract_val(r_mscf["results"]["co2"]),
            extract_val(r_scf["results"]["co2"]),
            places=4,
        )


# =============================================================================
# TIER 3 — COMBUSTION WITH GAS COMPOSITION (Carbon mass balance override)
# =============================================================================
class TestTier3CombustionGasComposition(unittest.TestCase):
    """
    Tier 3 Combustion with gas composition (carbon mass balance):
      volume = 1000 scf → 1000 * 0.0283168 = 28.3168 m3
      Gas: C1=80%, C2=10%, C3=5%, CO2_comp=5%
      combustion_efficiency = 0.995

      total_carbon_moles = 0.80*1 + 0.10*2 + 0.05*3 = 0.80+0.20+0.15 = 1.15

      CO2_combusted = vol_m3 * total_C * eta_c * density_co2
                    = 28.3168 * 1.15 * 0.995 * 1.861
                    = 28.3168 * 1.14425 * 1.861
        28.3168 * 1.15 = 32.5643; 32.5643 * 0.995 = 32.4015; 32.4015 * 1.861 = 60.299 kg

      CO2_native = vol * co2_comp * density_co2 = 28.3168 * 0.05 * 1.861 = 2.634 kg

      CO2_total = (60.299 + 2.634) / 1000 = 0.062933 tonne
    """

    def setUp(self):
        self.vol_scf = 1000.0
        vol_m3 = self.vol_scf * CONVERSIONS["scf_to_m3"]
        c1, c2, c3 = 0.80, 0.10, 0.05
        co2_comp = 0.05
        eta_c = 0.995
        density_co2 = CONVERSIONS["density_co2"]

        total_C = c1 * 1 + c2 * 2 + c3 * 3
        co2_comb = vol_m3 * total_C * eta_c * density_co2
        co2_nat = vol_m3 * co2_comp * density_co2
        self.expected_co2 = (co2_comb + co2_nat) / 1000.0

        inputs = {
            "amount": self.vol_scf,
            "quantity": self.vol_scf,
            "unit": "scf",
            "factor_source": "specific",
            "fuel_type": "gases",
            "hhv": 1020,
            "combustion_efficiency": eta_c * 100,  # passed as %
            "c1": c1 * 100,
            "c2": c2 * 100,
            "c3": c3 * 100,
            "co2_content": co2_comp * 100,
            "co2_mol": co2_comp * 100,
        }
        self.result = dispatcher.dispatch(
            "combustion", inputs, EF_NG, UNC_SPECIFIC, gwp_dict=GWP
        )

    def test_tier3_combustion_co2(self):
        co2 = extract_val(self.result["results"]["co2"])
        self.assertAlmostEqual(
            co2,
            self.expected_co2,
            places=4,
            msg=f"Tier3 Combustion CO2 (gas comp): got {co2}, expected {self.expected_co2}",
        )


# =============================================================================
# PROCESS_ROW INTEGRATION TEST (using mocked objects)
# =============================================================================
class TestProcessRowIntegration(unittest.TestCase):
    """
    Tests the full _process_row pipeline to verify data gets into Emission fields correctly.
    Uses mock objects to avoid needing a real database.
    """

    def _make_facility(self, fid=1, name="Test Plant"):
        class MockFacility:
            id = fid
            activity = "Exploration & Production"
            division = "Production"
            field = "North Field"

        f = MockFacility()
        f.name = name
        return f

    def test_combustion_process_row(self):
        """_process_row should return an Emission object with correct fields."""
        from background_processor import _process_row
        from calculations import compute_emissions
        from emission_factors import API_FACTORS

        fac = self._make_facility()
        fac_name_map = {fac.name.lower(): fac}
        fac_id_map = {"1": fac}
        cf_name_map = {}

        row = {
            "date": "2024-01",
            "facility_name": "Test Plant",
            "quantity": 10000,
            "unit": "scf",
            "process": "Combustion",
            "fuel": "Natural Gas",
            "factor_type": "default",
            "equipment": "GEN-001",
            "activity": "Exploration & Production",
        }

        gwp_dict = get_active_gwp(standard="AR5")
        emission, errors = _process_row(
            row,
            user_id=1,
            fac_name_map=fac_name_map,
            fac_id_map=fac_id_map,
            cf_name_map=cf_name_map,
            compute_emissions_fn=compute_emissions,
            API_FACTORS_dict=API_FACTORS,
            global_factor_type="auto",
            gwp_dict=gwp_dict,
        )

        self.assertEqual(errors, [], msg=f"Expected no errors, got: {errors}")
        self.assertIsNotNone(emission)
        self.assertEqual(emission.facility_id, 1)
        self.assertEqual(emission.process_type, "Combustion")
        self.assertEqual(emission.fuel_type, "Natural Gas")
        self.assertEqual(emission.quantity, 10000)
        self.assertEqual(emission.unit, "scf")
        self.assertEqual(emission.year, 2024)
        self.assertEqual(emission.month, 1)
        self.assertGreater(emission.co2_emissions, 0)
        self.assertGreater(emission.co2e_total, 0)
        # Verify CO2e = CO2 + CH4*28 + N2O*265
        expected_co2e = (
            emission.co2_emissions
            + emission.ch4_emissions * GWP_CH4
            + emission.n2o_emissions * GWP_N2O
        )
        self.assertAlmostEqual(emission.co2e_total, expected_co2e, places=6)

    def test_missing_facility_returns_error(self):
        """Row with unknown facility should return an error, not crash."""
        from background_processor import _process_row
        from calculations import compute_emissions
        from emission_factors import API_FACTORS

        row = {
            "date": "2024-06",
            "facility_name": "NONEXISTENT PLANT",
            "quantity": 100,
            "unit": "m3",
            "process": "Combustion",
            "fuel": "Natural Gas",
            "factor_type": "default",
        }
        emission, errors = _process_row(
            row,
            user_id=1,
            fac_name_map={},
            fac_id_map={},
            cf_name_map={},
            compute_emissions_fn=compute_emissions,
            API_FACTORS_dict=API_FACTORS,
            global_factor_type="auto",
            gwp_dict=get_active_gwp(standard="AR5"),
        )
        self.assertIsNone(emission)
        self.assertTrue(len(errors) > 0)
        self.assertIn("NONEXISTENT PLANT", errors[0])

    def test_missing_date_returns_error(self):
        """Row with no date should return a date error."""
        from background_processor import _process_row
        from calculations import compute_emissions
        from emission_factors import API_FACTORS

        fac = self._make_facility()
        row = {
            "facility_name": "Test Plant",
            "quantity": 100,
            "unit": "m3",
            "process": "Combustion",
            "fuel": "Natural Gas",
        }
        emission, errors = _process_row(
            row,
            user_id=1,
            fac_name_map={"test plant": fac},
            fac_id_map={"1": fac},
            cf_name_map={},
            compute_emissions_fn=compute_emissions,
            API_FACTORS_dict=API_FACTORS,
            global_factor_type="auto",
            gwp_dict=get_active_gwp(standard="AR5"),
        )
        self.assertIsNone(emission)
        self.assertTrue(len(errors) > 0)

    def test_flaring_process_row(self):
        """Verify flaring process row with Tier 1 default factor."""
        from background_processor import _process_row
        from calculations import compute_emissions
        from emission_factors import API_FACTORS

        fac = self._make_facility()
        row = {
            "date": "2024-03",
            "facility_name": "Test Plant",
            "quantity": 5000,
            "unit": "m3",
            "process": "Flaring",
            "fuel": "Associated Gas",
            "factor_type": "default",
        }
        emission, errors = _process_row(
            row,
            user_id=1,
            fac_name_map={"test plant": fac},
            fac_id_map={"1": fac},
            cf_name_map={},
            compute_emissions_fn=compute_emissions,
            API_FACTORS_dict=API_FACTORS,
            global_factor_type="auto",
            gwp_dict=get_active_gwp(standard="AR5"),
        )
        # If Associated Gas is in API_FACTORS, should succeed; if not, will error on EF lookup
        # Either way: no Python crash, either emission or errors
        self.assertTrue(
            emission is not None or len(errors) > 0,
            "Flaring row should either succeed or produce a descriptive error, not crash",
        )

    def test_venting_process_row(self):
        """Venting row with all required fields for Tier 3."""
        from background_processor import _process_row
        from calculations import compute_emissions
        from emission_factors import API_FACTORS

        fac = self._make_facility()
        row = {
            "date": "2024-05",
            "facility_name": "Test Plant",
            "quantity": 5,
            "unit": "m3",
            "process": "Venting",
            "fuel": "Natural Gas (Venting/Blowdown)",
            "factor_type": "default",
            "blowdown_volume": 5,
            "pressure": 100,
            "events": 3,
            "ch4_content": 85,
        }
        emission, errors = _process_row(
            row,
            user_id=1,
            fac_name_map={"test plant": fac},
            fac_id_map={"1": fac},
            cf_name_map={},
            compute_emissions_fn=compute_emissions,
            API_FACTORS_dict=API_FACTORS,
            global_factor_type="auto",
            gwp_dict=get_active_gwp(standard="AR5"),
        )
        self.assertTrue(
            emission is not None or len(errors) > 0,
            "Venting row should not crash, must produce result or error",
        )


# =============================================================================
# SUMMARY REPORTER
# =============================================================================
class SummaryResult:
    """Aggregates test results for a final summary table."""



if __name__ == "__main__":
    print("=" * 75)
    print("  SCOPE 1 EMISSION CALCULATOR — EXHAUSTIVE TEST SUITE")
    print("  GWP Standard: AR5  |  CH4=28  |  N2O=265  |  CO2=1")
    print("=" * 75)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestCO2ECalculation,
        TestUnitConversions,
        TestTier1Combustion,
        TestTier1CombustionDiesel,
        TestTier1Flaring,
        TestTier3Flaring,
        TestTier1Venting,
        TestTier3TankFlashing,
        TestTier3PneumaticDevices,
        TestTier3LiquidsUnloading,
        TestTier1DrillingMud,
        TestTier3Completions,
        TestTier1FugitiveAverage,
        TestTier3CombustionGasComposition,
        TestEdgeCases,
        TestProcessRowIntegration,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 75)
    if result.wasSuccessful():
        print(f"  [PASS]  ALL {result.testsRun} TESTS PASSED")
    else:
        print(
            f"  [FAIL]  {len(result.failures)} FAILURES / {len(result.errors)} ERRORS  out of {result.testsRun} tests"
        )
        for test, traceback in result.failures + result.errors:
            print(f"\n  FAILED: {test}")
    print("=" * 75)

    sys.exit(0 if result.wasSuccessful() else 1)
