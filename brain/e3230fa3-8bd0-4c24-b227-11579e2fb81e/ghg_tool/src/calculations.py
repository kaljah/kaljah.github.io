import pandas as pd
from src.factors import FACTORS
from src.units import UnitConverter

converter = UnitConverter()

def calculate_combustion(fuel_type, quantity, quantity_unit="MMBtu", tier="Tier 1", hhv=None, carbon_content=None):
    """
    Calculate combustion emissions with Multi-Tier support.
    Tier 1: Volume * Default EF
    Tier 2: Volume * Measured HHV * Energy EF
    Tier 3: Mass Balance (Carbon Content)
    """
    factors = FACTORS["combustion"].get(fuel_type)
    if not factors:
        return None
    
    # --- TIER 1: Default ---
    if tier == "Tier 1":
        # Normalize Quantity to Factor Units
        normalized_quantity = quantity
        target_unit = "MMBtu" if "MMBtu" in factors["units"] else "gal"
        
        if quantity_unit != target_unit:
            if target_unit == "MMBtu" and quantity_unit in ["m3", "scf", "Mscf"]:
                scf_val = converter.convert(quantity, "volume", quantity_unit, "scf")
                hhv_val = factors.get("hhv", 1026)
                normalized_quantity = (scf_val * hhv_val) / 1_000_000.0
            elif target_unit == "MMBtu":
                normalized_quantity = converter.convert(quantity, "energy", quantity_unit, "MMBtu")
            elif target_unit == "gal":
                normalized_quantity = converter.convert(quantity, "volume", quantity_unit, "gal")
                
        co2 = normalized_quantity * factors["co2"]
        ch4 = normalized_quantity * factors["ch4"]
        n2o = normalized_quantity * factors["n2o"]
        
        meta = {
            "method": "Tier 1 (Default Factors)",
            "formula": "E = Q \\times EF",
            "factors": {k: v for k, v in factors.items() if k in ["co2", "ch4", "n2o", "units"]}
        }

    # --- TIER 2: Measured HHV ---
    elif tier == "Tier 2":
        if not hhv: return None # Error handling in UI
        # Convert input to scf/gal then to MMBtu using measured HHV
        # Assuming input is Volume
        if quantity_unit in ["MMBtu", "GJ"]:
             # Already energy, just use Tier 1 logic effectively but maybe with specific EF? 
             # Tier 2 usually implies we measured the energy content.
             # Let's assume input is Volume and we use HHV to get Energy.
             pass
        
        # Simplified: Convert everything to MMBtu using PROVIDED HHV
        # Need to know if HHV is Btu/scf or Btu/gal
        # Let's assume HHV unit matches fuel type standard (Btu/scf for gas, Btu/gal for liquid)
        
        if "MMBtu" in factors["units"]: # Gas
            vol_scf = converter.convert(quantity, "volume", quantity_unit, "scf")
            energy_mmbtu = (vol_scf * hhv) / 1_000_000.0
        else: # Liquid
            vol_gal = converter.convert(quantity, "volume", quantity_unit, "gal")
            energy_mmbtu = (vol_gal * hhv) / 1_000_000.0
            
        # Use Energy-based factors (derived or standard)
        # API often gives factors in kg/MMBtu for everything in Tier 2
        # Let's use the natural gas kg/MMBtu factors as proxy or the specific ones
        
        co2 = energy_mmbtu * factors["co2"] # Assuming factor is energy based or we converted
        # If factor was kg/gal, we need kg/MMBtu. 
        # Diesel: 10.21 kg/gal / 0.138 MMBtu/gal = 74 kg/MMBtu
        if "gal" in factors["units"]:
            default_hhv_mmbtu = factors["hhv"] / 1_000_000.0
            ef_energy = factors["co2"] / default_hhv_mmbtu
            co2 = energy_mmbtu * ef_energy
        
        ch4 = energy_mmbtu * 0.001 # Default energy based
        n2o = energy_mmbtu * 0.0001
        
        meta = {
            "method": "Tier 2 (Measured HHV)",
            "formula": "E = V \\times HHV \\times EF_{energy}",
            "factors": {"HHV": hhv}
        }

    # --- TIER 3: Mass Balance ---
    elif tier == "Tier 3":
        if not carbon_content: return None
        # E_CO2 = Mass_Fuel * Carbon_Content * (44/12) * Oxidation_Factor
        
        # Convert to Mass (kg)
        # Need density
        density = factors.get("density", 1.0) # lb/unit
        
        if "MMBtu" in factors["units"]: # Gas
            vol_scf = converter.convert(quantity, "volume", quantity_unit, "scf")
            mass_lb = vol_scf * density
        else: # Liquid
            vol_gal = converter.convert(quantity, "volume", quantity_unit, "gal")
            mass_lb = vol_gal * density
            
        mass_kg = converter.convert(mass_lb, "mass", "lb", "kg")
        
        co2 = mass_kg * carbon_content * (44/12) * 1.0 # Assuming 100% oxidation
        ch4 = 0 # Mass balance usually for CO2. CH4/N2O use Tier 1/2.
        n2o = 0 
        
        meta = {
            "method": "Tier 3 (Mass Balance)",
            "formula": "E_{CO2} = M_{fuel} \\times CC \\times \\frac{44}{12}",
            "factors": {"Carbon Content": carbon_content, "Density": density}
        }
        
    emissions = {"CO2": co2, "CH4": ch4, "N2O": n2o}
    emissions["CO2e"] = emissions["CO2"] + (emissions["CH4"] * 25) + (emissions["N2O"] * 298)
    emissions["_meta"] = meta
    return emissions

