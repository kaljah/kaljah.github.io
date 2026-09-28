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


# API Compendium 2021 Table 7-8 - facility-level average equipment leak factors for onshore
# production, per unit of production (tonnes CH4). Gas factors are on a 78.8 mol % CH4 basis.
TABLE_7_8 = {
    "oil_production": {"bbl": 2.346e-04, "m3": 1.476e-03, "basis": None,
                       "name": "Facility - Onshore Oil Production (Table 7-8)"},
    "gas_production": {"mmscf": 2.601e-02, "mm_m3": 9.184e-01, "basis": 0.788,
                       "name": "Facility - Onshore Gas Production (Table 7-8)"},
}
FACILITY_TYPE_KEYS = {k: v["name"] for k, v in TABLE_7_8.items()}


class OnshoreFacilityFugitiveCalculator(BaseCalculator):
    """
    Tier 1: facility-level average factors on production throughput.
    Governing Standard: API Compendium 2021 section 7.2.2.1, Table 7-8 (Equation 7-7).
    """

    def __init__(self):
        super().__init__("Onshore Facility-Level Fugitives", "Section 7.2.2.1")

    @staticmethod
    def _production_in_table_unit(ftype, production, unit):
        from .units import norm_unit

        u = norm_unit(unit or "")
        if ftype == "oil_production":
            if u in ("bbl", "bbls", "barrel", "barrels"):
                return float(production), "bbl"
            if u in ("m3", "sm3"):
                return float(production), "m3"
            raise ValueError(f"Oil production must be in bbl or m3 (got '{unit}')")
        scale = {"scf": 1e-6, "mscf": 1e-3, "mcf": 1e-3, "mmscf": 1.0, "bcf": 1e3}
        if u in scale:
            return float(production) * scale[u], "mmscf"
        if u in ("m3", "sm3"):
            return float(production) * 1e-6, "mm_m3"
        if u in ("mm3", "mmm3", "10^6m3", "e6m3"):
            return float(production), "mm_m3"
        raise ValueError(f"Gas production must be in scf / Mcf / MMscf or m3 (got '{unit}')")

    def calculate(
        self,
        production: float,
        production_unit: str,
        facility_type: str,
        ch4_content: float = None,
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        ftype = str(facility_type or "").strip().lower()
        if ftype not in TABLE_7_8:
            by_name = {v["name"].lower(): k for k, v in TABLE_7_8.items()}
            ftype = by_name.get(ftype, ftype)
        if ftype not in TABLE_7_8:
            raise ValueError(
                f"Unknown facility type '{facility_type}' for facility-level fugitives; use oil_production "
                f"or gas_production (API Compendium 2021 Table 7-8, per unit of production)"
            )
        self.validate_inputs({"production": production}, ["production"])
        if float(production) < 0:
            raise ValueError("Production cannot be negative")
        uncertainties = uncertainties or {}
        row = TABLE_7_8[ftype]
        qty, tunit = self._production_in_table_unit(ftype, production, production_unit)
        ef = row[tunit]
        scale = 1.0
        if ch4_content not in (None, "") and row["basis"]:
            c = float(ch4_content)
            c = c / 100.0 if c > 1.0 else c
            scale = c / row["basis"]
        total_ch4 = qty * ef * scale

        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        u_ef = 0.955 if ftype == "oil_production" else 0.529  # Table 7-8, 95 % half-widths
        ch4_res = propagate_uncertainty(
            total_ch4,
            resolve_ef_uncertainty("fugitive_facility", "ch4", _tier, uncertainties.get("ch4", u_ef)),
            tier=_tier, process_category="fugitive_facility", gas="ch4",
        )
        co2_res = propagate_uncertainty(0.0, 0.0, tier=_tier, process_category="fugitive_facility", gas="co2")
        total_co2e = calculate_co2e(co2=0.0, ch4=total_ch4, gwp_dict=gwp_dict)
        return {
            "results": {"ch4": ch4_res, "co2": co2_res, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": {
                "api_section": "Section 7.2.2.1",
                "api_table": "Table 7-8",
                "methodology": "Tier 1: Facility-Level Average Factor (production basis)",
                "activity_inputs": {"production": production, "production_unit": production_unit,
                                    "facility_type": ftype},
                "factor_used": {"factor_value": ef, "factor_unit": f"tonne CH4/{tunit}", "ch4_scale": scale},
                "math_trace": f"{qty:g} {tunit} x {ef:g} t CH4/{tunit} x {scale:.4f} = {total_ch4:.5f} t CH4",
                "co2e_total": total_co2e,
            },
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
        if ef_val <= 0:
            # never a silent zero (BUG-015 class): the equipment factor comes from the catalog
            # (Tables 7-9 / 7-10 / 7-29) or a custom factor
            raise ValueError(f"No equipment-level emission factor for '{equipment_type}'; select a catalog "
                             "equipment factor (API 2021 Tables 7-9 / 7-10 / 7-29) or a custom factor")
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
            if count > 0 and not (float(ef or 0) > 0):
                # never a silent zero (BUG-015 class)
                raise ValueError(f"No component-level emission factor for '{comp_name}'; give its factor and "
                                 "unit (catalog component factor or a custom factor)")

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
        service_type: str = None,
        screening_values_ppm: list = None,
        operating_hours: float = 8760.0,
        ch4_content: float = None,
        uncertainties: dict = None,
        gwp_dict: dict = None,
        zero_count: int = 0,
        pegged_10k_count: int = 0,
        pegged_100k_count: int = 0,
    ) -> dict:
        """Correlation approach (Tables 7-40 / 7-41 / 7-42, Exhibit 7-5).

        Non-detects use the default-zero rate, screened values the correlation a*(SV)^b, and
        components pegging the instrument the 10,000 or 100,000 ppmv pegged rate. ch4_content is
        the CH4 weight fraction of TOC (default 0.564, Table C-1).
        """
        from emission_factors_api2021 import CORRELATION_ALIASES, CORRELATION_EQUATIONS
        key = str(component_type or "").strip().lower().replace(" ", "_").replace("-", "_")
        key = CORRELATION_ALIASES.get(key, key)
        corr = CORRELATION_EQUATIONS.get(key)
        if corr is None:
            raise ValueError(
                f"Unknown correlation component '{component_type}'. Use one of: {', '.join(CORRELATION_EQUATIONS)}"
            )
        a, b = corr["A"], corr["B"]

        def _count(v, name):
            n = float(v or 0)
            if n < 0 or n != int(n):
                raise ValueError(f"{name} must be a whole number of components, zero or more")
            return int(n)

        n_zero = _count(zero_count, "Non-detect count")
        n_p10 = _count(pegged_10k_count, "Pegged (10,000 ppmv) count")
        n_p100 = _count(pegged_100k_count, "Pegged (100,000 ppmv) count")

        toc_zero = n_zero * corr["default_zero"]
        toc_corr = 0.0
        n_corr = 0
        for ppm in screening_values_ppm or []:
            p_val = float(ppm)
            if p_val < 0:
                raise ValueError("Screening concentration cannot be negative")
            if p_val == 0:
                toc_zero += corr["default_zero"]
                n_zero += 1
            else:
                toc_corr += a * (p_val ** b)
                n_corr += 1
        toc_pegged = n_p10 * corr["pegged_10k"] + n_p100 * corr["pegged_100k"]
        if n_zero + n_corr + n_p10 + n_p100 == 0:
            raise ValueError("Enter at least one screened component")

        c_ch4 = 0.564 if ch4_content in (None, "") else float(ch4_content)
        if c_ch4 > 1.0:
            c_ch4 /= 100.0
        if not 0.0 <= c_ch4 <= 1.0:
            raise ValueError("CH4 weight fraction must be between 0 and 100 %")
        hours = float(operating_hours)
        if hours < 0:
            raise ValueError("Operating hours cannot be negative")

        total_toc_kg_hr = toc_zero + toc_corr + toc_pegged
        total_ch4_tonnes = total_toc_kg_hr * c_ch4 * hours / 1000.0
        total_co2e = calculate_co2e(co2=0.0, ch4=total_ch4_tonnes, gwp_dict=gwp_dict)
        ch4_res = propagate_uncertainty(total_ch4_tonnes, 0.15, tier="Tier 3", process_category="fugitive_screening", gas="ch4")

        return {
            "results": {"ch4": ch4_res, "co2": 0.0, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": {
                "api_table": "Tables 7-40 / 7-41 / 7-42",
                "methodology": "Tier 3B: correlation approach",
                "component": key,
                "screening_count": n_zero + n_corr + n_p10 + n_p100,
                "toc_default_zero_kg_hr": toc_zero,
                "toc_correlation_kg_hr": toc_corr,
                "toc_pegged_kg_hr": toc_pegged,
                "total_toc_kg_hr": total_toc_kg_hr,
                "ch4_wt_fraction": c_ch4,
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
