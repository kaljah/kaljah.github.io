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


@tenant_bp.route("/config", methods=["GET"])
def get_config():
    """Retrieve tenant configuration for the current user or tenant query."""
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
    tenant_id = tenant_param or get_current_tenant_id(user)
    updated = update_tenant_config(tenant_id, payload, user=user)
    return jsonify({
        "status": "success",
        "message": "Tenant configuration updated successfully",
        "config": updated,
    }), 200
