import datetime
from flask import Blueprint, request, jsonify, session, current_app
from models import CustomFactor, User
from extensions import db
from routes.auth import superuser_required, login_required
from utils import log_activity_and_notify, get_current_user

custom_factors_bp = Blueprint("custom_factors", __name__)


@custom_factors_bp.route("", methods=["GET"])
@custom_factors_bp.route("/", methods=["GET"])
@login_required
def get_custom_factors():
    """Get all custom emission factors"""
    user = get_current_user()
    if user and user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to operational factor data"}), 403

    q = CustomFactor.query
    if request.args.get("include_archived") not in ("1", "true"):
        q = q.filter(CustomFactor.is_archived.is_(False))
    factors = q.all()
    return jsonify(
        [
            {
                "id": f.id,
                "name": f.name,
                "factor_name": f.name,
                "co2_factor": float(f.co2_factor or 0),
                "ch4_factor": float(f.ch4_factor or 0),
                "n2o_factor": float(f.n2o_factor or 0),
                "co_factor": float(f.co_factor or 0),
                "unit": f.unit,
                "hhv_factor": float(f.hhv_factor or 0),
                "usage": f.usage or "Custom",
                "parent_fuel": f.parent_fuel,
                "source": f.source or "",
                "description": f.description or "",
                "version": f.version or "",
                "uncertainty": float(f.uncertainty or 0),
                "co2_uncertainty": float(f.co2_uncertainty or 0),
                "ch4_uncertainty": float(f.ch4_uncertainty or 0),
                "n2o_uncertainty": float(f.n2o_uncertainty or 0),
                "status": getattr(f, "status", None) or "Approved",
                "approved_by": getattr(f, "approved_by", None),
                "approved_at": f.approved_at.isoformat() if getattr(f, "approved_at", None) else None,
                "is_archived": bool(f.is_archived),
            }
            for f in factors
        ]
    )


def _parse_non_negative_float(val, field_name, default=0.0):
    """Finite, non-negative number; blank -> default (BUG-083: NaN/inf rejected)."""
    from input_validation import ValidationError, parse_number

    try:
        return parse_number(val, field_name, required=False, min_value=0, default=default)
    except ValidationError as err:
        raise ValueError(err.message)


def _canonical_parent_fuel(value):
    """Catalog name of a custom factor's parent fuel (it sets the HHV basis: Btu/gal, Btu/scf ...), or
    None when blank. An unknown name was stored and silently ignored, so a liquid factor fell back to
    the gas basis (deep-dive audit); it is now refused."""
    if value in (None, "") or not str(value).strip():
        return None
    from routes.emissions import _canonical_api_factor_name

    name = _canonical_api_factor_name(str(value).strip())
    if not name:
        raise ValueError(f"Parent fuel '{value}' is not a catalog fuel (e.g. Diesel, Natural Gas); leave it blank "
                         "for a gas factor or pick the catalog fuel the HHV belongs to")
    return name


def _canonical_factor_unit(unit):
    """BUG-063: one stored form for custom factor units. The Manage Data form sends the bare
    activity unit (values labelled "kg/unit"), so "scf" becomes "kg/scf"; anything the
    calculator cannot interpret is rejected here instead of being applied 1:1 later."""
    from calculations.units import UnitError, parse_factor_unit

    u = str(unit or "").strip()
    if not u:
        raise ValueError("Unit is required")
    canonical = u if "/" in u else f"kg/{u}"
    try:
        parse_factor_unit(canonical)
    except UnitError as err:
        raise ValueError(f"Unsupported factor unit '{u}': {err}")
    return canonical


def _name_taken(name, exclude_id=None):
    """BUG-065: factor names are unique (case-insensitive) among active factors."""
    q = CustomFactor.query.filter(db.func.lower(CustomFactor.name) == name.strip().lower(),
                                  CustomFactor.is_archived.is_(False))
    if exclude_id is not None:
        q = q.filter(CustomFactor.id != exclude_id)
    return db.session.query(q.exists()).scalar()


