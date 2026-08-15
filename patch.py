cbam_code = '''
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
    from flask import jsonify
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
    from flask import request, jsonify, session
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
    from models import Emission, Scope2Emission
    total_direct_tco2e = db.session.query(func.coalesce(func.sum(Emission.co2e_total), 0.0)).filter(
        Emission.facility_id == facility_id,
        Emission.year == year,
        Emission.status != 'Draft'
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
            created_by=session.get('user_id') if hasattr(request, 'session') else None
        )
        db.session.add(record)
        action = 'CREATE'

    try:
        user_id = session.get('user_id') if session else None
        user = User.query.get(user_id) if user_id else None
        log_activity_and_notify(
            action=action,
            record_id=str(record.id or 'new'),
            user=user,
            request=request,
            entity='CbamProductExport',
            details=f\"{action.title()} CBAM export: {quantity_tonnes} tonnes of {product_name} (CN {cn_code}) to {export_destination}\"
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'CBAM export record saved', 'id': record.id}), 201

@data_bp.route('/cbam-exports/<int:record_id>', methods=['DELETE'])
@login_required
def delete_cbam_export(record_id):
    from flask import jsonify
    record = CbamProductExport.query.get(record_id)
    if not record:
        return jsonify({'error': 'Record not found'}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({'message': 'CBAM export record deleted'})
'''

data = open('new/server/routes/data.py', encoding='utf-8').read()
data = data.replace('# ==========================================\n# OGMP 2.0 TOP-DOWN SURVEYS & TAXONOMY', cbam_code + '\n# ==========================================\n# OGMP 2.0 TOP-DOWN SURVEYS & TAXONOMY')
open('new/server/routes/data.py', 'w', encoding='utf-8').write(data)