def calculate_flaring(volume, volume_unit="Mscf", tier="Tier 1", gas_composition=None, destruction_efficiency=0.98):
    """
    Calculate flaring emissions with Multi-Tier support.
    """
    vol_mscf = converter.convert(volume, "volume", volume_unit, "Mscf")
    
    if tier == "Tier 1":
        co2_factor = 54.44 
        ch4_density = 19.2 
        n2o_factor = 0.001 
        
        co2 = vol_mscf * co2_factor * destruction_efficiency
        ch4 = vol_mscf * ch4_density * (1 - destruction_efficiency)
        n2o = vol_mscf * n2o_factor
        
        meta = {"method": "Tier 1 (Default Factors)", "formula": "Standard API Factors"}

    elif tier == "Tier 2" and gas_composition:
        # Calculate MW and Carbon Content from Composition
        # Simplified: Sum(Xi * MWi)
        # CO2 from Combustion = Sum(Xi * Ci) * Vol * ...
        
        # Let's assume gas_composition is dict: {"methane": 0.8, "ethane": 0.1 ...}
        # Moles to Mass conversion
        
        # Total Moles in Volume
        # 1 Mscf = 1.198 lb-moles (Standard conditions)
        moles = vol_mscf * 1.198
        
        total_carbon_moles = 0
        for comp, fraction in gas_composition.items():
            c_count = 1 if comp == "methane" else 2 if comp == "ethane" else 3 if comp == "propane" else 0
            total_carbon_moles += moles * fraction * c_count
            
        # CO2 from combustion
        co2_moles_generated = total_carbon_moles * destruction_efficiency
        co2_mass_lb = co2_moles_generated * 44.01
        co2 = converter.convert(co2_mass_lb, "mass", "lb", "kg")
        
        # CH4 unburnt
        ch4_moles = moles * gas_composition.get("methane", 0) * (1 - destruction_efficiency)
        ch4_mass_lb = ch4_moles * 16.04
        ch4 = converter.convert(ch4_mass_lb, "mass", "lb", "kg")
        
        n2o = vol_mscf * 0.001 # Default
        
        meta = {"method": "Tier 2 (Gas Composition)", "formula": "Mass Balance from Composition"}
        
    else:
        return None

    return {
        "CO2": co2, "CH4": ch4, "N2O": n2o,
        "CO2e": co2 + (ch4 * 25) + (n2o * 298),
        "_meta": meta
    }

