"""
API Compendium 2021 - Section 8: Indirect Emissions
Implementation of indirect steam/heat and cogeneration allocation methodologies.
"""
from .base import BaseCalculator
from .units import calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty

class IndirectSteamCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Indirect Steam/Heat", "Section 8.1")

    def calculate(self, heat_energy, ef_co2, boiler_efficiency, transmission_loss, uncertainties, heat_unit="btu"):
        """
        API Equation 8-2: Indirect emissions from steam/heat
        Emissions = Energy / (Eff_boiler - Eff_loss) * EF
        
        heat_unit: 'btu' (default), 'mmbtu', or 'kwh'  — CALC-02 FIX
        """
        self.validate_inputs({"energy": heat_energy}, ["energy"])
        
        # CALC-02 FIX: normalize input energy to BTU first
        u = str(heat_unit or 'btu').lower().replace(' ', '')
        if u in ['kwh', 'kw-hr', 'kilowatthour']:
            energy_btu = heat_energy * 3412.142  # 1 kWh = 3412.142 BTU
        elif u in ['mmbtu', 'mm_btu']:
            energy_btu = heat_energy * 1_000_000.0
        elif u in ['gj', 'gigajoule']:
            energy_btu = heat_energy * 947817.12  # 1 GJ = 947,817 BTU
        elif u in ['mwh', 'mw-hr']:
            energy_btu = heat_energy * 3_412_142.0
        else:  # assume BTU
            energy_btu = heat_energy
        
        # Efficiencies are in fractions (e.g. 0.80)
        # CALC-09 FORMULA NOTE: Using additive loss (boiler_eff - trans_loss) as per API Eq 8-2
        # interpretation where both are absolute fractions.
        # Example: boiler_eff=0.85, trans_loss=0.03 → net=0.82
        # Alternative multiplicative form (0.85 × 0.97 = 0.8245) differs by ~0.5%.
        # Ensure UI labels transmission_loss as "absolute fraction lost" not "% of output".
        net_efficiency = boiler_efficiency - transmission_loss
        if net_efficiency <= 0:
            net_efficiency = 0.80 # Default fallback
            
        # ef_co2 is expected in kg/MMBtu
        co2_kg = (energy_btu / 1_000_000.0) * ef_co2 / net_efficiency
        co2_tonnes = co2_kg / 1000.0
        
        # Standard Scope 2 usually reported as CO2 only
        total_co2e = calculate_co2e(co2=co2_tonnes)
        
        _unc_dict = uncertainties or {}
        _tier = resolve_tier(_unc_dict.get('_factor_source', 'default'))
        co2_res = propagate_uncertainty(co2_tonnes, resolve_ef_uncertainty('indirect', 'co2', _tier, _unc_dict.get('co2')), tier=_tier, process_category='indirect', gas='co2')
        
        return self.format_result(
            co2=co2_res,
            total_co2e=total_co2e,
            inputs={
                "heat_energy": heat_energy,
                "heat_unit": heat_unit,
                "energy_btu": energy_btu,
                "boiler_efficiency": boiler_efficiency,
                "transmission_loss": transmission_loss
            }
        )

class CogenAllocationCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Cogeneration Allocation", "Section 8.3")

    def calculate(self, total_emissions, heat_output, power_output, method="wri_efficiency", uncertainties=None):
        """
        API Section 8.3 - Allocation of Cogeneration Emissions
        Methods: wri_efficiency, energy_content, uk_ets
        """
        self.validate_inputs({
            "total_emissions": total_emissions,
            "heat_output": heat_output,
            "power_output": power_output
        }, ["total_emissions", "heat_output", "power_output"])
        
        if method == "wri_efficiency":
            # API Equation 8-5: WRI/WBCSD Efficiency Method
            # e_h = 0.8 (default), e_p = 0.33 (default)
            e_h = 0.8; e_p = 0.33
            denominator = (heat_output / e_h) + (power_output / e_p)
            allocated_heat = ((heat_output / e_h) / denominator) * total_emissions
            allocated_power = ((power_output / e_p) / denominator) * total_emissions
        elif method == "energy_content":
            # Simple energy content allocation
            denominator = heat_output + power_output
            allocated_heat = (heat_output / denominator) * total_emissions
            allocated_power = (power_output / denominator) * total_emissions
        else:
            # Default to Energy Content
            denominator = heat_output + power_output
            allocated_heat = (heat_output / denominator) * total_emissions
            allocated_power = (power_output / denominator) * total_emissions

        _unc_dict = uncertainties or {}
        _tier = resolve_tier(_unc_dict.get('_factor_source', 'default'))
        co2_res = propagate_uncertainty(allocated_heat, resolve_ef_uncertainty('indirect', 'co2', _tier, _unc_dict.get('co2')), tier=_tier, process_category='indirect', gas='co2')

        return self.format_result(
            co2=co2_res,
            total_co2e=calculate_co2e(co2=allocated_heat),
            inputs={
                "total_emissions": total_emissions,
                "heat_output": heat_output,
                "power_output": power_output,
                "method": method
            },
            metadata={
                "allocated_heat_tonnes": allocated_heat,
                "allocated_power_tonnes": allocated_power,
                "allocation_method": f"api2021_cogen_{method}"
            }
        )
