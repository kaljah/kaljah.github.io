import csv
import io
import json
import math
import hashlib
import hmac
from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, jsonify, request, Response, current_app
from sqlalchemy import distinct, func
from models import ActivityLog, db
from utils import iso_utc
from utils import get_current_user, log_activity_and_notify, get_allowed_facility_ids

audit_bp = Blueprint("audit", __name__)


def sanitize_csv_cell(val):
    """Prevent CSV formula injection (DDE/Excel macro execution) including leading whitespace bypasses."""
    if val is None:
        return ""
    s = str(val)
    stripped = s.lstrip()
    if stripped and stripped.startswith(("=", "+", "-", "@", "\t", "\r", "%")):
        return f"'{s}"
    return s


def is_it_role(user):
    return bool(user and user.role in ["it_admin", "it_manager", "it"])


def audit_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 204)
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        if user.role not in ["admin", "superuser", "it_admin", "it_manager"]:
            return (
                jsonify(
                    {"error": "Administrative privileges required to access audit logs"}
                ),
                403,
            )
        return f(*args, **kwargs)

    return decorated


SECURITY_ACTIONS = ["LOGIN", "LOGOUT", "REGISTER", "SECURITY", "UPDATE_PASSWORD", "PASSWORD_RESET"]


def _scoped_base(user):
    """Audit rows the user may see.

    - IT roles: security / account-lifecycle actions only.
    - BUG-038: region-restricted business users see entries for facilities in their scope
      and their own actions; entries without a facility (other regions' users, legacy rows)
      stay hidden from them.
    """
    query = ActivityLog.query
    if user and is_it_role(user):
        return query.filter(ActivityLog.action.in_(SECURITY_ACTIONS))
    allowed = get_allowed_facility_ids(user)
    if allowed is not None:
        user_id = user.id if user else -1
        query = query.filter(db.or_(ActivityLog.facility_id.in_(allowed or [-1]), ActivityLog.user_id == user_id))
    return query


def _build_audit_query(current_user=None):
    user_filter = request.args.get("user")
    action_filter = request.args.get("action")
    entity_filter = request.args.get("entity")
    search_query = request.args.get("search", "").strip()
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    query = _scoped_base(current_user)

    if user_filter and user_filter != "all":
        query = query.filter(ActivityLog.user_name == user_filter)

    if action_filter and action_filter != "all":
        query = query.filter(ActivityLog.action == action_filter)

    if entity_filter and entity_filter != "all":
        ent_lower = entity_filter.lower()
        if ent_lower in ("emission", "emissions"):
            query = query.filter(
                db.or_(
                    func.lower(ActivityLog.entity) == "emission",
                    func.lower(ActivityLog.entity) == "scope1_emission",
                    func.lower(ActivityLog.entity) == "scope1emission",
                )
            )
        elif ent_lower in ("batch emissions", "batch_emissions"):
            query = query.filter(func.lower(ActivityLog.entity) == "batch_emissions")
        else:
            query = query.filter(func.lower(ActivityLog.entity) == ent_lower)

    if search_query:
        term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                ActivityLog.user_name.ilike(term),
                ActivityLog.details.ilike(term),
                ActivityLog.record_id.ilike(term),
                ActivityLog.entity_id.ilike(term),
                ActivityLog.ip_address.ilike(term),
                ActivityLog.entity.ilike(term),
                ActivityLog.action.ilike(term),
            )
        )

    if start_date_str:
        try:
            start_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            query = query.filter(ActivityLog.timestamp >= start_dt)
        except Exception:
            pass

    if end_date_str:
        try:
            end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            if len(end_date_str.strip()) == 10:
                end_dt = end_dt.replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
            query = query.filter(ActivityLog.timestamp <= end_dt)
        except Exception:
            pass

    return query


def _serialize_log(log, is_it_user=False):
    old_val = None
    new_val = None
    # IT Admin / Manager separation of duties: redact operational emission / data diffs
    if not is_it_user:
        if log.old_values:
            try:
                old_val = json.loads(log.old_values)
            except Exception:
                old_val = log.old_values
        if log.new_values:
            try:
                new_val = json.loads(log.new_values)
            except Exception:
                new_val = log.new_values

    # Determine stable entity ID with fallback to record_id
    ent_id = log.entity_id or log.record_id

    return {
        "id": log.id,
        "action": log.action or "UNKNOWN",
        "recordId": log.record_id or ent_id,
        "user": log.user_name or "System",
        "details": log.details or "",
        "description": log.details or "",
        "old_values": old_val,
        "new_values": new_val,
        "ipAddress": log.ip_address or "Local / System",
        "entity": log.entity or "General",
        "entityId": ent_id,
        "timestamp": iso_utc(log.timestamp),
    }


