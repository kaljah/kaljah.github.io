from routes.auth import login_required
from flask import request, jsonify, session
import json
from . import data_bp
from utils import get_current_user, get_allowed_facility_ids, log_activity_and_notify, require_facility_access
from sqlalchemy import func
from models import (
    ProductionData, ActivityLog, User, Facility, OgmpSurvey, 
    MethaneSourceType, LevelUpgradeLog, Emission, CbamProductExport
)
from extensions import db

# Activities that are NOT oil & gas — excluded from OGMP 2.0 scope
NON_OG_ACTIVITIES = [
    'Steel & Iron (Acier DRI)',
    'Chemicals & Fertilizers',
    'Cement & Clinker',
]

@data_bp.route('/production', methods=['GET'])
@data_bp.route('/production/', methods=['GET'])
@login_required
def get_production():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to access operational production data.'}), 403
    query = ProductionData.query
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None:
        query = query.filter(ProductionData.facility_id.in_(allowed_fids))
    if request.args.get('facilityId'):
        try:
            fid = int(request.args.get('facilityId'))
            if not require_facility_access(user, fid):
                return jsonify({'error': 'Access to requested facility is denied'}), 403
            query = query.filter_by(facility_id=fid)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid facilityId'}), 400
    if request.args.get('year'):
        query = query.filter_by(year=request.args.get('year'))
        
    data = query.all()
    return jsonify([{
        'id': d.id,
        'facilityId': d.facility_id,
        'year': d.year,
        'month': d.month,
        'oil': d.oil_amount,
        'gas': d.gas_amount,
        'oilUnit': d.oil_unit,
        'gasUnit': d.gas_unit,
        'activity': d.activity,
        'division': d.division,
        'field': d.field
    } for d in data])

