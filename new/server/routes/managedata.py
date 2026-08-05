from flask import Blueprint, jsonify, request
from models import EmissionSource, MitigationRecord, MitigationProject, ReportingMetadata, Facility, ProductionData, Emission, Scope2Emission, Scope3Emission, Notification, User
from extensions import db
from utils import get_current_user, get_allowed_facility_ids
from sqlalchemy import func, distinct, or_
from routes.auth import admin_required, login_required

managedata_bp = Blueprint('managedata', __name__)

# --- Emission Sources ---
@managedata_bp.route('/sources', methods=['GET'])
@login_required
def get_sources():
    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)

    query = EmissionSource.query
    if allowed_fids is not None:
        query = query.filter(EmissionSource.facility_id.in_(allowed_fids))

    sources = query.all()
    return jsonify([{
        'id': s.id,
        'facility_id': s.facility_id,
        'name': s.name,
        'type': s.type,
        'equipment_id': s.equipment_id,
        'fuel_type': s.fuel_type,
        'design_capacity': s.design_capacity,
        'installation_date': s.installation_date,
        'status': s.status,
        'description': s.description,
        'activity': s.activity,
        'division': s.division,
        'field': s.field,
        'region': s.region
    } for s in sources])

@managedata_bp.route('/sources', methods=['POST'])
@login_required
def add_source():
    data = request.get_json()
    source = EmissionSource(
        facility_id=data.get('facility_id'),
        name=data.get('name'),
        type=data.get('type'),
        equipment_id=data.get('equipment_id'),
        fuel_type=data.get('fuel_type'),
        design_capacity=data.get('design_capacity'),
        installation_date=data.get('installation_date'),
        status=data.get('status', 'Active'),
        description=data.get('description'),
        activity=data.get('activity'),
        division=data.get('division'),
        field=data.get('field')
    )
    db.session.add(source)
    db.session.commit()
    return jsonify({'message': 'Source added', 'id': source.id}), 201

@managedata_bp.route('/sources/<int:source_id>', methods=['DELETE'])
@login_required
def delete_source(source_id):
    source = EmissionSource.query.get(source_id)
    if not source:
        return jsonify({'error': 'Source not found'}), 404
    db.session.delete(source)
    db.session.commit()
    return jsonify({'message': 'Source deleted'})

@managedata_bp.route('/sources/bulk-import', methods=['POST'])
@login_required
def bulk_import_sources():
    data = request.get_json()
    records = data.get('records', [])
    if not records:
        return jsonify({'error': 'No records provided'}), 400
    
    imported_count = 0
    facility_cache = {}

    for rec in records:
        # Resolve facility_id (could be a name string from CSV)
        f_val = rec.get('facility_id')
        facility = None
        
        if isinstance(f_val, str) and not str(f_val).isdigit():
            f_name_clean = f_val.strip()
            if f_name_clean.lower() in facility_cache:
                facility = facility_cache[f_name_clean.lower()]
            else:
                facility = Facility.query.filter(func.lower(Facility.name) == f_name_clean.lower()).first()
                facility_cache[f_name_clean.lower()] = facility
        else:
            try:
                fid = int(f_val) if f_val else None
                if fid in facility_cache:
                    facility = facility_cache[fid]
                else:
                    facility = Facility.query.get(fid)
                    facility_cache[fid] = facility
            except (ValueError, TypeError):
                facility = None

        if not facility:
            continue

        source = EmissionSource(
            facility_id=facility.id,
            name=rec.get('name'),
            equipment_id=rec.get('equipment_id'),
            type=rec.get('type'),
            fuel_type=rec.get('fuel_type') or rec.get('fuel'),
            design_capacity=rec.get('design_capacity'),
            installation_date=rec.get('installation_date'),
            status=rec.get('status', 'Active'),
            description=rec.get('description'),
            activity=rec.get('activity') or facility.activity,
            division=rec.get('division') or facility.division,
            field=rec.get('field') or facility.field
        )
        db.session.add(source)
        imported_count += 1
    
    db.session.commit()
    return jsonify({'message': f'{imported_count} sources imported'}), 201

