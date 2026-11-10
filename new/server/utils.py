import os
from flask import has_request_context, session
from models import db, User, Facility


def normalize_tenant_id(value):
    text = str(value or "").strip().lower()
    return text or "default"


def get_current_tenant_id(user=None):
    """Resolve normalized tenant identifier from the authenticated user (or session/env)."""
    if user is None and has_request_context():
        user = get_current_user()
    if user is not None:
        raw_tid = normalize_tenant_id(getattr(user, "tenant_id", None))
        if raw_tid != "default":
            return raw_tid
        org = str(getattr(user, "orgName", "") or "").lower().strip()
        if "al-amal" in org or "alamal" in org or "tenant_b" in org:
            return "mena_operator_b"
        if raw_tid:
            return raw_tid
    if has_request_context() and session.get("tenant_id"):
        return normalize_tenant_id(session.get("tenant_id"))
    return normalize_tenant_id(os.environ.get("DEFAULT_TENANT_ID", "default"))


def tenant_matches(column, tenant_id=None):
    """SQLAlchemy filter expression matching rows owned by `tenant_id`."""
    tid = normalize_tenant_id(tenant_id)
    trimmed_lower = db.func.lower(db.func.trim(column))
    if tid == "default":
        return db.or_(
            column.is_(None),
            db.func.trim(column) == "",
            trimmed_lower == "default",
        )
    return db.and_(column.isnot(None), trimmed_lower == tid)


def has_multi_tenant_data():
    """Return True if any non-default tenant exists in users or facilities."""
    for model in (Facility, User):
        col = getattr(model, "tenant_id", None)
        if col is None:
            continue
        hit = (
            db.session.query(model.id)
            .filter(
                col.isnot(None),
                db.func.trim(col) != "",
                db.func.lower(db.func.trim(col)) != "default",
            )
            .first()
        )
        if hit is not None:
            return True
    return False


def is_org_wide_user(user):
    """True for tenant-wide compliance roles (admin or unrestricted auditor)."""
    return bool(
        user
        and (
            user.role == "admin"
            or (user.role == "auditor" and is_unrestricted_location(getattr(user, "location", None)))
        )
    )


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


UNRESTRICTED_LOCATIONS = {"all", "global", "", None}


def is_unrestricted_location(loc):
    if loc is None:
        return True
    return str(loc).strip().lower() in {"all", "global", ""}


def is_it_role(user):
    """Check if user belongs to an IT administration role."""
    return bool(user and getattr(user, "role", None) in ["it_admin", "it_manager", "it"])


def get_allowed_facility_ids(user):
    """
    Returns None when operating in single-tenant mode for an org-wide admin / unrestricted auditor.
    When multiple tenants exist or caller belongs to a non-default tenant, returns only that
    tenant's facility IDs (list[int]) so admins never read across tenants.
    Returns [] for it, it_admin, it_manager (zero facility/emission data access).
    Returns a list of facility IDs if user is restricted to a region/location/facility (including superuser).
    """
    if not user:
        return []

    # IT Admin, IT Manager & IT roles have zero facility/emission data access.
    if user.role in ["it_admin", "it_manager", "it"]:
        return []

    caller_tenant = get_current_tenant_id(user)

    # Org-wide admin or unrestricted auditor: strictly scoped to caller's tenant.
    if user.role == "admin" or (user.role == "auditor" and is_unrestricted_location(user.location)):
        if caller_tenant == "default" and not has_multi_tenant_data():
            return None
        rows = (
            db.session.query(Facility.id)
            .filter(tenant_matches(Facility.tenant_id, caller_tenant))
            .all()
        )
        return [fid for (fid,) in rows]

    # Check explicit UserFacilityAccess table first (granular per-facility assignment, tenant-scoped)
    try:
        from models import UserFacilityAccess
        user_accesses = (
            db.session.query(UserFacilityAccess.facility_id)
            .join(Facility, UserFacilityAccess.facility_id == Facility.id)
            .filter(
                UserFacilityAccess.user_id == user.id,
                tenant_matches(Facility.tenant_id, caller_tenant),
            )
            .all()
        )
        if user_accesses:
            return list(set(fid for (fid,) in user_accesses))
    except Exception:
        pass

    # Superuser and regular users: fallback to assigned facility/region string matching within tenant.
    user_region = str(user.location).strip() if user.location else ""
    if not user_region or is_unrestricted_location(user_region):
        return []  # No specific facility/region assigned, no access for scoped role

    # Audit 2026-10-14 BUG-0010: exact case-insensitive match within caller's tenant.
    wanted = user_region.lower()
    facilities = Facility.query.filter(
        tenant_matches(Facility.tenant_id, caller_tenant),
        db.or_(
            db.func.lower(db.func.trim(Facility.region)) == wanted,
            db.func.lower(db.func.trim(Facility.location)) == wanted,
            db.func.lower(db.func.trim(Facility.name)) == wanted,
        ),
    ).all()

    allowed_ids = list(set([f.id for f in facilities]))
    return allowed_ids


