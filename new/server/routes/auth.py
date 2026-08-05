from flask import request, jsonify, session, current_app
from . import auth_bp
from models import User, ActivityLog
from extensions import db, limiter  # SEC-08 FIX: import flask-limiter
from utils import log_activity_and_notify
import datetime
import time
from functools import wraps

# In-memory store for login attempts (Key: IP, Value: [count, last_attempt_time])
# Note: For production with multiple workers, use Redis/Flask-Limiter
_login_attempts = {}

def rate_limit_login(limit=5, window=900): # Default: 5 attempts in 15 mins
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            now = time.time()
            
            # Clean up old records to prevent memory leaks
            if len(_login_attempts) > 1000:
                keys_to_delete = [k for k, v in _login_attempts.items() if now - v[1] > window]
                for k in keys_to_delete:
                    del _login_attempts[k]
                    
            if ip in _login_attempts:
                count, last_time = _login_attempts[ip]
                if now - last_time > window:
                    _login_attempts[ip] = [0, now]
            else:
                _login_attempts[ip] = [0, now]
                
            count, last_time = _login_attempts[ip]
            
            if count >= limit:
                return jsonify({
                    'error': f'Too many login attempts. Please try again in {window//60} minutes.'
                }), 429
                
            # Increment attempt counter
            _login_attempts[ip] = [count + 1, now]
            return f(*args, **kwargs)
        return decorated_function  # SEC-07 FIX: removed duplicate return that made decorator return None
    return decorator

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401
        user = User.query.get(user_id)
        if not user or user.role != 'it_admin':
            return jsonify({'error': 'IT Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['POST'])
@admin_required
def register():
    data = request.get_json()

    required_fields = ['fullName', 'orgName', 'email', 'sector', 'password']
    for field in required_fields:
        if not data or not data.get(field):
            return jsonify({'error': f'Missing required field: {field}'}), 400

    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({'error': 'Email already registered'}), 400
        
    password = data.get('password')
    if len(password) < 10:
        return jsonify({'error': 'Password must be at least 10 characters long'}), 400
        
    user = User(
        fullName=data.get('fullName'),
        orgName=data.get('orgName'),
        email=data.get('email'),
        sector=data.get('sector'),
        department=data.get('department'),
        jobTitle=data.get('jobTitle'),
        phone=data.get('phone'),
        location=data.get('location'),
        role=data.get('role', 'user')  # Admins can explicitly set roles
    )
    user.set_password(password)

    
    db.session.add(user)
    db.session.commit()  # BUG-01 FIX: single commit
    
    # Audit
    try:
        log_activity_and_notify(
            action='REGISTER',
            record_id=str(user.id),
            user=user,
            request=request,
            entity='User',
            details=f"User registered: {user.email}"
        )
    except Exception as e:
        print(f"Audit Log Error: {e}")
    
    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': user.id,
            'fullName': user.fullName,
            'email': user.email,
            'orgName': user.orgName,
            'role': user.role,
            'location': user.location,
            'department': user.department,
            'jobTitle': user.jobTitle,
            'status': user.status,
            'created_at': user.created_at.isoformat() if user.created_at else None,
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per 10 minutes")  # SEC-08 FIX: use flask-limiter instead of in-memory dict
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    
    if user and user.check_password(data.get('password')):
        if user.status != 'active':
            return jsonify({'error': 'Account disabled'}), 403
            
        session['user_id'] = user.id
        current_app.logger.debug(f"Session set for user_id={user.id}")  # SEC-12 FIX: replaced DEBUG print
        user.last_login = datetime.datetime.utcnow()
        
        # Reset rate limit on successful login
        if request.remote_addr in _login_attempts:
            del _login_attempts[request.remote_addr]
            
        db.session.commit()
        
        # Audit
        try:
            log_activity_and_notify(
                action='LOGIN',
                record_id=str(user.id),
                user=user,
                request=request,
                entity='User',
                details=f"User logged in: {user.email}"
            )
        except Exception as e:
            print(f"Audit Log Error: {e}")
        
        return jsonify({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'fullName': user.fullName,
                'email': user.email,
                'role': user.role,
                'orgName': user.orgName
            }
        })
        
    return jsonify({'error': 'Invalid credentials'}), 401

# Audit Login (Success)
# (Done inside login block above if successful? No, let's add it before return)
# Actually, inside the `if user and check_password` block is best.
# But I can't easily target inside the block with replace_file_content without context.
# I'll rely on the fact that I can match the return block.


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out'})

@auth_bp.route('/me', methods=['GET'])
def me():
    user_id = session.get('user_id')
    current_app.logger.debug(f"/me check session user_id={user_id}")  # SEC-12 FIX: replaced DEBUG print
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
        
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    return jsonify({
        'id': user.id,
        'fullName': user.fullName,
        'email': user.email,
        'role': user.role,
        'orgName': user.orgName,
        'sector': user.sector,
        'jobTitle': user.jobTitle,
        'department': user.department,
        'phone': user.phone,
        'location': user.location,
        'bio': user.bio,
        'profilePic': user.profilePic,
        'consolidationApproach': user.consolidationApproach
    })

@auth_bp.route('/profile', methods=['PUT'])
def update_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update allowed fields
    if 'fullName' in data:
        user.fullName = data['fullName']
    if 'jobTitle' in data:
        user.jobTitle = data['jobTitle']
    if 'department' in data:
        user.department = data['department']
    if 'phone' in data:
        user.phone = data['phone']
    if 'location' in data:
        user.location = data['location']
    if 'bio' in data:
        user.bio = data['bio']
    if 'consolidationApproach' in data:
        user.consolidationApproach = data['consolidationApproach']
    
    db.session.commit()
    
    return jsonify({'message': 'Profile updated successfully'})

@auth_bp.route('/change-password', methods=['POST'])
def change_password():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new passwords required'}), 400
    
    if not user.check_password(current_password):
        return jsonify({'error': 'Current password incorrect'}), 401
    
    # Password strength check
    if len(new_password) < 10:
        return jsonify({'error': 'Password must be at least 10 characters'}), 400
    
    user.set_password(new_password)
    user.password_updated_at = datetime.datetime.utcnow()

    # Audit + commit atomically
    try:
        log_activity_and_notify(
            action='UPDATE',
            record_id=str(user.id),
            user=user,
            request=request,
            entity='User',
            details=f"Password changed for user: {user.email}"
        )
        db.session.commit()  # commits: password hash + activity log + notification
    except Exception as e:
        db.session.rollback()
        print(f"Audit Log Error: {e}")
    
    return jsonify({'message': 'Password changed successfully'})

@auth_bp.route('/upload-avatar', methods=['POST'])
def upload_avatar():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON body provided'}), 400
    avatar_url = data.get('avatarUrl', '').strip()
    
    if not avatar_url:
        return jsonify({'error': 'Avatar URL required'}), 400

    # SEC-09 FIX: validate URL scheme — block javascript: / data: URIs
    from urllib.parse import urlparse
    parsed = urlparse(avatar_url)
    if parsed.scheme != 'https':
        return jsonify({'error': 'Avatar URL must use HTTPS'}), 400
    if not parsed.netloc:
        return jsonify({'error': 'Invalid URL'}), 400
    
    user.profilePic = avatar_url
    db.session.commit()
    
    return jsonify({'message': 'Avatar updated successfully', 'avatarUrl': avatar_url})

@auth_bp.route('/settings', methods=['GET'])
def get_settings():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Return default empty dict if none
    import json
    prefs = {}
    if user.preferences:
        try:
            prefs = json.loads(user.preferences)
        except:
            prefs = {}
            
    return jsonify(prefs)

@auth_bp.route('/settings', methods=['PUT'])
def update_settings():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    import json
    # Merge with existing? or Replace? Replace is simpler for a settings page that sends full state.
    # But usually safer to merge if we have partial updates.
    # The frontend seems to hold full state, so let's just save what we get, 
    # but maybe preserve existing keys not in data if we wanted to be partial.
    # For now, let's just dump the data as is.
    
    user.preferences = json.dumps(data)
    
    # Sync consolidation approach if present
    if 'consolidation' in data:
        user.consolidationApproach = data['consolidation']

    # Audit + commit atomically
    try:
        log_activity_and_notify(
            action='UPDATE',
            record_id=str(user.id),
            user=user,
            request=request,
            entity='User',
            details=f"Updated settings for user: {user.email}"
        )
        db.session.commit()  # commits: preferences + activity log + notification
    except Exception as e:
        db.session.rollback()
        print(f"Audit Log Error: {e}")
    
    return jsonify({'message': 'Settings saved successfully'})



@auth_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    # Force expire session cache so we always read fresh data from DB
    db.session.expire_all()

    it_admin_id = session.get('user_id')
    it_admin = User.query.get(it_admin_id)
    admin_region = it_admin.location if it_admin else None

    # Treat null / empty / "Global" as "no restriction" — see all users
    SENTINEL_VALUES = {None, '', 'Global', 'global'}
    region_restricted = admin_region not in SENTINEL_VALUES

    query = User.query
    if region_restricted:
        # Scope to users in the same region; always include admins/it_admins
        query = query.filter(
            db.or_(
                User.location == admin_region,
                User.role.in_(['admin', 'it_admin'])
            )
        )

    users = query.order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        result.append({
            'id': u.id,
            'fullName': u.fullName,
            'email': u.email,
            'orgName': u.orgName,
            'role': u.role,
            'location': u.location,
            'department': u.department,
            'jobTitle': u.jobTitle,
            'status': u.status,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'last_login': u.last_login.isoformat() if u.last_login else None
        })
    return jsonify(result)

@auth_bp.route('/users/<int:id>', methods=['PUT'])
@admin_required
def update_user(id):
    db.session.expire_all()
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # IT admin can only modify users within their own region
    it_admin_id = session.get('user_id')
    it_admin = User.query.get(it_admin_id)
    if it_admin and it_admin.location and user.role == 'user':
        if user.location != it_admin.location:
            return jsonify({'error': 'Unauthorized: User is outside your region'}), 403

    data = request.get_json()
    if 'role' in data:
        user.role = data['role']
    if 'location' in data:
        user.location = data['location']
    if 'status' in data:
        user.status = data['status']

    db.session.commit()
    # Return updated user so frontend can reflect changes immediately
    return jsonify({
        'message': 'User updated successfully',
        'user': {
            'id': user.id,
            'fullName': user.fullName,
            'email': user.email,
            'role': user.role,
            'location': user.location,
            'status': user.status
        }
    })

@auth_bp.route('/users/<int:id>', methods=['DELETE'])
@admin_required
def delete_user(id):
    if id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete your own account'}), 400

    db.session.expire_all()
    user = db.session.get(User, id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # IT admin can only delete users within their own region
    it_admin_id = session.get('user_id')
    it_admin = User.query.get(it_admin_id)
    if it_admin and it_admin.location and user.role == 'user':
        if user.location != it_admin.location:
            return jsonify({'error': 'Unauthorized: User is outside your region'}), 403

    # Nullify FK references before deleting to avoid constraint violations
    from models import ActivityLog, Notification
    from sqlalchemy import text
    # Nullify activity_log.user_id references
    db.session.execute(
        text('UPDATE activity_log SET user_id = NULL WHERE user_id = :uid'),
        {'uid': id}
    )
    # Nullify notifications.user_id references
    db.session.execute(
        text('UPDATE notifications SET user_id = NULL WHERE user_id = :uid'),
        {'uid': id}
    )
    # Nullify created_by on facilities
    db.session.execute(
        text('UPDATE facilities SET created_by = NULL WHERE created_by = :uid'),
        {'uid': id}
    )
    # Nullify any other created_by/updated_by references in emissions tables
    for tbl in ['emissions', 'scope2_emissions', 'scope3_emissions', 'mitigation_projects', 'mitigation_records']:
        try:
            db.session.execute(
                text(f'UPDATE {tbl} SET created_by = NULL WHERE created_by = :uid'),
                {'uid': id}
            )
        except Exception:
            pass  # Table may not have created_by column; skip

    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'})

