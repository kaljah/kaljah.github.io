"""
Emission Factors Database - API Compendium 2021
Complete catalog from Sections 5, 6, and 7

All factors include:
- Segment classification (upstream/midstream/downstream)
- Process category
- Uncertainty values for CO₂, CH₄, N₂O
- Source references to API Compendium 2021

Organized by:
1. Combustion & Flaring (Section 5)
2. Vented & Process Emissions (Section 6)
3. Fugitive Emissions (Section 7)
"""

# =============================================================================
# SECTION 5: COMBUSTION & FLARING EMISSION FACTORS
# =============================================================================

COMBUSTION_FACTORS = {
    # NATURAL GAS & GASEOUS FUELS
    "Natural Gas": {
        "code": "NG",
        "hhv": 1020,  # Btu/scf
        "co2": 53.06,  # kg CO₂/MMBtu
        "ch4": 0.001,  # kg CH₄/MMBtu
        "n2o": 0.0001,  # kg N₂O/MMBtu
        "uncertainty": {"co2": 0.05, "ch4": 0.20, "n2o": 0.20},  # ±5%, ±20%, ±20%
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Upstream",
        "process_category": "stationary_combustion",
        "type": "gases",
        "source": "API Compendium 2021 Section 5, Table 5-1"
    },
    "Landfill Gas": {
        "code": "LFG",
        "hhv": 500,
        "co2": 52.07,
        "ch4": 0.0032,
        "n2o": 0.00063,
        "uncertainty": {"co2": 0.05, "ch4": 0.40, "n2o": 0.50},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Midstream",
        "process_category": "stationary_combustion",
        "type": "gases",
        "source": "API Compendium 2021 Section 5"
    },
    "Coke Oven Gas": {
        "code": "COG",
        "hhv": 590,
        "co2": 46.85,
        "ch4": 0.00048,
        "n2o": 0.0001,
        "uncertainty": {"co2": 0.02, "ch4": 0.30, "n2o": 0.40},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "gases",
        "source": "API Compendium 2021 Section 5"
    },
    "Blast Furnace Gas": {
        "code": "BFG",
        "hhv": 92,
        "co2": 274.32,
        "ch4": 0.000022,
        "n2o": 0.0001,
        "uncertainty": {"co2": 0.02, "ch4": 0.30, "n2o": 0.40},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "gases",
        "source": "API Compendium 2021 Section 5"
    },
    "Propane (Gas)": {
        "code": "LPG_Gas",
        "hhv": 2500,  # Btu/scf
        "co2": 61.46,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.01, "ch4": 0.20, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "gases",
        "source": "API Compendium 2021 Section 5"
    },
    "Refinery Fuel Gas": {
        "code": "RFG",
        "hhv": 1400,  # Btu/scf (typical)
        "co2": 57.78,
        "ch4": 0.0028,
        "n2o": 0.0001,
        "uncertainty": {"co2": 0.10, "ch4": 0.30, "n2o": 0.40},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "gases",
        "source": "API Compendium 2021 Section 5"
    },
    
    # LIQUID FUELS
    "Marine Diesel Oil": {
        "code": "MDO",
        "hhv": 138858,
        "co2": 73.19,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion", "mobile"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "liquids",
        "source": "API Compendium 2021 Section 4, Table 4-14"
    },
    "Diesel (No. 2 Fuel Oil)": {
        "code": "DSL",
        "hhv": 138000,  # Btu/gal
        "co2": 73.96,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion", "mobile"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "liquids",
        "source": "API Compendium 2021 Section 5, Table 5-1"
    },
    "Residual Fuel Oil (No. 6)": {
        "code": "RFO",
        "hhv": 150000,
        "co2": 75.10,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "liquids",
        "source": "API Compendium 2021 Section 5, Table 5-1"
    },
    "Kerosene": {
        "code": "Kero",
        "hhv": 135000,
        "co2": 75.20,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion", "mobile"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "liquids",
        "source": "API Compendium 2021 Section 5"
    },
    "Motor Gasoline": {
        "code": "GAS",
        "hhv": 125000,
        "co2": 70.22,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion", "mobile"],
        "segment": "Downstream",
        "process_category": "mobile_combustion",
        "type": "liquids",
        "source": "API Compendium 2021 Section 5"
    },
    "Jet Fuel": {
        "code": "JET",
        "hhv": 135000,
        "co2": 72.22,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion", "mobile"],
        "segment": "Downstream",
        "process_category": "mobile_combustion",
        "type": "liquids",
        "source": "API Compendium 2021 Section 5"
    },
    "Propane (Liquid/LPG)": {
        "code": "LPG_Liq",
        "hhv": 91500,
        "co2": 62.88,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion", "mobile"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "liquids",
        "source": "API Compendium 2021 Section 5"
    },
    "Ethane": {
        "code": "Ethane",
        "hhv": 69600,
        "co2": 59.60,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Midstream",
        "process_category": "stationary_combustion",
        "type": "gases",
        "source": "API Compendium 2021 Section 5"
    },
    "Crude Oil": {
        "code": "Crude",
        "hhv": 138000,
        "co2": 74.54,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.30},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Upstream",
        "process_category": "stationary_combustion",
        "type": "liquids",
        "source": "API Compendium 2021 Section 5"
    },
    
    # SOLID FUELS
    "Anthracite Coal": {
        "code": "CoalAnth",
        "hhv": 25090,  # Btu/lb
        "co2": 103.69,
        "ch4": 0.011,
        "n2o": 0.0016,
        "uncertainty": {"co2": 0.03, "ch4": 0.30, "n2o": 0.40},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "solids",
        "source": "API Compendium 2021 Section 5"
    },
    "Bituminous Coal": {
        "code": "CoalBit",
        "hhv": 24930,
        "co2": 93.26,
        "ch4": 0.011,
        "n2o": 0.0016,
        "uncertainty": {"co2": 0.03, "ch4": 0.30, "n2o": 0.40},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "solids",
        "source": "API Compendium 2021 Section 5"
    },
    "Sub-Bituminous Coal": {
        "code": "CoalSub",
        "hhv": 17250,
        "co2": 97.17,
        "ch4": 0.011,
        "n2o": 0.0016,
        "uncertainty": {"co2": 0.03, "ch4": 0.30, "n2o": 0.40},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "solids",
        "source": "API Compendium 2021 Section 5"
    },
    "Lignite Coal": {
        "code": "CoalLig",
        "hhv": 14210,
        "co2": 97.72,
        "ch4": 0.011,
        "n2o": 0.0016,
        "uncertainty": {"co2": 0.03, "ch4": 0.30, "n2o": 0.40},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "solids",
        "source": "API Compendium 2021 Section 5"
    },
    "Petroleum Coke": {
        "code": "PetCoke",
        "hhv": 30000,
        "co2": 102.41,
        "ch4": 0.003,
        "n2o": 0.0006,
        "uncertainty": {"co2": 0.03, "ch4": 0.30, "n2o": 0.40},
        "unit": "kg/MMBtu",
        "usage": ["combustion"],
        "segment": "Downstream",
        "process_category": "stationary_combustion",
        "type": "solids",
        "source": "API Compendium 2021 Section 5"
    }
}

