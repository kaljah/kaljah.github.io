from flask import Blueprint, request, jsonify, session
from models import User, Scope3Emission, Facility
from extensions import db
from sqlalchemy import func
from routes.auth import login_required
from calculations.uncertainty import propagate_uncertainty, Tier
from calculations.units import compute_scope3_co2e
from utils import get_current_user, get_allowed_facility_ids, log_activity_and_notify, require_facility_access
import datetime

scope3_bp = Blueprint("scope3", __name__)


@scope3_bp.route("", methods=["GET"])
@login_required
def get_scope3_emissions():
    """Get all Scope 3 emissions scoped to user's allowed facilities"""
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to emission data"}), 403

    allowed_fids = get_allowed_facility_ids(user)

    query = Scope3Emission.query
    if allowed_fids is not None:
        query = query.filter(Scope3Emission.facility_id.in_(allowed_fids))

    # Optional query filters
    year_arg = request.args.get("year")
    fac_arg = request.args.get("facilityId") or request.args.get("facility_id")
    if year_arg and year_arg != "all":
        try:
            query = query.filter(Scope3Emission.year == int(year_arg))
        except ValueError:
            pass
    if fac_arg and fac_arg != "all":
        try:
            query = query.filter(Scope3Emission.facility_id == int(fac_arg))
        except ValueError:
            pass

    emissions = query.order_by(Scope3Emission.created_at.desc()).all()
    return jsonify(
        [
            {
                "id": e.id,
                "facility_id": e.facility_id,
                "year": e.year,
                "month": e.month,
                "category": e.category,
                "sub_category": e.sub_category,
                "activity_data": float(e.activity_data or 0),
                "unit": e.unit,
                "emission_factor": float(e.emission_factor or 0),
                "co2e": float(e.co2e or 0),
                "uncertainty": float(e.uncertainty) if e.uncertainty is not None else None,
                "calculation_method": e.calculation_method,
                "data_quality": e.data_quality,
                "notes": e.notes,
                "status": e.status or "Verified",
                "approved_by": e.approved_by,
                "approved_at": e.approved_at.isoformat() if e.approved_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in emissions
        ]
    )


@scope3_bp.route("", methods=["POST"])
@login_required
def create_scope3_emission():
    """Create a new Scope 3 emission record with Maker-Checker status"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only or administrative role cannot create emission records"}), 403

    data = request.get_json() or {}
    facility_id = data.get("facility_id")
    if not facility_id:
        return jsonify({"error": "Missing facility_id"}), 422

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and int(facility_id) not in allowed_fids:
        return jsonify({"error": "Unauthorized for this facility"}), 403

    req_status = data.get("status")
    if req_status == "Draft":
        initial_status = "Draft"
    else:
        # Maker-Checker: only admin role auto-verifies; all other roles (superuser, user) require admin approval
        initial_status = "Verified" if user.role == "admin" else "Pending"

    activity_data = float(data.get("activity_data") or data.get("amount", 0))
    emission_factor = float(data.get("emission_factor", 0))
    co2e_input = data.get("co2e") or data.get("emissions_tco2e")
    # Enforce server-side calculation from activity_data and emission_factor to prevent client-side tampering
    if activity_data > 0 and emission_factor > 0:
        factor_unit = str(data.get("factor_unit") or data.get("emission_factor_unit") or "")
        calc_method = str(data.get("calculation_method") or "")
        co2e_val = compute_scope3_co2e(activity_data, emission_factor, factor_unit, calc_method)
    elif co2e_input not in [None, ""] and user.role in ["admin", "superuser"]:
        co2e_val = float(co2e_input)
    else:
        co2e_val = 0.0

    emission = Scope3Emission(
        facility_id=data.get("facility_id"),
        year=data.get("year"),
        month=data.get("month"),
        category=data.get("category", "Category 11"),
        sub_category=data.get("sub_category")
        or data.get("activity_type"),  # Fallback to activity_type
        activity_data=activity_data,
        unit=data.get("unit"),
        emission_factor=emission_factor,
        co2e=co2e_val,
        status=initial_status,
        approved_by=user.id if initial_status == "Verified" else None,
        approved_at=datetime.datetime.now(datetime.timezone.utc) if initial_status == "Verified" else None,
    )

    # Calculate uncertainty
    provided_uncertainty = data.get("uncertainty")
    if provided_uncertainty is not None:
        final_uncertainty = float(provided_uncertainty)
    else:
        # Default Scope 3 uncertainty (20% EF, 10% AD -> ~22.3% combined)
        u_res = propagate_uncertainty(
            co2e_val,
            ef_uncertainty=0.20,
            activity_uncertainty=0.10,
            tier=Tier.T1,
            process_category="scope3",
            gas="co2",
        )
        final_uncertainty = u_res["relative_uncertainty"]

    emission.uncertainty = final_uncertainty
    calc_method = data.get("calculation_method") or f"Scope 3 - Category {emission.category}"
    emission.calculation_method = calc_method
    emission.data_quality = data.get("data_quality")
    emission.notes = data.get("notes")
    emission.created_by = user.id

    try:
        db.session.add(emission)
        db.session.flush()
        emission_id_val = emission.id
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create Scope 3 emission: {str(e)}"}), 500

    try:
        log_activity_and_notify(
            action="CREATE",
            record_id=str(emission_id_val),
            user=user,
            request=request,
            entity="Scope3Emission",
            details=f"Created Scope 3 emission: {emission.category} ({emission.co2e:.2f} tCO2e, Status: {initial_status})",
        )
        db.session.commit()

        if initial_status in ("Pending", "Pending Approval"):
            from models import Notification
            admins = User.query.filter_by(role="admin", status="active").all()
            for admin in admins:
                Notification.create(
                    user_id=admin.id,
                    type="audit",
                    title="New Scope 3 Emission Pending Review",
                    message=f"A new Scope 3 emission record ({emission.category}) was submitted by {user.fullName} and is awaiting your approval.",
                )
            db.session.commit()
    except Exception:
        db.session.rollback()

    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()

    return jsonify({
        "message": "Scope 3 emission created",
        "id": emission_id_val,
        "status": initial_status,
        "co2e": co2e_val,
        "emissions": {
            "totalCo2e": co2e_val,
            "co2": co2e_val,
            "ch4": 0.0,
            "n2o": 0.0,
            "uncertainty": final_uncertainty,
        },
        "record": {
            "id": emission_id_val,
            "year": emission.year,
            "month": emission.month,
            "facility_id": emission.facility_id,
            "category": emission.category,
            "sub_category": emission.sub_category,
            "activity_data": emission.activity_data,
            "amount": emission.activity_data,
            "unit": emission.unit,
            "emission_factor": emission.emission_factor,
            "co2e": co2e_val,
            "uncertainty": final_uncertainty,
            "status": emission.status,
        },
        "calculation_method": calc_method,
    }), 201


@scope3_bp.route("/<int:emission_id>", methods=["PUT"])
@login_required
def update_scope3_emission(emission_id):
    """Update a Scope 3 emission record"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only or administrative role cannot modify emission records"}), 403

    emission = db.session.get(Scope3Emission, emission_id)
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    if not require_facility_access(user, emission.facility_id):
        return jsonify({"error": "Unauthorized: Outside your region"}), 403

    # Enforce creator ownership for standard user role
    if user.role == "user" and emission.created_by is not None and emission.created_by != user.id:
        return jsonify({"error": "Unauthorized: You may only modify records you created"}), 403

    # If non-admin modifies a verified record, reset status to Pending for maker-checker review
    if user.role not in ["admin", "superuser"] and emission.status == "Verified":
        emission.status = "Pending"
        emission.approved_by = None
        emission.approved_at = None

    data = request.get_json() or {}

    # Strip status and co2e from direct client overwrite (H2, L9)
    data.pop("status", None)
    data.pop("approved_by", None)
    data.pop("approved_at", None)
    data.pop("co2e", None)

    if "facility_id" in data:
        new_fid = int(data["facility_id"])
        if not require_facility_access(user, new_fid):
            return jsonify({"error": "Unauthorized to reassign to this facility"}), 403
        emission.facility_id = new_fid
    if "year" in data:
        emission.year = int(data["year"])
    if "category" in data:
        emission.category = data["category"]
    if "sub_category" in data:
        emission.sub_category = data["sub_category"]

    recalc = False
    if "activity_data" in data:
        emission.activity_data = float(data["activity_data"] or 0)
        recalc = True
    if "unit" in data:
        emission.unit = data["unit"]
    if "emission_factor" in data:
        emission.emission_factor = float(data["emission_factor"] or 0)
        recalc = True

    if recalc:
        # Recalculate co2e in tonnes: activity_data * emission_factor (if factor is kg/unit -> /1000)
        ef = emission.emission_factor or 0.0
        act = emission.activity_data or 0.0
        factor_unit = str(data.get("factor_unit") or data.get("emission_factor_unit") or getattr(emission, "factor_unit", "") or "")
        calc_method = str(data.get("calculation_method") or getattr(emission, "calculation_method", "") or "")
        emission.co2e = round(compute_scope3_co2e(act, ef, factor_unit, calc_method), 4)

        if emission.status == "Verified" and user.role != "admin":
            emission.status = "Pending"
            emission.approved_by = None
            emission.approved_at = None

    if "uncertainty" in data:
        emission.uncertainty = float(data["uncertainty"] or 0)
    if "calculation_method" in data:
        emission.calculation_method = data["calculation_method"]
    if "data_quality" in data:
        emission.data_quality = data["data_quality"]
    if "notes" in data:
        emission.notes = data["notes"]

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update Scope 3 emission: {str(e)}"}), 500

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()

    return jsonify({"message": "Scope 3 emission updated"})


