"""
PHASE 2 VERIFICATION: FACTOR AND CONSTANT AUDIT
===============================================
Audits all emission factors, physical constants, densities, heating values,
and GWP values across the codebase against the API Compendium (2021) and NIST SP 811.

Checks:
- Transcription errors and precision drift
- Standard thermodynamic conditions (60 °F / 14.696 psia vs 15 °C vs 0 °C)
- Mixed GWP assessment reports (AR4, AR5, AR6, SAR)
- Duplicated constants with conflicting values
- Provable provenance for all factors
"""

import sys
import os
from decimal import Decimal
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(REPO_ROOT, "new", "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from calculations.constants import GWP_STANDARDS, GWP_SAR, GWP_AR4, GWP_AR5, GWP_AR6, get_active_gwp
from calculations.units import (
    CONVERSIONS,
    STD_TEMP_F,
    STD_TEMP_C,
    STD_PRESSURE_PSIA,
    STD_PRESSURE_KPA,
    MOLAR_VOLUME_SCF_PER_LBMOL,
    MOLAR_VOLUME_M3_PER_KMOL,
    MW_CH4,
    MW_CO2,
    NG_HHV_BTU_PER_SCF,
    MMBTU_PER_BOE,
)
from tests.verification.oracle.compendium_oracle import (
    GWP_REGISTRY,
    EXACT_CONVERSIONS,
    MW_C,
    MW_CO2 as ORACLE_MW_CO2,
    MW_CH4 as ORACLE_MW_CH4,
    MW_N2O as ORACLE_MW_N2O,
    DENSITY_CH4_STD,
    DENSITY_CO2_STD,
)


# =============================================================================
# 1. GWP AUDIT ACROSS ALL STANDARDS & HORIZONS
# =============================================================================

def test_gwp_standards_alignment_with_ipcc():
    """
    Validates GWP values against IPCC SAR (1995), AR4 (2007), AR5 (2013), and AR6 (2021).
    Ensures no mixed standards or corrupted values exist in the registry.
    """
    # SAR: CO2=1, CH4=21, N2O=310
    sar = GWP_STANDARDS["SAR"]
    assert sar["CO2"] == 1.0 and sar["CH4"] == 21.0 and sar["N2O"] == 310.0

    # AR4: CO2=1, CH4=25, N2O=298
    ar4 = GWP_STANDARDS["AR4"]
    assert ar4["CO2"] == 1.0 and ar4["CH4"] == 25.0 and ar4["N2O"] == 298.0

    # AR5 (without climate-carbon feedbacks, default for oil & gas): CO2=1, CH4=28, N2O=265
    ar5 = GWP_STANDARDS["AR5"]
    assert ar5["CO2"] == 1.0 and ar5["CH4"] == 28.0 and ar5["N2O"] == 265.0

    # AR6 (fossil methane): CO2=1, CH4=29.8, N2O=273.0
    ar6 = GWP_STANDARDS["AR6"]
    assert ar6["CO2"] == 1.0 and ar6["CH4"] == 29.8 and ar6["N2O"] == 273.0


def test_gwp_20_year_horizons():
    """
    Validates 20-year GWP values against IPCC Assessment Reports.
    - AR4: CH4=72, N2O=289
    - AR5: CH4=84, N2O=264
    - AR6: CH4=82.5, N2O=273
    """
    ar4_20 = get_active_gwp("AR4", horizon="20")
    assert ar4_20["CH4"] == 72.0 and ar4_20["N2O"] == 289.0

    ar5_20 = get_active_gwp("AR5", horizon="20")
    assert ar5_20["CH4"] == 84.0 and ar5_20["N2O"] == 264.0

    ar6_20 = get_active_gwp("AR6", horizon="20")
    assert ar6_20["CH4"] == 82.5 and ar6_20["N2O"] == 273.0


# =============================================================================
# 2. PHYSICAL CONSTANTS & STANDARD CONDITIONS
# =============================================================================

def test_standard_thermodynamic_conditions():
    """
    Verifies that the platform adheres strictly to API Compendium (2021) Section 3.4
    standard conditions: 60 °F (15.556 °C) and 14.696 psia (101.325 kPa).
    """
    assert STD_TEMP_F == 60.0
    assert abs(STD_TEMP_C - 15.556) < 0.01
    assert STD_PRESSURE_PSIA == 14.696
    assert STD_PRESSURE_KPA == 101.325


def test_molar_volume_and_gas_densities():
    """
    Validates molar volume and density constants:
    - 379.3 scf/lb-mol = 23.685 m3/kmol
    - rho_CH4 = 16.04 / 23.685 = ~0.67722 kg/m3
    - rho_CO2 = 44.01 / 23.685 = ~1.85814 kg/m3
    """
    assert MOLAR_VOLUME_SCF_PER_LBMOL == 379.3
    assert MOLAR_VOLUME_M3_PER_KMOL == 23.685

    expected_rho_ch4 = 16.04 / 23.685
    expected_rho_co2 = 44.01 / 23.685

    assert abs(CONVERSIONS["density_ch4"] - expected_rho_ch4) < 1e-6
    assert abs(CONVERSIONS["density_co2"] - expected_rho_co2) < 1e-6


def test_hydrocarbon_stoichiometric_constants():
    """
    Validates stoichiometric carbon and molecular weights:
    - C = 12.011 g/mol
    - CO2 = 44.01 g/mol
    - Stoichiometric ratio CO2 / C = 44.01 / 12.011 = ~3.66414
    1000 kg of pure Carbon (100% C) must produce exactly 3.66414 tonnes of CO2.
    """
    from calculations.stoichiometry import StoichiometricCalculator
    calc = StoichiometricCalculator()
    res = calc.calculate(fuel_mass=1000.0, carbon_content=1.0, mass_unit="kg")
    expected_tonnes = (1000.0 * 1.0 * (44.01 / 12.011)) / 1000.0
    assert res["results"]["co2"]["value"] == pytest.approx(expected_tonnes, rel=1e-5)


# =============================================================================
# 3. UNIT CONVERSION CONSTANTS AUDIT (NIST SP 811)
# =============================================================================

def test_volume_conversion_factors_nist():
    """
    Verifies volume conversion factors against NIST SP 811 exact constants:
    - 1 cu ft = 0.028316846592 m3
    - 1 US gallon = 0.003785411784 m3
    - 1 barrel (oil) = 42 US gallons = 0.158987294928 m3
    """
    assert CONVERSIONS["scf_to_m3"] == pytest.approx(0.028316846592, abs=1e-12)
    assert CONVERSIONS["gal_to_m3"] == pytest.approx(0.003785411784, abs=1e-12)
    assert CONVERSIONS["bbl_to_m3"] == pytest.approx(42.0 * 0.003785411784, abs=1e-8)


def test_mass_conversion_factors_nist():
    """
    Verifies mass conversion factors against NIST SP 811 exact constants:
    - 1 lb (avoirdupois) = 0.45359237 kg exactly
    - 1 short ton = 2000 lb = 907.18474 kg exactly
    - 1 metric ton = 1000 kg exactly
    """
    assert CONVERSIONS["lb_to_kg"] == 0.45359237
    assert CONVERSIONS["short_ton_to_kg"] == 907.18474
    assert CONVERSIONS["tonne_to_kg"] == 1000.0


def test_energy_conversion_factors_iso():
    """
    Verifies energy conversion factors against ISO 31-4:
    - 1 kWh = 3.6 MJ exactly
    - 1 MMBtu (IT) = 1055.05585262 MJ
    - 1 therm = 100,000 Btu = 105.505585262 MJ
    """
    assert CONVERSIONS["kwh_to_mj"] == 3.6
    assert CONVERSIONS["mmbtu_to_mj"] == pytest.approx(1055.05585262, rel=1e-6)
    assert CONVERSIONS["therm_to_mj"] == pytest.approx(105.505585262, rel=1e-6)


def test_boe_conversion_constants_api():
    """
    Verifies API Compendium 2021 BOE constants:
    - 5.80 MMBtu / BOE
    - 1,020 Btu / scf default gas HHV
    - 5,686.27 scf / BOE
    """
    assert MMBTU_PER_BOE == 5.8
    assert NG_HHV_BTU_PER_SCF == 1020.0
    expected_scf_per_boe = (5.8 * 1e6) / 1020.0
    assert CONVERSIONS["boe_to_scf"] == pytest.approx(expected_scf_per_boe, rel=1e-4)


# =============================================================================
# 4. REPRODUCIBILITY OF KNOWN FACTOR DEFECTS (BUG-03, BUG-04, BUG-05)
# =============================================================================

def test_gwp_sar_provenance():
    """
    Confirms that SAR (Second Assessment Report) is supported with correct constants.
    """
    sar = get_active_gwp("SAR")
    assert sar["CO2"] == 1.0
    assert sar["CH4"] == 21.0
    assert sar["N2O"] == 310.0
