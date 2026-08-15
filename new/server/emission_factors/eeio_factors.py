"""
EPA USEEIO Emission Factors v1.3
Maps NAICS codes to kg CO2e per $1,000 spend.
These are indicative factors used for Scope 3 Category 1 (Purchased Goods and Services)
when physical activity data is unavailable.
"""

EEIO_FACTORS = {
    # Agriculture, Forestry, Fishing and Hunting
    "111": {"name": "Crop Production", "kg_co2e_per_1000_usd": 1250.4},
    "112": {"name": "Animal Production and Aquaculture", "kg_co2e_per_1000_usd": 2100.5},
    "113": {"name": "Forestry and Logging", "kg_co2e_per_1000_usd": 450.2},
    "114": {"name": "Fishing, Hunting and Trapping", "kg_co2e_per_1000_usd": 890.3},
    
    # Mining, Quarrying, and Oil and Gas Extraction
    "211": {"name": "Oil and Gas Extraction", "kg_co2e_per_1000_usd": 3200.1},
    "212": {"name": "Mining (except Oil and Gas)", "kg_co2e_per_1000_usd": 2800.0},
    "213": {"name": "Support Activities for Mining", "kg_co2e_per_1000_usd": 950.6},
    
    # Utilities
    "221": {"name": "Utilities", "kg_co2e_per_1000_usd": 5400.8},
    
    # Construction
    "236": {"name": "Construction of Buildings", "kg_co2e_per_1000_usd": 410.5},
    "237": {"name": "Heavy and Civil Engineering Construction", "kg_co2e_per_1000_usd": 520.3},
    "238": {"name": "Specialty Trade Contractors", "kg_co2e_per_1000_usd": 350.2},
    
    # Manufacturing
    "311": {"name": "Food Manufacturing", "kg_co2e_per_1000_usd": 680.4},
    "324": {"name": "Petroleum and Coal Products Manufacturing", "kg_co2e_per_1000_usd": 4100.2},
    "325": {"name": "Chemical Manufacturing", "kg_co2e_per_1000_usd": 1800.5},
    "327": {"name": "Nonmetallic Mineral Product Manufacturing", "kg_co2e_per_1000_usd": 3400.9},
    "331": {"name": "Primary Metal Manufacturing", "kg_co2e_per_1000_usd": 2900.1},
    "333": {"name": "Machinery Manufacturing", "kg_co2e_per_1000_usd": 310.4},
    "334": {"name": "Computer and Electronic Product Manufacturing", "kg_co2e_per_1000_usd": 180.2},
    "336": {"name": "Transportation Equipment Manufacturing", "kg_co2e_per_1000_usd": 250.6},
    
    # Wholesale and Retail Trade
    "423": {"name": "Merchant Wholesalers, Durable Goods", "kg_co2e_per_1000_usd": 150.3},
    "441": {"name": "Motor Vehicle and Parts Dealers", "kg_co2e_per_1000_usd": 120.5},
    
    # Transportation and Warehousing
    "481": {"name": "Air Transportation", "kg_co2e_per_1000_usd": 2800.4},
    "482": {"name": "Rail Transportation", "kg_co2e_per_1000_usd": 950.2},
    "484": {"name": "Truck Transportation", "kg_co2e_per_1000_usd": 1100.8},
    "486": {"name": "Pipeline Transportation", "kg_co2e_per_1000_usd": 450.5},
    
    # Information & Services
    "511": {"name": "Publishing Industries", "kg_co2e_per_1000_usd": 90.5},
    "518": {"name": "Data Processing, Hosting, and Related Services", "kg_co2e_per_1000_usd": 450.2},
    "522": {"name": "Credit Intermediation and Related Activities", "kg_co2e_per_1000_usd": 45.3},
    "541": {"name": "Professional, Scientific, and Technical Services", "kg_co2e_per_1000_usd": 85.6},
    
    # Default fallback
    "000": {"name": "Generic Corporate Spend", "kg_co2e_per_1000_usd": 350.0}
}

def get_eeio_factor(naics_code: str) -> dict:
    """
    Returns the EEIO factor for a given 3-digit NAICS code.
    If exact match not found, tries prefix, else returns default.
    """
    if not naics_code:
        return EEIO_FACTORS["000"]
        
    code_str = str(naics_code)[:3]
    if code_str in EEIO_FACTORS:
        return EEIO_FACTORS[code_str]
        
    # If 2-digit fallback is needed
    for key, value in EEIO_FACTORS.items():
        if key.startswith(code_str[:2]):
            return value
            
    return EEIO_FACTORS["000"]
