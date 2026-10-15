"""User management routes (IT administration).

Split out of routes/auth.py unchanged (hardening plan, task 5.3). The routes are registered on the
same ``auth_bp`` blueprint, and routes.auth re-exports every name, so imports and URLs are the same.
"""
import datetime
import json
from extensions import db
from flask import current_app, jsonify, request, session
from models import Notification, User
from services.session_policy import forget_cached_timeout
from utils import internal_error, is_unrestricted_location, log_activity_and_notify
from . import auth_bp
from routes.auth import (
    BUSINESS_ROLE_GRANTORS,
    BUSINESS_ROLES,
    CLIENT_IT_PROTECTED_ROLES,
    CLIENT_IT_ROLES,
    IT_ADMIN_PROTECTED_ROLES,
    ROLE_RANK,
    SUPERUSER_REGION_ERROR,
    VENDOR_PROTECTED_ROLES,
    it_access_required,
    it_admin_required,
    register,
    validate_password_complexity,
)


USER_STATUSES = ("active", "inactive", "disabled")


def _user_json(u):
    return {k: getattr(u, k) for k in ("id", "fullName", "email", "orgName", "role", "location", "department",
                                       "jobTitle", "status")}


@auth_bp.route("/users", methods=["POST"])
@it_admin_required
def create_user():
    return register()


@auth_bp.route("/users", methods=["GET"])
@it_access_required
def get_users():
    # Force expire session cache so we always read fresh data from DB
    db.session.expire_all()

    # IT Admins have global authority over all accounts — no regional restriction
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([
        dict(_user_json(u), created_at=u.created_at.isoformat() if u.created_at else None,
             last_login=u.last_login.isoformat() if u.last_login else None)
        for u in users
    ])


