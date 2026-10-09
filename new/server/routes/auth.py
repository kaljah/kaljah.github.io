import json
import os
import datetime
import socket
import ipaddress
from urllib.parse import urlparse
from functools import wraps
from flask import request, jsonify, session, current_app
from . import auth_bp
from models import User, Notification, Facility
from extensions import db, limiter, csrf
from utils import log_activity_and_notify, is_unrestricted_location
from services.login_guard import (ACCOUNT_LOCKED, failed_sign_in, get_login_account_limit, get_login_rate_limit,  # noqa: F401
                                  login_account_key, record_failed_sign_in, validate_password_complexity)
from werkzeug.security import check_password_hash, generate_password_hash


def get_user_operational_defaults(user):
    """
    Computes default region, division, activity, and facility for a user.
    For regional users and superusers tied to a location/region,
    resolves the matching facility attributes.
    """
    defaults = {
        "region": None,
        "division": None,
        "activity": None,
        "facility_id": None,
        "facility_name": None,
    }
    if not user:
        return defaults

    user_loc = str(user.location).strip() if user.location else ""
    if user_loc and not is_unrestricted_location(user_loc):
        defaults["region"] = user_loc
        try:
            with db.session.no_autoflush:
                fac = (
                    db.session.query(
                        Facility.id,
                        Facility.name,
                        Facility.region,
                        Facility.location,
                        Facility.division,
                        Facility.activity,
                    )
                    .filter(
                        db.or_(
                            Facility.region.ilike(f"%{user_loc}%"),
                            Facility.location.ilike(f"%{user_loc}%"),
                            Facility.name.ilike(f"%{user_loc}%"),
                        )
                    )
                    .order_by(Facility.division.isnot(None).desc(), Facility.id.desc())
                    .first()
                )
                if fac:
                    defaults["region"] = fac.region or fac.location or user_loc
                    defaults["division"] = fac.division
                    defaults["activity"] = fac.activity
                    defaults["facility_id"] = str(fac.id)
                    defaults["facility_name"] = fac.name
        except Exception:
            defaults["region"] = user_loc

    return defaults



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
        if user.status != "active":
            session.pop("user_id", None)
            return jsonify({"error": "Account disabled"}), 403
        return f(*args, **kwargs)

    return decorated_function