@data_bp.route('/production', methods=['POST'])
@data_bp.route('/production/', methods=['POST'])
@login_required
def add_production():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to modify operational production data.'}), 403
    data = request.get_json() or {}
    fid = data.get('facility_id') or data.get('facilityId')
    if not fid:
        return jsonify({'error': 'Facility ID is required'}), 400
    try:
        fid = int(fid)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid facility ID'}), 400
        
    if not require_facility_access(user, fid):
        return jsonify({'error': 'Access to this facility is denied'}), 403
    
    # Check if exists
    existing = ProductionData.query.filter_by(
        facility_id=fid,
        year=data.get('year'),
        month=data.get('month')
    ).first()
    
    if existing:
        existing.oil_amount = data.get('oil_amount', 0)
        existing.gas_amount = data.get('gas_amount', 0)
        existing.oil_unit = data.get('oil_unit', 'bbl')
        existing.gas_unit = data.get('gas_unit', 'mscf')
        existing.activity = data.get('activity')
        existing.division = data.get('division')
        existing.field = data.get('field')
    else:
        prod = ProductionData(
            facility_id=fid,
            year=data.get('year'),
            month=data.get('month'),
            oil_amount=data.get('oil_amount', 0),
            gas_amount=data.get('gas_amount', 0),
            oil_unit=data.get('oil_unit', 'bbl'),
            gas_unit=data.get('gas_unit', 'mscf'),
            activity=data.get('activity'),
            division=data.get('division'),
            field=data.get('field')
        )
    # Audit + commit atomically
    try:
        if not existing:
            db.session.add(prod)
            db.session.flush()
            rec_id = prod.id
            action = 'CREATE'
        else:
            rec_id = existing.id
            action = 'UPDATE'
        
        log_details = f"{action.title()} Production Data for {data.get('year')}-{data.get('month')}: {data.get('oil_amount')} {data.get('oil_unit', 'bbl')} oil, {data.get('gas_amount')} {data.get('gas_unit', 'mscf')} gas"
        
        log_activity_and_notify(
            action=action,
            record_id=str(rec_id),
            user=user,
            request=request,
            entity='ProductionData',
            details=log_details
        )
        db.session.commit()  # commits: data + activity log + notification
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
    except Exception as e:
        db.session.rollback()
        import traceback
        from flask import current_app
        if current_app:
            current_app.logger.error(f"Production save error: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to save production data'}), 500

    return jsonify({'message': 'Production data saved'})

@data_bp.route('/production/<int:record_id>', methods=['DELETE'])
@login_required
def delete_production(record_id):
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to modify operational production data.'}), 403
    prod = ProductionData.query.get(record_id)
    if not prod:
        return jsonify({'error': 'Production record not found'}), 404
    
    if not require_facility_access(user, prod.facility_id):
        return jsonify({'error': 'Access to this facility is denied'}), 403
        
    db.session.delete(prod)
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()
    return jsonify({'message': 'Production record deleted'})


@data_bp.route('/production/bulk-import', methods=['POST'])
@login_required
def bulk_import_production():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to modify operational production data.'}), 403
    allowed_fids = get_allowed_facility_ids(user)
    data = request.get_json() or {}
    records = data.get('records', [])
    if not records:
        return jsonify({'error': 'No records provided'}), 400
    
    imported_count = 0
    facility_cache = {}

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

        if allowed_fids is not None and facility.id not in allowed_fids:
            continue

        year = rec.get('year')
        month = rec.get('month')
        if not year or not month:
            continue

        try:
            year = int(year)
            month = int(month)
        except ValueError:
            continue

        existing = ProductionData.query.filter_by(
            facility_id=facility.id,
            year=year,
            month=month
        ).first()

        oil_amount = float(rec.get('oil_amount') or 0)
        gas_amount = float(rec.get('gas_amount') or 0)

        if existing:
            existing.oil_amount = oil_amount
            existing.gas_amount = gas_amount
            if rec.get('oil_unit'): existing.oil_unit = rec.get('oil_unit')
            if rec.get('gas_unit'): existing.gas_unit = rec.get('gas_unit')
            if rec.get('activity'): existing.activity = rec.get('activity')
            if rec.get('division'): existing.division = rec.get('division')
            if rec.get('field'): existing.field = rec.get('field')
        else:
            prod = ProductionData(
                facility_id=facility.id,
                year=year,
                month=month,
                oil_amount=oil_amount,
                gas_amount=gas_amount,
                oil_unit=rec.get('oil_unit', 'bbl'),
                gas_unit=rec.get('gas_unit', 'mscf'),
                activity=rec.get('activity') or facility.activity,
                division=rec.get('division') or facility.division,
                field=rec.get('field') or facility.field
            )
            db.session.add(prod)
        
        imported_count += 1
    
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()
    return jsonify({'message': f'{imported_count} production records imported'}), 201





# ==========================================
# OGMP 2.0 TOP-DOWN SURVEYS & TAXONOMY
# ==========================================
@data_bp.route('/methane-sources', methods=['GET'])
@login_required
def get_methane_sources():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to view operational data.'}), 403
    sources = MethaneSourceType.query.order_by(MethaneSourceType.id.asc()).all()
    return jsonify([{
        'id': s.id,
        'code': s.code,
        'name': s.name,
        'category': s.category,
        'default_ef_reference': s.default_ef_reference,
        'default_level': s.default_level
    } for s in sources])

@data_bp.route('/ogmp-surveys', methods=['GET'])
@data_bp.route('/ogmp-surveys/', methods=['GET'])
@login_required
def get_ogmp_surveys():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to view operational OGMP data.'}), 403
    query = OgmpSurvey.query
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None:
        query = query.filter(OgmpSurvey.facility_id.in_(allowed_fids))
    if request.args.get('facilityId') and request.args.get('facilityId') != 'all':
        try:
            fid = int(request.args.get('facilityId'))
            if allowed_fids is not None and fid not in allowed_fids:
                return jsonify({'error': 'Access to requested facility is denied'}), 403
            query = query.filter_by(facility_id=fid)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid facilityId'}), 400
    # Single join to Facility — needed for O&G scope filter and optional segment filter
    query = query.join(Facility, OgmpSurvey.facility_id == Facility.id)
    # Restrict to Oil & Gas facilities only (OGMP 2.0 scope)
    query = query.filter(~Facility.activity.in_(NON_OG_ACTIVITIES))
    if request.args.get('segment') and request.args.get('segment') != 'all':
        query = query.filter(Facility.segment == request.args.get('segment'))
    if request.args.get('activity') and request.args.get('activity') != 'all':
        query = query.filter(Facility.activity == request.args.get('activity'))
    if request.args.get('division') and request.args.get('division') != 'all':
        query = query.filter(Facility.division == request.args.get('division'))
    if request.args.get('year') and request.args.get('year') != 'all':
        try:
            query = query.filter(OgmpSurvey.year == int(request.args.get('year')))
        except (ValueError, TypeError):
            pass
    if request.args.get('survey_type') and request.args.get('survey_type') != 'all':
        query = query.filter(OgmpSurvey.survey_type == request.args.get('survey_type'))

    data = query.order_by(OgmpSurvey.survey_date.desc()).all()
    return jsonify([{
        'id': d.id,
        'facility_id': d.facility_id,
        'facilityId': d.facility_id,
        'facility_name': d.facility.name if d.facility else 'Unknown',
        'facilityName': d.facility.name if d.facility else 'Unknown',
        'year': d.year,
        'survey_date': d.survey_date,
        'surveyDate': d.survey_date,
        'survey_type': d.survey_type,
        'surveyType': d.survey_type,
        'measured_rate_kg_hr': d.measured_rate_kg_hr,
        'measuredRateKgHr': d.measured_rate_kg_hr,
        'operating_hours_year': d.operating_hours_year or 8760.0,
        'operatingHoursYear': d.operating_hours_year or 8760.0,
        'estimated_annual_tch4': d.estimated_annual_tch4 or round(d.measured_rate_kg_hr * (d.operating_hours_year or 8760) / 1000.0, 2),
        'estimatedAnnualTch4': d.estimated_annual_tch4 or round(d.measured_rate_kg_hr * (d.operating_hours_year or 8760) / 1000.0, 2),
        'detection_threshold': d.detection_threshold,
        'detectionThreshold': d.detection_threshold,
        'instrument_vendor': d.instrument_vendor or '',
        'instrumentVendor': d.instrument_vendor or '',
        'raw_file_ref': d.raw_file_ref or '',
        'bottom_up_tch4': d.bottom_up_tch4 or 0.0,
        'variance_pct': d.variance_pct or 0.0,
        'variance_flag': bool(d.variance_flag),
        'reconciliation_status': d.reconciliation_status or 'Reconciled',
        'reconciliationStatus': d.reconciliation_status or 'Reconciled',
        'status': d.status or 'pending',
        'operator_notes': d.operator_notes or '',
        'operatorNotes': d.operator_notes or ''
    } for d in data])

@data_bp.route('/ogmp-surveys', methods=['POST'])
@data_bp.route('/ogmp-surveys/', methods=['POST'])
@login_required
def save_ogmp_survey():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to modify operational OGMP data.'}), 403
    data = request.get_json() or {}
    record_id = data.get('id')
    facility_id = data.get('facility_id') or data.get('facilityId')
    year = int(data.get('year', 2026))
    survey_date = (data.get('survey_date') or data.get('surveyDate') or '').strip()
    survey_type = (data.get('survey_type') or data.get('surveyType') or 'Satellite (Sentinel-5P/MethaneSAT)').strip()
    measured_rate_kg_hr = float(data.get('measured_rate_kg_hr') or data.get('measuredRateKgHr') or 0.0)
    operating_hours = float(data.get('operating_hours_year') or data.get('operatingHoursYear') or 8760.0)
    detection_threshold = float(data.get('detection_threshold') or data.get('detectionThreshold')) if data.get('detection_threshold') is not None or data.get('detectionThreshold') is not None else None
    instrument_vendor = (data.get('instrument_vendor') or data.get('instrumentVendor') or '').strip()
    reconciliation_status = (data.get('reconciliation_status') or data.get('reconciliationStatus') or 'Reconciled').strip()
    operator_notes = data.get('operator_notes') or data.get('operatorNotes') or ''

    if not facility_id or not survey_date or measured_rate_kg_hr < 0:
        return jsonify({'error': 'Facility, survey date, and measured emission rate are required'}), 400
    try:
        facility_id = int(facility_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid facility ID'}), 400

    if not require_facility_access(user, facility_id):
        return jsonify({'error': 'Access to this facility is denied'}), 403

    # Validate facility is Oil & Gas scope
    fac = Facility.query.get(facility_id)
    if not fac:
        return jsonify({'error': 'Facility not found'}), 404
    if fac.activity in NON_OG_ACTIVITIES:
        return jsonify({'error': f'OGMP 2.0 surveys are only applicable to Oil & Gas facilities. "{fac.name}" ({fac.activity}) is not in scope.'}), 400

    estimated_annual_tch4 = round(measured_rate_kg_hr * operating_hours / 1000.0, 2)

    # Compute bottom-up methane total for facility & year to compute variance
    bottom_up_sum = db.session.query(func.sum(Emission.ch4_emissions)).filter(
        Emission.facility_id == facility_id,
        Emission.year == year,
        Emission.status == 'Verified'
    ).scalar() or 0.0
    bottom_up_tch4 = round(float(bottom_up_sum), 2)

    # Compute variance %
    if bottom_up_tch4 > 0:
        variance_pct = round(((estimated_annual_tch4 - bottom_up_tch4) / bottom_up_tch4 * 100.0), 2)
        threshold = (fac.reconciliation_threshold if fac and fac.reconciliation_threshold else 20.0)
        variance_flag = abs(variance_pct) > threshold
    elif estimated_annual_tch4 > 0:
        variance_pct = None
        variance_flag = True
    else:
        variance_pct = 0.0
        variance_flag = False

    if record_id:
        record = OgmpSurvey.query.get(record_id)
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        record.facility_id = facility_id
        record.year = year
        record.survey_date = survey_date
        record.survey_type = survey_type
        record.measured_rate_kg_hr = measured_rate_kg_hr
        record.operating_hours_year = operating_hours
        record.estimated_annual_tch4 = estimated_annual_tch4
        record.detection_threshold = detection_threshold
        record.instrument_vendor = instrument_vendor
        record.bottom_up_tch4 = bottom_up_tch4
        record.variance_pct = variance_pct
        record.variance_flag = variance_flag
        record.reconciliation_status = reconciliation_status
        record.operator_notes = operator_notes
        action = 'UPDATE'
    else:
        record = OgmpSurvey(
            facility_id=facility_id,
            year=year,
            survey_date=survey_date,
            survey_type=survey_type,
            measured_rate_kg_hr=measured_rate_kg_hr,
            operating_hours_year=operating_hours,
            estimated_annual_tch4=estimated_annual_tch4,
            detection_threshold=detection_threshold,
            instrument_vendor=instrument_vendor,
            bottom_up_tch4=bottom_up_tch4,
            variance_pct=variance_pct,
            variance_flag=variance_flag,
            reconciliation_status=reconciliation_status,
            operator_notes=operator_notes,
            created_by=session.get('user_id')
        )
        db.session.add(record)
        db.session.flush()
        action = 'CREATE'

    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None
        log_activity_and_notify(
            action=action,
            record_id=str(record.id),
            user=user,
            request=request,
            entity='OgmpSurvey',
            details=f"{action.title()} OGMP 2.0 top-down survey: {measured_rate_kg_hr} kg CH4/hr via {survey_type} at {record.facility.name if record.facility else facility_id}"
        )
        db.session.commit()
        from routes.dashboard import clear_dashboard_cache
        clear_dashboard_cache()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'OGMP survey record saved', 'id': record.id}), 201

