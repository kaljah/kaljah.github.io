"""
API Compendium 2021 - Section 6.3: Oil and Natural Gas Production
Vented and Process Emissions Calculation Modules

Governing Standard:
API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry
4th Edition, November 2021, Section 6.3 & Associated Appendices:
- §6.3.1 Associated Gas Venting (Table 6-8, Exhibit 6-6)
- §6.3.2 Workovers without Hydraulic Fracturing (Table 6-9, Exhibit 6-7)
- §6.3.3 Workovers with Hydraulic Fracturing (Table 6-5, Table 6-7)
- §6.3.4 Liquids Unloading (Table 6-10, Table 6-11, Equations 6-8 to 6-13, Exhibit 6-8)
- §6.3.5 Casing Gas Vents (Table 6-12, Table 6-13, §6.3.5.2, Exhibit 6-9, Exhibit 6-10)
- §6.3.6 Natural Gas-Driven Pneumatic Controllers (Table 6-14, Table 6-15, Eq 6-12 to 6-14, Exhibits 6-11 & 6-12)
- §6.3.7 Gas-Driven Pneumatic Pumps / Chemical Injection (Table 6-16, Eq 6-15, Eq 6-16, Exhibit 6-13)
- §6.3.8 Gas Treatment: Glycol & Desiccant Dehydration, Acid Gas Removal (Table 6-17 to 6-19, Eq 6-17 to 6-19, Exhibits 6-13 to 6-17)
- §6.3.9 Hydrocarbon & Produced Water Storage Tanks: Flashing (VBE Eq 6-20/6-21, Standing Eq 6-22/6-23, EUB Eq 6-24,
  Table 6-20 to 6-27, Dump Valve Eq 6-25, Exhibits 6-18a/b/c, 6-20, 6-21)
- §6.3.10 CO2 Enhanced Oil Recovery (EOR) Operations (Eq 6-26, Eq 6-27, Exhibit 6-22)
- §6.3.11 Other Production Non-Routine Venting: PRV, ESD (Eq 6-28, Table 6-28)
- Blowdowns: Equipment & Process Blowdowns (Eq 6-30 to 6-33, Table 6-32, Exhibit 6-25)
"""

import math
from .base import BaseCalculator
from .units import (
    CONVERSIONS,
    STD_PRESSURE_PSIA,
    STD_TEMP_K,
    STD_TEMP_R,
    convert,
    to_psia,
    to_kelvin,
    calculate_co2e,
    normalize_efficiency,
)
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
)
from .constants import DEFAULT_GWP, get_active_gwp

# One gas-density convention with the rest of the engine (units.CONVERSIONS): scf -> m3 -> kg
SCF_TO_M3 = 0.028316846592

# Thermodynamic constants under standard conditions (60°F / 14.696 psia; 15.56°C / 101.325 kPa)
MOLAR_VOL_US = 379.3   # scf / lb-mole
MOLAR_VOL_SI = 23.685  # Sm³ / kg-mole
MW_CH4 = 16.04
MW_CO2 = 44.01
MW_N2O = 44.013
LB_PER_TONNE = 2204.6226218487757
R_GAS_US = 10.7316  # psi * ft³ / (lb-mole * °R)
R_GAS_SI = 8.31446  # kPa * m³ / (kg-mole * K)