# --- Mitigation Records ---
@managedata_bp.route('/mitigation', methods=['GET'])
@login_required
def get_mitigations():
    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)

    # Fetch Records (Legacy/Generic) — not facility-linked, visible to all
    records = MitigationRecord.query.all()

    # Fetch Projects (Facility-linked) — apply access filter
    proj_query = db.session.query(MitigationProject, Facility).outerjoin(Facility, MitigationProject.facility_id == Facility.id)
    if allowed_fids is not None:
        proj_query = proj_query.filter(
            or_(
                MitigationProject.facility_id.is_(None),
                MitigationProject.facility_id.in_(allowed_fids)
            )
        )
    projects = proj_query.all()
    
    results = []
    
    # Process Records
    for m in records:
        results.append({
            'id': f"rec_{m.id}",
            'type': 'record', 
            'year': m.year,
            'name': f"{m.type}", # Generic name
            'mitigation_type': m.type,
            'subtype': m.subtype,
            'quantity_tco2e': m.quantity_tco2e,
            'notes': m.notes,
            'reference_id': m.reference_id,
            'activity': '-',
            'division': '-',
            'region': '-',
            'status': 'Active'
        })
        
    # Process Projects
    for p, f in projects:
        results.append({
            'id': f"proj_{p.id}",
            'type': 'project',
            'year': p.year,
            'name': p.name,
            'mitigation_type': p.project_type,
            'subtype': '-',
            'quantity_tco2e': p.quantity_tco2e,
            'notes': p.description,
            'reference_id': '-',
            'activity': f.activity if f else '-',
            'division': f.division if f else '-',
            'region': f.name if f else '-',
            'status': p.status
        })
        
    return jsonify(results)

