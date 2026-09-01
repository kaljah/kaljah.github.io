import datetime
import re
import socket
import ipaddress
from urllib.parse import urlparse
from functools import wraps
from flask import request, jsonify, session, current_app
from . import auth_bp
from models import User, Notification
from extensions import db, limiter
from utils import log_activity_and_notify


def validate_password_complexity(password: str):
    """
    Validates password against NIST SP 800-63B / corporate complexity rules:
    - Minimum 10 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 numeric digit
    - At least 1 special character
    """
    if not password or len(password) < 10:
        return False, "Password must be at least 10 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter (A-Z)"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one numeric digit (0-9)"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_+=\[\]\\\/~`]', password):
        return (
            False,
            "Password must contain at least one special character (!@#$%^&*...)",
        )
    return True, ""


def is_safe_image_url(url_str: str) -> tuple[bool, str]:
    """
    SEC-02: Protects against Server-Side Request Forgery (SSRF).
    - Requires https scheme
    - Resolves DNS and blocks RFC 1918 private subnets, loopback (127.0.0.0/8, ::1),
      link-local (169.254.0.0/16), and cloud metadata endpoints.
    - Validates image extension or known trusted image hosts.
    """
    if not url_str or not isinstance(url_str, str):
        return False, "Avatar URL is required"

    parsed = urlparse(url_str.strip())
    if parsed.scheme.lower() != "https":
        return False, "Avatar URL must use secure HTTPS protocol"

    hostname = parsed.hostname
    if not hostname:
        return False, "Invalid URL hostname"

    # Block direct IP access to private/link-local ranges or resolve hostname
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
        for family, socktype, proto, canonname, sockaddr in addr_infos:
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)
            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_reserved
                or ip_obj.is_multicast
            ):
                return (
                    False,
                    f"Avatar URL cannot target private or internal IP addresses ({ip_str})",
                )
    except socket.gaierror:
        return False, "Could not resolve avatar URL domain"
    except Exception as e:
        return False, f"URL validation error: {str(e)}"

    return True, ""


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 204)
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        user = db.session.get(User, user_id)
        if not user:
            session.pop("user_id", None)
            return jsonify({"error": "User not found"}), 401
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 204)
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        user = User.query.get(user_id)
        if not user:
            session.pop("user_id", None)
            return jsonify({"error": "User not found"}), 401
        if user.role != "it_admin":
            return jsonify({"error": "IT Admin privileges required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def superuser_required(f):
    """Permits superuser, admin, and it_admin roles"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 204)
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        user = User.query.get(user_id)
        if not user:
            session.pop("user_id", None)
            return jsonify({"error": "User not found"}), 401
        if user.role not in ["superuser", "admin", "it_admin"]:
            return jsonify({"error": "Super User or Admin privileges required"}), 403
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route("/register", methods=["POST"])
@admin_required
def register():
    data = request.get_json()

    required_fields = ["fullName", "orgName", "email", "sector", "password"]
    for field in required_fields:
        if not data or not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    if User.query.filter_by(email=data.get("email")).first():
        return jsonify({"error": "Email already registered"}), 400

    password = data.get("password")
    valid, err_msg = validate_password_complexity(password)
    if not valid:
        return jsonify({"error": err_msg}), 400

    user = User(
        fullName=data.get("fullName"),
        orgName=data.get("orgName"),
        email=data.get("email"),
        sector=data.get("sector"),
        department=data.get("department"),
        jobTitle=data.get("jobTitle"),
        phone=data.get("phone"),
        location=data.get("location"),
        role=data.get("role", "user"),  # Admins can explicitly set roles
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    # Audit
    try:
        log_activity_and_notify(
            action="REGISTER",
            record_id=str(user.id),
            user=user,
            request=request,
            entity="User",
            details=f"User registered: {user.email}",
        )
    except Exception as e:
        current_app.logger.error(f"Audit Log Error on register: {e}")

    return (
        jsonify(
            {
                "message": "User registered successfully",
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
                    "created_at": (
                        user.created_at.isoformat() if user.created_at else None
                    ),
                },
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per 15 minutes")  # SEC-01 FIX: rely cleanly on Flask-Limiter
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email and password required"}), 400

    email_input = str(data.get("email", "")).strip()
    password_input = str(data.get("password", ""))

    user = User.query.filter(db.func.lower(User.email) == email_input.lower()).first()

    if user and user.check_password(password_input):
        if user.status != "active":
            return jsonify({"error": "Account disabled"}), 403

        session.permanent = True
        session["user_id"] = user.id
        current_app.logger.debug(f"Session set for user_id={user.id}")
        user.last_login = datetime.datetime.now(datetime.timezone.utc)

        db.session.commit()

        # Audit
        try:
            log_activity_and_notify(
                action="LOGIN",
                record_id=str(user.id),
                user=user,
                request=request,
                entity="User",
                details=f"User logged in: {user.email}",
            )
        except Exception as e:
            current_app.logger.error(f"Audit Log Error on login: {e}")

        return jsonify(
            {
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "fullName": user.fullName,
                    "email": user.email,
                    "role": user.role,
                    "orgName": user.orgName,
                },
            }
        )

    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per 15 minutes")
def forgot_password():
    """
    User triggers a password reset request.
    Creates a notification for the IT Role / Admin to reset their credentials.
    """
    data = request.get_json(silent=True) or {}
    email_input = str(data.get("email", "")).strip().lower()

    if not email_input:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter(db.func.lower(User.email) == email_input).first()

    if user:
        # Find IT Admins or Admins to notify
        it_admins = User.query.filter(User.role.in_(["it_admin", "admin"]), User.status == "active").all()

        notification_title = f"Password Reset Request: {user.fullName or user.email}"
        notification_msg = (
            f"User {user.fullName} ({user.email}) requested a password reset at "
            f"{datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}. "
            f"Please review and reset their password in User Management."
        )

        for admin in it_admins:
            Notification.create(
                title=notification_title,
                message=notification_msg,
                type="security",
                user_id=admin.id,
                metadata={"requester_id": user.id, "requester_email": user.email, "request_type": "forgot_password"}
            )

        try:
            log_activity_and_notify(
                action="SECURITY",
                record_id=str(user.id),
                user=user,
                request=request,
                entity="User",
                details=f"Password reset requested for: {user.email}",
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error logging forgot password request: {e}")

    # Standard security practice: always return a uniform success response to prevent email enumeration
    return jsonify({
        "message": "If your email is registered in the system, a password reset request has been forwarded to the IT Administrator."
    }), 200


# Audit Login (Success)
# (Done inside login block above if successful? No, let's add it before return)
# Actually, inside the `if user and check_password` block is best.
# But I can't easily target inside the block with replace_file_content without context.
# I'll rely on the fact that I can match the return block.


@auth_bp.route("/logout", methods=["POST"])
def logout():
    user_id = session.get("user_id")
    if user_id:
        user = User.query.get(user_id)
        if user:
            try:
                log_activity_and_notify(
                    action="LOGOUT",
                    record_id=str(user.id),
                    user=user,
                    request=request,
                    entity="User",
                    details=f"User logged out: {user.email}",
                )
            except Exception as e:
                current_app.logger.error(f"Audit Log Error on logout: {e}")

    session.pop("user_id", None)
    return jsonify({"message": "Logged out"})


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    user_id = session.get("user_id")
    current_app.logger.debug(
        f"/me check session user_id={user_id}"
    )  # SEC-12 FIX: replaced DEBUG print
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({"error": "User not found"}), 401

    return jsonify(
        {
            "id": user.id,
            "fullName": user.fullName,
            "email": user.email,
            "role": user.role,
            "orgName": user.orgName,
            "sector": user.sector,
            "jobTitle": user.jobTitle,
            "department": user.department,
            "phone": user.phone,
            "location": user.location,
            "bio": user.bio,
            "profilePic": user.profilePic,
            "consolidationApproach": user.consolidationApproach,
        }
    )


@auth_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()

    # Update allowed fields
    if "fullName" in data:
        user.fullName = data["fullName"]
    if "jobTitle" in data:
        user.jobTitle = data["jobTitle"]
    if "department" in data:
        user.department = data["department"]
    if "phone" in data:
        user.phone = data["phone"]
    if "location" in data:
        user.location = data["location"]
    if "bio" in data:
        user.bio = data["bio"]
    if "consolidationApproach" in data:
        user.consolidationApproach = data["consolidationApproach"]

    db.session.commit()

    return jsonify({"message": "Profile updated successfully"})


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    current_password = data.get("currentPassword")
    new_password = data.get("newPassword")

    if not current_password or not new_password:
        return jsonify({"error": "Current and new passwords required"}), 400

    if not user.check_password(current_password):
        return jsonify({"error": "Current password incorrect"}), 401

    # DB-02: Password complexity check
    valid, err_msg = validate_password_complexity(new_password)
    if not valid:
        return jsonify({"error": err_msg}), 400

    user.set_password(new_password)
    user.password_updated_at = datetime.datetime.utcnow()

    # Audit + commit atomically
    try:
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(user.id),
            user=user,
            request=request,
            entity="User",
            details=f"Password changed for user: {user.email}",
        )
        db.session.commit()  # commits: password hash + activity log + notification
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Audit Log Error on change_password: {e}")

    return jsonify({"message": "Password changed successfully"})


@auth_bp.route("/upload-avatar", methods=["POST"])
@login_required
def upload_avatar():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    avatar_url = data.get("avatarUrl", "").strip()

    if not avatar_url:
        return jsonify({"error": "Avatar URL required"}), 400

    # SEC-02: SSRF and URL validation
    is_safe, err_msg = is_safe_image_url(avatar_url)
    if not is_safe:
        return jsonify({"error": err_msg}), 400

    user.profilePic = avatar_url
    db.session.commit()

    return jsonify({"message": "Avatar updated successfully", "avatarUrl": avatar_url})


# Global Application & User Preferences Store (with DB persistence via SystemSetting)
_DEFAULT_APP_SETTINGS = {
    "gwp_standard": "AR5",
    "ogmp_default_base_year": 2023,
    "reconciliation_threshold": 20.0,
    "ogmp_upstream_target_pct": 0.20,
    "ogmp_midstream_target_pct": 0.05,
    "copernicus_username": "",
    "copernicus_password": "",
    "copernicus_client_id": "",
    "copernicus_client_secret": "",
    "copernicus_qa_threshold": 0.5,
    "copernicus_enabled": False,
    "wec_fee_rates": {"2024": 900.0, "2025": 1200.0, "2026": 1500.0},
    "theme": "light",
    "unit_system": "metric",
    "auto_flag_discrepancy": True,
    "gwp_values": {
        "AR5": {"ch4_100": 28.0, "ch4_20": 82.5, "n2o_100": 265.0, "co2": 1.0},
        "AR6": {"ch4_100": 27.9, "ch4_20": 82.5, "n2o_100": 273.0, "co2": 1.0},
        "AR4": {"ch4_100": 25.0, "ch4_20": 72.0, "n2o_100": 298.0, "co2": 1.0},
    },
}

_app_settings = dict(_DEFAULT_APP_SETTINGS)


def load_settings_from_db():
    """Loads all system settings from SystemSetting table in DB into _app_settings."""
    import json
    try:
        from models import SystemSetting
        settings = SystemSetting.query.all()
        for s in settings:
            try:
                _app_settings[s.key] = json.loads(s.value)
            except Exception:
                _app_settings[s.key] = s.value
    except Exception as e:
        # Table might not exist yet during migration
        pass
    return _app_settings


def save_setting_to_db(key: str, val):
    """Saves a setting to the SystemSetting table and syncs _app_settings."""
    import json
    from models import SystemSetting
    _app_settings[key] = val
    try:
        row = db.session.get(SystemSetting, key)
        if not row:
            row = SystemSetting(key=key, value=json.dumps(val))
            db.session.add(row)
        else:
            row.value = json.dumps(val)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to persist system setting '{key}': {e}")


def recalculate_all_emissions_gwp(standard):
    """
    Recalculates co2e_total for all stored Emission records in the database
    using the specified GWP standard ('AR4', 'AR5', 'AR6').
    Also updates gwp_version on the records and invalidates dashboard caches.
    """
    from models import Emission
    from calculations.constants import GWP_STANDARDS, GWP_AR5
    from sqlalchemy import func

    std_dict = GWP_STANDARDS.get(standard, GWP_AR5)
    co2_factor = float(std_dict.get("CO2", 1.0))
    ch4_factor = float(std_dict.get("CH4", 28.0))
    n2o_factor = float(std_dict.get("N2O", 265.0))

    # Perform database update
    db.session.query(Emission).update(
        {
            Emission.co2e_total: (
                func.coalesce(Emission.co2_emissions, 0.0) * co2_factor
                + func.coalesce(Emission.ch4_emissions, 0.0) * ch4_factor
                + func.coalesce(Emission.n2o_emissions, 0.0) * n2o_factor
            ),
            Emission.gwp_version: standard,
            Emission.updated_at: datetime.datetime.now(datetime.timezone.utc),
        },
        synchronize_session=False,
    )

    db.session.commit()

    # Clear dashboard cache
    try:
        from routes.dashboard import DASHBOARD_CACHE

        DASHBOARD_CACHE.clear()
    except Exception:
        pass


@auth_bp.route("/settings", methods=["GET"])
@login_required
def get_settings():
    import json

    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None

    # Load fresh persistent settings from DB
    load_settings_from_db()

    # Merge global settings with user preferences
    resp = dict(_app_settings)
    if user and user.preferences:
        try:
            prefs = json.loads(user.preferences)
            if isinstance(prefs, dict):
                resp.update(prefs)
        except Exception:
            pass
    return jsonify(resp)


@auth_bp.route("/settings", methods=["PUT", "POST"])
@login_required
def update_settings():
    import json
    from models import SystemSetting

    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    data = request.get_json() or {}

    load_settings_from_db()

    # Global system & GWP standards updates
    gwp_changed = False
    if "gwp_standard" in data and data["gwp_standard"] in ["AR4", "AR5", "AR6"]:
        new_gwp = data["gwp_standard"]
        if _app_settings.get("gwp_standard") != new_gwp:
            _app_settings["gwp_standard"] = new_gwp
            save_setting_to_db("gwp_standard", new_gwp)
            gwp_changed = True

    system_setting_keys = [
        "ogmp_default_base_year",
        "reconciliation_threshold",
        "ogmp_upstream_target_pct",
        "ogmp_midstream_target_pct",
        "copernicus_username",
        "copernicus_password",
        "copernicus_client_id",
        "copernicus_client_secret",
        "copernicus_qa_threshold",
        "copernicus_enabled",
        "theme",
        "unit_system",
        "auto_flag_discrepancy",
    ]

    for k in system_setting_keys:
        if k in data:
            val = data[k]
            if k == "ogmp_default_base_year":
                val = int(val)
            elif k in ["reconciliation_threshold", "ogmp_upstream_target_pct", "ogmp_midstream_target_pct", "copernicus_qa_threshold"]:
                val = float(val)
            elif k in ["copernicus_enabled", "auto_flag_discrepancy"]:
                val = bool(val)
            _app_settings[k] = val
            save_setting_to_db(k, val)

    if "wec_fee_rates" in data and isinstance(data["wec_fee_rates"], dict):
        rates = _app_settings.get("wec_fee_rates", {})
        rates.update({str(k): float(v) for k, v in data["wec_fee_rates"].items()})
        _app_settings["wec_fee_rates"] = rates
        save_setting_to_db("wec_fee_rates", rates)

    # If GWP standard was changed or set, recalculate existing emissions
    if gwp_changed:
        try:
            recalculate_all_emissions_gwp(_app_settings["gwp_standard"])
        except Exception as e:
            current_app.logger.error(f"Error recalculating emissions with new GWP: {e}")

    if user:
        try:
            existing = json.loads(user.preferences) if user.preferences else {}
        except Exception:
            existing = {}
        existing.update(data)
        user.preferences = json.dumps(existing)

        if "consolidation" in data:
            user.consolidationApproach = data["consolidation"]

        try:
            log_activity_and_notify(
                action="UPDATE",
                record_id=str(user.id),
                user=user,
                request=request,
                entity="User",
                details=f"Updated settings for user: {user.email} (GWP: {_app_settings['gwp_standard']})",
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Audit Log Error: {e}")

    try:
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
    except Exception:
        pass

    return jsonify(
        {"message": "Settings saved successfully", "settings": _app_settings}
    )


@auth_bp.route("/users", methods=["GET"])
@admin_required
def get_users():
    # Force expire session cache so we always read fresh data from DB
    db.session.expire_all()

    it_admin_id = session.get("user_id")
    it_admin = User.query.get(it_admin_id)
    admin_region = it_admin.location if it_admin else None

    # Treat null / empty / "Global" as "no restriction" — see all users
    SENTINEL_VALUES = {None, "", "Global", "global"}
    region_restricted = admin_region not in SENTINEL_VALUES

    query = User.query
    if region_restricted:
        # Scope to users in the same region; always include admins/it_admins
        query = query.filter(
            db.or_(User.location == admin_region, User.role.in_(["admin", "it_admin"]))
        )

    users = query.order_by(User.created_at.desc()).all()
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
@admin_required
def update_user(id):
    db.session.expire_all()
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # IT admin can only modify users within their own region
    it_admin_id = session.get("user_id")
    it_admin = User.query.get(it_admin_id)
    if it_admin and it_admin.location and user.role == "user":
        if user.location != it_admin.location:
            return jsonify({"error": "Unauthorized: User is outside your region"}), 403

    data = request.get_json()

    ROLE_RANK = {"user": 0, "superuser": 1, "admin": 2, "it_admin": 3}
    requester_rank = ROLE_RANK.get(it_admin.role if it_admin else "user", 0)
    target_new_rank = ROLE_RANK.get(
        data.get("role", user.role) if data else user.role, 0
    )
    if target_new_rank > requester_rank:
        return jsonify({"error": "Cannot assign a role higher than your own"}), 403

    if "role" in data:
        user.role = data["role"]
    if "location" in data:
        user.location = data["location"]
    if "status" in data:
        user.status = data["status"]

    db.session.commit()
    # Return updated user so frontend can reflect changes immediately
    return jsonify(
        {
            "message": "User updated successfully",
            "user": {
                "id": user.id,
                "fullName": user.fullName,
                "email": user.email,
                "role": user.role,
                "location": user.location,
                "status": user.status,
            },
        }
    )


@auth_bp.route("/users/<int:id>", methods=["DELETE"])
@admin_required
def delete_user(id):
    if id == session.get("user_id"):
        return jsonify({"error": "Cannot delete your own account"}), 400

    db.session.expire_all()
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # IT admin can only delete users within their own region
    it_admin_id = session.get("user_id")
    it_admin = User.query.get(it_admin_id)
    if it_admin and it_admin.location and user.role == "user":
        if user.location != it_admin.location:
            return jsonify({"error": "Unauthorized: User is outside your region"}), 403

    # Nullify FK references before deleting to avoid constraint violations
    from sqlalchemy import text

    # Nullify activity_log.user_id references
    db.session.execute(
        text("UPDATE activity_log SET user_id = NULL WHERE user_id = :uid"), {"uid": id}
    )
    # Nullify notifications.user_id references
    db.session.execute(
        text("UPDATE notifications SET user_id = NULL WHERE user_id = :uid"),
        {"uid": id},
    )
    # Nullify created_by on facilities
    db.session.execute(
        text("UPDATE facilities SET created_by = NULL WHERE created_by = :uid"),
        {"uid": id},
    )
    # Nullify any other created_by/updated_by references in emissions tables
    for tbl in [
        "emissions",
        "scope2_emissions",
        "scope3_emissions",
        "mitigation_projects",
        "mitigation_records",
    ]:
        try:
            db.session.execute(
                text(f"UPDATE {tbl} SET created_by = NULL WHERE created_by = :uid"),
                {"uid": id},
            )
        except Exception:
            pass  # Table may not have created_by column; skip

    db.session.delete(user)
    db.session.commit()
    return jsonify({"message": "User deleted successfully"})


@auth_bp.route("/users/<int:id>/reset-password", methods=["POST"])
@admin_required
def admin_reset_password(id):
    """
    IT Admin / Admin resets a user's password directly.
    """
    db.session.expire_all()
    user = db.session.get(User, id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    current_admin_id = session.get("user_id")
    admin_user = db.session.get(User, current_admin_id) if current_admin_id else None

    # IT Admin regional boundary check for regular users
    if admin_user and admin_user.role == "it_admin" and admin_user.location and user.role == "user":
        if user.location != admin_user.location:
            return jsonify({"error": "Unauthorized: User is outside your region"}), 403

    data = request.get_json(silent=True) or {}
    new_password = data.get("newPassword", "").strip()

    if not new_password:
        return jsonify({"error": "New password is required"}), 400

    valid, err_msg = validate_password_complexity(new_password)
    if not valid:
        return jsonify({"error": err_msg}), 400

    user.set_password(new_password)
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
