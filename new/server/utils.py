from flask import session
from models import db, User, Facility


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def get_allowed_facility_ids(user):
    """
    Returns None if user is admin/it_admin/superuser (allowed all).
    Returns a list of facility IDs if user is restricted to a region.
    """
    if not user:
        return []
    if user.role in ["admin", "it_admin"] or (
        user.role == "superuser" and user.location == "all"
    ):
        return None

    # User is tied to a specific location/region
    user_region = user.location
    if not user_region:
        return []  # No region assigned, no access

    facilities = Facility.query.filter(
        db.or_(Facility.region == user_region, Facility.location == user_region)
    ).all()

    allowed_ids = list(set([f.id for f in facilities]))
    return allowed_ids


def log_activity_and_notify(
    action,
    record_id,
    details,
    user=None,
    request=None,
    entity=None,
    entity_id=None,
    metadata_json=None,
):
    from models import ActivityLog, Notification, User
    from extensions import db
    from flask import current_app

    ip_address = request.remote_addr if request else None
    user_name = user.fullName if user else "System"
    user_id = user.id if user else None

    log = ActivityLog(
        action=action,
        record_id=str(record_id),
        user_name=user_name,
        details=details,
        ip_address=ip_address,
        user_id=user_id,
        entity=entity,
        entity_id=str(entity_id) if entity_id else None,
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