def _split_vent_flare(total_gas_m3, ch4_tonnes, co2_tonnes, ctrl_eff=0.0, hhv=1020.0, ef_n2o=None):
    """
    Decision D-01: Partitions gross gas into vented and flared fractions.
    Flared gas: 98% CH4 combustion efficiency, native CO2 pass-through,
    2% unburnt CH4 slip, and N2O from flared MMBtu.
    """
    ctrl = normalize_efficiency(ctrl_eff, default=0.0)
    vented_frac = 1.0 - ctrl

    vented_ch4 = ch4_tonnes * vented_frac
    vented_co2 = co2_tonnes * vented_frac

    flared_co2 = 0.0
    flared_unburnt_ch4 = 0.0
    flared_n2o = 0.0

    if ctrl > 0:
        flared_ch4_mass = ch4_tonnes * ctrl
        flared_native_co2 = co2_tonnes * ctrl

        flared_ch4_combusted = flared_ch4_mass * 0.98
        flared_co2 = (flared_ch4_combusted * (MW_CO2 / MW_CH4)) + flared_native_co2
        flared_unburnt_ch4 = flared_ch4_mass * 0.02

        flared_m3 = total_gas_m3 * ctrl
        flared_scf = convert(flared_m3, "m3", "scf")
        hhv_val = float(hhv or 1020.0)
        flared_mmbtu = (flared_scf * hhv_val) / 1_000_000.0
        n2o_ef_kg = float(ef_n2o if ef_n2o is not None else 0.0001)
        flared_n2o = (flared_mmbtu * n2o_ef_kg) / 1000.0

    total_ch4 = vented_ch4 + flared_unburnt_ch4
    total_co2 = vented_co2 + flared_co2

    return {
        "vented_ch4": vented_ch4,
        "vented_co2": vented_co2,
        "flared_co2": flared_co2,
        "flared_unburnt_ch4": flared_unburnt_ch4,
        "flared_n2o": flared_n2o,
        "total_ch4": total_ch4,
        "total_co2": total_co2,
    }


def _propagate_results(total_ch4, total_co2, flared_n2o, uncertainties, factor_source="default", category="vented"):
    # the dispatcher injects the record's factor source (default / custom / specific) so the tier
    # follows the method actually used, not the calculator's citation label
    _tier = resolve_tier((uncertainties or {}).get("_factor_source") or factor_source)
    ch4_res = propagate_uncertainty(
        total_ch4,
        resolve_ef_uncertainty(category, "ch4", _tier, (uncertainties or {}).get("ch4")),
        tier=_tier,
        process_category=category,
        gas="ch4",
    )
    co2_res = (
        propagate_uncertainty(
            total_co2,
            resolve_ef_uncertainty(category, "co2", _tier, (uncertainties or {}).get("co2")),
            tier=_tier,
            process_category=category,
            gas="co2",
        )
        if total_co2 > 0
        else None
    )
    n2o_res = (
        propagate_uncertainty(
            flared_n2o,
            resolve_ef_uncertainty(category, "n2o", _tier, (uncertainties or {}).get("n2o")),
            tier=_tier,
            process_category=category,
            gas="n2o",
        )
        if flared_n2o > 0
        else None
    )
    return ch4_res, co2_res, n2o_res


# ==============================================================================
# §6.3.2 Workovers without Hydraulic Fracturing
# ==============================================================================


# ==============================================================================
# §6.3.5 Casing Gas Vents
# ==============================================================================


# ==============================================================================
# §6.3.6 Natural Gas-Driven Pneumatic Controllers (Fixes BUG-100)
# ==============================================================================


# ==============================================================================
# §6.3.7 Gas Driven Pneumatic Pumps (Chemical Injection Pumps)
# ==============================================================================


# ==============================================================================
# §6.3.8 Gas Treatment: Dehydration and Acid Gas Removal
# ==============================================================================



# ==============================================================================
# §6.3.9 Storage Tanks: Flashing & Working/Standing Losses (Fixes BUG-102)
# ==============================================================================


# ==============================================================================
# §6.3.10 CO2 Enhanced Oil Recovery (EOR) Operations
# ==============================================================================


# ==============================================================================
# §6.3.11 Other Production Non-Routine Venting
# ==============================================================================


# ==============================================================================
# Equipment & Process Blowdowns (Upgraded BlowdownCalculator, Fixes BUG-101)
# ==============================================================================


# Calculators split out of this file; imported last because they use the helpers above.
from .vented_production_wells import WorkoverWithoutFracturingCalculator, CasingGasVentCalculator, CO2EORVentingCalculator, ProductionNonRoutineVentingCalculator  # noqa: E402,F401
from .vented_production_pneumatic import PneumaticDeviceCalculator, PneumaticPumpCalculator, GasDehydrationCalculator  # noqa: E402,F401
from .vented_production_tank import AcidGasRemovalCalculator, TankFlashingCalculator, BlowdownCalculator  # noqa: E402,F401