def calculate_venting(controller_type, count, hours=8760, tier="Tier 1", user_rate=None):
    """
    Venting with Tier 3 (User Rate).
    """
    if tier == "Tier 3" and user_rate:
        # user_rate in scf/hr
        total_volume_scf = user_rate * hours
        meta = {"method": "Tier 3 (Measured Rate)", "rate": f"{user_rate} scf/hr"}
    else:
        factor = FACTORS["venting"]["pneumatic_controllers"].get(controller_type)
        if factor is None: return None
        total_volume_scf = factor * count * hours
        meta = {"method": "Tier 1 (Default Factors)", "factor": factor}
    
    density = 0.0192 # kg/scf CH4
    ch4 = total_volume_scf * density
    
    return {
        "CO2": 0.0, "CH4": ch4, "N2O": 0.0, "CO2e": ch4 * 25,
        "_meta": meta
    }

def calculate_fugitives(component_counts, stream_type="gas", hours=8760, tier="Tier 1", user_leak_rate=None):
    """
    Fugitives with Tier 3 (User Total Rate).
    """
    if tier == "Tier 3" and user_leak_rate:
        # user_leak_rate in kg/hr (Total)
        total_ch4 = user_leak_rate * hours
        meta = {"method": "Tier 3 (Measured Total Rate)", "rate": f"{user_leak_rate} kg/hr"}
    else:
        total_ch4 = 0
        factors = FACTORS["fugitives"]["leaker_factors"]
        for component, count in component_counts.items():
            if component in factors:
                factor = factors[component].get(stream_type, 0)
                total_ch4 += factor * count * hours
        meta = {"method": "Tier 1 (Component Count)", "factors": "API Average"}
            
    return {
        "CO2": 0.0, "CH4": total_ch4, "N2O": 0.0, "CO2e": total_ch4 * 25,
        "_meta": meta
    }

def calculate_tank_losses(throughput, throughput_unit="bbl", temp_f=60, rvp=5.0, tier="Tier 1", gas_oil_ratio=None):
    """
    Tanks with Tier 3 (GOR).
    """
    throughput_bbl = converter.convert(throughput, "volume", throughput_unit, "bbl")
    
    if tier == "Tier 3" and gas_oil_ratio:
        # GOR in scf/bbl
        total_gas_scf = throughput_bbl * gas_oil_ratio
        # Assume gas is methane
        ch4_kg = total_gas_scf * 0.0192 # kg/scf
        voc_lb = 0 # Simplified
        meta = {"method": "Tier 3 (Gas-Oil Ratio)", "GOR": gas_oil_ratio}
    else:
        # Tier 1/2 Simplified
        Mv = FACTORS["tanks"]["defaults"]["vapor_molecular_weight"]["crude_oil"]
        Pva = rvp * 0.7
        lw_factor = 2.4e-5 * Mv * Pva 
        working_loss_lb = throughput_bbl * lw_factor
        standing_loss_lb = working_loss_lb * 0.2 
        total_voc_lb = working_loss_lb + standing_loss_lb
        ch4_kg = converter.convert(total_voc_lb * 0.1, "mass", "lb", "kg")
        meta = {"method": "Tier 1 (Simplified API 19.1)", "RVP": rvp}
    
    return {
        "CO2": 0.0, "CH4": ch4_kg, "N2O": 0.0, "CO2e": ch4_kg * 25,
        "_meta": meta
    }

def calculate_dehydrator(throughput, throughput_unit="MMscf", tier="Tier 1", emission_rate=None):
    """
    Dehydrators with Tier 3 (User Rate).
    """
    throughput_mmscf = converter.convert(throughput, "volume", throughput_unit, "MMscf")
    
    if tier == "Tier 3" and emission_rate:
        # Rate in kg/MMscf
        ch4_kg = throughput_mmscf * emission_rate
        meta = {"method": "Tier 3 (User Rate)", "rate": emission_rate}
    else:
        factor = FACTORS["dehydrators"]["emission_factors"]["uncontrolled_teg"]
        ch4_kg = throughput_mmscf * factor
        meta = {"method": "Tier 1 (Default Factor)", "factor": factor}
    
    return {
        "CO2": 0.0, "CH4": ch4_kg, "N2O": 0.0, "CO2e": ch4_kg * 25,
        "_meta": meta
    }