def _require_some_factor(co2, ch4, n2o):
    """BUG-112: a factor whose CO2, CH4 and N2O are all zero/blank would book 0 tCO2e."""
    if not any((v or 0) > 0 for v in (co2, ch4, n2o)):
        raise ValueError("At least one of co2_factor, ch4_factor or n2o_factor must be greater than 0")


def _factor_references(factor):
    """Emission records that use this factor, by FK, legacy id string, payload or name (BUG-056)."""
    from models import Emission, Scope2Emission

    fid = factor.id
    s1 = Emission.query.filter(
        db.or_(
            Emission.custom_factor_id == fid,
            Emission.fuel_type == str(fid),
            Emission.fuel_type == factor.name,
            Emission.source_payload.like(f'%"custom_factor_id": {fid},%'),
            Emission.source_payload.like(f'%"custom_factor_id": {fid}}}%'),
            Emission.source_payload.like(f'%"custom_factor_id": "{fid}"%'),
        )
    ).count()
    s2 = Scope2Emission.query.filter(Scope2Emission.source_type == factor.name).count()
    return s1 + s2


PLAUSIBILITY_BOUNDS = {
    "co2_factor": (0.0, 500.0),    # API 2021: typical solid fuels ~100 kg/MMBtu
    "ch4_factor": (0.0, 100.0),    # API 2021: max ~5 for most fuels
    "n2o_factor": (0.0, 10.0),     # API 2021: max ~0.5 for most fuels
}


def _check_plausibility(data):
    """Flags any extreme or out-of-bounds custom factor values for user review."""
    warnings = []
    if not isinstance(data, dict):
        return warnings
    for field, (lo, hi) in PLAUSIBILITY_BOUNDS.items():
        val = data.get(field)
        if val is not None and str(val).strip() != "":
            try:
                v = float(val)
                if v < lo or v > hi:
                    warnings.append(f"{field}={v} is outside typical plausible range [{lo}, {hi}]")
            except (ValueError, TypeError):
                pass
    return warnings


@custom_factors_bp.route("", methods=["POST"])

@custom_factors_bp.route("/", methods=["POST"])
@superuser_required
def create_custom_factor():
    """Create a new custom emission factor (Super User / Admin only)"""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    data = request.get_json()
    factor_name = (data.get("factor_name") or data.get("name") or data.get("fuel_name") or "").strip() if data else ""
    if not factor_name:
        return jsonify({"error": "Factor name is required"}), 400

    try:
        unit = _canonical_factor_unit(data.get("unit"))
    except ValueError as err:
        return jsonify({"error": str(err), "field": "unit"}), 400

    try:
        parent_fuel = _canonical_parent_fuel(data.get("parent_fuel"))
    except ValueError as err:
        return jsonify({"error": str(err), "field": "parent_fuel"}), 400

    try:
        co2_factor = _parse_non_negative_float(data.get("co2_factor"), "co2_factor")
        ch4_factor = _parse_non_negative_float(data.get("ch4_factor"), "ch4_factor")
        n2o_factor = _parse_non_negative_float(data.get("n2o_factor"), "n2o_factor")
        co_factor = _parse_non_negative_float(data.get("co_factor"), "co_factor")
        hhv_factor = _parse_non_negative_float(data.get("hhv_factor"), "hhv_factor")
        uncertainty = _parse_non_negative_float(data.get("uncertainty"), "uncertainty")
        co2_uncertainty = _parse_non_negative_float(data.get("co2_uncertainty"), "co2_uncertainty")
        ch4_uncertainty = _parse_non_negative_float(data.get("ch4_uncertainty"), "ch4_uncertainty")
        n2o_uncertainty = _parse_non_negative_float(data.get("n2o_uncertainty"), "n2o_uncertainty")
        _require_some_factor(co2_factor, ch4_factor, n2o_factor)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    if _name_taken(factor_name):
        return jsonify({"error": f"A custom factor named '{factor_name}' already exists"}), 409

    # Maker-checker policy for custom factors:
    # Only admin creates pre-approved factors; superusers/others require admin approval.
    initial_factor_status = "Approved" if user and user.role == "admin" else "Pending"

    factor = CustomFactor(
        name=factor_name,
        co2_factor=co2_factor,
        ch4_factor=ch4_factor,
        n2o_factor=n2o_factor,
        co_factor=co_factor,
        unit=unit,
        hhv_factor=hhv_factor,
        usage=data.get("usage", "Custom"),
        parent_fuel=parent_fuel,
        source=data.get("source"),
        description=data.get("description"),
        version=data.get("version"),
        uncertainty=uncertainty,
        co2_uncertainty=co2_uncertainty,
        ch4_uncertainty=ch4_uncertainty,
        n2o_uncertainty=n2o_uncertainty,
        created_by=user_id,
        status=initial_factor_status,
        approved_by=user_id if initial_factor_status == "Approved" else None,
        approved_at=datetime.datetime.now(datetime.timezone.utc) if initial_factor_status == "Approved" else None,
    )

    try:
        db.session.add(factor)
        db.session.flush()
        log_activity_and_notify(
            action="CREATE",
            record_id=str(factor.id),
            user=user,
            request=request,
            entity="CustomFactor",
            details=f"Custom factor created: {factor.name}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating custom factor: {e}")
        return jsonify({"error": "Failed to create custom factor"}), 500

    warnings = _check_plausibility(data)
    resp_data = {"message": "Custom factor created", "id": factor.id}
    if warnings:
        resp_data["warnings"] = warnings
    return jsonify(resp_data), 201



