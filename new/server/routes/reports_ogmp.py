"""UNEP OGMP 2.0 Official Annual Member Submission Template & Excel Export Route.

Generates the 100% compliant, 8-sheet UNEP / IMEO OGMP 2.0 Member Disclosure Workbook:
0. Company Profile & Declaration (UNEP IMEO official metadata)
1. Executive Summary & Operated Assets (Facility overview, production, loss rates)
2. Bottom-Up Inventory (L1-L4 source emissions with API Compendium 2021 factors)
3. Top-Down Surveys (L4/L5 site-level measurement campaigns & technologies)
4. Reconciliation Matrix (Bottom-Up vs Top-Down variance, thresholds & discrepancy flags)
5. Gold Standard Roadmap (3-year operated / 5-year non-operated compliance milestones)
6. Level 4 Direct Measurements (Source-level direct measurement & component uncertainty)
7. Non-Operated Assets (JV) (Joint venture working interest & equity disclosures)
Audit Assurance (Cryptographic SHA-256 data fingerprint & digital seal)
"""
import io
from datetime import datetime, timezone
from flask import current_app, jsonify, request, send_file

from models import Facility
from routes.auth import login_required
from services.audit_chain import record_report_fingerprint
from services.ogmp_workbook import Context, build_workbook
from utils import get_allowed_facility_ids, get_current_user
from routes.reports import _CH4_DENSITY, _safe_excel_value, reports_bp


@reports_bp.route("/ogmp-export", methods=["GET"])
@login_required
def export_ogmp_excel():
    """
    Generates the official UNEP / IMEO OGMP 2.0 Standard Annual Member Disclosure Workbook.
    Complies with UNEP OGMP 2.0 Technical Guidance Document (TGD 2024/2025). The sheets are built by
    services.ogmp_workbook.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return (
            jsonify(
                {"error": "Forbidden: IT personnel cannot access operational emission reports"}
            ),
            403,
        )

    try:
        allowed_fids = get_allowed_facility_ids(user)

        year = request.args.get("year", "all")
        year_filter = int(year) if year and year.isdigit() and year != "all" else None
        facility_id = request.args.get("facility_id") or request.args.get("facilityId")
        facility_filter = (
            int(facility_id) if facility_id and facility_id.isdigit() and facility_id != "all" else None
        )

        if (
            facility_filter is not None
            and allowed_fids is not None
            and facility_filter not in allowed_fids
        ):
            return jsonify({"error": "Unauthorized facility"}), 403

        ctx = Context(user, year, year_filter, facility_filter, allowed_fids,
                      _facilities(allowed_fids, facility_filter), _safe_excel_value)
        wb, wb_sha256 = build_workbook(ctx, _CH4_DENSITY)

        output_buffer = io.BytesIO()
        wb.save(output_buffer)
        output_buffer.seek(0)

        filename = f"OGMP_2.0_Methane_Report_{year if year != 'all' else 'AllYears'}.xlsx"
        resp = send_file(
            output_buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
        record_report_fingerprint(resp, user, "OGMP 2.0 workbook", {"year": year}, len(ctx.facilities), wb_sha256)
        resp.headers["X-Audit-Timestamp"] = datetime.now(timezone.utc).isoformat()
        resp.headers["X-Audit-SHA256"] = wb_sha256
        return resp

    except Exception as e:
        current_app.logger.error(f"Error generating OGMP Excel report: {e}", exc_info=True)
        return (
            jsonify({"error": "OGMP report export failed. Please try again or contact support."}),
            500,
        )


def _facilities(allowed_fids, facility_filter):
    """The facilities in the user's scope and the request's facility / activity / division / segment filters."""
    fac_q = Facility.query
    if allowed_fids is not None:
        fac_q = fac_q.filter(Facility.id.in_(allowed_fids))
    if facility_filter:
        fac_q = fac_q.filter_by(id=facility_filter)
    for column, arg in ((Facility.activity, "activity"), (Facility.division, "division"), (Facility.segment, "segment")):
        value = request.args.get(arg)
        if value and value != "all":
            fac_q = fac_q.filter(column == value)
    return fac_q.all()
