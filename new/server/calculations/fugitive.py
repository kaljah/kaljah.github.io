"""
API Compendium 2021 - Section 7: Fugitive Emissions
Implementation of equations for component-level and equipment-level fugitives.
"""

from .base import BaseCalculator
from .units import calculate_co2e
from .uncertainty import propagate_uncertainty, resolve_tier, resolve_ef_uncertainty


class ComponentFugitiveCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Component-Level Fugitive", "Section 7.2")

    def calculate(self, component_counts, ch4_content, uncertainties, gwp_dict=None):
        """
        Average Factor Method - counts * EF
        component_counts: dict of {type: count}
        """
        self.validate_inputs({"counts": component_counts, "ch4_content": ch4_content}, ["counts", "ch4_content"])

        # Example factors (kg CH4 / hr / component) - simplified from Table 7-1
        # In real implementation, these would come from emission_factors.py

        DEFAULT_EFS = {
            "valve": 0.0045, "valves": 0.0045, "gas_valve": 0.0045, "light_liquid_valve": 0.0025,
            "connector": 0.0002, "connectors": 0.0002, "flange": 0.00039, "flanges": 0.00039,
            "open_ended_line": 0.002, "open_ended_lines": 0.002, "pump_seal": 0.013, "pump_seals": 0.013,
            "relief_valve": 0.0088, "relief_valves": 0.0088, "other": 0.0088, "others": 0.0088,
        }
        total_ch4_kg_hr = 0
        for comp_type, data in component_counts.items():
            k_norm = str(comp_type or "").strip().lower().replace("-", "_").replace(" ", "_")
            explicit_ef = isinstance(data, dict) and data.get("ef") not in (None, "")
            if k_norm not in DEFAULT_EFS and not explicit_ef:  # an unknown component took the gas-valve factor
                raise ValueError(f"Unknown component type '{comp_type}': {sorted(DEFAULT_EFS)} or give its factor")
            if isinstance(data, dict):
                count = data.get("count", 0)
                ef_unit = str(data.get("unit") or data.get("ef_unit") or "kg TOC/hr/component")
                raw_ef = data.get("ef")
                if raw_ef is None or (raw_ef == 0 and "ef" not in data):
                    raw_ef = DEFAULT_EFS[k_norm]
                from .units import per_source_hour_kg
                ef, unit_is_ch4 = per_source_hour_kg(raw_ef, ef_unit)
                is_methane = bool(data.get("is_methane")) or unit_is_ch4
            else:
                count = float(data or 0)
                ef = DEFAULT_EFS[k_norm]
                is_methane = False
            count = float(count or 0)
            if count < 0:
                raise ValueError(f"Component count for '{comp_type}' cannot be negative")
            s_ch4 = str(ch4_content).replace("%", "").strip()
            c_ch4 = float(s_ch4)
            if c_ch4 < 0:
                raise ValueError("ch4_content cannot be negative")
            if "%" in str(ch4_content) or c_ch4 > 1.0:
                if c_ch4 <= 100.0:
                    c_ch4 /= 100.0
                else:
                    raise ValueError(f"ch4_content cannot exceed 100%: {ch4_content}")
            ch4_scaling = 1.0 if is_methane else c_ch4
            total_ch4_kg_hr += count * ef * ch4_scaling

        total_ch4_tonnes_year = (total_ch4_kg_hr * 8760) / 1000.0

        uncertainties = uncertainties or {}
        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        ch4_res = propagate_uncertainty(
            total_ch4_tonnes_year,
            resolve_ef_uncertainty(
                "fugitive_component", "ch4", _tier, uncertainties.get("ch4")
            ),
            tier=_tier,
            process_category="fugitive_component",
            gas="ch4",
        )
        total_co2e = calculate_co2e(ch4=total_ch4_tonnes_year, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={"component_counts": component_counts, "ch4_content": ch4_content},
        )


class EquipmentFugitiveCalculator(BaseCalculator):
    def __init__(self):
        super().__init__("Equipment-Level Fugitive", "Section 7.2.2")

    def calculate(
        self, equipment_count, ef, ch4_content=None, uncertainties=None, ef_unit="kg/hr", gwp_dict=None
    ):
        """
        Average Factor Method for equipment - count * EF
        """
        uncertainties = uncertainties or {}
        self.validate_inputs({"count": equipment_count, "ef": ef, "ch4_content": ch4_content},
                             ["count", "ef", "ch4_content"])  # no invented 85 % CH4

        eq_cnt = float(equipment_count)
        if eq_cnt < 0:
            raise ValueError(f"equipment_count cannot be negative: {equipment_count}")

        # BUG-048: parse the unit (subscript CH4, tonne vs kg, hourly vs annual)
        from .units import per_source_hour_kg

        kg_per_hr, is_methane = per_source_hour_kg(ef, ef_unit or "kg CH4/hr/source")
        if kg_per_hr < 0:
            raise ValueError(f"Emission factor cannot be negative: {ef}")
        s_ch4 = str(ch4_content).replace("%", "").strip()
        c_ch4 = float(s_ch4)
        if c_ch4 < 0:
            raise ValueError("ch4_content cannot be negative")
        if "%" in str(ch4_content) or c_ch4 > 1.0:
            if c_ch4 <= 100.0:
                c_ch4 /= 100.0
            else:
                raise ValueError(f"ch4_content cannot exceed 100%: {ch4_content}")
        scaling = 1.0 if is_methane else c_ch4
        total_ch4_tonnes_year = eq_cnt * kg_per_hr * scaling * 8760.0 / 1000.0

        _tier = resolve_tier(uncertainties.get("_factor_source", "default"))
        ch4_res = propagate_uncertainty(
            total_ch4_tonnes_year,
            resolve_ef_uncertainty(
                "equipment_fugitive", "ch4", _tier, uncertainties.get("ch4")
            ),
            tier=_tier,
            process_category="equipment_fugitive",
            gas="ch4",
        )
        total_co2e = calculate_co2e(ch4=total_ch4_tonnes_year, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={
                "equipment_count": equipment_count,
                "ef": ef,
                "ch4_content": c_ch4,
            },
        )


