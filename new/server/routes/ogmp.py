"""
UNEP OGMP 2.0 Level 4 / Level 5 REST API Blueprint (/api/ogmp).

Provides full RBAC, tenant-isolated, audit-logged workflows for:
- Official 15 Upstream / 12 Mid-Downstream source catalogs & pathways
- Reporting entities, corporate targets, and JV / NOJV assets
- Source-level disclosures (Quantified / MI / N/A, >10% YoY & zero-emission explanations)
- Site-level measurement campaigns (Instantaneous/Annualized, Option 1/2, 95% CI)
- Full RSS uncertainty propagation, 95% CI overlap & Pathway 1/2a/2b/2c/2d/3 reconciliation
- Y0-Y10 Implementation Plans (3-yr operated / 5-yr non-operated Gold Standard milestones)
- Portfolio 95% equity CH4 materiality & <5% NOJV exclusion computation

Sources, measurements and implementation plans are in routes/ogmp_sources.py; annual reports, reconciliation,
materiality and the audit trail in routes/ogmp_reports.py. Both register on ogmp_bp and use the helpers here.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request
from sqlalchemy import or_

from extensions import db
from input_validation import parse_number, parse_year
from models import (
    Facility,
    OgmpAnnualReport,
    OgmpAsset,
    OgmpAuditTrail,
    OgmpEmissionSource,
    OgmpImplementationPlan,
    OgmpReportingEntity,
    OgmpSiteMeasurement,
    OgmpTarget,
)
from routes.auth import login_required
from services.dashboard_filters import _parse_facility_ids
from services.ogmp_reconciliation import get_source_catalog
from utils import (
    facility_access_error,
    get_allowed_facility_ids,
    get_current_tenant_id,
    get_current_user,
    internal_error,
    is_it_role,
    log_activity_and_notify,
    tenant_matches,
)

ogmp_bp = Blueprint("ogmp", __name__, url_prefix="/api/ogmp")

_FORBIDDEN_IT = ({"error": "Forbidden: IT personnel cannot access operational OGMP data"}, 403)
_FORBIDDEN_WRITE = ({"error": "Forbidden: Read-only auditor and IT roles cannot modify operational OGMP data"}, 403)


def _can_read(user):
    if not user or is_it_role(user):
        return False
    return True


def _can_write(user):
    if not user or is_it_role(user) or user.role == "auditor":
        return False
    return True


def _scoped_query(model, user, allow_null_facility: bool = False):
    tenant_id = get_current_tenant_id(user)
    query = model.query.filter(tenant_matches(model.tenant_id, tenant_id))
    allowed = get_allowed_facility_ids(user)
    if allowed is not None:
        if allow_null_facility:
            query = query.filter(or_(model.facility_id.is_(None), model.facility_id.in_(allowed or [-1])))
        else:
            query = query.filter(model.facility_id.in_(allowed or [-1]))

    fac_arg = request.args.get("facility_id") or request.args.get("facilityId")
    parts = [p.strip() for p in str(fac_arg or "").split(",") if p.strip() and p.strip().lower() != "all"]
    if any(not p.isdigit() for p in parts):
        return None, (jsonify({"error": "Invalid facility_id: must be positive integers", "field": "facility_id"}), 422)
    parsed_fids = _parse_facility_ids(",".join(parts)) if parts else None
    if parsed_fids is not None:
        if allowed is not None and not set(parsed_fids).issubset(set(allowed)):
            return None, (jsonify({"error": "Unauthorized: Outside your assigned facilities"}), 403)
        query = query.filter(model.facility_id.in_(parsed_fids))

    year_arg = request.args.get("year")
    if year_arg and str(year_arg).lower() != "all" and hasattr(model, "year"):
        if not str(year_arg).isdigit():
            return None, (jsonify({"error": "Invalid year parameter", "field": "year"}), 400)
        query = query.filter(model.year == int(year_arg))

    return query, None


def _linked_annual_report_id(data, facility_id: int, tenant_id: str):
    """(id or None, error response): an annual report named in the body must be this facility's own."""
    raw = data.get("annual_report_id")
    if raw in (None, ""):
        return None, None
    try:
        rid = int(raw)
    except (TypeError, ValueError):
        return None, (jsonify({"error": "annual_report_id must be an integer", "field": "annual_report_id"}), 400)
    rep = db.session.get(OgmpAnnualReport, rid)
    if not rep or rep.facility_id != facility_id or rep.tenant_id != tenant_id:
        return None, (jsonify({"error": "Annual report not found for this facility", "field": "annual_report_id"}), 404)
    return rid, None


