"""Administrator-entered grid-average electricity factors (location-based Scope 2), GB RY2022 GB-003 / GB-021.

GHG Protocol Scope 2 Guidance Table 6.2: the location-based method uses grid-average factors, regional before
national; a supplier factor is market-based only. The catalog (electricity_factors) cannot hold every country's
dated average, so an administrator or superuser adds one with its year and source; it is used once a superuser or
administrator approves it (an administrator may approve their own, as custom factors, D10). Records pick the
vintage of their reporting year (electricity_factors.pick_vintage). Values are kg per kWh.
"""
import datetime

from flask import Blueprint, jsonify, request

from electricity_factors import clear_grid_cache
from extensions import db
from input_validation import ValidationError, parse_number
from models import GridFactor
from routes.auth import login_required, superuser_required
from utils import get_current_tenant_id, get_current_user, log_activity_and_notify, tenant_matches

grid_factors_bp = Blueprint("grid_factors", __name__)

LEVELS = ("national", "regional")
MAX_KG_PER_KWH = 2.0  # the most carbon-intensive grids are about 1.2 kg CO2e/kWh


def _row(g):
    return {"id": g.id, "name": g.name, "country": g.country, "level": g.level, "year": g.year, "co2": g.co2,
            "ch4": g.ch4, "n2o": g.n2o, "source": g.source, "status": g.status, "created_by": g.created_by,
            "approved_by": g.approved_by, "approved_at": g.approved_at.isoformat() if g.approved_at else None}


def _forbidden_it(user):
    return user is not None and user.role in ("it", "it_admin", "it_manager")


def _parse(data, partial=False):
    out = {}
    for key in ("name", "country", "source"):
        if key in data or not partial:
            val = str(data.get(key) or "").strip()
            if key in ("name", "source") and not val:
                raise ValidationError(f"'{key}' is required", key)
            out[key] = val or None
    if "level" in data or not partial:
        level = str(data.get("level") or "national").strip().lower()
        if level not in LEVELS:
            raise ValidationError("level must be national or regional", "level")
        out["level"] = level
    if "year" in data or not partial:
        year = parse_number(data.get("year"), "year", min_value=1990, max_value=2100)
        if int(year) != year:
            raise ValidationError("year must be a whole year", "year")
        out["year"] = int(year)
    for gas, required in (("co2", True), ("ch4", False), ("n2o", False)):
        if gas in data or (required and not partial):
            out[gas] = parse_number(data.get(gas), gas, required=required, min_value=0, max_value=MAX_KG_PER_KWH)
    if out.get("level") == "national" and not (out.get("country") or (partial and "country" not in data)):
        raise ValidationError("A national grid average names its country", "country")
    return out


@grid_factors_bp.route("", methods=["GET"])
@login_required
def list_grid_factors():
    user = get_current_user()
    if _forbidden_it(user):
        return jsonify({"error": "IT personnel do not have access to operational factor data"}), 403
    q = GridFactor.query.filter(tenant_matches(GridFactor.tenant_id, get_current_tenant_id(user)))
    if request.args.get("include_archived") not in ("1", "true"):
        q = q.filter(GridFactor.status != "Archived")
    return jsonify([_row(g) for g in q.order_by(GridFactor.name, GridFactor.year).all()])


@grid_factors_bp.route("", methods=["POST"])
@superuser_required
def create_grid_factor():
    user = get_current_user()
    vals = _parse(request.get_json(silent=True) or {})
    g = GridFactor(**vals, status="Pending", created_by=user.id, tenant_id=get_current_tenant_id(user))
    db.session.add(g)
    db.session.flush()
    log_activity_and_notify(action="CREATE", record_id=str(g.id), user=user, request=request, entity="GridFactor",
                            details=f"Grid factor added: {g.name} {g.year} ({g.co2} kg CO2/kWh, {g.source})",
                            new_values=_row(g))
    db.session.commit()
    clear_grid_cache()
    return jsonify(_row(g)), 201


