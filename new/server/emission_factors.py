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
        "ch4": 2.25,
        "factor": 2.25,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-14 API study production high-bleed (16.4 scf/h)",
    },
    "Pneumatic Controller - Low Bleed": {
        "code": "LowBleed",
        "type": "pneumatic",
        "ch4": 0.36,
        "factor": 0.36,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-14 API study production low-bleed (2.6 scf/h)",
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
        "hhv": 1026,  # Btu/scf, 40 CFR 98 Table C-1 / Compendium Table 4-5 (audit 2026-11 F-FAC-01)
        "co2": 53.06,
        "ch4": 0.56699,  # Table 4-11 (AP-42 3.2-2): 1.25 lb/10^6 Btu (HHV) x 0.45359 (audit 2026-11 F-FAC-06)
        "n2o": 0.0001,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "description": "Natural gas 4-stroke lean-burn engine (Table 4-11)",
        "uncertainty": {"co2": 0.05, "ch4": 0.3, "n2o": 0.3},
        "baseUnit": "scf",
    },
    "Natural Gas - 4-Stroke Rich Burn Engine": {
        "code": "NG_4SRB",
        "hhv": 1026,  # Btu/scf, 40 CFR 98 Table C-1 / Compendium Table 4-5 (audit 2026-11 F-FAC-01)
        "co2": 53.06,
        "ch4": 0.10433,  # Table 4-11 (AP-42 3.2-3) uncontrolled: 0.23 lb/10^6 Btu (HHV) (F-FAC-06)
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
        "hhv": 1026,  # Btu/scf, 40 CFR 98 Table C-1 / Compendium Table 4-5 (audit 2026-11 F-FAC-01)
        "co2": 53.06,
        "ch4": 0.003901,  # Table 4-11 (AP-42 3.1-2a): 0.0086 lb/10^6 Btu (HHV) (F-FAC-06)
        "n2o": 0.0013608,  # Table 4-11 (AP-42 3.1-2a): 0.003 lb/10^6 Btu (HHV) (F-FAC-06)
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "uncertainty": {"co2": 0.05, "ch4": 0.2, "n2o": 0.2},
        "baseUnit": "scf",
    },
    "Natural Gas - 2-Stroke Lean Burn Engine": {
        "code": "NG_2SLB",
        "hhv": 1026,  # Btu/scf, 40 CFR 98 Table C-1 / Compendium Table 4-5 (audit 2026-11 F-FAC-01)
        "co2": 53.06,
        "ch4": 0.65771,  # Table 4-11 (AP-42 3.2-1): 1.45 lb/10^6 Btu (HHV) (F-FAC-06)
        "n2o": 0.0001,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "uncertainty": {"co2": 0.05, "ch4": 0.3, "n2o": 0.2},
        "baseUnit": "scf",
    },
    "Natural Gas - Heater/Boiler": {
        "code": "NG_Heater",
        "hhv": 1026,  # Btu/scf, 40 CFR 98 Table C-1 / Compendium Table 4-5 (audit 2026-11 F-FAC-01)
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
        # Table 6-9 prints +/-924 % for this factor (audit 2026-11 F-FAC-04: 30 % was stored)
        "uncertainty": {"co2": 0.0, "ch4": 9.24, "n2o": 0.0},
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
        "description": "API Compendium 2021 Table 6-22 — crude oil flashing (large tank, without control)",
        "uncertainty": {"co2": 0.15, "ch4": 0.4, "n2o": 0.0},
    },
}

# Tier 1 fuels offered by the Scope 1 form that had no server factor (browser test F1: the form
# listed them, the server rejected every one). CO2 and heating values: Table 4-5 (40 CFR 98 Table C-1,
# kg CO2/MMBtu HHV); CH4 / N2O: Table 4-6 (HHV basis). Liquids are per gallon of liquid, gases per scf.
_PETROLEUM_CH4, _PETROLEUM_N2O = 0.003, 0.0006   # Table 4-6 petroleum products, kg/MMBtu (HHV)
_NG_CH4, _NG_N2O = 0.001, 0.0001                  # Table 4-6 natural gas


