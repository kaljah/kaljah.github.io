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


def test_facility_ids():
    """Ids of the test facilities (one query; pass the list to exclude_test_rows when calling it several times)."""
    return [fid for (fid,) in db.session.query(Facility.id).filter(Facility.is_test == True).all()]  # noqa: E712


def exclude_test_rows(query, model, test_fids=None):
    """Drop test rows (the record's own is_test flag and records of test facilities), as apply_scope does.

    For the queries that do their own facility / tenant scoping (SBTi, national inventory, equity, CBAM, OGMP,
    QA/QC): they counted test rows the dashboard leaves out (blind audit BA-006 / BA-011)."""
    if hasattr(model, "is_test"):
        query = query.filter(model.is_test == False)  # noqa: E712
    if hasattr(model, "facility_id") and hasattr(Facility, "is_test"):
        fids = test_fids if test_fids is not None else test_facility_ids()
        if fids:
            query = query.filter(~model.facility_id.in_(fids))
    return query


def apply_scope(query, model, allowed_fids=None, facility_id=None, activity=None, division=None, segment=None,
                joined=False, include_test=False, test_fids=None, tenant_id=None):
    """Facility-level scoping and filters for any model with a facility_id column."""
    needs_join = any(_set(v) for v in (activity, division, segment))
    if needs_join and not joined:
        query = query.join(Facility, Facility.id == model.facility_id)
        joined = True
    if not include_test:
        if model is Facility and hasattr(Facility, "is_test"):
            query = query.filter(Facility.is_test == False)
        else:
            if hasattr(model, "is_test"):
                query = query.filter(model.is_test == False)
            if needs_join and hasattr(Facility, "is_test"):
                query = query.filter(Facility.is_test == False)
            elif not needs_join and hasattr(model, "facility_id") and hasattr(Facility, "is_test"):
                resolved_test_fids = (
                    test_fids
                    if test_fids is not None
                    else [
                        fid
                        for (fid,) in db.session.query(Facility.id)
                        .filter(Facility.is_test == True)
                        .all()
                    ]
                )
                if resolved_test_fids:
                    query = query.filter(~model.facility_id.in_(resolved_test_fids))
    if allowed_fids is not None:
        target_col = Facility.id if model is Facility else getattr(model, "facility_id", None)
        if target_col is not None:
            query = query.filter(target_col.in_(allowed_fids or [-1]))
    else:
        # BUG-FLT-001: When allowed_fids is None, apply tenant filtering to prevent cross-tenant leak
        if tenant_id is None:
            # no try/except: if the tenant cannot be resolved the query must fail, not run unfiltered
            from utils import get_current_tenant_id, has_multi_tenant_data
            tid = get_current_tenant_id()
            if tid != "default" or has_multi_tenant_data():
                tenant_id = tid
        if tenant_id is not None:
            from utils import tenant_matches
            if model is Facility:
                query = query.filter(tenant_matches(Facility.tenant_id, tenant_id))
            elif hasattr(model, "facility_id"):
                if not joined:
                    query = query.join(Facility, Facility.id == model.facility_id)
                    joined = True
                query = query.filter(tenant_matches(Facility.tenant_id, tenant_id))
    fids = _parse_facility_ids(facility_id)
    if fids is not None:
        target_col = Facility.id if model is Facility else getattr(model, "facility_id", None)
        if target_col is not None:
            if len(fids) == 1:
                query = query.filter(target_col == fids[0])
            else:
                query = query.filter(target_col.in_(fids))
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
             "co2_eor": "vented", "thermal_oxidizer": "combustion",
             # midstream non-routine releases and compressor venting (Compendium Tables 6-33 / 6-43, s6.6) are vented;
             # wastewater (s7.5) is a non-combustion process source (audit 2026-11 F-GAPI-01: all were "other")
             "transmission_non_routine": "vented", "gathering_non_routine": "vented",
             "processing_non_routine": "vented", "distribution_non_routine": "vented",
             "transmission_compressor": "vented", "gathering_compressor": "vented", "wastewater": "process",
             # fire suppressant releases (Compendium s5 / 7.6) are not equipment leaks (GB RY2022 GB-055)
             "fire_suppression": "other"}


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
# API Compendium 2021 Table 3-4 BOE: 5.8 MMBtu per BOE; 1 BOE of natural gas = 5,647.52 scf (0.17707 BOE per Mcf).
from calculations.units import (
    NG_HHV_BTU_PER_SCF,
    MMBTU_PER_BOE,
    GAS_BOE_PER_MSCF,
    SCF_PER_BOE,
)


