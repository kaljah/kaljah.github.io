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
    METHOD21_CH4_WT_DEFAULT,
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
DENSITY_CH4 = MW_CH4 / MOLAR_VOL_SI  # kg / Sm³ at 60°F, 14.696 psia (0.6772)
DENSITY_CO2 = MW_CO2 / MOLAR_VOL_SI  # kg / Sm³ at 60°F, 14.696 psia (1.8581)


# measured leak rates: volumetric units are WHOLE GAS at standard conditions (scaled by the gas
# mole fractions); mass units are CH4 mass (a whole-gas mass cannot be speciated from mole % alone)
_VOL_M3_PER_HR = {"scf/hr": 0.028316846592, "scfh": 0.028316846592, "scf/h": 0.028316846592,
                  "scf/day": 0.028316846592 / 24.0, "scfd": 0.028316846592 / 24.0,
                  "m3/hr": 1.0, "m3/h": 1.0, "sm3/hr": 1.0, "m3/day": 1 / 24.0, "m3/d": 1 / 24.0,
                  "l/min": 0.06, "lpm": 0.06}
_MASS_KG_PER_HR = {"kg/hr": 1.0, "kg/h": 1.0, "kg/hour": 1.0, "lb/hr": 0.45359237, "lb/h": 0.45359237,
                   "g/s": 3.6, "gps": 3.6, "tonne/yr": 1000.0 / 8760.0, "tonnes/yr": 1000.0 / 8760.0,
                   "t/yr": 1000.0 / 8760.0, "tpy": 1000.0 / 8760.0}


def _rate_tables_extend():
    """S1K-F16: every volume-rate spelling of the shared parser (Mcf/day, scf/hr, Nm3/h ...) and mass
    rates per hour / day (g/hr, kg/day ...)."""
    from .units import MASS_UNITS_TO_KG, TIME_UNITS_TO_HOURS
    for m, kg in MASS_UNITS_TO_KG.items():
        for t, h in TIME_UNITS_TO_HOURS.items():
            if t in ("hr", "h", "hour", "day", "d", "s", "sec", "min", "yr", "year"):
                _MASS_KG_PER_HR.setdefault(f"{m}/{t}", kg / h)


_rate_tables_extend()


