"""
API Compendium 2021 - Section 6: Vented and Process Emissions
Implementation of equations for mud degassing, completions, liquids unloading, 
blowdowns (with thermodynamic T & P corrections), tanks, and pneumatics.
"""
from .base import BaseCalculator
from .units import (
    CONVERSIONS, calculate_co2e, convert, 
    to_psia, to_kelvin, STD_TEMP_K, STD_PRESSURE_PSIA, normalize_gas_volume_to_standard
)
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty
import math

class MudDegassingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Drilling Mud Degassing", "Section 6.2")

    def calculate(self, mud_volume, mud_type, uncertainties, ef_ch4=None, gwp_dict=None):
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
        
        ch4_kg = float(mud_volume) * ef
        ch4_tonnes = ch4_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(
            ch4_tonnes, 
            resolve_ef_uncertainty('vented', 'ch4', _tier, uncertainties.get('ch4')), 
            tier=_tier, 
            process_category='vented', 
            gas='ch4'
        )
        total_co2e = calculate_co2e(ch4=ch4_tonnes, gwp_dict=gwp_dict)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={"mud_volume": mud_volume, "mud_type": mud_type, "ef_ch4_used": ef}
        )

class CompletionFlowbackCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Well Completion Flowback", "Section 6.3")

    def calculate(self, flowback_volume=None, ch4_content=0.85, control_efficiency=0.0, uncertainties=None,
                  co2_content=0.0, ef_co2=None, ef_ch4=None, ef_n2o=None,
                  calculation_method='metered_volume', flowback_rate=None, flowback_duration_hours=None,
                  liquid_flowback_bbl=None, gas_oil_ratio=None, choke_size_in=None, well_head_pressure=None,
                  gwp_dict=None):
        """
        API Compendium 2021 §6.3 & EPA Subpart W §98.233(c) Completions & Workovers Flowback:
        Supports 3 rigorous calculation methodologies:
        1. 'metered_volume': Direct standard gas volume measurement (scf or m3).
        2. 'rate_duration': Flowback rate (Mscf/day or scf/hr) * duration (hours).
        3. 'gor_liquid': Liquid flowback volume (bbl) * GOR (scf/bbl).
        """
        uncertainties = uncertainties or {}
        
        # Determine standard gas volume (in m3) based on selected method
        method = str(calculation_method).lower()
        total_gas_scf = 0.0
        
        if method == 'rate_duration' and flowback_rate and flowback_duration_hours:
            # flowback_rate in Mscf/day -> scf/hr = (rate * 1000) / 24
            rate_scf_hr = (float(flowback_rate) * 1000.0) / 24.0
            total_gas_scf = rate_scf_hr * float(flowback_duration_hours)
            total_gas_m3 = convert(total_gas_scf, "scf", "m3")
        elif method == 'gor_liquid' and liquid_flowback_bbl and gas_oil_ratio:
            total_gas_scf = float(liquid_flowback_bbl) * float(gas_oil_ratio)
            total_gas_m3 = convert(total_gas_scf, "scf", "m3")
        else:
            # Direct flowback volume passed in m3 (or scf)
            self.validate_inputs({"flowback_volume": flowback_volume}, ["flowback_volume"])
            total_gas_m3 = float(flowback_volume)
            total_gas_scf = convert(total_gas_m3, "m3", "scf")

        ch4_frac = max(0.0, min(1.0, float(ch4_content if ch4_content is not None else 0.85)))
        co2_frac = max(0.0, min(1.0, float(co2_content or 0.0)))
        ctrl_eff = max(0.0, min(1.0, float(control_efficiency or 0.0)))
        
        # Methane mass
        ch4_vol = total_gas_m3 * ch4_frac
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        # CO2 mass
        co2_vol = total_gas_m3 * co2_frac
        co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
        co2_tonnes = co2_mass_kg / 1000.0
        
        # Vented fraction goes straight to atmosphere
        vented_ch4_tonnes = ch4_tonnes * (1.0 - ctrl_eff)
        vented_co2_tonnes = co2_tonnes * (1.0 - ctrl_eff)

        flared_co2_tonnes = 0.0
        flared_n2o_tonnes = 0.0
        flared_unburnt_ch4_tonnes = 0.0

        if ctrl_eff > 0:
            if ef_co2 is not None and ef_ch4 is not None:
                # TIER 3 FLARING using Gas Analysis Factors
                flared_volume = total_gas_m3 * ctrl_eff
                flared_co2_tonnes = (flared_volume * ef_co2) / 1000.0
                flared_unburnt_ch4_tonnes = (flared_volume * ef_ch4) / 1000.0
                flared_n2o_tonnes = (flared_volume * ef_n2o) / 1000.0 if ef_n2o else 0.0
            else:
                # TIER 1/2 FLARING (Dual Efficiency: 98% combustion of CH4 to CO2)
                flared_ch4_combusted = (ch4_tonnes * ctrl_eff) * 0.98
                flared_co2_tonnes = flared_ch4_combusted * (44.01 / 16.04) + (co2_tonnes * ctrl_eff)
                flared_unburnt_ch4_tonnes = (ch4_tonnes * ctrl_eff) * 0.02
                flared_n2o_tonnes = (total_gas_m3 * ctrl_eff * (ef_n2o or 0.0001)) / 1000.0

        total_ch4 = vented_ch4_tonnes + flared_unburnt_ch4_tonnes
        total_co2 = vented_co2_tonnes + flared_co2_tonnes
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'site_specific' if method != 'metered_volume' else 'default'))
        ch4_res = propagate_uncertainty(
            total_ch4, 
            resolve_ef_uncertainty('vented', 'ch4', _tier, uncertainties.get('ch4')), 
            tier=_tier, 
            process_category='vented', 
            gas='ch4'
        )
        co2_res = propagate_uncertainty(
            total_co2, 
            resolve_ef_uncertainty('vented', 'co2', _tier, uncertainties.get('co2')), 
            tier=_tier, 
            process_category='vented', 
            gas='co2'
        ) if total_co2 > 0 else None
        n2o_res = propagate_uncertainty(
            flared_n2o_tonnes, 
            resolve_ef_uncertainty('vented', 'n2o', _tier, uncertainties.get('n2o')), 
            tier=_tier, 
            process_category='vented', 
            gas='n2o'
        ) if flared_n2o_tonnes > 0 else None
        
        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o_tonnes, gwp_dict=gwp_dict)
        
        return self.format_result(
            ch4=ch4_res,
            co2=co2_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "method": method,
                "flowback_volume_m3": total_gas_m3,
                "flowback_volume_scf": total_gas_scf,
                "ch4_content": ch4_frac,
                "control_efficiency": ctrl_eff
            },
            metadata={
                "standard": "API Compendium §6.3 / EPA Subpart W §98.233(c)",
                "calculation_method": method
            }
        )

class LiquidsUnloadingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Liquids Unloading (Volume-Based)", "Section 6.4")

    def calculate(self, well_depth, diameter, pressure, ch4_content, events, uncertainties, 
                  co2_content=0.0, control_efficiency=0.0, ef_co2=None, ef_ch4=None, ef_n2o=None,
                  operating_temperature=60.0, temp_unit='F', gwp_dict=None):
        """
        API Equation 6-3 - Volume per unloading event with temperature correction:
        V_std = (pi/4) * D^2 * Depth * (P_tubing_abs / P_std) * (T_std / T_well_abs)
        """
        self.validate_inputs({
            "depth": well_depth,
            "diameter": diameter,
            "pressure": pressure,
            "events": events
        }, ["depth", "diameter", "pressure", "events"])
        
        # Diameter in inches -> convert to meters
        d_m = float(diameter) * 0.0254
        
        # Depth in feet -> convert to meters (standard oilfield unit is feet)
        depth_m = float(well_depth) * 0.3048

        # Volume at tubing conditions (m3)
        v_tubing = (math.pi / 4.0) * (d_m**2) * depth_m

        # Pressure and temperature correction (API Eq. 6-3 & §4.2.1)
        p_abs = to_psia(pressure, 'psig')
        p_factor = p_abs / STD_PRESSURE_PSIA
        
        t_abs_k = to_kelvin(operating_temperature, temp_unit)
        t_factor = STD_TEMP_K / max(1.0, t_abs_k)
        
        v_std = v_tubing * p_factor * t_factor
        total_v_std = v_std * float(events)
        
        ch4_vol = total_v_std * float(ch4_content)
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        co2_vol = total_v_std * float(co2_content or 0.0)
        co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
        co2_tonnes = co2_mass_kg / 1000.0
        
        ctrl_eff = float(control_efficiency or 0.0)
        vented_ch4_tonnes = ch4_tonnes * (1.0 - ctrl_eff)
        vented_co2_tonnes = co2_tonnes * (1.0 - ctrl_eff)

        flared_co2_tonnes = 0.0
        flared_n2o_tonnes = 0.0
        flared_unburnt_ch4_tonnes = 0.0

        if ctrl_eff > 0:
            if ef_co2 is not None and ef_ch4 is not None:
                flared_volume = total_v_std * ctrl_eff
                flared_co2_tonnes = (flared_volume * ef_co2) / 1000.0
                flared_unburnt_ch4_tonnes = (flared_volume * ef_ch4) / 1000.0
                flared_n2o_tonnes = (flared_volume * ef_n2o) / 1000.0 if ef_n2o else 0.0
            else:
                flared_ch4_combusted = (ch4_tonnes * ctrl_eff) * 0.98
                flared_co2_tonnes = flared_ch4_combusted * (44.01 / 16.04) + (co2_tonnes * ctrl_eff)
                flared_unburnt_ch4_tonnes = (ch4_tonnes * ctrl_eff) * 0.02
                flared_n2o_tonnes = (total_v_std * ctrl_eff * (ef_n2o or 0.0001)) / 1000.0

        total_ch4 = vented_ch4_tonnes + flared_unburnt_ch4_tonnes
        total_co2 = vented_co2_tonnes + flared_co2_tonnes

        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(
            total_ch4, 
            resolve_ef_uncertainty('vented', 'ch4', _tier, uncertainties.get('ch4')), 
            tier=_tier, 
            process_category='vented', 
            gas='ch4'
        )
        co2_res = propagate_uncertainty(
            total_co2, 
            resolve_ef_uncertainty('vented', 'co2', _tier, uncertainties.get('co2')), 
            tier=_tier, 
            process_category='vented', 
            gas='co2'
        ) if total_co2 > 0 else None
        n2o_res = propagate_uncertainty(
            flared_n2o_tonnes, 
            resolve_ef_uncertainty('vented', 'n2o', _tier, uncertainties.get('n2o')), 
            tier=_tier, 
            process_category='vented', 
            gas='n2o'
        ) if flared_n2o_tonnes > 0 else None
        
        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o_tonnes, gwp_dict=gwp_dict)
        
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
                "control_efficiency": control_efficiency,
                "operating_temperature": operating_temperature
            }
        )

