"""OGMP 2.0 routes on ogmp_bp: annual reports, L4/L5 reconciliation, portfolio materiality and the OGMP audit
trail (split from routes/ogmp.py, which holds the blueprint, access checks and serializers)."""

from __future__ import annotations

import json
from typing import Dict
from models import (
    Emission,
    Facility,
    OgmpAnnualReport,
    OgmpAssetReport,
    OgmpAuditTrail,
    OgmpEmissionSource,
    OgmpReportingEntity,
    OgmpSiteMeasurement,
    ProductionData,
)
from services.ogmp_reconciliation import (
    VALID_OPTION_MODES,
    VALID_PATHWAYS,
    compute_portfolio_materiality,
    reconcile_l4_l5,
)
from routes.ogmp import (
    _FORBIDDEN_IT,
    _FORBIDDEN_WRITE,
    _can_read,
    _can_write,
    _record_ogmp_audit,
    _scoped_query,
    _serialize_annual_report,
    ogmp_bp,
)
from extensions import db
from utils import (
    facility_access_error,
    get_current_tenant_id,
    get_current_user,
    internal_error,
    tenant_matches,
)
from sqlalchemy import func
from flask import jsonify, request
from routes.auth import login_required
from input_validation import parse_number, parse_year
from services.dashboard_filters import production_gas_m3


# ---------------------------------------------------------------------------
# Annual Reconciliation Engine (RSS 95% CI Overlap, Materiality, Pathway 1-3)
# ---------------------------------------------------------------------------
@ogmp_bp.route("/annual-reports", methods=["GET"])
@login_required
def list_annual_reports():
    user = get_current_user()
    if not _can_read(user):
        return jsonify(_FORBIDDEN_IT[0]), 403
    q, err = _scoped_query(OgmpAnnualReport, user)
    if err:
        return err
    rows = q.order_by(OgmpAnnualReport.year.desc(), OgmpAnnualReport.id.desc()).all()
    return jsonify([_serialize_annual_report(r) for r in rows])


