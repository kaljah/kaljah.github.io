"""CHP / cogeneration allocation of a Scope 2 record (API Compendium 2021 s8.2; moved out of routes/scope2.py)."""
from input_validation import ValidationError, parse_number
from services.scope2_policy import _LEGACY_BOILER_EF_KG_PER_MMBTU

_POWER = ("power", "electricity", "electric")


def calc_cogen_allocation(data):
    """Calculate heat-allocated tCO2e for CHP / cogeneration entry."""
    val = float(data.get("amount", 0) or data.get("co2e", 0) or data.get("total_emissions", 0))
    ci = data.get("calc_inputs", {}).get("cogen_allocation", {})
    total_emissions = float(data.get("total_emissions") or ci.get("total_emissions", val))
    if total_emissions == 0 and data.get("fuel_consumed_mmbtu"):
        # Calculate facility emissions from fuel consumed (e.g. 53.06 kg CO2/MMBtu)
        # natural gas: CO2 plus the Table 4-6 CH4 / N2O, as for the default steam boiler
        # fuel energy (HHV, as fuel is metered): the natural-gas HHV factor 53.06 kg CO2/MMBtu with the Table 4-6
        # CH4 / N2O (the LHV factors of Exhibit 8.3 belong to its 92 % LHV boiler efficiency only)
        from calculations.constants import get_active_gwp
        _g = get_active_gwp()
        total_emissions = (float(data["fuel_consumed_mmbtu"])
                           * (_LEGACY_BOILER_EF_KG_PER_MMBTU + 0.001 * float(_g["CH4"]) + 0.0001 * float(_g["N2O"]))) / 1000.0
    heat_output = float(data.get("heat_output_mmbtu") or ci.get("heat_output", 0))
    power_output = float(data.get("power_output_mwh") or ci.get("power_output", 0))
    method = data.get("allocation_method") or ci.get("allocation_method", "wri_efficiency")
    if total_emissions <= 0:
        return 0.0
    # API Compendium 2021 s8.2.1, Eq 8-3 / 8-4 and Exhibit 8.4 step 5: the plant's emissions are allocated on its
    # total heat and power outputs, then the buyer's share is the stream's allocation x bought / total. The whole
    # stream (or with a blank power output the whole plant) was booked (audit 2026-11 F-S23-01: 2.9 x to 4.7 x).
    if heat_output <= 0 or power_output <= 0:
        raise ValidationError("CHP allocation needs the plant's total heat output (MMBtu) and power output (MWh)",
                              "heat_output")
    p_stream = str(data.get("purchased_stream") or ci.get("purchased_stream") or data.get("energy_type") or "heat").lower()
    is_power = p_stream in ("power", "electricity", "electric")
    raw_bought = next((v for v in (data.get("quantity_bought"), ci.get("quantity_bought"),
                                   data.get("power_bought_mwh") if is_power else data.get("heat_bought_mmbtu"))
                       if v not in (None, "")), None)
    if raw_bought in (None, ""):
        raise ValidationError("CHP allocation needs the quantity of the stream bought (MMBtu of heat or MWh of power)",
                              "quantity_bought")
    bought = parse_number(raw_bought, "quantity_bought", min_value=0)
    stream_total = power_output if is_power else heat_output
    if bought > stream_total * (1 + 1e-9):
        raise ValidationError("The quantity bought cannot exceed the plant's output of that stream", "quantity_bought")
    # One allocation formula: calculations.indirect.CogenAllocationCalculator. Power output is
    # entered in MWh (BUG-097) and converted there.
    from calculations.indirect import CogenAllocationCalculator

    res = CogenAllocationCalculator().calculate(
        total_emissions=total_emissions, heat_output=heat_output, power_output=power_output,
        method="wri_efficiency" if method == "wri_efficiency" else "energy_content", power_unit="mwh",
        heat_efficiency=data.get("heat_efficiency") or ci.get("heat_efficiency"),
        power_efficiency=data.get("power_efficiency") or ci.get("power_efficiency"),
    )
    allocated = res["metadata"]["allocated_power_tonnes"] if is_power else res["metadata"]["allocated_heat_tonnes"]
    return allocated * bought / stream_total


def chp_heat_bought(data, ci=None, required=False):
    """The heat bought (MMBtu), the record's activity; 0 when power is bought (audit 2026-11 F-S23-01)."""
    ci = ci if ci is not None else ((data.get("calc_inputs") or {}).get("cogen_allocation") or {})
    if str(data.get("purchased_stream") or ci.get("purchased_stream") or "heat").lower() in _POWER:
        return 0.0
    raw = data.get("quantity_bought") or ci.get("quantity_bought") or data.get("heat_bought_mmbtu")
    return parse_number(raw, "quantity_bought", required=required, min_value=0, default=0.0)
