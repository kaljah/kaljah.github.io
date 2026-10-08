"""One way to build, calculate and persist a Scope 1 record (audit RC-6).

Used by POST /api/emissions/, PUT /api/emissions/<id> and /api/emissions/import so the
create, edit and import paths calculate from — and store — the same values:

- BUG-003 / BUG-030: `amount`/`quantity` and `fuel`/`fuel_type` are aliases; a request that sets
  one sets both, and the persisted quantity / fuel are exactly the values calculated from.
- BUG-042: the custom factor is resolved from the request, else from the stored payload, and a
  record whose factor_source is "custom" never falls back to the catalog or to zero.
- BUG-037: the persisted uncertainty is the propagated 1-sigma result, identical on every path.
- BUG-050 / BUG-109 / BUG-068: activity values are validated before any calculator runs.
"""
import json
import math

from input_validation import ValidationError, merge_inputs, parse_number

# Scope 2 process types must never be booked in the Scope 1 table (BUG-068)
SCOPE2_PROCESS_TYPES = {
    "indirect_steam", "cogen_allocation", "cogen", "chp", "purchased_steam", "purchased_heat",
    "purchased_electricity", "electricity", "steam", "heat", "cooling",
}


# Scope 1 process types offered by the manual form (client utils/EmissionFactors.js PROCESS_TYPES,
# kept in sync by tests/test_bulk_uploaders.py); bulk files may use the key or the label
PROCESS_LABELS = {
    "combustion": "Stationary Combustion",
    "flaring": "Flaring",
    "routine_flaring": "Routine Flaring",
    "non_routine_flaring": "Non-Routine Flaring",
    "safety_flaring": "Safety Flaring",
    "associated_gas_venting": "Associated Gas Venting",
    "venting": "Venting (Blowdown)",
    "pneumatic": "Pneumatic Device",
    "tank_flashing": "Storage Tank - Flashing/Events",
    "tank_working": "Storage Tank - Working Losses",
    "tank_breathing": "Storage Tank - Breathing Losses",
    "drilling": "Drilling Operations",
    "completions": "Well Completions & Workovers",
    "unloading": "Liquids Unloading",
    "agr": "Acid Gas Removal (AGR)",
    "dehydrator": "Dehydrator",
    "mobile": "Mobile Combustion",
    "fugitive": "Onshore Equipment Leaks / Fugitives",
    "loading": "Loading Losses",
    "separation": "Wastewater / Separation",
    "chemical_production": "Chemical Production (Process CO₂)",
    "nitric_acid_production": "Nitric Acid Production (Process N₂O)",
    "adipic_acid_production": "Adipic Acid Production (Process N₂O)",
    "asphalt_blowing": "Asphalt Blowing",
    "indirect_steam": "Indirect Steam / Heat (Section 8)",
    "cogen_allocation": "Cogeneration Allocation (Section 8)",
    "well_testing": "Well Testing",
    "workovers": "Workovers (no hydraulic fracturing)",
    "casing_gas": "Casing Gas Venting",
    "compressor_venting": "Compressor Venting (seals / rod packing)",
    "non_routine_venting": "Non-Routine Venting (blowdowns, PRVs, dig-ins)",
    "vented_gas": "Vented / Flared Gas Volume",
    "desiccant_dehydrator": "Desiccant Dehydrator",
    "co2_eor": "CO₂ EOR Venting",
    "thermal_oxidizer": "Thermal Oxidizer",
}

# names used by the earlier Excel template and import wizard
_PROCESS_SYNONYMS = {
    "storage_tank_flashing": "tank_flashing",
    "storage_tank_working": "tank_working",
    "storage_tank_breathing": "tank_breathing",
    "pneumatic_device": "pneumatic",
    "pneumatic_devices": "pneumatic",
    "pneumatics": "pneumatic",
    "pneumatic_controller": "pneumatic",
    "pneumatic_controllers": "pneumatic",
    "pneumatic_pump": "pneumatic",
    "pneumatic_pumps": "pneumatic",
    "well_completions": "completions",
    "well_completion": "completions",
    "fugitives": "fugitive",
    "fugitive_emissions": "fugitive",
    "fugitives_equipment": "fugitive",
    "fugitive_equipment": "fugitive",
    "equipment_leaks": "fugitive",
    "blowdowns": "blowdown",
    "acid_gas_removal": "agr",
    "dehydrators": "dehydrator",
    "glycol_dehydrator": "dehydrator",
}


def _slug(text):
    import re

    return re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")


