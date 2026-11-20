"""Input rules of CalculationDispatcher, split out of calculations/dispatcher.py (blind audit 2026-11-17).

- efficiencies are percentages, always (BA-012);
- engineering calculators get the record's own period and only the inputs they accept (BA-028 / BA-030);
- a gas volume rate on a catalog factor covers the record's period (BA-024);
- a feedstock carbon fraction with the amount in tonnes reads the amount as the feedstock (BA-039).
"""
from .units import UnitError, parse_volume_rate, period_volume_m3

# Efficiencies entered on any process: always percent, converted once in _dispatch_impl
EFFICIENCY_FIELDS = frozenset({
    "control_efficiency", "flare_efficiency", "flare_eff", "destruction_efficiency", "destruction_eff", "eta_d",
    "combustion_efficiency", "combustion_eff", "combustioneff", "comb_eff", "eta_c", "efficiency",
    "unload_flare_eff", "dehy_eff", "tank_control_eff", "comp_flare_eff", "agr_control_eff", "removal_efficiency",
    "abatement_efficiency", "abatement_eff", "eta_abatement", "boiler_eff", "boiler_efficiency",
    "heat_efficiency", "power_efficiency",
})


def efficiencies_as_fractions(flat_inputs):
    """Every entered efficiency read as a percentage and converted to a fraction (1 was 100 %, 2 was 2 %)."""
    from .dispatcher import percent_to_fraction

    conv = {k: percent_to_fraction(flat_inputs[k], k) for k in EFFICIENCY_FIELDS
            if flat_inputs.get(k) not in (None, "", "-")}
    return {**flat_inputs, **conv} if conv else flat_inputs


def rate_to_period_volume(quantity, unit, inputs):
    """(quantity, unit): a gas volume rate (MMscf/d, m3/h, Mscf/yr) as m3 over the record's period."""
    try:
        is_rate = parse_volume_rate(unit)[1] is not None
    except (UnitError, TypeError, ValueError):
        is_rate = False
    if not is_rate:
        return quantity, unit
    return period_volume_m3(quantity, unit, inputs.get("year"), inputs.get("month")), "m3"


def feedstock_tonnes(flat_inputs, num, cf, feed_t):
    """The hydrogen-plant feedstock in tonnes: entered, or the record amount in tonnes next to a carbon fraction
    (it was read as tonnes of hydrogen produced, Table 6-51, twice the carbon balance)."""
    h2_given = num("h2_produced_tonnes", "h2_produced_scf") is not None
    mass_amount = str(flat_inputs.get("unit") or "").lower() in ("t", "tonne", "tonnes", "metric ton")
    if cf is not None and feed_t is None and mass_amount and not h2_given:
        feed_t = num("amount", "quantity")
    if cf is not None and feed_t is None and not h2_given:
        raise ValueError("A feedstock carbon fraction needs the feedstock quantity (feedstock_rate_tonnes, "
                         "or the record amount in tonnes)")
    return feed_t


_PERIOD_HOUR_PARAMS = ("pressurized_hours", "hours", "operating_hours")
_PERIOD_DAY_PARAMS = ("operating_days",)


def _period_kwargs(method, inputs):
    """Keyword arguments for an engineering calculator's calculate(), with the record's period.

    Per-hour, per-day and per-unit-year factors cover the record's own period (its month): the calculators default
    to 8,760 h / 365 d / one year, so a monthly record booked a whole year. Inputs the method does not accept are
    dropped when it takes no **kwargs (the record always carries `amount`)."""
    import inspect

    from .dispatcher import operating_hours, record_period

    params = inspect.signature(method).parameters
    takes_any = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
    out = dict(inputs) if takes_any else {k: v for k, v in inputs.items() if k in params}
    hrs = operating_hours(inputs)  # entered hours / days, else the record's period
    year_fraction = hrs / 8760.0 if hrs != record_period(inputs)[0] else record_period(inputs)[2]
    for k in _PERIOD_HOUR_PARAMS:
        if k in params and inputs.get(k) in (None, "", "-"):
            out[k] = hrs
    for k in _PERIOD_DAY_PARAMS:
        if k in params and inputs.get(k) in (None, "", "-"):
            out[k] = hrs / 24.0
    if "year_fraction" in params and inputs.get("year_fraction") in (None, "", "-"):
        out["year_fraction"] = year_fraction
    elif takes_any and inputs.get("year_fraction") in (None, "", "-"):
        out["year_fraction"] = year_fraction
    # the record's amount is the calculator's count / miles: it never reached these parameters, which default
    # to 1 (audit 2026-11 F-VENT2-01: 50 miles of pipeline booked as 1 mile)
    amount = inputs.get("amount") if inputs.get("amount") not in (None, "", "-") else inputs.get("quantity")
    if amount not in (None, "", "-"):
        for k in _COUNT_PARAMS:
            if k in params and inputs.get(k) in (None, "", "-"):
                val = float(amount)
                u = str(inputs.get("unit") or "").strip().lower()
                if k == "count_or_miles" and u in ("km", "kilometer", "kilometers", "kilometre", "kilometres"):
                    val *= 0.621371192
                out[k] = val
                break
    return out


# the count / length parameter of each midstream calculator (one per calculator)
_COUNT_PARAMS = ("count_or_miles", "events_or_count", "compressor_count", "tank_count", "controller_count")