def convert_fugitive_flow_to_kg_hr(value: float, unit: str, ch4_mol: float = None, co2_mol: float = None) -> dict:
    """Measured leak rate -> kg/hr of CH4 and CO2.

    scf/hr, m3/hr ... : whole gas; CH4 = V x y_CH4 x rho_CH4, CO2 = V x y_CO2 x rho_CO2 (y_CH4 required)
    kg/hr, lb/hr ...  : CH4 mass; CO2 = CH4 x (y_CO2 / y_CH4) x (44.01 / 16.04) when both are given
    """
    u = str(unit or "").strip().lower().replace(" ch4", "").replace("ch4", "").strip()
    val = float(value)
    y_co2 = float(co2_mol or 0.0)
    if u in _VOL_M3_PER_HR:
        if ch4_mol in (None, ""):
            raise ValueError("A volumetric leak rate needs the gas CH4 content (mol %)")
        m3_hr = val * _VOL_M3_PER_HR[u]
        return {"ch4_kg_hr": m3_hr * float(ch4_mol) * DENSITY_CH4, "co2_kg_hr": m3_hr * y_co2 * DENSITY_CO2}
    if u in _MASS_KG_PER_HR:
        ch4_kg = val * _MASS_KG_PER_HR[u]
        co2_kg = ch4_kg * (y_co2 / float(ch4_mol)) * (MW_CO2 / MW_CH4) if (y_co2 and ch4_mol) else 0.0
        return {"ch4_kg_hr": ch4_kg, "co2_kg_hr": co2_kg}
    from .units import UnitError, volume_rate_m3_per_hour
    try:   # any other volume-rate spelling ("Mcf/day", "Nm3/h", "scfm") through the shared parser
        m3_hr = val * volume_rate_m3_per_hour(u)
    except UnitError:
        raise ValueError(f"Unknown leak rate unit '{unit}'")
    if ch4_mol in (None, ""):
        raise ValueError("A volumetric leak rate needs the gas CH4 content (mol %)")
    return {"ch4_kg_hr": m3_hr * float(ch4_mol) * DENSITY_CH4, "co2_kg_hr": m3_hr * y_co2 * DENSITY_CO2}


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
        ch4_wt_fraction: float = None,
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
        if not _is_ch4:
            # a TOC / whole-hydrocarbon mass factor is converted with the CH4 weight fraction
            # (API Compendium Eq 7-6); without one the CH4 share is unknown, never assumed 100 %
            if ch4_wt_fraction in (None, ""):
                raise ValueError(f"Factor unit '{factor_unit}' is not CH4-specific: give the CH4 weight fraction")
            w = float(ch4_wt_fraction)
            w = w / 100.0 if w > 1.0 else w
            if not 0.0 <= w <= 1.0:
                raise ValueError("CH4 weight fraction must be between 0 and 100 %")
            kg_per_hr *= w
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
    Tier 2B: component-level average factors.
    A bare count uses API Compendium 2021 Table 7-12 (EPA protocol, by component and service): CH4 =
    count x converted CH4 factor x hours x (site CH4 mol % / 81.6 %), CO2 = count x whole-gas factor x
    hours x site CO2 mol %. A given factor is used as given: a CH4 factor directly, a TOC / hydrocarbon
    factor x the CH4 weight fraction (Eq 7-6; default Table C-1 for the service). No CO2 is derived
    from a TOC mass (TOC contains no CO2).
    """
    def __init__(self):
        super().__init__("Onshore Component-Level Fugitives", "Section 7.2.2")

    def calculate(
        self,
        component_counts: dict,
        service_type: str = "Gas",
        operating_hours: float = 8760.0,
        ch4_content: float = None,
        co2_content: float = None,
        uncertainties: dict = None,
        gwp_dict: dict = None,
        ch4_wt_fraction: float = None,
    ) -> dict:
        self.validate_inputs(
            {"component_counts": component_counts, "operating_hours": operating_hours},
            ["component_counts", "operating_hours"],
        )
        if operating_hours < 0 or operating_hours > 8784:
            raise ValueError(f"Operating hours ({operating_hours}) must be between 0 and 8,784 hours/year")
        from emission_factors_chapter7_onshore import COMPONENT_FACTORS_T7_12
        from .units import per_source_hour_kg

        uncertainties = uncertainties or {}
        sv = str(service_type or "gas").strip().lower().replace("/", "_").replace(" ", "_")
        service_key = ("light_oil" if "light" in sv else "heavy_oil" if "heavy" in sv
                       else "water_oil" if "water" in sv else "gas")
        service_norm = {"gas": "Gas", "light_oil": "Light Oil", "heavy_oil": "Heavy Oil", "water_oil": "Water/Oil"}[service_key]

        def _frac(v):
            if v in (None, ""):
                return None
            x = float(v)
            x = x / 100.0 if x > 1.0 else x
            if not 0.0 <= x <= 1.0:
                raise ValueError("Gas content must be between 0 and 100 %")
            return x

        y_ch4, y_co2, w_ch4 = _frac(ch4_content), _frac(co2_content), _frac(ch4_wt_fraction)
        aliases = {"valves": "valve", "connectors": "connector", "flanges": "flange", "oel": "open_ended_line",
                   "open-ended_line": "open_ended_line", "pump": "pump_seal", "pump_seals": "pump_seal",
                   "others": "other", "prv": "other"}

        total_ch4_kg_hr = 0.0
        total_co2_kg_hr = 0.0
        component_breakdown = []
        tables = set()
        for comp_name, data in component_counts.items():
            if isinstance(data, dict):
                count = float(data.get("count", 0))
                ef = float(data.get("ef", 0) or 0)
                ef_unit = str(data.get("unit") or data.get("ef_unit") or "kg TOC/hr/component")
            else:
                count, ef, ef_unit = float(data or 0), 0.0, None
            if count < 0:
                raise ValueError(f"Component count for '{comp_name}' cannot be negative ({count})")

            if ef > 0:
                ef_kg_hr, is_ch4 = per_source_hour_kg(ef, ef_unit)  # BUG-048
                if is_ch4:
                    ch4_kg_hr = count * ef_kg_hr
                else:
                    w = w_ch4 if w_ch4 is not None else METHOD21_CH4_WT_DEFAULT.get(service_key)
                    if w is None:
                        raise ValueError(f"Give the CH4 weight fraction of TOC for '{service_norm}' service")
                    ch4_kg_hr = count * ef_kg_hr * w
                co2_kg_hr = 0.0
                source = "given factor"
            else:
                comp = str(comp_name or "").strip().lower().replace(" ", "_")
                comp = aliases.get(comp, comp)
                row = COMPONENT_FACTORS_T7_12.get(f"{comp}_{service_key}")
                if row is None:
                    if count > 0:
                        # never a silent zero (BUG-015 class)
                        raise ValueError(f"Table 7-12 has no factor for '{comp_name}' in {service_norm} service")
                    continue
                scale = (y_ch4 / row["ch4_basis"]) if y_ch4 is not None else 1.0
                ch4_kg_hr = count * row["ch4_t_hr"] * 1000.0 * scale
                co2_kg_hr = count * row["scf_hr"] * CONVERSIONS["scf_to_m3"] * (y_co2 or 0.0) * DENSITY_CO2
                ef, ef_unit, source = row["ch4_t_hr"], "tonne CH4/hr/component", row["table"]
                tables.add(row["table"])

            total_ch4_kg_hr += ch4_kg_hr
            total_co2_kg_hr += co2_kg_hr
            component_breakdown.append({"component": comp_name, "count": count, "ef": ef, "unit": ef_unit,
                                        "source": source, "ch4_kg_hr": ch4_kg_hr})
        c_ch4, c_co2 = y_ch4, y_co2

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
            "api_section": "Section 7.2.2",
            "api_table": ", ".join(sorted(tables)) or "given factor",
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
        ch4_content: float = None,
        uncertainties: dict = None,
        gwp_dict: dict = None,
    ) -> dict:
        """Screening ranges (Table 7-26): counts below / at or above 10,000 ppmv x TOC factor x CH4 wt
        fraction of TOC (default Table C-1 for the service) x hours."""
        comp = str(component_type or "").strip().lower().replace(" ", "_").replace("-", "_")
        comp = {"valves": "valve", "pump": "pump_seal", "pump_seals": "pump_seal", "connectors": "connector",
                "flanges": "flange", "oel": "open_ended_line", "others": "other", "prv": "other"}.get(comp, comp)
        serv = str(service_type or "gas").strip().lower().replace(" ", "_").replace("/", "_")
        key = f"{comp}_{serv}"
        meta = METHOD21_SCREENING_RANGES.get(key)
        if meta is None:
            raise ValueError(f"Table 7-26 has no screening factor for '{component_type}' in '{service_type}' service")
        n_low, n_high = float(non_pegged_count or 0), float(pegged_count or 0)
        if n_low < 0 or n_high < 0:
            raise ValueError("Component counts cannot be negative")
        if n_low + n_high == 0:
            raise ValueError("Enter the number of components below and / or at or above 10,000 ppmv")
        if n_high and meta["pegged_10k_ef"] is None:
            raise ValueError(f"Table 7-26 has no >= 10,000 ppmv factor for '{component_type}' in '{service_type}' service")
        if ch4_content in (None, ""):
            w = METHOD21_CH4_WT_DEFAULT.get(serv)
            if w is None:
                raise ValueError(f"Enter the CH4 weight fraction of TOC for '{service_type}' service")
        else:
            w = float(ch4_content)
            w = w / 100.0 if w > 1.0 else w
        if not 0.0 <= w <= 1.0:
            raise ValueError("CH4 weight fraction must be between 0 and 100 %")
        hours = float(operating_hours)
        if hours < 0:
            raise ValueError("Operating hours cannot be negative")

        toc_kg_hr = n_low * meta["non_pegged_ef"] + n_high * (meta["pegged_10k_ef"] or 0.0)
        total_ch4_tonnes = toc_kg_hr * w * hours / 1000.0
        total_co2e = calculate_co2e(co2=0.0, ch4=total_ch4_tonnes, gwp_dict=gwp_dict)
        ch4_res = propagate_uncertainty(total_ch4_tonnes, 0.15, tier="Tier 3", process_category="fugitive_screening", gas="ch4")
        return {
            "results": {"ch4": ch4_res, "co2": 0.0, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": {
                "api_table": meta["table"],
                "methodology": "Tier 3A: screening ranges",
                "counts": {"below_10k": n_low, "at_or_above_10k": n_high},
                "factors_kg_toc_hr": {"below_10k": meta["non_pegged_ef"], "at_or_above_10k": meta["pegged_10k_ef"]},
                "ch4_wt_fraction": w,
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
        total_surveyed: int = None,
        leakers_detected: int = 0,
        operating_hours: float = 8760.0,
        uncertainties: dict = None,
        gwp_dict: dict = None,
        ch4_mol: float = None,
        co2_mol: float = None,
    ) -> dict:
        """Leaker survey (Table 7-23): leakers x whole-gas factor (scf/h) x hours x site CH4 / CO2.

        The table has leaker factors only; without a site CH4 content its 81.6 mol % basis applies.
        """
        leakers = float(leakers_detected or 0)
        if leakers < 0 or leakers != int(leakers):
            raise ValueError("Detected leakers must be a whole number, zero or more")
        if total_surveyed not in (None, "") and leakers > float(total_surveyed):
            raise ValueError(f"Detected leakers ({int(leakers)}) cannot exceed total surveyed ({total_surveyed})")
        comp = str(component_type or "").strip().lower().replace(" ", "_").replace("-", "_")
        comp = {"valves": "valve", "flanges": "flange", "connectors": "connector", "oel": "open_ended_line",
                "pressure_relief_valve": "prv", "pump": "pump_seal", "pump_seals": "pump_seal",
                "others": "other"}.get(comp, comp)
        serv = str(service_type or "gas").strip().lower().replace(" ", "_")
        serv = {"light_oil": "light_crude", "heavy_oil": "heavy_crude"}.get(serv, serv)
        meta = OGI_LEAKER_FACTORS.get(f"{comp}_{serv}")
        if meta is None:
            raise ValueError(f"Table 7-23 has no leaker factor for '{component_type}' in '{service_type}' service")
        hours = float(operating_hours)
        if hours < 0:
            raise ValueError("Operating hours cannot be negative")
        y_ch4 = meta["ch4_basis"] if ch4_mol in (None, "") else float(ch4_mol)
        y_co2 = float(co2_mol or 0.0)
        gas_m3 = leakers * meta["whole_gas_scf_hr"] * hours * CONVERSIONS["scf_to_m3"]
        ch4_t = gas_m3 * y_ch4 * DENSITY_CH4 / 1000.0
        co2_t = gas_m3 * y_co2 * DENSITY_CO2 / 1000.0
        total_co2e = calculate_co2e(co2=co2_t, ch4=ch4_t, gwp_dict=gwp_dict)
        ch4_res = propagate_uncertainty(ch4_t, 0.15, tier="Tier 3", process_category="fugitive_ogi", gas="ch4")
        co2_res = propagate_uncertainty(co2_t, 0.15, tier="Tier 3", process_category="fugitive_ogi", gas="co2") if co2_t else 0.0
        return {
            "results": {"ch4": ch4_res, "co2": co2_res, "n2o": 0.0},
            "total_co2e": total_co2e,
            "intermediate": {
                "api_table": meta["table"],
                "methodology": "Tier 3C: leaker survey",
                "detected_leakers": int(leakers),
                "whole_gas_scf_hr_per_leaker": meta["whole_gas_scf_hr"],
                "ch4_mol_fraction": y_ch4,
                "total_ch4_tonnes": ch4_t,
            },
        }

    def calculate_direct_measurement(
        self,
        measured_rate: float,
        measurement_unit: str = "kg/hr",
        operating_hours: float = 8760.0,
        ch4_mol: float = None,
        co2_mol: float = None,
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
