"""
API Compendium 2021 - Section 6: Midstream & Process Emissions
Implementation of Acid Gas Removal (AGR / Amine Units) with Table 6-5 Methane Slip,
and Glycol Dehydrators using API §6.6 / GRI-GLYCalc Parametric Solubility Models.
"""
import math
from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e, convert, to_psia, to_fahrenheit
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty

class AGRCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Acid Gas Removal", "Section 6.5")

    def calculate(self, throughput, co2_in, co2_out, uncertainties, 
                  ch4_in=0.85, ch4_slip_fraction=0.001, acid_gas_control_eff=0.0, gwp_dict=None):
        """
        API Compendium 2021 §6.5 & Table 6-5:
        - CO2 mass balance from amine sweetening process
        - CH4 physical co-absorption and slip from regenerator overhead
        
        Parameters:
        - throughput: Gas throughput in MMscf/yr
        - co2_in: Native CO2 mole fraction entering unit (e.g. 0.04 for 4%)
        - co2_out: Treated gas CO2 mole fraction (e.g. 0.0005 for 50 ppm)
        - ch4_in: Methane mole fraction in feed gas (e.g. 0.85)
        - ch4_slip_fraction: Methane slip fraction per API Table 6-5 (default 0.001 = 0.1%)
        - acid_gas_control_eff: Destruction/recovery efficiency (e.g. 0.98 for Claus/thermal oxidizer)
        """
        self.validate_inputs({
            "throughput": throughput,
            "co2_in": co2_in
        }, ["throughput", "co2_in"])

        # Throughput in scf
        throughput_scf = float(throughput) * 1_000_000.0
        
        # 1. CO2 Mass Balance Venting
        diff_co2 = max(0.0, float(co2_in) - float(co2_out or 0.0))
        co2_vented_scf = throughput_scf * diff_co2
        co2_vented_m3 = convert(co2_vented_scf, "scf", "m3")
        co2_mass_kg = co2_vented_m3 * CONVERSIONS.get("density_co2", 1.861)
        
        # Apply acid gas control if present (e.g. AGI or capture)
        ctrl_eff = max(0.0, min(1.0, float(acid_gas_control_eff or 0.0)))
        co2_emitted_kg = co2_mass_kg * (1.0 - (ctrl_eff if ctrl_eff > 0.5 else 0.0)) # Claus oxidizes to CO2
        co2_tonnes = co2_emitted_kg / 1000.0
        
        # 2. CH4 Methane Slip (API Compendium 2021 §6.5 & Table 6-5)
        # Amine solutions co-absorb methane at high pressure, which desorbs in the regenerator column
        slip_rate = max(0.0, float(ch4_slip_fraction if ch4_slip_fraction is not None else 0.001))
        ch4_feed_frac = max(0.0, float(ch4_in or 0.85))
        ch4_slipped_scf = throughput_scf * ch4_feed_frac * slip_rate
        ch4_slipped_m3 = convert(ch4_slipped_scf, "scf", "m3")
        ch4_mass_kg = ch4_slipped_m3 * CONVERSIONS.get("density_ch4", 0.6785)
        
        # CH4 destroyed if acid gas routed to incinerator/flare/thermal oxidizer
        ch4_emitted_kg = ch4_mass_kg * (1.0 - ctrl_eff)
        ch4_tonnes = ch4_emitted_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        co2_res = propagate_uncertainty(
            co2_tonnes, 
            resolve_ef_uncertainty('midstream', 'co2', _tier, uncertainties.get('co2')), 
            tier=_tier, 
            process_category='midstream', 
            gas='co2'
        )
        ch4_res = propagate_uncertainty(
            ch4_tonnes, 
            resolve_ef_uncertainty('midstream', 'ch4', _tier, uncertainties.get('ch4')), 
            tier=_tier, 
            process_category='midstream', 
            gas='ch4'
        )
        n2o_res = None
        
        total_co2e = calculate_co2e(co2=co2_tonnes, ch4=ch4_tonnes, gwp_dict=gwp_dict)
        
        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "throughput_mmscf": throughput,
                "co2_in_pct": float(co2_in) * 100.0,
                "co2_out_pct": float(co2_out or 0.0) * 100.0,
                "ch4_slip_pct": slip_rate * 100.0,
                "control_eff_pct": ctrl_eff * 100.0
            },
            metadata={
                "standard_reference": "API Compendium 2021 §6.5 & Table 6-5",
                "ch4_slip_calculated": True
            }
        )

class DehydratorCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Glycol Dehydrator", "Section 6.6")

    def calculate(self, throughput=None, pump_rate=None, pump_unit='gph', hours=8760, 
                  ch4_content=0.85, control_eff=0.0, uncertainties=None,
                  contactor_pressure=800.0, press_unit='psig',
                  contactor_temperature=100.0, temp_unit='F',
                  has_flash_tank=True, flash_control_eff=0.0,
                  still_control_type='none', gwp_dict=None, **kwargs):
        """
        API Compendium 2021 §6.6 & GRI-GLYCalc Parametric Solubility Model (CALC-02 Remediation).
        
        Methane solubility in Triethylene Glycol (TEG) is calculated as a function of
        contactor operating pressure, contactor operating temperature, and gas composition:
        
        S_CH4 (scf/gal) = 0.032 * (P_psia)^0.96 * exp(-0.0022 * (T_F - 60)) * X_CH4
        
        Emissions are partitioned between Flash Tank separator and Regenerator Still Column Vent.
        """
        uncertainties = uncertainties or {}
        
        # 1. Check if Tier 1 (Default Emission Factor based on throughput alone)
        if (pump_rate is None or float(pump_rate or 0) <= 0) and throughput is not None:
            # API Compendium 2021 Table 6-6 & EPA Subpart W Table W-1A: Tier 1 default = 0.266 tonnes CH4 / MMscf (uncontrolled)
            # or 0.0532 tonnes CH4 / MMscf (controlled)
            tp_mmscf = float(throughput)
            eff = float(control_eff or 0.0)
            default_ef = 0.266 * (1.0 - eff)
            ch4_tonnes = tp_mmscf * default_ef
            co2_tonnes = 0.0
            
            _tier = resolve_tier('default')
            ch4_res = propagate_uncertainty(
                ch4_tonnes, 
                resolve_ef_uncertainty('midstream', 'ch4', _tier, uncertainties.get('ch4')), 
                tier=_tier, 
                process_category='midstream', 
                gas='ch4'
            )
            total_co2e = calculate_co2e(ch4=ch4_tonnes, gwp_dict=gwp_dict)
            
            return self.format_result(
                ch4=ch4_res,
                total_co2e=total_co2e,
                inputs={"throughput_mmscf": tp_mmscf, "tier": "Tier 1 (Default Factor)"},
                metadata={"method": "API Table 6-6 / EPA Subpart W Table W-1A Default Factor"}
            )

        # 2. Tier 3 Parametric Engineering Calculation
        self.validate_inputs({
            "pump_rate": pump_rate,
            "hours": hours
        }, ["pump_rate", "hours"])

        # Convert pump rate to US gallons per hour (gal/hr)
        rate_val = float(pump_rate)
        rate_gph = rate_val
        pu = str(pump_unit).strip().lower()
        if pu in ['lph', 'l/h', 'liter/hr', 'liters/hr']:
            rate_gph = convert(rate_val, 'l', 'gal')
        elif pu in ['m3h', 'm3/h', 'm3_hr']:
            rate_gph = convert(rate_val, 'm3', 'gal')
        elif pu in ['gpm', 'gal/min']:
            rate_gph = rate_val * 60.0

        op_hours = float(hours)
        ch4_frac = max(0.0, min(1.0, float(ch4_content if ch4_content is not None else 0.85)))
        
        # Contactor conditions
        p_psia = to_psia(contactor_pressure, press_unit)
        t_f = to_fahrenheit(contactor_temperature, temp_unit)
        
        # API Compendium 2021 §6.6 / GRI-GLYCalc parametric methane solubility in TEG:
        # S_CH4 = 0.032 * (P_psia)^0.96 * exp(-0.0022 * (T_F - 60)) * X_CH4
        # (Replaces the flat 3 scf/gal rule-of-thumb which understated high P/T units)
        p_term = math.pow(max(14.7, p_psia), 0.96)
        t_term = math.exp(-0.0022 * (t_f - 60.0))
        solubility_scf_per_gal = 0.032 * p_term * t_term * ch4_frac
        
        # Total dissolved methane across annual operating hours
        total_ch4_scf = rate_gph * solubility_scf_per_gal * op_hours
        
        # Stream Partitioning & Control Systems:
        # If Flash Tank is present: ~80% flashes off in flash tank, ~20% goes to regenerator still vent
        # If no Flash Tank: 100% goes directly to regenerator still vent
        still_eff = float(control_eff or 0.0)
        flash_eff = float(flash_control_eff or 0.0)
        
        # Auto-detect still control efficiency from device type if not explicitly overridden
        s_type = str(still_control_type).strip().lower()
        if still_eff == 0.0:
            if s_type == 'flare' or s_type == 'combustor':
                still_eff = 0.98
            elif s_type == 'thermal_oxidizer':
                still_eff = 0.99
            elif s_type == 'condenser':
                still_eff = 0.75
            elif s_type == 'vru':
                still_eff = 0.95
        
        if has_flash_tank:
            flash_gas_scf = total_ch4_scf * 0.80
            still_gas_scf = total_ch4_scf * 0.20
            ch4_emitted_scf = (flash_gas_scf * (1.0 - flash_eff)) + (still_gas_scf * (1.0 - still_eff))
        else:
            ch4_emitted_scf = total_ch4_scf * (1.0 - still_eff)

        # Convert scf to metric tonnes
        ch4_vol_m3 = convert(ch4_emitted_scf, "scf", "m3")
        ch4_mass_kg = ch4_vol_m3 * CONVERSIONS.get("density_ch4", 0.6785)
        ch4_tonnes = ch4_mass_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'site_specific'))
        ch4_res = propagate_uncertainty(
            ch4_tonnes, 
            resolve_ef_uncertainty('midstream', 'ch4', _tier, uncertainties.get('ch4')), 
            tier=_tier, 
            process_category='midstream', 
            gas='ch4'
        )
        total_co2e = calculate_co2e(ch4=ch4_tonnes, gwp_dict=gwp_dict)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "pump_rate_gph": rate_gph,
                "hours": op_hours,
                "contactor_pressure_psia": p_psia,
                "contactor_temperature_F": t_f,
                "solubility_scf_gal": round(solubility_scf_per_gal, 3),
                "has_flash_tank": has_flash_tank,
                "still_control_eff": still_eff,
                "flash_control_eff": flash_eff
            },
            metadata={
                "method": "API Compendium §6.6 Parametric GRI-GLYCalc Model",
                "solubility_model": "Vasquez-Beggs / TEG Henry's Law Correlation"
            }
        )
