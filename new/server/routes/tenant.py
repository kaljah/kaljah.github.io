"""
Tenant Configuration API Routes (Part 3.2)
==========================================
Provides dynamic tenant branding, regulatory frameworks, and localization
parameters without hardcoding operator specifics.
"""
from flask import Blueprint, jsonify, request
from utils import get_current_user
from routes.auth import admin_required, login_required
from services.tenant_config import get_tenant_config, update_tenant_config, get_current_tenant_id

tenant_bp = Blueprint("tenant", __name__, url_prefix="/api/tenant")


@tenant_bp.route("/branding", methods=["GET"])
def get_branding():
    """Retrieve public tenant branding (safe subset for unauthenticated login screen)."""
    tenant_param = request.args.get("tenant_id")
    tenant_id = tenant_param or get_current_tenant_id(None)
    cfg = get_tenant_config(tenant_id)
    return jsonify({
        "organization_name": cfg.get("organization_name", "Sonatrach"),
        "regulatory_framework": cfg.get("regulatory_framework", "Executive Decree 21-330"),
        "theme": cfg.get("theme", {}),
        "logo_url": cfg.get("logo_url", ""),
    }), 200


@tenant_bp.route("/config", methods=["GET"])
@login_required
def get_config():
    """Retrieve tenant configuration for the current user or tenant query (Authenticated only)."""
    user = get_current_user()
    tenant_param = request.args.get("tenant_id")
    tenant_id = tenant_param or get_current_tenant_id(user)
    cfg = get_tenant_config(tenant_id)
    return jsonify(cfg), 200


@tenant_bp.route("/config", methods=["PUT"])
@login_required
@admin_required
def set_config():
    """Update tenant configuration (Admin / Superuser only)."""
    user = get_current_user()
    payload = request.get_json(silent=True) or {}
    tenant_param = request.args.get("tenant_id")
    current_user_tenant = get_current_tenant_id(user)
    if tenant_param and tenant_param.lower() != current_user_tenant.lower() and getattr(user, "role", None) != "superuser":
        return jsonify({"error": "Unauthorized cross-tenant modification attempt"}), 403
    tenant_id = tenant_param or current_user_tenant
    try:
        updated = update_tenant_config(tenant_id, payload, user=user)
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    return jsonify({
        "status": "success",
        "message": "Tenant configuration updated successfully",
        "config": updated,
    }), 200
