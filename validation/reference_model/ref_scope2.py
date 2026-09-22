"""
INDEPENDENT REFERENCE MODEL: Scope 2 Indirect Emissions
Purchased Electricity (Location-based & Market-based), Purchased Steam, Heat, Cooling.
First-principles implementation - ZERO production code imports.
Governing equations:
- GHG Protocol Scope 2 Guidance (2015 Amendment to Corporate Standard)
- ISO 14064-1:2018 §5.2.3
"""

from .ref_constants import CONV_KWH_TO_MJ, CONV_MMBTU_TO_MJ


def ref_calculate_scope2_electricity(
    electricity_kwh,
    emission_factor_kg_kwh,
    method="location_based",
    loss_factor=0.0,
):
    if electricity_kwh is None or float(electricity_kwh) <= 0:
        return {"co2e": 0.0, "method": method}

    kwh = float(electricity_kwh)
    ef = float(emission_factor_kg_kwh or 0.0)
    loss = max(0.0, min(0.5, float(loss_factor or 0.0)))

    # Grid transmission loss adjustment: Q_delivered / (1 - loss)
    adj_kwh = kwh / max(0.001, (1.0 - loss))
    co2e_kg = adj_kwh * ef
    co2e_tonnes = co2e_kg / 1000.0

    return {"co2e": co2e_tonnes, "method": method}


def ref_calculate_scope2_steam(
    steam_tonnes,
    ef_kg_per_tonne=None,
    boiler_efficiency=0.80,
    loss_factor=0.05,
):
    if steam_tonnes is None or float(steam_tonnes) <= 0:
        return {"co2e": 0.0}

    tonnes = float(steam_tonnes)
    ef = float(ef_kg_per_tonne or 180.0)  # default ~180 kg CO2e / tonne steam
    loss = max(0.0, min(0.5, float(loss_factor or 0.05)))
    eta = max(0.1, min(1.0, float(boiler_efficiency or 0.80)))

    # Steam energy delivered including thermal distribution losses and boiler efficiency
    adj_tonnes = tonnes / (1.0 - loss)
    co2e_kg = (adj_tonnes * ef) / eta
    return {"co2e": co2e_kg / 1000.0}


def ref_calculate_scope2_cooling(
    cooling_ton_hours,
    cop=3.5,  # Coefficient of performance
    grid_ef_kg_kwh=0.50,
):
    if cooling_ton_hours is None or float(cooling_ton_hours) <= 0:
        return {"co2e": 0.0}

    # 1 ton-hour of refrigeration = 12,000 Btu = 3.51685 kWh thermal
    kwh_thermal = float(cooling_ton_hours) * 3.5168528
    # Electrical work = Thermal energy / COP
    kwh_electric = kwh_thermal / max(0.5, float(cop or 3.5))
    co2e_kg = kwh_electric * float(grid_ef_kg_kwh or 0.50)
    return {"co2e": co2e_kg / 1000.0}
