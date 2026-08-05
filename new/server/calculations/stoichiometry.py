"""
API Compendium 2021 - Section 4: Calculation Fundamentals
Implementation of stoichiometric mass balance calculations.
"""
from .base import BaseCalculator
from .units import calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty

class StoichiometricCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Stoichiometric Mass Balance", "Section 4.1")

    def calculate(self, fuel_mass, carbon_content, uncertainties, mass_unit="kg"):
        """
        API Equation 4-3/4-4: CO2 from carbon content
        CO2 = Mass * Carbon_Content * (44.01 / 12.011)
        """
        self.validate_inputs({
            "mass": fuel_mass,
            "carbon_content": carbon_content
        }, ["mass", "carbon_content"])
        
        # Normalize to kg
        norm_mass = fuel_mass
        u = str(mass_unit).lower()
        if u in ["lb", "lbs", "pound", "pounds"]:
            norm_mass = fuel_mass * 0.453592
        elif u in ["tonne", "tonnes", "metric_ton"]:
            norm_mass = fuel_mass * 1000.0
            
        # stoichiometric ratio CO2/C
        ratio = 44.01 / 12.011
        
        # carbon_content expected as fraction (e.g. 0.85)
        co2_kg = norm_mass * carbon_content * ratio
        co2_tonnes = co2_kg / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        co2_res = propagate_uncertainty(co2_tonnes, resolve_ef_uncertainty('stoichiometric', 'co2', _tier, uncertainties.get('co2')), tier=_tier, process_category='stoichiometric', gas='co2')
        total_co2e = calculate_co2e(co2=co2_tonnes)
        
        return self.format_result(
            co2=co2_res,
            total_co2e=total_co2e,
            inputs={
                "fuel_mass": fuel_mass,
                "carbon_content": carbon_content
            }
        )
