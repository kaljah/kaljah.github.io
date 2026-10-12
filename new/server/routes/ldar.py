"""LDAR (Leak Detection and Repair) REST API endpoints.

Implements EPA Method 21 and Optical Gas Imaging (OGI) leak survey tracking
along with Component Inventory management (BUG-0030 / BUG-ARCH-002).
"""
import datetime
from flask import jsonify, request
from extensions import db
from models import ComponentInventory, FugitiveSurvey, Facility, User
from routes.auth import login_required
from utils import get_allowed_facility_ids, get_current_user, is_it_role, log_activity_and_notify
from . import ldar_bp


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
    for key in ("equipment_type", "component_type", "service_type", "methodology", "factor_id",
                "factor_value", "factor_unit", "api_reference", "status", "description"):
        if key in data:
            setattr(comp, key, data[key])

    if "quantity" in data:
        try:
            comp.quantity = int(data["quantity"])
        except (ValueError, TypeError):
            pass
    if "operating_hours" in data:
        try:
            comp.operating_hours = float(data["operating_hours"])
        except (ValueError, TypeError):
            pass

    comp.updated_at = datetime.datetime.now(datetime.timezone.utc)
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