def normalize_process_type(raw):
    """Canonical process key for a bulk-file value (key, label or known synonym), or None."""
    from calculations.dispatcher import dispatcher

    s = _slug(raw)
    if not s:
        return None
    if s in PROCESS_LABELS:
        return s
    for key, label in PROCESS_LABELS.items():
        if s == _slug(label):
            return key
    if s in _PROCESS_SYNONYMS:
        return _PROCESS_SYNONYMS[s]
    return s if s in dispatcher.calculators else None


def check_factor_usage(process_type, factor_data, fuel=None):
    """A catalog factor carries the processes it applies to (`usage`); a Tier 1 row must not
    book, for example, crude-oil combustion under tank flashing."""
    from calculations.dispatcher import dispatcher

    usage = (factor_data or {}).get("usage")
    if not usage or factor_data.get("custom_factor_id"):
        return
    usage = [usage] if isinstance(usage, str) else list(usage)
    proc = _slug(process_type)
    calc = dispatcher.calculators.get(proc)
    for u in usage:
        if u == proc or (calc is not None and type(dispatcher.calculators.get(u)) is type(calc)):
            return
    raise ValidationError(
        f"'{fuel or factor_data.get('name') or 'This factor'}' is a {'/'.join(usage)} factor and does not apply to "
        f"process '{process_type}'",
        "fuel",
    )


def custom_factor_data(cf):
    """Map a CustomFactor row to the calculator's factor_data structure."""
    from emission_factors_api2021 import API_FACTORS  # noqa: WPS433

    fd = {
        "co2": cf.co2_factor, "ch4": cf.ch4_factor, "n2o": cf.n2o_factor, "co": cf.co_factor,
        "unit": cf.unit, "hhv": cf.hhv_factor, "type": "custom", "name": cf.name, "custom_factor_id": cf.id,
    }
    if cf.parent_fuel:
        # the HHV is in the parent fuel's basis (Btu/gal for diesel, Btu/scf for gas): without it a
        # custom kg/MMBtu diesel factor applied to gallons was refused as "per scf of gas"
        from calculations.combustion import factor_hhv_unit, fuel_basis
        from routes.emissions import _lookup_api_factor

        parent = _lookup_api_factor(cf.parent_fuel)
        if parent:
            hu = factor_hhv_unit(parent)
            if not hu:
                basis, mult = fuel_basis(parent.get("type") or cf.parent_fuel)
                hu = {1.0: "btu", 1e3: "kbtu", 1e6: "mmbtu"}[mult] + "/" + basis
            fd["hhv_unit"] = hu
    per_gas = [getattr(cf, f"{g}_uncertainty", None) for g in ("co2", "ch4", "n2o")]
    if any(per_gas):
        fd["uncertainty"] = {
            g: float(v or cf.uncertainty or 0) / 100.0 for g, v in zip(("co2", "ch4", "n2o"), per_gas)
        }
    elif cf.uncertainty and cf.uncertainty > 0:
        fd["uncertainty"] = {g: float(cf.uncertainty) / 100.0 for g in ("co2", "ch4", "n2o")}
    elif cf.parent_fuel:
        from routes.emissions import _lookup_api_factor

        parent_unc = _lookup_api_factor(cf.parent_fuel).get("uncertainty")
        if parent_unc:
            fd["uncertainty"] = parent_unc
    return fd


def _set_alias(payload, keys, value):
    for k in keys:
        payload[k] = value


def canonicalize(payload, delta=None):
    """Return a copy of `payload` with aliases synchronised.

    `delta` (for edits) wins over the stored payload: when it carries any alias, every alias
    takes the new value (BUG-003: a PUT of quantity used to leave the old `amount` in place).
    """
    out = dict(payload or {})
    src = delta if delta is not None else out
    for keys in (("amount", "quantity"), ("fuel", "fuel_type")):
        present = [k for k in keys if k in src and src[k] not in (None, "")]
        if present:
            _set_alias(out, keys, src[present[0]])
        elif delta is None:
            existing = next((out[k] for k in keys if out.get(k) not in (None, "")), None)
            if existing is not None:
                _set_alias(out, keys, existing)
    if delta is not None:
        for k, v in delta.items():
            if k not in ("amount", "quantity", "fuel", "fuel_type"):
                out[k] = merge_inputs(out.get(k), v) if k == "calc_inputs" else v  # edits may carry only some inputs
        # Keep calc_inputs synchronized with the edited activity amount/unit/fuel
        ptype = out.get("process_type") or out.get("source_type")
        if ptype and isinstance(out.get("calc_inputs"), dict):
            ci = out["calc_inputs"].get(ptype)
            if isinstance(ci, dict):
                ci_copy = dict(ci)
                if "amount" in out:
                    ci_copy["amount"] = out["amount"]
                if "unit" in out:
                    ci_copy["unit"] = out["unit"]
                if "fuel" in out:
                    ci_copy["fuel"] = out["fuel"]
                out["calc_inputs"] = {**out["calc_inputs"], ptype: ci_copy}
    if out.get("process_type") and not out.get("source_type"):
        out["source_type"] = out["process_type"]
    return out