@custom_factors_bp.route("/<int:factor_id>", methods=["PUT"])
@superuser_required
def update_custom_factor(factor_id):
    """Update a custom emission factor (Super User / Admin only)"""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    factor = db.session.get(CustomFactor, factor_id)
    if not factor:
        return jsonify({"error": "Factor not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "factor_name" in data or "name" in data or "fuel_name" in data:
        fn = (data.get("factor_name") or data.get("name") or data.get("fuel_name") or "").strip()
        if not fn:
            return jsonify({"error": "Factor name cannot be empty"}), 400
        if _name_taken(fn, exclude_id=factor.id):
            return jsonify({"error": f"A custom factor named '{fn}' already exists"}), 409
        factor.name = fn

    if "unit" in data:
        try:
            factor.unit = _canonical_factor_unit(data.get("unit"))
        except ValueError as err:
            return jsonify({"error": str(err), "field": "unit"}), 400

    try:
        if "co2_factor" in data:
            factor.co2_factor = _parse_non_negative_float(data["co2_factor"], "co2_factor")
        if "ch4_factor" in data:
            factor.ch4_factor = _parse_non_negative_float(data["ch4_factor"], "ch4_factor")
        if "n2o_factor" in data:
            factor.n2o_factor = _parse_non_negative_float(data["n2o_factor"], "n2o_factor")
        if "co_factor" in data:
            factor.co_factor = _parse_non_negative_float(data["co_factor"], "co_factor")
        if "hhv_factor" in data:
            factor.hhv_factor = _parse_non_negative_float(data["hhv_factor"], "hhv_factor")
        if "uncertainty" in data:
            factor.uncertainty = _parse_non_negative_float(data["uncertainty"], "uncertainty")
        if "co2_uncertainty" in data:
            factor.co2_uncertainty = _parse_non_negative_float(data["co2_uncertainty"], "co2_uncertainty")
        if "ch4_uncertainty" in data:
            factor.ch4_uncertainty = _parse_non_negative_float(data["ch4_uncertainty"], "ch4_uncertainty")
        if "n2o_uncertainty" in data:
            factor.n2o_uncertainty = _parse_non_negative_float(data["n2o_uncertainty"], "n2o_uncertainty")
        _require_some_factor(factor.co2_factor, factor.ch4_factor, factor.n2o_factor)
    except ValueError as err:
        db.session.rollback()
        return jsonify({"error": str(err)}), 400

    if "usage" in data:
        factor.usage = data["usage"]
    if "parent_fuel" in data:
        try:
            factor.parent_fuel = _canonical_parent_fuel(data["parent_fuel"])
        except ValueError as err:
            db.session.rollback()
            return jsonify({"error": str(err), "field": "parent_fuel"}), 400
    if "source" in data:
        factor.source = data["source"]
    if "description" in data:
        factor.description = data["description"]
    if "version" in data:
        factor.version = data["version"]

    factor.updated_at = datetime.datetime.now(datetime.timezone.utc)

    try:
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(factor.id),
            user=user,
            request=request,
            entity="CustomFactor",
            details=f"Custom factor updated: {factor.name}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating custom factor: {e}")
        return jsonify({"error": "Failed to update custom factor"}), 500

    return jsonify({"message": "Custom factor updated"})


@custom_factors_bp.route("/<int:factor_id>", methods=["DELETE"])
@superuser_required
def delete_custom_factor(factor_id):
    """Delete a custom emission factor (Super User / Admin only)"""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    factor = db.session.get(CustomFactor, factor_id)
    if not factor:
        return jsonify({"error": "Factor not found"}), 404

    refs = _factor_references(factor)
    if refs > 0:
        # BUG-056: a factor used by emission records cannot be deleted (its id must never be
        # reused); archive it instead via POST /api/custom-factors/<id>/archive.
        return jsonify({
            "error": f"Cannot delete factor '{factor.name}': referenced by {refs} emission records. Archive the factor instead.",
            "references": refs,
        }), 409

    factor_name = factor.name
    try:
        db.session.delete(factor)
        log_activity_and_notify(
            action="DELETE",
            record_id=str(factor_id),
            user=user,
            request=request,
            entity="CustomFactor",
            details=f"Custom factor deleted: {factor_name}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting custom factor: {e}")
        return jsonify({"error": "Failed to delete custom factor"}), 500

    return jsonify({"message": "Custom factor deleted"})


@custom_factors_bp.route("/<int:factor_id>/archive", methods=["POST"])
@superuser_required
def archive_custom_factor(factor_id):
    """BUG-056: hide a factor from new entries while keeping it for the records that use it."""
    user = get_current_user()
    factor = db.session.get(CustomFactor, factor_id)
    if not factor:
        return jsonify({"error": "Factor not found"}), 404
    restore = bool((request.get_json(silent=True) or {}).get("restore"))
    if restore and _name_taken(factor.name, exclude_id=factor.id):
        return jsonify({"error": f"An active custom factor named '{factor.name}' already exists"}), 409
    try:
        factor.is_archived = not restore
        log_activity_and_notify(
            action="RESTORE" if restore else "ARCHIVE",
            record_id=str(factor.id),
            user=user,
            request=request,
            entity="CustomFactor",
            details=f"Custom factor {'restored' if restore else 'archived'}: {factor.name}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to {'restore' if restore else 'archive'} factor: {e}"}), 500
    return jsonify({"message": f"Custom factor {'restored' if restore else 'archived'}", "archived": factor.is_archived})


