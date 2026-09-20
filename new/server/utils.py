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

    # admin has full unrestricted data access.
    # superuser with location in UNRESTRICTED_LOCATIONS also gets unrestricted access.
    if user.role == "admin" or (
        user.role == "superuser" and is_unrestricted_location(user.location)
    ):
        return None

    # User is tied to a specific location/region
    user_region = str(user.location).strip() if user.location else ""
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