class BlowdownCalculator(BaseCalculator):
    """
    API Eq. 6-4: Vessel/Pipeline Blowdown (Depressurization)
    V_std = V_physical * (P_vessel_abs / P_std) * (T_std / T_vessel_abs) * (1 / Z) * Events
    Remediates CALC-06 by incorporating exact temperature and compressibility normalization.
    """
    def __init__(self):
        super().__init__("Blowdown Events", "Section 6.4")

    def calculate(self, blowdown_volume, pressure, events, ch4_content, uncertainties, 
                  co2_content=0.0, control_efficiency=0.0, ef_co2=None, ef_ch4=None, ef_n2o=None,
                  operating_temperature=60.0, temp_unit='F', press_unit='psig', z_factor=1.0, gwp_dict=None):
        self.validate_inputs({
            "blowdown_volume": blowdown_volume,
            "pressure": pressure,
            "events": events
        }, ["blowdown_volume", "pressure", "events"])
        
        # API Eq. 6-4 with complete temperature and pressure normalization (CALC-06 Remediation)
        p_abs = to_psia(pressure, press_unit)
        p_factor = p_abs / STD_PRESSURE_PSIA
        
        t_abs_k = to_kelvin(operating_temperature, temp_unit)
        t_factor = STD_TEMP_K / max(1.0, t_abs_k)
        
        z = float(z_factor) if z_factor and float(z_factor) > 0 else 1.0
        
        v_std_per_event = float(blowdown_volume) * p_factor * t_factor * (1.0 / z)
        total_v_std = v_std_per_event * float(events)
        
        ch4_vol = total_v_std * float(ch4_content)
        ch4_mass_kg = ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0

        co2_vol = total_v_std * float(co2_content or 0.0)
        co2_mass_kg = co2_vol * CONVERSIONS["density_co2"]
        co2_tonnes = co2_mass_kg / 1000.0
        
        ctrl_eff = float(control_efficiency or 0.0)
        vented_ch4_tonnes = ch4_tonnes * (1.0 - ctrl_eff)
        vented_co2_tonnes = co2_tonnes * (1.0 - ctrl_eff)

        flared_co2_tonnes = 0.0
        flared_n2o_tonnes = 0.0
        flared_unburnt_ch4_tonnes = 0.0

        if ctrl_eff > 0:
            if ef_co2 is not None and ef_ch4 is not None:
                # TIER 3 FLARING using Gas Analysis Factors!
                flared_volume = total_v_std * ctrl_eff
                flared_co2_tonnes = (flared_volume * ef_co2) / 1000.0
                flared_unburnt_ch4_tonnes = (flared_volume * ef_ch4) / 1000.0
                flared_n2o_tonnes = (flared_volume * ef_n2o) / 1000.0 if ef_n2o else 0.0
            else:
                flared_ch4_combusted = (ch4_tonnes * ctrl_eff) * 0.98
                flared_co2_tonnes = flared_ch4_combusted * (44.01 / 16.04) + (co2_tonnes * ctrl_eff)
                flared_unburnt_ch4_tonnes = (ch4_tonnes * ctrl_eff) * 0.02
                flared_n2o_tonnes = (total_v_std * ctrl_eff * (ef_n2o or 0.0001)) / 1000.0

        total_ch4 = vented_ch4_tonnes + flared_unburnt_ch4_tonnes
        total_co2 = vented_co2_tonnes + flared_co2_tonnes

        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(
            total_ch4, 
            resolve_ef_uncertainty('vented', 'ch4', _tier, uncertainties.get('ch4')), 
            tier=_tier, 
            process_category='vented', 
            gas='ch4'
        )
        co2_res = propagate_uncertainty(
            total_co2, 
            resolve_ef_uncertainty('vented', 'co2', _tier, uncertainties.get('co2')), 
            tier=_tier, 
            process_category='vented', 
            gas='co2'
        ) if total_co2 > 0 else None
        n2o_res = propagate_uncertainty(
            flared_n2o_tonnes, 
            resolve_ef_uncertainty('vented', 'n2o', _tier, uncertainties.get('n2o')), 
            tier=_tier, 
            process_category='vented', 
            gas='n2o'
        ) if flared_n2o_tonnes > 0 else None
        
        total_co2e = calculate_co2e(ch4=total_ch4, co2=total_co2, n2o=flared_n2o_tonnes, gwp_dict=gwp_dict)
        
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
                "control_efficiency": control_efficiency,
                "operating_temperature": operating_temperature
            },
            metadata={
                "standard": "API Compendium Eq. 6-4 (T & P corrected)",
                "temp_correction_applied": True
            }
        )

class TankFlashingCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Storage Tank Emissions", "Section 6.8")

    def calculate(self, throughput, gas_oil_ratio, ch4_content, control_efficiency, uncertainties, process_type="tank_flashing", ef_ch4=0, gwp_dict=None):
        """
        Calculates Tank Emissions.
        If Flashing: Uses GOR method (Vasquez-Beggs or simple GOR * Throughput).
        If Working/Breathing: Uses simple Factor * Throughput.
        """
        self.validate_inputs({"throughput": throughput}, ["throughput"])

        is_flashing = process_type in ["tank_flashing", "tank", "storage_tanks"]
        
        if is_flashing:
            total_gas_scf = float(throughput) * float(gas_oil_ratio)
            ch4_vol_scf = total_gas_scf * float(ch4_content)
            
            ch4_vol_m3 = convert(ch4_vol_scf, "scf", "m3")
            ch4_mass_kg = ch4_vol_m3 * CONVERSIONS["density_ch4"]
            
            ctrl_eff = float(control_efficiency or 0.0)
            ch4_emitted_kg = ch4_mass_kg * (1.0 - ctrl_eff)
            ch4_tonnes = ch4_emitted_kg / 1000.0
            
            _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
            ch4_res = propagate_uncertainty(
                ch4_tonnes, 
                resolve_ef_uncertainty('tank_flashing', 'ch4', _tier, uncertainties.get('ch4')), 
                tier=_tier, 
                process_category='tank_flashing', 
                gas='ch4'
            )
        else:
            ch4_kg = float(throughput) * float(ef_ch4 or 0.0)
            ch4_tonnes = ch4_kg / 1000.0
             
            _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
            ch4_res = propagate_uncertainty(
                ch4_tonnes, 
                resolve_ef_uncertainty('tank', 'ch4', _tier, uncertainties.get('ch4')), 
                tier=_tier, 
                process_category='tank', 
                gas='ch4'
            )

        total_co2e = calculate_co2e(ch4=ch4_tonnes, gwp_dict=gwp_dict)
        
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

    def calculate(self, count, hours, bleed_rate, ch4_content, uncertainties, gwp_dict=None):
        """
        API Section 6.10 - Device count * Bleed rate
        """
        self.validate_inputs({"count": count, "hours": hours, "bleed_rate": bleed_rate}, ["count", "hours", "bleed_rate"])
        
        # Bleed rate in scf/hr -> m3/hr
        bleed_m3_hr = convert(float(bleed_rate), "scf", "m3")
        
        total_ch4_vol = float(count) * float(hours) * bleed_m3_hr * float(ch4_content)
        ch4_mass_kg = total_ch4_vol * CONVERSIONS["density_ch4"]
        ch4_tonnes = ch4_mass_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(
            ch4_tonnes, 
            resolve_ef_uncertainty('pneumatic', 'ch4', _tier, uncertainties.get('ch4')), 
            tier=_tier, 
            process_category='pneumatic', 
            gas='ch4'
        )
        total_co2e = calculate_co2e(ch4=ch4_tonnes, gwp_dict=gwp_dict)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "device_count": count,
                "hours_operating": hours,
                "bleed_rate_scf_hr": bleed_rate
            }
        )
