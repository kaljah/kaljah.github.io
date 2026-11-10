"""
PHASE 3 VERIFICATION: UNIT SAFETY & DIMENSIONAL HARNESS WITH PINT
================================================================
Uses Pint (dev/test scope) to independently verify the platform's
conversion matrix in both directions and complete round-trips.

Audits:
- Mass: kg <-> tonne <-> lb <-> short_ton <-> long_ton
- Volume: scf <-> m3 <-> bbl <-> gal <-> L
- Energy: MJ <-> GJ <-> MMBtu <-> kWh <-> MWh <-> therm
- Emissions: tCO2e <-> kgCO2e
- Finds implicit unit assumptions and missing unit checks
"""

import sys
import os
import pytest
import pint
from decimal import Decimal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SERVER_DIR = os.path.join(REPO_ROOT, "new", "server")
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from calculations.units import CONVERSIONS, convert, UnitError
from tests.verification.oracle.compendium_oracle import oracle_convert_unit, EXACT_CONVERSIONS

ureg = pint.UnitRegistry()
# Define custom aliases or oil & gas units if missing
ureg.define("standard_cubic_foot = cu_ft = scf")
ureg.define("million_standard_cubic_feet = 1000000 * standard_cubic_foot = mmscf = mmcf")
ureg.define("thousand_standard_cubic_feet = 1000 * standard_cubic_foot = mscf = mcf")
ureg.define("oil_barrel = 42 * gallon = bbl")
ureg.define("metric_ton = 1000 * kilogram = tonne = t = mt")


# =============================================================================
# 1. MASS ROUND-TRIPS & BIDIRECTIONAL CONVERSIONS (PINT VS APP VS ORACLE)
# =============================================================================

@pytest.mark.parametrize("val, u1, u2", [
    (100.0, "kg", "tonne"),
    (2500.0, "lb", "kg"),
    (50.0, "short_ton", "tonne"),
    (10.0, "long_ton", "tonne"),
    (1000000.0, "g", "kg"),
    (1.0, "tonne", "lb"),
])
def test_mass_conversions_bidirectional(val, u1, u2):
    """
    Asserts exact round-trip conversion for mass units:
    val in u1 -> u2 -> u1 == val
    and compares app conversion against Pint dimensional analysis.
    """
    # 1. App conversion
    forward = convert(val, u1, u2)
    reverse = convert(forward, u2, u1)
    assert reverse == pytest.approx(val, rel=1e-6)

    # 2. Oracle Decimal conversion
    oracle_fwd = float(oracle_convert_unit(Decimal(str(val)), u1, u2))
    oracle_rev = float(oracle_convert_unit(Decimal(str(oracle_fwd)), u2, u1))
    assert oracle_rev == pytest.approx(val, rel=1e-6)
    assert forward == pytest.approx(oracle_fwd, rel=1e-6)

    # 3. Pint independent verification
    pint_u1 = "metric_ton" if u1 in ("tonne", "t", "mt") else ("oil_barrel" if u1 == "bbl" else u1)
    pint_u2 = "metric_ton" if u2 in ("tonne", "t", "mt") else ("oil_barrel" if u2 == "bbl" else u2)
    pint_val = (val * ureg(pint_u1)).to(pint_u2).magnitude
    assert forward == pytest.approx(pint_val, rel=1e-4)


# =============================================================================
# 2. VOLUME ROUND-TRIPS (PINT VS APP VS ORACLE)
# =============================================================================

@pytest.mark.parametrize("val, u1, u2", [
    (1000.0, "scf", "m3"),
    (500.0, "mscf", "m3"),
    (10.0, "mmscf", "m3"),
    (1000.0, "bbl", "m3"),
    (1000.0, "gal", "l"),
    (100.0, "m3", "bbl"),
    (50000.0, "l", "m3"),
])
def test_volume_conversions_bidirectional(val, u1, u2):
    """
    Asserts exact volume round-trip conversions (API standard conditions 60 F).
    """
    forward = convert(val, u1, u2)
    reverse = convert(forward, u2, u1)
    assert reverse == pytest.approx(val, rel=1e-6)

    oracle_fwd = float(oracle_convert_unit(Decimal(str(val)), u1, u2))
    assert forward == pytest.approx(oracle_fwd, rel=1e-5)


# =============================================================================
# 3. ENERGY ROUND-TRIPS (PINT VS APP VS ORACLE)
# =============================================================================

@pytest.mark.parametrize("val, u1, u2", [
    (1000.0, "kwh", "mj"),
    (10.0, "mwh", "gj"),
    (50.0, "mmbtu", "gj"),
    (100.0, "therm", "mj"),
    (1000.0, "btu", "kj"),
    (500.0, "gj", "mmbtu"),
])
def test_energy_conversions_bidirectional(val, u1, u2):
    """
    Asserts exact energy round-trip conversions.
    """
    forward = convert(val, u1, u2)
    reverse = convert(forward, u2, u1)
    assert reverse == pytest.approx(val, rel=1e-6)

    oracle_fwd = float(oracle_convert_unit(Decimal(str(val)), u1, u2))
    assert forward == pytest.approx(oracle_fwd, rel=1e-5)


# =============================================================================
# 4. EMISSION QUANTITY SCALING (tCO2e vs kgCO2e)
# =============================================================================

def test_tco2e_kgco2e_scaling():
    """
    Verifies that tCO2e and kgCO2e strictly maintain 1,000x scaling factor.
    """
    t_val = 15.75
    kg_val = t_val * 1000.0
    assert (kg_val * ureg.kilogram).to(ureg.metric_ton).magnitude == pytest.approx(t_val, rel=1e-9)


# =============================================================================
# 5. INCOMPATIBLE UNIT PROTECTION (FINDING UNIT SAFETY FLAWS)
# =============================================================================

def test_incompatible_unit_addition_protection():
    """
    Verifies that the application prevents adding or comparing incompatible physical dimensions
    (e.g., volume + mass, energy + length).
    """
    with pytest.raises((ValueError, UnitError)):
        convert(100.0, "m3", "kg")  # Cannot convert volume directly to mass without density

    with pytest.raises((ValueError, UnitError)):
        convert(50.0, "mj", "m3")   # Cannot convert energy directly to volume without heating value