@data_bp.route('/ogmp-surveys/<int:record_id>', methods=['DELETE'])
@login_required
def delete_ogmp_survey(record_id):
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to modify operational OGMP data.'}), 403
    record = OgmpSurvey.query.get(record_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    if not require_facility_access(user, record.facility_id):
        return jsonify({'error': 'Access to this facility is denied'}), 403
    db.session.delete(record)
    db.session.commit()
    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()
    return jsonify({'message': 'OGMP survey record deleted'})

@data_bp.route('/ogmp/level-upgrade', methods=['POST'])
@login_required
def log_level_upgrade():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to modify operational OGMP data.'}), 403
    data = request.get_json() or {}
    facility_id = data.get('facility_id')
    old_level = int(data.get('old_level', 3))
    new_level = int(data.get('new_level', 4))
    source_type_code = data.get('source_type_code', 'ALL')
    justification = data.get('justification', '')
    target_date = data.get('target_date', '')

    if not facility_id or new_level < 1 or new_level > 5:
        return jsonify({'error': 'Valid facility ID and level (1-5) required'}), 400
    try:
        facility_id = int(facility_id)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid facility ID'}), 400

    if not require_facility_access(user, facility_id):
        return jsonify({'error': 'Access to this facility is denied'}), 403

    log = LevelUpgradeLog(
        facility_id=facility_id,
        source_type_code=source_type_code,
        old_level=old_level,
        new_level=new_level,
        target_date=target_date,
        justification=justification,
        created_by=session.get('user_id')
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'message': 'Level upgrade logged successfully', 'id': log.id}), 201

