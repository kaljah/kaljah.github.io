from flask import request, jsonify, session
import json
from . import facilities_bp
from utils import get_allowed_facility_ids, log_activity_and_notify
from models import Facility, ActivityLog, User
from extensions import db
from routes.auth import admin_required, login_required
import json

@facilities_bp.route('/', methods=['GET'])
@login_required
def get_facilities():
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None  # API-02 FIX: replaced deprecated query.get
    
    query = Facility.query
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None:
        query = query.filter(Facility.id.in_(allowed_fids))
        
    if request.args.get('search'):
        query = query.filter(Facility.name.contains(request.args.get('search')))
        
    facilities = query.all()
    return jsonify([{
        'id': f.id,
        'name': f.name,
        'location': f.location,
        'division': f.division,
        'activity': f.activity,
        'region': f.region,
        'boundary_notes': f.boundary_notes,
        'segment': f.segment,
        'field': f.field,
        'latitude': f.latitude,
        'longitude': f.longitude
    } for f in facilities])

@facilities_bp.route('/all-regions', methods=['GET'])
@login_required
def get_all_regions():
    """
    Return all unique region identifiers — IT Admin only, no access filtering.

    Mirrors the fallback logic in utils.get_allowed_facility_ids():
      - Uses facility.region when set
      - Falls back to facility.name for facilities where region is NULL
    This ensures the values shown in the dropdown will always resolve to
    actual facilities when a user's location is matched later.
    """
    user_id = session.get('user_id')
    caller = db.session.get(User, user_id) if user_id else None  # API-02 FIX
    if not caller or caller.role != 'it_admin':
        return jsonify({'error': 'IT Admin privileges required'}), 403

    identifiers = set()

    # 1. Facilities that have an explicit region value
    region_rows = db.session.query(Facility.region).filter(
        Facility.region.isnot(None),
        Facility.region != ''
    ).distinct().all()
    for (r,) in region_rows:
        if r and r.strip():
            identifiers.add(r.strip())

    # 2. For facilities with no region set, fall back to their name
    #    (mirrors utils.py line 28: filter_by(name=user_region))
    name_rows = db.session.query(Facility.name).filter(
        db.or_(Facility.region.is_(None), Facility.region == ''),
        Facility.name.isnot(None),
        Facility.name != ''
    ).distinct().all()
    for (n,) in name_rows:
        if n and n.strip():
            identifiers.add(n.strip())

    return jsonify(sorted(identifiers))

@facilities_bp.route('/', methods=['POST'])
def add_facility():
    data = request.get_json()
    
    fac = Facility(
        name=data.get('name'),
        location=data.get('location'),
        division=data.get('division'),
        activity=data.get('activity'),
        region=data.get('region'),
        field=data.get('field'),
        code=data.get('code'),
        boundary_notes=data.get('boundary_notes'),
        segment=data.get('segment'),
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    
    db.session.add(fac)
    db.session.flush() # Flush to get fac.id for audit log
    
    # Audit
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None
        
        log_details = f"Created facility: {fac.name} (Code: {fac.code}, Segment: {fac.segment})"
        
        log_activity_and_notify(
            action='CREATE',
            record_id=str(fac.id),
            user=user,
            request=request,
            entity='Facility',
            details=log_details,
            metadata_json=json.dumps({
                'name': fac.name,
                'code': fac.code,
                'segment': fac.segment,
                'location': fac.location
            })
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
    return jsonify({'message': 'Facility added', 'id': fac.id}), 201

@facilities_bp.route('/<int:facility_id>', methods=['PUT'])
@login_required
def update_facility(facility_id):
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None  # API-02 FIX
    
    facility = db.session.get(Facility, facility_id)  # API-02 FIX: replaced deprecated query.get
    if not facility:
        return jsonify({'error': 'Facility not found'}), 404
        
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and facility.id not in allowed_fids:
        return jsonify({'error': 'Unauthorized: Outside your region'}), 403
    
    data = request.get_json()
    
    if 'name' in data:
        facility.name = data['name']
    if 'location' in data:
        facility.location = data['location']
    if 'description' in data:
        facility.description = data['description']
    if 'boundary_notes' in data:
        facility.boundary_notes = data['boundary_notes']
    if 'activity' in data:
        facility.activity = data['activity']
    if 'region' in data:
        facility.region = data['region']
    if 'division' in data:
        facility.division = data['division']
    if 'field' in data:
        facility.field = data['field']
    if 'code' in data:
        facility.code = data['code']
    if 'external_id' in data:
        facility.external_id = data['external_id']
    if 'segment' in data:
        facility.segment = data['segment']
    if 'latitude' in data:
        facility.latitude = data['latitude']
    if 'longitude' in data:
        facility.longitude = data['longitude']
    
    import datetime
    facility.updated_at = datetime.datetime.utcnow()
    db.session.flush()
    
    # Audit
    try:
        user = db.session.get(User, user_id) if user_id else None  # API-02 FIX
        
        changes = [k for k in data if k in ['name', 'location', 'description', 'boundary_notes', 'activity', 'division', 'field', 'code', 'segment']]
        log_details = f"Updated facility: {facility.name}. Changed: {', '.join(changes)}"
        
        log_activity_and_notify(
            action='UPDATE',
            record_id=str(facility_id),
            user=user,
            request=request,
            entity='Facility',
            details=log_details,
            metadata_json=json.dumps({
                'updated_fields': changes,
                'new_values': {k: v for k, v in data.items() if k in changes}
            })
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
    return jsonify({'message': 'Facility updated'})

@facilities_bp.route('/<int:facility_id>', methods=['DELETE'])
@login_required
def delete_facility(facility_id):
    user_id = session.get('user_id')
    user = db.session.get(User, user_id) if user_id else None  # API-02 FIX
    
    facility = db.session.get(Facility, facility_id)  # API-02 FIX: replaced deprecated query.get
    if not facility:
        return jsonify({'error': 'Facility not found'}), 404
        
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and facility.id not in allowed_fids:
        return jsonify({'error': 'Unauthorized: Outside your region'}), 403
    
    db.session.delete(facility)
    db.session.flush()
    
    # Audit
    try:
        user = db.session.get(User, user_id) if user_id else None  # API-02 FIX
        log_details = f"Deleted facility: {facility.name} (Code: {facility.code})"
        
        log_activity_and_notify(
            action='DELETE',
            record_id=str(facility_id),
            user=user,
            request=request,
            entity='Facility',
            details=log_details,
            metadata_json=json.dumps({
                'name': facility.name,
                'code': facility.code,
                'location': facility.location
            })
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    
    return jsonify({'message': 'Facility deleted'})

@facilities_bp.route('/import', methods=['POST'])
def import_facilities():
    """Bulk import facilities"""
    user_id = session.get('user_id')
    
    data = request.get_json()
    facilities_data = data.get('facilities', [])
    
    if not facilities_data:
        return jsonify({'error': 'No facilities provided'}), 400
    
    imported_count = 0
    for fac_data in facilities_data:
        facility = Facility(
            name=fac_data.get('name'),
            location=fac_data.get('location'),
            description=fac_data.get('description'),
            boundary_notes=fac_data.get('boundary_notes'),
            activity=fac_data.get('activity'),
            division=fac_data.get('division'),
            region=fac_data.get('region'),
            field=fac_data.get('field'),
            code=fac_data.get('code'),
            external_id=fac_data.get('external_id'),
            segment=fac_data.get('segment'),
            created_by=user_id
        )
        db.session.add(facility)
        imported_count += 1
    
    db.session.commit()
    
    return jsonify({'message': f'{imported_count} facilities imported'})