BBL_PER_TONNE_CRUDE = 7.33  # average crude (~33 API), the convention the dashboard already used


def _safe_float(val, default=0.0):
    if val in (None, "", "-"):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _row_attr(row, key, default=None):
    """Safely retrieves a field from either an ORM row, namedtuple, SimpleNamespace, or dict."""
    if isinstance(row, dict):
        return row.get(key, default)
    return getattr(row, key, default)


def production_oil_bbl(row):
    """Oil / condensate in barrels, or None for an unknown unit."""
    from calculations.units import UnitError, unit_dimension

    amt = _row_attr(row, "oil_amount", None)
    if not amt:
        return 0.0
    try:
        dim, f = unit_dimension(_row_attr(row, "oil_unit", "bbl") or "bbl")
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
    Calculates oil barrels + gas at GAS_BOE_PER_MSCF (gas is net of reinjected volume).
    If total_production_no_injected_mmboe is recorded, it is preferred over total_production_mmboe
    so that reinjected gas does not inflate the denominator of intensity metrics.
    If total_production_mmboe is recorded (and no net variant exists):
      - Validates whether total_production_mmboe is within tolerance (30%) of the oil+gas converted BOE.
      - If consistent, total_production_mmboe * 1e6 is used (incorporating detailed stream accounting).
      - If discordant (e.g. test outlier like 10,000 MMBOE vs 0.62 MMBOE actual),
        it falls back to the canonical oil+gas converted BOE and logs a warning.
    """
    calc_boe = calculate_oil_gas_boe(row)

    # Prefer the net-of-reinjected BOE column when available
    # BUG-FLT-002: Respect total_production_no_injected_mmboe whenever present, regardless of stored volume magnitude
    raw_stored_no_inj = _row_attr(row, "total_production_no_injected_mmboe", None)
    if raw_stored_no_inj is not None and str(raw_stored_no_inj).strip() != "":
        stored_mmboe = _safe_float(raw_stored_no_inj, 0.0)
        if stored_mmboe > 0:
            return stored_mmboe * 1e6

    raw_stored = _row_attr(row, "total_production_mmboe", None)
    stored_mmboe = _safe_float(raw_stored, 0.0)
    if stored_mmboe > 0:
        stored_boe = stored_mmboe * 1e6
        if calc_boe is not None and calc_boe > 0:
            is_consistent, diff_pct = validate_production_mmboe_consistency(stored_mmboe, calc_boe, tolerance=0.30)
            if is_consistent:
                return stored_boe
            else:
                import logging
                logging.getLogger(__name__).warning(
                    "ProductionData row %s has discordant total_production_mmboe (%s MMBOE) "
                    "differing by %.1f%% from calculated oil+gas BOE (%s BOE). Falling back to calculated BOE.",
                    _row_attr(row, "id", "?"), stored_mmboe, diff_pct * 100.0, calc_boe
                )
                return calc_boe
        return stored_boe
    return calc_boe


def production_gas_m3(row):
    """Produced gas volume (m³) of one ProductionData row, **net of reinjected gas**, or None if unknown unit.

    Reinjected gas (pressure maintenance, EOR, storage) is not marketed production: keeping it in
    the denominator understates flaring intensity, carbon intensity and methane loss rate.  The
    Master Report already computes net gas (master_report_data_records._aggregate_production_records); the dashboard and
    intensity service now follow the same logic.
    """
    # 1. Prefer the pre-computed net column (gross minus reinjected)
    net_mm = _safe_float(_row_attr(row, "gas_without_injected_mmsm3", None), 0.0)
    if net_mm > 0:
        return net_mm * 1e6

    # 2. Gross minus reinjected if both are available
    gross_mm = _safe_float(_row_attr(row, "gross_gas_mmsm3", None), 0.0)
    injected_mm = _safe_float(_row_attr(row, "injected_gas_mmsm3", None), 0.0)
    if gross_mm > 0:
        if injected_mm > 0:
            return max(gross_mm - injected_mm, 0.0) * 1e6
        return gross_mm * 1e6

    # 3. Fall back to the legacy oil_amount / gas_amount columns (no reinjection data available)
    gas_amt = _row_attr(row, "gas_amount", None)
    if gas_amt:
        return gas_volume_m3(gas_amt, _row_attr(row, "gas_unit", "mscf") or "mscf", _row_attr(row, "year", None), _row_attr(row, "month", None))
    return 0.0


def query_sum(query, *cols):
    return query.with_entities(*[db.func.coalesce(db.func.sum(c), 0.0) for c in cols]).first()
