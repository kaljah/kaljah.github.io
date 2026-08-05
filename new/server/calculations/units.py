from .constants import DEFAULT_GWP

CONVERSIONS = {
    # Volume
    "scf_to_m3": 0.0283168,
    "m3_to_scf": 35.3147,
    "bbl_to_m3": 0.158987,
    "m3_to_bbl": 6.28981,
    "gal_to_m3": 0.00378541,
    "m3_to_gal": 264.172,
    "liter_to_m3": 0.001,
    "m3_to_liter": 1000.0,
    "l_to_gal": 0.264172,       # 1 liter = 0.264172 US gallons
    "gal_to_l": 3.78541,        # 1 US gallon = 3.78541 liters
    "bbl_to_gal": 42.0,
    "mmscf_to_m3": 28316.8,
    "m3_to_mmscf": 3.53147e-5,
    
    # Mass
    "lb_to_kg": 0.453592,
    "kg_to_lb": 2.20462,
    "tonne_to_kg": 1000.0,
    "short_ton_to_kg": 907.185,
    "long_ton_to_kg": 1016.05,
    
    # Energy
    "btu_to_kj": 1.05506,
    "mj_to_btu": 947.817,
    "mmbtu_to_mj": 1055.06,
    "mj_to_mmbtu": 0.000947817,
    "kwh_to_mj": 3.6,
    "mj_to_kwh": 0.277778,
    "therm_to_mj": 105.506,
    
    # Gas Densities (kg/m3 at standard conditions: 60F, 14.7 psia)
    "density_ch4": 0.6785,
    "density_c2h6": 1.282,  # Ethane
    "density_c3h8": 1.882,  # Propane
    "density_c4h10": 2.519, # n-Butane
    "density_co2": 1.861,
    "density_n2o": 1.860,
    
    # GWP (GHG Protocol AR5)
    "gwp_ch4": DEFAULT_GWP['CH4'],
    "gwp_n2o": DEFAULT_GWP['N2O'],

    # Global Warming Potentials (Comparison Reference)
    "GWP_AR4": {"ch4": 25, "n2o": 298},
    "GWP_AR5": DEFAULT_GWP,
    "GWP_AR6": {"ch4": 27.9, "n2o": 273}
}

def convert(value, from_unit, to_unit):
    """Simple unit conversion wrapper."""
    key = f"{from_unit}_to_{to_unit}"
    if key in CONVERSIONS:
        return value * CONVERSIONS[key]
    
    # Reverse conversion
    rev_key = f"{to_unit}_to_{from_unit}"
    if rev_key in CONVERSIONS:
        return value / CONVERSIONS[rev_key]
        
    raise ValueError(f"Unsupported conversion: {from_unit} to {to_unit}")

def calculate_co2e(co2=0, ch4=0, n2o=0):
    """Calculates CO2e using AR5 GWPs."""
    return co2 + (ch4 * CONVERSIONS["gwp_ch4"]) + (n2o * CONVERSIONS["gwp_n2o"])