@data_bp.route('/ogmp/level-logs', methods=['GET'])
@login_required
def get_level_logs():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to view operational OGMP data.'}), 403
    query = LevelUpgradeLog.query
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None:
        query = query.filter(LevelUpgradeLog.facility_id.in_(allowed_fids))
    facility_id = request.args.get('facility_id')
    if facility_id:
        try:
            fid = int(facility_id)
            if allowed_fids is not None and fid not in allowed_fids:
                return jsonify({'error': 'Access to requested facility is denied'}), 403
            query = query.filter_by(facility_id=fid)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid facility_id'}), 400
    logs = query.order_by(LevelUpgradeLog.changed_at.desc()).all()
    return jsonify([{
        'id': l.id,
        'facility_id': l.facility_id,
        'facility_name': l.facility.name if l.facility else 'Unknown',
        'source_type_code': l.source_type_code,
        'old_level': l.old_level,
        'new_level': l.new_level,
        'target_date': l.target_date,
        'justification': l.justification,
        'changed_at': l.changed_at.isoformat() if l.changed_at else None
    } for l in logs])


# ==========================================
# CBAM PRODUCT EXPORTS
# ==========================================
@data_bp.route('/cbam-exports', methods=['GET'])
@data_bp.route('/cbam-exports/', methods=['GET'])
@login_required
def get_cbam_exports():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to view operational CBAM data.'}), 403
    query = CbamProductExport.query
    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None:
        query = query.filter(CbamProductExport.facility_id.in_(allowed_fids))
    if request.args.get('facilityId') and request.args.get('facilityId') != 'all':
        try:
            fid = int(request.args.get('facilityId'))
            if allowed_fids is not None and fid not in allowed_fids:
                return jsonify({'error': 'Access to requested facility is denied'}), 403
            query = query.filter_by(facility_id=fid)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid facilityId'}), 400
    if request.args.get('year') and request.args.get('year') != 'all':
        try:
            query = query.filter_by(year=int(request.args.get('year')))
        except (ValueError, TypeError):
            pass

    activity = request.args.get('activity')
    division = request.args.get('division')
    segment = request.args.get('segment')
    if (activity and activity != 'all') or (division and division != 'all') or (segment and segment != 'all'):
        query = query.join(Facility, CbamProductExport.facility_id == Facility.id)
        if activity and activity != 'all':
            query = query.filter(Facility.activity == activity)
        if division and division != 'all':
            query = query.filter(Facility.division == division)
        if segment and segment != 'all':
            query = query.filter(Facility.segment == segment)
    
    records = query.order_by(CbamProductExport.created_at.desc()).all()
    return jsonify([{
        'id': r.id,
        'facility_id': r.facility_id,
        'year': r.year,
        'month': r.month,
        'product_name': r.product_name,
        'cn_code': r.cn_code,
        'quantity_tonnes': r.quantity_tonnes,
        'export_destination': r.export_destination,
        'specific_embedded_direct': r.specific_embedded_direct,
        'specific_embedded_indirect': r.specific_embedded_indirect,
        'total_embedded_emissions': round(
            (r.quantity_tonnes or 0.0) * ((r.specific_embedded_direct or 0.0) + (r.specific_embedded_indirect or 0.0)),
            2
        ),
        'notes': r.notes,
        'created_at': r.created_at.isoformat() if r.created_at else None
    } for r in records])

