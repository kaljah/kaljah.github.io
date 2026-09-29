"""
Emission Factors Database - API Compendium 2021
Comprehensive emission factors with automatic uncertainty loading,
segment-based categorization, and process type organization.

This module imports from emission_factors_api2021.py which contains
120+ emission factors from API Compendium 2021 Sections 5, 6, and 7.

All factors include:
- Segment classification (Upstream/Midstream/Downstream)
- Process category
- Uncertainty values for CO₂, CH₄, N₂O
- Source references to API Compendium 2021
"""

# Import comprehensive emission factors from API 2021 database
from emission_factors_api2021 import (
    # Main factor dictionaries
    API_FACTORS,
    EQUIPMENT_FACTORS,
    ALL_EMISSION_FACTORS,
    COMBUSTION_FACTORS,
    FLARING_FACTORS,
    VENTED_FACTORS,
    CHEMICAL_PRODUCTION_FACTORS,
    N2O_PRODUCTION_FACTORS,
    CORRELATION_EQUATIONS,
    API_CHAPTER7_ONSHORE_FACTORS,
    METHOD21_SCREENING_RANGES,
    OGI_LEAKER_FACTORS,
    DEFAULT_SERVICE_COMPOSITIONS,
    # Helper functions
    get_factor_by_segment,
    get_factor_by_process_category,
    get_factors_by_segment_and_category,
)

# Import process categorization
from process_categories import (
    SEGMENTS,
    PROCESS_TYPES,
    CATEGORIES,
    get_process_types_for_segment,
    get_segments_for_process,
    get_process_types_by_category,
)

# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================
# The original API_FACTORS dictionary has been replaced by imports from
# emission_factors_api2021.py which contains the comprehensive API 2021
# emission factors database with:
# - 120+ emission factors (Sections 5, 6, 7)
# - Automatic uncertainty values
# - Segment classification (Upstream/Midstream/Downstream)
# - Process category organization
#
# All existing code referencing API_FACTORS will continue to work.
# =============================================================================

# For convenience, expose the main dictionaries at module level
__all__ = [
    "API_FACTORS",
    "EQUIPMENT_FACTORS",
    "ALL_EMISSION_FACTORS",
    "COMBUSTION_FACTORS",
    "FLARING_FACTORS",
    "VENTED_FACTORS",
    "CHEMICAL_PRODUCTION_FACTORS",
    "N2O_PRODUCTION_FACTORS",
    "CORRELATION_EQUATIONS",
    "API_CHAPTER7_ONSHORE_FACTORS",
    "METHOD21_SCREENING_RANGES",
    "OGI_LEAKER_FACTORS",
    "DEFAULT_SERVICE_COMPOSITIONS",
    "get_factor_by_segment",
    "get_factor_by_process_category",
    "get_factors_by_segment_and_category",
    "SEGMENTS",
    "PROCESS_TYPES",
    "CATEGORIES",
    "get_process_types_for_segment",
    "get_segments_for_process",
    "get_process_types_by_category",
]

