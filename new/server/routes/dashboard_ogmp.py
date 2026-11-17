"""OGMP 2.0 metrics route.

Split out of routes/dashboard.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``dashboard_bp`` blueprint, so URLs and endpoint names are the same.
"""
from datetime import datetime, timezone
from extensions import db
from flask import jsonify, request
from models import Emission, Facility, OgmpAnnualReport, OgmpSurvey
from routes.auth import login_required
from services.ogmp import compute_facility_ogmp_level
from services.dashboard_filters import _parse_facility_ids
from sqlalchemy import func
from utils import get_allowed_facility_ids, get_current_tenant_id, get_current_user, tenant_matches
from routes.dashboard import dashboard_bp, is_it_role


def _scoped_facilities(caller_tenant, allowed_fids, fac_fids):
    """Facilities of the caller's tenant and scope, narrowed by the facility / segment / activity / division filters."""
    query = Facility.query.filter(tenant_matches(Facility.tenant_id, caller_tenant))
    if allowed_fids is not None:
        query = query.filter(Facility.id.in_(allowed_fids or [-1]))
    if fac_fids is not None:
        query = query.filter(Facility.id.in_(fac_fids))
    if request.args.get("segment") and request.args.get("segment") != "all":
        query = query.filter(Facility.segment == request.args.get("segment"))
    if request.args.get("activity") and request.args.get("activity") != "all":
        query = query.filter(Facility.activity == request.args.get("activity"))
    if request.args.get("division") and request.args.get("division") != "all":
        query = query.filter(Facility.division == request.args.get("division"))
    return query.all()


def _survey_and_inventory_ch4(allowed_fids, fac_fids, single_year, year):
    """(top-down survey tCH4, bottom-up verified tCH4) per facility; bottom-up covers the surveyed years only."""
    survey_query = db.session.query(
        OgmpSurvey.facility_id, OgmpSurvey.year, func.avg(OgmpSurvey.estimated_annual_tch4).label("td"),
    )
    if allowed_fids is not None:
        survey_query = survey_query.filter(OgmpSurvey.facility_id.in_(allowed_fids or [-1]))
    if fac_fids is not None:
        survey_query = survey_query.filter(OgmpSurvey.facility_id.in_(fac_fids))
    if single_year:
        survey_query = survey_query.filter(OgmpSurvey.year == int(year))
    survey_years = {}
    for r in survey_query.group_by(OgmpSurvey.facility_id, OgmpSurvey.year).all():
        if r.td is not None:
            survey_years.setdefault(r.facility_id, {})[r.year] = float(r.td)

    ch4_query = db.session.query(
        Emission.facility_id, Emission.year, func.sum(Emission.ch4_emissions).label("total_ch4")
    ).filter(Emission.status == "Verified", Emission.is_test == False)  # noqa: E712 (BA-011)
    if allowed_fids is not None:
        ch4_query = ch4_query.filter(Emission.facility_id.in_(allowed_fids or [-1]))
    if fac_fids is not None:
        ch4_query = ch4_query.filter(Emission.facility_id.in_(fac_fids))
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
        ch4_map[fid] = sum(cy.get(y, 0.0) for y in sy) if sy else sum(cy.values())
    return survey_map, ch4_map


def _latest_annual_reports(caller_tenant, allowed_fids, fac_fids, single_year, year):
    """The newest OGMP annual report of each facility in scope."""
    rep_q = OgmpAnnualReport.query.filter(tenant_matches(OgmpAnnualReport.tenant_id, caller_tenant))
    if allowed_fids is not None:
        rep_q = rep_q.filter(OgmpAnnualReport.facility_id.in_(allowed_fids or [-1]))
    if fac_fids is not None:
        rep_q = rep_q.filter(OgmpAnnualReport.facility_id.in_(fac_fids))
    if single_year:
        rep_q = rep_q.filter(OgmpAnnualReport.year == int(year))
    annual_by_fac = {}
    for rep in rep_q.order_by(OgmpAnnualReport.year.desc(), OgmpAnnualReport.id.desc()).all():
        annual_by_fac.setdefault(rep.facility_id, rep)
    return annual_by_fac


def _survey_has_discrepancy(f, single_year, year, threshold) -> bool:
    """Whether a survey of the facility is flagged or differs from the inventory by more than the threshold."""
    # no try/except: a failed query must not read as "no discrepancy"
    sq = OgmpSurvey.query.filter_by(facility_id=f.id)
    if single_year:
        sq = sq.filter_by(year=int(year))
    for s in sq.all():
        if (s.reconciliation_status or "").lower() == "discrepancy detected" or s.variance_flag is True or (s.variance_pct is not None and abs(s.variance_pct) > threshold):
            return True
    return False


