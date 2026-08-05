from routes.auth import login_required
from flask import request, jsonify, session
import json
from . import data_bp
from utils import get_current_user, get_allowed_facility_ids, log_activity_and_notify
from sqlalchemy import func
from models import ProductionData, ActivityLog, User, Facility, CbamProductExport, OgmpSurvey
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
# CBAM PRODUCT EXPORTS
# ==========================================
@data_bp.route('/cbam-exports', methods=['GET'])
@login_required
def get_cbam_exports():
    query = CbamProductExport.query
    allowed_fids = get_allowed_facility_ids(get_current_user())
    if allowed_fids is not None:
        query = query.filter(CbamProductExport.facility_id.in_(allowed_fids))
    if request.args.get('facilityId'):
        query = query.filter_by(facility_id=request.args.get('facilityId'))
    if request.args.get('year'):
        query = query.filter_by(year=request.args.get('year'))
    if request.args.get('cn_code'):
        query = query.filter_by(cn_code=request.args.get('cn_code'))
        
    data = query.order_by(CbamProductExport.year.desc(), CbamProductExport.month.desc()).all()
    return jsonify([{
        'id': d.id,
        'facility_id': d.facility_id,
        'facilityId': d.facility_id,
        'facility_name': d.facility.name if d.facility else 'Unknown',
        'facilityName': d.facility.name if d.facility else 'Unknown',
        'year': d.year,
        'month': d.month,
        'product_name': d.product_name,
        'productName': d.product_name,
        'cn_code': d.cn_code,
        'cnCode': d.cn_code,
        'quantity_tonnes': d.quantity_tonnes,
        'quantityTonnes': d.quantity_tonnes,
        'export_destination': d.export_destination or 'EU',
        'exportDestination': d.export_destination or 'EU',
        'specific_embedded_direct': d.specific_embedded_direct or 0.0,
        'specificEmbeddedDirect': d.specific_embedded_direct or 0.0,
        'specific_embedded_indirect': d.specific_embedded_indirect or 0.0,
        'specificEmbeddedIndirect': d.specific_embedded_indirect or 0.0,
        'notes': d.notes or ''
    } for d in data])

@data_bp.route('/cbam-exports', methods=['POST'])
@login_required
def save_cbam_export():
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
    notes = data.get('notes') or ''

    if not facility_id or not product_name or not cn_code or quantity_tonnes <= 0:
        return jsonify({'error': 'Facility, product name, valid CN code, and positive tonnage are required'}), 400

    # Auto-calculate specific embedded emissions if available
    # Direct = Scope 1 tCO2e / product tonnes (if product matches facility production)
    from models import Emission, Scope2Emission
    total_direct_tco2e = db.session.query(func.coalesce(func.sum(Emission.co2e_total), 0.0)).filter(
        Emission.facility_id == facility_id,
        Emission.year == year
    ).scalar()

    total_indirect_tco2e = db.session.query(func.coalesce(func.sum(Scope2Emission.co2e), 0.0)).filter(
        Scope2Emission.facility_id == facility_id,
        Scope2Emission.year == year
    ).scalar()

    se_dir = round(total_direct_tco2e / quantity_tonnes, 4) if quantity_tonnes > 0 else 0.0
    se_indir = round(total_indirect_tco2e / quantity_tonnes, 4) if quantity_tonnes > 0 else 0.0

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
        record.specific_embedded_indirect = se_indir
        record.notes = notes
        action = 'UPDATE'
    else:
        record = CbamProductExport(
            facility_id=facility_id,
            year=year,
            month=month,
            product_name=product_name,
            cn_code=cn_code,
            quantity_tonnes=quantity_tonnes,
            export_destination=export_destination,
            specific_embedded_direct=se_dir,
            specific_embedded_indirect=se_indir,
            notes=notes,
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
            entity='CbamProductExport',
            details=f"{action.title()} CBAM export: {quantity_tonnes} tonnes of {product_name} (CN {cn_code}) to {export_destination}"
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'CBAM export record saved', 'id': record.id}), 201

@data_bp.route('/cbam-exports/<int:record_id>', methods=['DELETE'])
@login_required
def delete_cbam_export(record_id):
    record = CbamProductExport.query.get(record_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'CBAM export record deleted'})


# ==========================================
# OGMP 2.0 TOP-DOWN SURVEYS
# ==========================================
@data_bp.route('/ogmp-surveys', methods=['GET'])
@login_required
def get_ogmp_surveys():
    query = OgmpSurvey.query
    allowed_fids = get_allowed_facility_ids(get_current_user())
    if allowed_fids is not None:
        query = query.filter(OgmpSurvey.facility_id.in_(allowed_fids))
    if request.args.get('facilityId'):
        query = query.filter_by(facility_id=request.args.get('facilityId'))
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
        'estimated_annual_tch4': d.estimated_annual_tch4 or round(d.measured_rate_kg_hr * 8760 / 1000.0, 2),
        'estimatedAnnualTch4': d.estimated_annual_tch4 or round(d.measured_rate_kg_hr * 8760 / 1000.0, 2),
        'reconciliation_status': d.reconciliation_status or 'Reconciled',
        'reconciliationStatus': d.reconciliation_status or 'Reconciled',
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
    reconciliation_status = (data.get('reconciliation_status') or data.get('reconciliationStatus') or 'Reconciled').strip()
    operator_notes = data.get('operator_notes') or data.get('operatorNotes') or ''

    if not facility_id or not survey_date or measured_rate_kg_hr < 0:
        return jsonify({'error': 'Facility, survey date, and measured emission rate are required'}), 400

    estimated_annual_tch4 = round(measured_rate_kg_hr * 8760 / 1000.0, 2) # kg/hr * 8760 hr/yr / 1000 kg/t

    if record_id:
        record = OgmpSurvey.query.get(record_id)
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        record.facility_id = facility_id
        record.year = year
        record.survey_date = survey_date
        record.survey_type = survey_type
        record.measured_rate_kg_hr = measured_rate_kg_hr
        record.estimated_annual_tch4 = estimated_annual_tch4
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
            estimated_annual_tch4=estimated_annual_tch4,
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