# Consolidate all factors into a single dictionary for routing lookup
# This combines Section 5/6 (API_FACTORS) and Section 7 (EQUIPMENT_FACTORS)
# with the legacy factor definitions.
LEGACY_FACTORS = {
    "Pneumatic Controller - High Bleed": {
        "code": "HighBleed",
        "type": "pneumatic",
        "ch4": 5.11,
        "factor": 5.11,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-14 EPA GHGRP production high-bleed",
    },
    "Pneumatic Controller - Low Bleed": {
        "code": "LowBleed",
        "type": "pneumatic",
        "ch4": 0.191,
        "factor": 0.191,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-14 EPA GHGRP production low-bleed",
    },
    "Pneumatic Controller - Intermittent": {
        "code": "Intermittent",
        "type": "pneumatic",
        "ch4": 1.85,
        "factor": 1.85,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-15 EPA GHGRP production intermittent",
    },
    "Pneumatic Controller - Continuous Vent (T&S)": {
        "code": "ContinuousVentTS",
        "type": "pneumatic",
        "ch4": 3.5,
        "factor": 3.5,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-42 continuous vent controller (transmission/storage)",
    },
    # Liquids Unloading Tier 1 - API Compendium 2021 Table 6-11
    "UnloadPlunger": {
        "code": "UnloadPlunger",
        "type": "unloading",
        "ch4": 1.774,  # tonnes CH4 per well-year (Plunger Lift)
        "factor": 1.774,
        "whole_gas_ef": 113466.0,
        "ch4_mol_pct": 81.6,
        "unit": "tonnes CH4/well-year",
        "baseUnit": "wells",
        "description": "Liquids Unloading - Plunger Lift (API Table 6-11)",
        "uncertainty": {"co2": 0.50, "ch4": 0.50, "n2o": 0.50},
    },
    "UnloadNonPlunger": {
        "code": "UnloadNonPlunger",
        "type": "unloading",
        "ch4": 2.792,  # tonnes CH4 per well-year (Non-Plunger Lift)
        "factor": 2.792,
        "whole_gas_ef": 178531.0,
        "ch4_mol_pct": 81.6,
        "unit": "tonnes CH4/well-year",
        "baseUnit": "wells",
        "description": "Liquids Unloading - Non-Plunger Lift (API Table 6-11)",
        "uncertainty": {"co2": 0.50, "ch4": 0.50, "n2o": 0.50},
    },
    "Natural Gas - 4-Stroke Lean Burn Engine": {
        "code": "NG_4SLB",
        "hhv": 1020,
        "co2": 53.06,
        "ch4": 0.56656,  # Table 4-7 AP-42: 0.537 t/10^12 J (HHV)
        "n2o": 0.0001,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "description": "Natural gas 4-stroke lean-burn engine (Table 4-7)",
        "uncertainty": {"co2": 0.05, "ch4": 0.3, "n2o": 0.3},
        "baseUnit": "scf",
    },
    "Natural Gas - 4-Stroke Rich Burn Engine": {
        "code": "NG_4SRB",
        "hhv": 1020,
        "co2": 53.06,
        "ch4": 0.10551,  # Table 4-7 AP-42 uncontrolled: 0.10 t/10^12 J (HHV)
        "n2o": 0.0001,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "uncertainty": {"co2": 0.05, "ch4": 0.3, "n2o": 0.3},
        "baseUnit": "scf",
    },
    "Liquids Unloading - Plunger Lift": {
        "code": "UnloadPlunger",
        "type": "unloading",
        "ch4": 1.774,
        "factor": 1.774,
        "whole_gas_ef": 113466.0,
        "ch4_mol_pct": 81.6,
        "unit": "tonnes CH4/well-year",
        "baseUnit": "wells",
        "usage": ["unloading", "liquids_unloading", "vented"],
        "description": "API Table 6-11: Liquid Unloading Vented Emission Factor, plunger lift (1,774 kg CH4/well-year)",
        "uncertainty": {"co2": 0.50, "ch4": 0.50, "n2o": 0.50},
    },
    "Liquids Unloading - Non-Plunger": {
        "code": "UnloadNonPlunger",
        "type": "unloading",
        "ch4": 2.792,
        "factor": 2.792,
        "whole_gas_ef": 178531.0,
        "ch4_mol_pct": 81.6,
        "unit": "tonnes CH4/well-year",
        "baseUnit": "wells",
        "usage": ["unloading", "liquids_unloading", "vented"],
        "description": "API Table 6-11: Liquid Unloading Vented Emission Factor, non-plunger (2,792 kg CH4/well-year)",
        "uncertainty": {"co2": 0.50, "ch4": 0.50, "n2o": 0.50},
    },
    "Propane (Liquid)": {
        "source": "API Compendium 2021 Table 4-5 / Table 4-6",
        "code": "LPG_Liq",
        "hhv": 91000,  # Table 4-5 propane: 0.091 MMBtu/gal
        "co2": 62.87,  # Table 4-5 propane
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.3},
        "unit": "kg/MMBtu",
        "usage": ["combustion", "mobile"],
        "baseUnit": "gal",
    },
    "Natural Gas - Turbine": {
        "code": "NG_Turbine",
        "hhv": 1020,
        "co2": 53.06,
        "ch4": 0.003904,  # Table 4-7: 0.0037 t/10^12 J (HHV)
        "n2o": 0.001372,  # Table 4-7: 0.0013 t/10^12 J (HHV)
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "uncertainty": {"co2": 0.05, "ch4": 0.2, "n2o": 0.2},
        "baseUnit": "scf",
    },
    "Natural Gas - 2-Stroke Lean Burn Engine": {
        "code": "NG_2SLB",
        "hhv": 1020,
        "co2": 53.06,
        "ch4": 0.6573,  # Table 4-7 AP-42: 0.623 t/10^12 J (HHV)
        "n2o": 0.0001,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "uncertainty": {"co2": 0.05, "ch4": 0.3, "n2o": 0.2},
        "baseUnit": "scf",
    },
    "Natural Gas - Heater/Boiler": {
        "code": "NG_Heater",
        "hhv": 1020,
        "co2": 53.06,
        "ch4": 0.001,
        "n2o": 0.0001,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "uncertainty": {"co2": 0.05, "ch4": 0.2, "n2o": 0.2},
        "baseUnit": "scf",
    },
    "Completion - Gas Well (No Flaring)": {
        "source": "API Compendium 2021 Table 6-6",
        "code": "CompGasNoFlare",
        "ch4": 1.7376,  # Table 6-6 gas well completion without HF, vented
        "co2": 0,
        "n2o": 0,
        "factor": 1.7376,
        "unit": "tonnes/event",
        "usage": ["completions"],
        "description": "Average per event (Uncontrolled)",
        "uncertainty": {"co2": 0.0, "ch4": 0.3, "n2o": 0.0},
    },
    "Workover - Gas Well (No Flaring)": {
        "source": "API Compendium 2021 Table 6-9",
        "code": "WorkoverGasNoFlare",
        "ch4": 0.047,  # Table 6-9 gas well workover without HF
        "co2": 0,
        "n2o": 0,
        "factor": 0.047,
        "unit": "tonnes/event",
        "usage": ["completions"],
        "description": "Average per event (Uncontrolled)",
        "uncertainty": {"co2": 0.0, "ch4": 0.3, "n2o": 0.0},
    },
    "Tank - Flash Emissions (Oil)": {
        "code": "TankFlashOil",
        "type": "tank",
        "ch4": 0.193,
        "co2": 0,  # Table 6-22 is CH4 only (same as emission_factors_api2021 and the client catalog)
        "n2o": 0,
        "factor": 0.193,
        "unit": "kg/bbl",
        "usage": ["tank_flashing"],
        "description": "API Table 5-16 / 6-4 — Default crude oil flash emission factor",
        "uncertainty": {"co2": 0.15, "ch4": 0.4, "n2o": 0.0},
    },
}

