"""REPORT audit entry for documents generated in the browser (ISO 14064-1 PDF, executive brief).

The server-built exports record their data fingerprint themselves (services.audit_chain); a report built
in the browser posts the SHA-256 of its data here, prints the same value in the document, and so gets
the same audit trail (ADM-15).
"""
import re

from flask import jsonify, request

from routes.auth import login_required
from services.audit_chain import record_report_fingerprint
from utils import get_current_user
from routes.reports import reports_bp

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@reports_bp.route("/fingerprint", methods=["POST"])
@login_required
def record_browser_report():
    user = get_current_user()
    if not user or user.role in ("it", "it_admin", "it_manager"):
        return jsonify({"error": "Forbidden: IT personnel cannot generate operational reports"}), 403
    data = request.get_json(silent=True) or {}
    fingerprint = str(data.get("fingerprint") or "").lower()
    if not _SHA256.match(fingerprint):
        return jsonify({"error": "'fingerprint' must be a SHA-256 hex digest", "field": "fingerprint"}), 400
    kind = str(data.get("kind") or "Browser report")[:80]
    filters = data.get("filters") if isinstance(data.get("filters"), dict) else {}
    try:
        count = max(0, int(data.get("record_count") or 0))
    except (TypeError, ValueError):
        count = 0
    return record_report_fingerprint(jsonify({"fingerprint": fingerprint}), user, kind, filters, count, fingerprint)
