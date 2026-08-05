"""
API Compendium 2021 - Section 7: Fugitive Emissions
Implementation of equations for component-level and equipment-level fugitives.
"""
from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty

class ComponentFugitiveCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Component-Level Fugitive", "Section 7.2")

    def calculate(self, component_counts, ch4_content, uncertainties):
        """
        Average Factor Method - counts * EF
        component_counts: dict of {type: count}
        """
        self.validate_inputs({"counts": component_counts}, ["counts"])
        
        # Example factors (kg CH4 / hr / component) - simplified from Table 7-1
        # In real implementation, these would come from emission_factors.py
        
        total_ch4_kg_hr = 0
        for comp_type, data in component_counts.items():
            count = data.get('count', 0)
            ef = data.get('ef', 0)
            total_ch4_kg_hr += count * ef * ch4_content

        total_ch4_tonnes_year = (total_ch4_kg_hr * 8760) / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(total_ch4_tonnes_year, resolve_ef_uncertainty('fugitive_component', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='fugitive_component', gas='ch4')
        total_co2e = calculate_co2e(ch4=total_ch4_tonnes_year)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "component_counts": component_counts,
                "ch4_content": ch4_content
            }
        )

class EquipmentFugitiveCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Equipment-Level Fugitive", "Section 7.2.2")

    def calculate(self, equipment_count, ef, ch4_content, uncertainties, ef_unit="kg/hr"):
        """
        Average Factor Method for equipment - count * EF
        """
        self.validate_inputs({"count": equipment_count, "ef": ef}, ["count", "ef"])
        
        # Check if EF is already in tonnes
        is_tonne = "tonne" in ef_unit.lower() or " mt" in ef_unit.lower()
        # Check if EF is already methane-based
        is_methane = "ch" in ef_unit.lower() or "methane" in ef_unit.lower()
        
        total_ch4_raw = equipment_count * ef
        if not is_methane:
            total_ch4_raw *= ch4_content
        
        # Determine annual tonnes
        if "yr" in ef_unit.lower() or "year" in ef_unit.lower():
            # Factor is already annual
            if is_tonne:
                total_ch4_tonnes_year = total_ch4_raw
            else:
                total_ch4_tonnes_year = total_ch4_raw / 1000.0
        else:
            # Factor is hourly (default for API fugitive components)
            total_ch4_annual_raw = total_ch4_raw * 8760
            if is_tonne:
                total_ch4_tonnes_year = total_ch4_annual_raw
            else:
                total_ch4_tonnes_year = total_ch4_annual_raw / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(total_ch4_tonnes_year, resolve_ef_uncertainty('equipment_fugitive', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='equipment_fugitive', gas='ch4')
        total_co2e = calculate_co2e(ch4=total_ch4_tonnes_year)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "equipment_count": equipment_count,
                "ef": ef,
                "ch4_content": ch4_content
            }
        )

class CompressorSealCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Compressor Seal Leakage", "Section 7.2.3")

    def calculate(self, compressor_count, seal_type, uncertainties):
        """
        API Section 7.2.3 - Compressor seals
        """
        self.validate_inputs({"count": compressor_count}, ["count"])
        
        # kg CH4 / hr / compressor
        factors = {
            "centrifugal_wet": 15.0,
            "centrifugal_dry": 1.5,
            "reciprocating": 1.2
        }
        ef = factors.get(seal_type, 1.2)
        
        total_ch4_kg_hr = compressor_count * ef
        total_ch4_tonnes_year = (total_ch4_kg_hr * 8760) / 1000.0
        
        _tier = resolve_tier(uncertainties.get('_factor_source', 'default'))
        ch4_res = propagate_uncertainty(total_ch4_tonnes_year, resolve_ef_uncertainty('compressor_fugitive', 'ch4', _tier, uncertainties.get('ch4')), tier=_tier, process_category='compressor_fugitive', gas='ch4')
        total_co2e = calculate_co2e(ch4=total_ch4_tonnes_year)
        
        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "compressor_count": compressor_count,
                "seal_type": seal_type
            }
        )
