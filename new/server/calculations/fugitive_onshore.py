"""
API GHG Compendium 2021 - Chapter 7: Equipment Leaks / Fugitive Emissions
ONSHORE OIL & NATURAL GAS OPERATIONS ONLY

Calculation Architecture:
- Tier 1: Facility-Level Average Factors (§7.2.2, Table 7-1 & Table 7-2)
- Tier 2A: Equipment-Level Population Factors (§7.2.2 & §7.2.3, Table 7-9, Table 7-10, Table 7-29)
- Tier 2B: Component-Level Population Factors (§7.2.2 & §7.2.3, Table 7-11, Table 7-30)
- Tier 3: Screening & Measurement Methodologies:
  - 3A: Method 21 Screening Ranges (Table 7-15 & Table 7-16)
  - 3B: Method 21 Correlation Equations (Table 7-17 & Table 7-18)
  - 3C: Optical Gas Imaging (OGI) Leaker Survey (Table 7-19, Table 7-20, Subpart W Table W-1E)
  - 3D: Direct Measurement (Hi-Flow Sampler, Calibrated Bagging, Flow Meter)
"""

import math
from .base import BaseCalculator
from .units import (
    CONVERSIONS,
    calculate_co2e,
    convert,
    STD_PRESSURE_PSIA,
    STD_TEMP_K,
    TIME_UNITS_TO_HOURS,
)
from .uncertainty import (
    propagate_uncertainty,
    resolve_tier,
    resolve_ef_uncertainty,
)
from .constants import DEFAULT_GWP, get_active_gwp
from emission_factors_chapter7_onshore import (
    API_CHAPTER7_ONSHORE_FACTORS,
    METHOD21_SCREENING_RANGES,
    OGI_LEAKER_FACTORS,
    DEFAULT_SERVICE_COMPOSITIONS,
)

# Standard Thermodynamic Constants (60°F / 14.696 psia)
MOLAR_VOL_US = 379.3   # scf / lb-mole
MOLAR_VOL_SI = 23.685  # Sm³ / kg-mole
MW_CH4 = 16.04
MW_CO2 = 44.01
DENSITY_CH4 = 0.6785  # kg / Sm³ at 60°F, 14.696 psia
DENSITY_CO2 = 1.861   # kg / Sm³ at 60°F, 14.696 psia


def convert_fugitive_flow_to_kg_hr(value: float, unit: str, ch4_mol: float = 0.85, co2_mol: float = 0.01) -> dict:
    """
    Converts measured flow rate to kg/hr for CH4 and CO2.
    Explicit conversion with no hidden constants.
    """
    u = str(unit or "kg/hr").strip().lower()
    val = float(value)

    if u in ["kg/hr", "kg/h", "kg/hour"]:
        ch4_kg = val * ch4_mol
        co2_kg = val * co2_mol * (MW_CO2 / MW_CH4)
    elif u in ["tonne/yr", "tonnes/yr", "t/yr", "tpy"]:
        total_kg_hr = (val * 1000.0) / 8760.0
        ch4_kg = total_kg_hr * ch4_mol
        co2_kg = total_kg_hr * co2_mol * (MW_CO2 / MW_CH4)
    elif u in ["scf/hr", "scfh", "scf/h"]:
        # Volume flow: scf/hr -> Sm3/hr -> mass via density
        m3_hr = val * CONVERSIONS["scf_to_m3"]
        ch4_kg = m3_hr * ch4_mol * DENSITY_CH4
        co2_kg = m3_hr * co2_mol * DENSITY_CO2
    elif u in ["scf/day", "scfd"]:
        scf_hr = val / 24.0
        m3_hr = scf_hr * CONVERSIONS["scf_to_m3"]
        ch4_kg = m3_hr * ch4_mol * DENSITY_CH4
        co2_kg = m3_hr * co2_mol * DENSITY_CO2
    elif u in ["m3/hr", "m3/h", "sm3/hr"]:
        ch4_kg = val * ch4_mol * DENSITY_CH4
        co2_kg = val * co2_mol * DENSITY_CO2
    elif u in ["m3/day", "m3/d"]:
        m3_hr = val / 24.0
        ch4_kg = m3_hr * ch4_mol * DENSITY_CH4
        co2_kg = m3_hr * co2_mol * DENSITY_CO2
    elif u in ["l/min", "lpm"]:
        m3_hr = (val * 60.0) / 1000.0
        ch4_kg = m3_hr * ch4_mol * DENSITY_CH4
        co2_kg = m3_hr * co2_mol * DENSITY_CO2
    elif u in ["g/s", "gps"]:
        kg_hr = (val * 3600.0) / 1000.0
        ch4_kg = kg_hr * ch4_mol
        co2_kg = kg_hr * co2_mol * (MW_CO2 / MW_CH4)
    elif u in ["lb/hr", "lb/h"]:
        kg_hr = val * CONVERSIONS["lb_to_kg"]
        ch4_kg = kg_hr * ch4_mol
        co2_kg = kg_hr * co2_mol * (MW_CO2 / MW_CH4)
    else:
        # Default fallback assume kg/hr
        ch4_kg = val * ch4_mol
        co2_kg = val * co2_mol

    return {"ch4_kg_hr": ch4_kg, "co2_kg_hr": co2_kg}


