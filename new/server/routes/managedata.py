import datetime
from flask import Blueprint, jsonify, request
from models import (
    EmissionSource,
    MitigationRecord,
    MitigationProject,
    ReportingMetadata,
    Facility,
    ProductionData,
    Emission,
    Scope2Emission,
    Scope3Emission,
    Notification,
    Goal,
    BaseYear,
    BaseYearRecalculation,
)
from extensions import db
from utils import log_activity_and_notify, get_current_user, get_allowed_facility_ids
from sqlalchemy import func, distinct, or_
from routes.auth import login_required
from utils import internal_error

managedata_bp = Blueprint("managedata", __name__)


# --- Emission Sources ---
@managedata_bp.route("/sources", methods=["GET"])
@managedata_bp.route("/sources/", methods=["GET"])
@login_required
def get_sources():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to view operational emission sources."}), 403
    allowed_fids = get_allowed_facility_ids(user)

    query = EmissionSource.query
    if allowed_fids is not None:
        query = query.filter(EmissionSource.facility_id.in_(allowed_fids))

    sources = query.all()
    return jsonify(
        [
            {
                "id": s.id,
                "facility_id": s.facility_id,
                "name": s.name,
                "type": s.type,
                "equipment_id": s.equipment_id,
                "fuel_type": s.fuel_type,
                "design_capacity": s.design_capacity,
                "installation_date": s.installation_date,
                "status": s.status,
                "description": s.description,
                "activity": s.activity,
                "division": s.division,
                "field": s.field,
                "region": s.region,
            }
            for s in sources
        ]
    )


