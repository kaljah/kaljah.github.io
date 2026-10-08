"""User management routes (IT administration).

Split out of routes/auth.py unchanged (hardening plan, task 5.3). The routes are registered on the
same ``auth_bp`` blueprint, and routes.auth re-exports every name, so imports and URLs are the same.
"""
import datetime
import json
from extensions import db
from flask import current_app, jsonify, request, session
from models import Notification, User
from utils import log_activity_and_notify
from . import auth_bp
from routes.auth import it_access_required, it_admin_required, register, validate_password_complexity


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
    result = []
    for u in users:
        result.append(
            {
                "id": u.id,
                "fullName": u.fullName,
                "email": u.email,
                "orgName": u.orgName,
                "role": u.role,
                "location": u.location,
                "department": u.department,
                "jobTitle": u.jobTitle,
                "status": u.status,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
            }
        )
    return jsonify(result)


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

    data = request.get_json()

    ROLE_RANK = {"user": 0, "it": 1, "superuser": 2, "admin": 3, "it_admin": 4, "it_manager": 4}
    VALID_ROLES = set(ROLE_RANK.keys())
    requester_rank = ROLE_RANK.get(it_admin.role if it_admin else "user", 0)

    if "role" in data:
        new_role = str(data["role"]).strip().lower()
        if new_role not in VALID_ROLES:
            return jsonify({"error": f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}"}), 400
        # Separation of Duties: IT Admin cannot assign business compliance Admin or Superuser role
        if new_role in ["admin", "superuser"] and it_admin.role not in ["admin", "it_manager"]:
            return jsonify({"error": "Forbidden: IT Administrators cannot assign business compliance roles (admin, superuser)"}), 403
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
            existing = User.query.filter(User.email == new_email, User.id != user.id).first()
            if existing:
                return jsonify({"error": "Email is already in use by another account"}), 400
            user.email = new_email

    if "department" in data:
        user.department = str(data["department"]).strip() if data["department"] else ""

    if "jobTitle" in data:
        user.jobTitle = str(data["jobTitle"]).strip() if data["jobTitle"] else ""

    if "location" in data:
        user.location = data["location"]
    if "status" in data:
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
    return jsonify(
        {
            "message": "User updated successfully",
            "user": {
                "id": user.id,
                "fullName": user.fullName,
                "email": user.email,
                "orgName": user.orgName,
                "role": user.role,
                "location": user.location,
                "department": user.department,
                "jobTitle": user.jobTitle,
                "status": user.status,
            },
        }
    )


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

    # BUG-010 / BUG-069: derive every reference to users.id from the schema instead of a
    # hand-maintained list, and keep the maker-checker identity on the records.
    from sqlalchemy import text
    from utils import user_label

    label = user_label(user)
    db.session.execute(text("DELETE FROM notifications WHERE user_id = :uid"), {"uid": id})
    for table in db.metadata.sorted_tables:
        if table.name in ("users", "notifications"):
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
    if admin_user and admin_user.role in ["it", "it_admin"]:
        if user.role in ["admin", "superuser", "it_manager"]:
            return jsonify({
                "error": "Forbidden: Client IT staff cannot reset passwords for Compliance Admin or Superuser accounts"
            }), 403

    data = request.get_json(silent=True) or {}
    new_password = data.get("newPassword", "").strip()

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
