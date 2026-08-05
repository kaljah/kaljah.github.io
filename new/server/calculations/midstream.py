"""
API Compendium 2021 - Section 5/6: Midstream Processes
Implementation of Acid Gas Removal (AGR) and Dehydrators.
"""
from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e, convert
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty

class AGRCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Acid Gas Removal", "Section 6.5")

    def calculate(self, throughput, co2_in, co2_out, uncertainties):
        """
        Mass balance for CO2 venting from Amine units.
        Emissions = Throughput * (CO2_in - CO2_out)
        """
        self.validate_inputs({
            "throughput": throughput,
            "co2_in": co2_in
        }, ["throughput", "co2_in"])

        # Throughput is usually MMscf/yr
        # Convert to scf
        throughput_scf = throughput * 1_000_000.0
        
        # Calculate volume of CO2 vented
        # vol_vented = throughput * (Xin - Xout)
        # Assuming fractions are passed (0-1), or convert % -> fraction
        # Let's assume input is fraction (0.02 for 2%)
        
        # Guard against negative
        diff = max(0, co2_in - co2_out)
        co2_vented_scf = throughput_scf * diff
        
        # Convert to mass (kg)
        # Density CO2 @ standard conditions ~ 1.861 kg/m3 or ~ 0.0526 kg/scf
        # CONVERSIONS["density_co2"] is kg/m3 (1.861)
        # scf -> m3
        co2_vented_m3 = convert(co2_vented_scf, "scf", "m3")
        co2_mass_kg = co2_vented_m3 * CONVERSIONS["density_co2"]
        
        co2_tonnes = co2_mass_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        co2_res = propagate_uncertainty(co2_tonnes, resolve_ef_uncertainty('midstream', 'co2', _tier, uncertainties.get('co2')), tier=_tier, process_category='midstream', gas='co2')
        
        # CH4 is small, usually considered negligible or specific slip factor
        ch4_res = {"value": 0, "uncertainty": 0}
        n2o_res = {"value": 0, "uncertainty": 0}
        
        total_co2e = calculate_co2e(co2_tonnes)
        
        return self.format_result(
            co2=co2_res,
            ch4=ch4_res,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "throughput_mmscf": throughput,
                "co2_in_pct": co2_in * 100,
                "co2_out_pct": co2_out * 100
            }
        )

class DehydratorCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Glycol Dehydrator", "Section 6.6")

    def calculate(self, throughput, pump_rate, pump_unit, hours, ch4_content, control_eff, uncertainties):
        """
        Engineering calculation based on Glycol Pump Rate.
        API Equation: Total Gas = Rate * Factor (3 scf/gal)
        """
        # Validate inputs
        self.validate_inputs({
            "pump_rate": pump_rate,
            "hours": hours
        }, ["pump_rate", "hours"])

        # Convert pump rate to gal/hr
        rate_gph = pump_rate
        if pump_unit == 'lph':
            rate_gph = convert(pump_rate, 'l', 'gal') # L -> gal
        elif pump_unit == 'm3h':
             rate_gph = convert(pump_rate, 'm3', 'gal')

        # Rule of Thumb Factor: 3 scf gas / gal glycol
        # This covers flash tank + regenerator vent typical
        gas_factor = 3.0 
        
        total_gas_vented_scf = rate_gph * gas_factor * hours
        
        # Methane portion
        ch4_vol_scf = total_gas_vented_scf * ch4_content
        
        # Convert to mass
        ch4_vol_m3 = convert(ch4_vol_scf, "scf", "m3")
        ch4_mass_kg = ch4_vol_m3 * CONVERSIONS["density_ch4"]
        
        # Apply controls
        ch4_emitted_kg = ch4_mass_kg * (1.0 - control_eff)
        ch4_tonnes = ch4_emitted_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(ch4_tonnes, resolve_ef_uncertainty('midstream', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='midstream', gas='ch4')
        total_co2e = calculate_co2e(ch4=ch4_tonnes)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "pump_rate_gph": rate_gph,
                "hours": hours,
                "control_eff": control_eff
            }
        )
