import logging

from .dispatcher import dispatcher as api2021_dispatcher
from .constants import DEFAULT_GWP, get_active_gwp

log = logging.getLogger(__name__)


def _note_fallback(branch, process, payload):
    """The API 2021 dispatcher did not produce a result; the older factor math is used.

    This is the designated path for entered Tier 3 factors, saved custom factors, zero
    activity and catalog factors of processes the dispatcher does not model (measured over
    the whole test suite: 11 uses in ~2,500 tests). Logged at DEBUG; raise the level of this
    logger to measure how often it runs."""
    log.debug(
        "legacy calculation fallback used: branch=%s process=%s factor_source=%s",
        branch, process or "?", (payload.get("factor_source") or "default"),
    )


# Constants
STD_TEMP_R = 519.67  # 60°F in Rankine
STD_PRESS_PSIA = 14.696  # Standard Pressure
MOLAR_VOL_US = 379.3  # scf/lb-mole (at 60°F, 14.696 psia)

MW = {
    "C": 12.01,
    "CO2": 44.01,
    "CH4": 16.04,
    "N2O": 44.013,
    "H2": 2.016,
    "Air": 28.96,
    "SO2": 64.06,
}

GWP = {"CH4": DEFAULT_GWP["CH4"], "N2O": DEFAULT_GWP["N2O"]}


from .units import norm_unit, parse_amount, UnitError


def _convert_factor_to_kg(val, factor_unit, activity_unit, hours=None, **conv):
    """kg per activity unit through the canonical converter (combustion.convert_factor_to_kg_per_unit):
    the HHV basis comes from its unit or the fuel type, never from the size of the number (an HHV
    above 500 used to be taken for Btu whatever it was per)."""
    from .combustion import convert_factor_to_kg_per_unit

    if val is None:
        return 0.0
    if not factor_unit or norm_unit(factor_unit) == norm_unit(activity_unit):
        return float(val)  # Manage Data convention: kg per activity unit
    try:
        return convert_factor_to_kg_per_unit(float(val), factor_unit, activity_unit, hours=hours, **conv)
    except UnitError as err:
        raise ValueError(str(err))


def _calculate_default_kg(amount, unit, factor_data, gas, hours=None, **conv):
    """kg of gas from factor_data. A factor whose unit equals the activity unit is kg per that unit
    (it was multiplied by 1000 when the unit was "tonnes"); a unit that cannot be applied to the
    activity is an error, never applied 1:1."""
    if not factor_data:
        return 0.0

    raw_val = (
        factor_data.get(gas)
        or factor_data.get("factor")
        or factor_data.get("total")
        or (factor_data.get("co2") if gas == "co2" else None)
        or 0.0
    )
    try:
        val = float(raw_val or 0.0)
    except (ValueError, TypeError):  # an unreadable factor was taken as 0 (no emissions booked)
        raise ValueError(f"Emission factor '{gas}' is not a number: {raw_val}")
    if val <= 0:
        return 0.0
    raw_unit = str(factor_data.get("unit") or "").strip()
    return float(amount) * _convert_factor_to_kg(val, raw_unit, unit, hours=hours, **conv)



_CH4_ONLY = frozenset({"fugitive", "pneumatic", "dehydrator"})
_NO_N2O = frozenset({"venting", "loading", "separation", "associated_gas_venting", "tank", "agr", "drilling",
                     "completions", "unloading"})


def _payload_density(payload):
    """The fuel density in kg/m3, with its density_unit, as the dispatcher reads it."""
    from .dispatcher import CalculationDispatcher

    return CalculationDispatcher._fuel_density(CalculationDispatcher, payload)


