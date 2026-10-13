"""LDAR (Leak Detection and Repair) REST API endpoints.

Implements EPA Method 21 and Optical Gas Imaging (OGI) leak survey tracking
along with Component Inventory management (BUG-0030 / BUG-ARCH-002).
"""
import datetime
from flask import jsonify, request
from extensions import db
from models import ComponentInventory, FugitiveSurvey, Facility, User, Notification
from routes.auth import login_required
from utils import get_allowed_facility_ids, get_current_user, is_it_role, log_activity_and_notify
from . import ldar_bp


def is_broken_status(status: str) -> bool:
    """Return True if status indicates a broken, damaged, or leaking component."""
    if not status:
        return False
    return str(status).strip().lower() in ("broken", "leaking", "damaged", "faulty", "needs repair")


def _serialize_component(comp):
    return {
        "id": comp.id,
        "facility_id": comp.facility_id,
        "facility_name": comp.facility.name if comp.facility else None,
        "emission_source_id": comp.emission_source_id,
        "equipment_type": comp.equipment_type,
        "component_type": comp.component_type,
        "service_type": comp.service_type,
        "quantity": comp.quantity,
        "operating_hours": comp.operating_hours,
        "methodology": comp.methodology,
        "factor_id": comp.factor_id,
        "factor_value": comp.factor_value,
        "factor_unit": comp.factor_unit,
        "api_reference": comp.api_reference,
        "status": comp.status,
        "description": comp.description,
        "created_by": comp.created_by,
        "created_at": comp.created_at.isoformat() if comp.created_at else None,
        "updated_at": comp.updated_at.isoformat() if comp.updated_at else None,
    }


def _serialize_survey(survey):
    return {
        "id": survey.id,
        "facility_id": survey.facility_id,
        "facility_name": survey.facility.name if survey.facility else None,
        "component_inventory_id": survey.component_inventory_id,
        "survey_method": survey.survey_method,
        "survey_date": survey.survey_date,
        "detection_threshold_ppm": survey.detection_threshold_ppm,
        "screening_value_ppm": survey.screening_value_ppm,
        "leak_status": survey.leak_status,
        "measured_emission_rate": survey.measured_emission_rate,
        "measurement_unit": survey.measurement_unit,
        "repair_date": survey.repair_date,
        "leaking_hours": survey.leaking_hours,
        "surveyor_name": survey.surveyor_name,
        "notes": survey.notes,
        "created_by": survey.created_by,
        "created_at": survey.created_at.isoformat() if survey.created_at else None,
    }


# ==============================================================================
# COMPONENT INVENTORIES
# ==============================================================================