@ogmp_bp.route("/reconcile", methods=["POST"])
@login_required
def run_l4_l5_reconciliation():
    user = get_current_user()
    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    data = request.get_json() or {}
    fid = data.get("facility_id") or data.get("facilityId")
    if (denied := facility_access_error(user, fid)):
        return denied
    fid = int(fid)
    fac = db.session.get(Facility, fid)
    year = parse_year(data.get("year"))
    tenant_id = get_current_tenant_id(user)

    l4_just = str(data.get("l4_justification") or "").strip()
    opt_mode = data.get("option_mode")
    if opt_mode and opt_mode not in VALID_OPTION_MODES:
        return jsonify({"error": f"option_mode must be one of: {', '.join(VALID_OPTION_MODES)}"}), 400
    pathway_override = data.get("pathway_code")
    if pathway_override and str(pathway_override).strip() not in VALID_PATHWAYS:
        return jsonify({"error": f"pathway_code must be one of: {', '.join(VALID_PATHWAYS)}"}), 400

    sources = OgmpEmissionSource.query.filter_by(facility_id=fid, year=year, tenant_id=tenant_id).all()
    measurements = OgmpSiteMeasurement.query.filter_by(facility_id=fid, year=year, tenant_id=tenant_id).all()
    threshold = parse_number(data.get("threshold_pct", fac.reconciliation_threshold or 20.0), "threshold_pct", required=False, min_value=0.1, max_value=200.0, default=20.0)

    result = reconcile_l4_l5(
        sources,
        measurements,
        threshold_pct=threshold,
        l4_justification=l4_just,
        option_mode=opt_mode,
        pathway_override=str(pathway_override).strip() if pathway_override else None,
    )

    prods = ProductionData.query.filter_by(facility_id=fid, year=year).all()
    gas_m3 = sum(production_gas_m3(p) or 0.0 for p in prods)
    bu_ch4 = result["bottom_up"]["total_tch4"]
    # CH4 density 16.04 / 23.685 kg/m3, as the intensity service (it was 0.678, BA-048)
    from services.intensity import CH4_DENSITY_KG_M3
    intensity_pct = round(((bu_ch4 * 1000.0 / CH4_DENSITY_KG_M3) / gas_m3) * 100.0, 4) if gas_m3 > 0 and bu_ch4 > 0 else None
    wi = float(fac.equity_share_pct if fac.equity_share_pct is not None else 100.0)
    equity_ch4 = round(bu_ch4 * (wi / 100.0), 4)

    ent = OgmpReportingEntity.query.filter_by(facility_id=fid, tenant_id=tenant_id).first()

    report = OgmpAnnualReport.query.filter_by(facility_id=fid, year=year, tenant_id=tenant_id).first()
    is_new = report is None
    before = _serialize_annual_report(report) if report else None
    if report is None:
        report = OgmpAnnualReport(facility_id=fid, year=year, tenant_id=tenant_id, created_by=user.id)
        db.session.add(report)

    report.reporting_entity_id = ent.id if ent else None
    report.reporting_level = result["reporting_level"]
    # a reconciliation is the maker's work: it awaits review and is never self-approved, so a
    # "status" sent with the request is not used
    report.status = "Pending"
    report.total_bottom_up_tch4 = result["bottom_up"]["total_tch4"]
    report.total_top_down_tch4 = result["top_down"]["total_tch4"]
    report.bu_uncertainty_pct = result["bottom_up"]["uncertainty_pct"]
    report.bu_ci_low_tch4 = result["bottom_up"]["ci_low_tch4"]
    report.bu_ci_high_tch4 = result["bottom_up"]["ci_high_tch4"]
    report.td_uncertainty_pct = result["top_down"]["uncertainty_pct"]
    report.td_ci_low_tch4 = result["top_down"]["ci_low_tch4"]
    report.td_ci_high_tch4 = result["top_down"]["ci_high_tch4"]
    report.ci_overlaps = result["ci_overlaps"]
    report.variance_pct = result["variance_pct"]
    report.variance_flag = result["variance_flag"]
    report.reconciliation_status = result["reconciliation_status"]
    report.l4_materiality_pct = result["materiality"]["l4_materiality_pct"]
    report.l4_justification = l4_just
    report.pathway_code = result["pathway_code"]
    report.measurement_mode = result["top_down"]["measurement_mode"]
    report.option_mode = result["top_down"]["option_mode"]
    report.gas_production_m3 = round(gas_m3, 2)
    report.ch4_intensity_pct = intensity_pct
    report.equity_ch4_tch4 = equity_ch4

    try:
        db.session.flush()
        for src in sources:
            src.annual_report_id = report.id
        for meas in measurements:
            meas.annual_report_id = report.id

        asset_rep = OgmpAssetReport.query.filter_by(annual_report_id=report.id, facility_id=fid).first()
        if asset_rep is None:
            asset_rep = OgmpAssetReport(
                annual_report_id=report.id,
                facility_id=fid,
                year=year,
                tenant_id=tenant_id,
            )
            db.session.add(asset_rep)
        asset_rep.ogmp_level = report.reporting_level
        asset_rep.bottom_up_tch4 = report.total_bottom_up_tch4
        asset_rep.top_down_tch4 = report.total_top_down_tch4
        asset_rep.bu_ci_low_tch4 = report.bu_ci_low_tch4
        asset_rep.bu_ci_high_tch4 = report.bu_ci_high_tch4
        asset_rep.td_ci_low_tch4 = report.td_ci_low_tch4
        asset_rep.td_ci_high_tch4 = report.td_ci_high_tch4
        asset_rep.variance_pct = report.variance_pct
        asset_rep.reconciliation_status = report.reconciliation_status
        asset_rep.l4_coverage_pct = report.l4_materiality_pct
        asset_rep.gas_throughput_m3 = report.gas_production_m3
        asset_rep.ch4_intensity_pct = report.ch4_intensity_pct

        after = _serialize_annual_report(report)
        _record_ogmp_audit(
            user,
            "RECONCILE_CREATE" if is_new else "RECONCILE_UPDATE",
            "OgmpAnnualReport",
            report.id,
            f"Reconciled OGMP 2.0 Level {report.reporting_level} ({report.reconciliation_status}, Pathway {report.pathway_code}, L4={report.l4_materiality_pct}%) for facility #{fid} ({year})",
            facility_id=fid,
            annual_report_id=report.id,
            before=before,
            after=after,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to persist annual OGMP reconciliation")

    return jsonify({**result, "annual_report": _serialize_annual_report(report)}), 200


# ---------------------------------------------------------------------------
# Portfolio 95% Equity Materiality & Audit Trail
# ---------------------------------------------------------------------------
@ogmp_bp.route("/portfolio-materiality", methods=["GET"])
@login_required
def get_portfolio_materiality():
    user = get_current_user()
    if not _can_read(user):
        return jsonify(_FORBIDDEN_IT[0]), 403
    q, err = _scoped_query(OgmpReportingEntity, user, allow_null_facility=True)
    if err:
        return err
    entities = q.order_by(OgmpReportingEntity.id.asc()).all()

    year_arg = request.args.get("year")
    year_filter = int(year_arg) if year_arg and str(year_arg).isdigit() else None
    tenant_id = get_current_tenant_id(user)

    fids = [e.facility_id for e in entities if e.facility_id]
    facility_ch4_map: Dict[int, float] = {}
    if fids:
        # 1. Prefer OgmpEmissionSource quantified totals for facility/year
        sq = db.session.query(
            OgmpEmissionSource.facility_id,
            func.sum(OgmpEmissionSource.ch4_tonnes),
        ).filter(
            OgmpEmissionSource.facility_id.in_(fids),
            tenant_matches(OgmpEmissionSource.tenant_id, tenant_id),
            OgmpEmissionSource.status_flag == "Quantified",
        )
        if year_filter:
            sq = sq.filter(OgmpEmissionSource.year == year_filter)
        for fid, val in sq.group_by(OgmpEmissionSource.facility_id).all():
            if val:
                facility_ch4_map[fid] = float(val)

        # 2. Fallback to Verified Emission CH4 for facilities without OgmpEmissionSource rows
        missing = [fid for fid in fids if fid not in facility_ch4_map]
        if missing:
            eq = db.session.query(
                Emission.facility_id,
                func.sum(Emission.ch4_emissions),
            ).filter(
                Emission.facility_id.in_(missing),
                Emission.status == "Verified",
            )
            if year_filter:
                eq = eq.filter(Emission.year == year_filter)
            for fid, val in eq.group_by(Emission.facility_id).all():
                if val:
                    facility_ch4_map[fid] = float(val)

    return jsonify(compute_portfolio_materiality(entities, facility_ch4_map))


@ogmp_bp.route("/audit-trail", methods=["GET"])
@login_required
def list_ogmp_audit_trail():
    user = get_current_user()
    if not _can_read(user):
        return jsonify(_FORBIDDEN_IT[0]), 403
    q, err = _scoped_query(OgmpAuditTrail, user, allow_null_facility=True)
    if err:
        return err
    rows = q.order_by(OgmpAuditTrail.created_at.desc(), OgmpAuditTrail.id.desc()).limit(200).all()
    return jsonify([
        {
            "id": r.id,
            "facility_id": r.facility_id,
            "facility_name": r.facility.name if r.facility else None,
            "annual_report_id": r.annual_report_id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "action": r.action,
            "actor_id": r.actor_id,
            "actor_name": r.actor_name or "",
            "summary": r.summary,
            "before": json.loads(r.before_json) if r.before_json else None,
            "after": json.loads(r.after_json) if r.after_json else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ])