# FLARING EMISSION FACTORS (Section 5.2)
FLARING_FACTORS = {
    "Natural Gas (Flaring - Elevated)": {
        "code": "NG_Flare_Elev",
        "co2": 1.92,  # kg CO₂/m³ flared
        "ch4": 0.012,  # kg CH₄/m³ flared
        "n2o": 0.00001,
        "combustion_efficiency_co2": 0.98,  # 98% for CO₂ formation
        "combustion_efficiency_ch4": 0.98,  # 98% for CH₄ destruction (production flare)
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.50},
        "unit": "kg/m³",
        "usage": ["flaring"],
        "segment": "Upstream",
        "process_category": "flaring",
        "type": "gases",
        "source": "API Compendium 2021 Section 5.2, Equations 5-3 & 5-4"
    },
    "Natural Gas (Flaring - Ground)": {
        "code": "NG_Flare_Ground",
        "co2": 1.88,
        "ch4": 0.024,
        "n2o": 0.00001,
        "combustion_efficiency_co2": 0.98,
        "combustion_efficiency_ch4": 0.96,  # 96% for ground flares
        "uncertainty": {"co2": 0.03, "ch4": 0.30, "n2o": 0.50},
        "unit": "kg/m³",
        "usage": ["flaring"],
        "segment": "Upstream",
        "process_category": "flaring",
        "type": "gases",
        "source": "API Compendium 2021 Section 5.2"
    },
    "Natural Gas (Flaring)": {
        "code": "NG_Flare",
        "co2": 1.92,
        "ch4": 0.012,
        "n2o": 0.00001,
        "combustion_efficiency_co2": 0.98,
        "combustion_efficiency_ch4": 0.98,
        "uncertainty": {"co2": 0.02, "ch4": 0.25, "n2o": 0.50},
        "unit": "kg/m³",
        "usage": ["flaring"],
        "segment": "Upstream",
        "process_category": "flaring",
        "type": "gases",
        "source": "API Compendium 2021 Section 5.2"
    },
    "Natural Gas (Flaring - Enclosed)": {
        "code": "NG_Flare_Enc",
        "co2": 1.94,
        "ch4": 0.006,
        "n2o": 0.00001,
        "combustion_efficiency_co2": 0.98,
        "combustion_efficiency_ch4": 0.99,  # 99% for enclosed flares
        "uncertainty": {"co2": 0.02, "ch4": 0.20, "n2o": 0.50},
        "unit": "kg/m³",
        "usage": ["flaring"],
        "segment": "Upstream",
        "process_category": "flaring",
        "type": "gases",
        "source": "API Compendium 2021 Section 5.2"
    },
    "Associated Gas (Flaring)": {
        "code": "AG_Flare",
        "co2": 2.15,
        "ch4": 0.018,
        "n2o": 0.00001,
        "combustion_efficiency_co2": 0.98,
        "combustion_efficiency_ch4": 0.98,
        "uncertainty": {"co2": 0.03, "ch4": 0.25, "n2o": 0.50},
        "unit": "kg/m³",
        "usage": ["flaring"],
        "segment": "Upstream",
        "process_category": "flaring",
        "type": "gases",
        "source": "API Compendium 2021 Section 5.2"
    },
    "Sour Gas (Flaring)": {
        "code": "SG_Flare",
        "co2": 2.30,
        "ch4": 0.015,
        "n2o": 0.00001,
        "combustion_efficiency_co2": 0.98,
        "combustion_efficiency_ch4": 0.98,
        "uncertainty": {"co2": 0.03, "ch4": 0.25, "n2o": 0.50},
        "unit": "kg/m³",
        "usage": ["flaring"],
        "segment": "Upstream",
        "process_category": "flaring",
        "type": "gases",
        "source": "API Compendium 2021 Section 5.2"
    },
    "Refinery Gas (Flaring)": {
        "code": "REF_Flare",
        "co2": 2.10,
        "ch4": 0.025,
        "n2o": 0.00001,
        "combustion_efficiency_co2": 0.98,
        "combustion_efficiency_ch4": 0.95,  # 95% for refinery flares
        "uncertainty": {"co2": 0.03, "ch4": 0.30, "n2o": 0.50},
        "unit": "kg/m³",
        "usage": ["flaring"],
        "segment": "Downstream",
        "process_category": "flaring",
        "type": "gases",
        "source": "API Compendium 2021 Section 5.2, Eq 5-4"
    }
}