@audit_bp.route("/", methods=["GET"])
@audit_access_required
def get_audit_logs():
    user = get_current_user()
    is_it_user = is_it_role(user)
    query = _build_audit_query(current_user=user)

    total_count = query.count()

    try:
        limit = int(request.args.get("limit", 50))
    except (ValueError, TypeError):
        limit = 50
    limit = max(1, min(limit, 500))

    try:
        page = int(request.args.get("page", 1))
    except (ValueError, TypeError):
        page = 1
    page = max(1, page)

    logs = (
        query.order_by(ActivityLog.timestamp.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    result = [_serialize_log(log, is_it_user=is_it_user) for log in logs]
    pages = max(1, math.ceil(total_count / limit))

    response = jsonify(
        {
            "logs": result,
            "total": total_count,
            "page": page,
            "limit": limit,
            "pages": pages,
        }
    )
    response.headers["X-Total-Count"] = str(total_count)
    return response


@audit_bp.route("/stats", methods=["GET"])
@audit_bp.route("/stats/", methods=["GET"])
@audit_access_required
def get_audit_stats():
    user = get_current_user()
    if user and is_it_role(user):
        sec_actions = ["LOGIN", "LOGOUT", "REGISTER", "SECURITY", "UPDATE_PASSWORD", "PASSWORD_RESET"]
        total_events = ActivityLog.query.filter(ActivityLog.action.in_(sec_actions)).count()
        total_logins = ActivityLog.query.filter(ActivityLog.action == "LOGIN").count()
        data_mutations = 0
        security_alerts = ActivityLog.query.filter(
            ActivityLog.action.in_(["SECURITY", "FAILED_LOGIN", "SUSPICIOUS"])
        ).count()
        unique_users = (
            db.session.query(func.count(distinct(ActivityLog.user_name)))
            .filter(ActivityLog.action.in_(sec_actions))
            .scalar()
            or 0
        )
    else:
        base = _scoped_base(user)
        total_events = base.count()
        total_logins = base.filter(ActivityLog.action == "LOGIN").count()
        data_mutations = base.filter(ActivityLog.action.in_(["CREATE", "UPDATE", "DELETE"])).count()
        security_alerts = base.filter(ActivityLog.action.in_(["SECURITY", "FAILED_LOGIN", "SUSPICIOUS"])).count()
        unique_users = base.with_entities(func.count(distinct(ActivityLog.user_name))).scalar() or 0

    return jsonify(
        {
            "totalEvents": total_events,
            "totalLogins": total_logins,
            "dataMutations": data_mutations,
            "securityAlerts": security_alerts,
            "uniqueUsers": unique_users,
        }
    )


@audit_bp.route("/filters", methods=["GET"])
@audit_bp.route("/filters/", methods=["GET"])
@audit_access_required
def get_audit_filters():
    user = get_current_user()
    if user and is_it_role(user):
        sec_actions = ["LOGIN", "LOGOUT", "REGISTER", "SECURITY", "UPDATE_PASSWORD", "PASSWORD_RESET"]
        users = (
            db.session.query(distinct(ActivityLog.user_name))
            .filter(ActivityLog.action.in_(sec_actions))
            .all()
        )
        return jsonify(
            {
                "users": sorted([u[0] for u in users if u[0]]),
                "actions": sorted(sec_actions),
                "entities": ["User", "Security"],
            }
        )

    base = _scoped_base(user)
    users = base.with_entities(distinct(ActivityLog.user_name)).all()
    actions = base.with_entities(distinct(ActivityLog.action)).all()
    entities = base.with_entities(distinct(ActivityLog.entity)).all()

    norm_entities = set()
    for e in entities:
        if e[0]:
            name = e[0].strip()
            if name.lower() in ("emission", "scope1_emission", "scope1emission"):
                norm_entities.add("Emission")
            elif name.lower() in ("batch_emissions", "batch emissions"):
                norm_entities.add("Batch Emissions")
            else:
                norm_entities.add(name)

    return jsonify(
        {
            "users": sorted([u[0] for u in users if u[0]]),
            "actions": sorted([a[0] for a in actions if a[0]]),
            "entities": sorted(list(norm_entities)),
        }
    )


@audit_bp.route("/export", methods=["GET"])
@audit_bp.route("/export/", methods=["GET"])
@audit_access_required
def export_audit_logs():
    export_format = request.args.get("format", "csv").lower()
    user = get_current_user()
    is_it_user = is_it_role(user)
    query = _build_audit_query(current_user=user)

    # Limit maximum export to 10,000 records to prevent memory exhaustion
    logs = query.order_by(ActivityLog.timestamp.desc()).limit(10000).all()
    serialized = [_serialize_log(log, is_it_user=is_it_user) for log in logs]
    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Record the export in the audit trail itself
    try:
        log_activity_and_notify(
            action="EXPORT",
            record_id="audit_export",
            user=user,
            request=request,
            entity="AuditLog",
            details=f"Exported {len(serialized)} audit trail records ({export_format.upper()})",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Audit Log Error on export: {e}")

    if export_format == "json":
        return Response(
            json.dumps(serialized, indent=2),
            mimetype="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="carbon_tech_audit_{timestamp_str}.json"'
            },
        )

    # Default CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "Timestamp (UTC)",
            "User",
            "Action",
            "Entity",
            "Reference ID",
            "Description / Details",
            "Old Values (Before)",
            "New Values (After)",
            "IP Address",
        ]
    )

    for item in serialized:
        old_val_str = (
            json.dumps(item["old_values"])
            if isinstance(item["old_values"], (dict, list))
            else str(item["old_values"] or "")
        )
        new_val_str = (
            json.dumps(item["new_values"])
            if isinstance(item["new_values"], (dict, list))
            else str(item["new_values"] or "")
        )

        writer.writerow(
            [
                sanitize_csv_cell(item["id"]),
                sanitize_csv_cell(item["timestamp"]),
                sanitize_csv_cell(item["user"]),
                sanitize_csv_cell(item["action"]),
                sanitize_csv_cell(item["entity"]),
                sanitize_csv_cell(item["entityId"]),
                sanitize_csv_cell(item["details"]),
                sanitize_csv_cell(old_val_str),
                sanitize_csv_cell(new_val_str),
                sanitize_csv_cell(item["ipAddress"]),
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="carbon_tech_audit_{timestamp_str}.csv"'
        },
    )


