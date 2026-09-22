"""
test_qfull_unit_conversions.py

QFULL END-TO-END CALCULATION PIPELINE VALIDATION
Phase 3: Unit Conversion Validation

Validates that physically equivalent quantities expressed in DIFFERENT UNITS
produce EQUIVALENT emission results. Each test:
1. Picks a known quantity in a base unit
2. Converts it to an equivalent quantity in a different unit
3. Runs compute_emissions for both
4. Asserts the results are equal within conversion rounding tolerance (0.1%)

API Reference: API Compendium 2021 §4.2
Date: 2026-09-21
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from calculations.legacy_engine import compute_emissions

# =====================================================================
# INDEPENDENT REFERENCE CONSTANTS (do NOT import from app)
# =====================================================================
SCF_TO_M3 = 0.028316846592
M3_TO_SCF = 35.314666721
DENSITY_CH4 = 0.6785   # kg/m3
DENSITY_CO2 = 1.861    # kg/m3
BBL_TO_M3 = 0.158987295
GAL_TO_M3 = 0.003785411784
LITER_TO_M3 = 0.001
LB_TO_KG = 0.45359237
TONNE_TO_KG = 1000.0
GWP_CH4_AR5 = 28.0
GWP_N2O_AR5 = 265.0
STD_TEMP_K = 288.706
STD_PRESS_PSIA = 14.696


def ref_co2e(co2=0.0, ch4=0.0, n2o=0.0):
    return co2 * 1.0 + ch4 * GWP_CH4_AR5 + n2o * GWP_N2O_AR5


# =====================================================================
# TEST CLASS: Mud Degassing Volume Units
# The dispatcher normalizes all volumes to m3 via _normalize_volume()
# before multiplying by the EF in kg/m3.
# =====================================================================
class TestMudVolumeUnits:
    """
    Verify that mud degassing gives same CH4 regardless of volume unit.
    Reference formula: ch4_kg = mud_vol_m3 * EF; tonnes = /1000
    For water_based: EF = 0.15 kg CH4/m3

    200 m3 = 1258.128... bbl = 52834.4... gal = 200,000 L
    Expected CH4 = 200 * 0.15 / 1000 = 0.030 tonnes
    """

    BASE_VOL_M3 = 200.0
    EXPECTED_CH4 = BASE_VOL_M3 * 0.15 / 1000.0  # 0.030 tonnes

    def _run(self, qty, unit):
        payload = {
            "process_type": "drilling",
            "quantity": qty,
            "unit": unit,
            "factor_source": "specific",
            "mud_type": "water_based",
        }
        em, _ = compute_emissions(payload, {})
        return em

    def test_mud_m3_reference(self):
        """Reference: 200 m3 water_based mud = 0.030 t CH4."""
        em = self._run(self.BASE_VOL_M3, "m3")
        assert em["ch4"] == pytest.approx(self.EXPECTED_CH4, rel=1e-4), (
            f"m3 reference: expected {self.EXPECTED_CH4:.6f}, got {em['ch4']:.6f}"
        )

    def test_mud_bbl_equivalent_to_m3(self):
        """
        1 m3 = 1/0.158987295 bbl = 6.28981 bbl
        200 m3 = 1258.128... bbl → same CH4.
        """
        qty_bbl = self.BASE_VOL_M3 / BBL_TO_M3
        em_m3 = self._run(self.BASE_VOL_M3, "m3")
        em_bbl = self._run(qty_bbl, "bbl")

        assert em_bbl["ch4"] == pytest.approx(em_m3["ch4"], rel=1e-3), (
            f"bbl vs m3: m3_result={em_m3['ch4']:.6f}, bbl_result={em_bbl['ch4']:.6f}\n"
            f"  (200 m3 = {qty_bbl:.4f} bbl)"
        )
        # Also verify against expected
        assert em_bbl["ch4"] == pytest.approx(self.EXPECTED_CH4, rel=1e-3)

    def test_mud_gal_equivalent_to_m3(self):
        """
        1 m3 = 264.172 gal
        200 m3 = 52834.4... gal → same CH4.
        """
        qty_gal = self.BASE_VOL_M3 / GAL_TO_M3
        em_m3 = self._run(self.BASE_VOL_M3, "m3")
        em_gal = self._run(qty_gal, "gal")

        assert em_gal["ch4"] == pytest.approx(em_m3["ch4"], rel=1e-3), (
            f"gal vs m3: m3={em_m3['ch4']:.6f}, gal={em_gal['ch4']:.6f}\n"
            f"  (200 m3 = {qty_gal:.2f} gal)"
        )

    def test_mud_liter_equivalent_to_m3(self):
        """
        1 m3 = 1000 L
        200 m3 = 200,000 L → same CH4.
        """
        qty_l = self.BASE_VOL_M3 / LITER_TO_M3
        em_m3 = self._run(self.BASE_VOL_M3, "m3")
        em_liter = self._run(qty_l, "liter")

        assert em_liter["ch4"] == pytest.approx(em_m3["ch4"], rel=1e-3), (
            f"liter vs m3: m3={em_m3['ch4']:.6f}, liter={em_liter['ch4']:.6f}"
        )

    def test_mud_oil_based_bbl_vs_m3(self):
        """
        Oil-based mud (EF=0.35 kg/m3): 100 m3 vs equivalent bbl.
        Expected: 100 * 0.35 / 1000 = 0.035 t CH4
        """
        qty_m3 = 100.0
        qty_bbl = qty_m3 / BBL_TO_M3

        def run_oil(qty, unit):
            return compute_emissions({
                "process_type": "drilling", "quantity": qty, "unit": unit,
                "factor_source": "specific", "mud_type": "oil_based"
            }, {})[0]

        em_m3 = run_oil(qty_m3, "m3")
        em_bbl = run_oil(qty_bbl, "bbl")

        expected = qty_m3 * 0.35 / 1000.0
        assert em_m3["ch4"] == pytest.approx(expected, rel=1e-4)
        assert em_bbl["ch4"] == pytest.approx(expected, rel=1e-3)


# =====================================================================
# TEST CLASS: Blowdown Volume Units (vessel volume)
# =====================================================================
class TestBlowdownVolumeUnits:
    """
    Blowdown: vessel volume in m3 vs scf should give same result
    after the dispatcher normalizes both to m3 for T/P correction.

    Reference: 5 m3 vessel, 500 psig, 10 events, ch4=0.85, temp=60°F
    p_factor = (500+14.696)/14.696 = 35.023
    t_factor = 288.706/288.706 = 1.0 (at 60°F)
    v_std = 5 * 35.023 * 1.0 = 175.11 m3 per event
    total = 175.11 * 10 = 1751.1 m3
    ch4_tonnes = 1751.1 * 0.85 * 0.6785 / 1000 ≈ 1.0093 t
    """

    BASE_VOL_M3 = 5.0
    PRESSURE_PSIG = 500.0
    EVENTS = 10
    CH4_FRAC = 0.85

    # INDEPENDENT REFERENCE CALCULATION
    P_ABS = PRESSURE_PSIG + STD_PRESS_PSIA
    P_FACTOR = P_ABS / STD_PRESS_PSIA
    # At 60°F: t_factor = 1.0
    EXPECTED_CH4 = BASE_VOL_M3 * P_FACTOR * 1.0 * EVENTS * CH4_FRAC * DENSITY_CH4 / 1000.0

    def _run(self, vol, unit):
        return compute_emissions({
            "process_type": "blowdown",
            "quantity": vol,
            "unit": unit,
            "factor_source": "specific",
            "blowdown_volume": vol,
            "blowdown_pressure": self.PRESSURE_PSIG,
            "blowdown_events": self.EVENTS,
            "ch4_content": self.CH4_FRAC,
        }, {})[0]

    def test_blowdown_m3_reference(self):
        """Reference result using m3."""
        em = self._run(self.BASE_VOL_M3, "m3")
        assert em["ch4"] == pytest.approx(self.EXPECTED_CH4, rel=1e-3), (
            f"Blowdown m3 reference: expected {self.EXPECTED_CH4:.6f}, got {em['ch4']:.6f}"
        )

    def test_blowdown_scf_equivalent_to_m3(self):
        """
        5 m3 = 5 * 35.3147 = 176.573 scf
        Both should give the same result after normalization.
        """
        vol_scf = self.BASE_VOL_M3 * M3_TO_SCF

        em_m3 = self._run(self.BASE_VOL_M3, "m3")
        em_scf = self._run(vol_scf, "scf")

        assert em_scf["ch4"] == pytest.approx(em_m3["ch4"], rel=1e-3), (
            f"scf vs m3: m3={em_m3['ch4']:.6f}, scf={em_scf['ch4']:.6f}\n"
            f"  (5 m3 = {vol_scf:.4f} scf)"
        )

    def test_blowdown_bbl_equivalent_to_m3(self):
        """
        5 m3 = 5 / 0.158987295 = 31.457... bbl
        """
        vol_bbl = self.BASE_VOL_M3 / BBL_TO_M3

        em_m3 = self._run(self.BASE_VOL_M3, "m3")
        em_bbl = self._run(vol_bbl, "bbl")

        assert em_bbl["ch4"] == pytest.approx(em_m3["ch4"], rel=1e-3), (
            f"bbl vs m3: m3={em_m3['ch4']:.6f}, bbl={em_bbl['ch4']:.6f}"
        )


# =====================================================================
# TEST CLASS: Completions Flowback Volume Units
# =====================================================================
class TestCompletionsVolumeUnits:
    """
    Completions metered_volume: 1000 m3 vs 35314.67 scf.
    Reference: ch4 = 1000 * 0.85 * 0.6785 / 1000 = 0.576725 t
    """

    BASE_M3 = 1000.0
    CH4_FRAC = 0.85
    EXPECTED_CH4 = BASE_M3 * CH4_FRAC * DENSITY_CH4 / 1000.0

    def _run(self, qty, unit):
        return compute_emissions({
            "process_type": "completions",
            "quantity": qty,
            "unit": unit,
            "factor_source": "specific",
            "ch4_content": self.CH4_FRAC,
            "comp_method": "metered_volume",
        }, {})[0]

    def test_completions_m3_reference(self):
        """1000 m3 flowback, 85% CH4 = 0.576725 t CH4."""
        em = self._run(self.BASE_M3, "m3")
        assert em["ch4"] == pytest.approx(self.EXPECTED_CH4, rel=1e-3), (
            f"Completions m3: expected {self.EXPECTED_CH4:.6f}, got {em['ch4']:.6f}"
        )

    def test_completions_scf_equivalent_to_m3(self):
        """
        1000 m3 = 35314.67 scf
        After normalization to m3, same CH4 result.
        """
        vol_scf = self.BASE_M3 * M3_TO_SCF

        em_m3 = self._run(self.BASE_M3, "m3")
        em_scf = self._run(vol_scf, "scf")

        assert em_scf["ch4"] == pytest.approx(em_m3["ch4"], rel=1e-3), (
            f"scf vs m3:\n"
            f"  1000 m3 = {vol_scf:.4f} scf\n"
            f"  m3 result: {em_m3['ch4']:.6f} t\n"
            f"  scf result: {em_scf['ch4']:.6f} t"
        )

    def test_completions_mscf_equivalent_to_m3(self):
        """
        1000 m3 = 35.31467 Mscf
        """
        vol_mscf = self.BASE_M3 * M3_TO_SCF / 1000.0

        em_m3 = self._run(self.BASE_M3, "m3")
        em_mscf = self._run(vol_mscf, "mscf")

        assert em_mscf["ch4"] == pytest.approx(em_m3["ch4"], rel=1e-3), (
            f"Mscf vs m3: m3={em_m3['ch4']:.6f}, mscf={em_mscf['ch4']:.6f}"
        )


# =====================================================================
# TEST CLASS: Tank Throughput Volume Units
# =====================================================================
class TestTankThroughputUnits:
    """
    Tank flashing (GOR method): throughput in bbl vs m3.
    The dispatcher converts m3→bbl internally (1 m3 = 6.28981 bbl).

    Reference: 1000 bbl, GOR=100 scf/bbl, ch4=0.85
    total_gas_scf = 100000; ch4_scf = 85000
    ch4_m3 = 85000 * 0.028316846592 = 2406.93 m3
    ch4_tonnes = 2406.93 * 0.6785 / 1000 = 1.633... t
    """

    BASE_BBL = 1000.0
    GOR = 100.0
    CH4_FRAC = 0.85

    TOTAL_GAS_SCF = BASE_BBL * GOR
    CH4_SCF = TOTAL_GAS_SCF * CH4_FRAC
    CH4_M3 = CH4_SCF * SCF_TO_M3
    EXPECTED_CH4 = CH4_M3 * DENSITY_CH4 / 1000.0

    def _run(self, qty, unit):
        return compute_emissions({
            "process_type": "tank",
            "quantity": qty,
            "unit": unit,
            "factor_source": "specific",
            "tank_gor": self.GOR,
            "tank_ch4_content": self.CH4_FRAC,
            "tank_control_eff": 0.0,
        }, {})[0]

    def test_tank_bbl_reference(self):
        """1000 bbl at GOR=100 → EXPECTED_CH4."""
        em = self._run(self.BASE_BBL, "bbl")
        assert em["ch4"] == pytest.approx(self.EXPECTED_CH4, rel=1e-3), (
            f"Tank bbl: expected {self.EXPECTED_CH4:.6f}, got {em['ch4']:.6f}"
        )

    def test_tank_m3_equivalent_to_bbl(self):
        """
        1000 bbl = 1000 * 0.158987295 = 158.987 m3
        Dispatcher converts m3 → bbl internally (×6.28981).
        """
        vol_m3 = self.BASE_BBL * BBL_TO_M3   # 158.987 m3

        em_bbl = self._run(self.BASE_BBL, "bbl")
        em_m3 = self._run(vol_m3, "m3")

        assert em_m3["ch4"] == pytest.approx(em_bbl["ch4"], rel=1e-3), (
            f"m3 vs bbl:\n"
            f"  {self.BASE_BBL} bbl = {vol_m3:.4f} m3\n"
            f"  bbl result: {em_bbl['ch4']:.6f} t\n"
            f"  m3 result: {em_m3['ch4']:.6f} t"
        )

    def test_tank_gal_equivalent_to_bbl(self):
        """
        1000 bbl = 42000 gal (1 bbl = 42 US gal)
        """
        # 1 bbl = 0.158987295 m3; 1 gal = 0.003785411784 m3
        # 1 bbl = 0.158987295 / 0.003785411784 = 42.0 gal
        vol_gal = self.BASE_BBL * (BBL_TO_M3 / GAL_TO_M3)

        em_bbl = self._run(self.BASE_BBL, "bbl")
        em_gal = self._run(vol_gal, "gal")

        assert em_gal["ch4"] == pytest.approx(em_bbl["ch4"], rel=1e-3), (
            f"gal vs bbl:\n"
            f"  {self.BASE_BBL} bbl = {vol_gal:.1f} gal\n"
            f"  bbl={em_bbl['ch4']:.6f} t, gal={em_gal['ch4']:.6f} t"
        )


# =====================================================================
# TEST CLASS: Energy Units for Indirect Steam
# =====================================================================
class TestEnergyUnitsIndirectSteam:
    """
    Indirect steam: 100 MMBtu = 29307.1 kWh (1 MMBtu = 293.071 kWh)
    Both should give the same CO2 when using same EF in kg/MMBtu.

    Reference:
      energy_btu = 100 * 1,000,000 = 100,000,000 BTU
      net_eff = 0.80 * (1 - 0.05) = 0.76
      co2_kg = (energy_btu / 1e6) * 56.1 / 0.76 = 7381.58 kg
      expected_co2 = 7.38158 t
    """

    BOILER_EFF = 0.80
    TRANS_LOSS = 0.05
    EF_CO2_KG_MMBTU = 56.1  # kg/MMBtu (natural gas boiler)
    NET_EFF = BOILER_EFF * (1 - TRANS_LOSS)

    BASE_MMBTU = 100.0
    EXPECTED_CO2 = (BASE_MMBTU * EF_CO2_KG_MMBTU / NET_EFF) / 1000.0

    def _run_indirect(self, qty, unit):
        payload = {
            "process_type": "indirect_steam",
            "quantity": qty,
            "unit": unit,
            "factor_source": "specific",
            "heat_output": qty,
            "heat_unit": unit,
            "boiler_eff": self.BOILER_EFF,
            "trans_loss": self.TRANS_LOSS,
            "total_emissions": 0.0,
        }
        factor_data = {
            "co2": self.EF_CO2_KG_MMBTU,
            "ch4": 0.0,
            "n2o": 0.0,
            "unit": "kg/mmbtu",
        }
        return compute_emissions(payload, factor_data)[0]

    def test_indirect_steam_mmbtu_reference(self):
        """100 MMBtu → EXPECTED_CO2 tonnes."""
        em = self._run_indirect(self.BASE_MMBTU, "mmbtu")
        assert em["co2"] == pytest.approx(self.EXPECTED_CO2, rel=1e-3), (
            f"MMBtu reference: expected {self.EXPECTED_CO2:.6f}, got {em['co2']:.6f}"
        )

    def test_indirect_steam_btu_equivalent_to_mmbtu(self):
        """
        100 MMBtu = 100,000,000 BTU
        Both should give the same CO2 (IndirectSteamCalculator normalizes to BTU internally).
        """
        qty_btu = self.BASE_MMBTU * 1_000_000.0

        em_mmbtu = self._run_indirect(self.BASE_MMBTU, "mmbtu")
        em_btu = self._run_indirect(qty_btu, "btu")

        assert em_btu["co2"] == pytest.approx(em_mmbtu["co2"], rel=1e-3), (
            f"BTU vs MMBtu:\n"
            f"  mmbtu result: {em_mmbtu['co2']:.6f} t\n"
            f"  btu result: {em_btu['co2']:.6f} t"
        )

    def test_indirect_steam_kwh_equivalent_to_mmbtu(self):
        """
        100 MMBtu = 100 * 1e6 BTU / 3412.142 BTU/kWh = 29307.1 kWh
        Formula (IndirectSteamCalculator): energy_btu = kwh * 3412.142
        """
        kwh_per_mmbtu = 1_000_000.0 / 3412.142    # BTU per MMBtu / BTU per kWh
        qty_kwh = self.BASE_MMBTU * kwh_per_mmbtu  # 29307.1... kWh

        em_mmbtu = self._run_indirect(self.BASE_MMBTU, "mmbtu")
        em_kwh = self._run_indirect(qty_kwh, "kwh")

        assert em_kwh["co2"] == pytest.approx(em_mmbtu["co2"], rel=1e-3), (
            f"kWh vs MMBtu:\n"
            f"  {self.BASE_MMBTU} MMBtu = {qty_kwh:.2f} kWh\n"
            f"  mmbtu result: {em_mmbtu['co2']:.6f} t\n"
            f"  kwh result: {em_kwh['co2']:.6f} t"
        )

    def test_indirect_steam_mwh_equivalent_to_kwh(self):
        """
        1 MWh = 1000 kWh → scaling test.
        29307.1 kWh = 29.307 MWh → same CO2.
        """
        kwh_per_mmbtu = 1_000_000.0 / 3412.142
        qty_kwh = self.BASE_MMBTU * kwh_per_mmbtu
        qty_mwh = qty_kwh / 1000.0

        em_kwh = self._run_indirect(qty_kwh, "kwh")
        em_mwh = self._run_indirect(qty_mwh, "mwh")

        assert em_mwh["co2"] == pytest.approx(em_kwh["co2"], rel=1e-3), (
            f"MWh vs kWh: kwh={em_kwh['co2']:.6f}, mwh={em_mwh['co2']:.6f}"
        )


# =====================================================================
# TEST CLASS: Combustion Factor Unit Conversions
# The dispatcher's convert_factor_to_kg_per_unit() handles EF unit conversion.
# For combustion Tier 1: test that the same physical result is obtained
# regardless of how the EF and quantity units are paired.
# =====================================================================
class TestCombustionFactorUnits:
    """
    Combustion Tier 1: validate that different EF unit representations
    give the same final emission result.

    Reference:
      1000 m3 natural gas, EF_co2 = 1.9 kg/m3
      expected_co2 = 1000 * 1.9 / 1000 = 1.9 tonnes
    """

    def test_combustion_kg_per_m3_reference(self):
        """Direct: 1000 m3 * 1.9 kg/m3 = 1.9 t CO2."""
        payload = {
            "process_type": "combustion",
            "quantity": 1000.0,
            "unit": "m3",
            "factor_source": "default",
        }
        factor_data = {"co2": 1.9, "ch4": 0.0, "n2o": 0.0, "unit": "kg/m3", "hhv": 1020.0}
        em, _ = compute_emissions(payload, factor_data)
        assert em["co2"] == pytest.approx(1.9, rel=1e-4)

    def test_combustion_double_quantity_double_result(self):
        """
        Unit conversion consistency via linearity:
        2000 m3 should give exactly double 1000 m3 emissions.
        """
        factor_data = {"co2": 1.9, "ch4": 0.00004, "n2o": 0.000002, "unit": "kg/m3", "hhv": 1020.0}

        def run_combustion(qty):
            return compute_emissions({
                "process_type": "combustion", "quantity": qty,
                "unit": "m3", "factor_source": "default"
            }, factor_data)[0]

        em_1000 = run_combustion(1000.0)
        em_2000 = run_combustion(2000.0)

        assert em_2000["co2"] == pytest.approx(2 * em_1000["co2"], rel=1e-6)
        assert em_2000["ch4"] == pytest.approx(2 * em_1000["ch4"], rel=1e-6)
        assert em_2000["n2o"] == pytest.approx(2 * em_1000["n2o"], rel=1e-6)
        assert em_2000["totalCo2e"] == pytest.approx(2 * em_1000["totalCo2e"], rel=1e-6)


# =====================================================================
# TEST CLASS: Pneumatic Device Unit Validation
# =====================================================================
class TestPneumaticBleedRateUnits:
    """
    Pneumatic bleed rate: 5 scf/hr expressed in m3/hr
    5 scf/hr = 5 * 0.028316846592 = 0.14158... m3/hr
    Both should give the same CH4 result.
    """

    COUNT = 10.0
    HOURS = 8760.0
    BLEED_RATE_SCF = 5.0
    CH4_FRAC = 0.85

    # INDEPENDENT REFERENCE
    BLEED_M3_HR = BLEED_RATE_SCF * SCF_TO_M3
    EXPECTED_CH4 = COUNT * HOURS * BLEED_M3_HR * CH4_FRAC * DENSITY_CH4 / 1000.0

    def test_pneumatic_scf_reference(self):
        """10 devices, 8760 hr, 5 scf/hr, 85% CH4."""
        payload = {
            "process_type": "pneumatic_devices",
            "quantity": self.COUNT,
            "unit": "m3",
            "factor_source": "specific",
            "pneu_count": self.COUNT,
            "pneu_hours": self.HOURS,
            "pneu_bleed_rate": self.BLEED_RATE_SCF,
            "pneu_bleed_unit": "scf",
            "pneu_ch4_content": self.CH4_FRAC,
        }
        em, _ = compute_emissions(payload, {})
        assert em["ch4"] == pytest.approx(self.EXPECTED_CH4, rel=1e-3), (
            f"Pneumatic scf: expected {self.EXPECTED_CH4:.6f}, got {em['ch4']:.6f}\n"
            f"  bleed_m3_hr={self.BLEED_M3_HR:.8f}"
        )

    def test_pneumatic_hours_scale(self):
        """
        Halving hours → exactly half CH4.
        Reference: 4380 hr vs 8760 hr.
        """
        def run_pneumatic(hours):
            return compute_emissions({
                "process_type": "pneumatic_devices",
                "quantity": self.COUNT, "unit": "m3",
                "factor_source": "specific",
                "pneu_count": self.COUNT, "pneu_hours": hours,
                "pneu_bleed_rate": self.BLEED_RATE_SCF,
                "pneu_bleed_unit": "scf",
                "pneu_ch4_content": self.CH4_FRAC,
            }, {})[0]

        em_full = run_pneumatic(8760.0)
        em_half = run_pneumatic(4380.0)

        assert em_half["ch4"] == pytest.approx(em_full["ch4"] / 2.0, rel=1e-6), (
            f"Half hours: expected {em_full['ch4']/2:.6f}, got {em_half['ch4']:.6f}"
        )


# =====================================================================
# TEST CLASS: Volume Round-Trip Conversion Accuracy
# =====================================================================
class TestVolumeRoundTrip:
    """
    Verify unit conversion math is consistent:
    m3 → scf → m3 should return original value (within float precision).
    """

    def test_scf_to_m3_round_trip(self):
        """scf × SCF_TO_M3 × M3_TO_SCF ≈ scf (round trip)."""
        original_scf = 10000.0
        m3 = original_scf * SCF_TO_M3
        back_to_scf = m3 * M3_TO_SCF
        assert back_to_scf == pytest.approx(original_scf, rel=1e-10)

    def test_bbl_to_m3_round_trip(self):
        """bbl × BBL_TO_M3 / BBL_TO_M3 = original bbl."""
        original_bbl = 500.0
        m3 = original_bbl * BBL_TO_M3
        back_to_bbl = m3 / BBL_TO_M3
        assert back_to_bbl == pytest.approx(original_bbl, rel=1e-10)

    def test_gal_to_m3_round_trip(self):
        """gal × GAL_TO_M3 / GAL_TO_M3 = original gal."""
        original_gal = 42000.0
        m3 = original_gal * GAL_TO_M3
        back_to_gal = m3 / GAL_TO_M3
        assert back_to_gal == pytest.approx(original_gal, rel=1e-10)

    def test_1_bbl_equals_42_gallons(self):
        """Standard petroleum: 1 bbl = exactly 42 US gallons."""
        bbl_in_m3 = BBL_TO_M3
        gal_in_m3 = GAL_TO_M3
        ratio = bbl_in_m3 / gal_in_m3
        assert ratio == pytest.approx(42.0, rel=1e-6)

    def test_scf_m3_factor_consistency(self):
        """SCF_TO_M3 × M3_TO_SCF must equal 1.0 (inverse relationship)."""
        product = SCF_TO_M3 * M3_TO_SCF
        assert product == pytest.approx(1.0, rel=1e-8)
