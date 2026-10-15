"""Custom emission factor governance (HR-06, HSE decision 2026-10-08).

- a source/method reference is required;
- a value outside ``PLAUSIBILITY_BOUNDS`` is refused unless a written justification is given, and the
  factor then waits for approval;
- an admin's own factor is approved by a second administrator (``CUSTOM_FACTOR_SECOND_APPROVER``,
  on by default).
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


def out_of_range_fields(co2, ch4, n2o):
    values = {"co2_factor": co2, "ch4_factor": ch4, "n2o_factor": n2o}
    return [
        f for f, (lo, hi) in PLAUSIBILITY_BOUNDS.items()
        if values[f] is not None and not lo <= float(values[f]) <= hi
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
    out = out_of_range_fields(co2, ch4, n2o)
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
    out = out_of_range_fields(factor.co2_factor, factor.ch4_factor, factor.n2o_factor)
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
