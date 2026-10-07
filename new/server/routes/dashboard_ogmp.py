"""OGMP 2.0 metrics route.

Split out of routes/dashboard.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``dashboard_bp`` blueprint, so URLs and endpoint names are the same.
"""
from datetime import datetime, timezone
from extensions import db
from flask import jsonify, request
from models import Emission, Facility, OgmpSurvey
from routes.auth import login_required
from services.ogmp import compute_facility_ogmp_level
from sqlalchemy import func
from utils import get_allowed_facility_ids, get_current_user
from routes.dashboard import dashboard_bp, is_it_role


@dashboard_bp.route("/ogmp-metrics", methods=["GET"])
@login_required
def get_ogmp_metrics():
    """
    OGMP 2.0 Gold Standard roadmap & milestone progress per facility.
    Returns compliance deadlines, current L1-L5 levels, and reconciliation status.
    """
    user = get_current_user()
    if is_it_role(user):
        return (
            jsonify(
                {"error": "Forbidden: IT Administrators cannot access operational dashboard data"}
            ),
            403,
        )
    from routes.auth import _app_settings

    default_base_year = _app_settings.get("ogmp_default_base_year", 2023)
    default_threshold = _app_settings.get("reconciliation_threshold", 20.0)
    allowed_fids = get_allowed_facility_ids(user)

    fac_id = request.args.get("facilityId")
    year = request.args.get("year")
    current_year = (
        int(year)
        if year and year != "all" and str(year).isdigit()
        else datetime.now(timezone.utc).year
    )

    query = Facility.query
    if allowed_fids is not None:
        query = query.filter(Facility.id.in_(allowed_fids))
    if fac_id and fac_id != "all" and str(fac_id).isdigit():
        query = query.filter(Facility.id == int(fac_id))
    if request.args.get("segment") and request.args.get("segment") != "all":
        query = query.filter(Facility.segment == request.args.get("segment"))
    if request.args.get("activity") and request.args.get("activity") != "all":
        query = query.filter(Facility.activity == request.args.get("activity"))
    if request.args.get("division") and request.args.get("division") != "all":
        query = query.filter(Facility.division == request.args.get("division"))

    facilities = query.all()

    # BUG-079: reconcile per facility-YEAR. Surveys are annual estimates, so they are averaged within
    # a facility-year (D-02) and summed across years; the bottom-up side covers exactly the years
    # that have a survey. Never pair a multi-year average with a multi-year sum.
    single_year = year and year != "all" and str(year).isdigit()
    survey_query = db.session.query(
        OgmpSurvey.facility_id, OgmpSurvey.year, func.avg(OgmpSurvey.estimated_annual_tch4).label("td"),
    )
    if allowed_fids is not None:
        survey_query = survey_query.filter(OgmpSurvey.facility_id.in_(allowed_fids or [-1]))
    if fac_id and fac_id != "all" and str(fac_id).isdigit():
        survey_query = survey_query.filter(OgmpSurvey.facility_id == int(fac_id))
    if single_year:
        survey_query = survey_query.filter(OgmpSurvey.year == int(year))
    survey_years = {}
    for r in survey_query.group_by(OgmpSurvey.facility_id, OgmpSurvey.year).all():
        if r.td is not None:
            survey_years.setdefault(r.facility_id, {})[r.year] = float(r.td)

    ch4_query = db.session.query(
        Emission.facility_id, Emission.year, func.sum(Emission.ch4_emissions).label("total_ch4")
    ).filter(Emission.status == "Verified")
    if allowed_fids is not None:
        ch4_query = ch4_query.filter(Emission.facility_id.in_(allowed_fids or [-1]))
    if single_year:
        ch4_query = ch4_query.filter(Emission.year == int(year))
    ch4_years = {}
    for r in ch4_query.group_by(Emission.facility_id, Emission.year).all():
        ch4_years.setdefault(r.facility_id, {})[r.year] = float(r.total_ch4 or 0)

    survey_map, ch4_map = {}, {}
    for fid in set(survey_years) | set(ch4_years):
        sy = survey_years.get(fid, {})
        cy = ch4_years.get(fid, {})
        survey_map[fid] = sum(sy.values())
        # bottom-up over the surveyed years when there are surveys, else over all years in scope
        ch4_map[fid] = sum(cy.get(y, 0.0) for y in sy) if sy else sum(cy.values())

    fac_list = []
    total_operated = 0
    total_non_operated = 0
    gold_compliant_count = 0

    for f in facilities:
        op_status = f.operator_status or "operated"
        membership_yr = f.ogmp_membership_year or default_base_year
        target_yr = membership_yr + (3 if op_status == "operated" else 5)
        threshold = f.reconciliation_threshold or default_threshold

        if op_status == "operated":
            total_operated += 1
        else:
            total_non_operated += 1

        is_compliant = current_year <= target_yr
        if is_compliant:
            gold_compliant_count += 1

        top_down = float(survey_map.get(f.id, 0.0) or 0.0)
        bottom_up = float(ch4_map.get(f.id, 0.0) or 0.0)
        if top_down > 0 and bottom_up > 0:
            variance_pct = round(((top_down - bottom_up) / bottom_up * 100.0), 2)
            variance_flag = abs(variance_pct) > threshold
            rec_status = "Discrepancy Flagged" if variance_flag else "Reconciled"
        elif top_down > 0 and bottom_up == 0:
            # Invariant Zero (Decision D-02): Zero Bottom-Up Edge Case
            variance_pct = None
            variance_flag = True
            rec_status = "Discrepancy Flagged"
        elif top_down == 0 and bottom_up > 0:
            variance_pct = None
            variance_flag = False
            rec_status = "Bottom-Up Only"
        else:
            variance_pct = None
            variance_flag = False
            rec_status = "No Activity"

        highest_level = compute_facility_ogmp_level(
            f, year=int(year) if single_year else None, top_down_tch4=top_down, bottom_up_tch4=bottom_up
        )

        fac_list.append(
            {
                "facility_id": f.id,
                "id": f.id,
                "facility_name": f.name,
                "name": f.name,
                "facility_code": f.code or f"FAC-{f.id}",
                "segment": f.segment or "Upstream",
                "country": f.country or "Algeria",
                "operator_status": op_status,
                "ogmp_membership_year": membership_yr,
                "target_year": target_yr,
                "target_compliance_year": target_yr,
                "target_gold_year": target_yr,
                "reconciliation_threshold": threshold,
                "is_compliant": is_compliant,
                "highest_ogmp_level": highest_level,
                "reconciliation_variance_pct": variance_pct,
                "variance_flag": variance_flag,
                "reconciliation_status": rec_status,
                "status": (
                    "Gold Pathway Active"
                    if is_compliant
                    else "Target Milestone Overdue"
                ),
            }
        )

    return jsonify(
        {
            "facilities": fac_list,
            "summary": {
                "total_facilities": len(facilities),
                "operated_count": total_operated,
                "non_operated_count": total_non_operated,
                "gold_compliant_count": gold_compliant_count,
                "current_reporting_year": current_year,
                "global_default_base_year": default_base_year,
                "global_threshold": default_threshold,
                "upstream_target_pct": _app_settings.get(
                    "ogmp_upstream_target_pct", 0.20
                ),
                "midstream_target_pct": _app_settings.get(
                    "ogmp_midstream_target_pct", 0.05
                ),
            },
        }
    )
