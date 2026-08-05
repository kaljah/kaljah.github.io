from flask import Blueprint, jsonify, request, session
from models import ActivityLog, User
from extensions import db
from datetime import datetime
from sqlalchemy import distinct
from routes.auth import admin_required, login_required

audit_bp = Blueprint('audit', __name__)

@audit_bp.route('/', methods=['GET'])
@login_required
def get_audit_logs():
    # Optional filters
    user_filter = request.args.get('user')
    action_filter = request.args.get('action')
    entity_filter = request.args.get('entity')
    limit = int(request.args.get('limit', 100))

    query = ActivityLog.query

    if user_filter and user_filter != 'all':
        query = query.filter(ActivityLog.user_name == user_filter)
    if action_filter and action_filter != 'all':
        query = query.filter(ActivityLog.action == action_filter)
    if entity_filter and entity_filter != 'all':
        query = query.filter(ActivityLog.entity == entity_filter)

    logs = query.order_by(ActivityLog.timestamp.desc()).limit(limit).all()

    return jsonify([{
        'id': log.id,
        'action': log.action,
        'recordId': log.record_id,
        'user': log.user_name,
        'details': log.details,
        'ipAddress': log.ip_address,
        'entity': log.entity,
        'entityId': log.entity_id,
        'timestamp': log.timestamp.isoformat()
    } for log in logs])

@audit_bp.route('/filters', methods=['GET'])
@login_required
def get_audit_filters():
    users = db.session.query(distinct(ActivityLog.user_name)).all()
    actions = db.session.query(distinct(ActivityLog.action)).all()
    entities = db.session.query(distinct(ActivityLog.entity)).all()
    
    return jsonify({
        'users': sorted([u[0] for u in users if u[0]]),
        'actions': sorted([a[0] for a in actions if a[0]]),
        'entities': sorted([e[0] for e in entities if e[0]])
    })

# SEC-04 FIX: POST /api/audit/ intentionally removed.
# Audit logs are written only by server-side application logic.
# Client applications must never be allowed to forge audit entries.