def _compute_emissions_impl(payload, factor_data=None, gwp_dict=None, gwp_standard=None):
    if factor_data is None:
        factor_data = {}
    if gwp_dict is None:
        gwp_dict = get_active_gwp(standard=gwp_standard)

    process = str(payload.get("process_type") or payload.get("process") or "").lower()

    # Normalize frontend names to expected internal keys
    if process == "pneumatics":
        process = "pneumatic"
    elif process == "tanks":
        process = "tank"
    elif process == "mud degassing":
        process = "drilling"
    elif process == "well completions":
        process = "completions"
    elif process == "dehydrators":
        process = "dehydrator"
    elif process == "blowdowns":
        process = "venting"
    elif process == "liquid unloading":
        process = "unloading"
    # "separation" stays its own process: it is not a tank-flashing calculation (browser test F4:
    # every separator / produced-water factor was computed with the crude flashing factor)
    elif process in ["associated gas venting", "associated venting", "associated gas"]:
        process = "associated_gas_venting"
    raw_amt = payload.get("amount") if payload.get("amount") not in [None, ""] else payload.get("quantity")
    raw_amt = parse_amount(raw_amt)
    amount = float(raw_amt or 0)
    unit = payload.get("unit") or "m3"

    # Safely parse HHV - handle None, empty string, or '-' placeholders
    hhv_val = payload.get("hhv") or factor_data.get("hhv") or 0
    if hhv_val in [None, "", "-"]:
        hhv = 0
    else:
        try:
            hhv = float(hhv_val)
        except (ValueError, TypeError):  # an unreadable HHV was taken as "none given"
            raise ValueError(f"Heating value (HHV) is not a number: {hhv_val}")

    if hhv and not payload.get("hhv"):
        payload["hhv"] = hhv
    from .combustion import factor_hhv_unit, user_hhv

    conv_hhv, conv_hu = user_hhv(hhv or None, payload.get("hhv_unit") if payload.get("hhv") not in (None, "") else None)
    conv = dict(
        hhv=conv_hhv,
        hhv_unit=conv_hu or factor_hhv_unit(factor_data),
        fuel_type=factor_data.get("type") if factor_data.get("type") not in (None, "", "custom") else (
            payload.get("fuel_type") or payload.get("fuel")),
        density=_payload_density(payload) or factor_data.get("density"),
    )

    calc_inputs = payload.get("calc_inputs") or {}
    inputs = calc_inputs.get(process) or {}  # Extract specific inputs
    if process == "completions" and isinstance(inputs, dict) and inputs.get("amount") not in (None, ""):
        # BUG-012: the Completions form's `amount` is the event count; it must not replace the
        # top-level activity volume, and it is passed on explicitly as `events`.
        inputs = dict(inputs)
        amt = inputs.pop("amount")
        # Tier 3: the amount is the metered flowback volume, not a count; events are explicit or 1
        # (Tier 3 browser test #1: 1.48e6 scf was read as 1.48e6 events)
        # and an amount in a volume unit (or on the metered method) is that volume, never a count
        # (deep-dive audit: 500 Mcf metered was 500 events x 500 Mcf)
        # (the unit of calc_inputs itself: the top-level unit belongs to the top-level volume)
        comp_unit = str(inputs.get("unit") or "").lower().strip()
        comp_meth = str(inputs.get("comp_method") or inputs.get("calc_method") or payload.get("comp_method") or "").lower()
        is_volume = comp_unit in ("scf", "m3", "sm3", "mcf", "mscf", "mmscf") or comp_meth.startswith("metered")
        if inputs.get("comp_volume") in (None, "") and inputs.get("flowback_volume") in (None, "") and not is_volume:
            inputs.setdefault("events", amt)

    # NEW: Merge root payload into inputs to support flat CSV data
    # This allows keys like 'comp_duration' or 'unload_diam' to be read directly from the CSV row
    inputs = {**payload, **inputs}
    # the record-level activity, kept for the unit-consistency check (S1K-F9: a form sends the converted
    # top-level amount and the method's own amount + unit; both are the same activity)
    inputs["_top_amount"], inputs["_top_unit"] = payload.get("amount"), payload.get("unit")  # (hhv: set on payload above)

    density_val = payload.get("density") or payload.get("fuel_density") or factor_data.get("density")
    if density_val not in [None, "", "-"]:
        try:
            inputs["density"] = float(density_val)
        except (ValueError, TypeError):  # an unreadable density was ignored
            raise ValueError(f"Fuel density is not a number: {density_val}")

    is_specific = payload.get("factor_source") == "specific" or payload.get(
        "isSpecific"
    )
    spec = payload.get("specificFactors") or payload.get("specific_factors")

    em = {"co2": 0, "ch4": 0, "n2o": 0, "totalCo2e": 0, "co": 0, "ce": 0}
    calc_method = "server_default"

    # --- API 2021 CALCULATION DISPATCHER --- first, except for entered Tier 3 factors (legacy path below):
    # with the catalog fuel the form always sends, it returned the catalog factor and ignored them
    _spec = payload.get("specific_factors") or payload.get("specificFactors") or {}
    _has_spec = isinstance(_spec, dict) and any(
        str(v).strip() not in ("", "0", "0.0", "None") for k, v in _spec.items() if not str(k).endswith("Unit")
    )
    uncertainties = factor_data.get("uncertainty", {})
    api_res = None if (is_specific and _has_spec) else api2021_dispatcher.dispatch(
        process, inputs, factor_data, uncertainties, gwp_dict=gwp_dict
    )

    def get_val(r):
        # BUG-15/16 FIX: handle None results from CH4-only calculators (e.g. MudDegassing, Completions)
        # format_result() sets co2/n2o to None when not passed; calling .get() on None crashes.
        if r is None:
            return 0
        if isinstance(r, dict):
            return r.get("value", 0)
        return r

    # A Tier 3 engineering result of zero is a real outcome (e.g. 0 operating hours); it must not fall
    # through to the legacy factor path and its misleading "request not understood" error
    _tier3_zero = (str(payload.get("factor_source") or "").lower() == "specific" and not _has_spec
                   and api_res and "results" in api_res)
    if (
        api_res
        and "results" in api_res
        and (any(get_val(api_res["results"].get(g)) for g in ["co2", "ch4", "n2o", "f_gas"]) or _tier3_zero or amount == 0)  # 0 is 0
    ):
        # If the dispatcher handled it, return the rich result structure
        # We extract the 'value' for backward compatibility with the legacy database record creation
        results = api_res["results"]

        # BUG-15/16 FIX: CH4-only calculators (e.g. MudDegassing) leave co2/n2o as None.
        # Normalize None → 0 at extraction point, not just in get_val.
        def _extract(r):
            if r is None:
                return 0
            if isinstance(r, dict):
                return r.get("value", 0) or 0
            return r or 0

        em["co2"] = _extract(results.get("co2"))
        em["ch4"] = _extract(results.get("ch4"))
        em["n2o"] = _extract(results.get("n2o"))
        em["totalCo2e"] = (
            (em["co2"] * float(gwp_dict.get("CO2", 1.0)))
            + (em["ch4"] * float(gwp_dict.get("CH4", 28.0)))
            + (em["n2o"] * float(gwp_dict.get("N2O", 265.0)))
            + float((results.get("f_gas") or {}).get("co2e") or 0)  # HFC / SF6 (sections 7.6)
        )

        em["_full_api_res"] = api_res  # the full rich result, for the route
        return em, api_res.get("method", "api2021_generic")

    # The legacy engineering blocks (completions, fugitive screening, pneumatics, dehydrators, tanks,
    # FCCU) that used to follow filled missing inputs with invented values (placeholder Table 7-7
    # factors, GOR 500 scf/bbl, 85 % CH4, high-bleed devices, 100 % CH4 completions). Every one of these
    # processes is calculated by the API 2021 dispatcher above; a request it did not handle continues
    # with the entered factors below, or is refused (MissingFactorError), never with placeholder numbers.

    # Standard / Specific (Combustion, Flaring, etc.)
    if is_specific and spec:
        base_unit = spec.get("co2Unit") or spec.get("unit") or unit

        # Helper: convert a factor value from its declared unit to kg per activity-unit
        def get_factor(gas):
            gas_unit = spec.get(f"{gas}Unit") or base_unit or unit

            # Prefer the explicit 'Raw' value (user entered in a different unit)
            raw = spec.get(f"{gas}Raw")
            if raw is not None and str(raw).strip() != "":
                try:
                    raw_val = float(raw)
                except (ValueError, TypeError):
                    raise ValueError(f"Specific factor '{gas}' has invalid raw value: {raw}")
                target_unit = spec.get(f"{gas}Unit") or base_unit
                if not target_unit or target_unit == unit:
                    return raw_val
                return _convert_factor_to_kg(
                    raw_val, target_unit, unit, hours=payload.get("hours"), **conv
                )

            # Otherwise use the direct value — but STILL convert from its declared unit
            val = spec.get(gas)
            if val is not None and str(val).strip() != "":
                try:
                    raw_val = float(val)
                except (ValueError, TypeError):
                    raise ValueError(f"Specific factor '{gas}' has invalid value: {val}")
                if gas_unit and gas_unit != unit:
                    return _convert_factor_to_kg(
                        raw_val, gas_unit, unit, hours=payload.get("hours"), **conv
                    )
                return raw_val
            return None

        f_co2 = get_factor("co2")
        f_ch4 = get_factor("ch4")
        f_n2o = get_factor("n2o")
        f_co = get_factor("co")

        em["co2"] = (
            (amount * f_co2)
            if f_co2 is not None
            else _calculate_default_kg(amount, unit, factor_data, "co2", **conv)
        )

        if process in ["combustion", "flaring", "venting"]:
            em["ch4"] = (
                (amount * f_ch4)
                if f_ch4 is not None
                else _calculate_default_kg(amount, unit, factor_data, "ch4", **conv)
            )
            em["n2o"] = (
                (amount * f_n2o)
                if f_n2o is not None
                else _calculate_default_kg(amount, unit, factor_data, "n2o", **conv)
            )
            em["co"] = (
                (amount * f_co) if (f_co is not None and process != "combustion") else 0
            )
        else:
            em["ch4"] = (amount * f_ch4) if f_ch4 is not None else 0
            em["n2o"] = (amount * f_n2o) if f_n2o is not None else 0

        em["totalCo2e"] = (
            em["co2"] + (em["ch4"] * gwp_dict["CH4"]) + (em["n2o"] * gwp_dict["N2O"])
        ) / 1000.0
        em["co2"] /= 1000.0
        em["ch4"] /= 1000.0
        em["n2o"] /= 1000.0
        if em["co"]:
            em["co"] /= 1000.0

        calc_method = "server_specific"
        _note_fallback(calc_method, process, payload)
        return em, calc_method

    if factor_data and factor_data.get("type"):
        # Use individual gas factors directly (correct for custom factors which carry co2/ch4/n2o fields).
        co2_kg = _calculate_default_kg(amount, unit, factor_data, "co2", **conv)
        ch4_kg = _calculate_default_kg(amount, unit, factor_data, "ch4", **conv)
        n2o_kg = _calculate_default_kg(amount, unit, factor_data, "n2o", **conv)

        em["co2"] = co2_kg / 1000.0
        em["ch4"] = ch4_kg / 1000.0
        em["n2o"] = n2o_kg / 1000.0
        em["totalCo2e"] = (
            em["co2"] + (em["ch4"] * gwp_dict["CH4"]) + (em["n2o"] * gwp_dict["N2O"])
        )

        calc_method = "server_custom_factor"
        _note_fallback(calc_method, process, payload)
        return em, calc_method

    # --- DEFAULT/CUSTOM MODE: Factor-Based Calculation ---
    # Apply process-specific gas calculation rules per API Compendium 2021

    # Calculate base emissions from factors
    co2_kg = _calculate_default_kg(amount, unit, factor_data, "co2", **conv)
    ch4_kg = _calculate_default_kg(amount, unit, factor_data, "ch4", **conv)
    n2o_kg = _calculate_default_kg(amount, unit, factor_data, "n2o", **conv)

    # Gases each process emits (API 2021): leaks and vents of fugitive / pneumatic / dehydrator gas are CH4
    # only; vented, tank, AGR, drilling and well processes have no N2O; combustion and the rest all three
    em["co2"] = 0 if process in _CH4_ONLY else co2_kg / 1000.0
    em["ch4"] = ch4_kg / 1000.0
    em["n2o"] = 0 if process in _CH4_ONLY or process in _NO_N2O else n2o_kg / 1000.0

    # Calculate total CO2e
    em["totalCo2e"] = (
        em["co2"] + (em["ch4"] * gwp_dict["CH4"]) + (em["n2o"] * gwp_dict["N2O"])
    )

    _note_fallback(calc_method, process, payload)
    return em, calc_method