# SEC-04: POST /api/audit/ intentionally removed.
# Audit logs are written strictly by server-side application logic.


@audit_bp.route("/verify-chain", methods=["GET"])
@audit_access_required
def verify_audit_chain():
    """
    Verifies the audit log's hash chain (services/audit_chain.py): every entry is recomputed and compared
    with the hash sealed when it was written, and each entry's link to the one before it is checked.
    Reports "verified" only when no entry was changed, removed or inserted; otherwise "tampered" with the
    entries concerned. Removing the newest entries is detected by comparing with a saved checkpoint
    (chain_head_hash, total_records, checkpoint_hmac) through /verify-checkpoint.
    """
    user = get_current_user()
    if get_allowed_facility_ids(user) is not None and not is_it_role(user):
        return jsonify({"error": "Chain verification requires organisation-wide audit access"}), 403
    from services.audit_chain import GENESIS_HASH, verify_chain

    query = ActivityLog.query.order_by(ActivityLog.id.asc()).yield_per(1000)
    total_records, head_hash, issues, issue_count = verify_chain(query)

    hmac_key = (current_app.config.get("SECRET_KEY") or "sonatrach-audit-secure-key").encode("utf-8")
    checkpoint_payload = f"{head_hash}:{total_records}"
    checkpoint_hmac = hmac.new(hmac_key, checkpoint_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    ok = issue_count == 0

    return jsonify({
        "status": "verified" if ok else "tampered",
        "is_intact": ok,
        "total_records": total_records,
        "issue_count": issue_count,
        "issues": issues,
        "genesis_hash": GENESIS_HASH,
        "chain_head_hash": head_hash,
        "checkpoint_hmac": checkpoint_hmac,
        "hmac_algorithm": "HMAC-SHA256",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "method": "SHA-256 hash chain sealed at write time; save chain_head_hash, total_records and "
                  "checkpoint_hmac to detect later removal of the newest entries.",
    })


@audit_bp.route("/verify-checkpoint", methods=["POST"])
@audit_access_required
def verify_audit_checkpoint():
    """
    Verifies a third-party auditor's sealed audit manifest checkpoint against the
    server's cryptographic HMAC key (ISO 14064-3 / ISAE 3410 assurance).
    """
    data = request.get_json() or {}
    chain_head_hash = data.get("chain_head_hash")
    total_records = data.get("total_records")
    provided_hmac = data.get("checkpoint_hmac")

    if not chain_head_hash or total_records is None or not provided_hmac:
        return jsonify({"error": "Missing required fields: chain_head_hash, total_records, checkpoint_hmac"}), 400

    hmac_key = (current_app.config.get("SECRET_KEY") or "sonatrach-audit-secure-key").encode("utf-8")
    checkpoint_payload = f"{chain_head_hash}:{total_records}"
    expected_hmac = hmac.new(hmac_key, checkpoint_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    is_valid = hmac.compare_digest(str(provided_hmac).strip(), expected_hmac)
    return jsonify({
        "valid": is_valid,
        "status": "authenticated" if is_valid else "rejected",
        "algorithm": "HMAC-SHA256",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "standard": "ISO 14064-3 / ISAE 3410 Cryptographic Checkpoint Assurance",
    })