@managedata_bp.route("/sources", methods=["POST"])
@managedata_bp.route("/sources/", methods=["POST"])
@login_required
def add_source():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify operational emission sources."}), 403
    data = request.get_json() or {}
    fid = data.get("facility_id")
    if not fid:
        return jsonify({"error": "Facility ID is required"}), 400
    try:
        fid = int(fid)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid facility ID"}), 400

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and fid not in allowed_fids:
        return jsonify({"error": "Access to this facility is denied"}), 403

    source = EmissionSource(
        facility_id=fid,
        name=data.get("name"),
        type=data.get("type"),
        equipment_id=data.get("equipment_id"),
        fuel_type=data.get("fuel_type"),
        design_capacity=data.get("design_capacity"),
        installation_date=data.get("installation_date"),
        status=data.get("status", "Active"),
        description=data.get("description"),
        activity=data.get("activity"),
        division=data.get("division"),
        field=data.get("field"),
    )
    try:
        db.session.add(source)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to add source")

    try:
        log_activity_and_notify(
            "CREATE",
            source.id,
            f"Added emission source {source.name}",
            user=user,
            request=request,
            entity="EmissionSource",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({"message": "Source added", "id": source.id}), 201


@managedata_bp.route("/sources/<int:source_id>", methods=["DELETE"])
@login_required
def delete_source(source_id):
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify operational emission sources."}), 403
    source = db.session.get(EmissionSource, source_id)
    if not source:
        return jsonify({"error": "Source not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and source.facility_id not in allowed_fids:
        return jsonify({"error": "Access to this facility is denied"}), 403

    try:
        db.session.delete(source)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to delete source")

    try:
        log_activity_and_notify(
            "DELETE",
            source_id,
            f"Deleted emission source",
            user=user,
            request=request,
            entity="EmissionSource",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({"message": "Source deleted"})


@managedata_bp.route("/sources/bulk-import", methods=["POST"])
@login_required
def bulk_import_sources():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify operational emission sources."}), 403
    data = request.get_json() or {}
    records = data.get("records", [])
    if not records:
        return jsonify({"error": "No records provided"}), 400

    # same validation as the file import (facility access, duplicates, dates)
    from background_processor import process_json_records

    imported_count, row_errors = process_json_records("sources", records, user)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to bulk import sources")

    try:
        log_activity_and_notify(
            "CREATE",
            "bulk",
            f"Bulk imported {imported_count} emission sources",
            user=user,
            request=request,
            entity="EmissionSource",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({"message": f"{imported_count} sources imported", "errors": row_errors}), 201


# --- Mitigation Records ---
@managedata_bp.route("/mitigation", methods=["GET"])
@managedata_bp.route("/mitigation/", methods=["GET"])
@login_required
def get_mitigations():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to view operational mitigation data."}), 403
    allowed_fids = get_allowed_facility_ids(user)

    # Fetch Records (Legacy/Generic) — not facility-linked, visible to all
    records = MitigationRecord.query.all()

    # Fetch Projects (Facility-linked) — apply access filter
    proj_query = db.session.query(MitigationProject, Facility).outerjoin(
        Facility, MitigationProject.facility_id == Facility.id
    )
    if allowed_fids is not None:
        proj_query = proj_query.filter(
            or_(
                MitigationProject.facility_id.is_(None),
                MitigationProject.facility_id.in_(allowed_fids),
            )
        )
    projects = proj_query.all()

    results = []

    # Process Records
    for m in records:
        results.append(
            {
                "id": f"rec_{m.id}",
                "type": "record",
                "year": m.year,
                "name": f"{m.type}",  # Generic name
                "mitigation_type": m.type,
                "subtype": m.subtype,
                "quantity_tco2e": m.quantity_tco2e,
                "notes": m.notes,
                "reference_id": m.reference_id,
                "activity": "-",
                "division": "-",
                "region": "-",
                "status": "Active",
            }
        )

    # Process Projects
    for p, f in projects:
        results.append(
            {
                "id": f"proj_{p.id}",
                "type": "project",
                "facility_id": p.facility_id,
                "facility_name": f.name if f else "-",
                "year": p.year,
                "name": p.name,
                "mitigation_type": p.project_type,
                "subtype": "-",
                "quantity_tco2e": p.quantity_tco2e,
                "notes": p.description,
                "reference_id": "-",
                "activity": f.activity if f else "-",
                "division": f.division if f else "-",
                "region": (f.location or f.region or f.name) if f else "-",
                "status": p.status,
            }
        )

    return jsonify(results)


@managedata_bp.route("/mitigation", methods=["POST"])
@managedata_bp.route("/mitigation/", methods=["POST"])
@login_required
def add_mitigation():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify operational mitigation data."}), 403
    data = request.get_json() or {}

    facility_id = data.get("facility_id")

    if facility_id:
        try:
            fid = int(facility_id)
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid facility ID"}), 400
        allowed_fids = get_allowed_facility_ids(user)
        if allowed_fids is not None and fid not in allowed_fids:
            return jsonify({"error": "Access to this facility is denied"}), 403

        # Create MitigationProject
        project = MitigationProject(
            name=data.get("name") or f"{data.get('type')} Project",
            project_type=data.get("type"),
            year=data.get("year"),
            quantity_tco2e=data.get("quantity_tco2e", 0),
            status=data.get("status", "active"),
            description=data.get("notes"),
            facility_id=fid,
        )
        db.session.add(project)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return internal_error(e, "Failed to add mitigation project")

        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
        return (
            jsonify(
                {"message": "Mitigation Project added", "id": f"proj_{project.id}"}
            ),
            201,
        )
    else:
        # Create generic MitigationRecord
        mitigation = MitigationRecord(
            year=data.get("year"),
            type=data.get("type"),
            subtype=data.get("subtype"),
            quantity_tco2e=data.get("quantity_tco2e", 0),
            notes=data.get("notes"),
            reference_id=data.get("reference_id"),
        )
        db.session.add(mitigation)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return internal_error(e, "Failed to add mitigation record")

        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
        return (
            jsonify(
                {"message": "Mitigation record added", "id": f"rec_{mitigation.id}"}
            ),
            201,
        )


@managedata_bp.route("/mitigation/<string:mitigation_id>", methods=["DELETE"])
@login_required
def delete_mitigation(mitigation_id):
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify operational mitigation data."}), 403
    # Determine type from ID prefix
    if mitigation_id.startswith("proj_"):
        try:
            pid = int(mitigation_id.split("_")[1])
        except (IndexError, ValueError):
            return jsonify({"error": "Invalid project ID format"}), 400
        item = db.session.get(MitigationProject, pid)
    elif mitigation_id.startswith("rec_"):
        try:
            rid = int(mitigation_id.split("_")[1])
        except (IndexError, ValueError):
            return jsonify({"error": "Invalid record ID format"}), 400
        item = db.session.get(MitigationRecord, rid)
    else:
        # Fallback for old IDs (assume record)
        try:
            item = db.session.get(MitigationRecord, int(mitigation_id))
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid ID format"}), 400

    if not item:
        return jsonify({"error": "Record not found"}), 404

    if isinstance(item, MitigationProject) and item.facility_id:
        allowed_fids = get_allowed_facility_ids(user)
        if allowed_fids is not None and item.facility_id not in allowed_fids:
            return jsonify({"error": "Access to this facility is denied"}), 403
    elif isinstance(item, MitigationRecord):
        if not user or user.role not in ["admin", "superuser"]:
            return jsonify({"error": "Admin or Superuser privileges required to delete corporate mitigation records"}), 403

    try:
        db.session.delete(item)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to delete mitigation item")

    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()
    return jsonify({"message": "Mitigation record deleted"})


# --- Reporting Metadata ---
@managedata_bp.route("/reporting-metadata", methods=["GET"])
@login_required
def get_reporting_metadata():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to view reporting metadata."}), 403
    year = request.args.get("year")
    if not year:
        return jsonify({"error": "Year required"}), 400

    metadata = ReportingMetadata.query.filter_by(year=int(year)).first()
    if not metadata:
        return jsonify(
            {
                "year": int(year),
                "has_reduction_target": 0,
                "target_description": "",
                "is_tcfd_aligned": 0,
                "assurance_level": "None",
                "assurance_provider": "",
                "notes": "",
            }
        )

    return jsonify(
        {
            "id": metadata.id,
            "year": metadata.year,
            "has_reduction_target": metadata.has_reduction_target,
            "target_description": metadata.target_description,
            "is_tcfd_aligned": metadata.is_tcfd_aligned,
            "assurance_level": metadata.assurance_level,
            "assurance_provider": metadata.assurance_provider,
            "notes": metadata.notes,
        }
    )


@managedata_bp.route("/reporting-metadata", methods=["POST"])
@login_required
def save_reporting_metadata():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify reporting metadata."}), 403
    if not user or user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Administrator privileges required to modify reporting metadata."}), 403

    data = request.get_json() or {}
    year = data.get("year")
    if not year:
        return jsonify({"error": "Year required"}), 400

    metadata = ReportingMetadata.query.filter_by(year=int(year)).first()
    if metadata:
        metadata.has_reduction_target = data.get(
            "has_reduction_target", metadata.has_reduction_target
        )
        metadata.target_description = data.get(
            "target_description", metadata.target_description
        )
        metadata.is_tcfd_aligned = data.get("is_tcfd_aligned", metadata.is_tcfd_aligned)
        metadata.assurance_level = data.get("assurance_level", metadata.assurance_level)
        metadata.assurance_provider = data.get(
            "assurance_provider", metadata.assurance_provider
        )
        metadata.notes = data.get("notes", metadata.notes)
    else:
        metadata = ReportingMetadata(
            year=int(year),
            has_reduction_target=data.get("has_reduction_target", 0),
            target_description=data.get("target_description", ""),
            is_tcfd_aligned=data.get("is_tcfd_aligned", 0),
            assurance_level=data.get("assurance_level", "None"),
            assurance_provider=data.get("assurance_provider", ""),
            notes=data.get("notes", ""),
        )
        db.session.add(metadata)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to save reporting metadata")

    # --- Audit Notification ---
    try:
        Notification.create(
            title="Reporting Metadata Updated",
            message=f"Reporting metadata for {year} was updated.",
            type="audit",
            user_id=None,
        )
    except Exception as e:
        print(f"Audit Notif Error: {e}")

    return jsonify({"message": "Reporting metadata saved"})


# --- Production Years ---
@managedata_bp.route("/production/years", methods=["GET"])
@login_required
def get_production_years():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to view operational data."}), 403
    years = (
        db.session.query(ProductionData.year)
        .distinct()
        .order_by(ProductionData.year.desc())
        .all()
    )
    return jsonify([y[0] for y in years])


# --- Global Available Filters ---
@managedata_bp.route("/filters/available", methods=["GET"])
@login_required
def get_available_filters():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to view operational filters."}), 403
    allowed_fids = get_allowed_facility_ids(user)

    year_queries = [
        db.session.query(distinct(Emission.year)),
        db.session.query(distinct(ProductionData.year)),
        db.session.query(distinct(MitigationRecord.year)),
        db.session.query(distinct(Scope2Emission.year)),
        db.session.query(distinct(Scope3Emission.year)),
    ]

    available_years = set()
    for query in year_queries:
        try:
            results = query.all()
            for r in results:
                if r[0]:
                    available_years.add(int(r[0]))
        except Exception:
            continue

    em_query = db.session.query(distinct(Emission.facility_id))
    if allowed_fids is not None:
        em_query = em_query.filter(Emission.facility_id.in_(allowed_fids))
    referenced_facility_ids = em_query.all()
    facility_ids = [r[0] for r in referenced_facility_ids if r[0]]

    # Get facility details
    fac_query = Facility.query
    if allowed_fids is not None:
        fac_query = fac_query.filter(Facility.id.in_(allowed_fids))
    facilities = (
        fac_query.filter(Facility.id.in_(facility_ids)).all()
        if facility_ids
        else fac_query.all()
    )

    segment_query = db.session.query(distinct(Facility.segment))
    if allowed_fids is not None:
        segment_query = segment_query.filter(Facility.id.in_(allowed_fids))
    
    # Strictly enforce only valid supply chain keywords: Upstream, Midstream, Downstream
    VALID_SEGMENTS = {"upstream", "midstream", "downstream"}
    raw_segments = [r[0] for r in segment_query.all() if r[0]]
    segments = sorted(list({s.strip().title() for s in raw_segments if s.strip().lower() in VALID_SEGMENTS}))
    if not segments:
        segments = ["Downstream", "Midstream", "Upstream"]

    return jsonify(
        {
            "years": sorted(list(available_years), reverse=True),
            "segments": segments,
            "regions": [
                {
                    "id": f.id,
                    "name": f.name,
                    "region": f.region or f.location or f.name,
                    "location": f.location or f.region,
                    "activity": f.activity,
                    "division": f.division,
                    "field": f.field,
                    "segment": f.segment,
                }
                for f in facilities
            ],
        }
    )


@managedata_bp.route("/mitigation/bulk-import", methods=["POST"])
@login_required
def bulk_import_mitigation():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify operational mitigation data."}), 403
    data = request.get_json() or {}
    records = data.get("records", [])
    if not records:
        return jsonify({"error": "No records provided"}), 400

    # same validation as the file import (required year, numbers, dates, facility access)
    from background_processor import process_json_records

    imported_count, row_errors = process_json_records("mitigation", records, user)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return internal_error(e, "Failed to bulk import mitigation projects")

    try:
        log_activity_and_notify(
            "CREATE",
            "bulk",
            f"Bulk imported {imported_count} mitigation projects",
            user=user,
            request=request,
            entity="MitigationProject",
        )
        db.session.commit()
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
    except Exception:
        db.session.rollback()
    return jsonify({"message": f"{imported_count} mitigation projects imported", "errors": row_errors}), 201


# --- Yearly Emission Goals ---
@managedata_bp.route("/goals", methods=["GET"])
@managedata_bp.route("/goals/", methods=["GET"])
@login_required
def get_all_goals():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to view corporate emission targets."}), 403
    try:
        goals = Goal.query.order_by(Goal.year.desc()).all()
        return jsonify(
            [
                {
                    "year": g.year,
                    "target_amount": (
                        float(g.target_amount) if g.target_amount is not None else 0.0
                    ),
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                }
                for g in goals
            ]
        )
    except Exception as e:
        return internal_error(e)


@managedata_bp.route("/goals", methods=["POST"])
@managedata_bp.route("/goals/", methods=["POST"])
@login_required
def add_or_update_goal():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify corporate emission targets."}), 403
    if not user or user.role not in ["admin", "superuser"] or get_allowed_facility_ids(user) is not None:
        return jsonify({"error": "Organisation-wide administrator privileges required to modify corporate emission targets."}), 403
    from input_validation import parse_number

    data = request.get_json() or {}
    # BUG-039: finite, positive target and a plausible year (targets may lie in the future)
    year = int(parse_number(data.get("year"), "year", min_value=1990, max_value=2100))
    if year != parse_number(data.get("year"), "year"):
        return jsonify({"error": "'year' must be a whole year", "field": "year"}), 400
    target = parse_number(data.get("target_amount"), "target_amount")
    if target <= 0:
        return jsonify({"error": "'target_amount' must be greater than 0", "field": "target_amount"}), 400

    existing = Goal.query.filter_by(year=year).first()
    if existing:
        existing.target_amount = target
    else:
        db.session.add(Goal(year=year, target_amount=target))
    log_activity_and_notify(action="UPDATE", record_id=f"goal-{year}", user=user, request=request,
                            entity="Goal", details=f"Emission goal for {year} set to {target} tCO2e")
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()
    return jsonify({"message": "Emission goal saved successfully", "year": year, "target_amount": target}), 200


@managedata_bp.route("/goals/<int:year>", methods=["DELETE"])
@login_required
def delete_goal(year):
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify corporate emission targets."}), 403
    # Audit 2026-10-01 (A-05): same rule as saving a goal (organisation-wide admins only), and audited
    if not user or user.role not in ["admin", "superuser"] or get_allowed_facility_ids(user) is not None:
        return jsonify({"error": "Organisation-wide administrator privileges required to modify corporate emission targets."}), 403
    try:
        goal = Goal.query.filter_by(year=year).first()
        if not goal:
            return jsonify({"error": "Goal not found"}), 404
        log_activity_and_notify(action="DELETE", record_id=f"goal-{year}", user=user, request=request,
                                entity="Goal", details=f"Emission goal for {year} ({goal.target_amount} tCO2e) deleted")
        db.session.delete(goal)
        db.session.commit()
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
        return jsonify({"message": "Goal deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return internal_error(e)


# --- Base Years & Recalculations ---
@managedata_bp.route("/base-years", methods=["GET"])
@managedata_bp.route("/base-years/", methods=["GET"])
@login_required
def get_base_years():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to view base year recalculation data."}), 403
    try:
        active_rec = BaseYearRecalculation.query.order_by(
            BaseYearRecalculation.recalc_date.desc()
        ).first()
        base_year_entry = db.session.get(BaseYear, 1)

        active_year = None
        if active_rec:
            active_year = active_rec.year
        elif base_year_entry:
            active_year = base_year_entry.year

        recalculations = BaseYearRecalculation.query.order_by(
            BaseYearRecalculation.recalc_date.desc()
        ).all()
        history = [
            {
                "id": r.id,
                "year": r.year,
                "reason": r.reason,
                "recalc_date": r.recalc_date.isoformat() if r.recalc_date else None,
                "previous_emissions": r.previous_emissions,
                "adjusted_emissions": r.adjusted_emissions,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recalculations
        ]

        return jsonify(
            {
                "active_year": active_year,
                "active_record": (
                    {
                        "id": active_rec.id,
                        "year": active_rec.year,
                        "reason": active_rec.reason,
                        "recalc_date": (
                            active_rec.recalc_date.isoformat()
                            if active_rec.recalc_date
                            else None
                        ),
                    }
                    if active_rec
                    else None
                ),
                "history": history,
            }
        )
    except Exception as e:
        return internal_error(e)


@managedata_bp.route("/base-years", methods=["POST"])
@managedata_bp.route("/base-years/", methods=["POST"])
@login_required
def add_base_year_recalculation():
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify base year recalculation data."}), 403
    # Audit A-05: the base year is organisation-wide; a region-restricted superuser may not move it
    if not user or user.role not in ["admin", "superuser"] or get_allowed_facility_ids(user) is not None:
        return jsonify({"error": "Organisation-wide administrator privileges required to modify base year recalculation data."}), 403
    try:
        data = request.get_json() or {}
        if not data.get("year") or not data.get("reason"):
            return jsonify({"error": "Year and reason for change are required"}), 400

        year = int(data["year"])
        reason = str(data["reason"]).strip()
        prev_em = (
            float(data["previous_emissions"])
            if data.get("previous_emissions") not in (None, "")
            else None
        )
        adj_em = (
            float(data["adjusted_emissions"])
            if data.get("adjusted_emissions") not in (None, "")
            else None
        )

        user_id = user.id if user else None

        recalc = BaseYearRecalculation(
            year=year,
            reason=reason,
            previous_emissions=prev_em,
            adjusted_emissions=adj_em,
            created_by=user_id,
        )
        db.session.add(recalc)

        # Keep BaseYear singleton synchronized
        base_year_singleton = db.session.get(BaseYear, 1)
        if base_year_singleton:
            base_year_singleton.year = year
        else:
            base_year_singleton = BaseYear(id=1, year=year, locked=1)
            db.session.add(base_year_singleton)

        db.session.flush()
        log_activity_and_notify(action="CREATE", record_id=f"base-year-{recalc.id}", user=user, request=request,
                                entity="BaseYearRecalculation",
                                details=f"Base year set to {year} ({reason}); previous {prev_em}, adjusted {adj_em} tCO2e")
        db.session.commit()
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
        return (
            jsonify(
                {"message": "Base year recalculated successfully", "id": recalc.id}
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return internal_error(e)


@managedata_bp.route("/base-years/<int:rec_id>", methods=["DELETE"])
@login_required
def delete_base_year_recalculation(rec_id):
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to modify base year recalculation data."}), 403
    # Audit A-05: the base year is organisation-wide; a region-restricted superuser may not move it
    if not user or user.role not in ["admin", "superuser"] or get_allowed_facility_ids(user) is not None:
        return jsonify({"error": "Organisation-wide administrator privileges required to modify base year recalculation data."}), 403
    try:
        rec = db.session.get(BaseYearRecalculation, rec_id)
        if not rec:
            return jsonify({"error": "Recalculation record not found"}), 404
        log_activity_and_notify(action="DELETE", record_id=f"base-year-{rec.id}", user=user, request=request,
                                entity="BaseYearRecalculation",
                                details=f"Base year recalculation {rec.id} (year {rec.year}: {rec.reason}) deleted")
        db.session.delete(rec)
        db.session.commit()

        # Resync singleton with latest remaining
        latest = BaseYearRecalculation.query.order_by(
            BaseYearRecalculation.recalc_date.desc()
        ).first()
        if latest:
            singleton = db.session.get(BaseYear, 1)
            if singleton:
                singleton.year = latest.year
                db.session.commit()

        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
        return jsonify({"message": "Recalculation record deleted"})
    except Exception as e:
        db.session.rollback()
        return internal_error(e)


@managedata_bp.route("/sbti", methods=["GET", "POST"])
@managedata_bp.route("/manage/sbti", methods=["GET", "POST"])
@login_required
def manage_sbti():
    from models import SbtiTarget, Emission, Scope2Emission, Scope3Emission, BaseYearRecalculation
    from routes.dashboard import clear_dashboard_cache
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT administrators are not authorized to access SBTi targets."}), 403

    if request.method == "GET":
        target = SbtiTarget.query.order_by(SbtiTarget.created_at.desc()).first()
        
        # Calculate suggested base year baseline from verified emissions or BaseYearRecalculation
        requested_by = request.args.get("base_year")
        if requested_by:
            try:
                calc_year = int(requested_by)
            except ValueError:
                calc_year = target.base_year if target else 2024
        else:
            calc_year = target.base_year if target else 2024

        # BUG-032: the suggestion is computed only over the caller's facilities
        allowed_fids = get_allowed_facility_ids(user)
        per_scope = _verified_totals_by_scope(calc_year, allowed_fids)
        recalc = BaseYearRecalculation.query.filter_by(year=calc_year).order_by(BaseYearRecalculation.recalc_date.desc()).first()
        if recalc and recalc.adjusted_emissions and allowed_fids is None:
            suggested_emissions = float(recalc.adjusted_emissions)
        else:
            suggested_emissions = per_scope["scope1"] + per_scope["scope2"] + per_scope["scope3"]

        if not target:
            return jsonify({
                "has_target": False,
                "suggested_base_year": calc_year,
                "suggested_base_year_emissions": round(suggested_emissions, 2),
                "suggested_by_scope": {k: round(v, 2) for k, v in per_scope.items()},
            })

        return jsonify({
            "has_target": True,
            "base_year": target.base_year,
            "base_year_emissions": target.base_year_emissions,
            "target_year": target.target_year,
            "reduction_rate_pct": target.reduction_rate_pct,
            "pathway_type": target.pathway_type,
            "scope_coverage": target.scope_coverage or "S1S2S3",
            "suggested_base_year": calc_year,
            "suggested_base_year_emissions": round(suggested_emissions, 2),
            "suggested_by_scope": {k: round(v, 2) for k, v in per_scope.items()},
        })

    # POST: the SBTi target is organisation-wide, so only unrestricted approvers may set it
    if not user or user.role not in ["admin", "superuser"] or get_allowed_facility_ids(user) is not None:
        return jsonify({"error": "Organisation-wide administrator privileges required to modify SBTi targets."}), 403
    data = request.get_json() or {}
    from input_validation import parse_number, ValidationError

    try:
        current_year = datetime.date.today().year
        base_year = int(parse_number(data.get("base_year"), "base_year", min_value=2015, max_value=current_year))
        base_year_emissions = parse_number(data.get("base_year_emissions"), "base_year_emissions", min_value=0)
        target_year = int(parse_number(data.get("target_year"), "target_year", required=False, default=2050))
        reduction_rate_pct = parse_number(data.get("reduction_rate_pct"), "reduction_rate_pct",
                                          required=False, default=4.2, max_value=25.0)
    except ValidationError as err:
        return jsonify({"error": err.message, "field": err.field}), 400
    pathway_type = str(data.get("pathway_type") or "1.5C").strip()
    scope_coverage = str(data.get("scope_coverage") or "S1S2S3").strip().upper()

    # BUG-034 (finite values, above) / BUG-059: validated pathway tied to its reduction rate
    if pathway_type not in SBTI_PATHWAY_MIN_RATE:
        return jsonify({"error": f"pathway_type must be one of {sorted(SBTI_PATHWAY_MIN_RATE)}"}), 400
    if scope_coverage not in ("S1S2S3", "S1S2"):
        return jsonify({"error": "scope_coverage must be 'S1S2S3' or 'S1S2'"}), 400
    if target_year <= base_year or target_year > 2070:
        return jsonify({"error": f"Target year must be greater than base year ({base_year}) and not exceed 2070."}), 400
    if base_year_emissions <= 0:
        return jsonify({"error": "Base year baseline emissions must be greater than 0 tCO2e."}), 400
    if reduction_rate_pct <= 0:
        return jsonify({"error": "Annual reduction rate must be between 0.1% and 25.0%."}), 400
    min_rate = SBTI_PATHWAY_MIN_RATE[pathway_type]
    if reduction_rate_pct < min_rate:
        return jsonify({"error": f"A {pathway_type} pathway requires an annual linear reduction of at least {min_rate}% (use 'custom' otherwise)."}), 400

    new_target = SbtiTarget(
        base_year=base_year,
        base_year_emissions=base_year_emissions,
        target_year=target_year,
        reduction_rate_pct=reduction_rate_pct,
        pathway_type=pathway_type,
        scope_coverage=scope_coverage,
        created_by=user.id,
    )
    db.session.add(new_target)
    log_activity_and_notify(
        action="CREATE", record_id="sbti", user=user, request=request, entity="SbtiTarget",
        details=f"SBTi target set: {pathway_type}, {scope_coverage}, base {base_year} = {base_year_emissions} t, {reduction_rate_pct}%/yr to {target_year}",
    )
    db.session.commit()
    clear_dashboard_cache()
    return jsonify({"message": "SBTi Target saved successfully"}), 201


# SBTi near-term linear annual reduction minimums (SBTi Corporate Net-Zero Standard / criteria v5):
# 1.5°C-aligned >= 4.2 %/yr, well-below 2°C >= 2.5 %/yr. "custom" targets are labelled as such.
SBTI_PATHWAY_MIN_RATE = {"1.5C": 4.2, "WB2C": 2.5, "custom": 0.1}


def _verified_totals_by_scope(year, allowed_fids):
    """Verified tCO2e per scope for one year, restricted to allowed facility ids (None = all)."""
    from models import Emission, Scope2Emission, Scope3Emission

    def total(col, model):
        q = db.session.query(db.func.coalesce(db.func.sum(col), 0.0)).filter(model.status == "Verified", model.year == year)
        if allowed_fids is not None:
            q = q.filter(model.facility_id.in_(allowed_fids or [-1]))
        return float(q.scalar() or 0.0)

    return {
        "scope1": total(db.func.coalesce(Emission.co2e_total, Emission.co2_emissions, 0.0), Emission),
        "scope2": total(Scope2Emission.co2e, Scope2Emission),
        "scope3": total(Scope3Emission.co2e, Scope3Emission),
    }


# --- Audit Stats Alias (/api/audit/stats) ---
@managedata_bp.route("/audit/stats", methods=["GET"])
@managedata_bp.route("/audit/stats/", methods=["GET"])
def managedata_audit_stats():
    from routes.audit import get_audit_stats
    return get_audit_stats()

