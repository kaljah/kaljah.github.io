from flask import request, jsonify, session
import json
from . import facilities_bp
from utils import get_allowed_facility_ids, log_activity_and_notify, is_unrestricted_location
from models import Facility, User
from extensions import db
from sqlalchemy.exc import IntegrityError
from routes.auth import login_required
import json


@facilities_bp.route("", methods=["GET"])
@facilities_bp.route("/", methods=["GET"])
@login_required
def get_facilities():
    user_id = session.get("user_id")
    user = (
        db.session.get(User, user_id) if user_id else None
    )  # API-02 FIX: replaced deprecated query.get
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return (
            jsonify(
                {"error": "Forbidden: IT personnel cannot access operational facility data"}
            ),
            403,
        )

    query = Facility.query
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None:
        query = query.filter(Facility.id.in_(allowed_fids))

    search_term = request.args.get("search")
    if search_term:
        escaped_search = search_term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(Facility.name.ilike(f"%{escaped_search}%", escape="\\"))

    facilities = query.all()
    return jsonify(
        [
            {
                "id": f.id,
                "name": f.name,
                "location": f.location,
                "division": f.division,
                "activity": f.activity,
                "region": f.region,
                # Computed identifier: falls back to name when region is NULL.
                # Mirrors the 3-way match in utils.get_allowed_facility_ids().
                # All frontend dropdowns and filters MUST use this field instead
                # of reading f.region directly.
                "region_identifier": f.region or f.name,
                "boundary_notes": f.boundary_notes,
                "boundary_type": f.boundary_type or "Operational Control",
                "boundary_detail": f.boundary_detail or "",
                "segment": f.segment,
                "operator_status": f.operator_status or "operated",
                "country": f.country or "Algeria",
                "ogmp_membership_year": f.ogmp_membership_year or 2023,
                "reconciliation_threshold": f.reconciliation_threshold or 20.0,
                "field": f.field,
                "latitude": f.latitude,
                "longitude": f.longitude,
            }
            for f in facilities
        ]
    )


@facilities_bp.route("/all-regions", methods=["GET"])
@login_required
def get_all_regions():
    """
    Return all unique region identifiers — IT personnel only, no access filtering.

    Mirrors the fallback logic in utils.get_allowed_facility_ids():
      - Uses facility.region when set
      - Falls back to facility.name for facilities where region is NULL
    This ensures the values shown in the dropdown will always resolve to
    actual facilities when a user's location is matched later.
    """
    user_id = session.get("user_id")
    caller = db.session.get(User, user_id) if user_id else None  # API-02 FIX
    if not caller or caller.role not in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT privileges required"}), 403

    identifiers = set()

    # 1. Facilities that have an explicit region value
    region_rows = (
        db.session.query(Facility.region)
        .filter(Facility.region.isnot(None), Facility.region != "")
        .distinct()
        .all()
    )
    for (r,) in region_rows:
        if r and r.strip():
            identifiers.add(r.strip())

    # 2. For facilities with no region set, fall back to their name
    #    (mirrors utils.py line 28: filter_by(name=user_region))
    name_rows = (
        db.session.query(Facility.name)
        .filter(
            db.or_(Facility.region.is_(None), Facility.region == ""),
            Facility.name.isnot(None),
            Facility.name != "",
        )
        .distinct()
        .all()
    )
    for (n,) in name_rows:
        if n and n.strip():
            identifiers.add(n.strip())

    return jsonify(sorted(identifiers))


