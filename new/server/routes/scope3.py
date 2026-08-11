from flask import Blueprint, request, jsonify, session
from models import User, Scope3Emission, Facility
from extensions import db
from sqlalchemy import func
from routes.auth import login_required
from calculations.uncertainty import propagate_uncertainty, Tier

scope3_bp = Blueprint("scope3", __name__)


@scope3_bp.route("", methods=["GET"])
@login_required
def get_scope3_emissions():
    """Get all Scope 3 emissions"""
    user = User.query.get(session.get("user_id"))
    if user and user.role != "admin":
        emissions = Scope3Emission.query.filter(
            Scope3Emission.created_by == user.id
        ).all()
    else:
        emissions = Scope3Emission.query.all()
    return jsonify(
        [
            {
                "id": e.id,
                "year": e.year,
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
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in emissions
        ]
    )


@scope3_bp.route("", methods=["POST"])
@login_required
def create_scope3_emission():
    """Create a new Scope 3 emission record"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()

    emission = Scope3Emission(
        facility_id=data.get("facility_id"),
        year=data.get("year"),
        month=data.get("month"),
        category=data.get("category", "Category 11"),
        sub_category=data.get("sub_category")
        or data.get("activity_type"),  # Fallback to activity_type
        activity_data=data.get("activity_data")
        or data.get("amount", 0),  # Fallback to amount
        unit=data.get("unit"),
        emission_factor=data.get("emission_factor", 0),
        co2e=data.get("co2e")
        or data.get("emissions_tco2e", 0),  # Fallback to emissions_tco2e
    )
    co2e_val = float(emission.co2e or 0)

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
    emission.calculation_method = data.get("calculation_method")
    emission.data_quality = data.get("data_quality")
    emission.notes = data.get("notes")
    emission.created_by = user_id

    db.session.add(emission)
    db.session.commit()

    return jsonify({"message": "Scope 3 emission created", "id": emission.id}), 201


@scope3_bp.route("/<int:emission_id>", methods=["PUT"])
@login_required
def update_scope3_emission(emission_id):
    """Update a Scope 3 emission record"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    emission = Scope3Emission.query.get(emission_id)
    user = User.query.get(session.get("user_id"))
    if user and user.role != "admin" and emission and emission.created_by != user.id:
        return jsonify({"error": "Unauthorized"}), 403
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    data = request.get_json()

    if "year" in data:
        emission.year = data["year"]
    if "category" in data:
        emission.category = data["category"]
    if "sub_category" in data:
        emission.sub_category = data["sub_category"]
    if "activity_data" in data:
        emission.activity_data = data["activity_data"]
    if "unit" in data:
        emission.unit = data["unit"]
    if "emission_factor" in data:
        emission.emission_factor = data["emission_factor"]
    if "co2e" in data:
        emission.co2e = data["co2e"]
    if "uncertainty" in data:
        emission.uncertainty = data["uncertainty"]
    if "calculation_method" in data:
        emission.calculation_method = data["calculation_method"]
    if "data_quality" in data:
        emission.data_quality = data["data_quality"]
    if "notes" in data:
        emission.notes = data["notes"]

    db.session.commit()

    return jsonify({"message": "Scope 3 emission updated"})


@scope3_bp.route("/<int:emission_id>", methods=["DELETE"])
@login_required
def delete_scope3_emission(emission_id):
    """Delete a Scope 3 emission record"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    emission = Scope3Emission.query.get(emission_id)
    user = User.query.get(session.get("user_id"))
    if user and user.role != "admin" and emission and emission.created_by != user.id:
        return jsonify({"error": "Unauthorized"}), 403
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    db.session.delete(emission)
    db.session.commit()

    return jsonify({"message": "Scope 3 emission deleted"})


@scope3_bp.route("/bulk-import", methods=["POST"])
@login_required
def bulk_import_scope3():
    """Import Scope 3 emissions from CSV data"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    records = data.get("records", [])
    if not records:
        return jsonify({"error": "No records provided"}), 400

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
                        facility = Facility.query.get(fid)
                        facility_cache[fid] = facility
                except (ValueError, TypeError):
                    facility = None

            if not facility:
                errors.append(f"Row {i}: Facility '{f_val}' not found")
                continue

            # 2. Extract Data and Calculate
            cat = rec.get("category", "11")
            sub_cat = rec.get("sub_category")
            amt = float(rec.get("amount") or 0)
            ef = float(rec.get("emission_factor") or 0)
            ef_unit = str(rec.get("ef_unit") or "kg").lower()

            # co2e stored in the DB is always in TONNES CO2e.
            # If a pre-calculated co2e value is provided in the CSV, use it directly (already in tonnes).
            if rec.get("co2e"):
                co2e = float(rec.get("co2e"))
            elif "t" in ef_unit or "tonne" in ef_unit:
                # EF is in t CO2e/unit (e.g. 0.43 tCO2e/bbl for crude) -> result already in tonnes
                co2e = amt * ef
            else:
                # EF is in kg CO2e/unit (default, most common for Scope 3 activity factors)
                # Divide by 1000 to convert kg -> tonnes
                co2e = (amt * ef) / 1000.0

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
                created_by=user_id,
            )
            db.session.add(emission)
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    db.session.commit()
    return jsonify(
        {"message": f"Successfully imported {imported_count} records", "errors": errors}
    ), (200 if not errors else 207)
