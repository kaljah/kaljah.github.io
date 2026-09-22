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
        "ch4": 8.304,
        "factor": 8.304,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-34 continuous bleed (gas processing)",
    },
    "Pneumatic Controller - Low Bleed": {
        "code": "LowBleed",
        "type": "pneumatic",
        "ch4": 0.0939,
        "factor": 0.0939,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-34 pneumatic/hydraulic valve operator (gas processing)",
    },
    "Pneumatic Controller - Intermittent": {
        "code": "Intermittent",
        "type": "pneumatic",
        "ch4": 0.4,
        "factor": 0.4,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-42 intermittent vent controller (transmission/storage)",
    },
    "Pneumatic Controller - Continuous Vent (T&S)": {
        "code": "ContinuousVentTS",
        "type": "pneumatic",
        "ch4": 3.5,
        "factor": 3.5,
        "unit": "tonnes CH4/yr",
        "description": "Table 6-42 continuous vent controller (transmission/storage)",
    },
    "Fugitive - Valve (Gas/Vapor)": {
        "code": "ValveGas",
        "type": "fugitive",
        "ch4": 0.0045,
        "factor": 0.0045,
        "unit": "kg/hr",
        "description": "Valves in Gas Service",
        "uncertainty": {"co2": 0.3, "ch4": 0.3, "n2o": 0.3},
    },
    "Fugitive - Connector (Gas/Vapor)": {
        "code": "ConnGas",
        "type": "fugitive",
        "ch4": 0.0002,
        "factor": 0.0002,
        "unit": "kg/hr",
        "description": "Connectors in Gas Service",
        "uncertainty": {"co2": 0.3, "ch4": 0.3, "n2o": 0.3},
    },
    "Fugitive - Flange (Gas/Vapor)": {
        "code": "FlangeGas",
        "type": "fugitive",
        "ch4": 0.00039,
        "factor": 0.00039,
        "unit": "kg/hr",
        "description": "Flanges in Gas Service",
        "uncertainty": {"co2": 0.3, "ch4": 0.3, "n2o": 0.3},
    },
    # Liquids Unloading Tier 1 - API Compendium 2021 Table 6-7
    "UnloadPlunger": {
        "code": "UnloadPlunger",
        "type": "unloading",
        "ch4": 0.0016,  # tonnes CH4 per event (Plunger Lift)
        "factor": 0.0016,
        "unit": "tonnes CH4/event",
        "description": "Liquids Unloading - Plunger Lift (API Table 6-7)",
        "uncertainty": {"co2": 0.0, "ch4": 0.50, "n2o": 0.0},
    },
    "UnloadNonPlunger": {
        "code": "UnloadNonPlunger",
        "type": "unloading",
        "ch4": 0.0341,  # tonnes CH4 per event (Non-Plunger Lift)
        "factor": 0.0341,
        "unit": "tonnes CH4/event",
        "description": "Liquids Unloading - Non-Plunger Lift (API Table 6-7)",
        "uncertainty": {"co2": 0.0, "ch4": 0.50, "n2o": 0.0},
    },
    "Natural Gas - 4-Stroke Lean Burn Engine": {
        "code": "NG_4SLB",
        "hhv": 1020,
        "co2": 53.06,
        "ch4": 0.3,
        "n2o": 0.0001,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "description": "High CH4 Slip",
        "uncertainty": {"co2": 0.05, "ch4": 0.3, "n2o": 0.3},
        "baseUnit": "scf",
    },
    "Natural Gas - 4-Stroke Rich Burn Engine": {
        "code": "NG_4SRB",
        "hhv": 1020,
        "co2": 53.06,
        "ch4": 0.001,
        "n2o": 0.0001,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "uncertainty": {"co2": 0.05, "ch4": 0.3, "n2o": 0.3},
        "baseUnit": "scf",
    },
    "Liquids Unloading - Plunger Lift": {
        "code": "UnloadPlunger",
        "type": "unloading",
        "ch4": 0.1,
        "factor": 0.1,
        "unit": "tonnes/event",
        "usage": ["unloading"],
        "description": "Average per event",
        "uncertainty": {"co2": 0.0, "ch4": 0.25, "n2o": 0.0},
    },
    "Liquids Unloading - Non-Plunger": {
        "code": "UnloadNonPlunger",
        "type": "unloading",
        "ch4": 0.2,
        "factor": 0.2,
        "unit": "tonnes/event",
        "usage": ["unloading"],
        "description": "Average per event",
        "uncertainty": {"co2": 0.0, "ch4": 0.25, "n2o": 0.0},
    },
    "Propane (Liquid)": {
        "code": "LPG_Liq",
        "hhv": 91500,
        "co2": 62.88,
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
        "ch4": 0.0037,
        "n2o": 0.0013,
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "uncertainty": {"co2": 0.05, "ch4": 0.2, "n2o": 0.2},
        "baseUnit": "scf",
    },
    "Natural Gas - 2-Stroke Lean Burn Engine": {
        "code": "NG_2SLB",
        "hhv": 1020,
        "co2": 53.06,
        "ch4": 0.6,
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
        "code": "CompGasNoFlare",
        "ch4": 0.7,
        "co2": 0,
        "n2o": 0,
        "factor": 0.7,
        "unit": "tonnes/event",
        "usage": ["completions"],
        "description": "Average per event (Uncontrolled)",
        "uncertainty": {"co2": 0.0, "ch4": 0.3, "n2o": 0.0},
    },
    "Workover - Gas Well (No Flaring)": {
        "code": "WorkoverGasNoFlare",
        "ch4": 0.05,
        "co2": 0,
        "n2o": 0,
        "factor": 0.05,
        "unit": "tonnes/event",
        "usage": ["completions"],
        "description": "Average per event (Uncontrolled)",
        "uncertainty": {"co2": 0.0, "ch4": 0.3, "n2o": 0.0},
    },
    "Tank - Working Losses (Oil)": {
        "code": "TankWorkOil",
        "ch4": 0.05,
        "co2": 0,
        "n2o": 0,
        "factor": 0.05,
        "unit": "kg/bbl",
        "usage": ["tank_working"],
        "description": "API 4.4 - Working losses",
        "uncertainty": {"co2": 0.0, "ch4": 0.4, "n2o": 0.0},
    },
    "Tank - Breathing Losses (Oil)": {
        "code": "TankBreathOil",
        "ch4": 0.001,
        "co2": 0,
        "n2o": 0,
        "factor": 0.001,
        "unit": "kg/bbl-year",
        "usage": ["tank_breathing"],
        "description": "API 4.4 - Standing storage breathing losses",
        "uncertainty": {"co2": 0.0, "ch4": 0.4, "n2o": 0.0},
    },
    "Loading - Crude Oil (Tank Truck)": {
        "code": "LoadCrudeTruck",
        "ch4": 0.00016,
        "co2": 0,
        "n2o": 0,
        "factor": 0.00016,
        "unit": "kg/bbl",
        "usage": ["loading"],
        "description": "Truck Loading (Submerged)",
        "uncertainty": {"co2": 0.0, "ch4": 0.3, "n2o": 0.0},
    },
    "Loading - Crude Oil (Marine Vessel)": {
        "code": "LoadCrudeMarine",
        "ch4": 0.00008,
        "co2": 0,
        "n2o": 0,
        "factor": 0.00008,
        "unit": "kg/bbl",
        "usage": ["loading"],
        "uncertainty": {"co2": 0.0, "ch4": 0.3, "n2o": 0.0},
    },
    "Wastewater - Oil/Water Separator": {
        "code": "WaterSep",
        "ch4": 0.0005,
        "co2": 0,
        "n2o": 0,
        "factor": 0.0005,
        "unit": "kg/bbl water",
        "baseUnit": "bbl",
        "usage": ["separation"],
        "description": "API Section 5.4 Separator",
        "uncertainty": {"co2": 0.0, "ch4": 0.5, "n2o": 0.0},
    },
}

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
