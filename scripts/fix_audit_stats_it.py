with open('new/server/routes/audit.py', 'r', encoding='utf-8') as f:
    c = f.read()

target = '''        unique_users = (
            db.session.query(func.count(distinct(ActivityLog.user_name)))
            .filter(ActivityLog.action.in_(sec_actions))
            .scalar()
            or 0
        )
    else:'''

replacement = '''        unique_users = (
            db.session.query(func.count(distinct(ActivityLog.user_name)))
            .filter(ActivityLog.action.in_(sec_actions))
            .scalar()
            or 0
        )
        other_events = max(0, total_events - (total_logins + data_mutations + security_alerts))
    else:'''

assert target in c, "target not found"
c = c.replace(target, replacement)
with open('new/server/routes/audit.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(c)
print("Updated audit.py other_events for IT role")
