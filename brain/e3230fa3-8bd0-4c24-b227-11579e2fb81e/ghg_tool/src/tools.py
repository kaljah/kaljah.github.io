import pandas as pd

# Physical Properties of Common Gases (Approximate)
# MW: g/mol, Carbon: # atoms, Hydrogen: # atoms, HHV: Btu/scf
GAS_PROPERTIES = {
    "methane": {"mw": 16.04, "c": 1, "h": 4, "hhv": 1010.0},
    "ethane": {"mw": 30.07, "c": 2, "h": 6, "hhv": 1769.0},
    "propane": {"mw": 44.10, "c": 3, "h": 8, "hhv": 2516.0},
    "butane": {"mw": 58.12, "c": 4, "h": 10, "hhv": 3262.0},
    "pentane": {"mw": 72.15, "c": 5, "h": 12, "hhv": 4000.0}, # Approx n-pentane
    "hexane": {"mw": 86.18, "c": 6, "h": 14, "hhv": 4750.0}, # Approx n-hexane
    "heptane": {"mw": 100.21, "c": 7, "h": 16, "hhv": 5500.0}, # Approx
    "octane": {"mw": 114.23, "c": 8, "h": 18, "hhv": 6250.0}, # Approx
    "co2": {"mw": 44.01, "c": 1, "h": 0, "hhv": 0.0},
    "n2": {"mw": 28.01, "c": 0, "h": 0, "hhv": 0.0},
    "h2s": {"mw": 34.08, "c": 0, "h": 2, "hhv": 637.0}, # Approx
    "h2o": {"mw": 18.02, "c": 0, "h": 2, "hhv": 0.0},
    "he": {"mw": 4.00, "c": 0, "h": 0, "hhv": 0.0},
}

def calculate_gas_properties(composition):
    """
    Calculate properties of a gas mixture based on molar composition.
    composition: dict {component: mole_fraction} (e.g., {"methane": 0.9, "ethane": 0.1})
    Returns: dict with MW, Carbon Content (wt%), HHV (Btu/scf), Density (kg/m3 approx)
    """
    total_moles = sum(composition.values())
    if abs(total_moles - 1.0) > 0.01:
        # Normalize if not close to 1
        composition = {k: v / total_moles for k, v in composition.items()}

    avg_mw = 0.0
    avg_hhv = 0.0
    total_c_mass = 0.0
    
    # Standard Molar Volume at 60F, 1 atm approx 379.5 scf/lb-mol or 23.64 L/mol (STP)
    # Using Ideal Gas Law approx for density: Density (kg/m3) = (P * MW) / (R * T)
    # At STP (0C, 1 atm): Density = MW / 22.414
    # At Standard Conditions (60F/15.5C, 1 atm): Density = MW / 23.64 (approx for kg/m3 if MW in g/mol)
    
    for gas, mole_frac in composition.items():
        props = GAS_PROPERTIES.get(gas.lower())
        if not props:
            continue
            
        mw = props["mw"]
        hhv = props["hhv"]
        c_atoms = props["c"]
        
        avg_mw += mw * mole_frac
        avg_hhv += hhv * mole_frac
        
        # Carbon Mass Contribution
        # Mass of C in 1 mol of mixture = sum(mole_frac_i * #C_i * 12.01)
        total_c_mass += mole_frac * c_atoms * 12.011

    # Carbon Content (Weight %)
    # Wt% C = (Mass of C / Total Mass) * 100
    if avg_mw > 0:
        carbon_content_wt = (total_c_mass / avg_mw)
    else:
        carbon_content_wt = 0.0
        
    # Density (kg/m3) at Standard Conditions (15C, 1 atm)
    # 1 kmol = 23.64 m3 approx
    # Density = MW (kg/kmol) / 23.64 (m3/kmol)
    density_kg_m3 = avg_mw / 23.64
    
    # --- POTENTIAL EMISSION FACTORS ---
    
    # Weight fractions
    wt_ch4 = (composition.get("methane", 0) * 16.04) / avg_mw if avg_mw > 0 else 0
    wt_co2 = (composition.get("co2", 0) * 44.01) / avg_mw if avg_mw > 0 else 0
    
    # 1. Combustion (100% Oxidation)
    # kg CO2 / kg Gas = wt% C * (44.01 / 12.011)
    ef_combustion_co2 = carbon_content_wt * (44.01 / 12.011)
    
    # 2. Flaring (98% Destruction Efficiency)
    # Per API Compendium:
    # - 98% of gas is combusted → produces CO2 (same as combustion)
    # - 2% of gas escapes unburnt → released as CH4 (for methane-rich gas)
    # CO2e = (0.98 × CO2 from combustion) + (0.02 × wt% CH4 × GWP_CH4)
    # 
    # The 2% unburnt portion releases methane with GWP = 25
    # So: 0.02 kg of gas × wt% CH4 in that gas × 25 (GWP)
    ef_flaring_co2_combusted = 0.98 * ef_combustion_co2
    ef_flaring_ch4_unburnt = 0.02 * wt_ch4 * 25  # kg CO2e from unburnt CH4
    ef_flaring_co2e = ef_flaring_co2_combusted + ef_flaring_ch4_unburnt
    
    # 3. Venting (100% Release)
    # CO2e = (wt% CO2 × 1) + (wt% CH4 × 25)
    ef_venting_co2e = wt_co2 + (wt_ch4 * 25)

    return {
        "molecular_weight": avg_mw, # g/mol
        "hhv_btu_scf": avg_hhv, # Btu/scf
        "carbon_content_wt": carbon_content_wt, # fraction (0-1)
        "density_kg_m3": density_kg_m3,
        "composition_normalized": composition,
        "ef_combustion_kg_kg": ef_combustion_co2, # kg CO2 / kg Gas
        "ef_flaring_kg_kg": ef_flaring_co2e, # kg CO2e / kg Gas (98% DE)
        "ef_venting_kg_kg": ef_venting_co2e # kg CO2e / kg Gas
    }