class MissingFactorError(ValueError):
    """Raised instead of silently booking 0 tCO2e when no emission factor could be resolved."""


def _has_factor_values(factor_data):
    if not factor_data:
        return False
    # the factors were read as numbers by the calculation (an unreadable one is refused there)
    return any(float(factor_data.get(key) or 0) > 0 for key in ("co2", "ch4", "n2o"))


def compute_emissions(payload, factor_data=None, gwp_dict=None, gwp_standard=None):
    """Entry point for Scope 1 calculations (routes, bulk, recalculation).

    Audit BUG-015 / BUG-042 / BUG-102 / BUG-112: a positive activity amount that yields zero
    emissions because no factor was resolved is an error, never a silent 0 tCO2e record.
    Tier 3 ("specific") engineering results are exempt: zero can be a real engineering outcome.
    """
    from .flare_defaults import (FLARE_PROCESSES, PRODUCTION_DESTRUCTION, REFINERY_DESTRUCTION,
                                 facility_segment, _efficiency_given)
    raw_proc = str(payload.get("process_type") or payload.get("process") or "").strip().lower()
    if raw_proc in FLARE_PROCESSES and not _efficiency_given(payload) and facility_segment(payload) == "downstream":
        payload = {**payload, "destruction_efficiency": REFINERY_DESTRUCTION}
        if factor_data and factor_data.get("combustion_efficiency_ch4") == PRODUCTION_DESTRUCTION and factor_data.get("ch4") not in (None, ""):
            residual = (1 - REFINERY_DESTRUCTION) / (1 - PRODUCTION_DESTRUCTION)
            factor_data = {**factor_data, "ch4": float(factor_data["ch4"]) * residual, "combustion_efficiency_ch4": REFINERY_DESTRUCTION}

    em, method = _compute_emissions_impl(payload, factor_data, gwp_dict=gwp_dict, gwp_standard=gwp_standard)
    if "_full_api_res" not in em:
        # factor-math fallback: the dispatcher applies CCS capture itself, so apply it here too
        from .dispatcher import capture_fraction

        capture = capture_fraction(payload)
        if capture:
            em["totalCo2e"] -= em["co2"] * capture
            em["co2"] *= 1.0 - capture
    if any(float(em.get(g) or 0) for g in ("co2", "ch4", "n2o")):
        return em, method
    raw = payload.get("amount") if payload.get("amount") not in (None, "") else payload.get("quantity")
    amount = float(str(raw).replace(",", "")) if raw not in (None, "") else 0.0  # parsed by the calculation
    source = str(payload.get("factor_source") or "default").lower()
    if amount > 0 and source in ("default", "custom", "") and not _has_factor_values(factor_data):
        name = payload.get("fuel") or payload.get("fuel_type") or payload.get("custom_factor_id") or "(none)"
        raise MissingFactorError(
            f"No emission factor found for '{name}' ({payload.get('process_type') or 'process'}); "
            "the record was not saved. Select a factor from the catalog or a saved custom factor."
        )
    return em, method