@auth_bp.route("/users/<int:id>", methods=["PUT"])
@it_admin_required
def update_user(id):
    db.session.expire_all()
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # IT Admins have global authority over all user accounts — no regional restriction
    it_admin_id = session.get("user_id")
    it_admin = db.session.get(User, it_admin_id)

    data = request.get_json(silent=True) or {}
    requester_is_client_it = bool(it_admin and it_admin.role in CLIENT_IT_ROLES)
    if requester_is_client_it and user.role in CLIENT_IT_PROTECTED_ROLES:
        return jsonify({"error": "Forbidden: Client IT staff cannot modify Compliance Admin, Superuser or platform operator accounts"}), 403
    if it_admin and it_admin.role == "it_admin" and user.role in IT_ADMIN_PROTECTED_ROLES:
        return jsonify({"error": "Forbidden: IT Administrator cannot modify Compliance Admin, Superuser, Auditor or platform operator accounts"}), 403

    VALID_ROLES = set(ROLE_RANK.keys())
    requester_rank = ROLE_RANK.get(it_admin.role if it_admin else "user", 0)

    if "role" in data:
        new_role = str(data["role"]).strip().lower()
        if new_role not in VALID_ROLES:
            return jsonify({"error": f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}"}), 400
        if it_admin and user.id == it_admin.id and new_role != user.role:
            return jsonify({"error": "You cannot change your own role"}), 403
        # Separation of Duties: Only authorized grantors may assign business roles
        if new_role in BUSINESS_ROLES and it_admin.role not in BUSINESS_ROLE_GRANTORS:
            return jsonify({"error": "Forbidden: IT Administrators cannot assign business compliance roles (admin, superuser)"}), 403
        if requester_is_client_it and new_role in CLIENT_IT_PROTECTED_ROLES:
            return jsonify({"error": "Forbidden: Client IT staff cannot assign the admin, superuser or it_manager role"}), 403
        if it_admin and it_admin.role == "it_admin" and new_role in VENDOR_PROTECTED_ROLES:
            return jsonify({"error": "Forbidden: IT Administrator cannot assign platform operator role"}), 403
        target_new_rank = ROLE_RANK.get(new_role, 0)
        if target_new_rank > requester_rank:
            return jsonify({"error": "Cannot assign a role higher than your own"}), 403
        user.role = new_role

    if "fullName" in data and data["fullName"]:
        new_name = str(data["fullName"]).strip()
        if new_name:
            user.fullName = new_name

    if "email" in data and data["email"]:
        new_email = str(data["email"]).strip().lower()
        if new_email and new_email != (user.email or "").lower():
            existing = User.query.filter(db.func.lower(User.email) == new_email, User.id != user.id).first()
            if existing:
                return jsonify({"error": "Email is already in use by another account"}), 400
            user.email = new_email

    if "department" in data:
        user.department = str(data["department"]).strip() if data["department"] else ""

    if "jobTitle" in data:
        user.jobTitle = str(data["jobTitle"]).strip() if data["jobTitle"] else ""

    if "location" in data:
        user.location = data["location"]
    if ("role" in data or "location" in data) and user.role == "superuser" and is_unrestricted_location(user.location):
        db.session.rollback()
        return jsonify({"error": SUPERUSER_REGION_ERROR, "field": "location"}), 400
    if "status" in data:
        # audit 2026-10-14 BUG-0038: a known status only, and the last active admin stays active
        new_status = str(data["status"] or "").strip().lower()
        if new_status not in USER_STATUSES:
            db.session.rollback()
            return jsonify({"error": f"Invalid status. Must be one of: {', '.join(USER_STATUSES)}",
                            "field": "status"}), 400
        if (user.role == "admin" and user.status == "active" and new_status != "active"
                and User.query.filter_by(role="admin", status="active").count() <= 1):
            db.session.rollback()
            return jsonify({"error": "This is the last active administrator account"}), 409
        data["status"] = new_status
        if data["status"] != user.status:
            user.session_version = int(user.session_version or 0) + 1  # BUG-114
        user.status = data["status"]

    log_activity_and_notify(
        action="UPDATE",
        record_id=str(user.id),
        user=it_admin,
        request=request,
        entity="User",
        details=f"User {user.email} updated by {it_admin.fullName if it_admin else 'IT Admin'}",
    )
    db.session.commit()
    # Return updated user so frontend can reflect changes immediately
    return jsonify({"message": "User updated successfully", "user": _user_json(user)})


@auth_bp.route("/users/<int:id>", methods=["DELETE"])
@it_admin_required
def delete_user(id):
    if id == session.get("user_id"):
        return jsonify({"error": "Cannot delete your own account"}), 400

    db.session.expire_all()
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # IT Admins have global authority over all user accounts — no regional restriction
    it_admin_id = session.get("user_id")
    it_admin = db.session.get(User, it_admin_id)
    if it_admin and it_admin.role in CLIENT_IT_ROLES and user.role in CLIENT_IT_PROTECTED_ROLES:
        return jsonify({"error": "Forbidden: Client IT staff cannot delete Compliance Admin, Superuser or platform operator accounts"}), 403
    if it_admin and it_admin.role == "it_admin" and user.role in IT_ADMIN_PROTECTED_ROLES:
        return jsonify({"error": "Forbidden: IT Administrator cannot delete Compliance Admin, Superuser, Auditor or platform operator accounts"}), 403
    # review 2026-10-15: the same guard as disabling (BUG-0038); deleting skipped it
    if (user.role == "admin" and user.status == "active"
            and User.query.filter_by(role="admin", status="active").count() <= 1):
        return jsonify({"error": "This is the last active administrator account"}), 409

    # BUG-010 / BUG-069: derive every reference to users.id from the schema instead of a
    # hand-maintained list, and keep the maker-checker identity on the records.
    from sqlalchemy import text
    from utils import user_label

    label = user_label(user)
    db.session.execute(text("DELETE FROM notifications WHERE user_id = :uid"), {"uid": id})
    # saved import column mappings are personal (user_id is NOT NULL): they go with the account
    db.session.execute(text("DELETE FROM import_mappings WHERE user_id = :uid"), {"uid": id})
    for table in db.metadata.sorted_tables:
        if table.name in ("users", "notifications", "import_mappings"):
            continue
        for col in table.columns:
            if not any(fk.column.table.name == "users" for fk in col.foreign_keys):
                continue
            snapshot = f"{col.name}_name"
            if snapshot in table.columns:
                db.session.execute(
                    text(f'UPDATE "{table.name}" SET "{snapshot}" = :label '
                         f'WHERE "{col.name}" = :uid AND ("{snapshot}" IS NULL OR "{snapshot}" = \'\')'),
                    {"uid": id, "label": label},
                )
            db.session.execute(
                text(f'UPDATE "{table.name}" SET "{col.name}" = NULL WHERE "{col.name}" = :uid'), {"uid": id}
            )

    # BUG-106: user deletion is an auditable action
    log_activity_and_notify(
        action="DELETE_USER",
        record_id=str(id),
        user=it_admin,
        request=request,
        entity="User",
        entity_id=str(id),
        details=f"Deleted user account {label} (role {user.role})",
        metadata_json=json.dumps({"email": user.email, "role": user.role, "location": user.location}),
    )

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"})


@auth_bp.route("/users/<int:id>/reset-password", methods=["POST"])
@it_access_required
def admin_reset_password(id):
    """
    IT Admin resets a user's password directly (global authority).
    """
    db.session.expire_all()
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    current_admin_id = session.get("user_id")
    admin_user = db.session.get(User, current_admin_id) if current_admin_id else None

    # Separation of Duties: Client IT staff (it, it_admin) CANNOT reset passwords for Admin or Superuser accounts.
    # Only it_manager (vendor platform operator) or an Admin can reset Admin/Superuser passwords.
    if admin_user and (admin_user.role in CLIENT_IT_ROLES or admin_user.role == "it_admin"):
        if user.role in CLIENT_IT_PROTECTED_ROLES:
            return jsonify({
                "error": "Forbidden: Client IT staff cannot reset passwords for Compliance Admin or Superuser accounts"
            }), 403

    # Audit 2026-10-01 (A-01): a reset hands over the account, so only a strictly higher role may
    # reset it (the IT role could take over IT admin accounts). Own password: /change-password.
    if not admin_user or ROLE_RANK.get(user.role, 0) >= ROLE_RANK.get(admin_user.role, 0):
        return jsonify({"error": "You can only reset the password of an account with a lower role than your own"}), 403

    data = request.get_json(silent=True) or {}
    new_password = str(data.get("newPassword") or "").strip()

    if not new_password:
        return jsonify({"error": "New password is required"}), 400

    valid, err_msg = validate_password_complexity(new_password)
    if not valid:
        return jsonify({"error": err_msg}), 400

    user.set_password(new_password)
    user.session_version = int(user.session_version or 0) + 1  # BUG-114
    user.password_updated_at = datetime.datetime.now(datetime.timezone.utc)

    # Create notification for the user whose password was reset
    Notification.create(
        title="Your Password Has Been Reset",
        message=f"Your account password was reset by IT Administrator ({admin_user.fullName if admin_user else 'IT Admin'}) on {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}.",
        type="security",
        user_id=user.id,
    )

    try:
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(user.id),
            user=admin_user or user,
            request=request,
            entity="User",
            details=f"Password reset for {user.email} by IT Admin {admin_user.email if admin_user else 'system'}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error logging admin password reset: {e}")

    return jsonify({"message": f"Password for {user.fullName} ({user.email}) has been successfully reset."}), 200


