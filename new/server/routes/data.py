from routes.auth import login_required
from flask import request, jsonify, session
import json
from . import data_bp
from utils import get_current_user, get_allowed_facility_ids, log_activity_and_notify
from sqlalchemy import func
from models import ProductionData, ActivityLog, User, Facility, OgmpSurvey, MethaneSourceType, LevelUpgradeLog, Emission
from extensions import db

@data_bp.route('/production', methods=['GET'])
@login_required
def get_production():
    query = ProductionData.query
    allowed_fids = get_allowed_facility_ids(get_current_user())
    if allowed_fids is not None:
        query = query.filter(ProductionData.facility_id.in_(allowed_fids))
    if request.args.get('facilityId'):
        query = query.filter_by(facility_id=request.args.get('facilityId'))
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
@login_required
def add_production():
    data = request.get_json()
    
    # Check if exists
    existing = ProductionData.query.filter_by(
        facility_id=data.get('facility_id'),
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
            facility_id=data.get('facility_id'),
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
        db.session.add(prod)
    
    # Audit + commit atomically
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None
        
        rec_id = existing.id if existing else prod.id
        action = 'UPDATE' if existing else 'CREATE'
        
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
    except Exception as e:
        db.session.rollback()
        print(f"Audit Log Error: {e}")

    return jsonify({'message': 'Production data saved'})

@data_bp.route('/production/<int:record_id>', methods=['DELETE'])
@login_required
def delete_production(record_id):
    prod = ProductionData.query.get(record_id)
    if not prod:
        return jsonify({'error': 'Production record not found'}), 404
    
    db.session.delete(prod)
    db.session.commit()
    return jsonify({'message': 'Production record deleted'})


@data_bp.route('/production/bulk-import', methods=['POST'])
@login_required
def bulk_import_production():
    data = request.get_json()
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
    return jsonify({'message': f'{imported_count} production records imported'}), 201





# ==========================================
# OGMP 2.0 TOP-DOWN SURVEYS & TAXONOMY
# ==========================================
@data_bp.route('/methane-sources', methods=['GET'])
@login_required
def get_methane_sources():
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
@login_required
def get_ogmp_surveys():
    query = OgmpSurvey.query
    allowed_fids = get_allowed_facility_ids(get_current_user())
    if allowed_fids is not None:
        query = query.filter(OgmpSurvey.facility_id.in_(allowed_fids))
    if request.args.get('facilityId'):
        query = query.filter_by(facility_id=request.args.get('facilityId'))
    if request.args.get('segment'):
        query = query.join(Facility, OgmpSurvey.facility_id == Facility.id).filter(Facility.segment == request.args.get('segment'))
    if request.args.get('year'):
        query = query.filter_by(year=request.args.get('year'))
    if request.args.get('survey_type'):
        query = query.filter_by(survey_type=request.args.get('survey_type'))

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
@login_required
def save_ogmp_survey():
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

    estimated_annual_tch4 = round(measured_rate_kg_hr * operating_hours / 1000.0, 2)

    # Compute bottom-up methane total for facility & year to compute variance
    fac = Facility.query.get(facility_id)
    bottom_up_sum = db.session.query(func.sum(Emission.ch4_emissions)).filter(
        Emission.facility_id == facility_id,
        Emission.year == year,
        Emission.status != 'Draft'
    ).scalar() or 0.0
    bottom_up_tch4 = round(float(bottom_up_sum), 2)

    # Compute variance %
    variance_pct = round(((estimated_annual_tch4 - bottom_up_tch4) / bottom_up_tch4 * 100.0), 2) if bottom_up_tch4 > 0 else 0.0
    threshold = (fac.reconciliation_threshold if fac and fac.reconciliation_threshold else 20.0)
    variance_flag = abs(variance_pct) > threshold

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
        action = 'CREATE'

    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None
        log_activity_and_notify(
            action=action,
            record_id=str(record.id or 'new'),
            user=user,
            request=request,
            entity='OgmpSurvey',
            details=f"{action.title()} OGMP 2.0 top-down survey: {measured_rate_kg_hr} kg CH4/hr via {survey_type} at {record.facility.name if record.facility else facility_id}"
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'OGMP survey record saved', 'id': record.id}), 201

@data_bp.route('/ogmp-surveys/<int:record_id>', methods=['DELETE'])
@login_required
def delete_ogmp_survey(record_id):
    record = OgmpSurvey.query.get(record_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'OGMP survey record deleted'})

@data_bp.route('/ogmp/level-upgrade', methods=['POST'])
@login_required
def log_level_upgrade():
    data = request.get_json() or {}
    facility_id = data.get('facility_id')
    old_level = int(data.get('old_level', 3))
    new_level = int(data.get('new_level', 4))
    source_type_code = data.get('source_type_code', 'ALL')
    justification = data.get('justification', '')
    target_date = data.get('target_date', '')

    if not facility_id or new_level < 1 or new_level > 5:
        return jsonify({'error': 'Valid facility ID and level (1-5) required'}), 400

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
    facility_id = request.args.get('facility_id')
    query = LevelUpgradeLog.query
    if facility_id:
        query = query.filter_by(facility_id=facility_id)
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