def facility_access_error(user, facility_id):
    """Error response for a write to `facility_id`: 403 when the user may not use it, 404 when it does not
    exist (an unknown id was a foreign-key error, a 500: pilot check 2026-10-09, F13). None when allowed."""
    from flask import jsonify
    from models import Facility

    fid = facility_id if isinstance(facility_id, int) and not isinstance(facility_id, bool) else (
        int(facility_id) if isinstance(facility_id, str) and facility_id.strip().isdigit() else None)
    if fid is None or not 0 < fid < 2**31:
        return jsonify({"error": "Invalid facility_id: must be a positive integer", "field": "facility_id"}), 422
    target = db.session.get(Facility, fid)
    if target is None:
        caller_tenant = get_current_tenant_id(user) if user else "default"
        if caller_tenant != "default" or has_multi_tenant_data():
            if not require_facility_access(user, fid):
                return jsonify({"error": "Access to this facility is denied"}), 403
        return jsonify({"error": "Facility not found"}), 404
    if not require_facility_access(user, fid):
        return jsonify({"error": "Access to this facility is denied"}), 403
    return None


def require_facility_access(user, facility_id):
    """
    Checks if user has permission to access or modify data for the given facility_id.
    Enforces tenant isolation even for org-wide admin users.
    Returns True if permitted, False otherwise.
    """
    if not user or user.role in ["it_admin", "it_manager", "it"]:
        return False
    try:
        fid = int(facility_id)
    except (ValueError, TypeError):
        return False
    allowed_ids = get_allowed_facility_ids(user)
    if allowed_ids is None:
        return True
    return fid in [int(x) for x in allowed_ids]


def user_label(user):
    """Human-readable identity snapshot stored on records (BUG-069)."""
    if user is None:
        return None
    name = (getattr(user, "fullName", None) or "").strip()
    email = (getattr(user, "email", None) or "").strip()
    return f"{name} <{email}>" if name and email else (name or email or f"user#{user.id}")


def facility_in_user_scope(user, region=None, location=None, name=None, facility_id=None):
    """True when a facility with these attributes falls inside the user's tenant & region/facility scope."""
    if not user or user.role in ["it_admin", "it_manager", "it"]:
        return False
    if facility_id is not None and not require_facility_access(user, facility_id):
        return False
    if user.role == "admin":
        if facility_id is None:
            return True
        target = db.session.get(Facility, int(facility_id))
        if target is None:
            return False
        return normalize_tenant_id(getattr(target, "tenant_id", None)) == get_current_tenant_id(user)
    allowed_ids = get_allowed_facility_ids(user)
    if allowed_ids is not None and facility_id is not None:
        try:
            if int(facility_id) in [int(fid) for fid in allowed_ids]:
                return True
        except (ValueError, TypeError):
            pass
    user_loc = str(user.location or "").strip().lower()
    if not user_loc or is_unrestricted_location(user_loc):
        return False
    return user_loc in {str(v or "").strip().lower() for v in (region, location, name)}


def facility_change_allowed(user, current, region=None, location=None, name=None):
    """May `user` create (current=None) or update `current` to these attribute values?

    Enforces tenant isolation for all roles, and keeps regional users in their scope.
    """
    fac_id = getattr(current, "id", None)
    if current is not None and normalize_tenant_id(getattr(current, "tenant_id", None)) != get_current_tenant_id(user):
        return False
    if not facility_in_user_scope(user, region, location, name, facility_id=fac_id):
        return False
    if user.role == "admin":
        return True
    user_loc = str(user.location or "").strip().lower()
    old_region = str(getattr(current, "region", None) or "").strip().lower()
    new_region = str(region or "").strip().lower()
    if not (new_region == old_region or new_region in ("", user_loc)):
        return False
    caller_tenant = get_current_tenant_id(user)
    foreign = _scope_keys(caller_tenant) - {user_loc}
    for field, value in (("region", region), ("location", location), ("name", name)):
        v = str(value or "").strip().lower()
        if v and v in foreign and v != str(getattr(current, field, None) or "").strip().lower():
            return False
    return True


