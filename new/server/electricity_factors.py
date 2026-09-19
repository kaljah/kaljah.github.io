"""
Grid Emission Factors - electricity_factors.py
Central registry for indirect (Scope 2) electricity emission factors.
Units: kg CO2e / kWh
"""

GRID_FACTORS = {
    "Algerian National Grid": {
        "factor": 0.522,
        "unit": "kg CO2e/kWh",
        "description": "Algerian electricity mix (primarily Natural Gas)",
        "source": "Sonelgaz / IEA typical for Algeria",
    },
    "Algerian Grid - North": {
        "factor": 0.510,
        "unit": "kg CO2e/kWh",
        "description": "Northern interconnected grid",
        "source": "Estimated local mix",
    },
    "Algerian Grid - South / Isolated": {
        "factor": 0.650,
        "unit": "kg CO2e/kWh",
        "description": "Isolated Southern grids (Diesel/Gas backup)",
        "source": "Estimated local mix",
    },
    "US Average": {
        "factor": 0.385,
        "unit": "kg CO2e/kWh",
        "description": "eGRID US Average grid mix",
        "source": "eGRID",
    },
    "US-WECC": {
        "factor": 0.3132,
        "unit": "kg CO2e/kWh",
        "description": "WECC average grid mix",
        "source": "eGRID",
    },
    "US-ERCOT": {
        "factor": 0.4345,
        "unit": "kg CO2e/kWh",
        "description": "Texas grid mix",
        "source": "eGRID",
    },
    "EU Grid Average": {
        "factor": 0.295,
        "unit": "kg CO2e/kWh",
        "description": "EU-27 average grid mix",
        "source": "EEA",
    },
    "UK National Grid": {
        "factor": 0.233,
        "unit": "kg CO2e/kWh",
        "description": "UK average grid mix",
        "source": "DEFRA",
    },
}
