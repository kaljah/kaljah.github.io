"""Shared dashboard building blocks (audit RC-9).

Every dashboard panel derives its population from the same rules so panels on one page cannot
disagree:

- Activity / division / segment filters are applied on the FACILITY (BUG-004): record-level
  labels are optional and often NULL, and the dropdowns are built from Facility values.
- Status: Verified, plus Pending when "Preview Pending" is on (BUG-054).
- GWP horizon: GWP-20 is computed from the per-gas columns with the active standard (BUG-005/072).
- Source categories come from one classifier (BUG-061), also used for the methane split.
- Gas volumes are converted with the canonical unit parser (BUG-033/035).
"""
from sqlalchemy import func

from extensions import db
from models import Facility

VERIFIED = ("Verified",)
VERIFIED_OR_PENDING = ("Verified", "Pending", "Pending Approval")


def statuses(include_pending=False):
    return VERIFIED_OR_PENDING if include_pending else VERIFIED


def _set(v):
    return v is not None and str(v).strip().lower() not in ("", "all", "null", "none", "undefined")


def _parse_facility_ids(facility_id):
    """Parses facility_id into a list of ints, or [-1] for 'none', or None if unrestricted ('all'/empty)."""
    if facility_id is None:
        return None
    if isinstance(facility_id, (list, tuple, set)):
        res = []
        for x in facility_id:
            try:
                res.append(int(x))
            except (ValueError, TypeError):
                pass
        return res if res else None
    s = str(facility_id).strip()
    if s.lower() in ("", "all", "null", "undefined"):
        return None
    if s.lower() == "none":
        return [-1]
    res = []
    for part in s.split(","):
        p = part.strip()
        if p.lower() == "none":
            return [-1]
        if p and p.lower() not in ("all", "null", "undefined"):
            try:
                res.append(int(p))
            except (ValueError, TypeError):
                pass
    return res if res else ([-1] if s.lower() == "none" else None)


def apply_scope(query, model, allowed_fids=None, facility_id=None, activity=None, division=None, segment=None,
                joined=False, include_test=False):
    """Facility-level scoping and filters for any model with a facility_id column."""
    needs_join = any(_set(v) for v in (activity, division, segment))
    if needs_join and not joined:
        query = query.join(Facility, Facility.id == model.facility_id)
    if not include_test:
        if model is Facility and hasattr(Facility, "is_test"):
            query = query.filter(Facility.is_test == False)
        else:
            if hasattr(model, "is_test"):
                query = query.filter(model.is_test == False)
            if needs_join and hasattr(Facility, "is_test"):
                query = query.filter(Facility.is_test == False)
            elif not needs_join and hasattr(model, "facility_id") and hasattr(Facility, "is_test"):
                query = query.filter(~model.facility_id.in_(
                    Facility.query.with_entities(Facility.id).filter(Facility.is_test == True)
                ))
    if allowed_fids is not None:
        query = query.filter(model.facility_id.in_(allowed_fids or [-1]))
    fids = _parse_facility_ids(facility_id)
    if fids is not None:
        if len(fids) == 1:
            query = query.filter(model.facility_id == fids[0])
        else:
            query = query.filter(model.facility_id.in_(fids))
    if _set(activity):
        query = query.filter(Facility.activity == activity)
    if _set(division):
        query = query.filter(Facility.division == division)
    if _set(segment):
        # segments are listed in one form (Upstream ...): match whatever case / spacing was stored (#14)
        query = query.filter(func.lower(func.trim(Facility.segment)) == str(segment).strip().lower())
    return query


def apply_year(query, model, year):
    if _set(year):
        query = query.filter(model.year == int(year))
    return query


def gwp_pair(horizon="100"):
    """(CH4, N2O) GWPs of the active standard for the requested horizon."""
    from calculations.constants import get_active_gwp

    g = get_active_gwp(horizon="20" if str(horizon) == "20" else "100")
    return float(g["CH4"]), float(g["N2O"])


def horizon_delta(ch4_t, n2o_t, horizon="100"):
    """tCO2e to ADD to a stored GWP-100 total to express it at `horizon` (0 for 100)."""
    if str(horizon) != "20":
        return 0.0
    c100, n100 = gwp_pair("100")
    c20, n20 = gwp_pair("20")
    return float(ch4_t or 0) * (c20 - c100) + float(n2o_t or 0) * (n20 - n100)