def _scope_keys(tenant_id=None):
    """Lower-cased values a regional scope can be keyed on within a tenant."""
    tid = normalize_tenant_id(tenant_id) if tenant_id is not None else get_current_tenant_id()
    keys = {
        str(r or "").strip().lower()
        for (r,) in db.session.query(Facility.region).filter(tenant_matches(Facility.tenant_id, tid)).distinct()
    }
    keys |= {
        str(loc or "").strip().lower()
        for (loc,) in db.session.query(User.location)
        .filter(User.role.in_(["user", "superuser"]), tenant_matches(User.tenant_id, tid))
        .distinct()
    }
    return {k for k in keys if k and not is_unrestricted_location(k)}


class NameMap(dict):
    """Case-insensitive name -> object map for bulk imports.

    Rows with a NULL/blank name are skipped (BUG-029: a NULL facility name crashed every
    import) and names shared by several objects are left out and listed in ``ambiguous``
    so a lookup can never silently pick one of them (BUG-065).
    """

    def __init__(self):
        super().__init__()
        self.ambiguous = set()

    def add(self, key, obj, overwrite=True):
        key = str(key or "").strip().lower()
        if not key or key in self.ambiguous:
            return
        if key in self and self[key] is not obj:
            if overwrite:
                del self[key]
                self.ambiguous.add(key)
            return
        self[key] = obj


def build_name_map(objs, attr="name"):
    m = NameMap()
    for o in objs:
        m.add(getattr(o, attr, None), o)
    return m


# ── Maker-checker status policy (audit RC-2) ────────────────────────────────
# One rule for every scope and channel: only an admin's own manual entry is
# Verified on creation; everything else waits for an approver.
STATUS_DRAFT = "Draft"
STATUS_PENDING = "Pending"
STATUS_VERIFIED = "Verified"
STATUS_REJECTED = "Rejected"
APPROVER_ROLES = ("admin", "superuser")


def initial_record_status(user, requested_status=None, channel="manual"):
    """Status for a newly created emission-type record.

    channel: "manual" (form / API create) or "bulk" (file or JSON import). Compliance admins are
    trusted for both: their records are Verified at once (decision 2026-10-09); everyone else's wait
    for an approver.
    """
    if channel != "bulk" and requested_status == STATUS_DRAFT:
        return STATUS_DRAFT
    return STATUS_VERIFIED if user is not None and user.role == "admin" else STATUS_PENDING


def bulk_status_fields(user):
    """status / approved_by / approved_at for a record created or overwritten by a bulk import."""
    import datetime

    status = initial_record_status(user, channel="bulk")
    verified = status == STATUS_VERIFIED
    return {"status": status, "approved_by": user.id if verified else None,
            "approved_at": datetime.datetime.now(datetime.timezone.utc) if verified else None}


def can_approve(user, record):
    """An approver may not approve a record they created or last modified."""
    if user is None or user.role not in APPROVER_ROLES:
        return False
    actor_ids = {getattr(record, "created_by", None), getattr(record, "updated_by", None)}
    return user.id not in actor_ids


_FACILITY_ENTITIES = {
    "Emission": "Emission", "Scope1": "Emission", "Scope1Emission": "Emission", "Scope2": "Scope2Emission", "Scope2Emission": "Scope2Emission",
    "Scope3": "Scope3Emission", "Scope3Emission": "Scope3Emission", "ProductionData": "ProductionData",
    "Production": "ProductionData", "OgmpSurvey": "OgmpSurvey",
    "MitigationProject": "MitigationProject", "EmissionSource": "EmissionSource",
}


def _resolve_log_facility(entity, record_id):
    """BUG-038: attach the facility to an ActivityLog row so the audit trail can be region-scoped."""
    import models
    from extensions import db

    if entity == "Facility":
        try:
            return int(record_id)
        except (TypeError, ValueError):
            return None
    model_name = _FACILITY_ENTITIES.get(entity or "")
    if not model_name:
        return None
    try:
        obj = db.session.get(getattr(models, model_name), int(record_id))
    except Exception:
        return None
    return getattr(obj, "facility_id", None) if obj is not None else None