# Tier 1 fuels offered by the Scope 1 form that had no server factor (browser test F1: the form
# listed them, the server rejected every one). CO2 and heating values: Table 4-5 (40 CFR 98 Table C-1,
# kg CO2/MMBtu HHV); CH4 / N2O: Table 4-6 (HHV basis). Liquids are per gallon of liquid, gases per scf.
_PETROLEUM_CH4, _PETROLEUM_N2O = 0.003, 0.0006   # Table 4-6 petroleum products, kg/MMBtu (HHV)
_BIOLIQUID_CH4, _BIOLIQUID_N2O = 0.0011, 0.00011  # Table 4-6 biodiesels / liquid biofuels
_NG_CH4, _NG_N2O = 0.001, 0.0001                  # Table 4-6 natural gas


def _fuel(code, hhv, base_unit, co2, ch4, n2o, source, usage=("combustion",), unc=(0.05, 0.2, 0.2), **extra):
    return {"code": code, "hhv": hhv, "baseUnit": base_unit, "co2": co2, "ch4": ch4, "n2o": n2o,
            "unit": "kg/MMBtu", "usage": list(usage), "source": source,
            "uncertainty": {"co2": unc[0], "ch4": unc[1], "n2o": unc[2]}, **extra}


# Pure-gas flare streams: CO2 by carbon balance at 98 % combustion (Equation 5-2, 23.685 Sm3/kgmole),
# no CH4 in the stream, N2O by Equation 5-6 (natural gas 1e-4 / 60 kg CO2 per MMBtu).
_MV_SM3_PER_KMOL = 23.685  # Sm3 / kgmole (Compendium section 5.1.2)