# --- IT Session Governance & Operational Security ---

def _limit_count(limit):
    """The count of a rate-limit string ("10 per 15 minutes", "10/15minutes")."""
    import re

    m = re.match(r"\s*(\d+)", str(limit or ""))
    return int(m.group(1)) if m else None


@auth_bp.route("/sessions/policy", methods=["GET"])
@it_access_required
def get_session_policy():
    """Retrieve operational session governance policies and statistics."""
    from models import SystemSetting
    import json
    row = db.session.get(SystemSetting, "session_timeout_minutes")
    timeout = 30
    if row and row.value:
        try:
            val = json.loads(row.value) if isinstance(row.value, str) and (row.value.startswith('"') or row.value.isdigit()) else row.value
            timeout = int(val)
        except Exception:
            timeout = 30

    from services.login_guard import get_login_account_limit

    active_count = User.query.filter_by(status="active").count()
    total_count = User.query.count()

    return jsonify({
        "idle_timeout_minutes": timeout,
        # the per-account lockout really applied (LOGIN_ACCOUNT_LIMIT, "10 per 15 minutes"); it said 5
        "max_failed_logins": _limit_count(get_login_account_limit()),
        "nist_password_policy": "NIST SP 800-63B Enforced (min 10 chars, uppercase, lowercase, digits, symbols)",
        "session_invalidation": "Cryptographic Session Versioning (sv)",
        "total_users": total_count,
        "active_users": active_count,
    })


