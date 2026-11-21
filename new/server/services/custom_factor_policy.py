"""Custom emission factor governance (HR-06, HSE decision 2026-10-08).

- a source/method reference is required;
- a value outside ``PLAUSIBILITY_BOUNDS`` is refused unless a written justification is given, and the
  factor then waits for approval;
- a new factor is Pending until a superuser or administrator approves it; an administrator may approve their own
  (GB RY2022 decision D10, 2026-11-21), a superuser may not. ``CUSTOM_FACTOR_SECOND_APPROVER=false`` (one-admin install)
  approves an administrator's in-range factor at creation.
"""
import os

PLAUSIBILITY_BOUNDS = {
    "co2_factor": (0.0, 500.0),    # API 2021: typical solid fuels ~100 kg/MMBtu
    "ch4_factor": (0.0, 100.0),    # API 2021: max ~5 for most fuels
    "n2o_factor": (0.0, 10.0),     # API 2021: max ~0.5 for most fuels
}
JUSTIFICATION_MIN_CHARS = 10


def second_approver_required():
    return os.environ.get("CUSTOM_FACTOR_SECOND_APPROVER", "true").strip().lower() not in ("0", "false", "no")


def _per_mmbtu_scale(unit):
    """Factor that converts a factor in `unit` to kg per MMBtu, or None when the unit is not per unit of energy.

    The bounds are kg/MMBtu (energy basis). They were applied to the number whatever its unit, so 3,186 kg CO2 per
    tonne of diesel (73.96 kg/MMBtu) needed a justification and 50 kg CH4/MMBtu passed (audit 2026-11 F-FAC-03).
    A factor per activity unit (per gal, scf, bbl, event ...) is not compared with an energy bound."""
    if not unit:
        return 1.0  # the form's default unit is kg/MMBtu
    from calculations.units import UnitError, parse_factor_unit

    try:
        parsed = parse_factor_unit(unit)
    except (UnitError, ValueError, TypeError):
        return None
    dens = parsed.get("denominators") or []
    if len(dens) != 1 or dens[0][0] != "energy":
        return None
    # base_factor_per_unit is the energy of one denominator unit in the parser's energy base; rescaled to MMBtu
    per_unit = float(dens[0][1])
    mmbtu = float(parse_factor_unit("kg/MMBtu")["denominators"][0][1])
    return float(parsed.get("mass_kg") or 1.0) / per_unit * mmbtu if per_unit else None


def out_of_range_fields(co2, ch4, n2o, unit=None):
    values = {"co2_factor": co2, "ch4_factor": ch4, "n2o_factor": n2o}
    scale = _per_mmbtu_scale(unit)
    if scale is None:
        return []  # not an energy-basis factor: the kg/MMBtu bounds do not apply
    return [
        f for f, (lo, hi) in PLAUSIBILITY_BOUNDS.items()
        if values[f] is not None and not lo <= float(values[f]) * scale <= hi
    ]


def _needs_justification_message(out):
    return (f"{', '.join(out)} is outside the plausible range; a written justification "
            f"(at least {JUSTIFICATION_MIN_CHARS} characters) is required")


def governance(user, data, co2, ch4, n2o):
    """Rules for a new factor. Returns (error_message, status, justification)."""
    # BUG-0045: a list / number / boolean is not a text reference (.strip() on it was a 500)
    if not isinstance(data.get("source") or "", str) or not isinstance(data.get("justification") or "", str):
        return "'source' and 'justification' must be text", None, None
    if not (data.get("source") or "").strip():
        return "A source or method reference is required for a custom factor", None, None
    out = out_of_range_fields(co2, ch4, n2o, data.get("unit"))
    justification = (data.get("justification") or "").strip()
    if out and len(justification) < JUSTIFICATION_MIN_CHARS:
        return _needs_justification_message(out), None, None
    is_admin = bool(user and user.role == "admin")
    approved_now = is_admin and not out and not second_approver_required()
    return None, "Approved" if approved_now else "Pending", justification if out else None


def check_update(factor, data):
    """For an edit that touches a factor value: (error_message, justification)."""
    if not any(k in data for k in ("co2_factor", "ch4_factor", "n2o_factor")):
        return None, None
    out = out_of_range_fields(factor.co2_factor, factor.ch4_factor, factor.n2o_factor, data.get("unit") or factor.unit)
    if not out:
        return None, None
    justification = (data.get("justification") or "").strip()
    if len(justification) < JUSTIFICATION_MIN_CHARS:
        return _needs_justification_message(out), None
    return None, justification


def with_justification(description, justification):
    if not justification:
        return description
    note = f"[Out-of-range justification] {justification}"
    return f"{description}\n{note}" if description else note


def factor_references(factor):
    """Emission records that use this factor, by FK, legacy id string, payload or name (BUG-056)."""
    from extensions import db
    from models import Emission, Scope2Emission

    fid = factor.id
    s1 = Emission.query.filter(
        db.or_(
            Emission.custom_factor_id == fid,
            Emission.fuel_type == str(fid),
            Emission.fuel_type == factor.name,
            Emission.source_payload.like(f'%"custom_factor_id": {fid},%'),
            Emission.source_payload.like(f'%"custom_factor_id": {fid}}}%'),
            Emission.source_payload.like(f'%"custom_factor_id": "{fid}"%'),
        )
    ).count()
    s2 = Scope2Emission.query.filter(Scope2Emission.source_type == factor.name).count()
    return s1 + s2


def visible_factors(query, user):
    """Custom factors a user may list: global ones and those of facilities in the user's scope (F-GREST-01)."""
    from extensions import db
    from models import CustomFactor
    from utils import get_allowed_facility_ids

    allowed = get_allowed_facility_ids(user)
    if allowed is None:
        return query
    return query.filter(db.or_(CustomFactor.facility_id.is_(None), CustomFactor.facility_id.in_(list(allowed) or [-1])))


def import_governance(holder, row, vals, uploader):
    """HR-06 for a custom factor row of a file import, as on the form and the JSON import (GB RY2022 GB-016: file
    factors were stored Approved with no source check, no bounds and no approver). Returns (error, row,
    initial_status, justification); an existing factor whose values change goes back to Pending unless an
    administrator (one-admin mode) imports it."""
    gov_data = {"source": row.get("source"), "justification": row.get("justification"), "unit": row.get("unit")}
    gases = ("co2_factor", "ch4_factor", "n2o_factor")
    if holder is None:
        err, status, just = governance(uploader, gov_data, vals["co2_factor"], vals["ch4_factor"], vals["n2o_factor"])
        return err, row, status, just
    if any(float(getattr(holder, k) or 0) != float(vals[k] or 0) for k in gases):
        err, just = check_update(holder, {**gov_data, **{k: vals[k] for k in gases}})
        if err:
            return err, row, None, None
        if not (row.get("source") or holder.source):
            return "A source or method reference is required for a custom factor", row, None, None
        if holder.status == "Approved" and (uploader.role != "admin" or second_approver_required()):
            holder.status, holder.approved_by, holder.approved_at = "Pending", None, None
        if just:
            row = dict(row, description=with_justification(row.get("description") or holder.description, just))
    return None, row, None, None
