with open('new/server/routes/audit.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_sec_actions = 'SECURITY_ACTIONS = ["LOGIN", "LOGOUT", "REGISTER", "SECURITY", "UPDATE_PASSWORD", "PASSWORD_RESET"]'
new_sec_actions = 'SECURITY_ACTIONS = ["LOGIN", "LOGOUT", "REGISTER", "SECURITY", "UPDATE_PASSWORD", "PASSWORD_RESET", "FAILED_LOGIN", "SUSPICIOUS", "ACCOUNT_LOCKED", "REVOKE_ALL_SESSIONS"]'

assert old_sec_actions in c, "old_sec_actions not found"
c = c.replace(old_sec_actions, new_sec_actions)

old_stats = '''@audit_bp.route("/stats", methods=["GET"])
@audit_bp.route("/stats/", methods=["GET"])
@audit_access_required
def get_audit_stats():
    user = get_current_user()
    if user and is_it_role(user):
        sec_actions = ["LOGIN", "LOGOUT", "REGISTER", "SECURITY", "UPDATE_PASSWORD", "PASSWORD_RESET"]
        total_events = ActivityLog.query.filter(ActivityLog.action.in_(sec_actions)).count()
        total_logins = ActivityLog.query.filter(ActivityLog.action == "LOGIN").count()
        data_mutations = 0
        security_alerts = ActivityLog.query.filter(
            ActivityLog.action.in_(["SECURITY", "FAILED_LOGIN", "SUSPICIOUS"])
        ).count()
        unique_users = (
            db.session.query(func.count(distinct(ActivityLog.user_name)))
            .filter(ActivityLog.action.in_(sec_actions))
            .scalar()
            or 0
        )
        other_events = max(0, total_events - (total_logins + data_mutations + security_alerts))
    else:
        base = _scoped_base(user)
        total_events = base.count()
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

new_stats = '''@audit_bp.route("/stats", methods=["GET"])
@audit_bp.route("/stats/", methods=["GET"])
@audit_access_required
def get_audit_stats():
    user = get_current_user()
    base = _scoped_base(user)
    total_events = base.count()
    total_logins = base.filter(ActivityLog.action == "LOGIN").count()
    if user and is_it_role(user):
        data_mutations = base.filter(ActivityLog.entity == "User", ActivityLog.action.in_(["UPDATE", "DELETE_USER"])).count()
    else:
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

assert old_stats in c, "old_stats not found"
c = c.replace(old_stats, new_stats)

with open('new/server/routes/audit.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)
print("Updated audit.py stats and security actions")
