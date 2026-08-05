"""
API Compendium 2021 - Section 6: Vented and Process Emissions
Implementation of equations for mud degassing, completions, unloading, tanks, and pneumatics.
"""
from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e, convert
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty
import math

class MudDegassingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Drilling Mud Degassing", "Section 6.2")

    def calculate(self, mud_volume, mud_type, uncertainties, ef_ch4=None):
        """
        API Section 6.2 - CH4 from mud degassing
        """
        self.validate_inputs({"volume": mud_volume}, ["volume"])
        
        # Default factors (kg CH4 / m3 mud)
        factors = {
            "water_based": 0.15,
            "oil_based": 0.35,
            "synthetic": 0.25
        }
        
        # Use provided EF if available (and non-zero), otherwise default based on type
        if ef_ch4 and ef_ch4 > 0:
            ef = ef_ch4
        else:
            ef = factors.get(mud_type, 0.25)
        
        ch4_kg = mud_volume * ef
        ch4_tonnes = ch4_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(ch4_tonnes, resolve_ef_uncertainty('vented', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='vented', gas='ch4')
        total_co2e = calculate_co2e(ch4=ch4_tonnes)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={"mud_volume": mud_volume, "mud_type": mud_type, "ef_ch4_used": ef}
        )

class CompletionFlowbackCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Well Completion Flowback", "Section 6.3")

    def calculate(self, flowback_volume, ch4_content, control_efficiency, uncertainties, co2_content=0.0, ef_co2=None, ef_ch4=None, ef_n2o=None):
        """
        API Eq. 6-12 (modified for volumetric):
        Total Vent Gas = Flowback Volume (m3) * GOR
        Currently using standard GOR factor simplified.
        """
        self.validate_inputs({
            "flowback_volume": flowback_volume,
            "ch4_content": ch4_content
        }, ["flowback_volume", "ch4_content"])
        
        # Simple volume model:
        ch4_vol = flowback_volume * ch4_content
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        co2_vol = flowback_volume * co2_content
        co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
        co2_tonnes = co2_mass_kg / 1000.0
        
        # Vented fraction goes straight to atmosphere
        vented_ch4_tonnes = ch4_tonnes * (1.0 - control_efficiency)
        vented_co2_tonnes = co2_tonnes * (1.0 - control_efficiency)

        flared_co2_tonnes = 0.0
        flared_n2o_tonnes = 0.0
        flared_unburnt_ch4_tonnes = 0.0

        if control_efficiency > 0:
            if ef_co2 is not None and ef_ch4 is not None:
                # TIER 3 FLARING using Gas Analysis Factors!
                # The emission factors are based on the entire gas stream volume
                # But only control_efficiency fraction of the volume goes to the flare
                flared_volume = flowback_volume * control_efficiency
                flared_co2_tonnes = (flared_volume * ef_co2) / 1000.0
                flared_unburnt_ch4_tonnes = (flared_volume * ef_ch4) / 1000.0
                flared_n2o_tonnes = (flared_volume * ef_n2o) / 1000.0 if ef_n2o else 0.0
            else:
                # TIER 1/2 FLARING (Simple Methane Combustion)
                # Flare assumes 98% combustion of CH4 to CO2. Note: 1 mole CH4 = 1 mole CO2 (44.01/16.04)
                flared_co2_tonnes = (ch4_tonnes * control_efficiency) * (44.01 / 16.04)
                flared_natural_co2_tonnes = co2_tonnes * control_efficiency
                flared_co2_tonnes += flared_natural_co2_tonnes
                # Unburnt methane is already handled because vented_ch4_tonnes assumes the rest was destroyed

        total_ch4 = vented_ch4_tonnes + flared_unburnt_ch4_tonnes
        total_co2 = vented_co2_tonnes + flared_co2_tonnes
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(total_ch4, resolve_ef_uncertainty('vented', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='vented', gas='ch4')
        co2_res = propagate_uncertainty(total_co2, resolve_ef_uncertainty('vented', 'co2', _tier, uncertainties.get('co2')), tier=_tier, process_category='vented', gas='co2') if total_co2 > 0 else None
        n2o_res = propagate_uncertainty(flared_n2o_tonnes, resolve_ef_uncertainty('vented', 'n2o', _tier, uncertainties.get('n2o')), tier=_tier, process_category='vented', gas='n2o') if flared_n2o_tonnes > 0 else None
        
        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o_tonnes)
        
        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "flowback_volume": flowback_volume,
                "ch4_content": ch4_content,
                "control_efficiency": control_efficiency
            }
        )

class LiquidsUnloadingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Liquids Unloading (Volume-Based)", "Section 6.4")

    def calculate(self, well_depth, diameter, pressure, ch4_content, events, uncertainties, co2_content=0.0, control_efficiency=0.0, ef_co2=None, ef_ch4=None, ef_n2o=None):
        """
        API Equation 6-3 - Volume per unloading event
        V = (pi/4) * D^2 * Depth * (P_tubing / P_std)
        """
        self.validate_inputs({
            "depth": well_depth,
            "diameter": diameter,
            "pressure": pressure,
            "events": events
        }, ["depth", "diameter", "pressure", "events"])
        
        # Diameter in inches -> convert to meters
        d_m = diameter * 0.0254
        
        # Depth in feet -> convert to meters (standard oilfield unit is feet)
        depth_m = well_depth * 0.3048

        # Volume at tubing conditions (m3)
        v_tubing = (math.pi / 4.0) * (d_m**2) * depth_m

        # Standard conditions expansion (API Eq. 6-3)
        # pressure is entered by users in psig (gauge) -> convert to psia (absolute)
        # P_abs = P_gauge + P_atm; P_std = 14.696 psia
        # EXTRA-05 FIX: use 14.696 consistently (not 14.7)
        P_STD = 14.696
        p_abs = pressure + P_STD
        v_std = v_tubing * (p_abs / P_STD)
        
        # Total annual volume
        total_v_std = v_std * events
        
        ch4_vol = total_v_std * ch4_content
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        co2_vol = total_v_std * co2_content
        co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
        co2_tonnes = co2_mass_kg / 1000.0
        
        # Vented fraction goes straight to atmosphere
        vented_ch4_tonnes = ch4_tonnes * (1.0 - control_efficiency)
        vented_co2_tonnes = co2_tonnes * (1.0 - control_efficiency)

        flared_co2_tonnes = 0.0
        flared_n2o_tonnes = 0.0
        flared_unburnt_ch4_tonnes = 0.0

        if control_efficiency > 0:
            if ef_co2 is not None and ef_ch4 is not None:
                # TIER 3 FLARING using Gas Analysis Factors!
                flared_volume = total_v_std * control_efficiency
                flared_co2_tonnes = (flared_volume * ef_co2) / 1000.0
                flared_unburnt_ch4_tonnes = (flared_volume * ef_ch4) / 1000.0
                flared_n2o_tonnes = (flared_volume * ef_n2o) / 1000.0 if ef_n2o else 0.0
            else:
                # TIER 1/2 FLARING (Simple Methane Combustion)
                flared_co2_tonnes = (ch4_tonnes * control_efficiency) * (44.01 / 16.04)
                flared_natural_co2_tonnes = co2_tonnes * control_efficiency
                flared_co2_tonnes += flared_natural_co2_tonnes
                # Unburnt methane handled in vented_ch4_tonnes

        total_ch4 = vented_ch4_tonnes + flared_unburnt_ch4_tonnes
        total_co2 = vented_co2_tonnes + flared_co2_tonnes

        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(total_ch4, resolve_ef_uncertainty('vented', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='vented', gas='ch4')
        co2_res = propagate_uncertainty(total_co2, resolve_ef_uncertainty('vented', 'co2', _tier, uncertainties.get('co2')), tier=_tier, process_category='vented', gas='co2') if total_co2 > 0 else None
        n2o_res = propagate_uncertainty(flared_n2o_tonnes, resolve_ef_uncertainty('vented', 'n2o', _tier, uncertainties.get('n2o')), tier=_tier, process_category='vented', gas='n2o') if flared_n2o_tonnes > 0 else None
        
        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o_tonnes)
        
        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "well_depth": well_depth,
                "diameter": diameter,
                "pressure": pressure,
                "events": events,
                "ch4_content": ch4_content,
                "co2_content": co2_content,
                "control_efficiency": control_efficiency
            }
        )