@custom_factors_bp.route("/import", methods=["POST"])
@superuser_required
def import_custom_factors():
    """Bulk import custom factors from CSV/Excel (Super User / Admin only)"""
    user_id = session.get("user_id")
    user = db.session.get(User, user_id)

    data = request.get_json()
    factors_data = data.get("factors", [])

    if not factors_data:
        return jsonify({"error": "No factors provided"}), 400

    imported_count = 0
    skipped = []
    seen = set()
    for i, factor_data in enumerate(factors_data):
        name = (factor_data.get("name") or factor_data.get("factor_name") or "").strip()
        unit = (factor_data.get("unit") or "").strip()
        if not name or not unit:
            skipped.append({"row": i + 1, "error": "name and unit are required"})
            continue
        if name.lower() in seen or _name_taken(name):
            skipped.append({"row": i + 1, "error": f"duplicate factor name '{name}'"})
            continue
        try:
            unit = _canonical_factor_unit(unit)
        except ValueError as err:
            skipped.append({"row": i + 1, "error": str(err)})
            continue

        try:
            co2_factor = _parse_non_negative_float(factor_data.get("co2_factor"), "co2_factor")
            ch4_factor = _parse_non_negative_float(factor_data.get("ch4_factor"), "ch4_factor")
            n2o_factor = _parse_non_negative_float(factor_data.get("n2o_factor"), "n2o_factor")
            co_factor = _parse_non_negative_float(factor_data.get("co_factor"), "co_factor")
            hhv_factor = _parse_non_negative_float(factor_data.get("hhv_factor"), "hhv_factor")
            uncertainty = _parse_non_negative_float(factor_data.get("uncertainty"), "uncertainty")
            co2_uncertainty = _parse_non_negative_float(factor_data.get("co2_uncertainty"), "co2_uncertainty")
            ch4_uncertainty = _parse_non_negative_float(factor_data.get("ch4_uncertainty"), "ch4_uncertainty")
            n2o_uncertainty = _parse_non_negative_float(factor_data.get("n2o_uncertainty"), "n2o_uncertainty")
            _require_some_factor(co2_factor, ch4_factor, n2o_factor)
            parent_fuel = _canonical_parent_fuel(factor_data.get("parent_fuel"))
        except ValueError as err:
            skipped.append({"row": i + 1, "error": str(err)})
            continue
        seen.add(name.lower())

        initial_factor_status = "Approved" if user and user.role == "admin" else "Pending"
        factor = CustomFactor(
            name=name,
            co2_factor=co2_factor,
            ch4_factor=ch4_factor,
            n2o_factor=n2o_factor,
            co_factor=co_factor,
            unit=unit,
            hhv_factor=hhv_factor,
            usage=factor_data.get("usage", "Custom"),
            parent_fuel=parent_fuel,
            source=factor_data.get("source"),
            description=factor_data.get("description"),
            version=factor_data.get("version"),
            uncertainty=uncertainty,
            co2_uncertainty=co2_uncertainty,
            ch4_uncertainty=ch4_uncertainty,
            n2o_uncertainty=n2o_uncertainty,
            created_by=user_id,
            status=initial_factor_status,
            approved_by=user_id if initial_factor_status == "Approved" else None,
            approved_at=datetime.datetime.now(datetime.timezone.utc) if initial_factor_status == "Approved" else None,
        )
        db.session.add(factor)
        imported_count += 1

    try:
        if imported_count > 0:
            log_activity_and_notify(
                action="IMPORT",
                record_id=str(imported_count),
                user=user,
                request=request,
                entity="CustomFactor",
                details=f"Bulk imported {imported_count} custom emission factors",
            )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error importing custom factors: {e}")
        return jsonify({"error": "Failed to import custom factors"}), 500

    return jsonify({"message": f"{imported_count} factors imported successfully", "imported": imported_count, "skipped": skipped})
 
 
@custom_factors_bp.route("/<int:factor_id>/approve", methods=["POST"])
@login_required
def approve_custom_factor(factor_id):
    """Approve a pending custom emission factor (Admin only)."""
    user = get_current_user()
    if not user or user.role != "admin":
        return jsonify({"error": "Only Compliance Administrators can approve custom emission factors"}), 403

    factor = db.session.get(CustomFactor, factor_id)
    if not factor or factor.is_archived:
        return jsonify({"error": "Custom factor not found"}), 404

    if getattr(factor, "status", None) == "Approved":
        return jsonify({"message": "Factor is already approved", "id": factor.id}), 200

    try:
        factor.status = "Approved"
        factor.approved_by = user.id
        factor.approved_at = datetime.datetime.now(datetime.timezone.utc)

        log_activity_and_notify(
            action="APPROVE",
            record_id=str(factor.id),
            user=user,
            request=request,
            entity="CustomFactor",
            entity_id=str(factor.id),
            details=f"Approved custom emission factor '{factor.name}' (ID: {factor.id})",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to approve custom factor: {e}"}), 500
    return jsonify({"message": f"Custom factor '{factor.name}' approved successfully", "id": factor.id}), 200
