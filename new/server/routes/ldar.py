"""LDAR (Leak Detection and Repair) REST API endpoints.

Implements EPA Method 21 and Optical Gas Imaging (OGI) leak survey tracking
along with Component Inventory management (BUG-0030 / BUG-ARCH-002).

Numbers and dates are read strictly (400 naming the field; an unreadable quantity was 1, unreadable
hours 8,760 and a text ppm a 500), and every change commits its audit entry in the same transaction
(the entries were added after the commit and discarded with the request; edits and deletes had none).
"""
import datetime
from flask import jsonify, request
from extensions import db
from input_validation import ValidationError, parse_number
from models import ComponentInventory, FugitiveSurvey, Facility, Notification
from routes.auth import login_required
from utils import get_allowed_facility_ids, get_current_user, internal_error, is_it_role, log_activity_and_notify
from services.dashboard_filters import _parse_facility_ids
from . import ldar_bp

HOURS_PER_YEAR = 8760.0
COMPONENT_FIELDS = ("equipment_type", "component_type", "service_type", "methodology", "factor_id",
                    "factor_value", "factor_unit", "api_reference", "status", "description")
SURVEY_FIELDS = ("survey_method", "survey_date", "detection_threshold_ppm", "screening_value_ppm", "leak_status",
                 "measured_emission_rate", "measurement_unit", "repair_date", "leaking_hours", "surveyor_name", "notes")
NUMBER_LIMITS = {  # field: (min, max)
    "quantity": (0, None), "operating_hours": (0, HOURS_PER_YEAR), "leaking_hours": (0, HOURS_PER_YEAR),
    "factor_value": (0, None), "detection_threshold_ppm": (0, 1e6), "screening_value_ppm": (0, 1e6),
    "measured_emission_rate": (0, None),
}
_FORBIDDEN_READ = ({"error": "Forbidden: IT personnel cannot access operational LDAR data"}, 403)


def is_broken_status(status: str) -> bool:
    """Return True if status indicates a broken, damaged, or leaking component."""
    if not status:
        return False
    return str(status).strip().lower() in ("broken", "leaking", "damaged", "faulty", "needs repair")


def _value(field, raw):
    """A request value as stored: numbers parsed within their limits, dates as YYYY-MM-DD."""
    if field in NUMBER_LIMITS:
        lo, hi = NUMBER_LIMITS[field]
        number = parse_number(raw, field, required=False, min_value=lo, max_value=hi)
        if field == "quantity" and number is not None:
            if number != int(number):
                raise ValidationError("'quantity' must be a whole number", field)
            return int(number)
        return number
    if field in ("survey_date", "repair_date"):
        if raw in (None, ""):
            return None
        try:
            return datetime.date.fromisoformat(str(raw).strip()).isoformat()
        except ValueError:
            raise ValidationError(f"'{field}' must be a date (YYYY-MM-DD)", field)
    return raw


def _serialize_component(comp):
    return {
        "id": comp.id,
        "facility_id": comp.facility_id,
        "facility_name": comp.facility.name if comp.facility else None,
        "emission_source_id": comp.emission_source_id,
        **{f: getattr(comp, f) for f in COMPONENT_FIELDS},
        "quantity": comp.quantity,
        "operating_hours": comp.operating_hours,
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
        **{f: getattr(survey, f) for f in SURVEY_FIELDS},
        "created_by": survey.created_by,
        "created_at": survey.created_at.isoformat() if survey.created_at else None,
    }


def _scoped_list(model, user):
    """The model's query within the user's facilities and the facility_id filter; (query, error)."""
    allowed = get_allowed_facility_ids(user)
    query = model.query if allowed is None else model.query.filter(model.facility_id.in_(allowed))
    fac = request.args.get("facility_id") or request.args.get("facilityId")
    parts = [p.strip() for p in str(fac or "").split(",") if p.strip() and p.strip().lower() != "all"]
    if any(not p.isdigit() for p in parts):  # an unreadable ID is refused, never dropped (it widened the list)
        return None, (jsonify({"error": "Invalid facility_id: must be positive integers", "field": "facility_id"}), 422)
    parsed_fids = _parse_facility_ids(",".join(parts)) if parts else None
    if parsed_fids is not None:
        if allowed is not None and not set(parsed_fids).issubset(set(allowed)):
            return None, (jsonify({"error": "Unauthorized: Outside your assigned facilities"}), 403)
        query = query.filter(model.facility_id.in_(parsed_fids))
    return query, None