@facilities_bp.route("", methods=["POST"])
@facilities_bp.route("/", methods=["POST"])
@login_required
def add_facility():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role not in ["admin", "superuser"]:
        return (
            jsonify({"error": "Forbidden: Only Administrators can create facilities"}),
            403,
        )

    data = request.get_json() or {}

    if user.role == "superuser" and not is_unrestricted_location(user.location):
        user_loc = (user.location or "").strip().lower()
        fac_region = (data.get("region") or "").strip().lower()
        fac_location = (data.get("location") or "").strip().lower()
        fac_name = (data.get("name") or "").strip().lower()
        if user_loc not in (fac_region, fac_location, fac_name):
            return (
                jsonify(
                    {"error": f"Superusers can only create facilities in their assigned region: {user.location}"}
                ),
                403,
            )

    code = data.get("code")
    if code:
        existing = Facility.query.filter_by(code=str(code).strip()).first()
        if existing:
            return jsonify({"error": f"Facility code '{code}' is already in use"}), 409

    fac = Facility(
        name=data.get("name"),
        location=data.get("location"),
        division=data.get("division"),
        activity=data.get("activity"),
        region=data.get("region"),
        field=data.get("field"),
        code=data.get("code"),
        boundary_notes=data.get("boundary_notes"),
        boundary_type=data.get("boundary_type", "Operational Control"),
        boundary_detail=data.get("boundary_detail"),
        segment=data.get("segment"),
        operator_status=data.get("operator_status", "operated"),
        country=data.get("country", "Algeria"),
        ogmp_membership_year=int(data.get("ogmp_membership_year", 2023) or 2023),
        reconciliation_threshold=float(
            data.get("reconciliation_threshold", 20.0) or 20.0
        ),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
    )

    try:
        db.session.add(fac)
        db.session.flush()  # Flush to get fac.id for audit log
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": f"Facility code '{fac.code}' is already in use"}), 409

    # Audit
    try:
        user_id = session.get("user_id")
        user = db.session.get(User, user_id) if user_id else None

        log_details = (
            f"Created facility: {fac.name} (Code: {fac.code}, Segment: {fac.segment})"
        )

        log_activity_and_notify(
            action="CREATE",
            record_id=str(fac.id),
            user=user,
            request=request,
            entity="Facility",
            details=log_details,
            metadata_json=json.dumps(
                {
                    "name": fac.name,
                    "code": fac.code,
                    "segment": fac.segment,
                    "location": fac.location,
                }
            ),
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    return jsonify({"message": "Facility added", "id": fac.id}), 201


@facilities_bp.route("/<int:facility_id>", methods=["PUT"])
@login_required
def update_facility(facility_id):
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None  # API-02 FIX
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role not in ["admin", "superuser"]:
        return (
            jsonify(
                {"error": "Forbidden: Administrative privileges required to manage facility configuration"}
            ),
            403,
        )

    facility = db.session.get(
        Facility, facility_id
    )  # API-02 FIX: replaced deprecated query.get
    if not facility:
        return jsonify({"error": "Facility not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and facility.id not in allowed_fids:
        return jsonify({"error": "Unauthorized: Outside your region"}), 403

    data = request.get_json()

    if "name" in data:
        facility.name = data["name"]
    if "location" in data:
        facility.location = data["location"]
    if "description" in data:
        facility.description = data["description"]
    if "boundary_notes" in data:
        facility.boundary_notes = data["boundary_notes"]
    if "boundary_type" in data:
        facility.boundary_type = data["boundary_type"]
    if "boundary_detail" in data:
        facility.boundary_detail = data["boundary_detail"]
    if "activity" in data:
        facility.activity = data["activity"]
    if "region" in data:
        facility.region = data["region"]
    if "division" in data:
        facility.division = data["division"]
    if "field" in data:
        facility.field = data["field"]
    if "code" in data:
        facility.code = data["code"]
    if "external_id" in data:
        facility.external_id = data["external_id"]
    if "segment" in data:
        facility.segment = data["segment"]
    if "operator_status" in data:
        facility.operator_status = data["operator_status"]
    if "country" in data:
        facility.country = data["country"]
    if "ogmp_membership_year" in data and data["ogmp_membership_year"] is not None:
        facility.ogmp_membership_year = int(data["ogmp_membership_year"])
    if (
        "reconciliation_threshold" in data
        and data["reconciliation_threshold"] is not None
    ):
        facility.reconciliation_threshold = float(data["reconciliation_threshold"])
    if "latitude" in data:
        facility.latitude = data["latitude"]
    if "longitude" in data:
        facility.longitude = data["longitude"]

    import datetime

    facility.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.session.flush()

    # Audit
    try:
        user = db.session.get(User, user_id) if user_id else None  # API-02 FIX

        changes = [
            k
            for k in data
            if k
            in [
                "name",
                "location",
                "description",
                "boundary_notes",
                "boundary_type",
                "boundary_detail",
                "activity",
                "division",
                "field",
                "code",
                "segment",
            ]
        ]
        log_details = (
            f"Updated facility: {facility.name}. Changed: {', '.join(changes)}"
        )

        log_activity_and_notify(
            action="UPDATE",
            record_id=str(facility_id),
            user=user,
            request=request,
            entity="Facility",
            details=log_details,
            metadata_json=json.dumps(
                {
                    "updated_fields": changes,
                    "new_values": {k: v for k, v in data.items() if k in changes},
                }
            ),
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e

    try:
        from routes.dashboard import clear_dashboard_cache

        clear_dashboard_cache()
    except Exception:
        pass

    return jsonify({"message": "Facility updated"})


@facilities_bp.route("/<int:facility_id>", methods=["DELETE"])
@login_required
def delete_facility(facility_id):
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None  # API-02 FIX
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role not in ["admin", "superuser"]:
        return (
            jsonify({"error": "Forbidden: Only Administrators can delete facilities"}),
            403,
        )

    facility = db.session.get(
        Facility, facility_id
    )  # API-02 FIX: replaced deprecated query.get
    if not facility:
        return jsonify({"error": "Facility not found"}), 404

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and facility.id not in allowed_fids:
        return jsonify({"error": "Unauthorized: Outside your region"}), 403

    try:
        db.session.delete(facility)
        db.session.flush()

        # Audit
        user = db.session.get(User, user_id) if user_id else None  # API-02 FIX
        log_details = f"Deleted facility: {facility.name} (Code: {facility.code})"

        log_activity_and_notify(
            action="DELETE",
            record_id=str(facility_id),
            user=user,
            request=request,
            entity="Facility",
            details=log_details,
            metadata_json=json.dumps(
                {
                    "name": facility.name,
                    "code": facility.code,
                    "location": facility.location,
                }
            ),
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete facility: {str(e)}"}), 500

    return jsonify({"message": "Facility deleted"})


@facilities_bp.route("/import", methods=["POST"])
@login_required
def import_facilities():
    """Bulk import facilities"""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role not in ["admin", "superuser"]:
        return (
            jsonify({"error": "Forbidden: Only Administrators can bulk import facilities"}),
            403,
        )

    data = request.get_json() or {}
    facilities_data = data.get("facilities", [])

    if not facilities_data:
        return jsonify({"error": "No facilities provided"}), 400

    if user.role == "superuser" and not is_unrestricted_location(user.location):
        user_loc = (user.location or "").strip().lower()
        for fac_data in facilities_data:
            fac_region = (fac_data.get("region") or "").strip().lower()
            fac_location = (fac_data.get("location") or "").strip().lower()
            fac_name = (fac_data.get("name") or "").strip().lower()
            if user_loc not in (fac_region, fac_location, fac_name):
                return (
                    jsonify(
                        {
                            "error": f"Superusers can only import facilities in their assigned region: {user.location}"
                        }
                    ),
                    403,
                )

    imported_count = 0
    for fac_data in facilities_data:
        facility = Facility(
            name=fac_data.get("name"),
            location=fac_data.get("location"),
            description=fac_data.get("description"),
            boundary_notes=fac_data.get("boundary_notes"),
            boundary_type=fac_data.get("boundary_type", "Operational Control"),
            boundary_detail=fac_data.get("boundary_detail"),
            activity=fac_data.get("activity"),
            division=fac_data.get("division"),
            region=fac_data.get("region"),
            field=fac_data.get("field"),
            code=fac_data.get("code"),
            external_id=fac_data.get("external_id"),
            segment=fac_data.get("segment"),
            created_by=user_id,
        )
        db.session.add(facility)
        imported_count += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to import facilities"}), 500

    return jsonify({"message": f"{imported_count} facilities imported"})