def _get(gid, user):
    g = db.session.get(GridFactor, gid)
    if g is None or not GridFactor.query.filter(GridFactor.id == gid,
                                                tenant_matches(GridFactor.tenant_id, get_current_tenant_id(user))).first():
        return None
    return g


@grid_factors_bp.route("/<int:gid>", methods=["PUT"])
@superuser_required
def update_grid_factor(gid):
    user = get_current_user()
    g = _get(gid, user)
    if g is None:
        return jsonify({"error": "Grid factor not found"}), 404
    if g.status == "Approved" and user.role != "admin":
        return jsonify({"error": "Only an administrator can change an approved grid factor"}), 403
    vals = _parse(request.get_json(silent=True) or {}, partial=True)
    old = _row(g)
    for k, v in vals.items():
        setattr(g, k, v)
    if any(old.get(k) != getattr(g, k) for k in ("co2", "ch4", "n2o", "year")) and g.status == "Approved":
        g.status, g.approved_by, g.approved_at = "Pending", None, None  # a changed value is approved again
    log_activity_and_notify(action="UPDATE", record_id=str(g.id), user=user, request=request, entity="GridFactor",
                            details=f"Grid factor updated: {g.name} {g.year}", old_values=old, new_values=_row(g))
    db.session.commit()
    clear_grid_cache()
    return jsonify(_row(g))


@grid_factors_bp.route("/<int:gid>/approve", methods=["POST"])
@superuser_required
def approve_grid_factor(gid):
    user = get_current_user()
    g = _get(gid, user)
    if g is None:
        return jsonify({"error": "Grid factor not found"}), 404
    if g.status != "Pending":
        return jsonify({"error": f"Only a pending grid factor can be approved (this one is {g.status})"}), 409
    self_approval = g.created_by == user.id
    if self_approval and user.role != "admin":
        return jsonify({"error": "A grid factor is approved by someone other than its author"}), 403
    g.status, g.approved_by, g.approved_at = "Approved", user.id, datetime.datetime.now(datetime.timezone.utc)
    log_activity_and_notify(action="APPROVE", record_id=str(g.id), user=user, request=request, entity="GridFactor",
                            details=f"Grid factor approved: {g.name} {g.year}"
                            + (" (self-approval by the administrator who created it)" if self_approval else ""))
    db.session.commit()
    clear_grid_cache()
    return jsonify(_row(g))


@grid_factors_bp.route("/<int:gid>/archive", methods=["POST"])
@superuser_required
def archive_grid_factor(gid):
    """Archived, never deleted: records keep the vintage they were calculated with in their stored CO2e."""
    user = get_current_user()
    g = _get(gid, user)
    if g is None:
        return jsonify({"error": "Grid factor not found"}), 404
    if g.status == "Approved" and user.role != "admin":
        return jsonify({"error": "Only an administrator can archive an approved grid factor"}), 403
    g.status = "Archived"
    log_activity_and_notify(action="ARCHIVE", record_id=str(g.id), user=user, request=request, entity="GridFactor",
                            details=f"Grid factor archived: {g.name} {g.year}")
    db.session.commit()
    clear_grid_cache()
    return jsonify(_row(g))


def approved_grid_options(known):
    """Approved administrator-entered grid averages for the Scope 2 grid list (latest year of each name not already
    in the catalog); a record uses the vintage of its own reporting year (GB RY2022 GB-021)."""
    from electricity_factors import grid_factor_kg_co2e_per_kwh

    latest = {}
    for g in GridFactor.query.filter(GridFactor.status == "Approved",
                                     tenant_matches(GridFactor.tenant_id, get_current_tenant_id(get_current_user()))):
        if g.name.lower() not in known and (g.name not in latest or g.year > latest[g.name].year):
            latest[g.name] = g
    return [{"region": g.name, "unit": "kg CO2e/kWh", "description": f"{g.name} ({g.year})", "source": g.source,
             "verified": True,
             "factor": round(grid_factor_kg_co2e_per_kwh({"co2": g.co2, "ch4": g.ch4 or 0.0, "n2o": g.n2o or 0.0}), 6)}
            for g in latest.values()]
