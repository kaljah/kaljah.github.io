import csv
import io
import json
import math
from datetime import datetime, timezone
from functools import wraps
from flask import Blueprint, jsonify, request, Response, current_app
from sqlalchemy import distinct, func
from models import ActivityLog, db
from utils import get_current_user, log_activity_and_notify

audit_bp = Blueprint("audit", __name__)


def sanitize_csv_cell(val):
    """Prevent CSV formula injection (DDE/Excel macro execution)."""
    if val is None:
        return ""
    s = str(val)
    if s.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{s}"
    return s


def audit_access_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 204)
        user = get_current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        if user.role not in ["admin", "superuser", "it_admin"]:
            return (
                jsonify(
                    {"error": "Administrative privileges required to access audit logs"}
                ),
                403,
            )
        return f(*args, **kwargs)

    return decorated


def _build_audit_query():
    user_filter = request.args.get("user")
    action_filter = request.args.get("action")
    entity_filter = request.args.get("entity")
    search_query = request.args.get("search", "").strip()
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")

    query = ActivityLog.query

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


def _serialize_log(log):
    old_val = None
    new_val = None
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
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }


@audit_bp.route("/", methods=["GET"])
@audit_access_required
def get_audit_logs():
    query = _build_audit_query()

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

    result = [_serialize_log(log) for log in logs]
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
    total_events = ActivityLog.query.count()
    total_logins = ActivityLog.query.filter(ActivityLog.action == "LOGIN").count()
    data_mutations = ActivityLog.query.filter(
        ActivityLog.action.in_(["CREATE", "UPDATE", "DELETE"])
    ).count()
    security_alerts = ActivityLog.query.filter(
        ActivityLog.action.in_(["SECURITY", "FAILED_LOGIN", "SUSPICIOUS"])
    ).count()
    unique_users = (
        db.session.query(func.count(distinct(ActivityLog.user_name))).scalar() or 0
    )

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
    users = db.session.query(distinct(ActivityLog.user_name)).all()
    actions = db.session.query(distinct(ActivityLog.action)).all()
    entities = db.session.query(distinct(ActivityLog.entity)).all()

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
    query = _build_audit_query()

    # Limit maximum export to 10,000 records to prevent memory exhaustion
    logs = query.order_by(ActivityLog.timestamp.desc()).limit(10000).all()
    serialized = [_serialize_log(log) for log in logs]

    user = get_current_user()
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