def _target_facility(user, data):
    """(Facility, error) for a create request."""
    raw = data.get("facility_id")
    if not raw:
        return None, (jsonify({"error": "Missing required field: facility_id"}), 400)
    try:
        fid = int(raw)
    except (ValueError, TypeError):
        return None, (jsonify({"error": "Invalid facility_id"}), 400)
    allowed = get_allowed_facility_ids(user)
    if allowed is not None and fid not in allowed:
        return None, (jsonify({"error": "Unauthorized: Outside your assigned facilities"}), 403)
    facility = db.session.get(Facility, fid)
    if not facility:
        return None, (jsonify({"error": "Facility not found"}), 404)
    return facility, None


def _scoped_get(model, obj_id, user, label):
    """(object, error) for one record within the user's facilities."""
    obj = db.session.get(model, obj_id)
    if not obj:
        return None, (jsonify({"error": f"{label} not found"}), 404)
    allowed = get_allowed_facility_ids(user)
    if allowed is not None and obj.facility_id not in allowed:
        return None, (jsonify({"error": "Unauthorized"}), 403)
    return obj, None


def _scoped_ids(model, user, data, label):
    """(records, error) for a bulk request's ids within the user's facilities."""
    ids = data.get("ids", [])
    if not isinstance(ids, list) or not ids:
        return None, (jsonify({"error": "ids list is required and cannot be empty"}), 400)
    try:
        int_ids = [int(i) for i in ids]
    except (ValueError, TypeError):
        return None, (jsonify({"error": f"Invalid {label} IDs"}), 400)
    query = model.query.filter(model.id.in_(int_ids))
    allowed = get_allowed_facility_ids(user)
    if allowed is not None:
        query = query.filter(model.facility_id.in_(allowed))
    records = query.all()
    if not records:
        return None, (jsonify({"error": f"No matching {label}s found or unauthorized"}), 404)
    return records, None


def _commit(user, action, entity, entity_id, details, failure, facility_id=None, old=None, new=None):
    """Commit the change together with its audit entry; a generic 500 on failure."""
    try:
        log_activity_and_notify(action=action, record_id=str(entity_id), user=user, request=request, entity=entity,
                                entity_id=str(entity_id), details=details, facility_id=facility_id,
                                old_values=old, new_values=new)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return internal_error(exc, failure)
    return None


def _notify(title, message, metadata):
    Notification.create(title=title, message=message, type="warning", user_id=None, metadata=metadata)


def _check_component_link(survey_facility_id, comp_id):
    """A survey's component must exist at the survey's facility."""
    if comp_id in (None, ""):
        return None
    try:
        comp = db.session.get(ComponentInventory, int(comp_id))
    except (ValueError, TypeError):
        comp = None
    if comp is None or comp.facility_id != survey_facility_id:
        raise ValidationError("component_inventory_id is not a component of this facility", "component_inventory_id")
    return comp.id


# ==============================================================================
# COMPONENT INVENTORIES
# ==============================================================================