class BlowdownCalculator(BaseCalculator):
    """
    API Eq. 6-4: Vessel/Pipeline Blowdown (Depressurization)
    V_std = V_physical * ((P_vessel_abs) / P_std) * Events
    Assumes standard temperature for simplicity if T is not provided.
    """
    def __init__(self):
        super().__init__("Blowdown Events", "Section 6.4")

    def calculate(self, blowdown_volume, pressure, events, ch4_content, uncertainties, co2_content=0.0, control_efficiency=0.0, ef_co2=None, ef_ch4=None, ef_n2o=None):
        self.validate_inputs({
            "blowdown_volume": blowdown_volume,
            "pressure": pressure,
            "events": events
        }, ["blowdown_volume", "pressure", "events"])
        
        # P_abs = P_gauge + P_atm; P_std = 14.696 psia
        # EXTRA-05 FIX: use 14.696 consistently (not 14.7)
        P_STD = 14.696
        p_abs = pressure + P_STD
        v_std_per_event = blowdown_volume * (p_abs / P_STD)
        total_v_std = v_std_per_event * events
        
        ch4_vol = total_v_std * ch4_content
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        co2_vol = total_v_std * co2_content
        co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
        co2_tonnes = co2_mass_kg / 1000.0
        
        # Vented fraction goes straight to atmosphere
        vented_ch4_tonnes = ch4_tonnes * (1.0 - control_efficiency)
        vented_co2_tonnes = co2_tonnes * (1.0 - control_efficiency)

        flared_co2_tonnes = 0.0
        flared_n2o_tonnes = 0.0
        flared_unburnt_ch4_tonnes = 0.0

        if control_efficiency > 0:
            if ef_co2 is not None and ef_ch4 is not None:
                # TIER 3 FLARING using Gas Analysis Factors!
                flared_volume = total_v_std * control_efficiency
                flared_co2_tonnes = (flared_volume * ef_co2) / 1000.0
                flared_unburnt_ch4_tonnes = (flared_volume * ef_ch4) / 1000.0
                flared_n2o_tonnes = (flared_volume * ef_n2o) / 1000.0 if ef_n2o else 0.0
            else:
                # TIER 1/2 FLARING (Simple Methane Combustion)
                flared_co2_tonnes = (ch4_tonnes * control_efficiency) * (44.01 / 16.04)
                flared_natural_co2_tonnes = co2_tonnes * control_efficiency
                flared_co2_tonnes += flared_natural_co2_tonnes

        total_ch4 = vented_ch4_tonnes + flared_unburnt_ch4_tonnes
        total_co2 = vented_co2_tonnes + flared_co2_tonnes

        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(total_ch4, resolve_ef_uncertainty('vented', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='vented', gas='ch4')
        co2_res = propagate_uncertainty(total_co2, resolve_ef_uncertainty('vented', 'co2', _tier, uncertainties.get('co2')), tier=_tier, process_category='vented', gas='co2') if total_co2 > 0 else None
        n2o_res = propagate_uncertainty(flared_n2o_tonnes, resolve_ef_uncertainty('vented', 'n2o', _tier, uncertainties.get('n2o')), tier=_tier, process_category='vented', gas='n2o') if flared_n2o_tonnes > 0 else None
        
        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o_tonnes)
        
        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "blowdown_volume": blowdown_volume,
                "pressure": pressure,
                "events": events,
                "ch4_content": ch4_content,
                "co2_content": co2_content,
                "control_efficiency": control_efficiency
            }
        )

class TankFlashingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Storage Tank Emissions", "Section 6.8")

    def calculate(self, throughput, gas_oil_ratio, ch4_content, control_efficiency, uncertainties, process_type="tank_flashing", ef_ch4=0):
        """
        Calculates Tank Emissions.
        If Flashing: Uses GOR method (Vasquez-Beggs or simple GOR * Throughput).
        If Working/Breathing: Uses simple Factor * Throughput.
        """
        self.validate_inputs({"throughput": throughput}, ["throughput"])

        is_flashing = process_type in ["tank_flashing", "tank", "storage_tanks"]
        
        if is_flashing:
            # API 4.4 / E&P Tanks Logic (Simplified GOR method)
            # CH4_emissions = Throughput * GOR * CH4_fraction * (1 - Control) * Density_CH4
            # GOR is scf/bbl. Throughput is bbl. Result is scf.
            
            # GOR is scf/bbl
            total_gas_scf = throughput * gas_oil_ratio
            ch4_vol_scf = total_gas_scf * ch4_content
            
            # Convert to mass
            ch4_vol_m3 = convert(ch4_vol_scf, "scf", "m3")
            ch4_mass_kg = ch4_vol_m3 * CONVERSIONS["density_ch4"]
            
            # Apply controls
            ch4_emitted_kg = ch4_mass_kg * (1.0 - control_efficiency)
            ch4_tonnes = ch4_emitted_kg / 1000.0
            
            _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
            ch4_res = propagate_uncertainty(ch4_tonnes, resolve_ef_uncertainty('tank_flashing', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='tank_flashing', gas='ch4')
        else:
            # Working / Breathing Losses
            # Uses supplied Emission Factor (kg/bbl or similar)
            # ef_ch4 comes from EmissionFactors.js via dispatcher
            
            ch4_kg = throughput * ef_ch4
            ch4_tonnes = ch4_kg / 1000.0
             
            _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
            ch4_res = propagate_uncertainty(ch4_tonnes, resolve_ef_uncertainty('tank', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='tank', gas='ch4')

        total_co2e = calculate_co2e(ch4=ch4_res["value"])
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "throughput_bbl": throughput,
                "gor": gas_oil_ratio if is_flashing else None,
                "type": process_type,
                "ef_used": ef_ch4 if not is_flashing else "GOR Calc"
            }
        )

class PneumaticDeviceCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Pneumatic Devices", "Section 6.10")

    def calculate(self, count, hours, bleed_rate, ch4_content, uncertainties):
        """
        API Section 6.10 - Device count * Bleed rate
        """
        self.validate_inputs({"count": count, "hours": hours, "bleed_rate": bleed_rate}, ["count", "hours", "bleed_rate"])
        
        # Bleed rate in scf/hr -> m3/hr
        bleed_m3_hr = convert(bleed_rate, "scf", "m3")
        
        total_ch4_vol = count * hours * bleed_m3_hr * ch4_content
        ch4_mass_kg = total_ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(ch4_tonnes, resolve_ef_uncertainty('pneumatic', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='pneumatic', gas='ch4')
        total_co2e = calculate_co2e(ch4=ch4_tonnes)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "device_count": count,
                "hours_operating": hours,
                "bleed_rate_scf_hr": bleed_rate
            }
        )