def _fuel(code, hhv, base_unit, co2, ch4, n2o, source, usage=("combustion",), unc=(0.05, 0.2, 0.2), **extra):
    return {"code": code, "hhv": hhv, "baseUnit": base_unit, "co2": co2, "ch4": ch4, "n2o": n2o,
            "unit": "kg/MMBtu", "usage": list(usage), "source": source,
            "uncertainty": {"co2": unc[0], "ch4": unc[1], "n2o": unc[2]}, **extra}


# Pure-gas flare streams: CO2 by carbon balance at 98 % combustion (Equation 5-2, 23.685 Sm3/kgmole),
# no CH4 in the stream, N2O by Equation 5-6 (natural gas 1e-4 / 60 kg CO2 per MMBtu).
_MV_SM3_PER_KMOL = 23.685  # Sm3 / kgmole (Compendium section 5.1.2)


def _pure_gas_flare(code, carbon_atoms, description):
    co2 = carbon_atoms * 44.01 / _MV_SM3_PER_KMOL * 0.965  # Dec 2025 correction: 96.5 % combustion efficiency
    return {"code": code, "co2": round(co2, 4), "ch4": 0.0, "n2o": round(co2 * 1e-4 / 60.0, 10),
            "unit": "kg/m³", "usage": ["flaring"], "type": "gases", "description": description,
            "source": "API Compendium 2021 Section 5.1, Equations 5-3 and 5-6 (96.5 % combustion, Dec 2025 corrections)",
            "uncertainty": {"co2": 0.05, "ch4": 0.0, "n2o": 0.5}}


