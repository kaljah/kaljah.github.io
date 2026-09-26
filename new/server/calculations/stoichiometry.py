"""
API Compendium 2021 - Section 4: Calculation Fundamentals
Implementation of stoichiometric mass balance calculations.
"""

from .base import BaseCalculator
from .units import CONVERSIONS, calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty


class StoichiometricCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Stoichiometric Mass Balance", "Section 4.1")

    def calculate(
        self, fuel_mass, carbon_content, uncertainties=None, mass_unit="kg", oxidation_factor=1.0, gwp_dict=None
    ):
        """
        API Equation 4-3/4-4: CO2 from carbon content
        CO2 = Mass * Carbon_Content * Oxidation_Factor * (44.01 / 12.011)
        """
        self.validate_inputs(
            {"mass": fuel_mass, "carbon_content": carbon_content},
            ["mass", "carbon_content"],
        )

        # Normalize to kg
        norm_mass = fuel_mass
        u = str(mass_unit).strip().lower()
        if u in ["lb", "lbs", "pound", "pounds"]:
            norm_mass = fuel_mass * CONVERSIONS["lb_to_kg"]
        elif u in ["tonne", "tonnes", "metric_ton", "metric_tons", "mt", "t"]:
            norm_mass = fuel_mass * CONVERSIONS["tonne_to_kg"]
        elif u in ["ton", "tons", "short_ton", "short_tons", "us_ton"]:
            norm_mass = fuel_mass * CONVERSIONS["short_ton_to_kg"]
        elif u in ["long_ton", "long_tons"]:
            norm_mass = fuel_mass * CONVERSIONS["long_ton_to_kg"]
        elif u in ["g", "gram", "grams"]:
            norm_mass = fuel_mass * 0.001
        elif u in ["kg", "kgs", "kilogram", "kilograms"]:
            norm_mass = fuel_mass
        else:
            try:
                from .units import convert
                norm_mass = convert(fuel_mass, mass_unit, "kg")
            except Exception:
                norm_mass = fuel_mass

        # stoichiometric ratio CO2/C
        ratio = 44.01 / 12.011

        # carbon_content normalized to fraction (e.g. 0.85 or 85.0 -> 0.85)
        c = float(carbon_content)
        if c > 1.0:
            c /= 100.0
        c = max(0.0, min(1.0, c))

        # oxidation factor (default 1.0, e.g. 0.99 for solid fuels)
        ox = float(oxidation_factor if oxidation_factor is not None else 1.0)
        if ox > 1.0:
            ox /= 100.0
        ox = max(0.0, min(1.0, ox))

        co2_kg = norm_mass * c * ox * ratio
        co2_tonnes = co2_kg / 1000.0

        uncertainties = uncertainties or {}
        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        co2_res = propagate_uncertainty(
            co2_tonnes,
            resolve_ef_uncertainty(
                "stoichiometric", "co2", _tier, uncertainties.get("co2")
            ),
            tier=_tier,
            process_category="stoichiometric",
            gas="co2",
        )
        total_co2e = calculate_co2e(co2=co2_tonnes, gwp_dict=gwp_dict)

        return self.format_result(
            co2=co2_res,
            total_co2e=total_co2e,
            inputs={"fuel_mass": fuel_mass, "carbon_content": carbon_content, "oxidation_factor": ox},
        )


class NitricAcidCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Nitric/Adipic Acid Production", "API Compendium Section 6 / IPCC")

    def calculate(
        self,
        production_amount,
        ef_n2o=None,
        abatement_efficiency=0.0,
        mass_unit="tonne",
        uncertainties=None,
        gwp_dict=None,
        process_type="nitric_acid_production",
    ):
        """
        API Compendium 2021 Section 6, pg 407 / IPCC 2006 Vol 3 Ch 3:
        N2O emissions from catalytic oxidation of ammonia (nitric acid) or cyclohexanone oxidation (adipic acid).
        N2O (kg) = Production (tonnes) * EF_N2O (kg/tonne) * (1 - Abatement_Efficiency)
        """
        self.validate_inputs(
            {"production_amount": production_amount},
            ["production_amount"],
        )

        norm_mass = float(production_amount)
        u = str(mass_unit).strip().lower()
        if u in ["lb", "lbs", "pound", "pounds"]:
            norm_tonnes = norm_mass * CONVERSIONS["lb_to_kg"] / 1000.0
        elif u in ["tonne", "tonnes", "metric_ton", "metric_tons", "mt", "t"]:
            norm_tonnes = norm_mass
        elif u in ["ton", "tons", "short_ton", "short_tons", "us_ton"]:
            norm_tonnes = norm_mass * CONVERSIONS["short_ton_to_kg"] / 1000.0
        elif u in ["kg", "kgs", "kilogram", "kilograms"]:
            norm_tonnes = norm_mass / 1000.0
        elif u in ["g", "gram", "grams"]:
            norm_tonnes = norm_mass / 1_000_000.0
        else:
            try:
                from .units import convert
                norm_tonnes = convert(norm_mass, mass_unit, "tonne")
            except Exception:
                norm_tonnes = norm_mass

        # Emission factor EF_N2O in kg N2O / tonne product
        if ef_n2o is not None and float(ef_n2o) > 0:
            ef = float(ef_n2o)
        else:
            # Default factors per API Compendium 2021 Section 6, pg 407
            if "adipic" in str(process_type).lower():
                ef = 300.0  # uncontrolled adipic acid default kg N2O/t
            else:
                ef = 9.0    # uncontrolled nitric acid default kg N2O/t

        # Abatement efficiency
        abatement_eff = float(abatement_efficiency or 0.0)
        if abatement_eff > 1.0:
            abatement_eff /= 100.0
        abatement_eff = max(0.0, min(1.0, abatement_eff))

        n2o_kg = norm_tonnes * ef * (1.0 - abatement_eff)
        n2o_tonnes = n2o_kg / 1000.0

        uncertainties = uncertainties or {}
        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        n2o_res = propagate_uncertainty(
            n2o_tonnes,
            resolve_ef_uncertainty(
                "chemical_production", "n2o", _tier, uncertainties.get("n2o", 0.15)
            ),
            tier=_tier,
            process_category="chemical_production",
            gas="n2o",
        )
        total_co2e = calculate_co2e(co2=0.0, ch4=0.0, n2o=n2o_tonnes, gwp_dict=gwp_dict)

        return self.format_result(
            co2=0.0,
            ch4=0.0,
            n2o=n2o_res,
            total_co2e=total_co2e,
            inputs={
                "production_amount": production_amount,
                "ef_n2o": ef,
                "abatement_efficiency": abatement_eff,
                "unit": mass_unit,
            },
        )