@auth_bp.route("/sessions/policy", methods=["PUT"])
@it_admin_required
def update_session_policy():
    """Update idle session timeout configuration."""
    from models import SystemSetting
    import json
    data = request.get_json(silent=True) or {}
    timeout = data.get("idle_timeout_minutes")
    if timeout is not None:
        try:
            timeout = int(timeout)
            if timeout not in [15, 30, 60, 120, 240, 480]:
                return jsonify({"error": "Invalid session timeout duration"}), 400
            row = db.session.get(SystemSetting, "session_timeout_minutes")
            if not row:
                row = SystemSetting(key="session_timeout_minutes", value=json.dumps(timeout))
                db.session.add(row)
            else:
                row.value = json.dumps(timeout)
            db.session.commit()
            forget_cached_timeout()
        except Exception as e:
            db.session.rollback()
            return internal_error(e, "Failed to update session policy")

    return jsonify({"success": True, "idle_timeout_minutes": timeout})


@auth_bp.route("/sessions/revoke-all", methods=["POST"])
@it_admin_required
def revoke_all_sessions():
    """Invalidate all active sessions across the platform by bumping session_version."""
    current_admin_id = session.get("user_id")
    current_admin = db.session.get(User, current_admin_id) if current_admin_id else None

    if current_admin and current_admin.role == "it_admin":
        users = User.query.filter(User.role.notin_(VENDOR_PROTECTED_ROLES)).all()
    else:
        users = User.query.all()

    revoked_count = 0
    for u in users:
        u.session_version = int(u.session_version or 0) + 1
        revoked_count += 1

    if current_admin:
        session["sv"] = int(current_admin.session_version)

    try:
        log_activity_and_notify(
            action="UPDATE",
            record_id="global-session-revoke",
            user=current_admin,
            request=request,
            entity="SessionGovernance",
            details=f"Global session invalidation executed by {current_admin.email if current_admin else 'IT'}. Revoked {revoked_count} accounts.",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to revoke sessions"}), 500

    return jsonify({"success": True, "revoked_count": revoked_count})


@auth_bp.route("/users/<int:id>/revoke-sessions", methods=["POST"])
@it_admin_required
def revoke_user_sessions(id):
    """Revoke all active sessions for a specific user."""
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    current_admin_id = session.get("user_id")
    current_admin = db.session.get(User, current_admin_id) if current_admin_id else None

    if current_admin and current_admin.role == "it_admin" and user.role in VENDOR_PROTECTED_ROLES:
        return jsonify({"error": "Forbidden: IT Administrator cannot revoke sessions for platform operator accounts"}), 403

    user.session_version = int(user.session_version or 0) + 1
    try:
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(user.id),
            user=current_admin or user,
            request=request,
            entity="User",
            details=f"Active sessions revoked for {user.email} by IT Admin {current_admin.email if current_admin else 'system'}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to revoke session"}), 500

    return jsonify({"success": True, "message": f"All active sessions for {user.email} have been revoked."})

