"""
Tenant Configuration API Routes (Part 3.2)
==========================================
Provides dynamic tenant branding, regulatory frameworks, and localization
parameters without hardcoding operator specifics.
"""
from flask import Blueprint, jsonify, request
from utils import get_current_user, normalize_tenant_id
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
        "organization_name": cfg.get("organization_name", "Demo Operator Co."),
        "regulatory_framework": cfg.get("regulatory_framework", "Executive Decree 21-330"),
        "theme": cfg.get("theme", {}),
        "logo_url": cfg.get("logo_url", ""),
    }), 200


@tenant_bp.route("/config", methods=["GET"])
@login_required
def get_config():
    """Retrieve tenant configuration strictly for the current user's tenant (Authenticated only)."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    tenant_param = request.args.get("tenant_id")
    if tenant_param and normalize_tenant_id(tenant_param) != caller_tenant:
        return jsonify({"error": "Unauthorized cross-tenant access"}), 403
    cfg = get_tenant_config(caller_tenant)
    return jsonify(cfg), 200


@tenant_bp.route("/config", methods=["PUT"])
@login_required
@admin_required
def set_config():
    """Update tenant configuration strictly for the current user's tenant (Admin / Superuser only)."""
    user = get_current_user()
    payload = request.get_json(silent=True) or {}
    tenant_param = request.args.get("tenant_id")
    current_user_tenant = get_current_tenant_id(user)
    if tenant_param and normalize_tenant_id(tenant_param) != normalize_tenant_id(current_user_tenant):
        return jsonify({"error": "Unauthorized cross-tenant modification attempt"}), 403
    tenant_id = current_user_tenant
    try:
        updated = update_tenant_config(tenant_id, payload, user=user)
    except ValueError as val_err:
        return jsonify({"error": str(val_err)}), 400
    return jsonify({
        "status": "success",
        "message": "Tenant configuration updated successfully",
        "config": updated,
    }), 200