def scope3_record_co2e(co2e_val, gc, horizon="100"):
    """Calculate effective Scope 3 co2e taking GWP-20 gas composition into account."""
    val = float(co2e_val or 0.0)
    if str(horizon).lower() in ("20", "gwp20", "20yr") and gc:
        if isinstance(gc, str):
            import json
            try:
                gc = json.loads(gc)
            except Exception:
                gc = None
        if isinstance(gc, dict):
            from calculations.constants import get_active_gwp
            _gwp = get_active_gwp()
            _g_ch4 = float(_gwp.get("CH4", _gwp.get("ch4", 28.0)))
            _g_n2o = float(_gwp.get("N2O", _gwp.get("n2o", 265.0)))
            ch4_t = gc.get("ch4_tonnes") or (val * (gc.get("ch4_pct", 0) / 100.0) / _g_ch4 if gc.get("ch4_pct") else 0.0)
            n2o_t = gc.get("n2o_tonnes") or (val * (gc.get("n2o_pct", 0) / 100.0) / _g_n2o if gc.get("n2o_pct") else 0.0)
            val += horizon_delta(ch4_t, n2o_t, "20")
    return val


# ── Source classification (BUG-061) ─────────────────────────────────────────────

_FLARING = {"flaring", "flare", "routine_flaring", "non_routine_flaring", "safety_flaring", "flare_gas",
            "emergency_flaring", "acid_gas_flaring"}
_TOKENS = [
    ("flaring", {"flaring", "flare", "flared"}),
    ("fugitive", {"fugitive", "fugitives", "leak", "leaks", "seal", "seals", "ldar", "component", "equipment"}),
    ("vented", {"vent", "venting", "vented", "blowdown", "blowdowns", "pneumatic", "pneumatics", "tank", "tanks",
                "flashing", "completion", "completions", "flowback", "unloading", "dehydrator", "dehydrators",
                "dehydration", "agr", "drilling", "degassing", "workover", "casing", "loading"}),
    ("combustion", {"combustion", "fuel", "boiler", "heater", "engine", "turbine", "furnace", "generator", "mobile",
                    "stationary", "incinerator", "cogen"}),
    ("process", {"process", "stoichiometric", "calcination", "chemical", "nitric", "adipic", "cement", "steel",
                 "hydrogen", "catalyst", "coker", "asphalt"}),
]


# Scope 1 processes the generic classifiers leave as "other": well testing / workovers / separator
# dump and produced water are vented gas (Compendium 6.2, 6.3), CO2 EOR is vented CO2 (Exhibit 6-22),
# a thermal oxidizer is a combustion device (5.3). As "other" their CH4 was counted as combustion
# methane and their emissions left out of Venting on the dashboard.
_EXPLICIT = {"well_testing": "vented", "workovers": "vented", "workover": "vented", "separation": "vented",
             "co2_eor": "vented", "thermal_oxidizer": "combustion"}


def source_category(process_type):
    """combustion | flaring | vented | fugitive | process | other."""
    p = str(process_type or "").strip().lower()
    if p in _FLARING:
        return "flaring"
    if p in _EXPLICIT:
        return _EXPLICIT[p]
    try:
        from calculations.uncertainty import PROCESS_CATEGORY

        cat = PROCESS_CATEGORY.get(p)
    except Exception:
        cat = None
    mapping = {"combustion": "combustion", "flaring": "flaring", "fugitive": "fugitive", "vented": "vented",
               "midstream": "vented", "stoichiometric": "process"}
    if cat in mapping:
        return mapping[cat]
    try:
        from process_categories import PROCESS_TYPES

        pc = (PROCESS_TYPES.get(p) or {}).get("category")
        if pc in ("vented", "fugitive", "process"):
            return pc
    except Exception:
        pass
    tokens = set(p.replace("-", " ").replace("_", " ").replace("/", " ").split())
    for name, words in _TOKENS:
        if tokens & words:
            return name
    return "other"


# ── Gas volume (BUG-033 / BUG-035) ──────────────────────────────────────────────

def gas_volume_m3(quantity, unit, year=None, month=None):
    """Standard m3 for a gas volume, or None when the unit is unknown (caller must flag it).
    A rate unit covers the record's month (its year when no month is given)."""
    from calculations.units import UnitError, period_volume_m3

    if quantity in (None, ""):
        return 0.0
    try:
        return period_volume_m3(float(quantity), unit or "", year=year, month=month)
    except (UnitError, ValueError, TypeError):
        return None


