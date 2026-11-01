import os

# 1. Patch login_guard.py
login_guard_path = 'new/server/services/login_guard.py'
with open(login_guard_path, 'r', encoding='utf-8') as f:
    lg_content = f.read()

old_failed_login = '''def record_failed_sign_in(email, user):
    """FAILED_LOGIN entry in the audit log (the Audit Trail counts it as a security alert)."""
    from extensions import db
    from utils import log_activity_and_notify

    try:
        log_activity_and_notify(action="FAILED_LOGIN", record_id=str(user.id) if user else "", user=None,
                                request=request, entity="User", details=f"Failed sign-in for {email[:120]}")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Audit Log Error on failed login: {e}")'''

new_failed_login = '''def record_failed_sign_in(email, user):
    """FAILED_LOGIN entry in the audit log (the Audit Trail counts it as a security alert)."""
    from extensions import db
    from utils import log_activity_and_notify

    try:
        actor_email = (user.email if user and user.email else email) or "Unknown User"
        log_activity_and_notify(
            action="FAILED_LOGIN",
            record_id=str(user.id) if user else "",
            user=actor_email,
            request=request,
            entity="User",
            details=f"Failed sign-in for {email[:120]}",
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Audit Log Error on failed login: {e}")'''

old_complexity_doc = 'Validates password against NIST SP 800-63B / corporate complexity rules:'
new_complexity_doc = 'Validates password against enterprise complexity policy:'

assert old_failed_login in lg_content, "old_failed_login not found in login_guard.py"
lg_content = lg_content.replace(old_failed_login, new_failed_login).replace(old_complexity_doc, new_complexity_doc)