@ldar_bp.route("/components", methods=["GET"])
@login_required
def list_components():
    """List component inventories filtered by facility and status."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify(_FORBIDDEN_READ[0]), _FORBIDDEN_READ[1]
    query, err = _scoped_list(ComponentInventory, user)
    if err:
        return err
    if request.args.get("status") and request.args.get("status").lower() != "all":
        query = query.filter(ComponentInventory.status == request.args["status"])
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
    facility, err = _target_facility(user, data)
    if err:
        return err
    equipment_type = str(data.get("equipment_type") or "").strip()
    component_type = str(data.get("component_type") or "").strip()
    if not equipment_type or not component_type:
        return jsonify({"error": "equipment_type and component_type are required"}), 400
    quantity = _value("quantity", data.get("quantity"))
    hours = _value("operating_hours", data.get("operating_hours"))
    comp = ComponentInventory(
        facility_id=facility.id,
        emission_source_id=data.get("emission_source_id"),
        equipment_type=equipment_type,
        component_type=component_type,
        service_type=str(data.get("service_type") or "Gas").strip(),
        quantity=1 if quantity is None else quantity,
        operating_hours=HOURS_PER_YEAR if hours is None else hours,
        methodology=str(data.get("methodology") or "Component Average"),
        factor_id=data.get("factor_id"),
        factor_value=_value("factor_value", data.get("factor_value")),
        factor_unit=data.get("factor_unit"),
        api_reference=data.get("api_reference"),
        status=data.get("status", "Active"),
        description=data.get("description"),
        created_by=user.id,
    )
    db.session.add(comp)
    db.session.flush()
    if is_broken_status(comp.status):
        _notify("LDAR Alert: Broken Component Added",
                f"A broken component ({comp.component_type} - {comp.equipment_type}) was recorded at {facility.name} "
                f"(Status: {comp.status}).",
                {"facility_id": comp.facility_id, "facility_name": facility.name, "component_id": comp.id,
                 "component_type": comp.component_type, "equipment_type": comp.equipment_type, "status": comp.status,
                 "created_by": user.fullName or user.email})
    err = _commit(user, "CREATE", "ComponentInventory", comp.id,
                  f"Created component inventory {comp.component_type} for facility {facility.name}",
                  "Failed to create component inventory", facility_id=comp.facility_id,
                  new=_serialize_component(comp))
    if err:
        return err
    return jsonify({"message": "Component created successfully", "component": _serialize_component(comp)}), 201


@ldar_bp.route("/components/<int:comp_id>", methods=["GET"])
@login_required
def get_component(comp_id):
    """Retrieve a single component inventory record."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify(_FORBIDDEN_READ[0]), _FORBIDDEN_READ[1]
    comp, err = _scoped_get(ComponentInventory, comp_id, user, "Component")
    return err or jsonify({"component": _serialize_component(comp)})


@ldar_bp.route("/components/<int:comp_id>", methods=["PUT"])
@login_required
def update_component(comp_id):
    """Update an existing component inventory record."""
    user = get_current_user()
    if is_it_role(user) or user.role == "auditor":
        return jsonify({"error": "Forbidden: Auditor and IT roles cannot modify LDAR components"}), 403
    comp, err = _scoped_get(ComponentInventory, comp_id, user, "Component")
    if err:
        return err
    data = request.get_json() or {}
    before = _serialize_component(comp)
    for key in COMPONENT_FIELDS + ("quantity", "operating_hours"):
        if key in data:
            value = _value(key, data[key])
            if value is None and key in ("quantity", "operating_hours"):
                raise ValidationError(f"'{key}' cannot be empty", key)
            setattr(comp, key, value)
    comp.updated_at = datetime.datetime.now(datetime.timezone.utc)
    if is_broken_status(comp.status) and not is_broken_status(before["status"]):
        facility_name = comp.facility.name if comp.facility else f"Facility #{comp.facility_id}"
        _notify("LDAR Alert: Component Marked Broken",
                f"Component #{comp.id} ({comp.component_type} - {comp.equipment_type}) was marked as '{comp.status}' "
                f"at {facility_name}.",
                {"facility_id": comp.facility_id, "facility_name": facility_name, "component_id": comp.id,
                 "component_type": comp.component_type, "equipment_type": comp.equipment_type, "status": comp.status,
                 "updated_by": user.fullName or user.email})
    err = _commit(user, "UPDATE", "ComponentInventory", comp.id, f"Updated LDAR component #{comp.id}",
                  "Failed to update component", facility_id=comp.facility_id, old=before,
                  new=_serialize_component(comp))
    return err or jsonify({"message": "Component updated successfully", "component": _serialize_component(comp)})