# =============================================================================
# SECTION 6 VENTED & PROCESS EMISSION FACTORS
# =============================================================================

VENTED_FACTORS = {
    "Natural Gas (Venting/Blowdown)": {
        "code": "NG_Vent",
        "co2": 0.054,  # kg CO₂/m³
        "ch4": 0.67,  # kg CH₄/m³
        "n2o": 0,
        "uncertainty": {"co2": 0.05, "ch4": 0.30, "n2o": 0.50},
        "unit": "kg/m³",
        "usage": ["venting"],
        "segment": "Upstream",
        "process_category": "venting",
        "type": "gases",
        "source": "API Compendium 2021 Section 6"
    },
    "Asphalt": {
        "code": "Asphalt",
        "type": "equipment",
        "ch4": 0.05 * 0.453592,  # 0.02268 kg/ton
        "co2": 23.0 * 0.453592,  # 10.4326 kg/ton
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0},
        "unit": "kg/ton",
        "segment": "Downstream",
        "process_category": "asphalt_blowing",
        "source": "API Compendium 2021 Section 6, Table 6-52"
    }
}

# CHEMICAL PRODUCTION FACTORS (Section 6, Table 6-167)
CHEMICAL_PRODUCTION_FACTORS = {
    "Acrylonitrile": {
        "code": "ACN_Prod",
        "co2": 1.00,  # tonne CO₂/tonne product
        "ch4": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.15, "ch4": 0, "n2o": 0},
        "unit": "tonne CO₂/tonne product",
        "usage": ["chemical_production"],
        "segment": "Downstream",
        "process_category": "chemical_production",
        "source": "API Compendium 2021 Section 6, Table 6-167"
    },
    "Carbon Black": {
        "code": "CB_Prod",
        "co2": 2.63,
        "ch4": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.15, "ch4": 0, "n2o": 0},
        "unit": "tonne CO₂/tonne product",
        "usage": ["chemical_production"],
        "segment": "Downstream",
        "process_category": "chemical_production",
        "source": "API Compendium 2021 Section 6, Table 6-167"
    },
    "Ethylene": {
        "code": "ETH_Prod",
        "co2": 0.77,
        "ch4": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.10, "ch4": 0, "n2o": 0},
        "unit": "tonne CO₂/tonne product",
        "usage": ["chemical_production"],
        "segment": "Downstream",
        "process_category": "chemical_production",
        "source": "API Compendium 2021 Section 6, Table 6-167"
    },
    "Ethylene Dichloride": {
        "code": "EDC_Prod",
        "co2": 0.041,
        "ch4": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.15, "ch4": 0, "n2o": 0},
        "unit": "tonne CO₂/tonne product",
        "usage": ["chemical_production"],
        "segment": "Downstream",
        "process_category": "chemical_production",
        "source": "API Compendium 2021 Section 6, Table 6-167"
    },
    "Ethylene Oxide": {
        "code": "ETO_Prod",
        "co2": 0.46,
        "ch4": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.10, "ch4": 0, "n2o": 0},
        "unit": "tonne CO₂/tonne product",
        "usage": ["chemical_production"],
        "segment": "Downstream",
        "process_category": "chemical_production",
        "source": "API Compendium 2021 Section 6, Table 6-167"
    },
    "Methanol": {
        "code": "MEOH_Prod",
        "co2": 0.67,
        "ch4": 0.0023,  # 2.3 kg CH₄/tonne methanol
        "n2o": 0,
        "uncertainty": {"co2": 0.10, "ch4": 0.20, "n2o": 0},
        "unit": "tonne CO₂/tonne product",
        "usage": ["chemical_production"],
        "segment": "Downstream",
        "process_category": "chemical_production",
        "source": "API Compendium 2021 Section 6, Table 6-167"
    }
}