def _int_field(data, key):
    """(int, None) or (None, 400 response) for a required integer id in the body."""
    try:
        return int(data.get(key)), None
    except (TypeError, ValueError):
        return None, (jsonify({"error": f"{key} must be an integer", "field": key}), 400)


def _record_ogmp_audit(
    user,
    action: str,
    entity_type: str,
    entity_id: Any,
    summary: str,
    *,
    facility_id: Optional[int] = None,
    annual_report_id: Optional[int] = None,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
):
    tenant_id = get_current_tenant_id(user)
    actor_name = getattr(user, "fullName", None) or getattr(user, "email", None) or "System"
    trail = OgmpAuditTrail(
        facility_id=facility_id,
        annual_report_id=annual_report_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        actor_id=getattr(user, "id", None),
        actor_name=actor_name,
        summary=summary,
        before_json=json.dumps(before, default=str) if before is not None else None,
        after_json=json.dumps(after, default=str) if after is not None else None,
        tenant_id=tenant_id,
    )
    db.session.add(trail)
    log_activity_and_notify(
        action=action,
        record_id=str(entity_id),
        user=user,
        request=request,
        entity=entity_type,
        entity_id=str(entity_id),
        facility_id=facility_id,
        details=summary,
    )


def _serialize_entity(e: OgmpReportingEntity) -> Dict[str, Any]:
    return {
        "id": e.id,
        "facility_id": e.facility_id,
        "facility_name": e.facility.name if e.facility else None,
        "entity_name": e.entity_name,
        "asset_name": e.asset_name or "",
        "segment": e.segment or "Upstream",
        "sub_segment": e.sub_segment or "",
        "country": e.country or (e.facility.country if e.facility else "") or "",
        "operator_status": e.operator_status or "operated",
        "operating_company": e.operating_company or "",
        "working_interest_pct": e.working_interest_pct if e.working_interest_pct is not None else 100.0,
        "has_operational_control": bool(e.has_operational_control),
        "membership_year": e.membership_year or 2023,
        "target_gold_year": e.target_gold_year or ((e.membership_year or 2023) + (3 if (e.operator_status or "operated") == "operated" else 5)),
        "is_nojv_material_excluded": bool(e.is_nojv_material_excluded),
        "exclusion_reason": e.exclusion_reason or "",
        "is_member_reported_nojv": bool(e.is_member_reported_nojv),
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _serialize_target(t: OgmpTarget) -> Dict[str, Any]:
    return {
        "id": t.id,
        "reporting_entity_id": t.reporting_entity_id,
        "entity_name": t.reporting_entity.entity_name if t.reporting_entity else None,
        "target_year": t.target_year,
        "metric_type": t.metric_type,
        "upstream_target_pct": t.upstream_target_pct,
        "midstream_target_pct": t.midstream_target_pct,
        "reduction_target_pct": t.reduction_target_pct,
        "base_year": t.base_year,
        "notes": t.notes or "",
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _serialize_asset(a: OgmpAsset) -> Dict[str, Any]:
    return {
        "id": a.id,
        "reporting_entity_id": a.reporting_entity_id,
        "facility_id": a.facility_id,
        "facility_name": a.facility.name if a.facility else None,
        "asset_code": a.asset_code or "",
        "asset_name": a.asset_name,
        "asset_type": a.asset_type or "",
        "segment": a.segment or "Upstream",
        "operator_status": a.operator_status or "operated",
        "equity_share_pct": a.equity_share_pct if a.equity_share_pct is not None else 100.0,
        "is_nojv": bool(a.is_nojv),
        "is_excluded_below_5pct": bool(a.is_excluded_below_5pct),
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_source(s: OgmpEmissionSource) -> Dict[str, Any]:
    return {
        "id": s.id,
        "facility_id": s.facility_id,
        "facility_name": s.facility.name if s.facility else None,
        "annual_report_id": s.annual_report_id,
        "year": s.year,
        "segment": s.segment,
        "source_code": s.source_code,
        "source_name": s.source_name,
        "source_category": s.source_category or "Fugitive",
        "ogmp_level": s.ogmp_level,
        "status_flag": s.status_flag,
        "ch4_tonnes": s.ch4_tonnes,
        "uncertainty_pct": s.uncertainty_pct,
        "emission_factor_ref": s.emission_factor_ref or "",
        "quantification_method": s.quantification_method or "",
        "pathway_code": s.pathway_code,
        "yoy_change_pct": s.yoy_change_pct,
        "yoy_explanation": s.yoy_explanation or "",
        "zero_emission_explanation": s.zero_emission_explanation or "",
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _serialize_measurement(m: OgmpSiteMeasurement) -> Dict[str, Any]:
    return {
        "id": m.id,
        "facility_id": m.facility_id,
        "facility_name": m.facility.name if m.facility else None,
        "annual_report_id": m.annual_report_id,
        "year": m.year,
        "campaign_date": m.campaign_date,
        "survey_type": m.survey_type,
        "instrument_vendor": m.instrument_vendor or "",
        "measurement_mode": m.measurement_mode or "Annualized",
        "option_mode": m.option_mode or "Option 1",
        "measured_rate_kg_hr": m.measured_rate_kg_hr,
        "operating_hours_year": m.operating_hours_year,
        "annualized_tch4": m.annualized_tch4,
        "uncertainty_pct": m.uncertainty_pct,
        "ci_low_tch4": m.ci_low_tch4,
        "ci_high_tch4": m.ci_high_tch4,
        "detection_threshold_kg_hr": m.detection_threshold_kg_hr,
        "meteorological_notes": m.meteorological_notes or "",
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


def _serialize_plan(p: OgmpImplementationPlan) -> Dict[str, Any]:
    return {
        "id": p.id,
        "facility_id": p.facility_id,
        "facility_name": p.facility.name if p.facility else None,
        "reporting_entity_id": p.reporting_entity_id,
        "asset_name": p.asset_name or (p.facility.name if p.facility else ""),
        "operator_status": p.operator_status or "operated",
        "base_year": p.base_year,
        "milestone_horizon": p.milestone_horizon,
        "planned_year": p.planned_year,
        "target_level": p.target_level,
        "actual_level": p.actual_level,
        "source_scope": p.source_scope or "",
        "methodology_upgrade": p.methodology_upgrade or "",
        "milestone_status": p.milestone_status or "Planned",
        "justification": p.justification or "",
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _serialize_annual_report(r: OgmpAnnualReport) -> Dict[str, Any]:
    return {
        "id": r.id,
        "facility_id": r.facility_id,
        "facility_name": r.facility.name if r.facility else None,
        "reporting_entity_id": r.reporting_entity_id,
        "year": r.year,
        "reporting_level": r.reporting_level,
        "status": r.status,
        "total_bottom_up_tch4": r.total_bottom_up_tch4,
        "total_top_down_tch4": r.total_top_down_tch4,
        "bu_uncertainty_pct": r.bu_uncertainty_pct,
        "bu_ci_low_tch4": r.bu_ci_low_tch4,
        "bu_ci_high_tch4": r.bu_ci_high_tch4,
        "td_uncertainty_pct": r.td_uncertainty_pct,
        "td_ci_low_tch4": r.td_ci_low_tch4,
        "td_ci_high_tch4": r.td_ci_high_tch4,
        "ci_overlaps": bool(r.ci_overlaps),
        "variance_pct": r.variance_pct,
        "variance_flag": bool(r.variance_flag),
        "reconciliation_status": r.reconciliation_status,
        "l4_materiality_pct": r.l4_materiality_pct,
        "l4_justification": r.l4_justification or "",
        "pathway_code": r.pathway_code,
        "measurement_mode": r.measurement_mode,
        "option_mode": r.option_mode,
        "gas_production_m3": r.gas_production_m3,
        "ch4_intensity_pct": r.ch4_intensity_pct,
        "equity_ch4_tch4": r.equity_ch4_tch4,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


# ---------------------------------------------------------------------------
# Catalogs
# ---------------------------------------------------------------------------
@ogmp_bp.route("/catalogs", methods=["GET"])
@login_required
def get_ogmp_catalogs():
    user = get_current_user()
    if not _can_read(user):
        return jsonify(_FORBIDDEN_IT[0]), 403
    return jsonify(get_source_catalog(request.args.get("segment")))


# ---------------------------------------------------------------------------
# Reporting Entities
# ---------------------------------------------------------------------------
@ogmp_bp.route("/entities", methods=["GET"])
@login_required
def list_entities():
    user = get_current_user()
    if not _can_read(user):
        return jsonify(_FORBIDDEN_IT[0]), 403
    q, err = _scoped_query(OgmpReportingEntity, user, allow_null_facility=True)
    if err:
        return err
    return jsonify([_serialize_entity(e) for e in q.order_by(OgmpReportingEntity.id.desc()).all()])


@ogmp_bp.route("/entities", methods=["POST"])
@login_required
def create_entity():
    user = get_current_user()
    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    data = request.get_json() or {}
    entity_name = str(data.get("entity_name") or "").strip()
    if not entity_name:
        return jsonify({"error": "entity_name is required", "field": "entity_name"}), 400

    fid = data.get("facility_id")
    if fid not in (None, ""):
        if (denied := facility_access_error(user, fid)):
            return denied
        fid = int(fid)
        fac = db.session.get(Facility, fid)
    else:
        fid = None
        fac = None

    op_status = str(data.get("operator_status") or (fac.operator_status if fac else "operated")).strip().lower()
    if op_status not in ("operated", "non_operated"):
        return jsonify({"error": "operator_status must be 'operated' or 'non_operated'", "field": "operator_status"}), 400

    wi = parse_number(data.get("working_interest_pct", (fac.equity_share_pct if fac else 100.0)), "working_interest_pct", required=False, min_value=0.0, max_value=100.0, default=100.0)
    m_year = parse_year(data.get("membership_year", (fac.ogmp_membership_year if fac else 2023)), required=False) or 2023
    gold_year = parse_year(data.get("target_gold_year"), required=False) or (m_year + (3 if op_status == "operated" else 5))

    is_excl = bool(data.get("is_nojv_material_excluded", False))
    excl_reason = str(data.get("exclusion_reason") or "").strip()
    if is_excl and op_status == "operated":
        return jsonify({"error": "Operated assets cannot be excluded under NOJV materiality exemption", "field": "is_nojv_material_excluded"}), 400
    if is_excl and not excl_reason:
        return jsonify({"error": "exclusion_reason is required when excluding a non-operated JV", "field": "exclusion_reason"}), 400

    ent = OgmpReportingEntity(
        facility_id=fid,
        entity_name=entity_name,
        asset_name=str(data.get("asset_name") or (fac.name if fac else entity_name)).strip(),
        segment=str(data.get("segment") or (fac.segment if fac else "Upstream")).strip(),
        sub_segment=str(data.get("sub_segment") or "").strip(),
        country=str(data.get("country") or (fac.country if fac else "") or "").strip(),
        operator_status=op_status,
        operating_company=str(data.get("operating_company") or "").strip(),
        working_interest_pct=wi,
        has_operational_control=bool(data.get("has_operational_control", op_status == "operated")),
        membership_year=m_year,
        target_gold_year=gold_year,
        is_nojv_material_excluded=is_excl,
        exclusion_reason=excl_reason,
        is_member_reported_nojv=bool(data.get("is_member_reported_nojv", False)),
        tenant_id=get_current_tenant_id(user),
        created_by=user.id,
    )
    try:
        db.session.add(ent)
        db.session.flush()
        _record_ogmp_audit(
            user, "CREATE", "OgmpReportingEntity", ent.id,
            f"Created OGMP reporting entity '{ent.entity_name}' ({ent.operator_status}, WI={ent.working_interest_pct}%)",
            facility_id=ent.facility_id, after=_serialize_entity(ent),
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to save OGMP reporting entity")
    return jsonify(_serialize_entity(ent)), 201


@ogmp_bp.route("/entities/<int:entity_id>", methods=["PUT", "DELETE"])
@login_required
def mutate_entity(entity_id: int):
    user = get_current_user()
    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    ent = db.session.get(OgmpReportingEntity, entity_id)
    if not ent:
        return jsonify({"error": "Reporting entity not found"}), 404
    if ent.tenant_id != get_current_tenant_id(user):
        return jsonify({"error": "Unauthorized"}), 403
    if ent.facility_id and (denied := facility_access_error(user, ent.facility_id)):
        return denied

    if request.method == "DELETE":
        before = _serialize_entity(ent)
        try:
            fid = ent.facility_id
            db.session.delete(ent)
            _record_ogmp_audit(user, "DELETE", "OgmpReportingEntity", entity_id, f"Deleted reporting entity '{before['entity_name']}'", facility_id=fid, before=before)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return internal_error(e, "Failed to delete reporting entity")
        return jsonify({"message": "Reporting entity deleted"})

    data = request.get_json() or {}
    before = _serialize_entity(ent)
    if "entity_name" in data and str(data["entity_name"]).strip():
        ent.entity_name = str(data["entity_name"]).strip()
    if "asset_name" in data:
        ent.asset_name = str(data["asset_name"] or "").strip()
    if "segment" in data and data["segment"]:
        ent.segment = str(data["segment"]).strip()
    if "sub_segment" in data:
        ent.sub_segment = str(data["sub_segment"] or "").strip()
    if "country" in data:
        ent.country = str(data["country"] or "").strip()
    if "operator_status" in data:
        op_st = str(data["operator_status"] or "").strip().lower()
        if op_st not in ("operated", "non_operated"):
            return jsonify({"error": "Invalid operator_status"}), 400
        ent.operator_status = op_st
    if "operating_company" in data:
        ent.operating_company = str(data["operating_company"] or "").strip()
    if "working_interest_pct" in data:
        ent.working_interest_pct = parse_number(data["working_interest_pct"], "working_interest_pct", min_value=0.0, max_value=100.0)
    if "has_operational_control" in data:
        ent.has_operational_control = bool(data["has_operational_control"])
    if "is_nojv_material_excluded" in data:
        ent.is_nojv_material_excluded = bool(data["is_nojv_material_excluded"])
    if "exclusion_reason" in data:
        ent.exclusion_reason = str(data["exclusion_reason"] or "").strip()
    if "is_member_reported_nojv" in data:
        ent.is_member_reported_nojv = bool(data["is_member_reported_nojv"])
    if ent.is_nojv_material_excluded and ent.operator_status == "operated":
        return jsonify({"error": "Operated assets cannot be excluded under NOJV materiality exemption"}), 400
    if ent.is_nojv_material_excluded and not (ent.exclusion_reason or "").strip():
        return jsonify({"error": "exclusion_reason is required when excluding a non-operated JV"}), 400

    try:
        after = _serialize_entity(ent)
        _record_ogmp_audit(user, "UPDATE", "OgmpReportingEntity", ent.id, f"Updated OGMP reporting entity '{ent.entity_name}'", facility_id=ent.facility_id, before=before, after=after)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to update reporting entity")
    return jsonify(_serialize_entity(ent))


# ---------------------------------------------------------------------------
# Targets & Assets
# ---------------------------------------------------------------------------
@ogmp_bp.route("/targets", methods=["GET"])
@login_required
def list_targets():
    user = get_current_user()
    if not _can_read(user):
        return jsonify(_FORBIDDEN_IT[0]), 403
    tenant_id = get_current_tenant_id(user)
    rows = OgmpTarget.query.filter(tenant_matches(OgmpTarget.tenant_id, tenant_id)).order_by(OgmpTarget.target_year.asc()).all()
    return jsonify([_serialize_target(t) for t in rows])


@ogmp_bp.route("/targets", methods=["POST"])
@login_required
def create_target():
    user = get_current_user()
    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    data = request.get_json() or {}
    if not data.get("reporting_entity_id"):
        return jsonify({"error": "reporting_entity_id is required", "field": "reporting_entity_id"}), 400
    ent_id, err = _int_field(data, "reporting_entity_id")
    if err:
        return err
    ent = db.session.get(OgmpReportingEntity, ent_id)
    if not ent or ent.tenant_id != get_current_tenant_id(user):
        return jsonify({"error": "Reporting entity not found"}), 404
    if ent.facility_id and (denied := facility_access_error(user, ent.facility_id)):
        return denied

    t_year = parse_year(data.get("target_year", 2026))
    b_year = parse_year(data.get("base_year", ent.membership_year or 2023), required=False) or 2023
    up_pct = parse_number(data.get("upstream_target_pct", 0.20), "upstream_target_pct", required=False, min_value=0.0, max_value=100.0, default=0.20)
    mid_pct = parse_number(data.get("midstream_target_pct", 0.05), "midstream_target_pct", required=False, min_value=0.0, max_value=100.0, default=0.05)
    red_pct = parse_number(data.get("reduction_target_pct", 0.0), "reduction_target_pct", required=False, min_value=0.0, max_value=100.0, default=0.0)

    target = OgmpTarget(
        reporting_entity_id=ent.id,
        target_year=t_year,
        metric_type=str(data.get("metric_type") or "methane_intensity").strip(),
        upstream_target_pct=up_pct,
        midstream_target_pct=mid_pct,
        reduction_target_pct=red_pct,
        base_year=b_year,
        notes=str(data.get("notes") or "").strip(),
        tenant_id=get_current_tenant_id(user),
        created_by=user.id,
    )
    try:
        db.session.add(target)
        db.session.flush()
        _record_ogmp_audit(user, "CREATE", "OgmpTarget", target.id, f"Added OGMP target {t_year} for '{ent.entity_name}'", facility_id=ent.facility_id, after=_serialize_target(target))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to save OGMP target")
    return jsonify(_serialize_target(target)), 201


@ogmp_bp.route("/targets/<int:target_id>", methods=["DELETE"])
@login_required
def delete_target(target_id: int):
    user = get_current_user()
    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    target = db.session.get(OgmpTarget, target_id)
    if not target or target.tenant_id != get_current_tenant_id(user):
        return jsonify({"error": "Target not found"}), 404
    ent = target.reporting_entity
    if ent and ent.facility_id and (denied := facility_access_error(user, ent.facility_id)):
        return denied
    try:
        db.session.delete(target)
        _record_ogmp_audit(user, "DELETE", "OgmpTarget", target_id, f"Deleted OGMP target #{target_id}", facility_id=ent.facility_id if ent else None)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to delete target")
    return jsonify({"message": "Target deleted"})


@ogmp_bp.route("/assets", methods=["GET", "POST"])
@login_required
def assets_collection():
    user = get_current_user()
    if request.method == "GET":
        if not _can_read(user):
            return jsonify(_FORBIDDEN_IT[0]), 403
        q, err = _scoped_query(OgmpAsset, user)
        if err:
            return err
        return jsonify([_serialize_asset(a) for a in q.order_by(OgmpAsset.id.asc()).all()])

    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    data = request.get_json() or {}
    fid = data.get("facility_id")
    if (denied := facility_access_error(user, fid)):
        return denied
    fid = int(fid)
    if not data.get("reporting_entity_id"):
        return jsonify({"error": "reporting_entity_id is required", "field": "reporting_entity_id"}), 400
    ent_id, err = _int_field(data, "reporting_entity_id")
    if err:
        return err
    ent = db.session.get(OgmpReportingEntity, ent_id)
    if not ent or ent.tenant_id != get_current_tenant_id(user):
        return jsonify({"error": "Reporting entity not found"}), 404

    asset = OgmpAsset(
        reporting_entity_id=ent.id,
        facility_id=fid,
        asset_code=str(data.get("asset_code") or "").strip(),
        asset_name=str(data.get("asset_name") or "").strip() or (db.session.get(Facility, fid).name),
        asset_type=str(data.get("asset_type") or "").strip(),
        segment=str(data.get("segment") or ent.segment or "Upstream").strip(),
        operator_status=str(data.get("operator_status") or ent.operator_status or "operated").strip().lower(),
        equity_share_pct=parse_number(data.get("equity_share_pct", 100.0), "equity_share_pct", required=False, min_value=0.0, max_value=100.0, default=100.0),
        is_nojv=bool(data.get("is_nojv", ent.operator_status == "non_operated")),
        is_excluded_below_5pct=bool(data.get("is_excluded_below_5pct", False)),
        tenant_id=get_current_tenant_id(user),
    )
    try:
        db.session.add(asset)
        db.session.flush()
        _record_ogmp_audit(user, "CREATE", "OgmpAsset", asset.id, f"Registered OGMP asset '{asset.asset_name}'", facility_id=fid, after=_serialize_asset(asset))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to save OGMP asset")
    return jsonify(_serialize_asset(asset)), 201


# Route modules split out of this file; imported last because they use the helpers above.
from routes import ogmp_reports, ogmp_sources  # noqa: E402,F401
