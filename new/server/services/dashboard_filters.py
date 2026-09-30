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
from extensions import db
from models import Facility

VERIFIED = ("Verified",)
VERIFIED_OR_PENDING = ("Verified", "Pending", "Pending Approval")


def statuses(include_pending=False):
    return VERIFIED_OR_PENDING if include_pending else VERIFIED


def _set(v):
    return v not in (None, "", "all")


def apply_scope(query, model, allowed_fids=None, facility_id=None, activity=None, division=None, segment=None,
                joined=False):
    """Facility-level scoping and filters for any model with a facility_id column."""
    needs_join = any(_set(v) for v in (activity, division, segment))
    if needs_join and not joined:
        query = query.join(Facility, Facility.id == model.facility_id)
    if allowed_fids is not None:
        query = query.filter(model.facility_id.in_(allowed_fids or [-1]))
    if _set(facility_id):
        query = query.filter(model.facility_id == int(facility_id))
    if _set(activity):
        query = query.filter(Facility.activity == activity)
    if _set(division):
        query = query.filter(Facility.division == division)
    if _set(segment):
        query = query.filter(Facility.segment == segment)
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

def gas_volume_m3(quantity, unit):
    """Standard m3 for a gas volume, or None when the unit is unknown (caller must flag it)."""
    from calculations.units import UnitError, annual_volume_m3

    if quantity in (None, ""):
        return 0.0
    try:
        return annual_volume_m3(float(quantity), unit or "")
    except (UnitError, ValueError, TypeError):
        return None


# ── BOE (BUG-044): one definition for every endpoint ─────────────────────────────
# The platform's intensity KPIs use 0.178 BOE per Mcf (= 5,618 scf/BOE, i.e. 5.8 MMBtu/BOE at
# ~1,032 Btu/scf); /granular-intensities used 5.8 Mcf/BOE. One constant is used everywhere now.
GAS_BOE_PER_MSCF = 0.178
SCF_PER_BOE = 1000.0 / GAS_BOE_PER_MSCF


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


def production_boe(row):
    """BOE of one ProductionData row, or None when a unit cannot be interpreted.

    Uses total_production_mmboe when recorded, otherwise oil barrels + gas at GAS_BOE_PER_MSCF.
    """
    if getattr(row, "total_production_mmboe", None):
        return float(row.total_production_mmboe) * 1e6
    oil = production_oil_bbl(row)
    gas_m3 = gas_volume_m3(row.gas_amount, row.gas_unit or "mscf") if getattr(row, "gas_amount", None) else 0.0
    if oil is None or gas_m3 is None:
        return None
    return oil + gas_m3 * 35.314666721 / SCF_PER_BOE


def production_gas_m3(row):
    """Produced gas volume (m3) of one ProductionData row, or None if unknown unit."""
    if getattr(row, "gross_gas_mmsm3", None):
        return float(row.gross_gas_mmsm3) * 1e6
    if getattr(row, "gas_amount", None):
        return gas_volume_m3(row.gas_amount, row.gas_unit or "mscf")
    return 0.0


def query_sum(query, *cols):
    return query.with_entities(*[db.func.coalesce(db.func.sum(c), 0.0) for c in cols]).first()