# N₂O EMISSION FACTORS (Section 6, pg 407)
N2O_PRODUCTION_FACTORS = {
    "Nitric Acid - With NSCR": {
        "code": "HNO3_NSCR",
        "co2": 0,
        "ch4": 0,
        "n2o": 2.0,  # kg N₂O/tonne HNO₃
        "uncertainty": {"co2": 0, "ch4": 0, "n2o": 0.10},
        "unit": "kg N₂O/tonne product",
        "usage": ["nitric_acid_production"],
        "segment": "Downstream",
        "process_category": "nitric_acid_production",
        "source": "API Compendium 2021 Section 6, pg 407"
    },
    "Nitric Acid - Without NSCR": {
        "code": "HNO3_NoNSCR",
        "co2": 0,
        "ch4": 0,
        "n2o": 9.0,  # kg N₂O/tonne HNO₃
        "uncertainty": {"co2": 0, "ch4": 0, "n2o": 0.20},
        "unit": "kg N₂O/tonne product",
        "usage": ["nitric_acid_production"],
        "segment": "Downstream",
        "process_category": "nitric_acid_production",
        "source": "API Compendium 2021 Section 6, pg 407"
    },
    "Adipic Acid - Thermal Abatement": {
        "code": "AA_Thermal",
        "co2": 0,
        "ch4": 0,
        "n2o": 13.0,  # kg N₂O/tonne product
        "uncertainty": {"co2": 0, "ch4": 0, "n2o": 0.10},
        "unit": "kg N₂O/tonne product",
        "usage": ["adipic_acid_production"],
        "segment": "Downstream",
        "process_category": "adipic_acid_production",
        "source": "API Compendium 2021 Section 6, pg 407"
    },
    "Adipic Acid - Catalytic Abatement": {
        "code": "AA_Catalytic",
        "co2": 0,
        "ch4": 0,
        "n2o": 53.0,  # kg N₂O/tonne product
        "uncertainty": {"co2": 0, "ch4": 0, "n2o": 0.15},
        "unit": "kg N₂O/tonne product",
        "usage": ["adipic_acid_production"],
        "segment": "Downstream",
        "process_category": "adipic_acid_production",
        "source": "API Compendium 2021 Section 6, pg 407"
    },
    "Adipic Acid - Uncontrolled": {
        "code": "AA_Uncontrolled",
        "co2": 0,
        "ch4": 0,
        "n2o": 300.0,  # kg N₂O/tonne product
        "uncertainty": {"co2": 0, "ch4": 0, "n2o": 0.30},
        "unit": "kg N₂O/tonne product",
        "usage": ["adipic_acid_production"],
        "segment": "Downstream",
        "process_category": "adipic_acid_production",
        "source": "API Compendium 2021 Section 6, pg 407"
    }
}

# Merge all API factors
API_FACTORS = {
    **COMBUSTION_FACTORS,
    **FLARING_FACTORS,
    **VENTED_FACTORS,
    **CHEMICAL_PRODUCTION_FACTORS,
    **N2O_PRODUCTION_FACTORS
}

# =============================================================================
# SECTION 7: FUGITIVE & EQUIPMENT EMISSION FACTORS  
# =============================================================================