TIER1_FUEL_ADDITIONS = {
    "Propylene": _fuel("Propylene", 91000, "gal", 67.77, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6 (liquid)"),
    "Butane": _fuel("Butane", 103000, "gal", 64.77, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6 (liquid)"),
    "Isobutane": _fuel("Isobutane", 99000, "gal", 64.94, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6 (liquid)"),
    "Naphtha": _fuel("Naphtha", 125000, "gal", 68.02, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6, naphtha < 401 F"),
    "Lubricants": _fuel("Lube", 144000, "gal", 74.27, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 / 4-6"),
    "Waste Oil": _fuel("WasteOil", 138000, "gal", 74.00, _PETROLEUM_CH4, _PETROLEUM_N2O, "Table 4-5 used oil / Table 4-6"),
    # solids: HHV in kBtu per short ton
    "Tires": _fuel("Tires", 28000, "short_ton", 85.97, 0.032, 0.0042,
                   "Table 4-5; CH4 / N2O 40 CFR 98 Table C-2 other solid fuels", unc=(0.03, 0.3, 0.4)),
    # gases (per scf)
    "Acetylene": _fuel("Acetylene", 1470, "scf", 71.59, _PETROLEUM_CH4, _PETROLEUM_N2O,
                       "Table 3-8 (1,470 Btu/scf, 0.0686 lb/ft3, 92.3 wt % C), 100 % oxidation; Table 4-6"),
    "Compressed Natural Gas (CNG)": _fuel("CNG", 1026, "scf", 53.06, _NG_CH4, _NG_N2O,
                                          "Natural gas, Table 4-5 (40 CFR 98 Table C-1: 1,026 Btu/scf, 53.06 kg CO2/MMBtu) / Table 4-6 (standard volume)",
                                          usage=("combustion", "mobile")),
    "Liquefied Natural Gas (LNG)": _fuel("LNG", 1026, "scf", 53.06, _NG_CH4, _NG_N2O,
                                         "Natural gas, Table 4-5 (40 CFR 98 Table C-1: 1,026 Btu/scf, 53.06 kg CO2/MMBtu) / Table 4-6 (regasified standard volume)",
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
# a name defined in both tables is one row: the API 2021 table's values and metadata, with the legacy row's
# fields it lacks and both usage lists. The manual route (ALL wins) and the bulk import (LEGACY wins) served
# different copies, so a usage check ran on one path only (audit 2026-11 F-FAC-08).
for _name in set(ALL_EMISSION_FACTORS) & set(LEGACY_FACTORS):
    _all, _leg = ALL_EMISSION_FACTORS[_name], LEGACY_FACTORS[_name]
    _usage = list(dict.fromkeys(list(_all.get("usage") or []) + list(_leg.get("usage") or [])))
    API_FACTORS[_name] = {**_leg, **_all, **({"usage": _usage} if _usage else {})}

# Rows whose source table prints no uncertainty ("Not specified"): their stored uncertainty is a platform
# default, labelled as one so it is not read as a published value (audit 2026-11 F-FAC-04)
UNCERTAINTY_DEFAULT_ROWS = frozenset({
    'Acrylonitrile',
    'Adipic Acid - Catalytic Abatement',
    'Adipic Acid - Thermal Abatement',
    'Adipic Acid - Uncontrolled',
    'Asphalt',
    'Associated Gas Venting - Anadarko Basin (Basin 360)',
    'Associated Gas Venting - Gulf Coast Basin (Basin 220)',
    'Associated Gas Venting - Other US Basins',
    'Associated Gas Venting - Permian Basin (Basin 430)',
    'Associated Gas Venting - US Average',
    'Associated Gas Venting - Williston Basin (Basin 395)',
    'Carbon Black',
    'Carbon Black (Thermal Abatement)',
    'Component - Block Valve',
    'Component - Compressor Seal',
    'Component - Connector (Non-Compressor)',
    'Component - Control Valve',
    'Component - Pressure Regulator',
    'Component - Pressure Relief Valve',
    'Ethylene (Ethane Feedstock)',
    'Ethylene (Other Feedstocks)',
    'Ethylene Dichloride',
    'Ethylene Oxide',
    'Ethylene Oxide (Thermal Abatement)',
    'LNG - Export Terminal',
    'LNG - Import Terminal',
    'LNG - Storage Station',
    'Liquids Unloading - Non-Plunger',
    'Liquids Unloading - Non-Plunger (Tier 1 Default)',
    'Liquids Unloading - Plunger Lift',
    'Liquids Unloading - Plunger Lift (Tier 1 Default)',
    'Methanol',
    'Nitric Acid - With NSCR',
    'Nitric Acid - Without NSCR',
    'Offshore - Gas Production (Facility)',
    'Offshore - Oil Production (Facility)',
    'Pneumatic Controller - Continuous Vent (T&S)',
    'Pneumatic Controller - High Bleed (>6 scfh)',
    'Pneumatic Controller - Intermittent',
    'Pneumatic Controller - Low Bleed (<6 scfh)',
    'Refinery - Fuel Gas System (100-199k bbl/day)',
    'Refinery - Fuel Gas System (50-99k bbl/day)',
    'Tank - Crude Oil (Large, >10 bbl/d)',
    'Tank - Crude Oil (Small, ≤10 bbl/d)',
    'Tank - Flash Emissions (Oil)',
    'Tank - Production Condensate (Large, >10 bbl/d)',
    'Tank - Production Condensate (Small, ≤10 bbl/d)',
    'UnloadNonPlunger',
    'UnloadPlunger',
})
for _name, _row in API_FACTORS.items():
    if isinstance(_row, dict) and isinstance(_row.get("uncertainty"), dict):
        _row.setdefault("uncertainty_basis", "platform default (the source table prints no uncertainty)"
                        if _name in UNCERTAINTY_DEFAULT_ROWS else "source table or IPCC 2006 default")

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

# CORRELATION_EQUATIONS is the API 2021 table imported above (Compendium Tables 7-40 / 7-42). A second,
# unused copy re-bound it here with values not in those tables (audit 2026-11 F-FAC-09).