@managedata_bp.route('/mitigation', methods=['POST'])
@login_required
def add_mitigation():
    data = request.get_json()
    
    facility_id = data.get('facility_id')
    
    if facility_id:
        # Create MitigationProject
        project = MitigationProject(
            name=data.get('name') or f"{data.get('type')} Project",
            project_type=data.get('type'),
            year=data.get('year'),
            quantity_tco2e=data.get('quantity_tco2e', 0),
            status=data.get('status', 'active'),
            description=data.get('notes'),
            facility_id=facility_id
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({'message': 'Mitigation Project added', 'id': f"proj_{project.id}"}), 201
    else:
        # Create generic MitigationRecord
        mitigation = MitigationRecord(
            year=data.get('year'),
            type=data.get('type'),
            subtype=data.get('subtype'),
            quantity_tco2e=data.get('quantity_tco2e', 0),
            notes=data.get('notes'),
            reference_id=data.get('reference_id')
        )
        db.session.add(mitigation)
        db.session.commit()
        return jsonify({'message': 'Mitigation record added', 'id': f"rec_{mitigation.id}"}), 201

@managedata_bp.route('/mitigation/<string:mitigation_id>', methods=['DELETE'])
@login_required
def delete_mitigation(mitigation_id):
    # Determine type from ID prefix
    if mitigation_id.startswith('proj_'):
        pid = int(mitigation_id.split('_')[1])
        item = MitigationProject.query.get(pid)
    elif mitigation_id.startswith('rec_'):
        rid = int(mitigation_id.split('_')[1])
        item = MitigationRecord.query.get(rid)
    else:
        # Fallback for old IDs (assume record)
        item = MitigationRecord.query.get(int(mitigation_id))
        
    if not item:
        return jsonify({'error': 'Record not found'}), 404
        
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Mitigation record deleted'})

# --- Reporting Metadata ---
@managedata_bp.route('/reporting-metadata', methods=['GET'])
@login_required
def get_reporting_metadata():
    year = request.args.get('year')
    if not year:
        return jsonify({'error': 'Year required'}), 400
    
    metadata = ReportingMetadata.query.filter_by(year=int(year)).first()
    if not metadata:
        return jsonify({
            'year': int(year),
            'has_reduction_target': 0,
            'target_description': '',
            'is_tcfd_aligned': 0,
            'assurance_level': 'None',
            'assurance_provider': '',
            'notes': ''
        })
    
    return jsonify({
        'id': metadata.id,
        'year': metadata.year,
        'has_reduction_target': metadata.has_reduction_target,
        'target_description': metadata.target_description,
        'is_tcfd_aligned': metadata.is_tcfd_aligned,
        'assurance_level': metadata.assurance_level,
        'assurance_provider': metadata.assurance_provider,
        'notes': metadata.notes
    })

@managedata_bp.route('/reporting-metadata', methods=['POST'])
@login_required
def save_reporting_metadata():
    data = request.get_json()
    year = data.get('year')
    if not year:
        return jsonify({'error': 'Year required'}), 400
    
    metadata = ReportingMetadata.query.filter_by(year=int(year)).first()
    if metadata:
        metadata.has_reduction_target = data.get('has_reduction_target', metadata.has_reduction_target)
        metadata.target_description = data.get('target_description', metadata.target_description)
        metadata.is_tcfd_aligned = data.get('is_tcfd_aligned', metadata.is_tcfd_aligned)
        metadata.assurance_level = data.get('assurance_level', metadata.assurance_level)
        metadata.assurance_provider = data.get('assurance_provider', metadata.assurance_provider)
        metadata.notes = data.get('notes', metadata.notes)
    else:
        metadata = ReportingMetadata(
            year=int(year),
            has_reduction_target=data.get('has_reduction_target', 0),
            target_description=data.get('target_description', ''),
            is_tcfd_aligned=data.get('is_tcfd_aligned', 0),
            assurance_level=data.get('assurance_level', 'None'),
            assurance_provider=data.get('assurance_provider', ''),
            notes=data.get('notes', '')
        )
        db.session.add(metadata)
    
    db.session.commit()
    
    # --- Audit Notification ---
    try:
        user_id = request.headers.get('X-User-ID') # Or session
        # If we had a current_user helper here:
        # For now, just create a system/audit notif
        Notification.create(
            title="Reporting Metadata Updated",
            message=f"Reporting metadata for {year} was updated.",
            type='audit',
            user_id=None # Global audit log
        )
    except Exception as e:
        print(f"Audit Notif Error: {e}")

    return jsonify({'message': 'Reporting metadata saved'})

# --- Production Years ---
@managedata_bp.route('/production/years', methods=['GET'])
@login_required
def get_production_years():
    years = db.session.query(ProductionData.year).distinct().order_by(ProductionData.year.desc()).all()
    return jsonify([y[0] for y in years])

# --- Global Available Filters ---
@managedata_bp.route('/filters/available', methods=['GET'])
@login_required
def get_available_filters():
    # Helper to get distinct years from various tables
    year_queries = [
        db.session.query(distinct(Emission.year)),
        db.session.query(distinct(ProductionData.year)),
        db.session.query(distinct(MitigationRecord.year)),
        db.session.query(distinct(Scope2Emission.year)),
        db.session.query(distinct(Scope3Emission.year))
    ]
    
    available_years = set()
    for query in year_queries:
        try:
            results = query.all()
            for r in results:
                if r[0]: available_years.add(int(r[0]))
        except Exception:
            continue
            
    user = get_current_user()
    allowed_fids = get_allowed_facility_ids(user)
    
    # Also include regions that have data
    # (Simplified: just return all active facilities for now, or those referenced in Emission rows)
    em_query = db.session.query(distinct(Emission.facility_id))
    if allowed_fids is not None:
        em_query = em_query.filter(Emission.facility_id.in_(allowed_fids))
    referenced_facility_ids = em_query.all()
    facility_ids = [r[0] for r in referenced_facility_ids if r[0]]
    
    # Get facility details
    fac_query = Facility.query
    if allowed_fids is not None:
        fac_query = fac_query.filter(Facility.id.in_(allowed_fids))
    facilities = fac_query.filter(Facility.id.in_(facility_ids)).all() if facility_ids else fac_query.all()
    
    return jsonify({
        'years': sorted(list(available_years), reverse=True),
        'regions': [{
            'id': f.id,
            'name': f.name,
            'activity': f.activity,
            'division': f.division,
            'field': f.field
        } for f in facilities]
    })



@managedata_bp.route('/mitigation/bulk-import', methods=['POST'])
@login_required
def bulk_import_mitigation():
    data = request.get_json()
    records = data.get('records', [])
    if not records:
        return jsonify({'error': 'No records provided'}), 400
    
    imported_count = 0
    facility_cache = {}
    from datetime import datetime

    for rec in records:
        f_val = rec.get('facility_id')
        facility = None
        
        if isinstance(f_val, str) and not str(f_val).isdigit():
            f_name_clean = f_val.strip()
            if f_name_clean.lower() in facility_cache:
                facility = facility_cache[f_name_clean.lower()]
            else:
                facility = Facility.query.filter(func.lower(Facility.name) == f_name_clean.lower()).first()
                facility_cache[f_name_clean.lower()] = facility
        else:
            try:
                fid = int(f_val) if f_val else None
                if fid in facility_cache:
                    facility = facility_cache[fid]
                else:
                    facility = Facility.query.get(fid)
                    facility_cache[fid] = facility
            except (ValueError, TypeError):
                facility = None

        if not facility:
            continue
            
        try:
            year = int(rec.get('year'))
        except (ValueError, TypeError):
            continue
            
        try:
            qty = float(rec.get('quantity_tco2e') or 0)
        except (ValueError, TypeError):
            continue
            
        start_date = None
        end_date = None
        if rec.get('start_date'):
            try:
                start_date = datetime.strptime(rec.get('start_date'), '%Y-%m-%d').date()
            except ValueError:
                pass
        if rec.get('end_date'):
            try:
                end_date = datetime.strptime(rec.get('end_date'), '%Y-%m-%d').date()
            except ValueError:
                pass
                
        investment = None
        if rec.get('investment_amount'):
            try:
                investment = float(rec.get('investment_amount'))
            except ValueError:
                pass

        proj = MitigationProject(
            facility_id=facility.id,
            name=rec.get('name'),
            project_type=rec.get('project_type'),
            year=year,
            quantity_tco2e=qty,
            status=rec.get('status', 'Active'),
            start_date=start_date,
            end_date=end_date,
            investment_amount=investment,
            description=rec.get('description'),
            created_by=get_current_user().id
        )
        db.session.add(proj)
        imported_count += 1
        
    db.session.commit()
    return jsonify({'message': f'{imported_count} mitigation projects imported'}), 201