EQUIPMENT_FACTORS = {
    # ========== PNEUMATIC DEVICES ==========
    "Pneumatic Controller - High Bleed (>6 scfh)": {
        "code": "HighBleed",
        "type": "pneumatic",
        "ch4": 8.304,  # tonnes CH₄/controller/yr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonnes CH₄/yr",
        "segment": "Upstream",
        "process_category": "pneumatic_devices",
        "type": "equipment",
        "description": "Continuous bleed pneumatic controller in gas processing",
        "source": "API Compendium 2021 Section 6, Table 6-34"
    },
    "Pneumatic Controller - Low Bleed (<6 scfh)": {
        "code": "LowBleed",
        "type": "pneumatic",
        "ch4": 0.0939,  # tonnes CH₄/controller/yr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonnes CH₄/yr",
        "segment": "Upstream",
        "process_category": "pneumatic_devices",
        "type": "equipment",
        "description": "Pneumatic/hydraulic valve operator in gas processing",
        "source": "API Compendium 2021 Section 6, Table 6-34"
    },
    "Pneumatic Controller - Intermittent": {
        "code": "Intermittent",
        "type": "pneumatic",
        "ch4": 0.4,  # tonnes CH₄/controller/yr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonnes CH₄/yr",
        "segment": "Midstream",
        "process_category": "pneumatic_devices",
        "type": "equipment",
        "description": "Intermittent vent controller in transmission/storage",
        "source": "API Compendium 2021 Section 6, Table 6-42"
    },
    "Pneumatic Controller - Continuous Vent (T&S)": {
        "code": "ContinuousVentTS",
        "type": "pneumatic",
        "ch4": 3.5,  # tonnes CH₄/controller/yr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonnes CH₄/yr",
        "segment": "Midstream",
        "process_category": "pneumatic_devices",
        "type": "equipment",
        "description": "Continuous vent controller in transmission/storage",
        "source": "API Compendium 2021 Section 6, Table 6-42"
    },
    
    # ========== STORAGE TANKS (TANK FLASHING) ==========
    "Tank - Crude Oil (Small, ≤10 bbl/d)": {
        "code": "TankCrudeSmall",
        "type": "tank",
        "ch4": 0.18,  # kg CH₄/bbl
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "kg CH₄/bbl",
        "segment": "Upstream",
        "process_category": "storage_tanks",
        "type": "equipment",
        "description": "Crude oil flashing, small tank (≤ 10 bbl/d)",
        "source": "API Compendium 2021 Section 6, Table 6-4"
    },
    "Tank - Crude Oil (Large, >10 bbl/d)": {
        "code": "TankCrudeLarge",
        "type": "tank",
        "ch4": 0.193,  # kg CH₄/bbl (matches Table 6-22)
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "kg CH₄/bbl",
        "segment": "Upstream",
        "process_category": "storage_tanks",
        "type": "equipment",
        "description": "Crude oil flashing, large tank (> 10 bbl/d)",
        "source": "API Compendium 2021 Section 6, Table 6-4"
    },
    "Tank - Production Condensate (Small, ≤10 bbl/d)": {
        "code": "TankProdSmall",
        "type": "tank",
        "ch4": 1.56,  # kg CH₄/bbl
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "kg CH₄/bbl",
        "segment": "Upstream",
        "process_category": "storage_tanks",
        "type": "equipment",
        "description": "Production condensate flashing, small tank (≤ 10 bbl/d)",
        "source": "API Compendium 2021 Section 6, Table 6-4"
    },
    "Tank - Production Condensate (Large, >10 bbl/d)": {
        "code": "TankProdLarge",
        "type": "tank",
        "ch4": 1.16,  # kg CH₄/bbl
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "kg CH₄/bbl",
        "segment": "Upstream",
        "process_category": "storage_tanks",
        "type": "equipment",
        "description": "Production condensate flashing, large tank (> 10 bbl/d)",
        "source": "API Compendium 2021 Section 6, Table 6-4"
    },
    "Tank - Gas-Well Condensate (Small, ≤10 bbl/d)": {
        "code": "TankGasSmall",
        "type": "tank",
        "ch4": 2.65,  # kg CH₄/bbl
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "kg CH₄/bbl",
        "segment": "Upstream",
        "process_category": "storage_tanks",
        "type": "equipment",
        "description": "Gas-well condensate flashing, small tank (≤ 10 bbl/d)",
        "source": "API Compendium 2021 Section 6, Table 6-4"
    },
    "Tank - Gas-Well Condensate (Large, >10 bbl/d)": {
        "code": "TankGasLarge",
        "type": "tank",
        "ch4": 2.05,  # kg CH₄/bbl
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "kg CH₄/bbl",
        "segment": "Upstream",
        "process_category": "storage_tanks",
        "type": "equipment",
        "description": "Gas-well condensate flashing, large tank (> 10 bbl/d)",
        "source": "API Compendium 2021 Section 6, Table 6-4"
    },
    
    # ========== DRILLING ==========
    "Drilling - Mud Degassing (Water Based)": {
        "code": "MudWater",
        "type": "drilling",
        "ch4": 0.15,  # kg CH₄/m³ mud (matches Section 6.2.1)
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.10, "ch4": 0.50, "n2o": 0.10},
        "unit": "kg CH₄/m³",
        "segment": "Upstream",
        "process_category": "drilling",
        "type": "equipment",
        "description": "Drilling mud degassing - water based",
        "source": "API Compendium 2021 Section 6.2"
    },
    "Drilling - Mud Degassing (Oil Based)": {
        "code": "MudOil",
        "type": "drilling",
        "ch4": 37.5,  # kg CH₄/bbl mud
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.10, "ch4": 0.50, "n2o": 0.10},
        "unit": "kg CH₄/bbl mud",
        "segment": "Upstream",
        "process_category": "drilling",
        "type": "equipment",
        "description": "Drilling mud degassing - oil based (diesel)",
        "source": "API Compendium 2021 Section 6.2"
    },
    
    # ========== DEHYDRATORS ==========
    "Dehydrator - Glycol (Uncontrolled)": {
        "code": "DehyUncont",
        "type": "dehydrator",
        "ch4": 0.177,  # scf CH₄/MMscf throughput
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0.30},
        "unit": "scf/MMscf",
        "segment": "Midstream",
        "process_category": "dehydrator",
        "type": "equipment",
        "description": "Glycol dehydrator venting (uncontrolled)",
        "source": "API Compendium 2021 Section 6.11"
    },
    
    # ========== UPSTREAM: OIL WELLHEADS (Table 7-9) ==========
    "Wellhead - Oil (Heavy Crude)": {
        "code": "WellOilHeavy",
        "type": "wellhead",
        "ch4": 6.63E-07,  # tonne CH₄/well/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/well/hr",
        "segment": "Upstream",
        "process_category": "wellhead_fugitive",
        "type": "equipment",
        "description": "Oil wellhead fugitive emissions - heavy crude (API < 20°)",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-9"
    },
    "Wellhead - Oil (Light Crude)": {
        "code": "WellOilLight",
        "type": "wellhead",
        "ch4": 1.56E-05,  # tonne CH₄/well/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/well/hr",
        "segment": "Upstream",
        "process_category": "wellhead_fugitive",
        "type": "equipment",
        "description": "Oil wellhead fugitive emissions - light crude (API ≥ 20°)",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-9"
    },
    "Wellhead - Gas": {
        "code": "WellGas",
        "type": "wellhead",
        "ch4": 1.80E-05,  # tonne CH₄/well/hr  
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.257, "n2o": 0},
        "unit": "tonne CH₄/well/hr",
        "segment": "Upstream",
        "process_category": "wellhead_fugitive",
        "type": "equipment",
        "description": "Gas wellhead fugitive emissions",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-10"
    },
    
    # ========== UPSTREAM: SEPARATORS (Tables 7-9, 7-10) ==========
    "Separator - Heavy Crude": {
        "code": "SepHeavy",
        "type": "separator",
        "ch4": 6.79E-07,  # tonne CH₄/separator/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/separator/hr",
        "segment": "Upstream",
        "process_category": "separator_fugitive",
        "type": "equipment",
        "description": "Separator fugitive emissions - heavy crude",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-9"
    },
    "Separator - Light Crude": {
        "code": "SepLight",
        "type": "separator",
        "ch4": 4.10E-05,  # tonne CH₄/separator/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/separator/hr",
        "segment": "Upstream",
        "process_category": "separator_fugitive",
        "type": "equipment",
        "description": "Separator fugitive emissions - light crude",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-9"
    },
    "Separator - Gas Production": {
        "code": "SepGas",
        "type": "separator",
        "ch4": 4.42E-05,  # tonne CH₄/separator/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.879, "n2o": 0},
        "unit": "tonne CH₄/separator/hr",
        "segment": "Upstream",
        "process_category": "separator_fugitive",
        "description": "Separator fugitive emissions - gas production",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-10"
    },
    
    # ========== UPSTREAM: COMPRESSORS (Tables 7-9, 7-10) ==========
    "Compressor - Small Reciprocating": {
        "code": "CompSmall",
        "type": "compressor",
        "ch4": 3.69E-05,  # tonne CH₄/compressor/hr (light crude)
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 1.00, "n2o": 0},
        "unit": "tonne CH₄/compressor/hr",
        "segment": "Upstream",
        "process_category": "compressor_fugitive",
        "type": "equipment",
        "description": "Small reciprocating compressor fugitive emissions",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-9"
    },
    "Compressor - Large Reciprocating": {
        "code": "CompLarge",
        "type": "compressor",
        "ch4": 1.31E-02,  # tonne CH₄/compressor/hr (light crude)
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 1.00, "n2o": 0},
        "unit": "tonne CH₄/compressor/hr",
        "segment": "Upstream",
        "process_category": "compressor_fugitive",
        "type": "equipment",
        "description": "Large reciprocating compressor fugitive emissions",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-9"
    },
    "Compressor - Gas Production Small Recip": {
        "code": "CompGasSmall",
        "type": "compressor",
        "ch4": 2.12E-04,  # tonne CH₄/compressor/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 1.27, "n2o": 0},
        "unit": "tonne CH₄/compressor/hr",
        "segment": "Upstream",
        "process_category": "compressor_fugitive",
        "type": "equipment",
        "description": "Small reciprocating gas compressor in production",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-10"
    },
    "Compressor - Gas Production Large Recip": {
        "code": "CompGasLarge",
        "type": "compressor",
        "ch4": 1.22E-02,  # tonne CH₄/compressor/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 2.02, "n2o": 0},
        "unit": "tonne CH₄/compressor/hr",
        "segment": "Upstream", 
        "process_category": "compressor_fugitive",
        "type": "equipment",
        "description": "Large reciprocating gas compressor in production",
        "source": "API Compendium 2021 Section 7.2.2, Table 7-10"
    },
    
    # ========== MIDSTREAM: GATHERING & BOOSTING (Table 7-29) ==========
    "Gathering - AGRU": {
        "code": "GathAGRU",
        "type": "equipment",
        "ch4": 6.83E-05,  # tonne CH₄/unit/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.46, "n2o": 0},
        "unit": "tonne CH₄/unit/hr",
        "segment": "Midstream",
        "process_category": "gathering_boosting",
        "type": "equipment",
        "description": "AGRU fugitive emissions in gathering",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-29"
    },
    "Gathering - Compressor": {
        "code": "GathComp",
        "type": "equipment",
        "ch4": 1.84E-03,  # tonne CH₄/unit/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.14, "n2o": 0},
        "unit": "tonne CH₄/unit/hr",
        "segment": "Midstream",
        "process_category": "gathering_boosting",
        "type": "equipment",
        "description": "Compressor fugitive emissions in gathering",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-29"
    },
    "Gathering - Dehydrator": {
        "code": "GathDehy",
        "type": "equipment",
        "ch4": 5.69E-05,  # tonne CH₄/unit/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.13, "n2o": 0},
        "unit": "tonne CH₄/unit/hr",
        "segment": "Midstream",
        "process_category": "gathering_boosting",
        "type": "equipment",
        "description": "Dehydrator fugitive emissions in gathering",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-29"
    },
    "Gathering - Separator": {
        "code": "GathSep",
        "type": "equipment",
        "ch4": 1.05E-05,  # tonne CH₄/unit/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.12, "n2o": 0},
        "unit": "tonne CH₄/unit/hr",
        "segment": "Midstream",
        "process_category": "gathering_boosting",
        "type": "equipment",
        "description": "Separator fugitive emissions in gathering",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-29"
    },
    "Gathering - Tank": {
        "code": "GathTank",
        "type": "equipment",
        "ch4": 6.4E-04,  # tonne CH₄/unit/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.099, "n2o": 0},
        "unit": "tonne CH₄/unit/hr",
        "segment": "Midstream",
        "process_category": "gathering_boosting",
        "type": "equipment",
        "description": "Tank fugitive emissions in gathering",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-29"
    },
    
    # ========== MIDSTREAM: COMPONENT-LEVEL FUGITIVE (Table 7-30) ==========
    "Component - Connector (Non-Compressor)": {
        "code": "ConnNonComp",
        "type": "component",
        "ch4": 9.79E-07,  # tonne CH₄/hr/source
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0.30},
        "unit": "tonne CH₄/hr/source",
        "segment": "Midstream",
        "process_category": "fugitive_component",
        "type": "equipment",
        "description": "Connector fugitive emissions (non-compressor area)",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-30"
    },
    "Component - Block Valve": {
        "code": "BlockValve",
        "type": "component",
        "ch4": 4.36E-06,  # tonne CH₄/hr/source
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0.30},
        "unit": "tonne CH₄/hr/source",
        "segment": "Midstream",
        "process_category": "fugitive_component",
        "type": "equipment",
        "description": "Block valve fugitive emissions",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-30"
    },
    "Component - Control Valve": {
        "code": "ControlValve",
        "type": "component",
        "ch4": 1.11E-05,  # tonne CH₄/hr/source
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0.30},
        "unit": "tonne CH₄/hr/source",
        "segment": "Midstream",
        "process_category": "fugitive_component",
        "type": "equipment",
        "description": "Control valve fugitive emissions",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-30"
    },
    "Component - Pressure Relief Valve": {
        "code": "PRV",
        "type": "component",
        "ch4": 1.39E-07,  # tonne CH₄/hr/source
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0.30},
        "unit": "tonne CH₄/hr/source",
        "segment": "Midstream",
        "process_category": "fugitive_component",
        "type": "equipment",
        "description": "Pressure relief valve fugitive emissions",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-30"
    },
    "Component - Pressure Regulator": {
        "code": "Regulator",
        "type": "component",
        "ch4": 1.87E-06,  # tonne CH₄/hr/source
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0.30},
        "unit": "tonne CH₄/hr/source",
        "segment": "Midstream",
        "process_category": "fugitive_component",
        "type": "equipment",
        "description": "Pressure regulator fugitive emissions",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-30"
    },
    "Component - Compressor Seal": {
        "code": "CompSeal",
        "type": "component",
        "ch4": 1.54E-04,  # tonne CH₄/hr/source
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0.30, "ch4": 0.30, "n2o": 0.30},
        "unit": "tonne CH₄/hr/source",
        "segment": "Midstream",
        "process_category": "fugitive_component",
        "type": "equipment",
        "description": "Compressor seal fugitive emissions",
        "source": "API Compendium 2021 Section 7.2.3, Table 7-30"
    },
    
    # ========== MIDSTREAM: GAS PROCESSING (Table 7-35) ==========
    "Processing - Reciprocating Compressor": {
        "code": "ProcRecipComp",
        "type": "compressor",
        "ch4": 8.95E-03,  # tonne CH₄/compressor/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.952, "n2o": 0},
        "unit": "tonne CH₄/compressor/hr",
        "segment": "Midstream",
        "process_category": "gas_processing",
        "type": "equipment",
        "description": "Reciprocating compressor in gas processing",
        "source": "API Compendium 2021 Section 7.3, Table 7-35"
    },
    "Processing - Centrifugal Compressor": {
        "code": "ProcCentComp",
        "type": "compressor",
        "ch4": 1.70E-02,  # tonne CH₄/compressor/hr
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.518, "n2o": 0},
        "unit": "tonne CH₄/compressor/hr",
        "segment": "Midstream",
        "process_category": "gas_processing",
        "type": "equipment",
        "description": "Centrifugal compressor in gas processing",
        "source": "API Compendium 2021 Section 7.3, Table 7-35"
    },
    
    # ========== DOWNSTREAM: LNG OPERATIONS (Table 7-76) ==========
    "LNG - Storage Station": {
        "code": "LNGStorage",
        "type": "facility",
        "ch4": 4.39E-04,  # tonne CH₄/facility
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/facility",
        "segment": "Downstream",
        "process_category": "lng_operations",
        "type": "equipment",
        "description": "LNG storage station fugitive emissions",
        "source": "API Compendium 2021 Section 7.3.6, Table 7-76"
    },
    "LNG - Import Terminal": {
        "code": "LNGImport",
        "type": "facility",
        "ch4": 3.29E-04,  # tonne CH₄/facility
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/facility",
        "segment": "Downstream",
        "process_category": "lng_operations",
        "type": "equipment",
        "description": "LNG import terminal fugitive emissions",
        "source": "API Compendium 2021 Section 7.3.6, Table 7-76"
    },
    "LNG - Export Terminal": {
        "code": "LNGExport",
        "type": "facility",
        "ch4": 1.26E-03,  # tonne CH₄/facility
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/facility",
        "segment": "Downstream",
        "process_category": "lng_operations",
        "type": "equipment",
        "description": "LNG export terminal fugitive emissions",
        "source": "API Compendium 2021 Section 7.3.6, Table 7-76"
    },
    
    # ========== DOWNSTREAM: REFINERY GAS SYSTEMS (Table 7-80) ==========
    "Refinery - Fuel Gas System (50-99k bbl/day)": {
        "code": "RefFuelGasSmall",
        "type": "facility",
        "ch4": 3.75E-04,  # tonnes CH₄/10³ bbl feedstock
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonnes CH₄/10³ bbl feedstock",
        "segment": "Downstream",
        "process_category": "refinery_fugitive",
        "type": "equipment",
        "description": "Refinery fuel gas system (50,000-99,000 bbl/day)",
        "source": "API Compendium 2021 Section 7.4.1, Table 7-80"
    },
    "Refinery - Fuel Gas System (100-199k bbl/day)": {
        "code": "RefFuelGasLarge",
        "type": "facility",
        "ch4": 1.41E-03,  # tonnes CH₄/10³ bbl feedstock
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonnes CH₄/10³ bbl feedstock",
        "segment": "Downstream",
        "process_category": "refinery_fugitive",
        "type": "equipment",
        "description": "Refinery fuel gas system (100,000-199,000 bbl/day)",
        "source": "API Compendium 2021 Section 7.4.1, Table 7-80"
    },
    
    # ========== OFFSHORE PRODUCTION (Table 7-3) ==========
    "Offshore - Oil Production (Facility)": {
        "code": "OffshoreOil",
        "type": "facility",
        "ch4": 3.86E-06,  # tonne CH₄/bbl produced
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/bbl produced",
        "segment": "Upstream",
        "process_category": "wellhead_fugitive",
        "type": "equipment",
        "description": "Offshore oil production facility-level fugitive emissions",
        "source": "API Compendium 2021 Section 7.2, Table 7-3"
    },
    "Offshore - Gas Production (Facility)": {
        "code": "OffshoreGas",
        "type": "facility",
        "ch4": 1.040E-02,  # tonne CH₄/10⁶ scf produced
        "co2": 0,
        "n2o": 0,
        "uncertainty": {"co2": 0, "ch4": 0.30, "n2o": 0},
        "unit": "tonne CH₄/10⁶ scf produced",
        "segment": "Upstream",
        "process_category": "wellhead_fugitive",
        "type": "equipment",
        "description": "Offshore gas production facility-level fugitive emissions",
        "source": "API Compendium 2021 Section 7.2, Table 7-3"
    }
}