def get_client_ip(req=None):
    """Extract client IP, inspecting X-Forwarded-For if behind a proxy / dev server."""
    if not req:
        return None
    xff = req.headers.get("X-Forwarded-For")
    if xff:
        ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
        if ips and (req.remote_addr in ("127.0.0.1", "::1", "localhost", None) or os.environ.get("BEHIND_PROXY")):
            return ips[0]
    return req.remote_addr

def log_activity_and_notify(
    action,
    record_id,
    details,
    user=None,
    request=None,
    entity=None,
    entity_id=None,
    metadata_json=None,
    old_values=None,
    new_values=None,
    facility_id=None,
):
    import json
    from models import ActivityLog, Notification, User
    from extensions import db
    from flask import current_app

    ip_address = get_client_ip(request) if request else None
    if isinstance(user, str):
        user_name = user
        user_id = None
    elif user:
        user_name = getattr(user, "fullName", None) or getattr(user, "email", None) or str(user)
        user_id = getattr(user, "id", None)
    else:
        user_name = "System"
        user_id = None

    # Serialize before/after state diffs if provided as dicts
    old_val_str = json.dumps(old_values, default=str) if isinstance(old_values, dict) else (str(old_values) if old_values is not None else None)
    new_val_str = json.dumps(new_values, default=str) if isinstance(new_values, dict) else (str(new_values) if new_values is not None else None)

    log = ActivityLog(
        action=action,
        record_id=str(record_id),
        user_name=user_name,
        details=details,
        old_values=old_val_str,
        new_values=new_val_str,
        ip_address=ip_address,
        user_id=user_id,
        entity=entity,
        entity_id=str(entity_id) if entity_id else (str(record_id) if record_id is not None else None),
        metadata_json=metadata_json,
        facility_id=facility_id if facility_id is not None else _resolve_log_facility(entity, entity_id or record_id),
    )
    db.session.add(log)

    if not user or action not in ["CREATE", "UPDATE", "DELETE"]:
        return

    try:
        caller_tenant = get_current_tenant_id(user) if not isinstance(user, str) else "default"
        if user.role == "superuser":
            admins = (
                User.query.filter_by(role="admin", status="active")
                .filter(tenant_matches(User.tenant_id, caller_tenant))
                .all()
            )
            for admin in admins:
                Notification.create(
                    user_id=admin.id,
                    type="SECURITY",
                    title="Super User Activity",
                    message=f"Super User {user.fullName} performed {action}: {details}",
                )
        elif user.role == "user":
            superusers = (
                User.query.filter_by(role="superuser", status="active")
                .filter(tenant_matches(User.tenant_id, caller_tenant))
                .all()
            )
            for su in superusers:
                if (  # superusers are facility/region-scoped: only their own scope's activity
                    su.location
                    and not is_unrestricted_location(su.location)
                    and str(su.location).strip().lower() == str(user.location or "").strip().lower()
                ):
                    Notification.create(
                        user_id=su.id,
                        type="SECURITY",
                        title="User Activity",
                        message=f"User {user.fullName} performed {action}: {details}",
                    )
    except Exception as e:
        if current_app:
            current_app.logger.error(f"Failed to create notification: {str(e)}")


def internal_error(exc, message="Internal server error", status=500, **extra):
    """BUG-087: log the exception server-side and return a generic body (no exception text)."""
    from flask import current_app, jsonify
    from input_validation import ValidationError

    if isinstance(exc, ValidationError):
        return jsonify({"error": exc.message, "field": exc.field, "code": 400}), 400

    try:
        current_app.logger.error("%s: %s", message, exc, exc_info=exc)
    except Exception:
        pass
    body = {"error": message}
    if "status_text" in extra:  # QA endpoints answer {"status": "error", "message": ...}
        body.update(status=extra.pop("status_text"), message=message)
    body.update(extra)
    return jsonify(body), status



def iso_utc(dt):
    """ISO 8601 with an explicit UTC offset. Stored datetimes are naive UTC (SQLite drops the
    zone); without the offset browsers read them as local time (browser test #19: the audit trail
    was two hours behind and new events read "2h ago")."""
    if dt is None:
        return None
    from datetime import timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def clear_dashboard_cache():
    try:
        from routes.dashboard import clear_dashboard_cache as _cdc
        _cdc()
    except Exception:
        pass

