import datetime
from flask import Blueprint, request, jsonify, session, current_app
from models import CustomFactor, User
from extensions import db
from routes.auth import superuser_required, login_required
from utils import log_activity_and_notify

custom_factors_bp = Blueprint('custom_factors', __name__)

@custom_factors_bp.route('', methods=['GET'])
@login_required
def get_custom_factors():
    """Get all custom emission factors"""
    factors = CustomFactor.query.all()
    return jsonify([{
        'id': f.id,
        'factor_name': f.name,
        'co2_factor': float(f.co2_factor or 0),
        'ch4_factor': float(f.ch4_factor or 0),
        'n2o_factor': float(f.n2o_factor or 0),
        'unit': f.unit,
        'parent_fuel': f.parent_fuel,
        'uncertainty': float(f.uncertainty or 0),
        'co2_uncertainty': float(f.co2_uncertainty or 0),
        'ch4_uncertainty': float(f.ch4_uncertainty or 0),
        'n2o_uncertainty': float(f.n2o_uncertainty or 0)
    } for f in factors])

@custom_factors_bp.route('', methods=['POST'])
@superuser_required
def create_custom_factor():
    """Create a new custom emission factor (Super User / Admin only)"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    data = request.get_json()
    if not data or not data.get('factor_name'):
        return jsonify({'error': 'Factor name is required'}), 400
    
    factor = CustomFactor(
        name=data.get('factor_name'),
        co2_factor=data.get('co2_factor', 0),
        ch4_factor=data.get('ch4_factor', 0),
        n2o_factor=data.get('n2o_factor', 0),
        unit=data.get('unit', 'scf'),
        parent_fuel=data.get('parent_fuel'),
        uncertainty=data.get('uncertainty', 0),
        co2_uncertainty=data.get('co2_uncertainty', 0),
        ch4_uncertainty=data.get('ch4_uncertainty', 0),
        n2o_uncertainty=data.get('n2o_uncertainty', 0),
        created_by=user_id
    )
    
    db.session.add(factor)
    db.session.commit()

    try:
        log_activity_and_notify(
            action='CREATE',
            record_id=str(factor.id),
            user=user,
            request=request,
            entity='CustomFactor',
            details=f"Custom factor created: {factor.name}"
        )
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Audit log error on custom factor create: {e}")
    
    return jsonify({'message': 'Custom factor created', 'id': factor.id}), 201

@custom_factors_bp.route('/<int:factor_id>', methods=['PUT'])
@superuser_required
def update_custom_factor(factor_id):
    """Update a custom emission factor (Super User / Admin only)"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    factor = CustomFactor.query.get(factor_id)
    if not factor:
        return jsonify({'error': 'Factor not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    if 'factor_name' in data:
        factor.name = data['factor_name']
    if 'co2_factor' in data:
        factor.co2_factor = data['co2_factor']
    if 'ch4_factor' in data:
        factor.ch4_factor = data['ch4_factor']
    if 'n2o_factor' in data:
        factor.n2o_factor = data['n2o_factor']
    if 'co_factor' in data:
        factor.co_factor = data['co_factor']
    if 'unit' in data:
        factor.unit = data['unit']
    if 'hhv_factor' in data:
        factor.hhv_factor = data['hhv_factor']
    if 'usage' in data:
        factor.usage = data['usage']
    if 'parent_fuel' in data:
        factor.parent_fuel = data['parent_fuel']
    if 'source' in data:
        factor.source = data['source']
    if 'version' in data:
        factor.version = data['version']
    if 'uncertainty' in data:
        factor.uncertainty = data['uncertainty']
    if 'co2_uncertainty' in data:
        factor.co2_uncertainty = data['co2_uncertainty']
    if 'ch4_uncertainty' in data:
        factor.ch4_uncertainty = data['ch4_uncertainty']
    if 'n2o_uncertainty' in data:
        factor.n2o_uncertainty = data['n2o_uncertainty']
    
    factor.updated_by = user_id
    factor.updated_at = datetime.datetime.utcnow()
    
    db.session.commit()

    try:
        log_activity_and_notify(
            action='UPDATE',
            record_id=str(factor.id),
            user=user,
            request=request,
            entity='CustomFactor',
            details=f"Custom factor updated: {factor.name}"
        )
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Audit log error on custom factor update: {e}")
    
    return jsonify({'message': 'Custom factor updated'})

@custom_factors_bp.route('/<int:factor_id>', methods=['DELETE'])
@superuser_required
def delete_custom_factor(factor_id):
    """Delete a custom emission factor (Super User / Admin only)"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    factor = CustomFactor.query.get(factor_id)
    if not factor:
        return jsonify({'error': 'Factor not found'}), 404
    
    factor_name = factor.name
    db.session.delete(factor)
    db.session.commit()

    try:
        log_activity_and_notify(
            action='DELETE',
            record_id=str(factor_id),
            user=user,
            request=request,
            entity='CustomFactor',
            details=f"Custom factor deleted: {factor_name}"
        )
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Audit log error on custom factor delete: {e}")
    
    return jsonify({'message': 'Custom factor deleted'})

@custom_factors_bp.route('/import', methods=['POST'])
@superuser_required
def import_custom_factors():
    """Bulk import custom factors from CSV/Excel (Super User / Admin only)"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    data = request.get_json()
    factors_data = data.get('factors', [])
    
    if not factors_data:
        return jsonify({'error': 'No factors provided'}), 400
    
    imported_count = 0
    for factor_data in factors_data:
        factor = CustomFactor(
            name=factor_data.get('name'),
            co2_factor=factor_data.get('co2_factor', 0),
            ch4_factor=factor_data.get('ch4_factor', 0),
            n2o_factor=factor_data.get('n2o_factor', 0),
            co_factor=factor_data.get('co_factor', 0),
            unit=factor_data.get('unit'),
            hhv_factor=factor_data.get('hhv_factor', 0),
            usage=factor_data.get('usage'),
            parent_fuel=factor_data.get('parent_fuel'),
            source=factor_data.get('source'),
            version=factor_data.get('version'),
            uncertainty=factor_data.get('uncertainty', 0),
            co2_uncertainty=factor_data.get('co2_uncertainty', 0),
            ch4_uncertainty=factor_data.get('ch4_uncertainty', 0),
            n2o_uncertainty=factor_data.get('n2o_uncertainty', 0),
            created_by=user_id
        )
        db.session.add(factor)
        imported_count += 1
    
    db.session.commit()

    try:
        log_activity_and_notify(
            action='IMPORT',
            record_id=str(imported_count),
            user=user,
            request=request,
            entity='CustomFactor',
            details=f"Bulk imported {imported_count} custom emission factors"
        )
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Audit log error on custom factor import: {e}")
    
    return jsonify({'message': f'{imported_count} factors imported successfully'})
