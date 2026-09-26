from flask import session
from models import db, User, Facility


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


def get_allowed_facility_ids(user):
    """
    Returns None if user is admin or superuser with unrestricted location (allowed all).
    Returns [] for it_admin (zero facility/emission data access).
    Returns a list of facility IDs if user is restricted to a region/location/name.
    """
    if not user:
        return []

    # IT Admin, IT Manager & IT roles have zero facility/emission data access.
    if user.role in ["it_admin", "it_manager", "it"]:
        return []

    # Admin has full unrestricted data access.
    if user.role == "admin":
        return None

    # Superuser with unrestricted location has full access across all facilities
    user_region = str(user.location).strip() if user.location else ""
    if user.role == "superuser" and is_unrestricted_location(user_region):
        return None

    if not user_region or is_unrestricted_location(user_region):
        return []  # No region assigned, no access for restricted role

    facilities = Facility.query.filter(
        db.or_(
            Facility.region.ilike(user_region),
            Facility.location.ilike(user_region),
            Facility.name.ilike(user_region),
        )
    ).all()

    allowed_ids = list(set([f.id for f in facilities]))
    return allowed_ids


def require_facility_access(user, facility_id):
    """
    Checks if user has permission to access or modify data for the given facility_id.
    Returns True if permitted, False otherwise.
    """
    if not user or user.role in ["it_admin", "it_manager", "it"]:
        return False
    if user.role == "admin":
        return True
    allowed_ids = get_allowed_facility_ids(user)
    if allowed_ids is None:
        return True
    try:
        return int(facility_id) in [int(fid) for fid in allowed_ids]
    except (ValueError, TypeError):
        return False


def facility_in_user_scope(user, region=None, location=None, name=None):
    """True when a facility with these attributes falls inside the user's region scope.

    Mirrors get_allowed_facility_ids (a regional user sees facilities whose region, location
    or name equals user.location). Used to validate the *resulting* values of facility
    creates/updates so a regional user cannot move a facility out of its own scope
    (audit RC-1: BUG-001, BUG-093).
    """
    if not user or user.role in ["it_admin", "it_manager", "it"]:
        return False
    if user.role == "admin":
        return True
    user_loc = str(user.location or "").strip().lower()
    if user.role == "superuser" and is_unrestricted_location(user_loc):
        return True
    if not user_loc or is_unrestricted_location(user_loc):
        return False
    return user_loc in {str(v or "").strip().lower() for v in (region, location, name)}


def facility_change_allowed(user, current, region=None, location=None, name=None):
    """May `user` create (current=None) or update `current` to these attribute values?

    Regional users must keep the facility in their scope and may not assign a region
    other than their own (re-regioning moves the facility into another region's scope).
    """
    if not facility_in_user_scope(user, region, location, name):
        return False
    if user.role == "admin" or (user.role == "superuser" and is_unrestricted_location(user.location)):
        return True
    user_loc = str(user.location or "").strip().lower()
    old_region = str(getattr(current, "region", None) or "").strip().lower()
    new_region = str(region or "").strip().lower()
    return new_region == old_region or new_region in ("", user_loc)


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

    channel: "manual" (form / API create) or "bulk" (file or JSON import).
    """
    if channel == "bulk":
        return STATUS_PENDING
    if requested_status == STATUS_DRAFT:
        return STATUS_DRAFT
    return STATUS_VERIFIED if user is not None and user.role == "admin" else STATUS_PENDING


def can_approve(user, record):
    """An approver may not approve a record they created or last modified."""
    if user is None or user.role not in APPROVER_ROLES:
        return False
    actor_ids = {getattr(record, "created_by", None), getattr(record, "updated_by", None)}
    return user.id not in actor_ids


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
):
    import json
    from models import ActivityLog, Notification, User
    from extensions import db
    from flask import current_app

    ip_address = request.remote_addr if request else None
    user_name = user.fullName if user else "System"
    user_id = user.id if user else None

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
    )
    db.session.add(log)

    if not user or action not in ["CREATE", "UPDATE", "DELETE"]:
        return

    try:
        if user.role == "superuser":
            admins = User.query.filter_by(role="admin", status="active").all()
            for admin in admins:
                Notification.create(
                    user_id=admin.id,
                    type="SECURITY",
                    title="Super User Activity",
                    message=f"Super User {user.fullName} performed {action}: {details}",
                )
        elif user.role == "user":
            superusers = User.query.filter_by(role="superuser", status="active").all()
            for su in superusers:
                if (
                    not su.location
                    or su.location == user.location
                    or su.location == "all"
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
