"""
Emission Factor Database
Source: API Compendium of Greenhouse Gas Emissions Methodologies for the Oil and Natural Gas Industry (2021/2023)
        & EPA/GHG Protocol where proprietary API data is not publicly indexed.
"""

FACTORS = {
    "combustion": {
        "natural_gas": {
            "units": "kg/MMBtu",
            "co2": 53.06,
            "ch4": 0.001,
            "n2o": 0.0001,
            "source": "API Compendium 2021 / GHG Protocol",
            "hhv": 1026, # Btu/scf
            "density": 0.042 # lb/scf (approx)
        },
        "diesel": {
            "units": "kg/gal",
            "co2": 10.21,
            "ch4": 0.00057,
            "n2o": 0.00026,
            "source": "API Compendium 2021 / GHG Protocol",
            "hhv": 138000, # Btu/gal
            "density": 7.1 # lb/gal
        },
        "crude_oil": {
            "units": "kg/gal",
            "co2": 11.0,  # Approx default
            "ch4": 0.0004,
            "n2o": 0.00008,
            "source": "Estimated / EPA Default",
            "hhv": 138000, # Btu/gal (approx)
            "density": 7.1 # lb/gal
        }
    },
    "flaring": {
        "destruction_efficiency": {
            "default": 0.98,
            "high_efficiency": 0.99,
            "unlit": 0.00
        },
        "methane_gwp": 25, # AR4 (Common in O&G reporting) or 28 (AR5)
        "co2_gwp": 1
    },
    "fugitives": {
        "leaker_factors": {
            # Average factors for O&G Production (kg/hr/source) - EPA/API Proxies
            "valves": {"gas": 0.0045, "light_oil": 0.0025, "heavy_oil": 0.00023},
            "connectors": {"gas": 0.0002, "light_oil": 0.0002, "heavy_oil": 0.00003},
            "flanges": {"gas": 0.00039, "light_oil": 0.00011, "heavy_oil": 0.0000003},
            "open_ended_lines": {"gas": 0.002, "light_oil": 0.0014, "heavy_oil": 0.00014},
            "pumps": {"gas": 0.0024, "light_oil": 0.013, "heavy_oil": 0.005}
        }
    },
    "venting": {
        "pneumatic_controllers": {
            # API 2021 Updated Factors (Approximate from summaries)
            "low_bleed": 0.1, # scf/hr
            "intermittent": 13.5, # scf/hr
            "high_bleed": 37.3 # scf/hr
        }
    },
    "tanks": {
        "saturation_factors": {
            "submerged_pipe": 0.6,
            "splash_loading": 1.45,
            "vapor_balance": 1.0
        },
        "defaults": {
            "vapor_molecular_weight": {
                "crude_oil": 50.0, # lb/lb-mole (approx)
                "condensate": 66.0,
                "gasoline": 66.0
            }
        }
    },
    "dehydrators": {
        "emission_factors": {
            # Simplified factors if GLYCalc not available (kg/MMscf throughput)
            # Source: EPA/API proxies
            "uncontrolled_teg": 150.0 # kg CH4 per MMscf (Very rough proxy)
        }
    },
    "loading": {
        "saturation_factors": {
            "submerged_pipe": 0.6,
            "submerged_pipe_balance": 1.0,
            "splash_loading": 1.45,
            "splash_loading_balance": 1.0
        }
    },
    "electricity": {
        "emission_factors": {
            "us_average_2022": 0.393, # kg CO2e/kWh (eGRID 2022 approx)
            "global_average_2024": 0.445, # kg CO2e/kWh (IEA 2024)
            "eu_average_2022": 0.255 # kg CO2e/kWh (EEA approx)
        }
    },
    "amine": {
        "emission_factors": {
            "generic_amine": 2.2 # kg CO2/m3 gas throughput (Simplified Proxy)
        }
    },
    "compressors": {
        "seal_factors": {
            "centrifugal_wet_seal": 0.04, # kg CH4/hr/seal (EPA/API Proxy)
            "centrifugal_dry_seal": 0.002,
            "reciprocating_rod_packing": 0.09 # kg CH4/hr/cylinder
        }
    },
    "defaults": {
        "gas_composition": {
            # Typical Associated Gas (Mole %)
            "methane": 0.75,
            "ethane": 0.10,
            "propane": 0.05,
            "butane": 0.02,
            "co2": 0.02,
            "nitrogen": 0.06
        },
        "carbon_content": {
            "natural_gas": 0.75, # kg C / kg Fuel
            "diesel": 0.86,
            "crude_oil": 0.85
        }
    }
}

# Export individual dictionaries for easier access
COMBUSTION_FACTORS = FACTORS["combustion"]
FLARING_FACTORS = FACTORS["flaring"]
FUGITIVE_FACTORS = FACTORS["fugitives"]["leaker_factors"]
VENTING_FACTORS = FACTORS["venting"]
TANK_FACTORS = FACTORS["tanks"]
DEHYDRATOR_FACTORS = FACTORS["dehydrators"]
LOADING_FACTORS = FACTORS["loading"]
ELECTRICITY_FACTORS = FACTORS["electricity"]["emission_factors"]
AMINE_FACTORS = FACTORS["amine"]
COMPRESSOR_SEAL_FACTORS = FACTORS["compressors"]["seal_factors"]