# Facility-type ids used by the Scope 1 form and the API (Table 7-1 gas / Table 7-2 oil)
FACILITY_TYPE_KEYS = {
    "gas_pad_nodehy": "Facility - Gas Well Pad / Battery (Without Dehydrator)",
    "gas_pad_dehy": "Facility - Gas Well Pad / Battery (With Dehydrator)",
    "central_gas": "Facility - Central Gas Production Facility",
    "oil_pad_light": "Facility - Oil Well Pad / Battery (Light Crude)",
    "oil_pad_heavy": "Facility - Oil Well Pad / Battery (Heavy Crude)",
    "central_oil": "Facility - Central Oil Treatment / Battery",
}


class OnshoreFacilityFugitiveCalculator(BaseCalculator):
    """
    Tier 1: Facility-Level Average Factors
    Governing Standard: API Compendium 2021 §7.2.2, Table 7-1 (Gas) & Table 7-2 (Oil)
    """
    def __init__(self):
        super().__init__("Onshore Facility-Level Fugitives", "Section 7.2.2")

    def calculate(
        self,
        facility_count: float,
        facility_type: str,
        operating_days: float = 365.25,
        factor_id: str = None,
        custom_ef: float = None,
        ef_unit: str = "tonne CH4/facility/day",
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        self.validate_inputs(
            {"facility_count": facility_count, "operating_days": operating_days},
            ["facility_count", "operating_days"],
        )
        if facility_count < 0:
            raise ValueError("Facility count cannot be negative")
        if operating_days < 0 or operating_days > 366:
            raise ValueError(f"Operating days ({operating_days}) must be between 0 and 366 days/year")

        uncertainties = uncertainties or {}

        # Resolve factor
        ef_val = 0.0
        table_ref = "Table 7-1 / Table 7-2"
        f_type_clean = str(facility_type or "").lower()

        if custom_ef is not None:
            ef_val = float(custom_ef)
            table_ref = "Custom Facility Factor"
        else:
            # BUG-110: exact facility-type keys only; an unknown type is an error, never a silent
            # fallback to the light-crude well pad factor
            key = FACILITY_TYPE_KEYS.get(f_type_clean.strip())
            if key is None:
                key = next((k for k in FACILITY_TYPE_KEYS.values() if k.lower() == f_type_clean.strip()), None)
            if key is None:
                raise ValueError(
                    f"Unknown facility type '{facility_type}' for facility-level fugitives; "
                    f"use one of: {', '.join(sorted(FACILITY_TYPE_KEYS))}"
                )
            factor_meta = API_CHAPTER7_ONSHORE_FACTORS[key]

            ef_val = factor_meta["factor_value"]
            table_ref = factor_meta["API_table"]
            ef_unit = factor_meta["factor_unit"]

        # Calculation: Count * EF * Operating Days
        total_ch4_tonnes = float(facility_count) * ef_val * float(operating_days)
        total_co2_tonnes = 0.0  # Facility-level API factors are pure CH4

        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        ch4_res = propagate_uncertainty(
            total_ch4_tonnes,
            resolve_ef_uncertainty("fugitive_facility", "ch4", _tier, uncertainties.get("ch4", 0.50)),
            tier=_tier,
            process_category="fugitive_facility",
            gas="ch4",
        )
        co2_res = propagate_uncertainty(0.0, 0.0, tier=_tier, process_category="fugitive_facility", gas="co2")
        total_co2e = calculate_co2e(co2=0.0, ch4=total_ch4_tonnes, gwp_dict=gwp_dict)

        audit_trace = {
            "api_section": "Section 7.2.2",
            "api_table": table_ref,
            "methodology": "Tier 1: Facility-Level Average Factor",
            "activity_inputs": {
                "facility_count": facility_count,
                "operating_days": operating_days,
                "facility_type": facility_type,
            },
            "factor_used": {
                "factor_value": ef_val,
                "factor_unit": ef_unit,
                "time_basis": "daily",
            },
            "math_trace": f"{facility_count} facilities * {ef_val} {ef_unit} * {operating_days} days = {total_ch4_tonnes:.5f} tonnes CH4/yr",
            "co2e_total": total_co2e,
        }

        return {
            "results": {"ch4": ch4_res, "co2": co2_res, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": audit_trace,
        }


class OnshoreEquipmentFugitiveCalculator(BaseCalculator):
    """
    Tier 2A: Equipment-Level Population Factors
    Governing Standard: API Compendium 2021 §7.2.2 (Tables 7-9 & 7-10) and §7.2.3 (Table 7-29)
    """
    def __init__(self):
        super().__init__("Onshore Equipment-Level Fugitives", "Section 7.2.2 & 7.2.3")

    def calculate(
        self,
        equipment_count: float,
        equipment_type: str,
        service_type: str = "Gas",
        operating_hours: float = 8760.0,
        factor_value: float = None,
        factor_unit: str = "tonne CH4/well/hr",
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        self.validate_inputs(
            {"count": equipment_count, "hours": operating_hours},
            ["count", "hours"],
        )
        if equipment_count < 0:
            raise ValueError("Equipment count cannot be negative")
        if operating_hours < 0 or operating_hours > 8784:
            raise ValueError(f"Operating hours ({operating_hours}) must be between 0 and 8,784 hours/year")

        uncertainties = uncertainties or {}

        # Resolve factor through the canonical unit parser (BUG-048: "CH₄" subscripts,
        # tonne vs kg numerators and annual vs hourly bases are all read from the unit itself)
        from .units import per_source_hour_kg

        ef_val = float(factor_value or 0.0)
        kg_per_hr, _is_ch4 = per_source_hour_kg(ef_val, factor_unit or "tonne CH4/well/hr")
        total_ch4 = float(equipment_count) * kg_per_hr * float(operating_hours) / 1000.0
        kg_per_source_hour = kg_per_hr  # audit trace

        total_co2 = 0.0  # Equipment factors are pure CH4

        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        ch4_res = propagate_uncertainty(
            total_ch4,
            resolve_ef_uncertainty("equipment_fugitive", "ch4", _tier, uncertainties.get("ch4", 0.30)),
            tier=_tier,
            process_category="equipment_fugitive",
            gas="ch4",
        )
        co2_res = propagate_uncertainty(0.0, 0.0, tier=_tier, process_category="equipment_fugitive", gas="co2")
        total_co2e = calculate_co2e(co2=0.0, ch4=total_ch4, gwp_dict=gwp_dict)

        audit_trace = {
            "api_section": "Section 7.2.2 / 7.2.3",
            "methodology": "Tier 2A: Equipment-Level Average Factor",
            "activity_inputs": {
                "equipment_count": equipment_count,
                "equipment_type": equipment_type,
                "service_type": service_type,
                "operating_hours": operating_hours,
            },
            "factor_used": {
                "factor_value": ef_val,
                "factor_unit": factor_unit,
                "kg_ch4_per_source_hour": kg_per_source_hour,
            },
            "math_trace": f"{equipment_count} units * {ef_val} {factor_unit} * {operating_hours} hrs = {total_ch4:.5f} tonnes CH4/yr",
            "co2e_total": total_co2e,
        }

        return {
            "results": {"ch4": ch4_res, "co2": co2_res, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": audit_trace,
        }


class OnshoreComponentFugitiveCalculator(BaseCalculator):
    """
    Tier 2B: Component-Level Population Factors
    Governing Standard: API Compendium 2021 §7.2.2, Table 7-11 (EPA 1995 Protocol) & §7.2.3 Table 7-30
    """
    def __init__(self):
        super().__init__("Onshore Component-Level Fugitives", "Section 7.2.2 & 7.2.3")

    def calculate(
        self,
        component_counts: dict,
        service_type: str = "Gas",
        operating_hours: float = 8760.0,
        ch4_content: float = None,
        co2_content: float = None,
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        self.validate_inputs(
            {"component_counts": component_counts, "operating_hours": operating_hours},
            ["component_counts", "operating_hours"],
        )
        if operating_hours < 0 or operating_hours > 8784:
            raise ValueError(f"Operating hours ({operating_hours}) must be between 0 and 8,784 hours/year")

        uncertainties = uncertainties or {}

        # Resolve gas/liquid stream composition
        service_clean = str(service_type or "Gas").strip().title()
        if "Light" in service_clean:
            service_norm = "Light Oil"
        elif "Heavy" in service_clean:
            service_norm = "Heavy Oil"
        elif "Water" in service_clean:
            service_norm = "Water/Oil"
        else:
            service_norm = "Gas"

        defaults = DEFAULT_SERVICE_COMPOSITIONS.get(service_norm, DEFAULT_SERVICE_COMPOSITIONS["Gas"])
        c_ch4 = float(ch4_content if ch4_content is not None else defaults["ch4_wt_in_toc"])
        if c_ch4 > 1.0:
            c_ch4 /= 100.0
        c_ch4 = max(0.0, min(1.0, c_ch4))

        c_co2 = float(co2_content if co2_content is not None else defaults.get("co2_mol", 0.01))
        if c_co2 > 1.0:
            c_co2 /= 100.0
        c_co2 = max(0.0, min(1.0, c_co2))

        total_ch4_kg_hr = 0.0
        total_co2_kg_hr = 0.0
        component_breakdown = []

        for comp_name, data in component_counts.items():
            if isinstance(data, dict):
                count = float(data.get("count", 0))
                ef = float(data.get("ef", 0))
                ef_unit = str(data.get("unit") or data.get("ef_unit") or "kg TOC/hr/component")
                from .units import per_source_hour_kg

                ef_kg_hr_parsed, is_direct_ch4 = per_source_hour_kg(ef, ef_unit)  # BUG-048
                is_tonne = False
            else:
                count = float(data or 0)
                ef = 0.0
                ef_unit = "kg/hr"
                is_direct_ch4 = False
                is_tonne = False

            if count < 0:
                raise ValueError(f"Component count for '{comp_name}' cannot be negative ({count})")

            # EF in kg TOC or kg CH4 per component-hour
            ef_kg_hr = ef_kg_hr_parsed if isinstance(data, dict) else ef

            if is_direct_ch4:
                comp_ch4_kg_hr = count * ef_kg_hr
                comp_co2_kg_hr = 0.0
            else:
                # TOC factor -> scale by CH4 weight fraction in TOC
                comp_ch4_kg_hr = count * ef_kg_hr * c_ch4
                comp_co2_kg_hr = count * ef_kg_hr * c_co2

            total_ch4_kg_hr += comp_ch4_kg_hr
            total_co2_kg_hr += comp_co2_kg_hr

            component_breakdown.append({
                "component": comp_name,
                "count": count,
                "ef": ef,
                "unit": ef_unit,
                "ch4_kg_hr": comp_ch4_kg_hr,
            })

        total_ch4_tonnes = (total_ch4_kg_hr * float(operating_hours)) / 1000.0
        total_co2_tonnes = (total_co2_kg_hr * float(operating_hours)) / 1000.0

        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        ch4_res = propagate_uncertainty(
            total_ch4_tonnes,
            resolve_ef_uncertainty("fugitive_component", "ch4", _tier, uncertainties.get("ch4", 0.30)),
            tier=_tier,
            process_category="fugitive_component",
            gas="ch4",
        )
        co2_res = propagate_uncertainty(
            total_co2_tonnes,
            resolve_ef_uncertainty("fugitive_component", "co2", _tier, uncertainties.get("co2", 0.20)),
            tier=_tier,
            process_category="fugitive_component",
            gas="co2",
        )
        total_co2e = calculate_co2e(co2=total_co2_tonnes, ch4=total_ch4_tonnes, gwp_dict=gwp_dict)

        audit_trace = {
            "api_section": "Section 7.2.2 / Table 7-11 & Section 7.2.3 / Table 7-30",
            "methodology": "Tier 2B: Component-Level Average Factor",
            "service_classification": service_norm,
            "speciation_used": {
                "ch4_fraction": c_ch4,
                "co2_fraction": c_co2,
            },
            "operating_hours": operating_hours,
            "component_breakdown": component_breakdown,
            "math_trace": f"Total CH4 rate {total_ch4_kg_hr:.6f} kg/hr * {operating_hours} hrs / 1000 = {total_ch4_tonnes:.5f} tonnes CH4/yr",
            "co2e_total": total_co2e,
        }

        return {
            "results": {"ch4": ch4_res, "co2": co2_res, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": audit_trace,
        }


class OnshoreScreeningMeasurementCalculator(BaseCalculator):
    """
    Tier 3: Screening & Measurement Methodologies
    Governing Standard: API Compendium 2021 §7.2.2 & §7.4
    - 3A: Method 21 Screening Ranges (Tables 7-15, 7-16)
    - 3B: Method 21 Correlation Equations (Tables 7-17, 7-18)
    - 3C: Optical Gas Imaging (OGI) Leaker Survey (Tables 7-19, 7-20 / Table W-1E)
    - 3D: Direct Measurement (Hi-Flow Sampler, Calibrated Bagging, Vent Meter)
    """
    def __init__(self):
        super().__init__("Onshore Screening & Measurement Fugitives", "Section 7.2.2 & 7.4")

    def calculate_method21_ranges(
        self,
        component_type: str,
        service_type: str,
        non_pegged_count: int,
        pegged_count: int,
        operating_hours: float = 8760.0,
        ch4_content: float = 0.85,
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        """Method 21 Screening Ranges (<10,000 ppmv vs >=10,000 ppmv pegged)."""
        key = f"{component_type.lower()}_{service_type.lower()}".replace(" ", "_")
        meta = METHOD21_SCREENING_RANGES.get(key, METHOD21_SCREENING_RANGES.get("valve_gas"))

        ef_non_pegged = meta["non_pegged_ef"]
        ef_pegged = meta["pegged_10k_ef"]

        c_ch4 = max(0.0, min(1.0, float(ch4_content or 0.85)))
        toc_kg_hr = (float(non_pegged_count) * ef_non_pegged) + (float(pegged_count) * ef_pegged)
        ch4_kg_hr = toc_kg_hr * c_ch4

        total_ch4_tonnes = (ch4_kg_hr * float(operating_hours)) / 1000.0
        total_co2e = calculate_co2e(co2=0.0, ch4=total_ch4_tonnes, gwp_dict=gwp_dict)

        _tier = "Tier 3"
        ch4_res = propagate_uncertainty(total_ch4_tonnes, 0.15, tier=_tier, process_category="fugitive_screening", gas="ch4")

        return {
            "results": {"ch4": ch4_res, "co2": 0.0, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": {
                "api_table": meta["table"],
                "methodology": "Tier 3A: Method 21 Screening Ranges",
                "counts": {"non_pegged_<10k": non_pegged_count, "pegged_>=10k": pegged_count},
                "factors_kg_hr": {"non_pegged": ef_non_pegged, "pegged": ef_pegged},
                "total_ch4_tonnes": total_ch4_tonnes,
            },
        }

    def calculate_correlation_equation(
        self,
        component_type: str,
        service_type: str,
        screening_values_ppm: list,
        operating_hours: float = 8760.0,
        ch4_content: float = 0.85,
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        """Method 21 Correlation Equations: Rate = a * (PPM)^b."""
        from emission_factors_api2021 import CORRELATION_EQUATIONS
        key = f"{service_type.lower()}_{component_type.lower()}".replace(" ", "_")
        corr = CORRELATION_EQUATIONS.get(key, CORRELATION_EQUATIONS.get("gas_valve"))

        a = corr["A"]
        b = corr["B"]
        pegged_default = corr.get("pegged_10k", 0.064)
        c_ch4 = max(0.0, min(1.0, float(ch4_content or 0.85)))

        total_toc_kg_hr = 0.0
        for ppm in screening_values_ppm:
            p_val = float(ppm)
            if p_val < 0:
                raise ValueError("Screening concentration cannot be negative")
            if p_val >= 10000.0:
                rate = pegged_default
            else:
                rate = a * (p_val ** b)
            total_toc_kg_hr += rate

        ch4_kg_hr = total_toc_kg_hr * c_ch4
        total_ch4_tonnes = (ch4_kg_hr * float(operating_hours)) / 1000.0
        total_co2e = calculate_co2e(co2=0.0, ch4=total_ch4_tonnes, gwp_dict=gwp_dict)

        _tier = "Tier 3"
        ch4_res = propagate_uncertainty(total_ch4_tonnes, 0.15, tier=_tier, process_category="fugitive_screening", gas="ch4")

        return {
            "results": {"ch4": ch4_res, "co2": 0.0, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": {
                "api_table": "Table 7-17 / Table 7-18",
                "methodology": "Tier 3B: Method 21 Correlation Equation",
                "equation": f"Rate (kg TOC/hr) = {a} * (PPM)^{b}",
                "screening_count": len(screening_values_ppm),
                "total_toc_kg_hr": total_toc_kg_hr,
                "total_ch4_tonnes": total_ch4_tonnes,
            },
        }

    def calculate_ogi_survey(
        self,
        component_type: str,
        service_type: str,
        total_surveyed: int,
        leakers_detected: int,
        operating_hours: float = 8760.0,
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        """Optical Gas Imaging (OGI) Leaker Method (§7.2.2, Table 7-19 / W-1E)."""
        if total_surveyed < 0:
            raise ValueError("Total surveyed components cannot be negative")
        if leakers_detected < 0:
            raise ValueError("Detected leakers cannot be negative")
        if leakers_detected > total_surveyed:
            raise ValueError(f"Detected leakers ({leakers_detected}) cannot exceed total surveyed ({total_surveyed})")

        key = f"{component_type.lower()}_{service_type.lower()}".replace(" ", "_")
        meta = OGI_LEAKER_FACTORS.get(key, OGI_LEAKER_FACTORS.get("valve_gas"))

        ef_leak = meta["leaker_ef"]
        ef_non_leak = meta["non_leaker_ef"]

        non_leakers = total_surveyed - leakers_detected
        ch4_kg_hr = (float(leakers_detected) * ef_leak) + (float(non_leakers) * ef_non_leak)

        total_ch4_tonnes = (ch4_kg_hr * float(operating_hours)) / 1000.0
        total_co2e = calculate_co2e(co2=0.0, ch4=total_ch4_tonnes, gwp_dict=gwp_dict)

        _tier = "Tier 3"
        ch4_res = propagate_uncertainty(total_ch4_tonnes, 0.15, tier=_tier, process_category="fugitive_ogi", gas="ch4")

        return {
            "results": {"ch4": ch4_res, "co2": 0.0, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": {
                "api_table": meta["table"],
                "methodology": "Tier 3C: OGI Leaker Survey",
                "surveyed_population": total_surveyed,
                "detected_leakers": leakers_detected,
                "non_leakers": non_leakers,
                "leaker_ef_kg_hr": ef_leak,
                "non_leaker_ef_kg_hr": ef_non_leak,
                "total_ch4_tonnes": total_ch4_tonnes,
            },
        }

    def calculate_direct_measurement(
        self,
        measured_rate: float,
        measurement_unit: str = "kg/hr",
        operating_hours: float = 8760.0,
        ch4_mol: float = 0.85,
        co2_mol: float = 0.01,
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        """Direct Measurement (Hi-Flow Sampler, Bagging, Vent Meter)."""
        if measured_rate < 0:
            raise ValueError("Measured flow rate cannot be negative")
        if operating_hours < 0 or operating_hours > 8784:
            raise ValueError(f"Operating hours ({operating_hours}) must be between 0 and 8,784 hours/year")

        rates = convert_fugitive_flow_to_kg_hr(measured_rate, measurement_unit, ch4_mol=ch4_mol, co2_mol=co2_mol)
        ch4_kg_hr = rates["ch4_kg_hr"]
        co2_kg_hr = rates["co2_kg_hr"]

        total_ch4_tonnes = (ch4_kg_hr * float(operating_hours)) / 1000.0
        total_co2_tonnes = (co2_kg_hr * float(operating_hours)) / 1000.0
        total_co2e = calculate_co2e(co2=total_co2_tonnes, ch4=total_ch4_tonnes, gwp_dict=gwp_dict)

        _tier = "Tier 3"
        ch4_res = propagate_uncertainty(total_ch4_tonnes, 0.05, tier=_tier, process_category="fugitive_measurement", gas="ch4")
        co2_res = propagate_uncertainty(total_co2_tonnes, 0.05, tier=_tier, process_category="fugitive_measurement", gas="co2")

        return {
            "results": {"ch4": ch4_res, "co2": co2_res, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": {
                "methodology": "Tier 3D: Direct Measurement",
                "measured_input": f"{measured_rate} {measurement_unit}",
                "operating_hours": operating_hours,
                "ch4_kg_hr": ch4_kg_hr,
                "co2_kg_hr": co2_kg_hr,
                "total_ch4_tonnes": total_ch4_tonnes,
                "total_co2_tonnes": total_co2_tonnes,
            },
        }