# Merge all emission factors
ALL_EMISSION_FACTORS = {
    **API_FACTORS,
    **EQUIPMENT_FACTORS
}

# Correlation equations for screening-based fugitive estimation (Section 7.3.1.6)
CORRELATION_EQUATIONS = {
    "gas_valve": {
        "A": 2.29e-6,
        "B": 0.746,
        "max_ppm": 100000,
        "pegged_10k": 0.064,  # kg/hr
        "pegged_100k": 0.11,
        "description": "Valves in gas service",
        "unit": "kg/hr/component"
    },
    "light_liquid_valve": {
        "A": 6.41e-6,
        "B": 0.797,
        "max_ppm": 100000,
        "pegged_10k": 0.074,
        "pegged_100k": 0.15,
        "description": "Valves in light liquid service",
        "unit": "kg/hr/component"
    },
    "light_liquid_pump": {
        "A": 5.03e-5,
        "B": 0.610,
        "max_ppm": 100000,
        "pegged_10k": 0.16,
        "pegged_100k": 0.68,
        "description": "Pump seals in light liquid service",
        "unit": "kg/hr/component"
    },
    "connector": {
        "A": 1.53e-6,
        "B": 0.735,
        "max_ppm": 100000,
        "pegged_10k": 0.028,
        "pegged_100k": 0.030,
        "description": "Connectors in gas service",
        "unit": "kg/hr/component"
    },
    "flange": {
        "A": 4.61e-6,
        "B": 0.703,
        "max_ppm": 100000,
        "pegged_10k": 0.085,
        "pegged_100k": 0.089,
        "description": "Flanges in gas service",
        "unit": "kg/hr/component"
    },
    "open_ended_line": {
        "A": 2.20e-6,
        "B": 0.704,
        "max_ppm": 100000,
        "pegged_10k": 0.012,
        "pegged_100k": 0.014,
        "description": "Open-ended lines in gas service",
        "unit": "kg/hr/component"
    },
    "other": {
        "A": 1.36e-5,
        "B": 0.589,
        "max_ppm": 100000,
        "pegged_10k": 0.073,
        "pegged_100k": 0.11,
        "description": "Other components in gas service",
        "unit": "kg/hr/component"
    }
}

