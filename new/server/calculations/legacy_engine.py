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


from .units import (
    factor_to_kg_per_activity,
    parse_factor_unit,
    convert,
    UnitError,
)


def _convert_factor_to_kg(val, factor_unit, activity_unit, hhv=0, hours=None):
    """Canonical unit conversion using calculations.units.factor_to_kg_per_activity."""
    if val is None:
        return 0.0
    if not factor_unit or factor_unit == activity_unit:
        return float(val)
    val_float = float(val)

    hhv_mj = None
    if hhv and float(hhv or 0) > 0:
        hhv_mj = float(hhv) * 0.001055056 if float(hhv) > 500 else float(hhv)

    return factor_to_kg_per_activity(
        val_float, factor_unit, activity_unit, hours=hours, hhv_mj_per_unit=hhv_mj
    )


def _calculate_default_kg(amount, unit, hhv, factor_data, gas, hours=None):
    """Calculates kg of gas using factor_data and canonical unit conversion."""
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
    except (ValueError, TypeError):
        return 0.0
    if val <= 0:
        return 0.0

    raw_unit = str(factor_data.get("unit") or "").strip()
    if not raw_unit or raw_unit.lower() == str(unit).lower():
        if "tonnes" in raw_unit.lower():
            val *= 1000.0
        return float(amount) * val

    hhv_mj = None
    if hhv and float(hhv or 0) > 0:
        hhv_mj = float(hhv) * 0.001055056 if float(hhv) > 500 else float(hhv)

    try:
        kg_per_activity = factor_to_kg_per_activity(
            val, raw_unit, unit, hours=hours, hhv_mj_per_unit=hhv_mj
        )
        return float(amount) * kg_per_activity
    except UnitError:
        if "tonne" in raw_unit.lower():
            val *= 1000.0
        return float(amount) * val



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
    if isinstance(raw_amt, str):
        s = raw_amt.strip()
        if "," in s and "." not in s:
            raw_amt = s.replace(",", ".")
        else:
            raw_amt = s.replace(",", "")
    amount = float(raw_amt or 0)
    unit = payload.get("unit") or "m3"

    # Safely parse HHV - handle None, empty string, or '-' placeholders
    hhv_val = payload.get("hhv") or factor_data.get("hhv") or 0
    if hhv_val in [None, "", "-"]:
        hhv = 0
    else:
        try:
            hhv = float(hhv_val)
        except (ValueError, TypeError):
            hhv = 0

    if hhv and not payload.get("hhv"):
        payload["hhv"] = hhv

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
    if hhv and not inputs.get("hhv"):
        inputs["hhv"] = hhv

    density_val = payload.get("density") or payload.get("fuel_density") or factor_data.get("density")
    if density_val not in [None, "", "-"]:
        try:
            inputs["density"] = float(density_val)
        except (ValueError, TypeError):
            pass

    is_specific = payload.get("factor_source") == "specific" or payload.get(
        "isSpecific"
    )
    spec = payload.get("specificFactors") or payload.get("specific_factors")
    factor_source = payload.get("factor_source")

    em = {"co2": 0, "ch4": 0, "n2o": 0, "totalCo2e": 0, "co": 0, "ce": 0}
    calc_method = "server_default"

    # --- API 2021 CALCULATION DISPATCHER ---
    # Try to use the new API 2021 compliant calculators first
    uncertainties = factor_data.get("uncertainty", {})
    api_res = api2021_dispatcher.dispatch(
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
    # (entered specific factors are applied by the legacy path below, so they keep that route)
    _spec = payload.get("specific_factors") or payload.get("specificFactors") or {}
    _has_spec = isinstance(_spec, dict) and any(
        str(v).strip() not in ("", "0", "0.0", "None") for k, v in _spec.items() if not str(k).endswith("Unit")
    )
    _tier3_zero = (str(payload.get("factor_source") or "").lower() == "specific" and not _has_spec
                   and api_res and "results" in api_res)
    if (
        api_res
        and "results" in api_res
        and (any(get_val(api_res["results"].get(g)) for g in ["co2", "ch4", "n2o"]) or _tier3_zero)
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
        )

        # We also attach the full rich result to the emission dict so the route can access it
        em["_full_api_res"] = api_res
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
                    raw_val, target_unit, unit, hhv=hhv, hours=payload.get("hours")
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
                        raw_val, gas_unit, unit, hhv=hhv, hours=payload.get("hours")
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
            else _calculate_default_kg(amount, unit, hhv, factor_data, "co2")
        )

        if process in ["combustion", "flaring", "venting"]:
            em["ch4"] = (
                (amount * f_ch4)
                if f_ch4 is not None
                else _calculate_default_kg(
                    amount, unit, hhv, factor_data, "ch4"
                )
            )
            em["n2o"] = (
                (amount * f_n2o)
                if f_n2o is not None
                else _calculate_default_kg(
                    amount, unit, hhv, factor_data, "n2o"
                )
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
        co2_kg = _calculate_default_kg(amount, unit, hhv, factor_data, "co2")
        ch4_kg = _calculate_default_kg(amount, unit, hhv, factor_data, "ch4")
        n2o_kg = _calculate_default_kg(amount, unit, hhv, factor_data, "n2o")

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
    co2_kg = _calculate_default_kg(amount, unit, hhv, factor_data, "co2")
    ch4_kg = _calculate_default_kg(amount, unit, hhv, factor_data, "ch4")
    n2o_kg = _calculate_default_kg(amount, unit, hhv, factor_data, "n2o")

    # Process-specific gas emission matrix (API 2021)
    # Determine which gases to calculate based on process type
    if process in ["combustion", "mobile"]:
        # All gases from fuel combustion
        em["co2"] = co2_kg / 1000.0
        em["ch4"] = ch4_kg / 1000.0
        em["n2o"] = n2o_kg / 1000.0

    elif process == "flaring":
        # CO2 from combustion + CH4 slip + N2O
        em["co2"] = co2_kg / 1000.0
        em["ch4"] = ch4_kg / 1000.0
        em["n2o"] = n2o_kg / 1000.0

    elif process in ["venting", "loading", "separation", "associated_gas_venting"]:
        # Primarily CH4 release, minor CO2
        em["ch4"] = ch4_kg / 1000.0
        em["co2"] = co2_kg / 1000.0 if co2_kg > 0 else 0
        em["n2o"] = 0

    elif process in ["fugitive", "pneumatic", "dehydrator"]:
        # CH4 only (leaks/vents)
        em["ch4"] = ch4_kg / 1000.0
        em["co2"] = 0
        em["n2o"] = 0

    elif process == "tank":
        # CH4 dominant, minor CO2 from flash gas
        em["ch4"] = ch4_kg / 1000.0
        em["co2"] = co2_kg / 1000.0 if co2_kg > 0 else 0
        em["n2o"] = 0

    elif process == "agr":
        # CO2 removal/venting, minor CH4
        em["co2"] = co2_kg / 1000.0
        em["ch4"] = ch4_kg / 1000.0 if ch4_kg > 0 else 0
        em["n2o"] = 0

    elif process in ["drilling"]:
        # Fuel combustion (CO2/CH4) + mud losses
        em["co2"] = co2_kg / 1000.0
        em["ch4"] = ch4_kg / 1000.0
        em["n2o"] = 0

    elif process in ["completions", "unloading"]:
        # Primarily CH4 from gas release, minor CO2 if flared
        em["ch4"] = ch4_kg / 1000.0
        em["co2"] = co2_kg / 1000.0 if co2_kg > 0 else 0
        em["n2o"] = 0

    else:
        # Default: Calculate all gases if factors exist
        em["co2"] = co2_kg / 1000.0
        em["ch4"] = ch4_kg / 1000.0
        em["n2o"] = n2o_kg / 1000.0

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
    for key in ("co2", "ch4", "n2o"):
        try:
            if float(factor_data.get(key) or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def compute_emissions(payload, factor_data=None, gwp_dict=None, gwp_standard=None):
    """Entry point for Scope 1 calculations (routes, bulk, recalculation).

    Audit BUG-015 / BUG-042 / BUG-102 / BUG-112: a positive activity amount that yields zero
    emissions because no factor was resolved is an error, never a silent 0 tCO2e record.
    Tier 3 ("specific") engineering results are exempt: zero can be a real engineering outcome.
    """
    em, method = _compute_emissions_impl(payload, factor_data, gwp_dict=gwp_dict, gwp_standard=gwp_standard)
    if any(float(em.get(g) or 0) for g in ("co2", "ch4", "n2o")):
        return em, method
    raw = payload.get("amount") if payload.get("amount") not in (None, "") else payload.get("quantity")
    try:
        amount = float(str(raw).replace(",", "")) if raw not in (None, "") else 0.0
    except (TypeError, ValueError):
        amount = 0.0
    source = str(payload.get("factor_source") or "default").lower()
    if amount > 0 and source in ("default", "custom", "") and not _has_factor_values(factor_data):
        name = payload.get("fuel") or payload.get("fuel_type") or payload.get("custom_factor_id") or "(none)"
        raise MissingFactorError(
            f"No emission factor found for '{name}' ({payload.get('process_type') or 'process'}); "
            "the record was not saved. Select a factor from the catalog or a saved custom factor."
        )
    return em, method
