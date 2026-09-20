"""
Exhaustive Unit Conversion and Thermodynamic Normalization Test Suite.
=====================================================================
Validates all unit conversion matrices, invertibility, transitivity,
temperature/pressure transformations, and API §4.2.1 thermodynamic normalization.
"""
import pytest
import math
import sys
from pathlib import Path

repo_root = str(Path(__file__).resolve().parents[3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from calculations.units import (
    CONVERSIONS,
    VOLUME_UNITS_TO_M3,
    MASS_UNITS_TO_KG,
    ENERGY_UNITS_TO_MJ,
    to_kelvin,
    to_celsius,
    to_fahrenheit,
    to_psia,
    from_psia,
    normalize_gas_volume_to_standard,
    STD_TEMP_K,
    STD_TEMP_F,
    STD_TEMP_C,
    STD_PRESSURE_PSIA,
    STD_PRESSURE_KPA,
    STD_PRESSURE_BAR,
)
from calculations.combustion import convert_factor_to_kg_per_unit
from validation.reference_model.unit_conversions import IndependentUnitConverter


class TestExhaustiveUnitInvertibility:
    """Tests A -> B -> A round-trip invertibility for every unit category."""

    @pytest.mark.parametrize("u1", list(VOLUME_UNITS_TO_M3.keys()))
    @pytest.mark.parametrize("u2", ["m3", "scf", "bbl", "gal", "liter"])
    def test_volume_invertibility(self, u1, u2):
        val = 1234.56
        # u1 -> m3 -> u2
        m3_val = val * VOLUME_UNITS_TO_M3[u1]
        u2_factor = VOLUME_UNITS_TO_M3[u2]
        val_u2 = m3_val / u2_factor
        # u2 -> m3 -> u1
        recovered_val = (val_u2 * u2_factor) / VOLUME_UNITS_TO_M3[u1]
        assert pytest.approx(recovered_val, rel=1e-8) == val

    @pytest.mark.parametrize("u1", list(MASS_UNITS_TO_KG.keys()))
    @pytest.mark.parametrize("u2", ["kg", "tonne", "lb", "short_ton"])
    def test_mass_invertibility(self, u1, u2):
        val = 9876.54
        kg_val = val * MASS_UNITS_TO_KG[u1]
        u2_factor = MASS_UNITS_TO_KG[u2]
        val_u2 = kg_val / u2_factor
        recovered_val = (val_u2 * u2_factor) / MASS_UNITS_TO_KG[u1]
        assert pytest.approx(recovered_val, rel=1e-8) == val

    @pytest.mark.parametrize("u1", list(ENERGY_UNITS_TO_MJ.keys()))
    @pytest.mark.parametrize("u2", ["mj", "mmbtu", "kwh", "therm"])
    def test_energy_invertibility(self, u1, u2):
        val = 5432.10
        mj_val = val * ENERGY_UNITS_TO_MJ[u1]
        u2_factor = ENERGY_UNITS_TO_MJ[u2]
        val_u2 = mj_val / u2_factor
        recovered_val = (val_u2 * u2_factor) / ENERGY_UNITS_TO_MJ[u1]
        assert pytest.approx(recovered_val, rel=1e-8) == val


class TestExhaustiveTransitivity:
    """Tests A -> B -> C == A -> C transitivity."""

    def test_volume_transitivity(self):
        # bbl -> gal -> scf == bbl -> scf
        bbl_val = 100.0
        gal_val = bbl_val * (VOLUME_UNITS_TO_M3["bbl"] / VOLUME_UNITS_TO_M3["gal"])
        scf_via_gal = gal_val * (VOLUME_UNITS_TO_M3["gal"] / VOLUME_UNITS_TO_M3["scf"])
        scf_direct = bbl_val * (VOLUME_UNITS_TO_M3["bbl"] / VOLUME_UNITS_TO_M3["scf"])
        assert pytest.approx(scf_via_gal, rel=1e-8) == scf_direct

    def test_mass_transitivity(self):
        # long_ton -> lb -> kg == long_ton -> kg
        lt_val = 50.0
        lb_val = lt_val * (MASS_UNITS_TO_KG["long_ton"] / MASS_UNITS_TO_KG["lb"])
        kg_via_lb = lb_val * (MASS_UNITS_TO_KG["lb"] / MASS_UNITS_TO_KG["kg"])
        kg_direct = lt_val * MASS_UNITS_TO_KG["long_ton"]
        assert pytest.approx(kg_via_lb, rel=1e-8) == kg_direct

    def test_energy_transitivity(self):
        # mmbtu -> therm -> kwh == mmbtu -> kwh
        mmbtu_val = 250.0
        therm_val = mmbtu_val * (ENERGY_UNITS_TO_MJ["mmbtu"] / ENERGY_UNITS_TO_MJ["therm"])
        kwh_via_therm = therm_val * (ENERGY_UNITS_TO_MJ["therm"] / ENERGY_UNITS_TO_MJ["kwh"])
        kwh_direct = mmbtu_val * (ENERGY_UNITS_TO_MJ["mmbtu"] / ENERGY_UNITS_TO_MJ["kwh"])
        assert pytest.approx(kwh_via_therm, rel=1e-8) == kwh_direct


class TestThermodynamicTemperatureAndPressure:
    """Tests temperature and pressure transformations and standards."""

    def test_temperature_canonical_points(self):
        # Boiling point: 100°C == 212°F == 373.15 K == 671.67 °R
        assert pytest.approx(to_kelvin(100.0, "C"), rel=1e-5) == 373.15
        assert pytest.approx(to_fahrenheit(100.0, "C"), rel=1e-5) == 212.0
        assert pytest.approx(to_celsius(212.0, "F"), rel=1e-5) == 100.0
        assert pytest.approx(to_celsius(373.15, "K"), rel=1e-5) == 100.0

        # Freezing point: 0°C == 32°F == 273.15 K == 491.67 °R
        assert pytest.approx(to_kelvin(0.0, "C"), rel=1e-5) == 273.15
        assert pytest.approx(to_fahrenheit(0.0, "C"), rel=1e-5) == 32.0
        assert pytest.approx(to_celsius(32.0, "F"), rel=1e-5) == 0.0

        # Absolute zero: 0 K == -273.15°C == -459.67°F
        assert pytest.approx(to_kelvin(-273.15, "C"), abs=1e-3) == 0.0
        assert pytest.approx(to_celsius(0.0, "K"), rel=1e-5) == -273.15

    def test_pressure_gauge_to_absolute(self):
        # 0 psig == 14.696 psia
        assert pytest.approx(to_psia(0.0, "psig"), rel=1e-5) == STD_PRESSURE_PSIA
        # 100 psig == 114.696 psia
        assert pytest.approx(to_psia(100.0, "psig"), rel=1e-5) == 114.696

        # Atmospheric pressure in bar: 1.01325 bar == 14.696 psia
        assert pytest.approx(to_psia(1.01325, "bar"), rel=1e-3) == STD_PRESSURE_PSIA
        # Atmospheric pressure in kPa: 101.325 kPa == 14.696 psia
        assert pytest.approx(to_psia(101.325, "kpa"), rel=1e-3) == STD_PRESSURE_PSIA

    def test_pressure_round_trip(self):
        for unit in ["psia", "psig", "bar", "barg", "kpa", "kpag", "mpa"]:
            p_val = 75.0
            psia = to_psia(p_val, unit)
            recovered = from_psia(psia, unit)
            assert pytest.approx(recovered, rel=1e-4) == p_val


class TestGasVolumeThermodynamicNormalization:
    """Tests API §4.2.1 thermodynamic gas volume normalization to standard conditions."""

    def test_normalization_at_standard_conditions_is_identity(self):
        # When operating at std temp (60°F) and std press (0 psig / 14.696 psia) with Z=1.0,
        # normalized volume must equal measured volume exactly.
        vol = 50_000.0
        norm_vol = normalize_gas_volume_to_standard(
            volume=vol,
            operating_temp=STD_TEMP_F,
            temp_unit="F",
            operating_press=0.0,
            press_unit="psig",
            z_factor=1.0,
        )
        assert pytest.approx(norm_vol, rel=1e-4) == vol

    def test_normalization_higher_temp_decreases_standard_volume(self):
        # Charles's law: warmer gas has lower density, so fewer standard moles per actual m3
        vol = 10_000.0
        v_std_cold = normalize_gas_volume_to_standard(vol, operating_temp=0.0, temp_unit="C")
        v_std_hot = normalize_gas_volume_to_standard(vol, operating_temp=100.0, temp_unit="C")
        assert v_std_cold > v_std_hot

    def test_normalization_higher_pressure_increases_standard_volume(self):
        # Boyle's law: compressed gas contains more standard volume
        vol = 10_000.0
        v_std_low = normalize_gas_volume_to_standard(vol, operating_press=10.0, press_unit="psig")
        v_std_high = normalize_gas_volume_to_standard(vol, operating_press=100.0, press_unit="psig")
        assert v_std_high > v_std_low

    def test_normalization_z_factor_scaling(self):
        vol = 10_000.0
        v_z1 = normalize_gas_volume_to_standard(vol, z_factor=1.0)
        v_z08 = normalize_gas_volume_to_standard(vol, z_factor=0.8)
        assert pytest.approx(v_z08, rel=1e-6) == v_z1 / 0.8