def _pure_gas_flare(code, carbon_atoms, description):
    co2 = carbon_atoms * 44.01 / _MV_SM3_PER_KMOL * 0.98
    return {"code": code, "co2": round(co2, 4), "ch4": 0.0, "n2o": round(co2 * 1e-4 / 60.0, 10),
            "unit": "kg/m³", "usage": ["flaring"], "type": "gases", "description": description,
            "source": "API Compendium 2021 Section 5.1, Equations 5-3 and 5-6 (98 % combustion)",
            "uncertainty": {"co2": 0.05, "ch4": 0.0, "n2o": 0.5}}


TIER1_FUEL_ADDITIONS = {
    "Propylene": _fuel("Propylene", 91000, "gal", 67.77, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6 (liquid)"),
    "Butane": _fuel("Butane", 103000, "gal", 64.77, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6 (liquid)"),
    "Isobutane": _fuel("Isobutane", 99000, "gal", 64.94, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6 (liquid)"),
    "Naphtha": _fuel("Naphtha", 125000, "gal", 68.02, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6, naphtha < 401 F"),
    "Lubricants": _fuel("Lube", 144000, "gal", 74.27, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6"),
    "Waste Oil": _fuel("WasteOil", 138000, "gal", 74.00, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 used oil / Table 4-6"),
    "Ethanol (100%)": _fuel("EtOH", 84000, "gal", 68.44, _BIOLIQUID_CH4, _BIOLIQUID_N2O, "Table 4-5 / 4-6",
                            usage=("combustion", "mobile"), unc=(0.05, 0.4, 0.5)),
    "Biodiesel (100%)": _fuel("BioDSL", 128000, "gal", 73.84, _BIOLIQUID_CH4, _BIOLIQUID_N2O, "Table 4-5 / 4-6",
                              usage=("combustion", "mobile"), unc=(0.05, 0.4, 0.5)),
    # solids: HHV in kBtu per short ton
    "Wood / Wood Waste": _fuel("Wood", 17480, "ton", 93.80, 0.0072, 0.0036, "Table 4-5 (dry basis) / Table 4-6",
                               unc=(0.05, 0.4, 0.5)),
    "Tires": _fuel("Tires", 28000, "ton", 85.97, 0.032, 0.0042,
                   "Table 4-5; CH4 / N2O 40 CFR 98 Table C-2 other solid fuels", unc=(0.03, 0.3, 0.4)),
    # gases (per scf)
    "Acetylene": _fuel("Acetylene", 1470, "scf", 71.59, _PETROLEUM_CH4, _PETROLEUM_N2O,
                       "Table 3-8 (1,470 Btu/scf, 0.0686 lb/ft3, 92.3 wt % C), 100 % oxidation; Table 4-6"),
    "Compressed Natural Gas (CNG)": _fuel("CNG", 1020, "scf", 53.06, _NG_CH4, _NG_N2O,
                                          "Natural gas, Tables 3-8 / 4-5 / 4-6 (standard volume)",
                                          usage=("combustion", "mobile")),
    "Liquefied Natural Gas (LNG)": _fuel("LNG", 1020, "scf", 53.06, _NG_CH4, _NG_N2O,
                                         "Natural gas, Tables 3-8 / 4-5 / 4-6 (regasified standard volume)",
                                         usage=("combustion", "mobile")),
    "Propane (Flaring)": _pure_gas_flare("LPG_Flare", 3, "Propane flared (pure stream)"),
    "Butane (Flaring)": _pure_gas_flare("Butane_Flare", 4, "Butane flared (pure stream)"),
    "Ethylene (Flaring)": _pure_gas_flare("Ethylene_Flare", 2, "Ethylene flared (pure stream)"),
    "Propylene (Flaring)": _pure_gas_flare("Propylene_Flare", 3, "Propylene flared (pure stream)"),
}
LEGACY_FACTORS.update(TIER1_FUEL_ADDITIONS)

# Source of truth: ALL_EMISSION_FACTORS contains the full 120+ factors from Sections 5, 6, 7
# We merge legacy definitions on top if they differ, but favor the new comprehensive database.
API_FACTORS = {**ALL_EMISSION_FACTORS, **LEGACY_FACTORS}

# Update EQUIPMENT_FACTORS for internal module compatibility
EQUIPMENT_FACTORS = {
    k: v
    for k, v in API_FACTORS.items()
    if v.get("type")
    in [
        "pneumatic",
        "tank",
        "drilling",
        "fugitive",
        "dehydrator",
        "equipment",
        "compressor",
        "separator",
        "wellhead",
        "component",
        "facility",
    ]
}

PROCESS_TYPES = {
    "combustion": "Stationary Combustion",
    "flaring": "Flaring",
    "routine_flaring": "Routine Flaring",
    "non_routine_flaring": "Non-Routine Flaring",
    "safety_flaring": "Safety Flaring",
    "venting": "Venting (Blowdown)",
    "pneumatic": "Pneumatic Device",
    "tank": "Storage Tank",
    "drilling": "Drilling Operations",
    "completions": "Well Completions & Workovers",
    "unloading": "Liquids Unloading",
    "agr": "Acid Gas Removal (AGR)",
    "dehydrator": "Dehydrator",
    "mobile": "Mobile Combustion",
    "fugitive": "Fugitive Emissions",
}

# API Table 7-3: Correlation Equations (kg/hr/source)
# Leak Rate = A * (Screening Value)^B
CORRELATION_EQUATIONS = {
    "gas_valve": {
        "A": 2.29e-6,
        "B": 0.746,
        "max_ppm": 100000,
        "pegged_10k": 0.064,
        "pegged_100k": 0.11,
    },
    "light_liquid_valve": {
        "A": 6.41e-6,
        "B": 0.797,
        "max_ppm": 100000,
        "pegged_10k": 0.074,
        "pegged_100k": 0.15,
    },
    "light_liquid_pump": {
        "A": 5.03e-5,
        "B": 0.610,
        "max_ppm": 100000,
        "pegged_10k": 0.16,
        "pegged_100k": 0.68,
    },
    "connector": {
        "A": 1.53e-6,
        "B": 0.735,
        "max_ppm": 100000,
        "pegged_10k": 0.028,
        "pegged_100k": 0.030,
    },
    "flange": {
        "A": 4.61e-6,
        "B": 0.703,
        "max_ppm": 100000,
        "pegged_10k": 0.085,
        "pegged_100k": 0.089,
    },
    "open_ended_line": {
        "A": 2.20e-6,
        "B": 0.704,
        "max_ppm": 100000,
        "pegged_10k": 0.012,
        "pegged_100k": 0.014,
    },
    "other": {
        "A": 1.36e-5,
        "B": 0.589,
        "max_ppm": 100000,
        "pegged_10k": 0.073,
        "pegged_100k": 0.11,
    },
}