@ldar_bp.route("/components", methods=["GET"])
@login_required
def list_components():
    """List component inventories filtered by facility and status."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify({"error": "Forbidden: IT personnel cannot access operational LDAR data"}), 403

    allowed_fids = get_allowed_facility_ids(user)
    query = ComponentInventory.query

    if allowed_fids is not None:
        query = query.filter(ComponentInventory.facility_id.in_(allowed_fids))

    fac_id = request.args.get("facility_id") or request.args.get("facilityId")
    if fac_id:
        try:
            fid = int(fac_id)
            if allowed_fids is not None and fid not in allowed_fids:
                return jsonify({"error": "Unauthorized: Outside your assigned facilities"}), 403
            query = query.filter(ComponentInventory.facility_id == fid)
        except ValueError:
            pass

    status_arg = request.args.get("status")
    if status_arg:
        query = query.filter(ComponentInventory.status == status_arg)

    components = query.order_by(ComponentInventory.id.desc()).all()
    return jsonify({"components": [_serialize_component(c) for c in components], "count": len(components)})


@ldar_bp.route("/components", methods=["POST"])
@login_required
def create_component():
    """Create a new component inventory item."""
    user = get_current_user()
    if is_it_role(user) or user.role == "auditor":
        return jsonify({"error": "Forbidden: Auditor and IT roles cannot modify LDAR components"}), 403

    data = request.get_json() or {}
    facility_id = data.get("facility_id")
    if not facility_id:
        return jsonify({"error": "Missing required field: facility_id"}), 400

    try:
        fid = int(facility_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid facility_id"}), 400

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and fid not in allowed_fids:
        return jsonify({"error": "Unauthorized: Outside your assigned facilities"}), 403

    facility = db.session.get(Facility, fid)
    if not facility:
        return jsonify({"error": "Facility not found"}), 404

    equipment_type = str(data.get("equipment_type") or "").strip()
    component_type = str(data.get("component_type") or "").strip()
    service_type = str(data.get("service_type") or "Gas").strip()

    if not equipment_type or not component_type:
        return jsonify({"error": "equipment_type and component_type are required"}), 400

    try:
        quantity = int(data.get("quantity", 1))
        if quantity < 0:
            return jsonify({"error": "quantity cannot be negative"}), 400
    except (ValueError, TypeError):
        quantity = 1

    try:
        operating_hours = float(data.get("operating_hours", 8760.0))
        if operating_hours < 0 or operating_hours > 8760.0:
            return jsonify({"error": "operating_hours must be between 0 and 8760"}), 400
    except (ValueError, TypeError):
        operating_hours = 8760.0

    comp = ComponentInventory(
        facility_id=fid,
        emission_source_id=data.get("emission_source_id"),
        equipment_type=equipment_type,
        component_type=component_type,
        service_type=service_type,
        quantity=quantity,
        operating_hours=operating_hours,
        methodology=str(data.get("methodology") or "Component Average"),
        factor_id=data.get("factor_id"),
        factor_value=data.get("factor_value"),
        factor_unit=data.get("factor_unit"),
        api_reference=data.get("api_reference"),
        status=data.get("status", "Active"),
        description=data.get("description"),
        created_by=user.id,
    )

    try:
        db.session.add(comp)
        db.session.flush()

        if is_broken_status(comp.status):
            Notification.create(
                title="LDAR Alert: Broken Component Added",
                message=f"A broken component ({comp.component_type} - {comp.equipment_type}) was recorded at {facility.name} (Status: {comp.status}).",
                type="warning",
                user_id=None,
                metadata={
                    "facility_id": comp.facility_id,
                    "facility_name": facility.name,
                    "component_id": comp.id,
                    "component_type": comp.component_type,
                    "equipment_type": comp.equipment_type,
                    "status": comp.status,
                    "created_by": user.fullName or user.email,
                },
            )

        db.session.commit()
        log_activity_and_notify(
            action="CREATE",
            record_id=str(comp.id),
            user=user,
            request=request,
            entity="ComponentInventory",
            entity_id=str(comp.id),
            details=f"Created component inventory {comp.component_type} for facility {facility.name}",
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create component inventory: {e}"}), 500

    return jsonify({"message": "Component created successfully", "component": _serialize_component(comp)}), 201


@ldar_bp.route("/components/<int:comp_id>", methods=["GET"])
@login_required
def get_component(comp_id):
    """Retrieve a single component inventory record."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify({"error": "Forbidden: IT personnel cannot access operational LDAR data"}), 403

    comp = db.session.get(ComponentInventory, comp_id)
    if not comp:
        return jsonify({"error": "Component not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and comp.facility_id not in allowed_fids:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify({"component": _serialize_component(comp)})


@ldar_bp.route("/components/<int:comp_id>", methods=["PUT"])
@login_required
def update_component(comp_id):
    """Update an existing component inventory record."""
    user = get_current_user()
    if is_it_role(user) or user.role == "auditor":
        return jsonify({"error": "Forbidden: Auditor and IT roles cannot modify LDAR components"}), 403

    comp = db.session.get(ComponentInventory, comp_id)
    if not comp:
        return jsonify({"error": "Component not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and comp.facility_id not in allowed_fids:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}
    old_status = comp.status
    for key in ("equipment_type", "component_type", "service_type", "methodology", "factor_id",
                "factor_value", "factor_unit", "api_reference", "status", "description"):
        if key in data:
            setattr(comp, key, data[key])

    if "quantity" in data:
        try:
            qty = int(data["quantity"])
            if qty < 0:
                return jsonify({"error": "quantity cannot be negative"}), 400
            comp.quantity = qty
        except (ValueError, TypeError):
            return jsonify({"error": "quantity must be an integer"}), 400
    if "operating_hours" in data:
        try:
            hrs = float(data["operating_hours"])
            if hrs < 0 or hrs > 8760.0:
                return jsonify({"error": "operating_hours must be between 0 and 8760"}), 400
            comp.operating_hours = hrs
        except (ValueError, TypeError):
            return jsonify({"error": "operating_hours must be a number"}), 400

    comp.updated_at = datetime.datetime.now(datetime.timezone.utc)
    if is_broken_status(comp.status) and not is_broken_status(old_status):
        facility_name = comp.facility.name if comp.facility else f"Facility #{comp.facility_id}"
        Notification.create(
            title="LDAR Alert: Component Marked Broken",
            message=f"Component #{comp.id} ({comp.component_type} - {comp.equipment_type}) was marked as '{comp.status}' at {facility_name}.",
            type="warning",
            user_id=None,
            metadata={
                "facility_id": comp.facility_id,
                "facility_name": facility_name,
                "component_id": comp.id,
                "component_type": comp.component_type,
                "equipment_type": comp.equipment_type,
                "status": comp.status,
                "updated_by": user.fullName or user.email,
            },
        )

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update component: {e}"}), 500

    return jsonify({"message": "Component updated successfully", "component": _serialize_component(comp)})


@ldar_bp.route("/components/<int:comp_id>", methods=["DELETE"])
@login_required
def delete_component(comp_id):
    """Delete a component inventory record."""
    user = get_current_user()
    if user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Forbidden: Only Administrators can delete LDAR components"}), 403

    comp = db.session.get(ComponentInventory, comp_id)
    if not comp:
        return jsonify({"error": "Component not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and comp.facility_id not in allowed_fids:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        db.session.delete(comp)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete component: {e}"}), 500

    return jsonify({"message": "Component deleted successfully"})


@ldar_bp.route("/components/bulk-update", methods=["POST"])
@login_required
def bulk_update_components():
    """Bulk update status, operating hours, or other attributes of components."""
    user = get_current_user()
    if is_it_role(user) or user.role == "auditor":
        return jsonify({"error": "Forbidden: Auditor and IT roles cannot modify LDAR components"}), 403

    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ids list is required and cannot be empty"}), 400

    try:
        int_ids = [int(i) for i in ids]
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid component IDs"}), 400

    allowed_fids = get_allowed_facility_ids(user)
    query = ComponentInventory.query.filter(ComponentInventory.id.in_(int_ids))
    if allowed_fids is not None:
        query = query.filter(ComponentInventory.facility_id.in_(allowed_fids))

    components = query.all()
    if not components:
        return jsonify({"error": "No matching components found or unauthorized"}), 404

    new_status = data.get("status")
    new_service_type = data.get("service_type")
    new_equipment_type = data.get("equipment_type")
    new_operating_hours = data.get("operating_hours")

    if new_operating_hours is not None:
        try:
            new_operating_hours = float(new_operating_hours)
            if new_operating_hours < 0 or new_operating_hours > 8760.0:
                return jsonify({"error": "operating_hours must be between 0 and 8760"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "operating_hours must be a valid number"}), 400

    broken_components_marked = []
    now = datetime.datetime.now(datetime.timezone.utc)

    for comp in components:
        old_status = comp.status
        if new_status is not None and str(new_status).strip():
            comp.status = str(new_status).strip()
            if is_broken_status(comp.status) and not is_broken_status(old_status):
                broken_components_marked.append(comp)
        if new_service_type is not None and str(new_service_type).strip():
            comp.service_type = str(new_service_type).strip()
        if new_equipment_type is not None and str(new_equipment_type).strip():
            comp.equipment_type = str(new_equipment_type).strip()
        if new_operating_hours is not None:
            comp.operating_hours = new_operating_hours
        comp.updated_at = now

    if broken_components_marked:
        Notification.create(
            title="LDAR Alert: Components Marked Broken",
            message=f"{len(broken_components_marked)} component(s) were marked as broken/leaking via bulk update.",
            type="warning",
            user_id=None,
            metadata={
                "component_ids": [c.id for c in broken_components_marked],
                "status": new_status,
                "updated_by": user.fullName or user.email,
            },
        )

    try:
        db.session.commit()
        log_activity_and_notify(
            action="BULK_UPDATE",
            record_id=str(len(components)),
            user=user,
            request=request,
            entity="ComponentInventory",
            entity_id="bulk",
            details=f"Bulk updated {len(components)} LDAR component(s)",
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to bulk update components: {e}"}), 500

    return jsonify({
        "message": f"Successfully updated {len(components)} component(s)",
        "updated_count": len(components),
        "updated_ids": [c.id for c in components],
    }), 200


@ldar_bp.route("/components/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_components():
    """Bulk delete component inventory records."""
    user = get_current_user()
    if user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Forbidden: Only Administrators can delete LDAR components"}), 403

    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ids list is required and cannot be empty"}), 400

    try:
        int_ids = [int(i) for i in ids]
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid component IDs"}), 400

    allowed_fids = get_allowed_facility_ids(user)
    query = ComponentInventory.query.filter(ComponentInventory.id.in_(int_ids))
    if allowed_fids is not None:
        query = query.filter(ComponentInventory.facility_id.in_(allowed_fids))

    components = query.all()
    if not components:
        return jsonify({"error": "No matching components found or unauthorized"}), 404

    deleted_count = len(components)
    for comp in components:
        db.session.delete(comp)

    try:
        db.session.commit()
        log_activity_and_notify(
            action="BULK_DELETE",
            record_id=str(deleted_count),
            user=user,
            request=request,
            entity="ComponentInventory",
            entity_id="bulk",
            details=f"Bulk deleted {deleted_count} LDAR component(s)",
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to bulk delete components: {e}"}), 500

    return jsonify({
        "message": f"Successfully deleted {deleted_count} component(s)",
        "deleted_count": deleted_count,
    }), 200


# ==============================================================================
# FUGITIVE SURVEYS
# ==============================================================================

@ldar_bp.route("/surveys", methods=["GET"])
@login_required
def list_surveys():
    """List leak detection surveys."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify({"error": "Forbidden: IT personnel cannot access operational LDAR data"}), 403

    allowed_fids = get_allowed_facility_ids(user)
    query = FugitiveSurvey.query

    if allowed_fids is not None:
        query = query.filter(FugitiveSurvey.facility_id.in_(allowed_fids))

    fac_id = request.args.get("facility_id") or request.args.get("facilityId")
    if fac_id:
        try:
            fid = int(fac_id)
            if allowed_fids is not None and fid not in allowed_fids:
                return jsonify({"error": "Unauthorized: Outside your assigned facilities"}), 403
            query = query.filter(FugitiveSurvey.facility_id == fid)
        except ValueError:
            pass

    leak_status = request.args.get("leak_status")
    if leak_status:
        query = query.filter(FugitiveSurvey.leak_status == leak_status)

    surveys = query.order_by(FugitiveSurvey.id.desc()).all()
    return jsonify({"surveys": [_serialize_survey(s) for s in surveys], "count": len(surveys)})


@ldar_bp.route("/surveys", methods=["POST"])
@login_required
def create_survey():
    """Create a new fugitive leak survey record."""
    user = get_current_user()
    if is_it_role(user) or user.role == "auditor":
        return jsonify({"error": "Forbidden: Auditor and IT roles cannot modify LDAR surveys"}), 403

    data = request.get_json() or {}
    facility_id = data.get("facility_id")
    if not facility_id:
        return jsonify({"error": "Missing required field: facility_id"}), 400

    try:
        fid = int(facility_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid facility_id"}), 400

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and fid not in allowed_fids:
        return jsonify({"error": "Unauthorized: Outside your assigned facilities"}), 403

    facility = db.session.get(Facility, fid)
    if not facility:
        return jsonify({"error": "Facility not found"}), 404

    survey_method = str(data.get("survey_method") or "Method 21").strip()
    survey_date = str(data.get("survey_date") or datetime.date.today().isoformat()).strip()

    survey = FugitiveSurvey(
        facility_id=fid,
        component_inventory_id=data.get("component_inventory_id"),
        survey_method=survey_method,
        survey_date=survey_date,
        detection_threshold_ppm=data.get("detection_threshold_ppm"),
        screening_value_ppm=data.get("screening_value_ppm"),
        leak_status=data.get("leak_status", "Non-leaking"),
        measured_emission_rate=data.get("measured_emission_rate"),
        measurement_unit=data.get("measurement_unit", "kg/hr"),
        repair_date=data.get("repair_date"),
        leaking_hours=float(data["leaking_hours"]) if data.get("leaking_hours") is not None else 8760.0,
        surveyor_name=data.get("surveyor_name", user.fullName),
        notes=data.get("notes"),
        created_by=user.id,
    )

    try:
        db.session.add(survey)
        db.session.flush()

        if survey.leak_status == "Leaking":
            Notification.create(
                title="LDAR Alert: Leak Detected in Survey",
                message=f"A leak was detected during {survey.survey_method} survey at {facility.name} (Screening: {survey.screening_value_ppm or 0} ppm).",
                type="warning",
                user_id=None,
                metadata={
                    "facility_id": survey.facility_id,
                    "facility_name": facility.name,
                    "survey_id": survey.id,
                    "component_inventory_id": survey.component_inventory_id,
                    "screening_value_ppm": survey.screening_value_ppm,
                    "survey_method": survey.survey_method,
                    "surveyor_name": survey.surveyor_name,
                },
            )

        db.session.commit()
        log_activity_and_notify(
            action="CREATE",
            record_id=str(survey.id),
            user=user,
            request=request,
            entity="FugitiveSurvey",
            entity_id=str(survey.id),
            details=f"Logged LDAR survey ({survey.survey_method}) for facility {facility.name}",
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to log fugitive survey: {e}"}), 500

    return jsonify({"message": "Survey recorded successfully", "survey": _serialize_survey(survey)}), 201


@ldar_bp.route("/surveys/<int:survey_id>", methods=["GET"])
@login_required
def get_survey(survey_id):
    """Retrieve a single fugitive survey record."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify({"error": "Forbidden: IT personnel cannot access operational LDAR data"}), 403

    survey = db.session.get(FugitiveSurvey, survey_id)
    if not survey:
        return jsonify({"error": "Survey not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and survey.facility_id not in allowed_fids:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify({"survey": _serialize_survey(survey)})


@ldar_bp.route("/surveys/<int:survey_id>", methods=["PUT", "PATCH"])
@login_required
def update_survey(survey_id):
    """Update a fugitive survey record (e.g. record leak repairs, post-repair PPM)."""
    user = get_current_user()
    if is_it_role(user) or user.role in ["auditor", "viewer"]:
        return jsonify({"error": "Forbidden: Read-only and IT roles cannot modify LDAR surveys"}), 403

    survey = db.session.get(FugitiveSurvey, survey_id)
    if not survey:
        return jsonify({"error": "Survey not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and survey.facility_id not in allowed_fids:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json() or {}
    old_leak_status = survey.leak_status
    updatable_fields = [
        "survey_method", "survey_date", "detection_threshold_ppm",
        "screening_value_ppm", "leak_status", "measured_emission_rate",
        "measurement_unit", "repair_date", "leaking_hours",
        "surveyor_name", "notes"
    ]
    for f in updatable_fields:
        if f in data:
            val = data[f]
            if f == "leaking_hours" and val is not None:
                try:
                    val = float(val)
                except (ValueError, TypeError):
                    val = survey.leaking_hours
            setattr(survey, f, val)

    if survey.leak_status == "Leaking" and old_leak_status != "Leaking":
        fac_name = survey.facility.name if survey.facility else f"Facility #{survey.facility_id}"
        Notification.create(
            title="LDAR Alert: Survey Marked Leaking",
            message=f"Survey #{survey.id} was marked as Leaking at {fac_name}.",
            type="warning",
            user_id=None,
            metadata={
                "facility_id": survey.facility_id,
                "facility_name": fac_name,
                "survey_id": survey.id,
                "screening_value_ppm": survey.screening_value_ppm,
                "updated_by": user.fullName or user.email,
            },
        )

    try:
        db.session.commit()
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(survey.id),
            user=user,
            request=request,
            entity="FugitiveSurvey",
            entity_id=str(survey.id),
            details=f"Updated LDAR survey for facility {survey.facility.name if survey.facility else survey.facility_id}",
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update survey: {e}"}), 500

    return jsonify({"message": "Survey updated successfully", "survey": _serialize_survey(survey)}), 200


@ldar_bp.route("/surveys/<int:survey_id>", methods=["DELETE"])
@login_required
def delete_survey(survey_id):
    """Delete a fugitive survey record."""
    user = get_current_user()
    if user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Forbidden: Only Administrators can delete LDAR surveys"}), 403

    survey = db.session.get(FugitiveSurvey, survey_id)
    if not survey:
        return jsonify({"error": "Survey not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and survey.facility_id not in allowed_fids:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        db.session.delete(survey)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete survey: {e}"}), 500

    return jsonify({"message": "Survey deleted successfully"})


@ldar_bp.route("/surveys/bulk-update", methods=["POST"])
@login_required
def bulk_update_surveys():
    """Bulk update leak status, repair date, or notes on fugitive surveys."""
    user = get_current_user()
    if is_it_role(user) or user.role in ["auditor", "viewer"]:
        return jsonify({"error": "Forbidden: Read-only and IT roles cannot modify LDAR surveys"}), 403

    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ids list is required and cannot be empty"}), 400

    try:
        int_ids = [int(i) for i in ids]
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid survey IDs"}), 400

    allowed_fids = get_allowed_facility_ids(user)
    query = FugitiveSurvey.query.filter(FugitiveSurvey.id.in_(int_ids))
    if allowed_fids is not None:
        query = query.filter(FugitiveSurvey.facility_id.in_(allowed_fids))

    surveys = query.all()
    if not surveys:
        return jsonify({"error": "No matching surveys found or unauthorized"}), 404

    new_leak_status = data.get("leak_status")
    repair_date = data.get("repair_date")
    notes = data.get("notes")
    survey_method = data.get("survey_method")
    post_repair_ppm = data.get("screening_value_ppm")

    leaks_marked = []
    for s in surveys:
        old_leak_status = s.leak_status
        if new_leak_status is not None and str(new_leak_status).strip():
            s.leak_status = str(new_leak_status).strip()
            if s.leak_status == "Leaking" and old_leak_status != "Leaking":
                leaks_marked.append(s)
        if repair_date is not None:
            s.repair_date = str(repair_date).strip() if repair_date else None
        if post_repair_ppm is not None:
            try:
                s.screening_value_ppm = float(post_repair_ppm)
            except (ValueError, TypeError):
                pass
        if notes:
            note_str = str(notes).strip()
            if note_str:
                s.notes = f"{s.notes} | {note_str}" if s.notes else note_str
        if survey_method is not None and str(survey_method).strip():
            s.survey_method = str(survey_method).strip()

    if leaks_marked:
        Notification.create(
            title="LDAR Alert: Surveys Marked Leaking",
            message=f"{len(leaks_marked)} survey(s) were updated to Leaking status.",
            type="warning",
            user_id=None,
            metadata={
                "survey_ids": [s.id for s in leaks_marked],
                "updated_by": user.fullName or user.email,
            },
        )

    try:
        db.session.commit()
        log_activity_and_notify(
            action="BULK_UPDATE",
            record_id=str(len(surveys)),
            user=user,
            request=request,
            entity="FugitiveSurvey",
            entity_id="bulk",
            details=f"Bulk updated {len(surveys)} LDAR survey(s)",
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to bulk update surveys: {e}"}), 500

    return jsonify({
        "message": f"Successfully updated {len(surveys)} survey(s)",
        "updated_count": len(surveys),
        "updated_ids": [s.id for s in surveys],
    }), 200


@ldar_bp.route("/surveys/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_surveys():
    """Bulk delete fugitive survey records."""
    user = get_current_user()
    if user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Forbidden: Only Administrators can delete LDAR surveys"}), 403

    data = request.get_json() or {}
    ids = data.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "ids list is required and cannot be empty"}), 400

    try:
        int_ids = [int(i) for i in ids]
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid survey IDs"}), 400

    allowed_fids = get_allowed_facility_ids(user)
    query = FugitiveSurvey.query.filter(FugitiveSurvey.id.in_(int_ids))
    if allowed_fids is not None:
        query = query.filter(FugitiveSurvey.facility_id.in_(allowed_fids))

    surveys = query.all()
    if not surveys:
        return jsonify({"error": "No matching surveys found or unauthorized"}), 404

    deleted_count = len(surveys)
    for s in surveys:
        db.session.delete(s)

    try:
        db.session.commit()
        log_activity_and_notify(
            action="BULK_DELETE",
            record_id=str(deleted_count),
            user=user,
            request=request,
            entity="FugitiveSurvey",
            entity_id="bulk",
            details=f"Bulk deleted {deleted_count} LDAR survey(s)",
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to bulk delete surveys: {e}"}), 500

    return jsonify({
        "message": f"Successfully deleted {deleted_count} survey(s)",
        "deleted_count": deleted_count,
    }), 200