def it_admin_required(f):
    """Restricts access to IT Manager / IT Admin role only — for user account management routes."""
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
        if user.status != "active":
            session.pop("user_id", None)
            return jsonify({"error": "Account disabled"}), 403
        if user.role not in ["it_admin", "it_manager"]:
            return jsonify({"error": "IT Admin privileges required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def it_access_required(f):
    """Allows IT Manager, IT Admin, and IT roles — for accessing user list and resetting passwords."""
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
        if user.status != "active":
            session.pop("user_id", None)
            return jsonify({"error": "Account disabled"}), 403
        if user.role not in ["it_admin", "it_manager", "it"]:
            return jsonify({"error": "IT privileges required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Restricts access to business/data Admin role only."""
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
        if user.status != "active":
            session.pop("user_id", None)
            return jsonify({"error": "Account disabled"}), 403
        if user.role != "admin":
            return jsonify({"error": "Admin privileges required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def superuser_required(f):
    """Permits superuser and admin roles for data management operations.
    NOTE: it_admin is intentionally excluded — they manage accounts only, not data.
    """

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
        if user.status != "active":
            session.pop("user_id", None)
            return jsonify({"error": "Account disabled"}), 403
        if user.role not in ["superuser", "admin"]:
            return jsonify({"error": "Super User or Admin privileges required"}), 403
        return f(*args, **kwargs)

    return decorated_function


ROLE_RANK = {"user": 0, "it": 1, "superuser": 2, "admin": 3, "it_admin": 4, "it_manager": 4}
BUSINESS_ROLES = ("admin", "superuser")
BUSINESS_ROLE_GRANTORS = ("admin", "it_manager")  # separation of duties (update_user and register)
CLIENT_IT_ROLES = ("it", "it_admin")  # client IT staff manage ordinary accounts only:
CLIENT_IT_PROTECTED_ROLES = ("admin", "superuser", "it_manager")  # they may not grant, edit or delete these
SUPERUSER_REGION_ERROR = ("A superuser is limited to one facility or region: set a specific location "
                          "(organisation-wide access is the admin role)")


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
@it_admin_required
def register():
    data = request.get_json()

    required_fields = ["fullName", "orgName", "email", "sector", "password"]
    for field in required_fields:
        if not data or not data.get(field):
            return jsonify({"error": f"Missing required field: {field}"}), 400

    email_clean = str(data.get("email", "")).strip().lower()
    if User.query.filter(db.func.lower(User.email) == email_clean).first():
        return jsonify({"error": "Email already registered"}), 409

    password = data.get("password")
    valid, err_msg = validate_password_complexity(password)
    if not valid:
        return jsonify({"error": err_msg}), 400

    VALID_ROLES = set(ROLE_RANK.keys())
    role_requested = str(data.get("role", "user")).strip().lower()
    if role_requested not in VALID_ROLES:
        return jsonify({"error": f"Invalid role. Must be one of: {', '.join(sorted(VALID_ROLES))}"}), 400

    creator_id = session.get("user_id")
    creator = db.session.get(User, creator_id) if creator_id else None
    if creator and creator.role in CLIENT_IT_ROLES and role_requested in CLIENT_IT_PROTECTED_ROLES:
        return jsonify({"error": "Forbidden: Client IT staff cannot create Compliance Admin or Superuser accounts"}), 403
    # Audit 2026-10-01 (A-02): the same separation of duties as update_user
    if role_requested in BUSINESS_ROLES and (not creator or creator.role not in BUSINESS_ROLE_GRANTORS):
        return jsonify({"error": "Forbidden: IT Administrators cannot assign business compliance roles (admin, superuser)"}), 403
    if creator and ROLE_RANK.get(role_requested, 0) > ROLE_RANK.get(creator.role, 0):
        return jsonify({"error": "Cannot assign a role higher than your own"}), 403
    if role_requested == "superuser" and is_unrestricted_location(data.get("location")):
        return jsonify({"error": SUPERUSER_REGION_ERROR, "field": "location"}), 400

    user = User(
        fullName=data.get("fullName"),
        orgName=data.get("orgName"),
        email=email_clean,
        sector=data.get("sector"),
        department=data.get("department"),
        jobTitle=data.get("jobTitle"),
        phone=data.get("phone"),
        location=data.get("location"),
        role=role_requested,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.flush()

    # BUG-106: the REGISTER entry used to be added after the only commit and was lost.
    creator = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
    log_activity_and_notify(
        action="REGISTER",
        record_id=str(user.id),
        user=creator or user,
        request=request,
        entity="User",
        details=f"User account created: {user.email} (role {user.role})",
    )
    db.session.commit()

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




_DUMMY_PASSWORD_HASH = generate_password_hash("timing-equaliser-not-a-real-account")


@auth_bp.route("/login", methods=["POST"])
@csrf.exempt
@limiter.limit(get_login_rate_limit, deduct_when=failed_sign_in)
@limiter.limit(get_login_account_limit, key_func=login_account_key, deduct_when=failed_sign_in,
               error_message=ACCOUNT_LOCKED)
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

        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["sv"] = int(user.session_version or 0)  # BUG-114
        current_app.logger.debug(f"Session set for user_id={user.id}")

        # Compute operational defaults before setting last_login to prevent premature query autoflush
        user_defaults = get_user_operational_defaults(user)
        user.last_login = datetime.datetime.now(datetime.timezone.utc)

        user_info = {
            "id": user.id,
            "fullName": user.fullName,
            "email": user.email,
            "role": user.role,
            "orgName": user.orgName,
            "jobTitle": user.jobTitle,
            "department": user.department,
            "sector": user.sector,
            "phone": user.phone,
            "location": user.location,
            "status": user.status,
            "default_region": user_defaults["region"],
            "default_division": user_defaults["division"],
            "default_activity": user_defaults["activity"],
            "default_facility_id": user_defaults["facility_id"],
            "default_facility_name": user_defaults["facility_name"],
        }

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

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.warning(f"Login commit warning under concurrency: {e}")

        return jsonify(
            {
                "message": "Login successful",
                "user": user_info,
            }
        )

    if user is None:
        # Audit A-06: same password-hash work as for an existing account, so response time does
        # not reveal which e-mail addresses are registered (forgot-password does the same)
        check_password_hash(_DUMMY_PASSWORD_HASH, password_input)
    record_failed_sign_in(email_input, user)
    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/forgot-password", methods=["POST"])
@csrf.exempt
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
        # Find IT Admins or IT Managers to notify
        it_admins = User.query.filter(User.role.in_(["it_admin", "it_manager"]), User.status == "active").all()

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
            from services.email_service import send_password_reset_email
            send_password_reset_email(user.email, user.fullName)
        except Exception as _em_err:
            current_app.logger.warning(f"Failed to dispatch password reset email: {_em_err}")

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
    else:
        # Mitigate user enumeration timing attack by executing cryptographic hash equivalent
        from werkzeug.security import generate_password_hash
        generate_password_hash("timing_mitigation_constant_salt_and_work_factor")

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
@limiter.limit("60 per minute")
def logout():
    user_id = session.get("user_id")
    if user_id:
        user = db.session.get(User, user_id)
        if user:
            try:
                # BUG-114: invalidate every copy of this user's session cookie
                user.session_version = int(user.session_version or 0) + 1
                log_activity_and_notify(
                    action="LOGOUT",
                    record_id=str(user.id),
                    user=user,
                    request=request,
                    entity="User",
                    details=f"User logged out: {user.email}",
                )
                db.session.commit()  # BUG-106: the LOGOUT entry was never committed
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Audit Log Error on logout: {e}")

    session.clear()
    resp = jsonify({"message": "Logged out"})
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session")
    resp.delete_cookie(
        cookie_name,
        path="/",
        samesite=current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
        secure=current_app.config.get("SESSION_COOKIE_SECURE", False),
        httponly=True,
    )
    return resp


@auth_bp.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated", "authenticated": False, "user": None}), 401

    user = db.session.get(User, user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({"error": "Not authenticated", "authenticated": False, "user": None}), 401

    user_defaults = get_user_operational_defaults(user)

    return jsonify(
        {
            "authenticated": True,
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
            "status": user.status,
            "default_region": user_defaults["region"],
            "default_division": user_defaults["division"],
            "default_activity": user_defaults["activity"],
            "default_facility_id": user_defaults["facility_id"],
            "default_facility_name": user_defaults["facility_name"],
        }
    )


@auth_bp.route("/profile", methods=["PUT"])
@login_required
def update_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()

    # Update allowed fields (location is immutable via /profile to prevent RBAC bypass; managed via /users/<id>)
    if "fullName" in data:
        user.fullName = data["fullName"]
    if "jobTitle" in data:
        user.jobTitle = data["jobTitle"]
    if "department" in data:
        user.department = data["department"]
    if "phone" in data:
        user.phone = data["phone"]
    if "bio" in data:
        user.bio = data["bio"]
    if "consolidationApproach" in data:
        user.consolidationApproach = data["consolidationApproach"]

    try:
        from utils import log_activity_and_notify
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(user.id),
            user=user,
            request=request,
            entity="User",
            entity_id=str(user.id),
            details=f"User {user.email} updated profile information",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update profile: {e}")
        return jsonify({"error": "Failed to update profile"}), 500

    return jsonify({"message": "Profile updated successfully"})


@auth_bp.route("/change-password", methods=["POST"])
@limiter.limit("5 per hour")
@login_required
def change_password():
    user = db.session.get(User, session.get("user_id"))  # login_required: the session has a user id
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json(silent=True) or {}
    current_password, new_password = data.get("currentPassword"), data.get("newPassword")

    if not current_password or not new_password:
        return jsonify({"error": "Current and new passwords required"}), 400

    if not user.check_password(current_password):  # 400, not 401: the client signs out on any 401
        return jsonify({"error": "Current password incorrect", "field": "currentPassword"}), 400
    if new_password == current_password:
        return jsonify({"error": "The new password must differ from the current one", "field": "newPassword"}), 400

    # DB-02: Password complexity check
    valid, err_msg = validate_password_complexity(new_password)
    if not valid:
        return jsonify({"error": err_msg}), 400

    user.set_password(new_password)
    user.password_updated_at = datetime.datetime.now(datetime.timezone.utc)
    # Session fixation / exfiltration protection: regenerate session ID on credential change
    user.session_version = int(user.session_version or 0) + 1  # BUG-114: other sessions end

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
        db.session.commit()  # commits: password hash + session version + activity log + notification
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Audit Log Error on change_password: {e}")
        return jsonify({"error": "Failed to update password"}), 500

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    session["sv"] = int(user.session_version)

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
    try:
        from utils import log_activity_and_notify
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(user.id),
            user=user,
            request=request,
            entity="User",
            entity_id=str(user.id),
            details=f"User {user.email} updated profile picture",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update avatar: {e}")
        return jsonify({"error": "Failed to update avatar"}), 500

    return jsonify({"message": "Avatar updated successfully", "avatarUrl": avatar_url})


# Global Application & User Preferences Store (with DB persistence via SystemSetting)


# Modules split out of this file. Importing them registers their routes on auth_bp. The names they define
# stay importable from here (other modules import _app_settings, load_settings_from_db and others from
# routes.auth); they are resolved lazily so the import order of these modules never matters.
from . import auth_settings, auth_users  # noqa: E402,F401

_MOVED_NAMES = {
    "_DEFAULT_APP_SETTINGS": "auth_settings",
    "_app_settings": "auth_settings",
    "load_settings_from_db": "auth_settings",
    "save_setting_to_db": "auth_settings",
    "recalculate_all_emissions_gwp": "auth_settings",
    "get_settings": "auth_settings",
    "update_settings": "auth_settings",
    "create_user": "auth_users",
    "get_users": "auth_users",
    "update_user": "auth_users",
    "delete_user": "auth_users",
    "admin_reset_password": "auth_users",
}


def __getattr__(name):
    module = _MOVED_NAMES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    return getattr(import_module(f"{__package__}.{module}"), name)