@ldar_bp.route("/components/<int:comp_id>", methods=["DELETE"])
@login_required
def delete_component(comp_id):
    """Delete a component inventory record."""
    user = get_current_user()
    if user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Forbidden: Only Administrators can delete LDAR components"}), 403
    comp, err = _scoped_get(ComponentInventory, comp_id, user, "Component")
    if err:
        return err
    before = _serialize_component(comp)
    db.session.delete(comp)
    err = _commit(user, "DELETE", "ComponentInventory", comp_id, f"Deleted LDAR component #{comp_id}",
                  "Failed to delete component", facility_id=before["facility_id"], old=before)
    return err or jsonify({"message": "Component deleted successfully"})


@ldar_bp.route("/components/bulk-update", methods=["POST"])
@login_required
def bulk_update_components():
    """Bulk update status, operating hours, or other attributes of components."""
    user = get_current_user()
    if is_it_role(user) or user.role == "auditor":
        return jsonify({"error": "Forbidden: Auditor and IT roles cannot modify LDAR components"}), 403
    data = request.get_json() or {}
    components, err = _scoped_ids(ComponentInventory, user, data, "component")
    if err:
        return err
    hours = _value("operating_hours", data.get("operating_hours"))
    text = {k: str(data[k]).strip() for k in ("status", "service_type", "equipment_type")
            if data.get(k) is not None and str(data[k]).strip()}
    marked = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for comp in components:
        was_broken = is_broken_status(comp.status)
        for key, value in text.items():
            setattr(comp, key, value)
        if "status" in text and is_broken_status(comp.status) and not was_broken:
            marked.append(comp)
        if hours is not None:
            comp.operating_hours = hours
        comp.updated_at = now
    if marked:
        _notify("LDAR Alert: Components Marked Broken",
                f"{len(marked)} component(s) were marked as broken/leaking via bulk update.",
                {"component_ids": [c.id for c in marked], "status": data.get("status"),
                 "updated_by": user.fullName or user.email})
    err = _commit(user, "BULK_UPDATE", "ComponentInventory", "bulk",
                  f"Bulk updated {len(components)} LDAR component(s): {[c.id for c in components]}",
                  "Failed to bulk update components", new=dict(text, operating_hours=hours))
    if err:
        return err
    return jsonify({"message": f"Successfully updated {len(components)} component(s)",
                    "updated_count": len(components), "updated_ids": [c.id for c in components]}), 200