@data_bp.route('/cbam-exports', methods=['POST'])
@data_bp.route('/cbam-exports/', methods=['POST'])
@login_required
def save_cbam_export():
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to modify operational CBAM data.'}), 403
    try:
        data = request.get_json() or {}
        record_id = data.get('id')
        facility_id = data.get('facility_id') or data.get('facilityId')
        year = int(data.get('year', 2026))
        month = int(data.get('month', 1))
        product_name = (data.get('product_name') or data.get('productName') or '').strip()
        cn_code = (data.get('cn_code') or data.get('cnCode') or '').strip()
        quantity_tonnes = float(data.get('quantity_tonnes') or data.get('quantityTonnes') or 0.0)
        export_destination = (data.get('export_destination') or data.get('exportDestination') or 'EU').strip()
        specific_embedded_direct = float(data.get('specific_embedded_direct') or data.get('specificEmbeddedDirect') or 0.0)
        specific_embedded_indirect = float(data.get('specific_embedded_indirect') or data.get('specificEmbeddedIndirect') or 0.0)
        notes = (data.get('notes') or '').strip()

        if not facility_id or not product_name or not cn_code or quantity_tonnes <= 0:
            return jsonify({'error': 'Facility, product name, valid CN code, and positive tonnage are required'}), 400
        try:
            facility_id = int(facility_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid facility ID'}), 400

        if not require_facility_access(user, facility_id):
            return jsonify({'error': 'Access to this facility is denied'}), 403

        total_direct_tco2e = db.session.query(func.coalesce(func.sum(Emission.co2e_total), 0.0)).filter(
            Emission.facility_id == facility_id,
            Emission.year == year,
            Emission.status == 'Verified'
        ).scalar()
        
        from models import Scope2Emission
        total_indirect_tco2e = db.session.query(func.coalesce(func.sum(Scope2Emission.co2e), 0.0)).filter(
            Scope2Emission.facility_id == facility_id,
            Scope2Emission.year == year,
            Scope2Emission.status == 'Verified'
        ).scalar()

        if specific_embedded_direct > 0:
            se_dir = specific_embedded_direct
        else:
            se_dir = round(total_direct_tco2e / quantity_tonnes, 4) if quantity_tonnes > 0 else 0.0

        if specific_embedded_indirect > 0:
            se_ind = specific_embedded_indirect
        else:
            se_ind = round(total_indirect_tco2e / quantity_tonnes, 4) if quantity_tonnes > 0 else 0.0

        if record_id:
            record = CbamProductExport.query.get(record_id)
            if not record:
                return jsonify({'error': 'Record not found'}), 404
            record.facility_id = facility_id
            record.year = year
            record.month = month
            record.product_name = product_name
            record.cn_code = cn_code
            record.quantity_tonnes = quantity_tonnes
            record.export_destination = export_destination
            record.specific_embedded_direct = se_dir
            record.specific_embedded_indirect = se_ind
            record.notes = notes
            action = 'UPDATE'
        else:
            user_id = session.get('user_id') if session else None
            record = CbamProductExport(
                facility_id=facility_id,
                year=year,
                month=month,
                product_name=product_name,
                cn_code=cn_code,
                quantity_tonnes=quantity_tonnes,
                export_destination=export_destination,
                specific_embedded_direct=se_dir,
                specific_embedded_indirect=se_ind,
                notes=notes,
                created_by=user_id
            )
            db.session.add(record)
            db.session.flush()
            action = 'CREATE'

        log_activity_and_notify(
            action=action,
            record_id=str(record.id),
            user=user,
            request=request,
            entity='CbamProductExport',
            details=f'{action} CBAM Export: {product_name} ({quantity_tonnes} t) to {export_destination}'
        )
        db.session.commit()
        return jsonify({'message': 'CBAM Export saved successfully', 'id': record.id})
    except Exception as e:
        import traceback
        from flask import current_app
        current_app.logger.error(f"CBAM Export save error: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@data_bp.route('/cbam-exports/<int:record_id>', methods=['DELETE'])
@login_required
def delete_cbam_export(record_id):
    user = get_current_user()
    if user and user.role == 'it_admin':
        return jsonify({'error': 'IT administrators are not authorized to modify operational CBAM data.'}), 403
    try:
        record = CbamProductExport.query.get(record_id)
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        if not require_facility_access(user, record.facility_id):
            return jsonify({'error': 'Access to this facility is denied'}), 403
        prod_name = record.product_name
        rec_id = record.id
        db.session.delete(record)
        log_activity_and_notify(
            action='DELETE',
            record_id=str(rec_id),
            user=user,
            request=request,
            entity='CbamProductExport',
            details=f'Deleted CBAM Export: {prod_name}'
        )
        db.session.commit()
        return jsonify({'message': 'CBAM export deleted successfully'})
    except Exception as e:
        import traceback
        from flask import current_app
        current_app.logger.error(f"CBAM Export delete error: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