class CompressorSealCalculator(BaseCalculator):
    """Compressor seal / rod packing venting with the API Compendium 2021 default factors.

    kg CH4 per compressor-hour by segment and seal type. The former 15 / 1.5 / 1.2 kg/hr were not in
    the Compendium (they were attributed to "Table 7-3", which lists offshore facility factors).
    """

    SEAL_FACTORS_KG_HR = {
        # production / gathering & boosting
        ("production", "centrifugal_wet"): (26.0, "Section 6.5.4.2, GHGRP wet seal degassing for production and G&B, 0.026 t/compressor-hr"),
        ("production", "reciprocating"): (0.443, "Table 6-30, rod packing (US) 4.43E-04 t/compressor-hr"),
        # processing
        ("processing", "centrifugal_wet"): (86426.0 / 8760.0, "Table 6-38, wet seal 86,426 kg/compressor-yr"),
        ("processing", "centrifugal_dry"): (28192.0 / 8760.0, "Table 6-38, dry seal 28,192 kg/compressor-yr"),
        ("processing", "reciprocating"): (2.7, "Table 6-37, rod packing 0.0027 t/compressor-hr"),
        # transmission & storage
        ("transmission", "centrifugal_wet"): (18.4, "Table 6-41, wet seal average 1.84E-02 t/compressor-hr"),
        ("transmission", "centrifugal_dry"): (5.75, "Table 6-41, dry seal average 5.75E-03 t/compressor-hr"),
        ("transmission", "reciprocating"): (4.72, "Table 6-40, rod packing T&S operating 4.72E-03 t/compressor-hr"),
    }

    def __init__(self):
        super().__init__("Compressor Seal Leakage", "Sections 6.4.3 / 6.5.4 / 6.6")

    def calculate(self, compressor_count, seal_type, uncertainties=None, hours=8760, gwp_dict=None,
                  segment="production", measured_kg_hr=None):
        uncertainties = uncertainties or {}
        self.validate_inputs({"count": compressor_count}, ["count"])
        comp_count = float(compressor_count)
        if comp_count < 0:
            raise ValueError(f"compressor_count cannot be negative: {compressor_count}")
        seg = str(segment or "production").lower()
        seg = ("processing" if "process" in seg else "transmission" if ("transmission" in seg or "storage" in seg)
               else "production")

        if measured_kg_hr not in (None, ""):
            ef, source = float(measured_kg_hr), "measured leak rate"
            if ef < 0:
                raise ValueError("measured_kg_hr cannot be negative")
            factor_source = uncertainties.get("_factor_source", "specific")
        else:
            entry = self.SEAL_FACTORS_KG_HR.get((seg, seal_type))
            if entry is None:
                raise ValueError(f"The API Compendium gives no {seal_type.replace('_', ' ')} factor for the {seg} "
                                 "segment; enter a measured leak rate (kg CH4/hr per compressor) or the segment")
            ef, source = entry
            factor_source = "default"  # a Compendium default is Tier 1 whatever the record's source

        op_hours = float(hours if hours is not None else 8760)
        if op_hours < 0 or op_hours > 8784:
            raise ValueError(f"hours must be between 0 and 8784: {op_hours}")
        total_ch4_kg_hr = comp_count * ef
        total_ch4_tonnes_year = (total_ch4_kg_hr * op_hours) / 1000.0

        _tier = resolve_tier(factor_source)
        ch4_res = propagate_uncertainty(
            total_ch4_tonnes_year,
            resolve_ef_uncertainty(
                "compressor_fugitive", "ch4", _tier, uncertainties.get("ch4")
            ),
            tier=_tier,
            process_category="compressor_fugitive",
            gas="ch4",
        )
        total_co2e = calculate_co2e(ch4=total_ch4_tonnes_year, gwp_dict=gwp_dict)

        return self.format_result(
            ch4=ch4_res,
            total_co2e=total_co2e,
            inputs={"compressor_count": compressor_count, "seal_type": seal_type, "segment": seg,
                    "ef_kg_ch4_per_hr": ef, "factor": source, "hours": op_hours},
        )