def _reconciliation_result(top_down, bottom_up, threshold, survey_has_discrepancy):
    """(variance %, variance flag, reconciliation status) of the top-down vs bottom-up comparison."""
    if top_down > 0 and bottom_up > 0:
        variance_pct = round(((top_down - bottom_up) / bottom_up * 100.0), 2)
        variance_flag = abs(variance_pct) > threshold or survey_has_discrepancy
        rec_status = "Discrepancy Detected" if variance_flag else "Reconciled"
    elif top_down > 0 and bottom_up == 0:
        variance_pct = None
        variance_flag = True
        rec_status = "Discrepancy Detected"
    elif top_down == 0 and bottom_up > 0:
        variance_pct = None
        variance_flag = False
        rec_status = "Bottom-Up Only"
    else:
        variance_pct = None
        variance_flag = False
        rec_status = "No Activity"
    return variance_pct, variance_flag, rec_status


@dashboard_bp.route("/ogmp-metrics", methods=["GET"])
@login_required
def get_ogmp_metrics():
    """
    OGMP 2.0 Gold Standard roadmap & milestone progress per facility.
    Returns compliance deadlines, current L1-L5 levels, L4 materiality, RSS 95% CI reconciliation & pathways.
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
    caller_tenant = get_current_tenant_id(user)

    fac_id = request.args.get("facilityId") or request.args.get("facility_id")
    year = request.args.get("year")
    current_year = (
        int(year)
        if year and year != "all" and str(year).isdigit()
        else datetime.now(timezone.utc).year
    )

    fac_fids = _parse_facility_ids(fac_id)
    if fac_fids is not None and allowed_fids is not None and not set(fac_fids).issubset(set(allowed_fids)):
        return jsonify({"error": "Unauthorized facility"}), 403
    facilities = _scoped_facilities(caller_tenant, allowed_fids, fac_fids)

    single_year = year and year != "all" and str(year).isdigit()
    survey_map, ch4_map = _survey_and_inventory_ch4(allowed_fids, fac_fids, single_year, year)
    annual_by_fac = _latest_annual_reports(caller_tenant, allowed_fids, fac_fids, single_year, year)

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

        top_down = float(survey_map.get(f.id, 0.0) or 0.0)
        bottom_up = float(ch4_map.get(f.id, 0.0) or 0.0)
        highest_level = compute_facility_ogmp_level(
            f, year=int(year) if single_year else None, top_down_tch4=top_down, bottom_up_tch4=bottom_up
        )
        is_compliant = (highest_level >= 4) or (current_year <= target_yr and highest_level >= 2)

        survey_has_discrepancy = _survey_has_discrepancy(f, single_year, year, threshold)
        variance_pct, variance_flag, rec_status = _reconciliation_result(top_down, bottom_up, threshold, survey_has_discrepancy)

        if survey_has_discrepancy:
            variance_flag = True
            rec_status = "Discrepancy Detected"
            highest_level = min(4, highest_level)

        ann_rep = annual_by_fac.get(f.id)
        if ann_rep is not None and not survey_has_discrepancy and top_down == 0:
            highest_level = int(ann_rep.reporting_level or highest_level)
            is_compliant = (highest_level >= 4) or (current_year <= target_yr and highest_level >= 2)
            variance_pct = ann_rep.variance_pct
            variance_flag = bool(ann_rep.variance_flag)
            rec_status = ann_rep.reconciliation_status or rec_status

        if is_compliant:
            gold_compliant_count += 1

        fac_list.append(
            {
                "facility_id": f.id,
                "id": f.id,
                "facility_name": f.name,
                "name": f.name,
                "facility_code": f.code or f"FAC-{f.id}",
                "segment": f.segment or "Upstream",
                "country": f.country or "",
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
                "l4_materiality_pct": ann_rep.l4_materiality_pct if ann_rep else None,
                "pathway_code": ann_rep.pathway_code if ann_rep else None,
                "ci_overlaps": bool(ann_rep.ci_overlaps) if ann_rep else None,
                "bu_ci_low_tch4": ann_rep.bu_ci_low_tch4 if ann_rep else None,
                "bu_ci_high_tch4": ann_rep.bu_ci_high_tch4 if ann_rep else None,
                "td_ci_low_tch4": ann_rep.td_ci_low_tch4 if ann_rep else None,
                "td_ci_high_tch4": ann_rep.td_ci_high_tch4 if ann_rep else None,
                "measurement_mode": ann_rep.measurement_mode if ann_rep else None,
                "option_mode": ann_rep.option_mode if ann_rep else None,
                "status": "Gold Pathway Active" if is_compliant else "Target Milestone Overdue",
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
                "upstream_target_pct": _app_settings.get("ogmp_upstream_target_pct", 0.20),
                "midstream_target_pct": _app_settings.get("ogmp_midstream_target_pct", 0.05),
            },
        }
    )