def validate_activity(payload, require_unit):
    """BUG-050 / BUG-068 / BUG-109: validate before any calculator runs."""
    ptype = str(payload.get("process_type") or "").strip().lower()
    if ptype in SCOPE2_PROCESS_TYPES:
        raise ValidationError(
            f"'{payload.get('process_type')}' is a Scope 2 (purchased energy) source; record it on the Scope 2 page",
            "process_type",
        )
    amount = None
    if payload.get("amount") not in (None, ""):
        amount = parse_number(payload.get("amount"), "amount", min_value=0)
        _set_alias(payload, ("amount", "quantity"), amount)
    if require_unit and amount is not None and not str(payload.get("unit") or "").strip():
        raise ValidationError("'unit' is required for the activity amount", "unit")
    # S1K-F6: "Mt" is the SI megatonne but "MT" is often a metric ton; the case-insensitive unit table
    # booked "1 Mt" as 1 tonne. Refused as ambiguous, like a bare "ton" in files.
    if str(payload.get("unit") or "").strip().lower().replace(".", "") in ("mt", "mts"):
        raise ValidationError(
            f"'{payload.get('unit')}' is ambiguous (megatonne or metric ton): write 'tonne' (1,000 kg)", "unit")
    # one activity representation: calc_inputs must not contradict the top-level activity
    ci = (payload.get("calc_inputs") or {}).get(payload.get("process_type") or "") or {}
    tier12 = str(payload.get("factor_source") or "default").lower() in ("default", "custom")
    # Tier 3 engineering forms carry method-specific inputs in calc_inputs (e.g. the completions
    # event count), so the "one activity representation" rule applies to catalog/custom factors.
    if tier12 and isinstance(ci, dict) and amount is not None and ci.get("amount") not in (None, ""):
        ci_amt = parse_number(ci.get("amount"), "calc_inputs.amount", min_value=0)
        ci_unit = str(ci.get("unit") or payload.get("unit") or "").strip().lower()
        top_unit = str(payload.get("unit") or "").strip().lower()
        if ci_unit != top_unit or not math.isclose(ci_amt, amount, rel_tol=1e-9, abs_tol=1e-12):
            raise ValidationError(
                f"Inconsistent activity: amount {amount} {payload.get('unit')} but calc_inputs {ci_amt} {ci.get('unit') or ''}",
                "amount",
            )
    return amount


# processes whose API Compendium Tier 2 is computed by their own calculator (no factor needed)
ENGINEERING_TIER2 = {
    "completions", "completion_flowback", "unloading", "liquids_unloading",
    "associated_gas_venting", "associated_venting", "associated_gas", "fugitive",
}


def resolve_factor(payload, stored_payload=None, allow_archived=False):
    """Factor data for a calculation. Raises ValidationError when a required factor is missing."""
    from extensions import db
    from models import CustomFactor
    from routes.emissions import _lookup_api_factor

    source = str(payload.get("factor_source") or "").lower()
    # "Library factor" (the site's own factor database: calculated or equipment factors) is a
    # separate choice from the API Compendium tiers; it always needs the selected library factor
    library = str(payload.get("factor_mode") or "").lower() == "library"
    process = str(payload.get("process_type") or payload.get("process") or "").lower()
    cf_id = payload.get("custom_factor_id")
    if cf_id in (None, "") and stored_payload:
        cf_id = stored_payload.get("custom_factor_id")
    if cf_id in (None, "") and (source == "custom" or library):
        fuel = str(payload.get("fuel") or "")
        cf_id = int(fuel) if fuel.isdigit() else None
    if library and cf_id in (None, ""):
        raise ValidationError("Select a library factor", "custom_factor_id")
    if cf_id not in (None, ""):
        try:
            cf = db.session.get(CustomFactor, int(cf_id))
        except (TypeError, ValueError):
            cf = None
        if cf is None or (cf.is_archived and not allow_archived):
            raise ValidationError(f"Custom factor {cf_id} does not exist or is archived", "custom_factor_id")
        payload["custom_factor_id"] = cf.id
        payload["factor_source"] = "custom"
        return custom_factor_data(cf)
    catalog = _lookup_api_factor(payload.get("fuel") or payload.get("fuel_type"))
    if source == "custom" and process in ENGINEERING_TIER2:
        # API Compendium Tier 2 for these processes is an engineering method (operational data,
        # GOR balance, event factors, equipment counts) computed by the process calculator
        return catalog
    if source == "custom":
        # Tier 2 without a saved factor is only valid as "catalog EF + site-specific fuel
        # properties" (national HHV / density presets). Otherwise a Tier 2 record must never
        # silently fall back to the plain catalog factor (BUG-042).
        has_site_props = any(payload.get(k) not in (None, "", 0) for k in ("hhv", "density", "fuel_density"))
        if not (catalog and has_site_props):
            raise ValidationError("factor_source is 'custom' but no custom factor was given", "custom_factor_id")
    if source in ("default", "") and catalog:
        if catalog.get("unverified_basis"):
            raise ValidationError(
                f"'{payload.get('fuel') or payload.get('fuel_type')}' ({catalog.get('unit')}, "
                f"{catalog.get('source') or 'catalog'}) has no verified time basis and cannot be applied to a monthly "
                "record; use a custom factor with an explicit unit (e.g. tonne CH4/hr/facility)",
                "fuel",
            )
        check_activity_unit(catalog, payload.get("unit"), payload.get("fuel") or payload.get("fuel_type"))
    return catalog


