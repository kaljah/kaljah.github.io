"""Saved column mappings for the import wizard (/api/emissions/upload/mappings).

Registered on the same ``emissions_bp`` blueprint; routes/emissions.py imports this module last.
"""
from extensions import db
from flask import jsonify, request
from routes.auth import login_required
from utils import get_current_user
from . import emissions_bp

# ── Saved column mappings (import wizard) ─────────────────────────────────────
_MAPPING_SCOPES = ("1", "2", "3", "3_eeio", "sources", "production", "mitigation", "custom_factors", "facilities")
MAX_SAVED_MAPPINGS = 50


@emissions_bp.route("/upload/mappings", methods=["GET"])
@login_required
def list_import_mappings():
    """The user's saved column mappings for an import type, most recently used first."""
    from models import ImportMapping

    user = get_current_user()
    scope = str(request.args.get("scope", "1"))
    rows = ImportMapping.query.filter_by(user_id=user.id, scope=scope).all()
    rows.sort(key=lambda m: (m.last_used_at or m.updated_at or m.created_at).isoformat() if (
        m.last_used_at or m.updated_at or m.created_at) else "", reverse=True)
    return jsonify([m.to_dict() for m in rows])


@emissions_bp.route("/upload/mappings", methods=["POST"])
@login_required
def save_import_mapping():
    """Save (or replace, by name) a column mapping: {scope, name, headers: [...], mapping: {field: column}}."""
    import json

    from models import ImportMapping

    user = get_current_user()
    data = request.get_json(silent=True) or {}
    scope = str(data.get("scope", "1"))
    name = str(data.get("name") or "").strip()
    headers = data.get("headers")
    mapping = data.get("mapping")
    if scope not in _MAPPING_SCOPES:
        return jsonify({"error": f"Unknown import type '{scope}'"}), 400
    if not name or len(name) > 80:
        return jsonify({"error": "Give the mapping a name (80 characters at most)"}), 400
    if not isinstance(headers, list) or not headers or len(headers) > 500 or not all(
            isinstance(h, str) and len(h) <= 200 for h in headers):
        return jsonify({"error": "headers must be the file's column names"}), 400
    if not isinstance(mapping, dict) or not mapping or len(mapping) > 500:
        return jsonify({"error": "mapping must be an object of field -> column"}), 400
    clean = {}
    for k, v in mapping.items():
        if not (isinstance(k, str) and isinstance(v, str) and len(k) <= 100):
            return jsonify({"error": "mapping must be an object of field -> column"}), 400
        if v:
            if v not in headers:
                return jsonify({"error": f"Column '{v}' is not one of the file's columns"}), 400
            clean[k] = v
    if not clean:
        return jsonify({"error": "The mapping has no matched column"}), 400

    row = ImportMapping.query.filter_by(user_id=user.id, scope=scope, name=name).first()
    if row is None:
        if ImportMapping.query.filter_by(user_id=user.id).count() >= MAX_SAVED_MAPPINGS:
            return jsonify({"error": f"You have {MAX_SAVED_MAPPINGS} saved mappings: delete one first"}), 400
        row = ImportMapping(user_id=user.id, scope=scope, name=name)
        db.session.add(row)
    row.headers = json.dumps(headers)
    row.mapping = json.dumps(clean)
    from models import utc_now

    row.updated_at = utc_now()
    db.session.commit()
    return jsonify(row.to_dict()), 201


@emissions_bp.route("/upload/mappings/<int:mapping_id>/used", methods=["POST"])
@login_required
def touch_import_mapping(mapping_id):
    """Mark a saved mapping as used (it is then offered first)."""
    from models import ImportMapping, utc_now

    row = ImportMapping.query.filter_by(id=mapping_id, user_id=get_current_user().id).first()
    if row is None:
        return jsonify({"error": "Not found"}), 404
    row.last_used_at = utc_now()
    db.session.commit()
    return jsonify(row.to_dict())


@emissions_bp.route("/upload/mappings/<int:mapping_id>", methods=["DELETE"])
@login_required
def delete_import_mapping(mapping_id):
    from models import ImportMapping

    row = ImportMapping.query.filter_by(id=mapping_id, user_id=get_current_user().id).first()
    if row is None:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"deleted": mapping_id})
