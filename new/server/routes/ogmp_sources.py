"""OGMP 2.0 routes on ogmp_bp: source-level disclosures, site-level measurement campaigns and implementation
plans (split from routes/ogmp.py, which holds the blueprint, access checks and serializers)."""

from __future__ import annotations

import datetime
from models import (
    Facility,
    OgmpEmissionSource,
    OgmpImplementationPlan,
    OgmpReportingEntity,
    OgmpSiteMeasurement,
)
from process_categories import NON_OG_ACTIVITIES
from services.ogmp_reconciliation import (
    VALID_MEASUREMENT_MODES,
    VALID_OPTION_MODES,
    build_default_implementation_plan,
    validate_emission_source_payload,
)
from routes.ogmp import (
    _FORBIDDEN_IT,
    _FORBIDDEN_WRITE,
    _can_read,
    _can_write,
    _linked_annual_report_id,
    _record_ogmp_audit,
    _scoped_query,
    _serialize_measurement,
    _serialize_plan,
    _serialize_source,
    ogmp_bp,
)
from extensions import db
from utils import facility_access_error, get_current_tenant_id, get_current_user, internal_error, tenant_matches
from flask import jsonify, request
from routes.auth import login_required
from input_validation import parse_number, parse_year


# ---------------------------------------------------------------------------
# Emission Sources (15 Upstream / 12 Mid-Downstream, MI/N/A, YoY & Zero rules)
# ---------------------------------------------------------------------------
@ogmp_bp.route("/emission-sources", methods=["GET", "POST"])
@login_required
def emission_sources_collection():
    user = get_current_user()
    if request.method == "GET":
        if not _can_read(user):
            return jsonify(_FORBIDDEN_IT[0]), 403
        q, err = _scoped_query(OgmpEmissionSource, user)
        if err:
            return err
        rows = q.order_by(OgmpEmissionSource.year.desc(), OgmpEmissionSource.source_code.asc()).all()
        return jsonify([_serialize_source(r) for r in rows])

    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    data = request.get_json() or {}
    fid = data.get("facility_id") or data.get("facilityId")
    if (denied := facility_access_error(user, fid)):
        return denied
    fid = int(fid)
    fac = db.session.get(Facility, fid)
    if fac and fac.activity in NON_OG_ACTIVITIES:
        return jsonify({"error": f"Facility '{fac.name}' ({fac.activity}) is outside OGMP 2.0 Oil & Gas scope"}), 400

    year = parse_year(data.get("year"))
    source_code = str(data.get("source_code") or "").strip()
    prior_rec = (
        OgmpEmissionSource.query.filter_by(
            facility_id=fid,
            source_code=source_code,
            year=year - 1,
            tenant_id=get_current_tenant_id(user),
        ).first()
        if source_code else None
    )
    prior_ch4 = prior_rec.ch4_tonnes if prior_rec else None

    try:
        clean = validate_emission_source_payload(data, prior_year_ch4=prior_ch4)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    report_id, err = _linked_annual_report_id(data, fid, get_current_tenant_id(user))
    if err:
        return err

    src = OgmpEmissionSource(
        facility_id=fid,
        annual_report_id=report_id,
        year=year,
        tenant_id=get_current_tenant_id(user),
        created_by=user.id,
        **clean,
    )
    try:
        db.session.add(src)
        db.session.flush()
        _record_ogmp_audit(
            user, "CREATE", "OgmpEmissionSource", src.id,
            f"Logged OGMP L{src.ogmp_level} source {src.source_code} ({src.status_flag}: {src.ch4_tonnes} tCH4 ±{src.uncertainty_pct}%) for facility #{fid} ({year})",
            facility_id=fid, after=_serialize_source(src),
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to save OGMP emission source")
    return jsonify(_serialize_source(src)), 201


@ogmp_bp.route("/emission-sources/<int:source_id>", methods=["PUT", "DELETE"])
@login_required
def mutate_emission_source(source_id: int):
    user = get_current_user()
    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    src = db.session.get(OgmpEmissionSource, source_id)
    if not src or src.tenant_id != get_current_tenant_id(user):
        return jsonify({"error": "Emission source not found"}), 404
    if (denied := facility_access_error(user, src.facility_id)):
        return denied

    if request.method == "DELETE":
        before = _serialize_source(src)
        try:
            fid = src.facility_id
            db.session.delete(src)
            _record_ogmp_audit(user, "DELETE", "OgmpEmissionSource", source_id, f"Deleted source {before['source_code']}", facility_id=fid, before=before)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return internal_error(e, "Failed to delete emission source")
        return jsonify({"message": "Emission source deleted"})

    data = request.get_json() or {}
    before = _serialize_source(src)
    merged = {**before, **data}
    year = parse_year(merged.get("year"))
    prior_rec = OgmpEmissionSource.query.filter_by(
        facility_id=src.facility_id,
        source_code=str(merged.get("source_code") or src.source_code),
        year=year - 1,
        tenant_id=src.tenant_id,
    ).first()
    try:
        clean = validate_emission_source_payload(merged, prior_year_ch4=prior_rec.ch4_tonnes if prior_rec else None)
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400

    src.year = year
    for k, v in clean.items():
        setattr(src, k, v)
    try:
        after = _serialize_source(src)
        _record_ogmp_audit(user, "UPDATE", "OgmpEmissionSource", src.id, f"Updated source {src.source_code} ({src.status_flag})", facility_id=src.facility_id, before=before, after=after)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to update emission source")
    return jsonify(_serialize_source(src))


# ---------------------------------------------------------------------------
# Site Measurements (L5 Instantaneous / Annualized & Option 1 / Option 2)
# ---------------------------------------------------------------------------
@ogmp_bp.route("/site-measurements", methods=["GET", "POST"])
@login_required
def site_measurements_collection():
    user = get_current_user()
    if request.method == "GET":
        if not _can_read(user):
            return jsonify(_FORBIDDEN_IT[0]), 403
        q, err = _scoped_query(OgmpSiteMeasurement, user)
        if err:
            return err
        rows = q.order_by(OgmpSiteMeasurement.year.desc(), OgmpSiteMeasurement.campaign_date.desc()).all()
        return jsonify([_serialize_measurement(m) for m in rows])

    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    data = request.get_json() or {}
    fid = data.get("facility_id") or data.get("facilityId")
    if (denied := facility_access_error(user, fid)):
        return denied
    fid = int(fid)
    fac = db.session.get(Facility, fid)
    if fac and fac.activity in NON_OG_ACTIVITIES:
        return jsonify({"error": f"Facility '{fac.name}' ({fac.activity}) is outside OGMP 2.0 Oil & Gas scope"}), 400

    year = parse_year(data.get("year"))
    cdate = str(data.get("campaign_date") or "").strip()
    try:
        c_day = datetime.date.fromisoformat(cdate)
    except ValueError:
        return jsonify({"error": "campaign_date must be YYYY-MM-DD", "field": "campaign_date"}), 400
    if c_day.year != year:  # a campaign of another year was accepted (audit 2026-11 F-GOGMP-09)
        return jsonify({"error": f"campaign_date {cdate} is not in the reporting year {year}",
                        "field": "campaign_date"}), 400

    survey_type = str(data.get("survey_type") or "").strip()
    if not survey_type:
        return jsonify({"error": "survey_type is required", "field": "survey_type"}), 400

    mode = str(data.get("measurement_mode") or "Annualized").strip()
    if mode not in VALID_MEASUREMENT_MODES:
        return jsonify({"error": f"measurement_mode must be one of: {', '.join(VALID_MEASUREMENT_MODES)}", "field": "measurement_mode"}), 400

    opt = str(data.get("option_mode") or "Option 1").strip()
    if opt not in VALID_OPTION_MODES:
        return jsonify({"error": f"option_mode must be one of: {', '.join(VALID_OPTION_MODES)}", "field": "option_mode"}), 400

    rate = parse_number(data.get("measured_rate_kg_hr"), "measured_rate_kg_hr", min_value=0.0)
    hours = parse_number(data.get("operating_hours_year", 8760.0), "operating_hours_year", required=False, min_value=0.0, max_value=8784.0, default=8760.0)
    # the campaign's own uncertainty (95 %): a 30 / 20 % default was inserted silently (audit 2026-11 F-RPT-06)
    unc = parse_number(data.get("uncertainty_pct"), "uncertainty_pct", min_value=0.0, max_value=500.0)
    det = parse_number(data.get("detection_threshold_kg_hr"), "detection_threshold_kg_hr", required=False, min_value=0.0)

    raw_ann = data.get("annualized_tch4")
    if raw_ann not in (None, ""):
        annualized = parse_number(raw_ann, "annualized_tch4", min_value=0.0)
    else:
        annualized = round(rate * hours / 1000.0, 4)

    hw = annualized * (unc / 100.0)
    ci_low = round(max(0.0, annualized - hw), 4)
    ci_high = round(annualized + hw, 4)
    report_id, err = _linked_annual_report_id(data, fid, get_current_tenant_id(user))
    if err:
        return err

    meas = OgmpSiteMeasurement(
        facility_id=fid,
        annual_report_id=report_id,
        year=year,
        campaign_date=cdate,
        survey_type=survey_type,
        instrument_vendor=str(data.get("instrument_vendor") or "").strip(),
        measurement_mode=mode,
        option_mode=opt,
        measured_rate_kg_hr=rate,
        operating_hours_year=hours,
        annualized_tch4=annualized,
        uncertainty_pct=unc,
        ci_low_tch4=ci_low,
        ci_high_tch4=ci_high,
        detection_threshold_kg_hr=det,
        meteorological_notes=str(data.get("meteorological_notes") or "").strip(),
        tenant_id=get_current_tenant_id(user),
        created_by=user.id,
    )
    try:
        db.session.add(meas)
        db.session.flush()
        _record_ogmp_audit(
            user, "CREATE", "OgmpSiteMeasurement", meas.id,
            f"Recorded L5 site measurement ({survey_type}, {mode}/{opt}: {annualized} tCH4 ±{unc}%)",
            facility_id=fid, after=_serialize_measurement(meas),
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to save site measurement")
    return jsonify(_serialize_measurement(meas)), 201


@ogmp_bp.route("/site-measurements/<int:meas_id>", methods=["DELETE"])
@login_required
def delete_site_measurement(meas_id: int):
    user = get_current_user()
    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    meas = db.session.get(OgmpSiteMeasurement, meas_id)
    if not meas or meas.tenant_id != get_current_tenant_id(user):
        return jsonify({"error": "Site measurement not found"}), 404
    if (denied := facility_access_error(user, meas.facility_id)):
        return denied
    before = _serialize_measurement(meas)
    try:
        fid = meas.facility_id
        db.session.delete(meas)
        _record_ogmp_audit(user, "DELETE", "OgmpSiteMeasurement", meas_id, f"Deleted site measurement #{meas_id}", facility_id=fid, before=before)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to delete site measurement")
    return jsonify({"message": "Site measurement deleted"})


# ---------------------------------------------------------------------------
# Implementation Plans (Y0-Y10; 3-yr operated / 5-yr non-operated)
# ---------------------------------------------------------------------------
@ogmp_bp.route("/implementation-plans", methods=["GET", "POST"])
@login_required
def implementation_plans_collection():
    user = get_current_user()
    if request.method == "GET":
        if not _can_read(user):
            return jsonify(_FORBIDDEN_IT[0]), 403
        q, err = _scoped_query(OgmpImplementationPlan, user)
        if err:
            return err
        rows = q.order_by(OgmpImplementationPlan.facility_id.asc(), OgmpImplementationPlan.planned_year.asc()).all()
        return jsonify([_serialize_plan(p) for p in rows])

    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    data = request.get_json() or {}
    fid = data.get("facility_id") or data.get("facilityId")
    if (denied := facility_access_error(user, fid)):
        return denied
    fid = int(fid)
    fac = db.session.get(Facility, fid)
    tenant_id = get_current_tenant_id(user)

    rep_ent_id = data.get("reporting_entity_id")
    if rep_ent_id not in (None, ""):
        try:
            rep_ent = db.session.get(OgmpReportingEntity, int(rep_ent_id))
        except (ValueError, TypeError):
            rep_ent = None
        if not rep_ent or rep_ent.tenant_id != tenant_id:
            return jsonify({"error": "Reporting entity not found or unauthorized", "field": "reporting_entity_id"}), 404
        rep_ent_id = rep_ent.id
    else:
        rep_ent_id = None

    if data.get("generate_default"):
        # the reporting entity's membership year, as its Gold target (the facility default 2023 was used: F-GOGMP-12)
        _ent = (db.session.get(OgmpReportingEntity, rep_ent_id) if rep_ent_id else
                OgmpReportingEntity.query.filter_by(facility_id=fid, tenant_id=tenant_id).first())
        b_default = (_ent.membership_year if _ent and _ent.membership_year else fac.ogmp_membership_year) or 2023
        b_year = parse_year(data.get("base_year", b_default), required=False) or b_default
        op_st = str(data.get("operator_status") or fac.operator_status or "operated").lower()
        # tenant_matches, like the other OGMP routes: "Default " or "default" is the same tenant
        existing = OgmpImplementationPlan.query.filter(
            OgmpImplementationPlan.facility_id == fid,
            tenant_matches(OgmpImplementationPlan.tenant_id, tenant_id),
        )
        replaced = existing.count()
        # the default plan replaces the facility's milestones: ask before deleting any
        if replaced and data.get("confirm") is not True:
            return jsonify({
                "error": f"This facility already has {replaced} implementation-plan milestone(s); generating the default plan replaces them. Send confirm: true to proceed.",
                "requires_confirmation": True,
                "existing_count": replaced,
            }), 409
        defaults = build_default_implementation_plan(fid, fac.name, operator_status=op_st, base_year=b_year)
        created = []
        try:
            if replaced:
                existing.delete(synchronize_session=False)
            for row in defaults:
                obj = OgmpImplementationPlan(
                    reporting_entity_id=rep_ent_id,
                    tenant_id=tenant_id,
                    created_by=user.id,
                    **row,
                )
                db.session.add(obj)
                created.append(obj)
            db.session.flush()
            _record_ogmp_audit(user, "GENERATE_PLAN", "OgmpImplementationPlan", fid, f"Generated Y0-Y10 UNEP implementation plan ({op_st}) for facility #{fid}, replacing {replaced} milestone(s)", facility_id=fid)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return internal_error(e, "Failed to generate Y0-Y10 implementation plan")
        return jsonify([_serialize_plan(p) for p in created]), 201

    horizon = str(data.get("milestone_horizon") or "").strip().upper()
    if horizon not in {f"Y{i}" for i in range(11)}:
        return jsonify({"error": "milestone_horizon must be Y0 through Y10", "field": "milestone_horizon"}), 400
    target_lvl = int(parse_number(data.get("target_level", 4), "target_level", min_value=1, max_value=5))
    actual_raw = data.get("actual_level")
    actual_lvl = int(parse_number(actual_raw, "actual_level", required=False, min_value=1, max_value=5)) if actual_raw not in (None, "") else None
    b_year = parse_year(data.get("base_year", fac.ogmp_membership_year or 2023), required=False) or 2023
    from input_validation import parse_future_year  # plan years run up to Y10 (F-GOGMP-07)
    p_year = parse_future_year(data.get("planned_year", b_year + int(horizon[1:])), "planned_year", required=False) or b_year

    plan = OgmpImplementationPlan(
        facility_id=fid,
        reporting_entity_id=rep_ent_id,
        asset_name=str(data.get("asset_name") or fac.name).strip(),
        operator_status=str(data.get("operator_status") or fac.operator_status or "operated").lower(),
        base_year=b_year,
        milestone_horizon=horizon,
        planned_year=p_year,
        target_level=target_lvl,
        actual_level=actual_lvl,
        source_scope=str(data.get("source_scope") or "").strip(),
        methodology_upgrade=str(data.get("methodology_upgrade") or "").strip(),
        milestone_status=str(data.get("milestone_status") or "Planned").strip(),
        justification=str(data.get("justification") or "").strip(),
        tenant_id=tenant_id,
        created_by=user.id,
    )
    try:
        db.session.add(plan)
        db.session.flush()
        _record_ogmp_audit(user, "CREATE", "OgmpImplementationPlan", plan.id, f"Added Y0-Y10 milestone {horizon} ({p_year}, L{target_lvl}) for facility #{fid}", facility_id=fid, after=_serialize_plan(plan))
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to save implementation plan milestone")
    return jsonify(_serialize_plan(plan)), 201


@ogmp_bp.route("/implementation-plans/<int:plan_id>", methods=["DELETE"])
@login_required
def delete_implementation_plan(plan_id: int):
    user = get_current_user()
    if not _can_write(user):
        return jsonify(_FORBIDDEN_WRITE[0]), 403
    plan = db.session.get(OgmpImplementationPlan, plan_id)
    if not plan or plan.tenant_id != get_current_tenant_id(user):
        return jsonify({"error": "Implementation plan milestone not found"}), 404
    if (denied := facility_access_error(user, plan.facility_id)):
        return denied
    try:
        fid = plan.facility_id
        db.session.delete(plan)
        _record_ogmp_audit(user, "DELETE", "OgmpImplementationPlan", plan_id, f"Deleted implementation milestone #{plan_id}", facility_id=fid)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to delete milestone")
    return jsonify({"message": "Milestone deleted"})