def calculate_loading(volume_loaded, volume_unit="gal", temp_f=60, rvp=5.0, mode="submerged_pipe", tier="Tier 1", vru_efficiency=0.0):
    """
    Loading with Tier 3 (VRU).
    """
    vol_gal = converter.convert(volume_loaded, "volume", volume_unit, "gal")
    vol_1000gal = vol_gal / 1000.0
    
    S = FACTORS["loading"]["saturation_factors"].get(mode, 0.6)
    P = rvp * 0.7 
    M = 50.0
    T = temp_f + 459.67
    
    LL_lb_per_1000gal = (12.46 * S * P * M) / T
    total_voc_lb = LL_lb_per_1000gal * vol_1000gal
    
    if tier == "Tier 3":
        total_voc_lb = total_voc_lb * (1 - vru_efficiency)
        meta = {"method": "Tier 3 (VRU Controlled)", "Efficiency": vru_efficiency}
    else:
        meta = {"method": "Tier 1 (AP-42)", "S": S}
    
    ch4_kg = converter.convert(total_voc_lb * 0.01, "mass", "lb", "kg")
    
    return {
        "CO2": 0.0, "CH4": ch4_kg, "N2O": 0.0, "CO2e": ch4_kg * 25,
        "_meta": meta
    }

def calculate_electricity(usage, usage_unit="kWh", region="us_average_2022"):
    """
    Scope 2 Electricity Calculation.
    """
    # Normalize to kWh
    if usage_unit == "MWh":
        kwh = usage * 1000.0
    else:
        kwh = usage
        
    factor = FACTORS["electricity"]["emission_factors"].get(region, 0.4)
    co2e = kwh * factor
    
    return {
        "CO2": 0.0, "CH4": 0.0, "N2O": 0.0, "CO2e": co2e,
        "_meta": {"method": "Location Based", "factor": f"{factor} kg/kWh", "region": region}
    }

def calculate_amine(throughput, throughput_unit="MMscf", tier="Tier 1"):
    """
    Calculate Amine Unit Emissions (Acid Gas Removal).
    """
    throughput_mmscf = converter.convert(throughput, "volume", throughput_unit, "MMscf")
    # Convert to m3 for factor application (Factor is kg/m3 approx or kg/MMscf?)
    # Let's use kg/MMscf directly if possible or convert.
    # Factor in factors.py is 2.2 kg CO2/m3 gas.
    # 1 MMscf = 28316.8 m3
    
    vol_m3 = converter.convert(throughput, "volume", throughput_unit, "m3")
    
    if tier == "Tier 1":
        factor = FACTORS["amine"]["emission_factors"]["generic_amine"] # kg CO2 / m3
        co2_kg = vol_m3 * factor
        meta = {"method": "Tier 1 (Generic Factor)", "factor": f"{factor} kg CO2/m3"}
    else:
        return None # Placeholder for higher tiers
        
    return {
        "CO2": co2_kg, "CH4": 0.0, "N2O": 0.0, "CO2e": co2_kg,
        "_meta": meta
    }

def calculate_compressor(compressor_type, count, hours=8760, tier="Tier 1"):
    """
    Calculate Compressor Seal Emissions.
    """
    if tier == "Tier 1":
        # Map type to factor key
        key_map = {
            "Centrifugal (Wet Seal)": "centrifugal_wet_seal",
            "Centrifugal (Dry Seal)": "centrifugal_dry_seal",
            "Reciprocating": "reciprocating_rod_packing"
        }
        key = key_map.get(compressor_type)
        if not key: return None
        
        factor = FACTORS["compressors"]["seal_factors"].get(key, 0.0)
        ch4_kg = factor * count * hours
        meta = {"method": "Tier 1 (Default Factor)", "factor": f"{factor} kg CH4/hr"}
    else:
        return None

    return {
        "CO2": 0.0, "CH4": ch4_kg, "N2O": 0.0, "CO2e": ch4_kg * 25,
        "_meta": meta
    }
