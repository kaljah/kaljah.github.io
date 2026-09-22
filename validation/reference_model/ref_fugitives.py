"""
INDEPENDENT REFERENCE MODEL: Fugitive Leaks
Component & Equipment Leaks.
First-principles implementation - ZERO production code imports.
Governing equations:
- API Compendium 2021 §6.1, §6.2, §6.4
- US EPA Protocol for Equipment Leak Emission Estimates (EPA-453/R-95-017)
"""

from .ref_constants import resolve_gwp

DEFAULT_COMPONENT_EF_KG_HR = {
    "valve": 0.0045,
    "pump_seal": 0.0135,
    "flange": 0.00039,
    "connector": 0.00020,
    "open_ended_line": 0.0020,
    "sampling_connection": 0.0150,
}

DEFAULT_EQUIPMENT_EF_KG_HR = {
    "gas_wellhead": 0.158,
    "oil_wellhead": 0.018,
    "separator": 0.220,
    "heater_treater": 0.140,
    "compressor_reciprocating": 1.250,
    "compressor_centrifugal": 2.100,
}


def ref_calculate_component_fugitives(
    component_count,
    hours=8760,
    component_type="valve",
    ef_kg_hr=None,
    ch4_fraction=0.90,
    co2_fraction=0.01,
    gwp_standard="AR5",
    gwp_horizon="100",
):
    if component_count is None or float(component_count) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    count = float(component_count)
    hrs = float(hours or 8760.0)
    ct = str(component_type or "valve").lower().strip().replace(" ", "_")
    ef = float(ef_kg_hr) if ef_kg_hr is not None else DEFAULT_COMPONENT_EF_KG_HR.get(ct, 0.0045)

    c1 = float(ch4_fraction or 0.90)
    co2_f = float(co2_fraction or 0.01)

    total_leak_kg = count * ef * hrs
    ch4_tonnes = (total_leak_kg * c1) / 1000.0
    co2_tonnes = (total_leak_kg * co2_f) / 1000.0

    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e = co2_tonnes * gwp["CO2"] + ch4_tonnes * gwp["CH4"]

    return {"co2": co2_tonnes, "ch4": ch4_tonnes, "n2o": 0.0, "co2e": co2e}


def ref_calculate_equipment_fugitives(
    equipment_count,
    hours=8760,
    equipment_type="separator",
    ef_kg_ch4_hr=None,
    gwp_standard="AR5",
    gwp_horizon="100",
):
    if equipment_count is None or float(equipment_count) <= 0:
        return {"co2": 0.0, "ch4": 0.0, "n2o": 0.0, "co2e": 0.0}

    count = float(equipment_count)
    hrs = float(hours or 8760.0)
    eq = str(equipment_type or "separator").lower().strip().replace(" ", "_")
    ef = float(ef_kg_ch4_hr) if ef_kg_ch4_hr is not None else DEFAULT_EQUIPMENT_EF_KG_HR.get(eq, 0.220)

    ch4_kg = count * ef * hrs
    ch4_tonnes = ch4_kg / 1000.0

    gwp = resolve_gwp(gwp_standard, gwp_horizon)
    co2e = ch4_tonnes * gwp["CH4"]

    return {"co2": 0.0, "ch4": ch4_tonnes, "n2o": 0.0, "co2e": co2e}
