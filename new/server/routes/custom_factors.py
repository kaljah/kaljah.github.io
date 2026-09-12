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
    if user and user.role == "it_admin":
        return jsonify({"error": "IT Admins do not have access to operational factor data"}), 403

    factors = CustomFactor.query.all()
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
                "version": f.version or "",
                "uncertainty": float(f.uncertainty or 0),
                "co2_uncertainty": float(f.co2_uncertainty or 0),
                "ch4_uncertainty": float(f.ch4_uncertainty or 0),
                "n2o_uncertainty": float(f.n2o_uncertainty or 0),
            }
            for f in factors
        ]
    )


def _parse_non_negative_float(val, field_name, default=0.0):
    if val is None or val == "":
        return default
    try:
        f = float(val)
        if f < 0:
            raise ValueError(f"{field_name} must be non-negative")
        return f
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a non-negative number")


@custom_factors_bp.route("", methods=["POST"])
@custom_factors_bp.route("/", methods=["POST"])
@superuser_required
def create_custom_factor():
    """Create a new custom emission factor (Super User / Admin only)"""
    user_id = session.get("user_id")
    user = User.query.get(user_id)

    data = request.get_json()
    factor_name = (data.get("factor_name") or data.get("name") or "").strip() if data else ""
    if not factor_name:
        return jsonify({"error": "Factor name is required"}), 400

    unit = (data.get("unit") or "scf").strip()
    if not unit:
        return jsonify({"error": "Unit is required"}), 400

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
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    factor = CustomFactor(
        name=factor_name,
        co2_factor=co2_factor,
        ch4_factor=ch4_factor,
        n2o_factor=n2o_factor,
        co_factor=co_factor,
        unit=unit,
        hhv_factor=hhv_factor,
        usage=data.get("usage", "Custom"),
        parent_fuel=data.get("parent_fuel"),
        source=data.get("source"),
        version=data.get("version"),
        uncertainty=uncertainty,
        co2_uncertainty=co2_uncertainty,
        ch4_uncertainty=ch4_uncertainty,
        n2o_uncertainty=n2o_uncertainty,
        created_by=user_id,
    )

    try:
        db.session.add(factor)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating custom factor: {e}")
        return jsonify({"error": "Failed to create custom factor"}), 500

    try:
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
        current_app.logger.error(f"Audit log error on custom factor create: {e}")

    return jsonify({"message": "Custom factor created", "id": factor.id}), 201


@custom_factors_bp.route("/<int:factor_id>", methods=["PUT"])
@superuser_required
def update_custom_factor(factor_id):
    """Update a custom emission factor (Super User / Admin only)"""
    user_id = session.get("user_id")
    user = User.query.get(user_id)

    factor = CustomFactor.query.get(factor_id)
    if not factor:
        return jsonify({"error": "Factor not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "factor_name" in data or "name" in data:
        fn = (data.get("factor_name") or data.get("name") or "").strip()
        if not fn:
            return jsonify({"error": "Factor name cannot be empty"}), 400
        factor.name = fn

    if "unit" in data:
        u = (data.get("unit") or "").strip()
        if not u:
            return jsonify({"error": "Unit cannot be empty"}), 400
        factor.unit = u

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
    except ValueError as err:
        return jsonify({"error": str(err)}), 400

    if "usage" in data:
        factor.usage = data["usage"]
    if "parent_fuel" in data:
        factor.parent_fuel = data["parent_fuel"]
    if "source" in data:
        factor.source = data["source"]
    if "version" in data:
        factor.version = data["version"]

    factor.updated_by = user_id
    factor.updated_at = datetime.datetime.utcnow()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating custom factor: {e}")
        return jsonify({"error": "Failed to update custom factor"}), 500

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
        current_app.logger.error(f"Audit log error on custom factor update: {e}")

    return jsonify({"message": "Custom factor updated"})


@custom_factors_bp.route("/<int:factor_id>", methods=["DELETE"])
@superuser_required
def delete_custom_factor(factor_id):
    """Delete a custom emission factor (Super User / Admin only)"""
    user_id = session.get("user_id")
    user = User.query.get(user_id)

    factor = CustomFactor.query.get(factor_id)
    if not factor:
        return jsonify({"error": "Factor not found"}), 404

    factor_name = factor.name
    try:
        db.session.delete(factor)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting custom factor: {e}")
        return jsonify({"error": "Failed to delete custom factor"}), 500

    try:
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
        current_app.logger.error(f"Audit log error on custom factor delete: {e}")

    return jsonify({"message": "Custom factor deleted"})


@custom_factors_bp.route("/import", methods=["POST"])
@superuser_required
def import_custom_factors():
    """Bulk import custom factors from CSV/Excel (Super User / Admin only)"""
    user_id = session.get("user_id")
    user = User.query.get(user_id)

    data = request.get_json()
    factors_data = data.get("factors", [])

    if not factors_data:
        return jsonify({"error": "No factors provided"}), 400

    imported_count = 0
    for factor_data in factors_data:
        name = (factor_data.get("name") or factor_data.get("factor_name") or "").strip()
        unit = (factor_data.get("unit") or "scf").strip()
        if not name or not unit:
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
        except ValueError:
            continue

        factor = CustomFactor(
            name=name,
            co2_factor=co2_factor,
            ch4_factor=ch4_factor,
            n2o_factor=n2o_factor,
            co_factor=co_factor,
            unit=unit,
            hhv_factor=hhv_factor,
            usage=factor_data.get("usage", "Custom"),
            parent_fuel=factor_data.get("parent_fuel"),
            source=factor_data.get("source"),
            version=factor_data.get("version"),
            uncertainty=uncertainty,
            co2_uncertainty=co2_uncertainty,
            ch4_uncertainty=ch4_uncertainty,
            n2o_uncertainty=n2o_uncertainty,
            created_by=user_id,
        )
        db.session.add(factor)
        imported_count += 1

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error importing custom factors: {e}")
        return jsonify({"error": "Failed to import custom factors"}), 500

    try:
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
        current_app.logger.error(f"Audit log error on custom factor import: {e}")

    return jsonify({"message": f"{imported_count} factors imported successfully"})