# Helper functions for emission factor access
def get_factor_by_segment(segment):
    """
    Returns all emission factors applicable to the given segment.
    
    Args:
        segment (str): One of 'Upstream', 'Midstream', 'Downstream'
    
    Returns:
        dict: Filtered emission factors dictionary
    """
    return {
        factor_name: factor_data
        for factor_name, factor_data in ALL_EMISSION_FACTORS.items()
        if factor_data.get("segment") == segment
    }

def get_factor_by_process_category(process_category):
    """
    Returns all emission factors for the given process category.
    
    Args:
        process_category (str): Process category ID
    
    Returns:
        dict: Filtered emission factors dictionary
    """
    return {
        factor_name: factor_data
        for factor_name, factor_data in ALL_EMISSION_FACTORS.items()
        if factor_data.get("process_category") == process_category
    }

def get_factors_by_segment_and_category(segment, process_category):
    """
    Returns all emission factors for a specific segment and process category.
    
    Args:
        segment (str): One of 'Upstream', 'Midstream', 'Downstream'
        process_category (str): Process category ID
    
    Returns:
        dict: Filtered emission factors dictionary
    """
    return {
        factor_name: factor_data
        for factor_name, factor_data in ALL_EMISSION_FACTORS.items()
        if (factor_data.get("segment") == segment and 
            factor_data.get("process_category") == process_category)
    }
