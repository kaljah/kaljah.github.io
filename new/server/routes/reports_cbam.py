"""
European Commission DG TAXUD CBAM Official Communication Template, Pre-Export Validation & XML Registry Generator.
Complies strictly with Regulation (EU) 2023/956 and Implementing Regulation (EU) 2023/1773.
"""

import io
from flask import request, send_file, jsonify, current_app

from models import Facility, CbamProductExport
from routes.auth import login_required
from services.audit_chain import record_report_fingerprint
from services.cbam_data import (  # noqa: F401
    CbamContext,
    _cbam_family,
    _clean_xml_text,
    _get_facility_production_tonnes,
    _get_facility_scope1_split,
    _get_facility_scope2_metrics,
    _production_tonnes,
    get_cbam_aggregated_category,
    get_cbam_production_route,
    quarter_of,
    validate_cbam_context,
)
from services.report_params import report_facility, report_quarter, report_statuses, report_year
from utils import get_allowed_facility_ids, get_current_tenant_id, get_current_user, tenant_matches
from routes.reports import _safe_excel_value, reports_bp


def _scoped_query(model, allowed_fids, facility_filter, caller_tenant="default", id_column="facility_id"):
    q = model.query
    if hasattr(model, "tenant_id"):
        q = q.filter(tenant_matches(model.tenant_id, caller_tenant))
    column = getattr(model, id_column)
    if allowed_fids is not None:
        q = q.filter(column.in_(allowed_fids or [-1]))
    if facility_filter:
        q = q.filter(column == facility_filter)
    return q


def _load_cbam_context(user):
    year = request.args.get("year", "all")
    year_filter = report_year(year)
    facility_filter = report_facility(request.args.get("facility_id") or request.args.get("facilityId"))
    statuses = report_statuses(request.args.get("status"))
    quarter = report_quarter(request.args.get("quarter"))

    allowed_fids = get_allowed_facility_ids(user)
    if facility_filter is not None and allowed_fids is not None and facility_filter not in allowed_fids:
        return None, None, (jsonify({"error": "Unauthorized facility"}), 403)

    caller_tenant = get_current_tenant_id(user)
    facilities = {
        f.id: f
        for f in _scoped_query(Facility, allowed_fids, facility_filter, caller_tenant, "id").all()
    }
    cbam_q = _scoped_query(CbamProductExport, allowed_fids, facility_filter, caller_tenant)
    cbam_q = cbam_q.filter(CbamProductExport.facility_id.in_(facilities.keys() or [-1]))
    if year_filter:
        cbam_q = cbam_q.filter_by(year=year_filter)
    records = cbam_q.order_by(
        CbamProductExport.year.desc(),
        CbamProductExport.month.desc(),
        CbamProductExport.id.asc(),
    ).all()
    if quarter in ("Q1", "Q2", "Q3", "Q4"):
        records = [r for r in records if quarter_of(r) == quarter]

    ctx = CbamContext(user, year_filter, statuses, facilities, records, _safe_excel_value, quarter=quarter)
    return ctx, year, None


@reports_bp.route("/cbam-validate", methods=["GET"])
@reports_bp.route("/cbam-validate/", methods=["GET"])
@login_required
def validate_cbam_report():
    """Pre-export validation checklist & completeness audit for EU CBAM submissions."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "Forbidden: IT personnel cannot access operational compliance reports"}), 403

    ctx, _year, err = _load_cbam_context(user)
    if err:
        return err
    return jsonify(validate_cbam_context(ctx)), 200


@reports_bp.route("/cbam-export", methods=["GET"])
@reports_bp.route("/cbam-export/", methods=["GET"])
@login_required
def export_cbam_report():
    """
    Generates the official EU CBAM Communication Template under Regulation (EU) 2023/956
    and Implementing Regulation (EU) 2023/1773.
    Supports ?format=excel (default) or ?format=xml, and strict ?quarter=Q1|Q2|Q3|Q4|Q1-Q4|all.
    """
    from services.cbam_workbook import build_workbook
    from services.cbam_xml import build_xml

    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "Forbidden: IT personnel cannot access operational compliance reports"}), 403

    export_format = request.args.get("format", "excel").lower()
    if export_format not in ("excel", "xml", "xlsx"):
        return jsonify({"error": f"Unsupported export format '{export_format}'. Supported formats: 'excel', 'xml'"}), 400

    ctx, year, err = _load_cbam_context(user)
    if err:
        return err

    try:
        q_str = ctx.quarter if ctx.quarter and str(ctx.quarter).lower() not in ("none", "all", "") else "FullYear"
        if export_format == "xml":
            data, sha256 = build_xml(ctx, ctx.quarter)
            buffer, mimetype, label = io.BytesIO(data), "application/xml", "EU CBAM XML Declaration"
            filename = f"CBAM_Transitional_Declaration_{ctx.rep_year_str}_{q_str}.xml"
        else:
            wb, sha256 = build_workbook(ctx)
            buffer = io.BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            label = "EU CBAM Communication Template"
            filename = f"EU_CBAM_Communication_Template_{ctx.rep_year_str}_{q_str}.xlsx"

        resp = send_file(buffer, mimetype=mimetype, as_attachment=True, download_name=filename)
        record_report_fingerprint(resp, user, label, {"year": year, "quarter": ctx.quarter}, len(ctx.records), sha256)
        resp.headers["X-Audit-Timestamp"] = ctx.now_utc.isoformat()
        resp.headers["X-Audit-SHA256"] = sha256
        return resp

    except Exception as e:
        current_app.logger.error(f"Error generating CBAM report: {e}", exc_info=True)
        return jsonify({"error": "CBAM report export failed. Please try again or contact support."}), 500