@ldar_bp.route("/components/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_components():
    """Bulk delete component inventory records."""
    user = get_current_user()
    if user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Forbidden: Only Administrators can delete LDAR components"}), 403
    components, err = _scoped_ids(ComponentInventory, user, request.get_json() or {}, "component")
    if err:
        return err
    ids = [c.id for c in components]
    for comp in components:
        db.session.delete(comp)
    err = _commit(user, "BULK_DELETE", "ComponentInventory", "bulk", f"Bulk deleted {len(ids)} LDAR component(s): {ids}",
                  "Failed to bulk delete components")
    return err or (jsonify({"message": f"Successfully deleted {len(ids)} component(s)", "deleted_count": len(ids)}), 200)


# ==============================================================================
# FUGITIVE SURVEYS
# ==============================================================================

@ldar_bp.route("/surveys", methods=["GET"])
@login_required
def list_surveys():
    """List leak detection surveys."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify(_FORBIDDEN_READ[0]), _FORBIDDEN_READ[1]
    query, err = _scoped_list(FugitiveSurvey, user)
    if err:
        return err
    if request.args.get("leak_status") and request.args.get("leak_status").lower() != "all":
        query = query.filter(FugitiveSurvey.leak_status == request.args["leak_status"])
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
    facility, err = _target_facility(user, data)
    if err:
        return err
    values = {f: _value(f, data.get(f)) for f in SURVEY_FIELDS if f in data}
    values["survey_method"] = str(data.get("survey_method") or "Method 21").strip()
    values["survey_date"] = values.get("survey_date") or datetime.date.today().isoformat()
    values.setdefault("leak_status", "Non-leaking")
    values.setdefault("measurement_unit", "kg/hr")
    values.setdefault("surveyor_name", user.fullName)
    if values.get("leaking_hours") is None:
        values["leaking_hours"] = HOURS_PER_YEAR
    if values.get("repair_date") and values.get("survey_date") and values["repair_date"] < values["survey_date"]:
        raise ValidationError("repair_date cannot precede survey_date", "repair_date")
    survey = FugitiveSurvey(facility_id=facility.id, created_by=user.id,
                            component_inventory_id=_check_component_link(facility.id, data.get("component_inventory_id")),
                            **values)
    db.session.add(survey)
    db.session.flush()
    if survey.leak_status == "Leaking":
        _notify("LDAR Alert: Leak Detected in Survey",
                f"A leak was detected during {survey.survey_method} survey at {facility.name} "
                f"(Screening: {survey.screening_value_ppm or 0} ppm).",
                {"facility_id": survey.facility_id, "facility_name": facility.name, "survey_id": survey.id,
                 "component_inventory_id": survey.component_inventory_id,
                 "screening_value_ppm": survey.screening_value_ppm, "survey_method": survey.survey_method,
                 "surveyor_name": survey.surveyor_name})
    err = _commit(user, "CREATE", "FugitiveSurvey", survey.id,
                  f"Logged LDAR survey ({survey.survey_method}) for facility {facility.name}",
                  "Failed to log fugitive survey", facility_id=survey.facility_id, new=_serialize_survey(survey))
    return err or (jsonify({"message": "Survey recorded successfully", "survey": _serialize_survey(survey)}), 201)


@ldar_bp.route("/surveys/<int:survey_id>", methods=["GET"])
@login_required
def get_survey(survey_id):
    """Retrieve a single fugitive survey record."""
    user = get_current_user()
    if is_it_role(user):
        return jsonify(_FORBIDDEN_READ[0]), _FORBIDDEN_READ[1]
    survey, err = _scoped_get(FugitiveSurvey, survey_id, user, "Survey")
    return err or jsonify({"survey": _serialize_survey(survey)})


@ldar_bp.route("/surveys/<int:survey_id>", methods=["PUT", "PATCH"])
@login_required
def update_survey(survey_id):
    """Update a fugitive survey record (e.g. record leak repairs, post-repair PPM)."""
    user = get_current_user()
    if is_it_role(user) or user.role in ["auditor", "viewer"]:
        return jsonify({"error": "Forbidden: Read-only and IT roles cannot modify LDAR surveys"}), 403
    survey, err = _scoped_get(FugitiveSurvey, survey_id, user, "Survey")
    if err:
        return err
    data = request.get_json() or {}
    before = _serialize_survey(survey)
    for f in SURVEY_FIELDS:
        if f in data:
            value = _value(f, data[f])
            if value is None and f in ("survey_date", "leaking_hours"):
                raise ValidationError(f"'{f}' cannot be empty", f)
            setattr(survey, f, value)
    if survey.repair_date and survey.survey_date and survey.repair_date < survey.survey_date:  # either date edited
        raise ValidationError("repair_date cannot precede survey_date", "repair_date")
    if survey.leak_status == "Leaking" and before["leak_status"] != "Leaking":
        fac_name = survey.facility.name if survey.facility else f"Facility #{survey.facility_id}"
        _notify("LDAR Alert: Survey Marked Leaking", f"Survey #{survey.id} was marked as Leaking at {fac_name}.",
                {"facility_id": survey.facility_id, "facility_name": fac_name, "survey_id": survey.id,
                 "screening_value_ppm": survey.screening_value_ppm, "updated_by": user.fullName or user.email})
    err = _commit(user, "UPDATE", "FugitiveSurvey", survey.id,
                  f"Updated LDAR survey for facility {survey.facility.name if survey.facility else survey.facility_id}",
                  "Failed to update survey", facility_id=survey.facility_id, old=before, new=_serialize_survey(survey))
    return err or (jsonify({"message": "Survey updated successfully", "survey": _serialize_survey(survey)}), 200)


@ldar_bp.route("/surveys/<int:survey_id>", methods=["DELETE"])
@login_required
def delete_survey(survey_id):
    """Delete a fugitive survey record."""
    user = get_current_user()
    if user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Forbidden: Only Administrators can delete LDAR surveys"}), 403
    survey, err = _scoped_get(FugitiveSurvey, survey_id, user, "Survey")
    if err:
        return err
    before = _serialize_survey(survey)
    db.session.delete(survey)
    err = _commit(user, "DELETE", "FugitiveSurvey", survey_id, f"Deleted LDAR survey #{survey_id}",
                  "Failed to delete survey", facility_id=before["facility_id"], old=before)
    return err or jsonify({"message": "Survey deleted successfully"})


@ldar_bp.route("/surveys/bulk-update", methods=["POST"])
@login_required
def bulk_update_surveys():
    """Bulk update leak status, repair date, or notes on fugitive surveys."""
    user = get_current_user()
    if is_it_role(user) or user.role in ["auditor", "viewer"]:
        return jsonify({"error": "Forbidden: Read-only and IT roles cannot modify LDAR surveys"}), 403
    data = request.get_json() or {}
    surveys, err = _scoped_ids(FugitiveSurvey, user, data, "survey")
    if err:
        return err
    new_status = str(data.get("leak_status") or "").strip()
    method = str(data.get("survey_method") or "").strip()
    repair_date = _value("repair_date", data["repair_date"]) if "repair_date" in data and data["repair_date"] is not None else False
    ppm = _value("screening_value_ppm", data.get("screening_value_ppm"))
    note = str(data.get("notes") or "").strip()
    marked = []
    for s in surveys:
        if new_status:
            if new_status == "Leaking" and s.leak_status != "Leaking":
                marked.append(s)
            s.leak_status = new_status
        if repair_date is not False:
            if repair_date and s.survey_date and repair_date < s.survey_date:
                raise ValidationError(f"repair_date cannot precede survey #{s.id}'s survey_date", "repair_date")
            s.repair_date = repair_date
        if ppm is not None:
            s.screening_value_ppm = ppm
        if note:
            s.notes = f"{s.notes} | {note}" if s.notes else note
        if method:
            s.survey_method = method
    if marked:
        _notify("LDAR Alert: Surveys Marked Leaking", f"{len(marked)} survey(s) were updated to Leaking status.",
                {"survey_ids": [s.id for s in marked], "updated_by": user.fullName or user.email})
    err = _commit(user, "BULK_UPDATE", "FugitiveSurvey", "bulk",
                  f"Bulk updated {len(surveys)} LDAR survey(s): {[s.id for s in surveys]}", "Failed to bulk update surveys",
                  new={"leak_status": new_status or None, "repair_date": repair_date if repair_date is not False else None,
                       "screening_value_ppm": ppm, "survey_method": method or None, "notes": note or None})
    if err:
        return err
    return jsonify({"message": f"Successfully updated {len(surveys)} survey(s)", "updated_count": len(surveys),
                    "updated_ids": [s.id for s in surveys]}), 200


@ldar_bp.route("/surveys/bulk-delete", methods=["POST"])
@login_required
def bulk_delete_surveys():
    """Bulk delete fugitive survey records."""
    user = get_current_user()
    if user.role not in ["admin", "superuser"]:
        return jsonify({"error": "Forbidden: Only Administrators can delete LDAR surveys"}), 403
    surveys, err = _scoped_ids(FugitiveSurvey, user, request.get_json() or {}, "survey")
    if err:
        return err
    ids = [s.id for s in surveys]
    for s in surveys:
        db.session.delete(s)
    err = _commit(user, "BULK_DELETE", "FugitiveSurvey", "bulk", f"Bulk deleted {len(ids)} LDAR survey(s): {ids}",
                  "Failed to bulk delete surveys")
    return err or (jsonify({"message": f"Successfully deleted {len(ids)} survey(s)", "deleted_count": len(ids)}), 200)