def check_activity_unit(factor_data, unit, name=None):
    """A catalog factor is applied to an activity of its own dimension: per-event, per-completion and
    per-well-year factors take a count (events, completions, wells) and a per-bbl factor a volume.
    Those calculators used the amount whatever its unit, so 1,000 m3 of a completion factor was
    booked as 1,000 completions (audit 2026-09-30). An energy factor may still take a volume or a
    mass (converted with the heating value). Units that cannot be parsed are left to the calculator."""
    from calculations.units import UnitError, parse_factor_unit, unit_dimension

    if not unit or not (factor_data or {}).get("unit"):
        return
    try:
        dims = {d for d, _, _ in parse_factor_unit(factor_data["unit"])["denominators"] if d != "time"}
        a_dim, _ = unit_dimension(unit)
    except UnitError:
        return
    if not dims or a_dim in dims or ("energy" in dims and a_dim in ("volume", "mass")):
        return
    expected = {"count": "a count (events, completions, wells)", "volume": "a volume (bbl, m3, scf)",
                "mass": "a mass (tonne, kg)", "energy": "an energy (MMBtu, GJ)"}
    need = " or ".join(expected.get(d, d) for d in sorted(dims))
    raise ValidationError(
        f"'{name or factor_data.get('name') or 'This factor'}' is in {factor_data['unit']}: the activity must be "
        f"{need}, not '{unit}'",
        "unit",
    )


def _gas_unc(api_res, gas):
    r = (api_res or {}).get("results", {}).get(gas)
    return r.get("uncertainty") if isinstance(r, dict) else None


