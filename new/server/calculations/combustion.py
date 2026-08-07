"""
API Compendium 2021 - Section 5: Combustion and Flaring
Implementation of stationary combustion and flaring dual-efficiency calculations.
Supports API §4.2.1 thermodynamic temperature and pressure normalization.
"""
from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e, normalize_gas_volume_to_standard, STD_TEMP_C, STD_PRESSURE_PSIA
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty, Tier

class CombustionCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Stationary Combustion", "Section 5.1")

    def calculate(self, fuel_quantity, ef_co2, ef_ch4, ef_n2o, uncertainties, hhv, ef_unit, fuel_unit, fuel_type, 
                  combustion_efficiency=0.995, operating_temperature=None, temp_unit='C', 
                  operating_pressure=None, press_unit='psig', z_factor=1.0, **comps):
        """
        Standard fuel-based combustion calculation with API §4.2.1 thermodynamic normalization.
        Emissions = Quantity * EF * (HHV if energy-based)
        """
        # Validate inputs
        self.validate_inputs({"quantity": fuel_quantity}, ["quantity"])
        
        is_gas_fuel = fuel_type in ['gases', 'gas', 'Natural Gas', 'natural_gas'] or str(fuel_unit).lower() in ['m3', 'scf', 'mmscf', 'cubic_meters', 'm³']
        
        # Apply API §4.2.1 thermodynamic normalization to gas fuels if operating T/P supplied
        raw_quantity = fuel_quantity
        if is_gas_fuel and (operating_temperature is not None or operating_pressure is not None):
            normalized_gas_vol = normalize_gas_volume_to_standard(
                volume=fuel_quantity,
                operating_temp=operating_temperature,
                temp_unit=temp_unit,
                operating_press=operating_pressure,
                press_unit=press_unit,
                z_factor=z_factor
            )
            raw_quantity = normalized_gas_vol
        
        # Normalize quantity to the unit expected by HHV (usually scf for gas, gal for liquid)
        normalized_quantity = raw_quantity
        u = str(fuel_unit).lower()
        if u in ['m3', 'cubic_meters', 'm³']:
            if fuel_type == 'liquids':
                normalized_quantity = raw_quantity * CONVERSIONS.get("m3_to_gal", 264.172)
            else:
                normalized_quantity = raw_quantity * CONVERSIONS.get("m3_to_scf", 35.3147)
        elif u in ['mmscf']:
            # 1 MMscf = 1,000,000 scf
            normalized_quantity = raw_quantity * 1_000_000.0
        elif u in ['l', 'liter', 'liters']:
            normalized_quantity = raw_quantity * CONVERSIONS.get("l_to_gal", 0.264172)
        elif u in ['bbl', 'barrel', 'barrels']:
            normalized_quantity = raw_quantity * 42.0
        elif u in ['ton', 'short_ton', 'tons']:
             normalized_quantity = raw_quantity * 2000.0 # lb
        elif u in ['tonne', 'metric_ton', 'tonnes']:
             normalized_quantity = raw_quantity * 2204.62 # lb
        elif u in ['kg', 'kilogram']:
             normalized_quantity = raw_quantity * 2.20462 # lb
              
        # Determine energy factor
        # If EF is energy-based (MMBtu), we need to multiply by HHV (Btu/unit) and divide by 1e6
        energy_factor = 1.0
        ef_u_lower = str(ef_unit).lower()
        
        if "mmbtu" in ef_u_lower:
            energy_factor = (hhv or 1020.0) / 1_000_000.0
        
        # Calculate raw values in kg
        co2_kg = normalized_quantity * energy_factor * ef_co2
        ch4_kg = normalized_quantity * energy_factor * ef_ch4
        n2o_kg = normalized_quantity * energy_factor * ef_n2o
        
        # Convert kg to tonnes
        co2_val = co2_kg / 1000.0
        ch4_val = ch4_kg / 1000.0
        n2o_val = n2o_kg / 1000.0
        
        # Tier 3 Gas Composition Override (Carbon Mass Balance)
        heavy_hc_warning = False
        if 'c1' in comps and comps['c1'] not in [None, '', '-']:
            c_fractions = {
                'c1': float(comps.get('c1') or 0),
                'c2': float(comps.get('c2') or 0),
                'c3': float(comps.get('c3') or 0),
                'c4': float(comps.get('c4') or 0),
                'c5': float(comps.get('c5') or 0),
                'c6': float(comps.get('c6') or 0),
                'c7': float(comps.get('c7') or 0),
                'c8': float(comps.get('c8') or 0),
                'c9': float(comps.get('c9') or 0),
                'c10': float(comps.get('c10') or 0),
            }
            
            c2_plus_total = sum(c_fractions[k] for k in ['c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9', 'c10'])
            if c2_plus_total > 0.10:
                heavy_hc_warning = True
            
            # Use passed combustion_efficiency
            eta_c = combustion_efficiency or 0.995
            
            total_carbon_moles = (
                c_fractions['c1'] * 1 + c_fractions['c2'] * 2 + c_fractions['c3'] * 3 +
                c_fractions['c4'] * 4 + c_fractions['c5'] * 5 + c_fractions['c6'] * 6 +
                c_fractions['c7'] * 7 + c_fractions['c8'] * 8 + c_fractions['c9'] * 9 +
                c_fractions['c10'] * 10
            )
            
            # Apply to gas streams (by fuel_type or volumetric units)
            if is_gas_fuel:
                # Convert quantity to standard m3
                vol_m3 = raw_quantity
                if u in ['scf']: vol_m3 = raw_quantity * CONVERSIONS.get('scf_to_m3', 0.0283168)
                elif u in ['mmscf']: vol_m3 = raw_quantity * 1_000_000.0 * CONVERSIONS.get('scf_to_m3', 0.0283168)
                
                density_co2 = CONVERSIONS.get("density_co2", 1.861)
                
                # Combusted CO2
                co2_combusted_vol = vol_m3 * total_carbon_moles * eta_c
                co2_combusted_kg = co2_combusted_vol * density_co2
                
                # Native CO2
                co2_native_fraction = float(comps.get('co2_comp') or comps.get('co2_mol') or 0)
                co2_native_kg = (vol_m3 * co2_native_fraction) * density_co2
                
                co2_val = (co2_combusted_kg + co2_native_kg) / 1000.0
        
        # Resolve tier from factor_source (passed via uncertainties dict sidecar or defaults)
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        _cat = 'combustion'
        # Propagate uncertainty — tier-aware, 95% CI, non-negative bounds
        co2_res = propagate_uncertainty(
            co2_val,
            ef_uncertainty=resolve_ef_uncertainty(_cat, 'co2', _tier, uncertainties.get('co2')),
            tier=_tier, process_category=_cat, gas='co2'
        )
        ch4_res = propagate_uncertainty(
            ch4_val,
            ef_uncertainty=resolve_ef_uncertainty(_cat, 'ch4', _tier, uncertainties.get('ch4')),
            tier=_tier, process_category=_cat, gas='ch4'
        )
        n2o_res = propagate_uncertainty(
            n2o_val,
            ef_uncertainty=resolve_ef_uncertainty(_cat, 'n2o', _tier, uncertainties.get('n2o')),
            tier=_tier, process_category=_cat, gas='n2o'
        )
        
        total_co2e = calculate_co2e(co2_val, ch4_val, n2o_val)
        
        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={"quantity": fuel_quantity, "hhv": hhv, "ef_unit": ef_unit, "fuel_unit": fuel_unit},
            metadata={
                "operating_temperature": operating_temperature,
                "operating_pressure": operating_pressure,
                "heavy_hydrocarbon_warning": heavy_hc_warning,
                "thermodynamic_normalized": operating_temperature is not None or operating_pressure is not None
            }
        )

class FlaringCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Flaring Dual-Efficiency", "Section 5.2")

    def calculate(self, gas_volume, ch4_fraction, flare_type, uncertainties, hhv=None, ef_unit=None, 
                  fuel_unit=None, fuel_type=None, ef_n2o=0.0, operating_temperature=None, temp_unit='C',
                  operating_pressure=None, press_unit='psig', z_factor=1.0, **comps):
        """
        Dual-efficiency flaring model (API 5-3, 5-4) with API §4.2.1 thermodynamic normalization.
        Supports full C1-C10 gas composition tracking for accurate CO2 math.
        """
        self.validate_inputs({
            "volume": gas_volume, 
            "ch4_fraction": ch4_fraction
        }, ["volume", "ch4_fraction"])

        # Determine efficiencies based on flare type
        if flare_type == "enclosed_ground":
            eta_c = 0.996
            eta_d = 0.995 # Higher for enclosed
        elif flare_type == "elevated":
            eta_c = 0.984
            eta_d = 0.98
        else:  # pit/other
            eta_c = 0.920
            eta_d = 0.95

        # Normalize gas volume if actual temperature/pressure supplied
        vol_std = gas_volume
        if operating_temperature is not None or operating_pressure is not None:
            vol_std = normalize_gas_volume_to_standard(
                volume=gas_volume,
                operating_temp=operating_temperature,
                temp_unit=temp_unit,
                operating_press=operating_pressure,
                press_unit=press_unit,
                z_factor=z_factor
            )

        # Parse C1-C10 from kwargs, falling back to ch4_fraction for C1 if not provided
        c_fractions = {
            'c1': float(comps.get('c1') or ch4_fraction or 0),
            'c2': float(comps.get('c2') or 0),
            'c3': float(comps.get('c3') or 0),
            'c4': float(comps.get('c4') or 0),
            'c5': float(comps.get('c5') or 0),
            'c6': float(comps.get('c6') or 0),
            'c7': float(comps.get('c7') or 0),
            'c8': float(comps.get('c8') or 0),
            'c9': float(comps.get('c9') or 0),
            'c10': float(comps.get('c10') or 0),
        }
        
        actual_ch4_fraction = c_fractions['c1']
        co2_native_fraction = float(comps.get('co2_comp') or comps.get('co2_mol') or 0)
        
        # CH4 Emissions (Undestroyed native methane)
        density_ch4 = CONVERSIONS.get("density_ch4", 0.6785)
        ch4_undestroyed_vol = vol_std * actual_ch4_fraction * (1 - eta_d)
        ch4_mass_kg = ch4_undestroyed_vol * density_ch4
        ch4_tonnes = ch4_mass_kg / 1000.0

        # CO2 from Combustion of Hydrocarbons (C1-C10)
        total_carbon_moles_per_mole_gas = (
            c_fractions['c1'] * 1 +
            c_fractions['c2'] * 2 +
            c_fractions['c3'] * 3 +
            c_fractions['c4'] * 4 +
            c_fractions['c5'] * 5 +
            c_fractions['c6'] * 6 +
            c_fractions['c7'] * 7 +
            c_fractions['c8'] * 8 +
            c_fractions['c9'] * 9 +
            c_fractions['c10'] * 10
        )
        
        # Calculate Combusted CO2
        density_co2 = CONVERSIONS.get("density_co2", 1.861)
        co2_combusted_vol = vol_std * total_carbon_moles_per_mole_gas * eta_c * eta_d
        co2_combusted_kg = co2_combusted_vol * density_co2
        
        # Add Native Uncombusted CO2 passing through the flare
        co2_native_vol = vol_std * co2_native_fraction
        co2_native_kg = co2_native_vol * density_co2
        
        co2_tonnes = (co2_combusted_kg + co2_native_kg) / 1000.0

        # Resolve tier — flaring with full gas composition is Tier 3
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        _cat = 'flaring'
        co2_res = propagate_uncertainty(
            co2_tonnes,
            ef_uncertainty=resolve_ef_uncertainty(_cat, 'co2', _tier, uncertainties.get('co2')),
            tier=_tier, process_category=_cat, gas='co2'
        )
        ch4_res = propagate_uncertainty(
            ch4_tonnes,
            ef_uncertainty=resolve_ef_uncertainty(_cat, 'ch4', _tier, uncertainties.get('ch4')),
            tier=_tier, process_category=_cat, gas='ch4'
        )

        # N2O from flaring
        n2o_tonnes = vol_std * (ef_n2o or 0.0) / 1000.0
        n2o_res = propagate_uncertainty(
            n2o_tonnes,
            ef_uncertainty=resolve_ef_uncertainty(_cat, 'n2o', _tier, uncertainties.get('n2o')),
            tier=_tier, process_category=_cat, gas='n2o'
        )

        total_co2e = calculate_co2e(co2_tonnes, ch4_tonnes, n2o_tonnes)

        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "gas_volume": gas_volume,
                "ch4_fraction": ch4_fraction,
                "flare_type": flare_type,
                "hhv": hhv,
                "ef_unit": ef_unit,
                "fuel_unit": fuel_unit,
                "fuel_type": fuel_type
            },
            metadata={
                "combustion_efficiency": eta_c,
                "destruction_efficiency": eta_d,
                "thermodynamic_normalized": operating_temperature is not None or operating_pressure is not None
            }
        )