with open(login_guard_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(lg_content)
print("Patched login_guard.py successfully")


# 2. Patch utils.py: client IP from X-Forwarded-For behind dev proxy & string user in log_activity_and_notify
utils_path = 'new/server/utils.py'
with open(utils_path, 'r', encoding='utf-8') as f:
    utils_content = f.read()

# Add get_client_ip function if not present
if "def get_client_ip(" not in utils_content:
    ip_helper = '''
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
'''
    # insert before log_activity_and_notify
    target_pos = utils_content.find('def log_activity_and_notify(')
    assert target_pos != -1, "log_activity_and_notify not found in utils.py"
    utils_content = utils_content[:target_pos] + ip_helper + '\n' + utils_content[target_pos:]

old_ip_and_user = '''    ip_address = request.remote_addr if request else None
    user_name = user.fullName if user else "System"
    user_id = user.id if user else None'''

new_ip_and_user = '''    ip_address = get_client_ip(request) if request else None
    if isinstance(user, str):
        user_name = user
        user_id = None
    elif user:
        user_name = getattr(user, "fullName", None) or getattr(user, "email", None) or str(user)
        user_id = getattr(user, "id", None)
    else:
        user_name = "System"
        user_id = None'''

assert old_ip_and_user in utils_content, "old_ip_and_user not found in utils.py"
utils_content = utils_content.replace(old_ip_and_user, new_ip_and_user)

with open(utils_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(utils_content)
print("Patched utils.py successfully")


# 3. Patch app.py: proxy hops in dev, and 429 lockout audit logging
app_path = 'new/server/app.py'
with open(app_path, 'r', encoding='utf-8') as f:
    app_content = f.read()

old_proxy_check = '''if not _proxy_hops and (os.environ.get("USE_PROXY_FIX", "").lower() == "true"
                        or os.environ.get("BEHIND_PROXY", "").lower() == "true"):
    _proxy_hops = 1'''

new_proxy_check = '''if not _proxy_hops and (os.environ.get("USE_PROXY_FIX", "").lower() == "true"
                        or os.environ.get("BEHIND_PROXY", "").lower() == "true"
                        or os.environ.get("FLASK_ENV") == "development"
                        or not app.config.get("IS_PRODUCTION", False)):
    _proxy_hops = 1'''

assert old_proxy_check in app_content, "old_proxy_check not found in app.py"
app_content = app_content.replace(old_proxy_check, new_proxy_check)

# Add 429 error handler with audit logging on login rate limit
if "handle_rate_limit_lockout" not in app_content:
    lockout_handler = '''
@app.errorhandler(429)
def handle_rate_limit_lockout(e):
    from flask import request, jsonify
    if request.path.endswith("/login"):
        try:
            data = request.get_json(silent=True) or {}
            email = str(data.get("email", "")).strip()[:120]
            from utils import log_activity_and_notify
            log_activity_and_notify(
                action="ACCOUNT_LOCKED",
                record_id="",
                user=email or "Unknown User",
                request=request,
                entity="User",
                details=f"Account locked / rate limit exceeded after repeated failed sign-in attempts: {email or 'unknown'}",
            )
            db.session.commit()
        except Exception as audit_err:
            db.session.rollback()
            app.logger.error(f"Audit Log Error on lockout: {audit_err}")
    desc = getattr(e, "description", None) or "Too many requests. Please try again later."
    return jsonify({"error": desc}), 429
'''
    pos_err = app_content.find('@app.errorhandler(413)')
    assert pos_err != -1, "413 error handler not found in app.py"
    app_content = app_content[:pos_err] + lockout_handler + '\n' + app_content[pos_err:]

with open(app_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(app_content)
print("Patched app.py successfully")


# 4. Patch routes/auth_users.py:
# - return is_test in _user_json
# - update nist_password_policy string to Enterprise Complexity Standard
# - exclude current admin from revoke-all-sessions session_version bump
auth_users_path = 'new/server/routes/auth_users.py'
with open(auth_users_path, 'r', encoding='utf-8') as f:
    au_content = f.read()

old_user_json = '''def _user_json(u):
    return {k: getattr(u, k) for k in ("id", "fullName", "email", "orgName", "role", "location", "department",
                                       "jobTitle", "status")}'''

new_user_json = '''def _user_json(u):
    data = {k: getattr(u, k) for k in ("id", "fullName", "email", "orgName", "role", "location", "department",
                                       "jobTitle", "status")}
    data["is_test"] = bool(getattr(u, "is_test", False))
    return data'''

assert old_user_json in au_content, "old_user_json not found in auth_users.py"
au_content = au_content.replace(old_user_json, new_user_json)

old_nist_str = '"nist_password_policy": "NIST SP 800-63B Enforced (min 10 chars, uppercase, lowercase, digits, symbols)",'
new_nist_str = '''"nist_password_policy": "Enterprise Complexity Standard (min 10 chars, uppercase, lowercase, digits, symbols)",
        "password_policy": "Enterprise Complexity Standard (min 10 chars, uppercase, lowercase, digits, symbols)",'''

assert old_nist_str in au_content, "old_nist_str not found in auth_users.py"
au_content = au_content.replace(old_nist_str, new_nist_str)

old_revoke_all = '''    revoked_count = 0
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
        )'''

new_revoke_all = '''    revoked_count = 0
    for u in users:
        # Exclude the current admin's session from revocation
        if current_admin and u.id == current_admin.id:
            continue
        u.session_version = int(u.session_version or 0) + 1
        revoked_count += 1

    if current_admin:
        session["sv"] = int(current_admin.session_version or 0)

    try:
        log_activity_and_notify(
            action="REVOKE_ALL_SESSIONS",
            record_id="global-session-revoke",
            user=current_admin,
            request=request,
            entity="SessionGovernance",
            details=f"Global session invalidation executed by {current_admin.email if current_admin else 'IT'}. Revoked {revoked_count} accounts (current admin session preserved).",
        )'''

assert old_revoke_all in au_content, "old_revoke_all not found in auth_users.py"
au_content = au_content.replace(old_revoke_all, new_revoke_all)

with open(auth_users_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(au_content)
print("Patched auth_users.py successfully")


# 5. Patch routes/audit.py:
# - add otherEvents to stats
# - include ACCOUNT_LOCKED in securityAlerts
audit_path = 'new/server/routes/audit.py'
with open(audit_path, 'r', encoding='utf-8') as f:
    audit_content = f.read()

old_audit_stats = '''        total_events = base.count()
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
    )'''

new_audit_stats = '''        total_events = base.count()
        total_logins = base.filter(ActivityLog.action == "LOGIN").count()
        data_mutations = base.filter(ActivityLog.action.in_(["CREATE", "UPDATE", "DELETE"])).count()
        security_alerts = base.filter(ActivityLog.action.in_(["SECURITY", "FAILED_LOGIN", "SUSPICIOUS", "ACCOUNT_LOCKED", "REVOKE_ALL_SESSIONS"])).count()
        other_events = max(0, total_events - (total_logins + data_mutations + security_alerts))
        unique_users = base.with_entities(func.count(distinct(ActivityLog.user_name))).scalar() or 0

    return jsonify(
        {
            "totalEvents": total_events,
            "totalLogins": total_logins,
            "dataMutations": data_mutations,
            "securityAlerts": security_alerts,
            "otherEvents": other_events,
            "uniqueUsers": unique_users,
        }
    )'''

assert old_audit_stats in audit_content, "old_audit_stats not found in audit.py"
audit_content = audit_content.replace(old_audit_stats, new_audit_stats)

with open(audit_path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(audit_content)
print("Patched audit.py successfully")