def apply_result(record, payload, em_result, method, factor_data, gwp_std):
    """Persist exactly what was calculated (values, activity, factor link, uncertainty)."""
    record.process_type = payload.get("process_type") or record.process_type
    record.fuel_type = payload.get("fuel") if payload.get("fuel") not in (None, "") else record.fuel_type
    if factor_data and factor_data.get("custom_factor_id") and factor_data.get("name"):
        # a library / custom factor is recorded by its name, not by its id (browser test #13)
        record.fuel_type = factor_data["name"]
    elif factor_data and record.fuel_type:
        # a catalog factor is recorded under its catalog name ("natural gas" -> "Natural Gas")
        from routes.emissions import _canonical_api_factor_name
        record.fuel_type = _canonical_api_factor_name(record.fuel_type) or record.fuel_type
    if not record.fuel_type:
        # Compendium activity rows (Section 6 tables) are recorded by their source label
        proc = str(payload.get("process_type") or "")
        key = payload.get("activity_key") or ((payload.get("calc_inputs") or {}).get(proc) or {}).get("activity_key")
        if key:
            from calculations.activity_factors import ACTIVITY_FACTORS
            row = ACTIVITY_FACTORS.get(str(key))
            if row:
                record.fuel_type = row["label"]
    if payload.get("amount") not in (None, ""):
        record.quantity = float(payload["amount"])
    record.unit = payload.get("unit") or record.unit
    if payload.get("amount") in (None, ""):
        # engineered methods carry no activity amount: record the activity the engine used
        # (Tier 3 browser test #18: the Quantity column was empty)
        api_r = em_result.get("_full_api_res") or {}
        # S1K-F19: the engineered methods report their activity under "inputs" too (flowback volume,
        # vented volume, leakers found, measured hours)
        inter = {**(api_r.get("inputs") if isinstance(api_r.get("inputs"), dict) else {}),
                 **(api_r.get("intermediate") or {})}
        for key, unit in (("net_flowback_scf", "scf"), ("total_vented_scf", "scf"), ("detected_leakers", "leakers")):
            if inter.get("activity_amount") in (None, "") and inter.get(key) not in (None, ""):
                inter = {**inter, "activity_amount": inter[key], "activity_unit": unit}
        if inter.get("activity_amount") in (None, "") and inter.get("operating_hours") not in (None, "") \
                and inter.get("measured_input"):
            inter = {**inter, "activity_amount": inter["operating_hours"], "activity_unit": "h measured"}
        if inter.get("activity_amount") not in (None, "") and inter.get("activity_unit"):
            record.quantity, record.unit = float(inter["activity_amount"]), inter["activity_unit"]
        for key, unit in (("gas_volume_scf", "scf"), ("energy_mmbtu", "MMBtu"), ("fuel_gal", "gal"),
                          ("fuel_mass_t", "t fuel"), ("toc_t", "t TOC"), ("hc_emitted_t", "t HC emitted")):
            if record.quantity is not None and inter.get("activity_amount") not in (None, ""):
                break
            if inter.get(key) not in (None, ""):
                record.quantity, record.unit = float(inter[key]), unit
                break
    record.co2_emissions = em_result["co2"]
    record.ch4_emissions = em_result["ch4"]
    record.n2o_emissions = em_result["n2o"]
    record.co_emissions = em_result.get("co", 0)
    record.co2e_total = em_result["totalCo2e"]
    record.calc_method = method
    record.gwp_version = gwp_std
    record.custom_factor_id = factor_data.get("custom_factor_id") if factor_data else None
    if record.custom_factor_id:
        record.factor_source = "custom"
    record.ef_used_co2 = factor_data.get("co2") if factor_data else None
    record.ef_used_ch4 = factor_data.get("ch4") if factor_data else None
    record.ef_used_n2o = factor_data.get("n2o") if factor_data else None
    record.source_payload = json.dumps(payload, default=str)

    # BUG-037: store the propagated 1-sigma combined uncertainty on every path
    api_res = em_result.get("_full_api_res")
    if api_res:
        record.uncertainty = _gas_unc(api_res, "co2")
        record.uncertainty_ch4 = _gas_unc(api_res, "ch4")
        record.uncertainty_n2o = _gas_unc(api_res, "n2o")
        comps = api_res.get("uncertainty_components") or {}
        record.uncertainty_ad = comps.get("activity")
        record.uncertainty_ef_co2 = comps.get("ef_co2")
        record.uncertainty_ef_ch4 = comps.get("ef_ch4")
        record.uncertainty_ef_n2o = comps.get("ef_n2o")
    else:
        u = (factor_data or {}).get("uncertainty") or {}
        # catalog values are 95 % half-widths; stored values are 1-sigma (k = 2)
        record.uncertainty = (u.get("co2") / 2.0) if isinstance(u, dict) and u.get("co2") else None
        record.uncertainty_ch4 = (u.get("ch4") / 2.0) if isinstance(u, dict) and u.get("ch4") else None
        record.uncertainty_n2o = (u.get("n2o") / 2.0) if isinstance(u, dict) and u.get("n2o") else None
    # Tier 3 browser test #19: a gas with emissions must carry an uncertainty; when neither the
    # calculator nor the factor gives one, the Tier default for the process category applies
    from calculations.uncertainty import resolve_ef_uncertainty, resolve_tier
    tier = resolve_tier(str(payload.get("factor_source") or "default"))
    for attr, gas in (("uncertainty", "co2"), ("uncertainty_ch4", "ch4"), ("uncertainty_n2o", "n2o")):
        if getattr(record, attr) is None and float(em_result.get(gas) or 0) > 0:
            setattr(record, attr, resolve_ef_uncertainty(record.process_type or "", gas, tier))
    record.ef_key = _ef_key(payload, factor_data)


def _ef_key(payload, factor_data):
    """Identifies the emission-factor source so the inventory can correlate its uncertainty (BUG-008)."""
    if factor_data and factor_data.get("custom_factor_id"):
        return f"custom:{factor_data['custom_factor_id']}"
    src = str(payload.get("factor_source") or "default").lower()
    if src == "specific":
        return None  # site-specific: independent per record
    name = factor_data.get("name") if factor_data else None
    return f"catalog:{name or payload.get('fuel') or payload.get('process_type')}"