@scope3_bp.route("/<int:emission_id>", methods=["DELETE"])
@login_required
def delete_scope3_emission(emission_id):
    """Delete a Scope 3 emission record"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to emission data"}), 403

    if user.role in ["auditor"]:
        return jsonify({"error": "Forbidden: Read-only accounts cannot delete emission records"}), 403

    emission = db.session.get(Scope3Emission, emission_id)
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    if user.role not in ["admin", "superuser"]:
        if emission.created_by != user.id:
            return (
                jsonify(
                    {"error": "Forbidden: You do not have permission to delete records created by another user"}
                ),
                403,
            )
    else:
        if not require_facility_access(user, emission.facility_id):
            return jsonify({"error": "Unauthorized: Outside your region"}), 403

    log_details = f"Deleted Scope 3 emission: {emission.category} ({emission.co2e:.2f} tCO2e, facility #{emission.facility_id})"
    db.session.delete(emission)
    try:
        from utils import log_activity_and_notify
        log_activity_and_notify(
            action="DELETE",
            record_id=str(emission_id),
            user=user,
            request=request,
            entity="Scope3Emission",
            details=log_details,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete Scope 3 emission: {e}")
        return jsonify({"error": "Failed to delete Scope 3 record"}), 500

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()

    return jsonify({"message": "Scope 3 emission deleted"})


@scope3_bp.route("/bulk-import", methods=["POST"])
@login_required
def bulk_import_scope3():
    """Import Scope 3 emissions from CSV data"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to upload emission data"}), 403

    data = request.get_json() or {}
    records = data.get("records", [])
    if not records:
        return jsonify({"error": "No records provided"}), 400

    MAX_SYNCHRONOUS_IMPORT = 2500
    if len(records) > MAX_SYNCHRONOUS_IMPORT:
        return (
            jsonify(
                {
                    "error": f"Payload exceeds maximum synchronous limit of {MAX_SYNCHRONOUS_IMPORT} rows. Please split the batch."
                }
            ),
            413,
        )

    # Per D-04: bulk imports are Verified only if created by admin, otherwise Pending
    bulk_status = "Verified" if user.role == "admin" else "Pending"
    allowed_fids = get_allowed_facility_ids(user)

    imported_count = 0
    errors = []
    facility_cache = {}

    for i, rec in enumerate(records):
        try:
            # 1. Resolve facility
            f_val = rec.get("facility_id")
            facility = None
            if isinstance(f_val, str) and not str(f_val).isdigit():
                f_name_clean = f_val.strip()
                if f_name_clean.lower() in facility_cache:
                    facility = facility_cache[f_name_clean.lower()]
                else:
                    facility = Facility.query.filter(
                        func.lower(Facility.name) == f_name_clean.lower()
                    ).first()
                    facility_cache[f_name_clean.lower()] = facility
            else:
                try:
                    fid = int(f_val) if f_val else None
                    if fid in facility_cache:
                        facility = facility_cache[fid]
                    else:
                        facility = db.session.get(Facility, fid)
                        facility_cache[fid] = facility
                except (ValueError, TypeError):
                    facility = None

            if not facility:
                errors.append(f"Row {i}: Facility '{f_val}' not found")
                continue

            if allowed_fids is not None and facility.id not in allowed_fids:
                errors.append(f"Row {i}: Unauthorized for facility '{f_val}'")
                continue

            # 2. Extract Data and Calculate
            from background_processor import _clean_float
            cat = rec.get("category", "11")
            sub_cat = rec.get("sub_category")
            amt = _clean_float(rec.get("amount"), default=0.0)
            ef = _clean_float(rec.get("emission_factor"), default=0.0)
            ef_unit = str(rec.get("ef_unit") or rec.get("factor_unit") or "kg").strip()
            calc_method = str(rec.get("calculation_method") or "")

            # Authoritatively calculate co2e when activity amount and EF are present
            if amt > 0 and ef > 0:
                co2e = compute_scope3_co2e(amt, ef, ef_unit, calc_method)
            elif rec.get("co2e") and user.role in ["admin", "superuser"]:
                co2e = _clean_float(rec.get("co2e"), default=0.0)
            else:
                co2e = 0.0

            emission = Scope3Emission(
                facility_id=facility.id,
                year=int(rec.get("year", 2024)),
                month=int(rec.get("month", 1)),
                category=(
                    f"Category {cat}" if not str(cat).startswith("Category") else cat
                ),
                sub_category=sub_cat,
                activity_data=amt,
                unit=rec.get("unit"),
                emission_factor=ef,
                co2e=co2e,
                notes=rec.get("notes", "Bulk Imported"),
                created_by=user.id,
                status=bulk_status,
                approved_by=user.id if bulk_status == "Verified" else None,
                approved_at=datetime.datetime.now(datetime.timezone.utc) if bulk_status == "Verified" else None,
            )
            db.session.add(emission)
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to bulk import Scope 3 emissions: {str(e)}"}), 500

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
    try:
        if bulk_status in ("Pending", "Pending Approval") and imported_count > 0:
            from models import Notification
            admins = User.query.filter_by(role="admin", status="active").all()
            for admin in admins:
                Notification.create(
                    user_id=admin.id,
                    type="audit",
                    title="Scope 3 Bulk Upload Pending Review",
                    message=f"{imported_count} new Scope 3 emission records were uploaded by {user.fullName} and are awaiting your approval.",
                )
            db.session.commit()

        if imported_count > 0:
            log_activity_and_notify(
                action="BULK_IMPORT",
                record_id=f"count:{imported_count}",
                user=user,
                request=request,
                entity="Scope3Emission",
                details=f"Bulk imported {imported_count} Scope 3 records (Status: {bulk_status})",
            )
            db.session.commit()
    except Exception:
        db.session.rollback()

    return jsonify(
        {"message": f"Successfully imported {imported_count} records", "errors": errors}
    ), (200 if not errors else 207)

@scope3_bp.route("/eeio-calculate", methods=["POST"])
@login_required
def calculate_eeio():
    """Calculate Scope 3 Category 1 emissions based on spend and NAICS code"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    naics_code = str(data.get("naics_code", ""))
    spend_usd = float(data.get("spend_usd", 0))
    
    if spend_usd <= 0:
        return jsonify({"co2e": 0, "emission_factor": 0, "message": "Zero spend"}), 200
        
    from emission_factors.eeio_factors import get_eeio_factor
    factor_data = get_eeio_factor(naics_code)
    
    # Calculate emissions
    # Factor is kg CO2e per $1000 spend
    # So formula is: (spend_usd / 1000) * factor -> gives kg CO2e
    # Then divide by 1000 to get tonnes CO2e
    spend_k = spend_usd / 1000.0
    kg_co2e = spend_k * factor_data["kg_co2e_per_1000_usd"]
    tonnes_co2e = kg_co2e / 1000.0
    
    return jsonify({
        "co2e": tonnes_co2e,
        "emission_factor": factor_data["kg_co2e_per_1000_usd"],
        "ef_unit": "kg CO2e / $1000",
        "industry_name": factor_data["name"]
    }), 200