# ── BOE (BUG-044): one definition for every endpoint ─────────────────────────────
# API Compendium 2021 BOE conversion: 5.8 MMBtu per BOE and the heat content of the gas. With the platform's
# natural gas HHV (1,020 Btu/scf, emission_factors.py) that is 1.020 / 5.8 = 0.17586 BOE per Mcf (5,686 scf/BOE).
from calculations.units import (
    NG_HHV_BTU_PER_SCF,
    MMBTU_PER_BOE,
    GAS_BOE_PER_MSCF,
    SCF_PER_BOE,
)


BBL_PER_TONNE_CRUDE = 7.33  # average crude (~33 API), the convention the dashboard already used


def production_oil_bbl(row):
    """Oil / condensate in barrels, or None for an unknown unit."""
    from calculations.units import UnitError, unit_dimension

    amt = getattr(row, "oil_amount", None)
    if not amt:
        return 0.0
    try:
        dim, f = unit_dimension(row.oil_unit or "bbl")
    except UnitError:
        return None
    if dim == "volume":
        return float(amt) * f / 0.158987295
    if dim == "mass":
        return float(amt) * f / 1000.0 * BBL_PER_TONNE_CRUDE
    return None


def calculate_oil_gas_boe(row):
    """Compute BOE directly from oil barrels and gas volume at standard conversion."""
    oil = production_oil_bbl(row)
    gas_m3 = production_gas_m3(row)
    if oil is None and gas_m3 is None:
        return None
    gas_boe = (gas_m3 * 35.314666721 / SCF_PER_BOE) if gas_m3 is not None else 0.0
    oil_boe = oil if oil is not None else 0.0
    return oil_boe + gas_boe


def validate_production_mmboe_consistency(total_mmboe, calculated_boe, tolerance=0.30):
    """
    Validates whether total_production_mmboe is within tolerance of oil+gas converted BOE.
    Returns (is_consistent, diff_pct).
    """
    if total_mmboe is None or calculated_boe is None or calculated_boe <= 0:
        return True, 0.0
    stored_boe = float(total_mmboe) * 1e6
    diff_pct = abs(stored_boe - calculated_boe) / calculated_boe
    return diff_pct <= tolerance, diff_pct


def production_boe(row):
    """BOE of one ProductionData row, or None when a unit cannot be interpreted.

    Consistent calculation:
    Calculates oil barrels + gas at GAS_BOE_PER_MSCF.
    If total_production_mmboe is recorded:
      - Validates whether total_production_mmboe is within tolerance (30%) of the oil+gas converted BOE.
      - If consistent, total_production_mmboe * 1e6 is used (incorporating detailed stream accounting).
      - If discordant (e.g. test outlier like 10,000 MMBOE vs 0.62 MMBOE actual),
        it falls back to the canonical oil+gas converted BOE and logs a warning.
    """
    calc_boe = calculate_oil_gas_boe(row)
    stored_mmboe = getattr(row, "total_production_mmboe", None)
    if stored_mmboe is not None and float(stored_mmboe) > 0:
        stored_boe = float(stored_mmboe) * 1e6
        if calc_boe is not None and calc_boe > 0:
            is_consistent, diff_pct = validate_production_mmboe_consistency(stored_mmboe, calc_boe, tolerance=0.30)
            if is_consistent:
                return stored_boe
            else:
                import logging
                logging.getLogger(__name__).warning(
                    "ProductionData row %s has discordant total_production_mmboe (%s MMBOE) "
                    "differing by %.1f%% from calculated oil+gas BOE (%s BOE). Falling back to calculated BOE.",
                    getattr(row, "id", "?"), stored_mmboe, diff_pct * 100.0, calc_boe
                )
                return calc_boe
        return stored_boe
    return calc_boe


def production_gas_m3(row):
    """Produced gas volume (m3) of one ProductionData row, or None if unknown unit."""
    if getattr(row, "gross_gas_mmsm3", None):
        return float(row.gross_gas_mmsm3) * 1e6
    if getattr(row, "gas_amount", None):
        return gas_volume_m3(row.gas_amount, row.gas_unit or "mscf", getattr(row, "year", None), getattr(row, "month", None))
    return 0.0


def query_sum(query, *cols):
    return query.with_entities(*[db.func.coalesce(db.func.sum(c), 0.0) for c in cols]).first()
